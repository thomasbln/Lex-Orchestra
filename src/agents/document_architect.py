"""
Document Architect — Node 4
Generates compliance document drafts locally from graph + reasoning results.
All output stays in legal/drafts/ — never leaves local infrastructure (ADR-001).
"""

import logging
import re
from collections import defaultdict
from datetime import date
from enum import StrEnum
from pathlib import Path

import psycopg2
import psycopg2.extras
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from src.graph.asset_translator import _resolve_db_url
from src.graph.graph_client import is_ai_service, resolve_control_title
from src.documents.disclaimer import apply_hedging, get_confidence_block, get_disclaimer
from src.scanner.gap_analyzer import analyze_gaps, load_retention_policies, top_n_actions

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parents[2] / "src" / "templates"

# ── ADR-121 Ebene-0 "Warum-Box" — per-doc-type trigger (NOT uniform) ─────────
# Service-driven docs show the N/X/Differenz provenance; the third-country doc
# (SCC) shows the gdpr_adequate=false subset; use-case/AI docs show a legal
# trigger sentence, NOT a service N/X box (wording memo Pro-Doc-Tabelle).
_EBENE0_SERVICE = {"AVV", "VVT", "TOM"}
_EBENE0_DRITTLAND = {"SCC"}
_EBENE0_USECASE = {
    "DSFA": "Dieser Entwurf entsteht, weil ein Auslöser für eine Datenschutz-Folgenabschätzung erkannt wurde (Art. 35 DSGVO).",
    "KI_Policy": "Dieser Entwurf entsteht, weil KI-Nutzung erkannt wurde und der EU AI Act (Art. 4) KI-Kompetenz verlangt.",
    "AI_Act_Manifest": "Dieser Entwurf entsteht, weil ein erkanntes KI-System einer Risikoklasse nach der EU-KI-Verordnung (VO 2024/1689) zuzuordnen ist.",
    "KI_System_Dokumentation": "Dieser Entwurf entsteht, weil ein KI-Dienst erkannt wurde, für den der EU AI Act (Art. 11) technische Dokumentation verlangt.",
}
# B-2/L6 (EN package): lex-authored EN twins — the DE sentences were injected
# into the EN render path verbatim.
_EBENE0_USECASE_EN = {
    "DSFA": "This draft exists because a trigger for a data protection impact assessment was detected (Art. 35 GDPR).",
    "KI_Policy": "This draft exists because AI usage was detected and the EU AI Act (Art. 4) requires AI literacy.",
    "AI_Act_Manifest": "This draft exists because a detected AI system must be assigned to a risk class under the EU AI Regulation (Reg. 2024/1689).",
    "KI_System_Dokumentation": "This draft exists because an AI service was detected for which the EU AI Act (Art. 11) requires technical documentation.",
}
def _fmt_ebene0_names(names: list[str]) -> str:
    """Named-variant list (ADR-121 Open Decision resolved → named).

    Every detected service is named verbatim; returns '' for an empty list. No
    '+K weitere' tail — a count collapse would hide exactly the services the
    Ebene-0 box exists to surface.
    """
    return ", ".join(names) if names else ""


def _render_graph_client(graph_result: dict) -> tuple[dict, object | None]:
    """Return a render-local copy of graph_result carrying a GraphClient.

    ADR-106 PR C5 injects a live GraphClient so the AVV/VVT/DSFA/TOM builders can
    collect BfDI footer citations. It must never be written into the caller's dict:
    in the scan pipeline that dict IS state["graph_result"], and a Bolt driver in
    the LangGraph state breaks the end-of-run checkpoint serialization
    (unpicklable BoltPool.open.<locals>.opener).

    Second return value is the client THIS function owns — the caller must close it.
    None when the caller supplied its own client (it owns that one) or when Neo4j is
    unreachable (best-effort: absent client → empty footer, no breakage).
    """
    local = dict(graph_result)
    if local.get("_graph_client") is not None:
        return local, None
    try:
        from src.graph.graph_client import GraphClient
        client = GraphClient()
    except Exception:
        return local, None
    local["_graph_client"] = client
    return local, client


# Fields from project_config that may contain PII (used in log — field names only)
PII_FIELDS = [
    "company_name", "legal_form", "address", "zip_code", "city",
    "contact_email", "website_url", "responsible_name", "responsible_title",
    "dpo_name", "dpo_email", "register_court", "register_number",
]


def _dedupe_legal_form(company_name: str, legal_form: str) -> str:
    """Return empty string when company_name already ends with legal_form token.

    Prevents 'Rand Industries Inc. (Inc.)' when legal_form suffix is embedded.
    """
    if not legal_form:
        return ""
    if company_name.strip().lower().rstrip(".").endswith(legal_form.strip().lower().rstrip(".")):
        return ""
    return legal_form


class FieldSource(StrEnum):
    """ADR-075 provenance labels for document fields.

    Canonical mapping for generator context and ADR-076 marker rendering
    (✓ for CODE/PII/SVC/UC, ? for Q, ⊘ for STD with delegation).
    """
    CODE = "CODE"   # Repo scan signal (imports, configs)
    PII  = "PII"    # Presidio hit
    SVC  = "SVC"    # Service node + graph data
    UC   = "UC"     # UseCase classification (Phi-4-mini / Gemma4)
    Q    = "Q"      # Questionnaire / setup answer
    STD  = "STD"    # Standard clause, no input needed


def _field_with_source(
    value: str | int | float | bool | None,
    source: FieldSource,
    *,
    evidence: str | None = None,
    confidence: float | None = None,
) -> dict:
    """Wrap a template value with provenance meta (ADR-075 fundament).

    ADR-076 marker renderer consumes these dicts. A missing value keeps
    ``value=None`` — the template decides the fallback copy.
    """
    return {
        "value":      value,
        "source":     source.value,
        "evidence":   evidence,
        "confidence": confidence,
    }


_MISSING_FIELD = {
    "value": None,
    "source": "MISSING",
    "evidence": None,
    "confidence": None,
}


def _merge_sources(
    code: dict | None,
    setup: dict | None,
    field_name: str,
) -> tuple[dict, list[dict]]:
    """ADR-076 reconciliation of code vs. setup signals.

    Returns (winner_field, warnings). Warnings do NOT go into the generated
    document — they are surfaced via scan_findings and the dashboard banner
    so divergences are fixed at the source instead of being papered over.

    Rules (ADR-076 § Reconciliation):
      - only code        → code, no warning
      - only setup       → setup, no warning
      - both agree       → code (confirmed), no warning
      - both divergent   → setup wins, warning with both values
      - neither present  → MISSING sentinel, no warning
    """
    warnings: list[dict] = []

    if code and setup:
        if code["value"] == setup["value"]:
            return code, []
        warnings.append({
            "field":       field_name,
            "code_value":  code["value"],
            "setup_value": setup["value"],
            "severity":    "warning",
            "source_stage": "three_layer_reconcile",
            "message":     (
                f"Scanner reports {code['value']!r} for {field_name}, "
                f"setup says {setup['value']!r}. Resolve at source."
            ),
        })
        return setup, warnings

    if code:
        return code, []
    if setup:
        return setup, []
    return dict(_MISSING_FIELD), []


def _default_purpose(category: str) -> str:
    defaults = {
        "database":        "Datenspeicherung und -verwaltung",
        "nosql_db":        "NoSQL-Datenspeicherung und -verwaltung",
        "cache_db":        "In-Memory-Caching und Session-Management",
        "baas":            "Backend-as-a-Service: Datenspeicherung, Authentifizierung, APIs",
        "ai_llm":          "KI-gestützte Textgenerierung und -verarbeitung",
        "ai_platform":     "KI-Plattformdienste und Modellinferenz",
        "payment":         "Zahlungsabwicklung und Transaktionsverarbeitung",
        "email":           "Transaktionaler E-Mail-Versand",
        "email_marketing": "E-Mail-Marketing und Newsletter-Versand",
        "auth":            "Authentifizierung, Autorisierung und Identity Management",
        "analytics":       "Nutzungsanalyse, Tracking und Monitoring",
        "hosting":         "Server-Hosting und Infrastrukturbereitstellung",
        "cloud":           "Cloud-Infrastruktur und verwaltete Dienste",
        "storage":         "Datei- und Objektspeicherung",
        "vector_db":       "Vektordatenbank für Embedding-Speicherung (RAG)",
        "monitoring":      "Fehler-Monitoring, Log-Aggregation und Alerting",
        "cdn_security":    "Content Delivery und Web-Application-Security",
        "vcs":             "Versionskontrolle und Quellcode-Management",
        "ci_cd":           "Continuous Integration und Deployment-Automatisierung",
        "crm":             "Customer Relationship Management und Kundendatenverwaltung",
        "crm_support":     "Support-Ticketing und Kundenservice",
        "sms":             "SMS-Versand und Mobile Messaging",
        "observability":   "LLM-Observability und KI-Audit-Trail (EU AI Act Art. 12)",
        "media_storage":   "Medien- und Asset-Speicherung",
        "search_db":       "Volltextsuche und Such-Index",
        "security":        "Security-Monitoring, SIEM und Threat Intelligence",
    }
    return defaults.get(category, "Leistungserbringung gemäß Hauptvertrag")


# ADR-063: TOM section mapping for OWASP Controls.
# ISO Controls have no tom_section property — fallback via range-based derivation
# in _get_tom_section() below. Keys: OWASP Control ID, Value: TOM section per Art. 32 GDPR
OWASP_TOM_SECTION: dict[str, str] = {
    "API1":  "1.3 Zugriffskontrolle",
    "API2":  "1.2 Zugangskontrolle",
    "API3":  "1.3 Zugriffskontrolle",
    "API4":  "3.1 Verfügbarkeitskontrolle",
    "API5":  "1.3 Zugriffskontrolle",
    "API6":  "1.3 Zugriffskontrolle",
    "API7":  "2.1 Weitergabekontrolle",
    "API8":  "4.1 Datenschutz-Maßnahmen",
    "API9":  "4.1 Datenschutz-Maßnahmen",
    "API10": "4.1 Datenschutz-Maßnahmen",
    "LLM01": "4.1 Datenschutz-Maßnahmen",
    "LLM02": "1.5 Pseudonymisierung",
    "LLM03": "4.4 Auftragskontrolle",
    "LLM04": "4.3 Privacy by Design",
    "LLM05": "4.1 Datenschutz-Maßnahmen",
    "LLM06": "1.3 Zugriffskontrolle",
    "LLM07": "1.5 Pseudonymisierung",
    "LLM08": "4.3 Privacy by Design",
    "LLM09": "4.1 Datenschutz-Maßnahmen",
    "LLM10": "3.1 Verfügbarkeitskontrolle",
    "A01": "1.3 Zugriffskontrolle",
    "A02": "1.2 Zugangskontrolle",
    "A03": "4.1 Datenschutz-Maßnahmen",
    "A05": "4.3 Privacy by Design",
    "A06": "4.1 Datenschutz-Maßnahmen",
    "A07": "1.2 Zugangskontrolle",
    "A09": "2.2 Eingangskontrolle",
}

TOM_SECTION_ORDER = [
    "1.1 Zutrittskontrolle",
    "1.2 Zugangskontrolle",
    "1.3 Zugriffskontrolle",
    "1.4 Trennungskontrolle",
    "1.5 Pseudonymisierung",
    "2.1 Weitergabekontrolle",
    "2.2 Eingangskontrolle",
    "3.1 Verfügbarkeitskontrolle",
    "4.1 Datenschutz-Maßnahmen",
    "4.2 Incident-Response-Management",
    "4.3 Privacy by Design",
    "4.4 Auftragskontrolle",
]


def _get_tom_section(control: dict) -> str:
    """Resolve TOM section for a control — OWASP via dict, ISO via range, BSI via prefix."""
    control_id = control.get("control_id", "")
    framework = control.get("framework", "")

    if framework in ("OWASP_API_Top10", "OWASP_LLM_Top10", "OWASP_Top10"):
        return OWASP_TOM_SECTION.get(control_id, "4.1 Datenschutz-Maßnahmen")

    if framework == "ISO_27001":
        try:
            major_str, _, minor_str = control_id.partition(".")
            major = int(major_str)
            minor = int(minor_str) if minor_str else 0
            # ISO 27001:2022 Annex A — 5=Organisational, 6=People, 7=Physical, 8=Technological
            if major == 5:
                return "4.4 Auftragskontrolle"
            if major in (6, 7):
                return "4.1 Datenschutz-Maßnahmen"
            if major == 8:
                # 8.1-8.5 Endpoint/Access, 8.6-8.14 Capacity/Backup/Logging,
                # 8.15-8.23 Network/Transfer, 8.24-8.34 Crypto/DevSecOps/Data
                if minor <= 5:
                    return "1.3 Zugriffskontrolle"
                if minor <= 14:
                    return "3.1 Verfügbarkeitskontrolle"
                if minor <= 23:
                    return "2.1 Weitergabekontrolle"
                return "4.1 Datenschutz-Maßnahmen"
        except (ValueError, TypeError):
            pass

    bsi_map = {
        "ORP": "4.1 Datenschutz-Maßnahmen",
        "CON": "4.3 Privacy by Design",
        "OPS": "4.4 Auftragskontrolle",
        "APP": "1.3 Zugriffskontrolle",
        "SYS": "1.2 Zugangskontrolle",
        "NET": "2.1 Weitergabekontrolle",
        "INF": "3.1 Verfügbarkeitskontrolle",
        "DER": "4.2 Incident-Response-Management",
    }
    prefix = control_id.split(".")[0]
    return bsi_map.get(prefix, "4.1 Datenschutz-Maßnahmen")


FRAMEWORK_LABELS = {
    "BSI_Grundschutz": "BSI IT-Grundschutz",
    "ISO_27001":        "ISO 27001",
    "OWASP_LLM_Top10":  "OWASP LLM Top 10",
    "OWASP_API_Top10":  "OWASP API Top 10",
    "OWASP_Top10":      "OWASP Web Top 10",
    "NIST_CSF_2":       "NIST CSF 2.0",
}


class DocumentOrchestrator:

    DRAFTS_DIR = Path(__file__).parents[2] / "legal" / "drafts"

    def __init__(self):
        self._current_signals: list[dict] = []
        self._current_service_categories: list[str] = []
        self._gap_registry: dict = {}
        # ADR-111 provenance logbook: builders populate this per doc_type in
        # PR 2; _try_generate writes one <doctype>_<id>.logbook.json per doc.
        # Empty in PR 1 — the pipe is wired, the section semantics arrive in PR 2.
        self._logbook_entries: dict[str, list] = {}
        # ADR-121 Ebene-0 box: per-render-lifecycle provenance cache, keyed by
        # run_id. NOT persisted (C1 NO-CACHE forbids freezing into the artifact,
        # not reusing within one render run). A new scan = new run_id = recompute.
        self._provenance_cache: dict[str, dict | None] = {}
        self._jinja = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        # has_signal() checks scan signals AND service_categories from graph (ADR-098 PR2)
        def _has_signal(name: str, min_confidence: float = 0.5) -> bool:
            signal_match = any(
                s.get("signal_type") == name and s.get("confidence", 0) >= min_confidence
                for s in self._current_signals
            )
            return signal_match or name in self._current_service_categories
        self._jinja.globals["has_signal"] = _has_signal
        self._jinja.globals["inline_gap_marker"] = self.inline_gap_marker

        # PR-B Mini-Gate: ISO 'YYYY-MM-DD' → 'DD.MM.YYYY' for German doc rendering.
        # Defensive: empty/None and non-ISO strings pass through unchanged (no crash,
        # no data loss). Applied only in the value branch of {% if %}; gap markers untouched.
        def _de_date(value):
            if not value:
                return value
            try:
                return date.fromisoformat(str(value)).strftime("%d.%m.%Y")
            except (ValueError, TypeError):
                return value
        self._jinja.filters["de_date"] = _de_date

        # B-2/L12 (EN package): EN twin — ISO 'YYYY-MM-DD' → '2 August 2025'.
        # Same defensive semantics as de_date (pass-through on empty/non-ISO).
        def _en_date(value):
            if not value:
                return value
            try:
                d = date.fromisoformat(str(value))
                return f"{d.day} {d.strftime('%B %Y')}"
            except (ValueError, TypeError):
                return value
        self._jinja.filters["en_date"] = _en_date

        # B-2/L2 (EN package): German legal-citation form → EN convention.
        # "DSGVO Art. 28 Abs. 3 lit. a" → "Art. 28(3)(a) GDPR". Mechanical,
        # lex-authored citation RENDERING — the norm reference itself is
        # unchanged. Unknown patterns pass through (linter catches leftovers).
        def _en_cite(value):
            if not value:
                return value
            parts = [p.strip() for p in str(value).split(";")]
            out = []
            for p in parts:
                gdpr = p.startswith("DSGVO ")
                if gdpr:
                    p = p[len("DSGVO "):]
                p = re.sub(r"Abs\. (\d+)", r"(\1)", p)
                p = re.sub(r"lit\. ([a-z])", r"(\1)", p)
                p = re.sub(r"Satz (\d+)", r"sentence \1", p)
                p = re.sub(r"Nr\. (\d+)", r"no. \1", p)
                p = re.sub(r"Anhang III", "Annex III", p)
                p = p.replace("(TOM-Nachweispflicht)", "(TOM accountability)")
                p = re.sub(r"Art\. (\d+) \(", r"Art. \1(", p)
                p = p.replace(") (", ")(")
                if gdpr:
                    p += " GDPR"
                out.append(p)
            return "; ".join(out)
        self._jinja.filters["en_cite"] = _en_cite

    # ADR-129 B-1 (language-pure owner texts): render-only markers for per-row states
    # that gap_analyzer can NOT know (it is project/scan-scoped, not row-scoped).
    # Resolved BEFORE the registry lookup; never stored in owner_measures.
    _RENDER_ONLY_MARKERS = {
        "translation_pending": {
            "de": "☐ Übersetzung ausstehend (englische Fassung vorhanden)",
            "en": "☐ translation pending (German version exists)",
        },
    }

    def inline_gap_marker(self, gap_id: str) -> str:
        """Return a ✏️ inline marker string for a missing required/recommended field.

        Used in templates as: {{ inline_gap_marker('gap_id') }}
        Reads from self._gap_registry populated by generate_all() via analyze_gaps();
        render-only per-row markers (_RENDER_ONLY_MARKERS) resolve first.
        """
        en = getattr(self, "_current_lang", "de") == "en"
        special = self._RENDER_ONLY_MARKERS.get(gap_id)
        if special:
            return special["en"] if en else special["de"]
        gap = self._gap_registry.get(gap_id)
        if not gap:
            return "☐ to be added" if en else "☐ noch zu ergänzen"
        if en:
            return (
                f"☐ to be added ({gap.article}) — "
                f"[add in the project settings]({gap.fix_url})"
            )
        return (
            f"☐ noch zu ergänzen ({gap.article}) — "
            f"[in den Projekteinstellungen ergänzen]({gap.fix_url})"
        )

    def _prepend_warn_header(self, doc_type: str, body: str, gap_hints: list, lang: str = "de") -> str:
        """Fill the [[LEX_STATUS]] sentinel with the 📥 status box (when REQUIRED gaps
        target this doc_type) or remove it. Defensive: any leftover [[LEX_...]] marker is
        stripped so a sentinel can never leak into the delivered document."""
        required = [
            g for g in gap_hints
            if getattr(g, "severity", "RECOMMENDED") == "REQUIRED"
            and doc_type in (g.doc_affected or [])
        ]
        if required:
            header = self._jinja.get_template("_warn_header.md.j2").render(gaps=required, lang=lang)
            body = body.replace("[[LEX_STATUS]]", header.strip() + "\n\n", 1)
        # Remove the placeholder if it was not replaced (no required gaps) + strip any
        # stray sentinel as a safety net (never leak "[[LEX_...]]" into the output).
        body = body.replace("[[LEX_STATUS]]", "")
        body = re.sub(r"\[\[LEX_[A-Z_]*\]\]", "", body)
        return body

    def _get_template(self, name: str, lang: str = "de"):
        """Language fallback chain: {lang}/{name} → de/{name} → {name} (root).

        ADR-079 2a: the 8 doc templates live in de/ and en/; DE is the
        authoritative base language, so any non-de language falls back to the
        German template before the root. Root remains the final fallback for
        shared partials (_marker, _bfdi_footer, …) and scan_report, which are
        not split and are looked up by bare name.
        """
        candidates = [f"{lang}/{name}"]
        if lang != "de":
            candidates.append(f"de/{name}")
        candidates.append(name)
        for candidate in candidates:
            try:
                return self._jinja.get_template(candidate)
            except TemplateNotFound:
                continue
        raise FileNotFoundError(f"No template found for {name} (lang={lang})")

    def _render_with_disclaimer(
        self,
        template_name: str,
        lang: str,
        doc_type: str,
        confidence: float,
        **ctx,
    ) -> str:
        """
        Render a Jinja2 template and wrap it with disclaimer header + confidence footer.

        Header: disclaimer from Supabase (lang + doc_type specific, with NULL fallback).
        Body:   rendered template with hedging substitutions applied.
        Footer: confidence score block.
        """
        # ADR-085: set signal context so has_signal() Jinja global can inspect it
        self._current_signals = ctx.get("risk_signals") or []
        self._current_lang = lang   # ADR-129 PR 14: inline_gap_marker localisation
        # ADR-076: expose lang inside the template so the marker macro can
        # localise its labels. Full i18n template split is a future ADR.
        body = self._get_template(template_name, lang).render(**ctx, lang=lang)
        body = apply_hedging(body)
        disclaimer = get_disclaimer(doc_type, lang)
        footer = get_confidence_block(confidence, lang)
        # ADR-121 3-layer head: DISCLAIMER → Ebene-0 Warum-Box → ℹ️ definition.
        ebene0_box = self._render_ebene0_box(doc_type, ctx, lang)  # '' or 'box\n\n'
        intro_box = self._render_intro_box(doc_type, lang)   # '' or 'box\n\n'
        # A4 (Doc-Intro): order = TITLE → DISCLAIMER → 🔎 EBENE-0 → ℹ️ INTRO → 📥 STATUS → BODY → FOOTER.
        # Templates carry a [[LEX_HEAD_END]] sentinel right after their title region; the
        # [[LEX_STATUS]] placeholder is filled (or removed) by _prepend_warn_header.
        if "[[LEX_HEAD_END]]" in body:
            title_region, rest = body.split("[[LEX_HEAD_END]]", 1)
            return (
                f"{title_region.strip()}\n\n"
                f"{disclaimer}\n\n"
                f"{ebene0_box}"
                f"{intro_box}"
                f"[[LEX_STATUS]]"
                f"{rest.lstrip()}\n\n"
                f"{footer}\n"
            )
        # Defensive fallback: no sentinel → boxes on top (pre-A4 behaviour), never splice mid-body.
        return (
            f"[[LEX_STATUS]]"
            f"{disclaimer}\n\n"
            f"{ebene0_box}"
            f"{intro_box}"
            f"{body}\n\n"
            f"{footer}\n"
        )

    def _provenance(self, run_id: str) -> dict | None:
        """Ebene-0 provenance for ``run_id``, computed once per render lifecycle.

        ADR-121 C1 NO-CACHE: the result is reused *within* one render run (the 8
        docs share the same run_id), never frozen into the document or DB. A new
        scan carries a new run_id → cache miss → recompute. Returns None when the
        graph/Supabase is unreachable (box silently omitted).
        """
        if not run_id:
            return None
        if run_id not in self._provenance_cache:
            try:
                from src.graph.graph_client import GraphClient
                with GraphClient() as gc:
                    self._provenance_cache[run_id] = gc.resolve_processing_provenance(run_id)
            except Exception as exc:  # graph optional — never block document output
                logger.warning("Ebene-0 provenance skipped for %s: %s", run_id, exc)
                self._provenance_cache[run_id] = None
        return self._provenance_cache[run_id]

    def _render_ebene0_box(self, doc_type: str, ctx: dict, lang: str = "de") -> str:
        """Project-specific 'Warum dieses Dokument?' box — per-doc-type trigger.

        Service docs (AVV/VVT/TOM) show N/X/Differenz; SCC shows X_drittland;
        use-case/AI docs (DSFA/KI_Policy/AI_Act_Manifest/KI_System) show a legal
        trigger sentence with NO service N/X. Empty for any other doc type or
        when provenance is unavailable.
        """
        if doc_type in _EBENE0_USECASE:
            rendered = self._jinja.get_template("_ebene0_box.md.j2").render(
                variant="usecase",
                usecase_text=(_EBENE0_USECASE_EN if lang == "en" else _EBENE0_USECASE)[doc_type],
                lang=lang,
            )
            return rendered.strip() + "\n\n" if rendered.strip() else ""

        if doc_type not in _EBENE0_SERVICE and doc_type not in _EBENE0_DRITTLAND:
            return ""

        prov = self._provenance(ctx.get("run_id", ""))
        if not prov or prov.get("n", 0) == 0:
            return ""

        variant = "drittland" if doc_type in _EBENE0_DRITTLAND else "service"
        rendered = self._jinja.get_template("_ebene0_box.md.j2").render(
            variant=variant, lang=lang,
            n=prov["n"], x=prov["x"], differenz=prov["differenz"],
            processors=_fmt_ebene0_names(prov["processors"]),
            tooling=_fmt_ebene0_names(prov["tooling"]),
            other=_fmt_ebene0_names(prov["other_services"]),
            other_count=len(prov["other_services"]),
            x_drittland=prov["x_drittland"],
            third_country=_fmt_ebene0_names(prov["third_country"]),
        )
        return rendered.strip() + "\n\n" if rendered.strip() else ""

    def _render_intro_box(self, doc_type: str, lang: str = "de") -> str:
        """Graph-sourced 'Was ist das?' intro box (DocumentType.description_{lang}).

        Returns '' when no description is seeded or the graph is unreachable —
        the box is silently omitted, rendering never breaks.
        """
        try:
            from src.graph.graph_client import GraphClient
            with GraphClient() as gc:
                intro_text = gc.get_doctype_description(doc_type, lang)
        except Exception as exc:  # graph optional — never block document output
            logger.warning("Intro box skipped for %s: %s", doc_type, exc)
            return ""
        if not intro_text:
            return ""
        rendered = self._jinja.get_template("_intro_box.md.j2").render(intro_text=intro_text, lang=lang)
        return rendered.strip() + "\n\n"

    def _compute_confidence(self, ctx: dict) -> float:
        """Derive confidence score from field evidence in ctx (ADR-086).

        Counts fields wrapped by _field_with_source() with source 'code'/'setup'
        vs total tracked fields. Fallback 0.75 when no tracking present.
        """
        fields = ctx.get("fields", {})
        if not fields:
            return 0.75
        evidenced = sum(
            1 for v in fields.values()
            if isinstance(v, dict) and v.get("source") in ("CODE", "Q", "SVC", "UC", "PII")
        )
        total = len(fields)
        raw = evidenced / total if total else 0.75
        return max(0.40, min(0.95, round(raw, 2)))

    def generate_all(
        self,
        graph_result: dict,
        reasoning_result: dict,
        project_name: str,
        run_id: str,
        risk_signals: list[dict] | None = None,
        extraction_summary: dict | None = None,
    ) -> list[dict]:
        """
        Generate all required compliance documents and record them in PostgreSQL.
        Returns list of dicts: [{id, doc_type, file_path, version, status}]

        The GraphClient the builders need lives for exactly this call: it is injected
        into a render-local copy of graph_result and closed on every exit path. The
        caller's dict is never touched — see _render_graph_client().
        """
        graph_result, owned_client = _render_graph_client(graph_result)
        try:
            return self._generate_all(
                graph_result=graph_result,
                reasoning_result=reasoning_result,
                project_name=project_name,
                run_id=run_id,
                risk_signals=risk_signals,
                extraction_summary=extraction_summary,
            )
        finally:
            if owned_client is not None:
                try:
                    owned_client.close()
                except Exception as exc:
                    logger.warning("Closing render GraphClient failed: %s", exc)

    def _generate_all(
        self,
        graph_result: dict,
        reasoning_result: dict,
        project_name: str,
        run_id: str,
        risk_signals: list[dict] | None = None,
        extraction_summary: dict | None = None,
    ) -> list[dict]:
        """Render body — graph_result is the render-local copy from generate_all()."""
        self._current_signals = risk_signals or []
        self._current_service_categories = graph_result.get("service_categories", [])
        self.DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
        config = self._load_project_config(project_name)
        # ADR-129 PR 15: owner-maintained retention rows ride along for AVV/VVT
        try:
            from src.scanner.gap_analyzer import load_retention_policies
            config["_retention_policies"] = load_retention_policies(project_name)
        except Exception:
            config["_retention_policies"] = []

        # Populate _gap_registry BEFORE any _write_* runs so inline_gap_marker()
        # resolves against real gap data during Jinja rendering (ADR-098 PR1 Task 1.7).
        setup = self._load_project_setup(project_name)
        retention_policies = load_retention_policies(project_name)
        gap_hints = analyze_gaps(
            project_name=project_name,
            config=config,
            setup=setup,
            retention_policies=retention_policies,
            services_detected=graph_result.get("services", []),
            extraction_summary=extraction_summary,
        )
        self._gap_registry = {g.id: g for g in gap_hints}
        # ADR-111: reset the per-run logbook collector. The dict is keyed by
        # doc_type (so AVV entries never leak into the VVT logbook), but it must
        # also start empty each run — otherwise a second generate_all() on the
        # same instance would accumulate the previous run's entries (PR 2 fills
        # these; PR 1 only guarantees the per-run/per-doc isolation).
        self._logbook_entries = {}

        generated = []
        doc_types = graph_result.get("doc_types", [])

        def _try_generate(doc_type: str, write_fn, *args):
            try:
                path = write_fn(*args)
                if path is None:
                    return
                # Render a print-ready PDF alongside the Markdown (best-effort —
                # a missing PDF never blocks the draft, see pdf_renderer).
                from src.documents.pdf_renderer import render_md_to_pdf
                pdf = render_md_to_pdf(path)
                generated.append(self._save_doc(
                    run_id, project_name, doc_type, str(path),
                    pdf_path=str(pdf) if pdf else None,
                ))
                # ADR-111: write the additive provenance logbook next to the
                # .md / .pdf. Best-effort — a logbook failure never blocks the
                # draft. Only doc types whose builder participates in the logbook
                # (AVV/VVT/SCC in PR 2) get a file; the five follow-up doc writers
                # have no key here and get no logbook — "not yet covered", not an
                # empty "no provenance" artifact.
                if doc_type in self._logbook_entries:
                    try:
                        from src.documents.logbook import write_logbook
                        write_logbook(
                            run_id, doc_type,
                            self._logbook_entries[doc_type],
                            self.DRAFTS_DIR,
                        )
                    except Exception as lb_exc:
                        logger.error("Failed to write logbook for %s: %s", doc_type, lb_exc)
            except Exception as exc:
                logger.error("Failed to generate %s: %s", doc_type, exc)

        services = graph_result.get("services", [])

        # Minimal KI-doc gating (Pre-DSB sprint): the four AI/KI documents render
        # ONLY when AI services are actually detected. An AI Act manifest, KI policy,
        # KI system doc, or DSFA for an AI-free stack would assert obligations (EU AI
        # Act, Art. 35 DPIA) that do not apply — a DSB spots that immediately.
        ai_services = [s for s in services if is_ai_service(s)]
        ai_services_detected = bool(ai_services)

        # ADR-124 Doc-Polish: resolve BOTH risk classifications once, here — this is the
        # only layer that sees both the project-wide scanner class (ai_usecase_type) and the
        # per-service deployer class (per_service.purpose). The AI-Act manifest and the KI
        # docs both consume these; hoisted above the ai_act call so both branches share them.
        usecase_map: dict = {}
        ai_usecase: dict | None = None
        per_service_cfg: dict = {}
        project_risk_level: str | None = None
        service_risk_diverges = False
        if ai_services_detected:
            usecase_map = self._resolve_usecase_map()
            scanner_type = config.get("ai_usecase_type")
            ai_usecase = usecase_map.get(scanner_type) if scanner_type else None
            per_service_cfg = (config.get("ai_config") or {}).get("per_service") or {}
            project_risk_level = ai_usecase.get("risk_level") if ai_usecase else None
            # Divergence = ANY service whose per-service purpose risk differs from project-wide.
            # Only comparable when both sides exist; effective falls back to ai_usecase when no
            # purpose → identical → no divergence (correct).
            if project_risk_level:
                for s in ai_services:
                    purpose = (per_service_cfg.get(s.get("name")) or {}).get("purpose")
                    eff = (usecase_map.get(purpose) if purpose else None) or ai_usecase
                    svc_risk = eff.get("risk_level") if eff else None
                    if svc_risk and svc_risk != project_risk_level:
                        service_risk_diverges = True
                        break

        needs_avv = (
            "AVV" in doc_types
            or any(s.get("dpa_url") for s in services)
            or any(not s.get("gdpr_adequate") for s in services)
        )
        if needs_avv:
            _try_generate("AVV", self._write_avv, project_name, run_id, graph_result, config)
        if "TOM" in doc_types:
            _try_generate("TOM", self._write_tom, project_name, run_id, graph_result, reasoning_result, config)
        if "AI_Act_Manifest" in doc_types and ai_services_detected:
            _try_generate("AI_Act_Manifest", self._write_ai_act_manifest, project_name, run_id, graph_result, config, service_risk_diverges)

        # SCC — SCCBuilder decides via select_services_for_scc(); returns None if no Drittland transfers
        from src.documents.builders.scc_builder import SCCBuilder as _SCCBuilder
        if _SCCBuilder.select_services_for_scc(services):
            _try_generate("SCC", self._write_scc, project_name, run_id, graph_result, config)

        # VVT — always required (Art. 30 DSGVO)
        _try_generate("VVT", self._write_vvt, project_name, run_id, graph_result, config)

        # KI-specific docs — when AI services detected (see gating note above)
        if ai_services_detected:
            # ADR-124 Gate B: usecase_map / ai_usecase / per_service_cfg resolved once above
            # (hoisted for the divergence computation the ai_act manifest also needs).
            for service in ai_services:
                # ADR-124 precedence: deployer per-service `purpose` beats the scanner's
                # project-level `ai_usecase_type` when set; scanner is the fallback.
                purpose = (per_service_cfg.get(service.get("name")) or {}).get("purpose")
                effective_usecase = (usecase_map.get(purpose) if purpose else None) or ai_usecase
                # Doc-Polish: pass the project-wide risk as the counterpart so ki_system can
                # show a divergence hint when its per-service risk differs.
                _try_generate(
                    "KI_System_Dokumentation",
                    self._write_ki_system_doc,
                    project_name, run_id, service, effective_usecase, config, graph_result,
                    project_risk_level,
                )
            _try_generate("KI_Policy", self._write_ki_policy, project_name, run_id, ai_services, config)

            # DSFA — conditional on risk indicators
            active_risk_ids = graph_result.get("active_risks", [])
            needs_dsfa = (
                (ai_usecase and ai_usecase.get("risk_level") == "High")
                or "RAG_OVER_PII" in active_risk_ids
                or "PII_IN_LLM_CONTEXT" in active_risk_ids
            )
            if needs_dsfa:
                _try_generate(
                    "DSFA",
                    self._write_dsfa,
                    project_name, run_id, graph_result, ai_services, ai_usecase, config,
                )

        return generated

    def _load_project_config(self, project_name: str) -> dict:
        """Load project config from Supabase. Returns empty dict if not found."""
        db_url = _resolve_db_url()
        if not db_url:
            return {}
        try:
            with psycopg2.connect(db_url) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        "SELECT * FROM project_config WHERE project_name = %s",
                        (project_name,),
                    )
                    row = cur.fetchone()
                    return dict(row) if row else {}
        except Exception as e:
            logger.warning("Could not load project_config: %s", e)
            return {}

    def _load_project_setup(self, project_name: str) -> dict | None:
        """ADR-076: Load current project_setups row joined with latest revision meta.

        Returns None if no setup exists — templates fall back to today's
        no-marker rendering so legacy projects keep their existing output.
        """
        db_url = _resolve_db_url()
        if not db_url:
            return None
        try:
            with psycopg2.connect(db_url) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("""
                        SELECT ps.*,
                               psr.created_at AS revision_created_at,
                               psr.created_by AS revision_created_by
                          FROM project_setups ps
                     LEFT JOIN project_setup_revisions psr
                            ON psr.id = ps.current_revision_id
                         WHERE ps.project_name = %s
                    """, (project_name,))
                    row = cur.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            logger.warning("Could not load project_setup: %s", e)
            return None

    def _load_hosting_provider(self, provider_name: str | None) -> dict | None:
        """ADR-076: Look up curated HostingProvider compliance metadata.

        Returns None if name is missing or not in the curated list — caller
        falls back to a plain Layer-2 ? marker instead of the ⊘ delegation.
        """
        if not provider_name:
            return None
        try:
            from src.graph.graph_client import GraphClient
            with GraphClient() as gc:
                rows = gc.run_query(
                    """
                    MATCH (h:HostingProvider {name: $name})
                    RETURN h.name AS name, h.soc2 AS soc2, h.iso27001 AS iso27001,
                           h.default_regions AS default_regions,
                           h.requires_scc_outside_eu AS requires_scc_outside_eu
                    """,
                    {"name": provider_name},
                )
                return dict(rows[0]) if rows else None
        except Exception as e:
            logger.warning("Could not load HostingProvider %s: %s", provider_name, e)
            return None

    def _save_doc(self, run_id: str, project_name: str, doc_type: str, file_path: str,
                  pdf_path: str | None = None) -> dict:
        """Insert a generated_docs row with version management. Returns the row as dict."""
        fallback = {"id": None, "doc_type": doc_type, "file_path": file_path,
                    "pdf_path": pdf_path, "version": 1, "status": "draft"}
        db_url = _resolve_db_url()
        if not db_url:
            logger.warning("No DB URL — skipping generated_docs write for %s", doc_type)
            return fallback

        try:
            with psycopg2.connect(db_url) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # ADR-080: resolve project_id for denormalised FK. Ensure
                    # the project_config row exists so the FK holds — scans
                    # sometimes beat the dashboard save.
                    cur.execute(
                        "INSERT INTO project_config (project_name) VALUES (%s) "
                        "ON CONFLICT (project_name) DO UPDATE SET project_name = EXCLUDED.project_name "
                        "RETURNING id",
                        (project_name,),
                    )
                    project_id = cur.fetchone()["id"]

                    cur.execute(
                        "SELECT COALESCE(MAX(version), 0) AS max_v FROM generated_docs "
                        "WHERE project_id = %s AND doc_type = %s",
                        (project_id, doc_type),
                    )
                    max_version = cur.fetchone()["max_v"]
                    version = max_version + 1

                    if max_version > 0:
                        cur.execute(
                            "UPDATE generated_docs SET status = 'outdated' "
                            "WHERE project_id = %s AND doc_type = %s AND status != 'outdated'",
                            (project_id, doc_type),
                        )

                    cur.execute(
                        """
                        INSERT INTO generated_docs
                            (run_id, project_id, project_name, doc_type, file_path, pdf_path, version, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 'draft')
                        RETURNING id, doc_type, file_path, pdf_path, version, status
                        """,
                        (run_id, project_id, project_name, doc_type, file_path, pdf_path, version),
                    )
                    row = dict(cur.fetchone())
                    row["id"] = str(row["id"])
                    conn.commit()
                    logger.debug("Saved generated_doc: %s v%d (id=%s)", doc_type, version, row["id"])

                    # ADR-045: log document generation for trust chain
                    try:
                        from src.utils.scan_logger import log_document_generation
                        import os
                        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                        log_document_generation(
                            run_id=run_id,
                            doc_type=doc_type,
                            version=version,
                            pii_fields_used=PII_FIELDS,
                            # ADR-127 Phase 3: host-agnostic label — connection is env-driven
                            # (NEO4J_URI). Authoritative graph is NucBox-local (ADR-053);
                            # Aura is non-authoritative since 2026-05-27. The old "neo4j_aura"
                            # was a false provenance claim.
                            graph_source="neo4j",
                            # ADR-127 Phase 3: document generation is deterministic
                            # (Builder/ContentModel → Jinja2 from graph) — no LLM call.
                            # The old hardcoded cloud model was a false trust-chain claim
                            # after the reasoning node was removed.
                            llm_source="deterministic",
                            stays_local=True,
                            file_size_bytes=file_size,
                        )
                    except Exception:
                        pass

                    return row
        except Exception as e:
            logger.error("Failed to save generated_doc %s: %s", doc_type, e)
            return fallback

    def _resolve_usecase_map(self) -> dict:
        """All UseCase nodes keyed by type — one graph fetch, reused per service (ADR-124).

        Covers Limited/High/Minimal (parity with the prior _resolve_ai_usecase fetch);
        Unacceptable is omitted intentionally — a deployer never selects a prohibited use.
        """
        from src.graph.graph_client import GraphClient
        try:
            with GraphClient() as gc:
                all_usecases = (
                    gc.get_usecases_for_risk_level("Limited")
                    + gc.get_usecases_for_risk_level("High")
                    + gc.get_usecases_for_risk_level("Minimal")
                )
                return {u["type"]: u for u in all_usecases}
        except Exception as e:
            logger.warning("Could not resolve usecase map: %s", e)
            return {}

    def _resolve_ai_usecase(self, config: dict) -> dict | None:
        """Load the scanner-classified project-level UseCase (config.ai_usecase_type)."""
        ai_usecase_type = config.get("ai_usecase_type")
        if not ai_usecase_type:
            return None
        return self._resolve_usecase_map().get(ai_usecase_type)

    def _common_config_context(self, project_name: str, run_id: str, config: dict) -> dict:
        """Build the common header context dict shared across templates.

        ADR-076: also surfaces project_setup metadata and pre-computed
        marker fields (customer_info / hosting_delegation / physical_access)
        so templates can render ✓ / ? / ⊘ blocks via _marker.md.j2.
        Projects without a setup row keep today's no-marker output.
        """
        setup = self._load_project_setup(project_name)
        setup_d: dict = setup or {}

        # ADR-076: setup (Layer 2) wins over config for overlapping fields.
        # `or` is used on the config side too because nullable TEXT columns
        # return Python None via psycopg2, which bypasses dict.get defaults
        # and would render literal "None" in templates.
        def _prefer(setup_key: str, config_key: str | None = None, default: str = "") -> str:
            config_key = config_key or setup_key
            val = setup_d.get(setup_key) or config.get(config_key) or default
            return val

        ctx = {
            "project_name": project_name,
            "run_id": run_id,
            "generation_date": str(date.today()),
            "company_name":      config.get("company_name") or project_name,
            "legal_form":        _dedupe_legal_form(
                config.get("company_name") or project_name,
                config.get("legal_form") or "",
            ),
            "address":           config.get("address") or "(Adresse eintragen)",
            "zip_code":          config.get("zip_code") or "",
            "city":              config.get("city") or "",
            "zip_city":          config.get("zip_city") or "",
            "contact_email":     config.get("contact_email") or "(E-Mail eintragen)",
            "website_url":       config.get("website_url") or "",
            "responsible_name":  config.get("responsible_name") or "",
            "responsible_title": config.get("responsible_title") or "",
            "dpo_name":          _prefer("dpo_name"),
            "dpo_email":         _prefer("dpo_email"),
            "register_court":    config.get("register_court") or "",
            "register_number":   config.get("register_number") or "",
        }

        # ADR-076: marker context. When no setup row exists, leave everything
        # empty/None so templates fall back to today's rendering without markers.
        project = {
            "on_prem":          bool(setup["on_prem"]) if setup else False,
            "hosting_provider": (setup or {}).get("hosting_provider"),
            "hosting_region":   (setup or {}).get("hosting_region"),
        }

        setup_revision_short = ""
        setup_revision_date  = ""
        setup_author         = ""
        fields: dict = {}

        if setup:
            rev_id = setup.get("current_revision_id")
            if rev_id:
                setup_revision_short = str(rev_id)[:8]
            rev_date = setup.get("revision_created_at")
            if rev_date:
                setup_revision_date = rev_date.date().isoformat()
            setup_author = setup.get("revision_created_by") or ""

            # Layer 2 customer header — rendered once at top of document when
            # setup exists. Source is Q, no single evidence (user-entered form).
            fields["customer_info"] = _field_with_source(
                setup.get("hosting_provider") or project_name,
                FieldSource.Q,
            )

            # Conditional physical-controls block (TOM § 1.1 Zutrittskontrolle).
            # Cloud-native → ⊘ delegation to hoster. On-prem → ? questionnaire.
            if project["on_prem"]:
                fields["physical_access"] = _field_with_source(
                    "on_premise_questionnaire_pending",
                    FieldSource.Q,
                )
            else:
                hp = self._load_hosting_provider(project["hosting_provider"])
                if hp:
                    fields["hosting_delegation"] = {
                        "value": {
                            "provider": hp["name"],
                            "region":   project["hosting_region"] or
                                        (hp.get("default_regions") or [""])[0],
                            "soc2":     bool(hp.get("soc2")),
                            "iso27001": bool(hp.get("iso27001")),
                        },
                        "source":     "STD_DELEGATED",
                        "evidence":   None,
                        "confidence": None,
                    }
                # else: hosting_provider unknown → no marker, template stays silent.

        ctx.update({
            "project":              project,
            "project_setup":        setup,
            "setup_revision_short": setup_revision_short,
            "setup_revision_date":  setup_revision_date,
            "setup_author":         setup_author,
            "fields":               fields,
        })
        return ctx

    def _write_avv(self, project_name: str, run_id: str, graph_result: dict, config: dict) -> Path:
        import dataclasses as _dc
        from src.documents.builders.avv_builder import AVVBuilder
        from src.documents.content_models import BuildContext

        build_ctx = BuildContext(
            run_id=run_id,
            generation_date=str(date.today()),
            project_name=project_name,
        )
        gap_hints = list(self._gap_registry.values())
        builder = AVVBuilder()
        model = builder.build(graph_result, {}, config, gap_hints, build_ctx)
        # ADR-111 PR2: record per-source-node provenance for this doc.
        self._logbook_entries["AVV"] = builder.logbook_entries(model, graph_result)

        services_meta = graph_result.get("services", [])
        instructing_persons = config.get("instructing_persons") or []
        # ADR-129 PR 15 (audit K24/F5): every service appears in § 7 — a missing
        # period renders a gap marker in the template, never a silent drop.
        deletion_periods = [
            {"service": s["name"], "period": s.get("deletion_period")}
            for s in services_meta
        ]
        transfer_mechanism = next(
            (d.get("transfer_mechanism") for d in graph_result.get("docs_required", [])
             if d.get("transfer_mechanism")),
            None,
        )

        ctx = self._common_config_context(project_name, run_id, config)
        ctx.update({
            # Legacy ctx keys — still read by non-migrated template sections
            "services": services_meta,
            "deletion_periods": deletion_periods,
            "transfer_mechanism": transfer_mechanism,
            "instructing_persons": instructing_persons,
            # ADR-099 PR 1a: ContentModel for migrated template sections
            # data_categories, data_subjects, special_categories → model.*
            "model": _dc.asdict(model),
        })

        lang = config.get("doc_language", "de") or "de"
        content = self._render_with_disclaimer("avv.md.j2", lang, "AVV", self._compute_confidence(ctx), **ctx)
        content = self._prepend_warn_header("AVV", content, gap_hints, lang)
        path = self.DRAFTS_DIR / f"avv_{run_id[:8]}.md"
        path.write_text(content, encoding="utf-8")
        return path

    def _build_framework_groups(
        self,
        controls: list[dict],
        bsi_defaults: dict[str, dict],
        config: dict,
        reasoning_tom: dict | None = None,
    ) -> list[dict]:
        """Build framework groups for TOM template: [{label, controls: [{measure, bsi_default, concrete}]}]

        tom_implementations priority (highest wins):
          1. project_config (manual override)
          2. reasoning_result (LLM-generated)
          3. control.default_tom_measure (graph — deterministic)
          4. empty string → template renders ⚠️
        """
        lang = config.get("doc_language", "de") or "de"
        grouped: dict[str, list[dict]] = defaultdict(list)
        seen: set[tuple[str, str]] = set()
        for c in controls:
            fw = c.get("framework", "Sonstige")
            cid = c.get("control_id", "")
            key = (fw, cid)
            if key in seen:
                continue
            seen.add(key)
            grouped[fw].append(c)

        tom_impl = {
            **(reasoning_tom or {}),
            **(config.get("tom_implementations") or {}),
        }
        result = []

        for framework, items in grouped.items():
            label = FRAMEWORK_LABELS.get(framework, framework)
            ctrl_list = []
            for c in items:
                cid = c.get("control_id", "")
                title = resolve_control_title(c, lang)
                measure = f"{cid} — {title}"

                bsi_reqs = bsi_defaults.get(cid, {}).get("basis_requirements", [])
                if bsi_reqs:
                    bsi_text = "<br>".join(f"• {r}" for r in bsi_reqs[:3])
                    if len(bsi_reqs) > 3:
                        bsi_text += f"<br>_+{len(bsi_reqs)-3} weitere_"
                else:
                    bsi_text = ""  # Template renders DE fallback label when empty

                concrete = (
                    tom_impl.get(cid)                       # 1+2: manual / LLM override
                    or c.get("default_tom_measure") or ""   # 3: graph default
                )

                ctrl_list.append({
                    "measure": measure,
                    "bsi_default": bsi_text,
                    "concrete": concrete,
                })
            result.append({"label": label, "controls": ctrl_list})

        return result

    # Keep for backward compatibility — used by tests that check the string directly
    def _build_controls_table(
        self,
        controls: list[dict],
        bsi_defaults: dict[str, dict],
        config: dict,
    ) -> str:
        groups = self._build_framework_groups(controls, bsi_defaults, config)
        lines = [
            "| Maßnahme | Standard-Umsetzung (BSI) | Konkrete Umsetzung |",
            "|---|---|---|",
        ]
        for group in groups:
            lines.append(f"| **{group['label']}** | | |")
            for c in group["controls"]:
                lines.append(f"| {c['measure']} | {c['bsi_default']} | {c['concrete']} |")
        return "\n".join(lines) if len(lines) > 2 else "- (keine Controls erkannt)"

    def _write_tom(
        self,
        project_name: str,
        run_id: str,
        graph_result: dict,
        reasoning_result: dict,
        config: dict,
    ) -> Path:
        import dataclasses as _dc
        from src.documents.builders.tom_builder import TOMBuilder
        from src.documents.content_models import BuildContext

        # Build common ctx first so hosting_delegation is available for the builder
        ctx = self._common_config_context(project_name, run_id, config)
        hosting_delegation = ctx.get("fields", {}).get("hosting_delegation")

        build_ctx = BuildContext(
            run_id=run_id,
            generation_date=str(date.today()),
            project_name=project_name,
        )
        gap_hints = list(self._gap_registry.values())
        model = TOMBuilder().build(
            graph_result, reasoning_result, config, gap_hints, build_ctx,
            hosting_delegation=hosting_delegation,
        )

        # Legacy ctx keys — still read by non-migrated template sections.
        # ADR-127 P4.3/P4.6: the section-overview table (template) is a SEPARATE
        # path from the builder's measures table, so it needs the same
        # deleted_controls skip — otherwise an owner-deactivated control still
        # shows up in the "section → control IDs" overview. Best-effort loader
        # (same shared source as the builder overlay); DB down → empty → no skip.
        controls = graph_result.get("controls", [])
        _lang = config.get("doc_language", "de") or "de"
        from src.documents.builders.common.owner_measures import load_owner_measures
        _, _deleted = load_owner_measures(project_name, run_id, _lang)
        from collections import defaultdict as _dd
        controls_by_section: dict[str, list[dict]] = _dd(list)
        seen_sc: set[tuple[str, str]] = set()
        for ctrl in controls:
            cid = ctrl.get("control_id", "")
            if cid in _deleted:
                continue
            section = _get_tom_section(ctrl)
            if (section, cid) in seen_sc:
                continue
            seen_sc.add((section, cid))
            controls_by_section[section].append(ctrl)
        controls_by_section_ordered = [
            (section, controls_by_section[section])
            for section in TOM_SECTION_ORDER
            if section in controls_by_section
        ]

        ctx.update({
            "framework_groups": [],   # migrated — template reads model.curated_controls
            "priority_actions": (reasoning_result or {}).get("priority_actions", []),
            "active_risks": graph_result.get("active_risks", []),
            "controls_by_section": dict(controls_by_section),
            "controls_by_section_ordered": controls_by_section_ordered,
            "tom_section_order": TOM_SECTION_ORDER,
            # ADR-099 PR 1b: ContentModel for migrated template sections
            "model": _dc.asdict(model),
        })

        lang = config.get("doc_language", "de") or "de"
        content = self._render_with_disclaimer("tom.md.j2", lang, "TOM", self._compute_confidence(ctx), **ctx)
        content = self._prepend_warn_header("TOM", content, gap_hints, lang)
        path = self.DRAFTS_DIR / f"tom_{run_id[:8]}.md"
        path.write_text(content, encoding="utf-8")
        return path

    def _write_vvt(
        self,
        project_name: str,
        run_id: str,
        graph_result: dict,
        config: dict,
    ) -> Path:
        import dataclasses as _dc
        from src.documents.builders.vvt_builder import VVTBuilder
        from src.documents.content_models import BuildContext
        from datetime import date as _date

        build_ctx = BuildContext(run_id=run_id, generation_date=str(_date.today()), project_name=project_name)
        gap_hints = list(self._gap_registry.values())
        builder = VVTBuilder()
        model = builder.build(graph_result, {}, config, gap_hints, build_ctx)
        # ADR-111 PR2: record per-source-node provenance for this doc.
        self._logbook_entries["VVT"] = builder.logbook_entries(model, graph_result)

        services_meta = graph_result.get("services", [])
        non_eu_services = [s for s in services_meta if not s.get("gdpr_adequate")]

        ctx = self._common_config_context(project_name, run_id, config)
        ctx.update({
            "services": services_meta,
            "processing_activities": _dc.asdict(model)["activities"],
            "non_eu_services": non_eu_services,
            "model": _dc.asdict(model),
        })

        lang = config.get("doc_language", "de") or "de"
        content = self._render_with_disclaimer("vvt.md.j2", lang, "VVT", self._compute_confidence(ctx), **ctx)
        content = self._prepend_warn_header("VVT", content, list(self._gap_registry.values()), lang)
        path = self.DRAFTS_DIR / f"vvt_{run_id[:8]}.md"
        path.write_text(content, encoding="utf-8")
        return path

    def _write_ki_system_doc(
        self,
        project_name: str,
        run_id: str,
        service: dict,
        ai_usecase: dict | None,
        config: dict,
        graph_result: dict | None = None,
        project_risk_level: str | None = None,
    ) -> Path:
        import dataclasses as _dc
        from src.documents.builders.ki_system_builder import KISystemBuilder
        from src.documents.content_models import BuildContext

        build_ctx = BuildContext(
            run_id=run_id,
            generation_date=str(date.today()),
            project_name=project_name,
        )
        gap_hints = list(self._gap_registry.values())
        # DELETED: service_with_risk = {**service, "risk_level": ...}
        # Builder derives risk_level from graph_result.risk_levels directly.
        model = KISystemBuilder().build(
            graph_result or {}, {}, config, gap_hints, build_ctx,
            service=service,
            ai_usecase=ai_usecase,
            project_risk_level=project_risk_level,
        )

        ctx = self._common_config_context(project_name, run_id, config)
        ctx["model"] = _dc.asdict(model)
        # ctx["service"] and ctx["ai_usecase"] removed — template reads model.service.*

        lang = config.get("doc_language", "de") or "de"
        content = self._render_with_disclaimer("ki_system.md.j2", lang, "KI_System_Dokumentation", self._compute_confidence(ctx), **ctx)
        content = self._prepend_warn_header("KI_System_Dokumentation", content, gap_hints, lang)

        slug = re.sub(r"[^a-z0-9]+", "_", service.get("name", "unknown").lower()).strip("_")
        path = self.DRAFTS_DIR / f"ki_system_{slug}_{run_id[:8]}.md"
        path.write_text(content, encoding="utf-8")
        return path

    def _write_ki_policy(
        self,
        project_name: str,
        run_id: str,
        ai_services: list[dict],
        config: dict,
    ) -> Path:
        import dataclasses as _dc
        from src.documents.builders.ki_policy_builder import KIPolicyBuilder
        from src.documents.content_models import BuildContext

        build_ctx = BuildContext(
            run_id=run_id,
            generation_date=str(date.today()),
            project_name=project_name,
        )
        gap_hints = list(self._gap_registry.values())
        # ai_services is pre-filtered by generate_all(); wrap for builder convention
        graph_result_for_builder = {"services": ai_services}
        model = KIPolicyBuilder().build(graph_result_for_builder, {}, config, gap_hints, build_ctx)

        ctx = self._common_config_context(project_name, run_id, config)
        ctx["model"] = _dc.asdict(model)
        # ctx["ai_services"] removed — template reads model.ai_services

        lang = config.get("doc_language", "de") or "de"
        content = self._render_with_disclaimer("ki_policy.md.j2", lang, "KI_Policy", self._compute_confidence(ctx), **ctx)
        content = self._prepend_warn_header("KI_Policy", content, gap_hints, lang)
        path = self.DRAFTS_DIR / f"ki_policy_{run_id[:8]}.md"
        path.write_text(content, encoding="utf-8")
        return path

    def _write_dsfa(
        self,
        project_name: str,
        run_id: str,
        graph_result: dict,
        ai_services: list[dict],
        ai_usecase: dict | None,
        config: dict,
    ) -> Path:
        import dataclasses as _dc
        from src.documents.builders.dsfa_builder import DSFABuilder
        from src.documents.content_models import BuildContext

        build_ctx = BuildContext(
            run_id=run_id,
            generation_date=str(date.today()),
            project_name=project_name,
        )
        gap_hints = list(self._gap_registry.values())
        model = DSFABuilder().build(graph_result, {}, config, gap_hints, build_ctx,
                                    ai_usecase=ai_usecase)

        ctx = self._common_config_context(project_name, run_id, config)
        ctx["model"] = _dc.asdict(model)
        # risk_signals kept — ADR-085 has_signal() Jinja-global reads self._current_signals
        ctx["risk_signals"] = self._current_signals
        # Removed: ai_services, ai_usecase, active_risk_ids, dsfa_zweck,
        #          dsfa_rechtsgrundlage, dsfa_pii_services, services

        lang = config.get("doc_language", "de") or "de"
        content = self._render_with_disclaimer("dsfa.md.j2", lang, "DSFA", self._compute_confidence(ctx), **ctx)
        content = self._prepend_warn_header("DSFA", content, gap_hints, lang)
        path = self.DRAFTS_DIR / f"dsfa_{run_id[:8]}.md"
        path.write_text(content, encoding="utf-8")
        return path

    def _write_scc(self, project_name: str, run_id: str, graph_result: dict, config: dict) -> Path | None:
        import dataclasses as _dc
        from src.documents.builders.scc_builder import SCCBuilder
        from src.documents.content_models import BuildContext
        from datetime import date as _date

        build_ctx = BuildContext(run_id=run_id, generation_date=str(_date.today()), project_name=project_name)
        gap_hints = list(self._gap_registry.values())
        builder = SCCBuilder()
        model = builder.build(graph_result, {}, config, gap_hints, build_ctx)
        if model is None:
            return None
        # ADR-111 PR2: record per-source-node provenance for this doc.
        self._logbook_entries["SCC"] = builder.logbook_entries(model, graph_result)

        model_dict = _dc.asdict(model)
        services = graph_result.get("services", [])
        drittland = SCCBuilder.select_services_for_scc(services)
        dpa_links = [
            {"name": s["name"], "url": s["dpa_url"]}
            for s in drittland
            if s.get("dpa_url")
        ]

        ctx = self._common_config_context(project_name, run_id, config)
        ctx.update({
            "services": drittland,
            "dpa_links": dpa_links,
            "model": model_dict,
        })

        lang = config.get("doc_language", "de") or "de"
        content = self._render_with_disclaimer("scc.md.j2", lang, "SCC", self._compute_confidence(ctx), **ctx)
        content = self._prepend_warn_header("SCC", content, list(self._gap_registry.values()), lang)
        path = self.DRAFTS_DIR / f"scc_{run_id[:8]}.md"
        path.write_text(content, encoding="utf-8")
        return path

    def _write_ai_act_manifest(
        self,
        project_name: str,
        run_id: str,
        graph_result: dict,
        config: dict,
        service_risk_diverges: bool = False,
    ) -> Path:
        import dataclasses as _dc
        from src.documents.builders.ai_act_builder import AIActBuilder
        from src.documents.content_models import BuildContext

        build_ctx = BuildContext(
            run_id=run_id,
            generation_date=str(date.today()),
            project_name=project_name,
        )
        gap_hints = list(self._gap_registry.values())
        model = AIActBuilder().build(graph_result, {}, config, gap_hints, build_ctx,
                                     service_risk_diverges=service_risk_diverges)

        ctx = self._common_config_context(project_name, run_id, config)
        ctx["model"] = _dc.asdict(model)
        # Removed: risk_levels, deployer_usecase, ai_usecase_type, indicated_usecases,
        #          all_usecases, has_audit_trail_gap, art4_effective_date

        lang = config.get("doc_language", "de") or "de"
        content = self._render_with_disclaimer("ai_act_manifest.md.j2", lang, "AI_Act_Manifest", self._compute_confidence(ctx), **ctx)
        content = self._prepend_warn_header("AI_Act_Manifest", content, gap_hints, lang)
        path = self.DRAFTS_DIR / f"ai_act_manifest_{run_id[:8]}.md"
        path.write_text(content, encoding="utf-8")
        return path

    def _build_risk_section(self, active_risks: list[str]) -> str:
        """Risk content lives in tom.md.j2 — kept for API compatibility."""
        return ""

    def _write_scan_report(
        self,
        state: dict,
        graph_result: dict,
        reasoning_result: dict,
        generated_doc_types: list[str],
    ) -> Path:
        """Generate scan summary. Delegates to ScanReportBuilder + Jinja."""
        import dataclasses as _dc
        from src.documents.builders.scan_report_builder import ScanReportBuilder
        from src.documents.content_models import BuildContext

        project_name = state.get("project_name", "—")
        run_id = state.get("run_id", "")

        build_ctx = BuildContext(
            run_id=run_id,
            generation_date=str(date.today()),
            project_name=project_name,
        )

        # Load config ONCE — reused for both gap-fallback path and builder call
        config = self._load_project_config(project_name)
        # ADR-129 PR 15: owner-maintained retention rows ride along for AVV/VVT
        try:
            from src.scanner.gap_analyzer import load_retention_policies
            config["_retention_policies"] = load_retention_policies(project_name)
        except Exception:
            config["_retention_policies"] = []

        # Prefer cached gap_hints from generate_all() to avoid duplicate DB calls
        if self._gap_registry:
            gap_hints = list(self._gap_registry.values())
        else:
            setup = self._load_project_setup(project_name)
            retention_policies = load_retention_policies(project_name)
            gap_hints = analyze_gaps(
                project_name=project_name,
                config=config,
                setup=setup,
                retention_policies=retention_policies,
                services_detected=graph_result.get("services", []),
                extraction_summary=state.get("repo_extraction_summary"),
            )

        model = ScanReportBuilder().build(
            graph_result, reasoning_result, config, gap_hints, build_ctx,
            risk_signals=state.get("risk_signals"),
            repo_extraction_summary=state.get("repo_extraction_summary"),
            generated_doc_types=generated_doc_types,
            provenance=self._provenance(run_id),  # ADR-121 Ebene-0 (NO-CACHE, C1)
        )

        ctx = {"model": _dc.asdict(model)}
        content = self._jinja.get_template("scan_report.md.j2").render(**ctx)
        path = self.DRAFTS_DIR / f"scan_report_{run_id[:8]}.md"
        path.write_text(content, encoding="utf-8")
        return path
