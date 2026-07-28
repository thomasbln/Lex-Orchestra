"""ADR-102 Doc-Linter — violation pattern assertions.

Renders all 8 document types using rand_industries fixture data and asserts
that none of the violation strings defined in ADR-102 §7 appear in rendered output.

Does NOT require a live DB connection — builds ContentModels from fixtures and
renders via a local Jinja environment.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parents[1] / "src" / "templates"
FIXTURE = Path(__file__).parent / "fixtures"
DEFAULT_CONFIG = "rand_industries_config.json"
GAPS_CONFIG = "rand_industries_config_gaps.json"  # empty required fields — the gap-path fixture


def _load_config(lang: str, config_file: str = DEFAULT_CONFIG) -> dict:
    config = json.loads((FIXTURE / config_file).read_text())
    config["doc_language"] = lang
    return config


def _linter_gap_hints(config: dict, config_file: str):
    """Default fixture -> pre-baked gap list; gaps fixture -> LIVE detectors,
    so the warn-header/gap branches actually fire (fixture-drift lesson)."""
    from src.scanner.gap_analyzer import GapHint, analyze_gaps
    if config_file == DEFAULT_CONFIG:
        gaps_raw = json.loads((FIXTURE / "rand_industries_gaps.json").read_text())
        return [GapHint(**g) if isinstance(g, dict) else g for g in gaps_raw]
    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    return analyze_gaps("rand-industries", config, None, [],
                        graph.get("services", []), None)


# ADR-102 §7: violation patterns that must be absent from all rendered output
VIOLATION_PATTERNS = [
    "Status dokumentieren",
    "_(Datum eintragen",
    "REST / SDK",
    "(Vertragsbedingungen",
    "Datenminimierung prüfen",
    "## Standardmaßnahmen",
]

# Context-specific: (prüfen) as a table cell value (not part of a longer phrase like "Ergebnisse prüfen")
VIOLATION_PATTERN_PRUEFEN = "(prüfen)"


# ---------------------------------------------------------------------------
# Jinja environment (no DB required)
# ---------------------------------------------------------------------------

def _make_jinja(lang: str = "de") -> Environment:
    # B-2 row 11 (EN package): lang-parametrised — the linter previously loaded
    # ONLY de/ and rendered everything German; there was zero automated EN
    # render coverage (the structural cause of the B-2 leak list).
    env = Environment(
        loader=FileSystemLoader([str(TEMPLATES_DIR / lang), str(TEMPLATES_DIR)]),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.globals["has_signal"] = lambda name, min_confidence=0.5: False
    env.globals["inline_gap_marker"] = lambda gap_id: f"🔴 [{gap_id}]"

    # de_date filter — mirrors document_architect's production registration so the
    # linter renders templates that use `| de_date` (PR-B Mini-Gate).
    def _de_date(value):
        if not value:
            return value
        try:
            from datetime import date
            return date.fromisoformat(str(value)).strftime("%d.%m.%Y")
        except (ValueError, TypeError):
            return value
    env.filters["de_date"] = _de_date

    # en_date + en_cite — mirror document_architect's production registration
    # (harness-mirror lesson, 2026-06-07: a filter missing here fails ONLY in
    # the linter while production is green).
    def _en_date(value):
        if not value:
            return value
        try:
            from datetime import date
            d = date.fromisoformat(str(value))
            return f"{d.day} {d.strftime('%B %Y')}"
        except (ValueError, TypeError):
            return value
    env.filters["en_date"] = _en_date

    def _en_cite(value):
        import re as _re
        if not value:
            return value
        parts = [p.strip() for p in str(value).split(";")]
        out = []
        for p in parts:
            gdpr = p.startswith("DSGVO ")
            if gdpr:
                p = p[len("DSGVO "):]
            p = _re.sub(r"Abs\. (\d+)", r"(\1)", p)
            p = _re.sub(r"lit\. ([a-z])", r"(\1)", p)
            p = _re.sub(r"\s*Satz \d+", "", p)   # sentence counting dropped in EN (2026-07-28)
            p = _re.sub(r"Nr\. (\d+)", r"no. \1", p)
            p = _re.sub(r"Anhang III", "Annex III", p)
            p = p.replace("(TOM-Nachweispflicht)", "(TOM accountability)")
            p = _re.sub(r"Art\. (\d+) \(", r"Art. \1(", p)
            p = p.replace(") (", ")(")
            if gdpr:
                p += " GDPR"
            out.append(p)
        return "; ".join(out)
    env.filters["en_cite"] = _en_cite
    return env


def _base_ctx(lang: str = "de", config_file: str = DEFAULT_CONFIG) -> dict:
    """Minimal flat context that satisfies all template header variables.
    No value-inventing defaults — with the gaps fixture the empty fields must
    reach the templates so the fallback branches fire."""
    config = _load_config(lang, config_file)
    return {
        "lang":            lang,   # _warn_header / _bfdi_footer branch on this
        "project_name":    "rand-industries",
        "run_id":          "linter-test-00000000",
        "generation_date": "2026-04-23",
        # harness-mirror of _common_config_context: the flat header fields
        # carry the SAME language-pure fallbacks as production, so the gaps
        # fixture exercises the real header path.
        "company_name":    config.get("company_name") or "rand-industries",
        "legal_form":      config.get("legal_form", ""),
        "address":         config.get("address") or ("(add address)" if lang == "en" else "(Adresse eintragen)"),
        "zip_code":        config.get("zip_code", ""),
        "city":            config.get("city", ""),
        "zip_city":        config.get("zip_city", ""),
        "contact_email":   config.get("contact_email") or ("(add e-mail)" if lang == "en" else "(E-Mail eintragen)"),
        "website_url":     config.get("website_url", ""),
        "responsible_name":  config.get("responsible_name", ""),
        "responsible_title": config.get("responsible_title", ""),
        "dpo_name":        config.get("dpo_name", ""),
        "dpo_email":       config.get("dpo_email", ""),
        "register_court":  "",
        "register_number": "",
        "fields":          {},
        "project":         {"on_prem": False, "hosting_provider": None, "hosting_region": None},
    }


# ---------------------------------------------------------------------------
# Per-document render helpers
# ---------------------------------------------------------------------------

def _render_avv(env: Environment, lang: str = "de", config_file: str = DEFAULT_CONFIG) -> str:
    from src.documents.builders.avv_builder import AVVBuilder
    from src.documents.content_models import BuildContext
    from src.scanner.gap_analyzer import GapHint

    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    config = _load_config(lang, config_file)
    gap_hints = _linter_gap_hints(config, config_file)
    ctx = BuildContext(run_id="linter000", generation_date="2026-04-23", project_name="rand-industries")
    model = AVVBuilder().build(graph, {}, config, gap_hints, ctx)
    ctx_dict = _base_ctx(lang, config_file)
    ctx_dict["model"] = dataclasses.asdict(model)
    ctx_dict["services"] = graph.get("services", [])
    # ADR-129 PR N4 (re-audit B-4): feed the builder's real deletion rows so § 7
    # actually renders bullets — with [] the trim_blocks regression guard
    # (test_avv_deletion_list_renders_one_bullet_per_line) inspected an empty
    # section and could never fail.
    ctx_dict["deletion_periods"] = dataclasses.asdict(model)["deletion_periods"]
    ctx_dict["transfer_mechanism"] = None
    ctx_dict["instructing_persons"] = config.get("instructing_persons", [])
    return env.get_template("avv.md.j2").render(**ctx_dict)


def _render_tom(env: Environment, lang: str = "de", config_file: str = DEFAULT_CONFIG) -> str:
    from src.documents.builders.tom_builder import TOMBuilder
    from src.documents.content_models import BuildContext
    from src.agents.document_architect import TOM_SECTION_ORDER

    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    config = _load_config(lang, config_file)
    ctx = BuildContext(run_id="linter000", generation_date="2026-04-23", project_name="rand-industries")
    model = TOMBuilder().build(graph, {}, config, [], ctx)
    ctx_dict = _base_ctx(lang, config_file)
    ctx_dict["model"] = dataclasses.asdict(model)
    ctx_dict["priority_actions"] = []
    ctx_dict["active_risks"] = graph.get("active_risks", [])
    ctx_dict["controls_by_section"] = {}
    ctx_dict["tom_section_order"] = TOM_SECTION_ORDER
    # harness-mirror: production (_write_tom) passes the display-label table
    from src.documents.builders.tom_builder import TOM_SECTION_LABELS
    ctx_dict["tom_section_labels"] = TOM_SECTION_LABELS.get(lang, {})
    return env.get_template("tom.md.j2").render(**ctx_dict)


def _render_vvt(env: Environment, lang: str = "de", config_file: str = DEFAULT_CONFIG) -> str:
    from src.documents.builders.vvt_builder import VVTBuilder
    from src.documents.content_models import BuildContext

    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    config = _load_config(lang, config_file)
    ctx = BuildContext(run_id="linter000", generation_date="2026-04-23", project_name="rand-industries")
    model = VVTBuilder().build(graph, {}, config, [], ctx)
    ctx_dict = _base_ctx(lang, config_file)
    ctx_dict["model"] = dataclasses.asdict(model)
    return env.get_template("vvt.md.j2").render(**ctx_dict)


def _render_ki_policy(env: Environment, lang: str = "de", config_file: str = DEFAULT_CONFIG) -> str:
    from src.documents.builders.ki_policy_builder import KIPolicyBuilder
    from src.documents.content_models import BuildContext

    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    config = _load_config(lang, config_file)
    ai_services = [s for s in graph.get("services", []) if s.get("ai_act_relevant") or s.get("category") == "ai_llm"]
    ctx = BuildContext(run_id="linter000", generation_date="2026-04-23", project_name="rand-industries")
    model = KIPolicyBuilder().build({"services": ai_services}, {}, config, [], ctx)
    ctx_dict = _base_ctx(lang, config_file)
    ctx_dict["model"] = dataclasses.asdict(model)
    return env.get_template("ki_policy.md.j2").render(**ctx_dict)


def _render_ki_system(env: Environment, lang: str = "de", config_file: str = DEFAULT_CONFIG) -> str:
    from src.documents.builders.ki_system_builder import KISystemBuilder
    from src.documents.content_models import BuildContext

    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    config = _load_config(lang, config_file)
    ai_services = [s for s in graph.get("services", []) if s.get("ai_act_relevant") or s.get("category") == "ai_llm"]
    service = ai_services[0] if ai_services else {"name": "OpenAI", "category": "ai_llm"}
    ai_usecase = {"type": "hr_recruitment_screening", "risk_level": "High",
                  "title_de": "HR-Recruiting", "description_de": "Bewerberauswahl",
                  "article": "6", "annex_iii_nr": 4, "deployer_action": "Konformitätsbewertung"}
    ctx = BuildContext(run_id="linter000", generation_date="2026-04-23", project_name="rand-industries")
    model = KISystemBuilder().build(graph, {}, config, [], ctx, service=service, ai_usecase=ai_usecase)
    ctx_dict = _base_ctx(lang, config_file)
    ctx_dict["model"] = dataclasses.asdict(model)
    return env.get_template("ki_system.md.j2").render(**ctx_dict)


def _render_dsfa(env: Environment, lang: str = "de", config_file: str = DEFAULT_CONFIG) -> str:
    from src.documents.builders.dsfa_builder import DSFABuilder
    from src.documents.content_models import BuildContext

    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    config = _load_config(lang, config_file)
    ai_usecase = {"type": "hr_recruitment_screening", "risk_level": "High",
                  "title_de": "HR-Recruiting", "description_de": "Bewerberauswahl",
                  "article": "6", "annex_iii_nr": 4}
    ctx = BuildContext(run_id="linter000", generation_date="2026-04-23", project_name="rand-industries")
    model = DSFABuilder().build(graph, {}, config, [], ctx, ai_usecase=ai_usecase)
    ctx_dict = _base_ctx(lang, config_file)
    ctx_dict["model"] = dataclasses.asdict(model)
    return env.get_template("dsfa.md.j2").render(**ctx_dict)


def _render_ai_act_manifest(env: Environment, lang: str = "de", config_file: str = DEFAULT_CONFIG) -> str:
    from src.documents.builders.ai_act_builder import AIActBuilder
    from src.documents.content_models import BuildContext

    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    config = _load_config(lang, config_file)
    ctx = BuildContext(run_id="linter000", generation_date="2026-04-23", project_name="rand-industries")
    model = AIActBuilder().build(graph, {}, config, [], ctx)
    ctx_dict = _base_ctx(lang, config_file)
    ctx_dict["model"] = dataclasses.asdict(model)
    return env.get_template("ai_act_manifest.md.j2").render(**ctx_dict)


def _render_scan_report(env: Environment, lang: str = "de", config_file: str = DEFAULT_CONFIG) -> str:
    from src.documents.builders.scan_report_builder import ScanReportBuilder
    from src.documents.content_models import BuildContext
    from src.scanner.gap_analyzer import GapHint

    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    config = _load_config(lang, config_file)
    gap_hints = _linter_gap_hints(config, config_file)
    ctx = BuildContext(run_id="linter000", generation_date="2026-04-23", project_name="rand-industries")
    signals = graph.get("signals", [])
    active_risks = graph.get("active_risks", [])
    usecase_risks = graph.get("usecase_risks", [])
    model = ScanReportBuilder().build(graph, {}, config, gap_hints, ctx,
                                      risk_signals=signals)
    return env.get_template("scan_report.md.j2").render(model=dataclasses.asdict(model))


# ---------------------------------------------------------------------------
# Rendered outputs fixture — rendered once, shared across all violation tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def rendered_docs() -> dict[str, str]:
    env = _make_jinja()
    return {
        "AVV":              _render_avv(env),
        "TOM":              _render_tom(env),
        "VVT":              _render_vvt(env),
        "KI-Policy":        _render_ki_policy(env),
        "KI-System":        _render_ki_system(env),
        "DSFA":             _render_dsfa(env),
        "AI-Act-Manifest":  _render_ai_act_manifest(env),
        "Scan-Report":      _render_scan_report(env),
    }


# ---------------------------------------------------------------------------
# Linter assertions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("pattern", VIOLATION_PATTERNS)
def test_no_violation_pattern(rendered_docs, pattern):
    """ADR-102 §7: violation pattern must be absent from all 8 rendered documents."""
    violations = [
        doc_type for doc_type, content in rendered_docs.items()
        if pattern in content
    ]
    assert not violations, (
        f"Violation pattern {pattern!r} found in: {violations} — "
        "ADR-102 §7 compliance failure"
    )


def test_no_pruefen_table_cell(rendered_docs):
    """ADR-102 §7: '(prüfen)' as a table cell value must be absent from all documents."""
    violations = [
        doc_type for doc_type, content in rendered_docs.items()
        if VIOLATION_PATTERN_PRUEFEN in content
    ]
    assert not violations, (
        f"Violation pattern {VIOLATION_PATTERN_PRUEFEN!r} found in: {violations} — "
        "ADR-102 §7 compliance failure"
    )


ENGINE_JARGON = [
    "aus dem Graph",
    "ServiceCategory",
    "Knowledge-Graph",
    "Knowledge Graph",
    "SupervisoryAuthority",
]

# ADR-121 C2: scan the 8 raw DE template sources directly — rendered_docs omits
# SCC, and engine jargon must be caught at the source for every doc type.
import re as _re_jargon  # noqa: E402
_DE_TEMPLATES = sorted((TEMPLATES_DIR / "de").glob("*.md.j2")) + [
    TEMPLATES_DIR / "_ebene0_box.md.j2",  # ADR-121 Ebene-0 box partial
]


@pytest.mark.parametrize("template_path", _DE_TEMPLATES, ids=lambda p: p.name)
def test_no_engine_jargon_in_de_templates(template_path):
    """ADR-121 C2 / wording memo: documents show evidence, never method words.

    Engine internals ('Graph', 'ServiceCategory', internal ADR/PR refs) must not
    leak into the rendered customer documents — checked at template source.
    """
    source = template_path.read_text(encoding="utf-8")
    # Jinja comments are stripped first (2026-07-28): `{# ... #}` provably cannot
    # reach a rendered document, so flagging an ADR reference inside one is a
    # false positive that punishes documenting a template. Everything outside a
    # comment is still scanned unchanged — jargon in the body still fails.
    source = _re_jargon.sub(r"\{#.*?#\}", "", source, flags=_re_jargon.DOTALL)
    hits = [j for j in ENGINE_JARGON if j in source]
    # Internal ADR/PR references (e.g. "ADR-106 PR B4") are also jargon.
    if _re_jargon.search(r"\bPR\s?B\d", source) or _re_jargon.search(r"\bADR-\d{3}\b", source):
        hits.append("internal ADR/PR reference")
    assert not hits, (
        f"Engine jargon {hits!r} found in {template_path.name} — "
        "ADR-121 C2: show provenance, not the machine"
    )


def test_all_8_docs_render_without_error(rendered_docs):
    """All 8 document types must render without exception."""
    assert len(rendered_docs) == 8
    for doc_type, content in rendered_docs.items():
        assert isinstance(content, str) and len(content) > 100, (
            f"{doc_type} rendered empty or too short"
        )


# ---------------------------------------------------------------------------
# ADR-110 regression riegel — delegated Stripe must not assert card data
# ---------------------------------------------------------------------------

def _stripe_delegated_graph() -> dict:
    """Minimal graph_result: Stripe (US, SCC-relevant) with delegated mode."""
    return {
        "services": [{
            "name": "Stripe", "country": "USA", "gdpr_adequate": False,
            "dpa_required": True, "category": "payment",
            "data_categories": "Zahlungsdaten, Kreditkartendaten (tokenisiert), "
                               "Rechnungsadressen, Transaktionsdaten",
            "data_subjects": "Kunden", "integration_mode": "delegated",
        }],
        "docs_required": [], "doc_types": [], "controls": [], "risk_levels": [],
    }


def test_adr110_delegated_stripe_no_card_data_in_avv_vvt_scc():
    """ADR-110 riegel: Stripe + delegated ⇒ no 'Kreditkartendaten' in AVV/VVT/SCC,
    and the delegated wording is present instead. Locks the fixed error as a
    regression across all three documents from one run."""
    from src.documents.builders.avv_builder import AVVBuilder
    from src.documents.builders.vvt_builder import VVTBuilder
    from src.documents.builders.scc_builder import SCCBuilder
    from src.documents.content_models import BuildContext

    env = _make_jinja()
    graph = _stripe_delegated_graph()
    config = json.loads((FIXTURE / "rand_industries_config.json").read_text())
    config["doc_language"] = "de"   # this riegel asserts the DE wording
    ctx = BuildContext(run_id="adr110000", generation_date="2026-05-31", project_name="shop")
    base = _base_ctx()

    avv = AVVBuilder().build(graph, {}, config, [], ctx)
    vvt = VVTBuilder().build(graph, {}, config, [], ctx)
    scc = SCCBuilder().build(graph, {}, config, [], ctx)
    assert scc is not None, "Stripe US must be SCC-relevant (precondition)"

    avv_out = env.get_template("avv.md.j2").render(
        **{**base, "model": dataclasses.asdict(avv), "services": graph["services"],
           "deletion_periods": [], "transfer_mechanism": None, "instructing_persons": []})
    vvt_out = env.get_template("vvt.md.j2").render(**{**base, "model": dataclasses.asdict(vvt)})
    scc_out = env.get_template("scc.md.j2").render(**{**base, "model": dataclasses.asdict(scc)})

    for doc, out in [("AVV", avv_out), ("VVT", vvt_out), ("SCC", scc_out)]:
        assert "Kreditkartendaten" not in out, \
            f"{doc}: delegated Stripe still asserts 'Kreditkartendaten'"
        assert "direkt vom Zahlungsdienstleister" in out, \
            f"{doc}: delegated wording missing"


def test_avv_deletion_list_renders_one_bullet_per_line(rendered_docs):
    """ADR-129 PR 15/17 regression guard: an inline {% endif %} at line end lets
    trim_blocks eat the newline — § 7 bullets must never glue onto one line.

    PR N4 (re-audit B-4): guard is only meaningful with real bullets — assert
    the section is non-empty first, so a fixture regression (empty
    deletion_periods) turns the guard red instead of vacuous."""
    import re
    assert re.search(r"^- \*\*", rendered_docs["AVV"], re.M), \
        "AVV § 7 rendered no bullets — the trim_blocks guard has nothing to inspect"
    assert not re.search(r"\*\*: [^\n]*- \*\*", rendered_docs["AVV"]), \
        "AVV § 7 bullets glued into one line (trim_blocks regression)"


# ---------------------------------------------------------------------------
# B-2 row 11 (EN package, 2026-07-16): EN render linter
# The structural cause of the B-2 leak list was that this file rendered ONLY
# German. The fixture below renders the 8 EN legal documents (scan report is
# DE-only by design, ADR-129); the assert catches German signals with a
# documented accepted-remnant whitelist. Flip criterion (ADR-126): no German
# except the deliberately-labelled Class-C BfDI footer.
# ---------------------------------------------------------------------------

def _render_scc(env: Environment, lang: str = "de", config_file: str = DEFAULT_CONFIG) -> str:
    from src.documents.builders.scc_builder import SCCBuilder
    from src.documents.content_models import BuildContext

    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    config = _load_config(lang, config_file)
    ctx = BuildContext(run_id="linter000", generation_date="2026-04-23", project_name="rand-industries")
    model = SCCBuilder().build(graph, {}, config, [], ctx)
    if model is None:
        return ""
    ctx_dict = _base_ctx(lang, config_file)
    ctx_dict["model"] = dataclasses.asdict(model)
    return env.get_template("scc.md.j2").render(**ctx_dict)


@pytest.fixture(scope="module")
def rendered_docs_en() -> dict[str, str]:
    # EN close-out: all NINE doc types — the scan report was the 9th type that
    # fell through the original 8-count (analysis 2026-07-28).
    env = _make_jinja("en")
    return {
        "AVV":             _render_avv(env, "en"),
        "TOM":             _render_tom(env, "en"),
        "VVT":             _render_vvt(env, "en"),
        "SCC":             _render_scc(env, "en"),
        "KI-Policy":       _render_ki_policy(env, "en"),
        "KI-System":       _render_ki_system(env, "en"),
        "DSFA":            _render_dsfa(env, "en"),
        "AI-Act-Manifest": _render_ai_act_manifest(env, "en"),
        "Scan-Report":     _render_scan_report(env, "en"),
    }


# ═══════════════════════════════════════════════════════════════════════════
# EN-linter blind-spot inventory — EVERY deliberate exception in one place.
# Each entry is a spot where this linter cannot see German; the TOM-§ column
# leak stayed invisible through exactly this mechanic. Extend this list ONLY
# with a one-line justification.
#
# Explicit exceptions (enforced below):
#   1. Service.deletion_period values   — L14, graph data; owner text, own seed
#      strand post-release (_accepted_remnants).
#   2. TOM-§ taxonomy — EXCEPTION DROPPED 2026-07-28: the EN TOM now renders
#      display labels (TOM_SECTION_LABELS, § 64(3) BDSG-EN terms); the 11
#      German section words joined the stopword list below as a ratchet.
#      Keys stay German (identity) — ADR-079 remains open.
#   3. BfDI footer block                — Class C, deliberately German with an
#      "unofficial for EN readers" label; block is cut, not word-whitelisted
#      (_strip_accepted).
#
# Implicit blind spots (pass because _GERMAN_STOPWORDS is deliberately NOT
# exhaustive and they carry no umlaut):
#   4. Doc-type name TOM                — stands in the EN document itself
#      ("Technical and Organisational Measures (TOM)"), kept by decision.
#      AVV / VVT / DSFA are NOT exceptions anymore (unification 2026-07-28:
#      gap prose, annex list AND affected column all say DPA / RoPA / DPIA;
#      full probe over 9 EN renders + live-gap render = 0 hits) — they are in
#      the stopword list below as a permanent re-introduction guard.
#   5. "Impressum"                      — German legal institution, proper noun
#      in EN prose (gap_reason_en references it deliberately).
#   6. "a.s.k. Datenschutz"             — vendor name in the TOM template
#      footer (en/tom.md.j2), not prose.
#   7. The stopword list itself         — heuristic by design; umlaut check
#      carries most of the load, the list only catches umlaut-free leaks.
# ═══════════════════════════════════════════════════════════════════════════

# German signals: umlauts + high-frequency legal/German stopwords. Deliberately
# NOT exhaustive — the umlaut check catches most German; the word list catches
# umlaut-free leaks ("eintragen", "weitere", ...).
_GERMAN_STOPWORDS = [
    "gemäß", "Verantwortlicher", "Auftragsverarbeiter", "Verarbeitung",
    "Rechtsgrundlage", "Maßnahme", "eintragen", "ausstehend", "ausfüllen",
    "Pflicht", "Empfänger", "Betroffene", "Speicherfrist", "Hinweis",
    "Entwurf", "fehlt", "Anschrift", "Unterzeichner", "weitere", "Zweck",
    # German doc acronyms — EN says DPA / RoPA / DPIA everywhere (2026-07-28
    # unification); any reappearance is a leak, not an identifier.
    "AVV", "VVT", "DSFA",
    # Doc-type keys + their German display names — the affected column maps
    # them per language (_AFFECTED_DOC_EN/_DE); a raw key or German doc name
    # reappearing in the EN path is a leak (probe 2026-07-28: 0 hits for all).
    "AI_Act_Manifest", "KI_Policy", "KI_System_Dokumentation",
    "KI-Nutzungsrichtlinie", "KI-System-Dokumentation", "Risiko-Manifest",
    "KI-System", "Dokumentation",
    # TOM-§ taxonomy — the EN TOM renders § 64(3) BDSG-EN display labels
    # (TOM_SECTION_LABELS) since 2026-07-28; a German section word in the EN
    # path is a leak again, not an accepted remnant. ('Privacy by Design' is
    # English — no stopword needed for 4.3.)
    "Zutrittskontrolle", "Zugangskontrolle", "Zugriffskontrolle",
    "Trennungskontrolle", "Pseudonymisierung", "Weitergabekontrolle",
    "Eingangskontrolle", "Verfügbarkeitskontrolle", "Datenschutz-Maßnahmen",
    "Incident-Response-Management", "Auftragskontrolle",
]


def _accepted_remnants() -> list[str]:
    """Exact substrings that MAY be German in an EN document (documented):
    - L14 (accepted): Service.deletion_period values — owner text, own seed
      strand post-release. (The TOM-§ taxonomy exception was DROPPED
      2026-07-28: the EN TOM renders TOM_SECTION_LABELS now, and the German
      section words are stopword-ratcheted instead.)
    - Class-C content is handled by cutting the BfDI footer block instead
    """
    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    return [s.get("deletion_period") for s in graph.get("services", [])
            if s.get("deletion_period")]


def _strip_accepted(text: str) -> str:
    # Class-C BfDI footer: deliberately German (flip criterion) — cut the block.
    cut = text.find("## BfDI source references")
    if cut != -1:
        text = text[:cut]
    for r in _accepted_remnants():
        text = text.replace(r, "")
    return text


def _render_scan_report_live_gaps(lang: str) -> str:
    """Scan report rendered from LIVE analyze_gaps output on an empty config.

    The fixture gaps are pre-baked; this path proves the gap branches actually
    fire (empty required fields → company/address/… hints) so fix_label /
    gap_reason reach the render in the requested language.
    """
    from src.documents.builders.scan_report_builder import ScanReportBuilder
    from src.documents.content_models import BuildContext
    from src.scanner.gap_analyzer import analyze_gaps

    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    hints = analyze_gaps(
        project_name="rand-industries",
        config={"doc_language": lang},   # everything else empty → gaps fire
        setup=None, retention_policies=[], services_detected=[],
        extraction_summary=None,
    )
    assert len(hints) >= 8, "empty config must fire the company/hosting/retention detectors"
    ctx = BuildContext(run_id="gapline0", generation_date="2026-04-23",
                       project_name="rand-industries")
    model = ScanReportBuilder().build(
        graph, {}, {"doc_language": lang}, hints, ctx,
        generated_doc_types=["AVV", "TOM", "VVT"],
    )
    env = _make_jinja(lang)
    return env.get_template("scan_report.md.j2").render(model=dataclasses.asdict(model))


def test_scan_report_live_gap_path_en_language_pure():
    """EN close-out: live-emitted gap hints render English in the EN report."""
    import re
    text = _strip_accepted(_render_scan_report_live_gaps("en"))
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if any(u in line for u in "äöüÄÖÜß"):
            hits.append((i, "umlaut", line.strip()[:90]))
            continue
        for w in _GERMAN_STOPWORDS:
            if re.search(rf"\b{re.escape(w)}\b", line):
                hits.append((i, w, line.strip()[:90]))
                break
    assert not hits, "Scan-Report (live gaps): German in EN render:\n" + "\n".join(
        f"  line {n} [{why}]: {frag}" for n, why, frag in hits[:12]
    )
    assert "Set company details" in text          # fix_label_en fired
    assert "Company name not configured" in text  # gap_reason_en fired
    # Review 2026-07-28 corrections — each fires live, not merely exists:
    assert "privacy policy and RoPA cannot state storage periods" in text   # VVT→RoPA
    assert "required in the DPA signature block and the RoPA" in text       # AVV→DPA
    assert "per Art. 28(3)(a) GDPR" in text                                 # norm at the law, EN citation style
    assert "among others `privacy.html`, `impressum.html`, `DPA.*`" in text  # real globs, marked as selection
    assert re.search(r"\bAVV Art\.", text) is None                          # no law glued to a doc name
    # Unification 2026-07-28: affected column + annex list use the EN doc names
    assert re.search(r"Affected documents:\*\* .*\bAVV\b", text) is None
    assert re.search(r"Affected documents:\*\* .*\bVVT\b", text) is None
    assert "DPA, TOM, RoPA" in text or "DPA, RoPA" in text                  # mapped column fired


def test_scan_report_live_gap_path_de_labels_german():
    """The DE side of the axis: previously-English labels are now German."""
    text = _render_scan_report_live_gaps("de")
    assert "Firmenangaben setzen" in text                      # was "Set company details"
    assert "Unternehmensname nicht konfiguriert" in text       # was English gap_reason
    assert "Set company details" not in text


def test_scan_report_en_all_blocks_language_pure():
    """The rand_industries fixture leaves signals / usecase blocks / Ebene-0
    empty — this render activates EVERY template block (signals, high-risk
    usecase incl. deployer_action_en, Ebene-0, repo extractions, HR actions)
    and asserts the EN output stays language-pure."""
    import re
    from src.documents.builders.scan_report_builder import ScanReportBuilder
    from src.documents.content_models import BuildContext

    graph = {
        "services": [{"name": "OpenAI", "category": "ai_llm"}],
        "controls": [{"control_id": "LLM01"}],
        "overall_risk": "limited",
        "active_risks": ["PII_IN_LLM_CONTEXT", "NO_AI_AUDIT_TRAIL"],
        "usecase_risks": [{
            "type": "hr_recruitment_screening", "risk_level": "high",
            "article": "Art. 6 Abs. 2", "annex_iii_nr": "4",
            "title_de": "HR-Recruiting / Bewerbungsauswahl",
            "title_en": "HR recruiting / applicant screening",
            "deployer_action": "Menschliche Aufsicht sicherstellen",
            "deployer_action_en": "Ensure human oversight",
        }],
    }
    config = {
        "doc_language": "en",
        "ai_usecase_type": "hr_recruitment_screening",
        "ai_usecase_confidence": 0.91,
    }
    ctx = BuildContext(run_id="fullblok", generation_date="2026-04-23",
                       project_name="rand-industries")
    model = ScanReportBuilder().build(
        graph, {}, config, [], ctx,
        risk_signals=[{"signal_type": "ai_usage", "confidence": 0.9},
                      {"signal_type": "personal_data", "confidence": 0.8}],
        repo_extraction_summary={
            "extractions_count": 2, "extractions_successful": 1,
            "fields_merged": 3, "fields_skipped": 1,
            "source_files": ["privacy.html"], "merged_fields": ["company_name"],
        },
        generated_doc_types=["AVV", "TOM", "DSFA"],
        provenance={"n": 5, "x": 3, "differenz": 2,
                    "processors": ["OpenAI"], "unclassified": ["Worker", "Nginx"],
                    "other_services": ["Foo"], "x_drittland": 1,
                    "third_country": ["OpenAI"]},
    )
    env = _make_jinja("en")
    text = env.get_template("scan_report.md.j2").render(model=dataclasses.asdict(model))
    # every optional block fired
    for probe in ("What was detected?", "AI API usage detected",
                  "HR recruiting / applicant screening", "Ensure human oversight",
                  "Legal documents found in the repository",
                  "Register the HR AI system in the EU database"):
        assert probe in text, f"block probe missing: {probe}"
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if any(u in line for u in "äöüÄÖÜß"):
            hits.append((i, "umlaut", line.strip()[:90]))
            continue
        for w in _GERMAN_STOPWORDS:
            if re.search(rf"\b{re.escape(w)}\b", line):
                hits.append((i, w, line.strip()[:90]))
                break
    assert not hits, "Scan-Report (all blocks): German in EN render:\n" + "\n".join(
        f"  line {n} [{why}]: {frag}" for n, why, frag in hits[:12]
    )


@pytest.mark.parametrize("doc", [
    "AVV", "TOM", "VVT", "SCC", "KI-Policy", "KI-System", "DSFA",
    "AI-Act-Manifest", "Scan-Report",
])
def test_en_docs_contain_no_german(rendered_docs_en, doc):
    """Row 11: the EN render path never shows German (language-pure cut, N1).
    Mutation-proven: a German literal injected into an en/ template turns this red."""
    import re
    text = _strip_accepted(rendered_docs_en[doc])
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if any(u in line for u in "äöüÄÖÜß"):
            hits.append((i, "umlaut", line.strip()[:90]))
            continue
        for w in _GERMAN_STOPWORDS:
            if re.search(rf"\b{re.escape(w)}\b", line):
                hits.append((i, w, line.strip()[:90]))
                break
    assert not hits, f"{doc}: German in EN render:\n" + "\n".join(
        f"  line {n} [{why}]: {frag}" for n, why, frag in hits[:12]
    )


# ---------------------------------------------------------------------------
# Gap-path fixture (2026-07-28) — the THIRD fixture blind spot of this week:
# the default config is fully populated, so NO fallback branch ever fired in
# this linter (that is how the German "(Adresse eintragen)" placeholders
# survived in four builders). GAPS_CONFIG carries only project_name — every
# field with a fallback branch is empty, and the branches run permanently.
# ---------------------------------------------------------------------------

_ALL_RENDERERS = {
    "AVV": _render_avv, "TOM": _render_tom, "VVT": _render_vvt,
    "SCC": _render_scc, "KI-Policy": _render_ki_policy,
    "KI-System": _render_ki_system, "DSFA": _render_dsfa,
    "AI-Act-Manifest": _render_ai_act_manifest, "Scan-Report": _render_scan_report,
}


@pytest.fixture(scope="module")
def rendered_docs_en_gaps() -> dict[str, str]:
    env = _make_jinja("en")
    return {name: fn(env, "en", GAPS_CONFIG) for name, fn in _ALL_RENDERERS.items()}


@pytest.mark.parametrize("doc", sorted(_ALL_RENDERERS))
def test_en_gap_paths_contain_no_german(rendered_docs_en_gaps, doc):
    """EMPTY required fields, EN render: every fallback branch fires and none
    may show German. This is the ratchet the A5-A8 finding lacked."""
    import re
    text = _strip_accepted(rendered_docs_en_gaps[doc])
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if any(u in line for u in "äöüÄÖÜß"):
            hits.append((i, "umlaut", line.strip()[:90]))
            continue
        for w in _GERMAN_STOPWORDS:
            if re.search(rf"\b{re.escape(w)}\b", line):
                hits.append((i, w, line.strip()[:90]))
                break
    assert not hits, f"{doc} (gaps fixture): German in EN render:\n" + "\n".join(
        f"  line {n} [{why}]: {frag}" for n, why, frag in hits[:12]
    )


def test_gap_fixture_fires_the_fallbacks():
    """Sanity: the gaps fixture actually exercises the branches — the EN
    company-block fallbacks and the live warn-header must be present."""
    env = _make_jinja("en")
    tom = _render_tom(env, "en", GAPS_CONFIG)
    assert "(add address)" in tom, "address fallback did not fire"
    assert "(add e-mail)" in tom, "contact_email fallback did not fire"
    avv = _render_avv(env, "en", GAPS_CONFIG)
    assert "(add address)" in avv
    # The warn-header is injected in production via the [[LEX_STATUS]] sentinel
    # (_prepend_warn_header) — the harness renders templates raw, so assert the
    # live-hint -> description_en chain on the partial directly.
    cfg = _load_config("en", GAPS_CONFIG)
    hints = [h for h in _linter_gap_hints(cfg, GAPS_CONFIG) if h.severity == "REQUIRED"]
    assert hints, "empty config must fire REQUIRED hints"
    header = env.get_template("_warn_header.md.j2").render(gaps=hints, lang="en")
    assert "Company name" in header and "still missing" in header


def test_all_docs_render_with_empty_config_both_langs():
    """Smoke: all 9 doc types render in BOTH languages from the empty config."""
    for lang in ("de", "en"):
        env = _make_jinja(lang)
        for name, fn in _ALL_RENDERERS.items():
            out = fn(env, lang, GAPS_CONFIG)
            assert isinstance(out, str) and len(out) > 100, f"{name}/{lang} empty"
