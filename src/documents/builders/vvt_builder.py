from __future__ import annotations

from dataclasses import dataclass

from src.documents.builders.base import DocumentBuilder
from src.documents.builders.common.bfdi_footer import BfDICitation, collect_bfdi_citations
from src.documents.builders.common.payment_mode import (
    integration_mode_note,
    resolve_payment_categories,
)
from src.documents.builders.common.psp_role import psp_role_line
from src.documents.content_models import BuildContext, CompanyBlock, RetentionPolicyRow
from src.documents.logbook import (
    LogbookEntry,
    SourceType,
    Status,
    extract_provenance,
)
from src.documents.legal_basis_map import render_legal_basis, render_data_subjects
from src.documents.purpose_map import pick_lang_text, resolve_processing_purpose
from src.documents.builders.avv_builder import _owner_retention_rows

def _render_list_or_string(value) -> str | None:
    """ADR-106 PR C.1 Cleanup: normalize list[str] | str | None into a
    comma-joined string for VVT table cells. Prevents Python repr leak
    (e.g. "['Anwendungsdaten', 'Datenbankinhalt']") in rendered output.
    """
    if value is None:
        return None
    if isinstance(value, list):
        return ", ".join(str(v).strip() for v in value if v) or None
    if isinstance(value, str):
        return value.strip() or None
    return str(value)


@dataclass
class VVTActivity:
    name: str
    purpose: str
    purpose_inferred: bool  # True when purpose is category-derived, not graph-evidenced
    legal_basis: str | None
    role: str | None          # ADR-115 A1: ACTS_AS role (controller|special_case|…) or None
    role_label: str | None    # German label for non-special roles; None otherwise
    role_source: str | None   # EDPB citation / special-case reasoning; None for non-PSP
    ai_type: str | None
    ai_risk_level: str | None
    data_subjects: str | None
    data_categories: str | None
    data_categories_gap: bool  # ADR-110: True → gap marker at the categories cell
    recipients: str | None
    third_country: str | None
    dpa_url: str | None
    retention: str | None
    systems: str | None


@dataclass
class VVTContentModel:
    """Every field here will be rendered by vvt.md.j2. No extras, no guesses."""
    company: CompanyBlock
    generation_date: str
    run_id: str
    warn_header_gaps: list
    activities: list[VVTActivity]
    non_eu_count: int
    scc_doc_ref: str | None   # None when no Drittland transfers
    owner_retention: list[RetentionPolicyRow]  # ADR-129 PR 15: owner-maintained rows (as-is)
    bfdi_citations: list[BfDICitation]  # ADR-106 PR C5


class VVTBuilder(DocumentBuilder):

    def build(
        self,
        graph_result: dict,
        reasoning_result: dict,
        config: dict,
        gap_hints: list,
        ctx: BuildContext,
    ) -> VVTContentModel:
        services = graph_result.get("services", [])
        lang = config.get("doc_language", "de") or "de"
        activities = [self._to_activity(s, lang) for s in services]
        non_eu = [s for s in services if not s.get("gdpr_adequate")]

        scc_doc_ref = f"scc_{ctx.run_id[:8]}.md" if non_eu else None

        bfdi_citations = collect_bfdi_citations(graph_result.get("_graph_client"), "VVT")

        return VVTContentModel(
            company=self._company_block(config, ctx),
            generation_date=ctx.generation_date,
            run_id=ctx.run_id,
            warn_header_gaps=self._required_gaps_for("VVT", gap_hints),
            activities=activities,
            non_eu_count=len(non_eu),
            scc_doc_ref=scc_doc_ref,
            owner_retention=_owner_retention_rows(config),
            bfdi_citations=bfdi_citations,
        )

    def logbook_entries(
        self, model: VVTContentModel, graph_result: dict
    ) -> list[LogbookEntry]:
        """ADR-111 PR2: one graph_node entry per processing activity (= per
        service), read off the built model so the logbook never drifts from
        the rendered VVT."""
        svc_by_name = {s.get("name"): s for s in graph_result.get("services", [])}
        entries: list[LogbookEntry] = []
        for act in model.activities:
            svc = svc_by_name.get(act.name, {})
            entries.append(LogbookEntry(
                section=f"VVT Verarbeitungstätigkeit: {act.name}",
                source_type=SourceType.GRAPH_NODE,
                source_key={"label": "Service", "name": act.name},
                status=Status.GAP if act.data_categories_gap else Status.SOURCED,
                provenance=extract_provenance(svc),
                note=integration_mode_note(svc),
            ))
        return entries

    def _to_activity(self, s: dict, lang: str = "de") -> VVTActivity:
        purpose, purpose_inferred = resolve_processing_purpose(
            s.get("processing_purpose"), s.get("category"), lang,
            graph_value_en=s.get("processing_purpose_en"),   # B-2/L8
        )
        # ADR-110: a payment integration mode overrides the static categories.
        override, is_gap = resolve_payment_categories(s, lang)
        raw_cats = pick_lang_text(                           # B-2/L8
            s.get("data_categories"), s.get("data_categories_en"), lang
        )
        data_categories = (
            _render_list_or_string(override) if override is not None
            else _render_list_or_string(raw_cats)
        )
        role_line = psp_role_line(s, lang)
        return VVTActivity(
            # B-2/L13 (EN package): fallback language-pure
            name=s.get("name") or ("(fill in)" if lang == "en" else "(ausfüllen)"),
            purpose=purpose,
            purpose_inferred=purpose_inferred,
            legal_basis=render_legal_basis(s.get("legal_basis"), lang),
            role=role_line.role if role_line else None,
            role_label=role_line.role_label if role_line else None,
            role_source=role_line.role_source if role_line else None,
            ai_type=("generative (LLM)" if lang == "en" else "generativ (LLM)") if s.get("category") == "ai_llm" else None,
            ai_risk_level=s.get("risk_level"),
            data_subjects=render_data_subjects(s.get("data_subjects"), lang),
            data_categories=data_categories,
            data_categories_gap=is_gap,
            recipients=s.get("name"),
            third_country=s.get("country") if not s.get("gdpr_adequate") else None,
            dpa_url=s.get("dpa_url"),
            retention=s.get("deletion_period"),
            systems=s.get("name"),
        )

    def _company_block(self, config: dict, ctx: BuildContext) -> CompanyBlock:
        zip_city = (
            config.get("zip_city")
            or (f"{config.get('zip_code', '')} {config.get('city', '')}".strip())
            or ""
        )
        return CompanyBlock(
            name=config.get("company_name") or ctx.project_name,
            legal_form=config.get("legal_form") or "",
            address=config.get("address") or ("(add address)" if (config.get("doc_language") or "de") == "en" else "(Adresse eintragen)"),
            zip_city=zip_city,
            contact_email=config.get("contact_email") or ("(add e-mail)" if (config.get("doc_language") or "de") == "en" else "(E-Mail eintragen)"),
            website_url=config.get("website_url") or "",
            responsible_name=config.get("responsible_name") or None,
            responsible_title=config.get("responsible_title") or None,
            dpo_name=config.get("dpo_name") or None,
            dpo_email=config.get("dpo_email") or None,
        )
