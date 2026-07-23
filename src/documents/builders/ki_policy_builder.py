from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from src.documents.builders.base import DocumentBuilder
from src.documents.content_models import BuildContext, CompanyBlock


@dataclass
class AIServiceRow:
    """Single AI service entry in KI-Policy. Curated view — no raw graph fields."""
    name: str
    category: str | None
    purpose: str
    data_categories: str | None
    country: str | None
    gdpr_adequate: bool


@dataclass
class KIPolicyContentModel:
    """Every field here will be rendered by ki_policy.md.j2. No extras, no guesses."""
    company: CompanyBlock
    generation_date: str
    run_id: str
    warn_header_gaps: list
    ai_services: list[AIServiceRow]
    has_drittland: bool
    has_llm: bool
    # ADR-124 Gate B: AI literacy (Art. 4) from ai_config.project_level. Real fields,
    # asdict-safe. ki_policy_review_date removed (ADR-124) → risk-gated default sentence.
    ai_literacy_measures: bool | None = None   # tri-state: True / False / None (unset → gap)
    ai_literacy_note: str | None = None        # optional free text ("how")


_AI_PURPOSE_BY_CATEGORY: dict[str, str] = {
    "ai_llm":        "KI-gestützte Textgenerierung und -verarbeitung",
    "ai_platform":   "KI-Plattformdienste und Modellinferenz",
    "vector_db":     "Vektordatenbank für Embedding-Speicherung (RAG)",
    "observability": "LLM-Observability und KI-Audit-Trail (EU AI Act Art. 12)",
}

# B-2/L3 (EN package): EN twin — the builder never read doc_language, so the
# EN KI policy rendered 100% German rows. lex-authored translations.
_AI_PURPOSE_BY_CATEGORY_EN: dict[str, str] = {
    "ai_llm":        "AI-assisted text generation and processing",
    "ai_platform":   "AI platform services and model inference",
    "vector_db":     "Vector database for embedding storage (RAG)",
    "observability": "LLM observability and AI audit trail (EU AI Act Art. 12)",
}
_AI_PURPOSE_FALLBACK = "KI-basierte Leistungserbringung"
_AI_PURPOSE_FALLBACK_EN = "AI-based service delivery"


class KIPolicyBuilder(DocumentBuilder):

    def build(
        self,
        graph_result: dict,
        reasoning_result: dict,
        config: dict,
        gap_hints: list,
        ctx: BuildContext,
    ) -> KIPolicyContentModel:
        # graph_result["services"] is already the ai-filtered list, passed via
        # graph_result_for_builder = {"services": ai_services} in _write_ki_policy.
        # Caller pre-filters — no re-filtering here (would be harmless but misleading).
        lang = config.get("doc_language", "de") or "de"   # B-2/L3
        ai_rows = [self._to_service_row(s, lang) for s in graph_result.get("services", [])]

        # ADR-124 Gate B: project-level AI literacy (Art. 4) from ai_config.
        project_level = (config.get("ai_config") or {}).get("project_level") or {}
        ai_literacy_measures = project_level.get("ai_literacy_measures")  # bool|None, keep False
        ai_literacy_note = project_level.get("ai_literacy_note") or None

        return KIPolicyContentModel(
            company=self._company_block(config, ctx),
            generation_date=ctx.generation_date,
            run_id=ctx.run_id,
            warn_header_gaps=self._required_gaps_for("KI_Policy", gap_hints),
            ai_services=ai_rows,
            has_drittland=any(not s.gdpr_adequate for s in ai_rows),
            has_llm=any(s.category == "ai_llm" for s in ai_rows),
            ai_literacy_measures=ai_literacy_measures,
            ai_literacy_note=ai_literacy_note,
        )

    def _to_service_row(self, s: dict, lang: str = "de") -> AIServiceRow:
        category = s.get("category")
        purpose_map = _AI_PURPOSE_BY_CATEGORY_EN if lang == "en" else _AI_PURPOSE_BY_CATEGORY
        fallback = _AI_PURPOSE_FALLBACK_EN if lang == "en" else _AI_PURPOSE_FALLBACK
        purpose = s.get("purpose") or purpose_map.get(category or "", fallback)
        return AIServiceRow(
            name=s.get("name", ""),
            category=category,
            purpose=purpose,
            data_categories=s.get("data_categories"),
            country=s.get("country"),
            gdpr_adequate=bool(s.get("gdpr_adequate")),
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
            address=config.get("address") or "(Adresse eintragen)",
            zip_city=zip_city,
            contact_email=config.get("contact_email") or "(E-Mail eintragen)",
            website_url=config.get("website_url") or "",
            responsible_name=config.get("responsible_name") or None,
            responsible_title=config.get("responsible_title") or None,
            dpo_name=config.get("dpo_name") or None,
            dpo_email=config.get("dpo_email") or None,
        )
