from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass

from src.documents.builders.base import DocumentBuilder
from src.documents.builders.common.cell_safe import cell_text
from src.documents.content_models import BuildContext, CompanyBlock
from src.graph.graph_client import resolve_control_title

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level constants (copied from document_architect.py — will be the
# canonical location after DA is fully refactored)
# ---------------------------------------------------------------------------

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

FRAMEWORK_LABELS: dict[str, str] = {
    "BSI_Grundschutz": "BSI IT-Grundschutz",
    "ISO_27001":        "ISO 27001",
    "OWASP_LLM_Top10":  "OWASP LLM Top 10",
    "OWASP_API_Top10":  "OWASP API Top 10",
    "OWASP_Top10":      "OWASP Web Top 10",
    "NIST_CSF_2":       "NIST CSF 2.0",
}


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
            if major == 5:
                return "4.4 Auftragskontrolle"
            if major in (6, 7):
                return "4.1 Datenschutz-Maßnahmen"
            if major == 8:
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


# ---------------------------------------------------------------------------
# Content Model
# ---------------------------------------------------------------------------

@dataclass
class TOMSectionRow:
    section: str
    control_ids: list[str]


@dataclass
class TOMControlRow:
    framework_label: str
    measure: str         # "CID — Title"
    bsi_default: str
    concrete: str        # non-empty, OR empty with translation_pending=True
    tom_section: str = "4.1 Datenschutz-Maßnahmen"  # ADR-106 PR A2: sort key
    applicable_services: list = None                 # ADR-106 PR A3: which services map here
    # ADR-129 B-1 (language-pure owner texts): custom measure exists in the other
    # lang only → the row renders with a translation-pending marker, never the
    # other-lang text and never a silent drop.
    translation_pending: bool = False

    def __post_init__(self):
        if self.applicable_services is None:
            self.applicable_services = []


@dataclass
class TOMSDMDefaultRow:
    """Per-section SDM-Measure default (ADR-106 PR D7) for TOM-§ that have no
    scan-derived controls. Fills the '—' cells in TOM-Abschnitte table.
    """
    tom_section: str
    measures: list[str]   # list of Measure.name_de


@dataclass
class TOMContentModel:
    """Every field here will be rendered by tom.md.j2. No extras, no guesses."""
    company: CompanyBlock
    generation_date: str
    run_id: str
    warn_header_gaps: list
    hosting_delegation: dict | None      # from _common_config_context fields
    sections_overview: list[TOMSectionRow]
    curated_controls: list[TOMControlRow]    # concrete != "" guaranteed
    priority_actions: list[str]
    pii_in_llm_risk: bool
    rag_over_pii_risk: bool
    pii_in_logs_risk: bool
    sdm_defaults_by_section: dict[str, list[str]]   # ADR-106 PR D7


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

class TOMBuilder(DocumentBuilder):

    def build(
        self,
        graph_result: dict,
        reasoning_result: dict,
        config: dict,
        gap_hints: list,
        ctx: BuildContext,
        hosting_delegation: dict | None = None,
    ) -> TOMContentModel:
        controls = graph_result.get("controls", [])
        active_risks = graph_result.get("active_risks", [])
        actions = (reasoning_result or {}).get("priority_actions", [])
        reasoning_tom = (reasoning_result or {}).get("tom_implementations") if reasoning_result else None
        lang = config.get("doc_language", "de") or "de"  # ADR-126 Phase 5: thread to graph lookups

        # ADR-127 P4.3: owner overlay (best-effort) — edits win over config/default,
        # deleted controls drop out entirely. Falls back to graph defaults on DB error.
        from src.documents.builders.common.owner_measures import load_owner_measures, load_custom_measures
        owner_edits, deleted_controls = load_owner_measures(ctx.project_name, ctx.run_id, lang)
        # ADR-127 PR5e: owner-authored custom measures (TOM-only) — appended as synthetic
        # controls so they render; deleted_controls-skip + owner overlay apply by control_id.
        # New list (do not mutate graph_result["controls"]).
        controls = list(controls) + load_custom_measures(ctx.project_name, ctx.run_id, lang)

        bsi_defaults = self._load_bsi_defaults(controls, lang)
        framework_groups = self._build_framework_groups(
            controls, bsi_defaults, config, reasoning_tom, owner_edits, deleted_controls
        )
        curated_controls = self._flatten_curated(framework_groups)
        sections_overview = self._build_sections_overview(controls, deleted_controls)

        # ADR-106 PR D7: only attempt SDM-Defaults lookup when graph_result
        # carries an explicit _graph_client (orchestrator-injected, see PR C5).
        # Tests/fixtures get empty defaults — no DB dependency.
        sdm_defaults = (
            self._load_sdm_defaults_for_empty_sections(sections_overview, lang)
            if graph_result.get("_graph_client") else {}
        )

        return TOMContentModel(
            company=self._company_block(config, ctx),
            generation_date=ctx.generation_date,
            run_id=ctx.run_id,
            warn_header_gaps=self._required_gaps_for("TOM", gap_hints),
            hosting_delegation=hosting_delegation,
            sections_overview=sections_overview,
            curated_controls=curated_controls,
            priority_actions=actions,
            pii_in_llm_risk="PII_IN_LLM_CONTEXT" in active_risks,
            rag_over_pii_risk="RAG_OVER_PII" in active_risks,
            pii_in_logs_risk="PII_IN_LOGS" in active_risks,
            sdm_defaults_by_section=sdm_defaults,
        )

    def _load_sdm_defaults_for_empty_sections(
        self,
        sections_overview: list[TOMSectionRow],
        lang: str = "de",
    ) -> dict[str, list[str]]:
        """ADR-106 PR D7: query SDM-Measure-Layer for default measures per TOM-§
        that have NO scan-derived controls. Returns {section: [measure_name, ...]}.
        Best-effort: returns empty dict if graph unreachable.

        ADR-126 Phase 5: name_{lang} with DE fallback (lang='de' yields the exact
        prior value — coalesce(m.name_de, m.name_de) — so the DE path is unchanged).
        """
        filled_sections = {r.section for r in sections_overview if r.control_ids}
        empty_sections = [s for s in TOM_SECTION_ORDER if s not in filled_sections]
        if not empty_sections:
            return {}
        try:
            from src.graph.graph_client import GraphClient, NEO4J_DB
            with GraphClient() as gc:
                with gc._driver.session(database=NEO4J_DB) as sess:
                    out: dict[str, list[str]] = {}
                    rows = sess.run("""
                        UNWIND $sections AS sec
                        MATCH (m:Measure {tom_section: sec})
                        RETURN sec AS section,
                               collect(coalesce(m['name_' + $lang], m.name_de))[..3] AS names
                    """, sections=empty_sections, lang=lang)
                    for r in rows:
                        if r["names"]:
                            out[r["section"]] = list(r["names"])
                    return out
        except Exception as exc:
            logger.warning("TOMBuilder: SDM-Defaults lookup failed: %s", exc)
            return {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_bsi_defaults(self, controls: list[dict], lang: str = "de") -> dict[str, dict]:
        bsi_ids = [c["control_id"] for c in controls if c.get("framework") == "BSI_Grundschutz"]
        if not bsi_ids:
            return {}
        try:
            from src.graph.graph_client import GraphClient
            with GraphClient() as gc:
                return gc.get_bsi_defaults_for_controls(bsi_ids, lang)
        except Exception as exc:
            logger.warning("TOMBuilder: could not load BSI defaults: %s", exc)
            return {}

    def _build_framework_groups(
        self,
        controls: list[dict],
        bsi_defaults: dict[str, dict],
        config: dict,
        reasoning_tom: dict | None = None,
        owner_edits: dict[str, str] | None = None,
        deleted_controls: set[str] | None = None,
    ) -> list[dict]:
        owner_edits = owner_edits or {}
        deleted_controls = deleted_controls or set()
        # ADR-106 PR A3: collect Services per (framework, control_id) so each
        # control row can list which services in this scan trigger it.
        services_per_key: dict[tuple[str, str], list[str]] = defaultdict(list)
        for c in controls:
            key = (c.get("framework", "Sonstige"), c.get("control_id", ""))
            svc = c.get("service", "")
            if svc and svc not in services_per_key[key] and not svc.startswith("category:"):
                services_per_key[key].append(svc)

        grouped: dict[str, list[dict]] = defaultdict(list)
        seen: set[tuple[str, str]] = set()
        for c in controls:
            fw = c.get("framework", "Sonstige")
            cid = c.get("control_id", "")
            if cid in deleted_controls:   # ADR-127 P4.3: owner-deactivated → real skip (not concrete="")
                continue
            key = (fw, cid)
            if key in seen:
                continue
            seen.add(key)
            grouped[fw].append(c)

        tom_impl = {
            **(reasoning_tom or {}),
            **(config.get("tom_implementations") or {}),
        }
        lang = config.get("doc_language", "de") or "de"
        result = []
        for framework, items in grouped.items():
            label = FRAMEWORK_LABELS.get(framework, framework)
            ctrl_list = []
            for c in items:
                cid = c.get("control_id", "")
                title = resolve_control_title(c, lang)
                # ADR-129 B3: titles are owner-editable (custom measures) — escape at
                # the render layer so a pipe/newline cannot split the table row.
                # PR5e-5: customs render title-only — `custom-<uuid8>` is internal
                # identity, not a norm citation.
                measure = cell_text(title) if cid.startswith("custom-") else f"{cid} — {cell_text(title)}"

                bsi_reqs = bsi_defaults.get(cid, {}).get("basis_requirements", [])
                if bsi_reqs:
                    bsi_text = "<br>".join(f"• {r}" for r in bsi_reqs[:3])
                    if len(bsi_reqs) > 3:
                        # B-2/L13 (EN package): unit word language-pure
                        more = "more" if lang == "en" else "weitere"
                        bsi_text += f"<br>_+{len(bsi_reqs)-3} {more}_"
                else:
                    bsi_text = ""

                # ADR-129 PR 9 (audit K20/F1): EN renders the EN graph default when
                # present, with honest DE fallback — never a silent empty cell.
                graph_default = (
                    (c.get("default_tom_measure_en") if lang == "en" else None)
                    or c.get("default_tom_measure") or ""
                )
                concrete = (
                    owner_edits.get(cid)            # ADR-127 P4.3: owner > config > default
                    # B-2 (EN package, linter find): tom_implementations is the
                    # LEGACY flat owner layer without a language axis (DE-only
                    # by nature; live empty on both projects, ADR-127 phase 0)
                    # — it must never leak into the EN document.
                    or (tom_impl.get(cid) if lang != "en" else None)
                    or graph_default
                )
                ctrl_list.append({
                    "measure": measure,
                    "bsi_default": bsi_text,
                    # ADR-127: \n → <br> so owner-authored multi-line text does not
                    # split the Markdown table row (render-layer only; DB text stays raw).
                    "concrete": cell_text(concrete),
                    # ADR-129 B-1: custom authored in the other lang only — row stays,
                    # cell renders the translation-pending marker (template-side).
                    "translation_pending": bool(c.get("translation_pending")) and not concrete,
                    "label": label,
                    "tom_section": _get_tom_section(c),
                    "applicable_services": services_per_key.get((framework, cid), []),
                })
            result.append({"label": label, "controls": ctrl_list})
        return result

    def _flatten_curated(self, framework_groups: list[dict]) -> list[TOMControlRow]:
        """Flatten groups → flat list, filter concrete == '', sorted by TOM § then control_id.

        ADR-106 PR A2: primary sort by tom_section (1.1 → 4.4) instead of framework order.
        ADR-106 PR A3: row carries applicable_services list.
        """
        rows: list[TOMControlRow] = []
        for group in framework_groups:
            for c in group["controls"]:
                # ADR-129 B-1: a translation-pending custom row survives the
                # empty-concrete filter — dropping it would silently hide an
                # owner measure from one language's document.
                if not c.get("concrete") and not c.get("translation_pending"):
                    continue
                rows.append(TOMControlRow(
                    framework_label=group["label"],
                    measure=c["measure"],
                    bsi_default=c.get("bsi_default") or "",
                    concrete=c["concrete"],
                    tom_section=c.get("tom_section", "4.1 Datenschutz-Maßnahmen"),
                    applicable_services=c.get("applicable_services", []),
                    translation_pending=bool(c.get("translation_pending")),
                ))
        # PR A2: sort by TOM § (using TOM_SECTION_ORDER index), then by measure
        section_idx = {s: i for i, s in enumerate(TOM_SECTION_ORDER)}
        rows.sort(key=lambda r: (section_idx.get(r.tom_section, 99), r.measure))
        return rows

    def _build_sections_overview(
        self, controls: list[dict], deleted_controls: set[str] | None = None
    ) -> list[TOMSectionRow]:
        deleted_controls = deleted_controls or set()
        by_section: dict[str, list[str]] = defaultdict(list)
        seen: set[tuple[str, str]] = set()
        for ctrl in controls:
            cid = ctrl.get("control_id", "")
            if cid.startswith("custom-"):   # ADR-127 PR5e: custom shows in the measures table (with title), not as a raw uuid in the overview
                continue
            if cid in deleted_controls:   # ADR-127 P4.3: owner-deactivated → also out of the section overview
                continue
            section = _get_tom_section(ctrl)
            if (section, cid) in seen:
                continue
            seen.add((section, cid))
            by_section[section].append(cid)

        return [
            TOMSectionRow(section=s, control_ids=sorted(by_section[s]))
            for s in TOM_SECTION_ORDER
            if s in by_section
        ]

    def _company_block(self, config: dict, ctx: BuildContext) -> CompanyBlock:
        zip_city = (
            config.get("zip_city")
            or (f"{config.get('zip_code', '')} {config.get('city', '')}".strip())
            or ""
        )
        return CompanyBlock(
            name=config.get("company_name") or ctx.project_name,
            legal_form=config.get("legal_form") or "",
            address=config.get("address") or "(Adresse eintragen)",
            zip_city=zip_city,
            contact_email=config.get("contact_email") or "(E-Mail eintragen)",
            website_url=config.get("website_url") or "",
            responsible_name=config.get("responsible_name") or None,
            responsible_title=config.get("responsible_title") or None,
            dpo_name=config.get("dpo_name") or None,
            dpo_email=config.get("dpo_email") or None,
        )
