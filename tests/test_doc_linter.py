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
            p = _re.sub(r"Satz (\d+)", r"sentence \1", p)
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


def _base_ctx(lang: str = "de") -> dict:
    """Minimal flat context that satisfies all template header variables."""
    config = json.loads((FIXTURE / "rand_industries_config.json").read_text())
    config["doc_language"] = lang
    return {
        "lang":            lang,   # _warn_header / _bfdi_footer branch on this
        "project_name":    "rand-industries",
        "run_id":          "linter-test-00000000",
        "generation_date": "2026-04-23",
        "company_name":    config.get("company_name", "Rand Industries Inc."),
        "legal_form":      config.get("legal_form", "Inc."),
        "address":         config.get("address", "123 Main St"),
        "zip_code":        config.get("zip_code", ""),
        "city":            config.get("city", ""),
        "zip_city":        config.get("zip_city", ""),
        "contact_email":   config.get("contact_email", "info@example.com"),
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

def _render_avv(env: Environment, lang: str = "de") -> str:
    from src.documents.builders.avv_builder import AVVBuilder
    from src.documents.content_models import BuildContext
    from src.scanner.gap_analyzer import GapHint

    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    config = json.loads((FIXTURE / "rand_industries_config.json").read_text())
    config["doc_language"] = lang
    gaps_raw = json.loads((FIXTURE / "rand_industries_gaps.json").read_text())
    gap_hints = [GapHint(**g) if isinstance(g, dict) else g for g in gaps_raw]
    ctx = BuildContext(run_id="linter000", generation_date="2026-04-23", project_name="rand-industries")
    model = AVVBuilder().build(graph, {}, config, gap_hints, ctx)
    ctx_dict = _base_ctx(lang)
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


def _render_tom(env: Environment, lang: str = "de") -> str:
    from src.documents.builders.tom_builder import TOMBuilder
    from src.documents.content_models import BuildContext
    from src.agents.document_architect import TOM_SECTION_ORDER

    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    config = json.loads((FIXTURE / "rand_industries_config.json").read_text())
    config["doc_language"] = lang
    ctx = BuildContext(run_id="linter000", generation_date="2026-04-23", project_name="rand-industries")
    model = TOMBuilder().build(graph, {}, config, [], ctx)
    ctx_dict = _base_ctx(lang)
    ctx_dict["model"] = dataclasses.asdict(model)
    ctx_dict["priority_actions"] = []
    ctx_dict["active_risks"] = graph.get("active_risks", [])
    ctx_dict["controls_by_section"] = {}
    ctx_dict["tom_section_order"] = TOM_SECTION_ORDER
    return env.get_template("tom.md.j2").render(**ctx_dict)


def _render_vvt(env: Environment, lang: str = "de") -> str:
    from src.documents.builders.vvt_builder import VVTBuilder
    from src.documents.content_models import BuildContext

    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    config = json.loads((FIXTURE / "rand_industries_config.json").read_text())
    config["doc_language"] = lang
    ctx = BuildContext(run_id="linter000", generation_date="2026-04-23", project_name="rand-industries")
    model = VVTBuilder().build(graph, {}, config, [], ctx)
    ctx_dict = _base_ctx(lang)
    ctx_dict["model"] = dataclasses.asdict(model)
    return env.get_template("vvt.md.j2").render(**ctx_dict)


def _render_ki_policy(env: Environment, lang: str = "de") -> str:
    from src.documents.builders.ki_policy_builder import KIPolicyBuilder
    from src.documents.content_models import BuildContext

    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    config = json.loads((FIXTURE / "rand_industries_config.json").read_text())
    config["doc_language"] = lang
    ai_services = [s for s in graph.get("services", []) if s.get("ai_act_relevant") or s.get("category") == "ai_llm"]
    ctx = BuildContext(run_id="linter000", generation_date="2026-04-23", project_name="rand-industries")
    model = KIPolicyBuilder().build({"services": ai_services}, {}, config, [], ctx)
    ctx_dict = _base_ctx(lang)
    ctx_dict["model"] = dataclasses.asdict(model)
    return env.get_template("ki_policy.md.j2").render(**ctx_dict)


def _render_ki_system(env: Environment, lang: str = "de") -> str:
    from src.documents.builders.ki_system_builder import KISystemBuilder
    from src.documents.content_models import BuildContext

    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    config = json.loads((FIXTURE / "rand_industries_config.json").read_text())
    config["doc_language"] = lang
    ai_services = [s for s in graph.get("services", []) if s.get("ai_act_relevant") or s.get("category") == "ai_llm"]
    service = ai_services[0] if ai_services else {"name": "OpenAI", "category": "ai_llm"}
    ai_usecase = {"type": "hr_recruitment_screening", "risk_level": "High",
                  "title_de": "HR-Recruiting", "description_de": "Bewerberauswahl",
                  "article": "6", "annex_iii_nr": 4, "deployer_action": "Konformitätsbewertung"}
    ctx = BuildContext(run_id="linter000", generation_date="2026-04-23", project_name="rand-industries")
    model = KISystemBuilder().build(graph, {}, config, [], ctx, service=service, ai_usecase=ai_usecase)
    ctx_dict = _base_ctx(lang)
    ctx_dict["model"] = dataclasses.asdict(model)
    return env.get_template("ki_system.md.j2").render(**ctx_dict)


def _render_dsfa(env: Environment, lang: str = "de") -> str:
    from src.documents.builders.dsfa_builder import DSFABuilder
    from src.documents.content_models import BuildContext

    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    config = json.loads((FIXTURE / "rand_industries_config.json").read_text())
    config["doc_language"] = lang
    ai_usecase = {"type": "hr_recruitment_screening", "risk_level": "High",
                  "title_de": "HR-Recruiting", "description_de": "Bewerberauswahl",
                  "article": "6", "annex_iii_nr": 4}
    ctx = BuildContext(run_id="linter000", generation_date="2026-04-23", project_name="rand-industries")
    model = DSFABuilder().build(graph, {}, config, [], ctx, ai_usecase=ai_usecase)
    ctx_dict = _base_ctx(lang)
    ctx_dict["model"] = dataclasses.asdict(model)
    return env.get_template("dsfa.md.j2").render(**ctx_dict)


def _render_ai_act_manifest(env: Environment, lang: str = "de") -> str:
    from src.documents.builders.ai_act_builder import AIActBuilder
    from src.documents.content_models import BuildContext

    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    config = json.loads((FIXTURE / "rand_industries_config.json").read_text())
    config["doc_language"] = lang
    ctx = BuildContext(run_id="linter000", generation_date="2026-04-23", project_name="rand-industries")
    model = AIActBuilder().build(graph, {}, config, [], ctx)
    ctx_dict = _base_ctx(lang)
    ctx_dict["model"] = dataclasses.asdict(model)
    return env.get_template("ai_act_manifest.md.j2").render(**ctx_dict)


def _render_scan_report(env: Environment, lang: str = "de") -> str:
    from src.documents.builders.scan_report_builder import ScanReportBuilder
    from src.documents.content_models import BuildContext
    from src.scanner.gap_analyzer import GapHint

    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    config = json.loads((FIXTURE / "rand_industries_config.json").read_text())
    config["doc_language"] = lang
    gaps_raw = json.loads((FIXTURE / "rand_industries_gaps.json").read_text())
    gap_hints = [GapHint(**g) if isinstance(g, dict) else g for g in gaps_raw]
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

def _render_scc(env: Environment, lang: str = "de") -> str:
    from src.documents.builders.scc_builder import SCCBuilder
    from src.documents.content_models import BuildContext

    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    config = json.loads((FIXTURE / "rand_industries_config.json").read_text())
    config["doc_language"] = lang
    ctx = BuildContext(run_id="linter000", generation_date="2026-04-23", project_name="rand-industries")
    model = SCCBuilder().build(graph, {}, config, [], ctx)
    if model is None:
        return ""
    ctx_dict = _base_ctx(lang)
    ctx_dict["model"] = dataclasses.asdict(model)
    return env.get_template("scc.md.j2").render(**ctx_dict)


@pytest.fixture(scope="module")
def rendered_docs_en() -> dict[str, str]:
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
    }


# German signals: umlauts + high-frequency legal/German stopwords. Deliberately
# NOT exhaustive — the umlaut check catches most German; the word list catches
# umlaut-free leaks ("eintragen", "weitere", ...).
_GERMAN_STOPWORDS = [
    "gemäß", "Verantwortlicher", "Auftragsverarbeiter", "Verarbeitung",
    "Rechtsgrundlage", "Maßnahme", "eintragen", "ausstehend", "ausfüllen",
    "Pflicht", "Empfänger", "Betroffene", "Speicherfrist", "Hinweis",
    "Entwurf", "fehlt", "Anschrift", "Unterzeichner", "weitere", "Zweck",
]


def _accepted_remnants() -> list[str]:
    """Exact substrings that MAY be German in an EN document (documented):
    - L14 (accepted): Service.deletion_period values + TOM section taxonomy
    - Class-C content is handled by cutting the BfDI footer block instead
    """
    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    remnants = [s.get("deletion_period") for s in graph.get("services", [])
                if s.get("deletion_period")]
    from src.agents.document_architect import TOM_SECTION_ORDER
    remnants += list(TOM_SECTION_ORDER)
    # section labels also appear without their numeric prefix in table cells
    remnants += [s.split(" ", 1)[1] for s in TOM_SECTION_ORDER if " " in s]
    return remnants


def _strip_accepted(text: str) -> str:
    # Class-C BfDI footer: deliberately German (flip criterion) — cut the block.
    cut = text.find("## BfDI source references")
    if cut != -1:
        text = text[:cut]
    for r in _accepted_remnants():
        text = text.replace(r, "")
    return text


@pytest.mark.parametrize("doc", [
    "AVV", "TOM", "VVT", "SCC", "KI-Policy", "KI-System", "DSFA", "AI-Act-Manifest",
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
