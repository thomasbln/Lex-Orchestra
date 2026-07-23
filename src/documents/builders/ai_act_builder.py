from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.documents.builders.base import DocumentBuilder
from src.documents.builders.common.bfdi_footer import BfDICitation
from src.documents.content_models import BuildContext, CompanyBlock

logger = logging.getLogger(__name__)


@dataclass
class AIActUseCaseBlock:
    """AI use case for manifest — includes risk classification."""
    type: str
    title_de: str
    description_de: str | None
    risk_level: str
    article: str | None
    annex_iii_nr: str | None
    deployer_action: str | None
    reason: str | None = None   # §3 Begründung — UseCase.reason from the graph


@dataclass
class AIActRiskLevelRow:
    """Service risk-level assignment from graph_result.risk_levels."""
    service: str
    level: str


@dataclass
class AIActContentModel:
    """Every field here will be rendered by ai_act_manifest.md.j2. No extras."""
    company: CompanyBlock
    generation_date: str
    run_id: str
    warn_header_gaps: list
    risk_levels: list[AIActRiskLevelRow]
    deployer_usecase: AIActUseCaseBlock | None
    ai_usecase_type: str | None
    indicated_usecases: list[AIActUseCaseBlock]
    all_usecases: list[AIActUseCaseBlock]
    has_audit_trail_gap: bool
    art4_effective_date: str
    # TODO ADR-098 PR 3: Law-Node-References integration
    # Currently empty — will be populated by gc.get_law_text() calls after PR 4.
    law_references: list[str] = field(default_factory=list)
    # ADR-106 PR C.1 Cleanup
    bfdi_citations: list[BfDICitation] = field(default_factory=list)
    bias_risk_annex_iii_nr_4: bool = False   # HR-Recruiting trigger for bias warning
    # PR-B Gate 1: operative AI responsibility from ai_config.project_level.
    # Real field (not @property) — asdict() in document_architect:1316 only
    # serializes declared fields. None when ai_config is empty/missing.
    operative_responsible: str | None = None
    tech_responsible: str | None = None   # PR-B Gate 2a — same project_level path
    # ADR-124 Gate B: AI literacy (Art. 4) from ai_config.project_level. asdict-safe.
    ai_literacy_measures: bool | None = None   # tri-state: True / False / None (unset → gap)
    ai_literacy_note: str | None = None        # optional free text ("how")
    # ADR-124 Doc-Polish: True when ANY detected AI service's per-service purpose risk differs
    # from this manifest's project-wide classification. Computed by the orchestrator (the only
    # layer that sees both sides). Drives a divergence hint under the risk table. False when no
    # service diverges or no comparison is possible (one side absent).
    service_risk_diverges: bool = False


class AIActBuilder(DocumentBuilder):

    def build(
        self,
        graph_result: dict,
        reasoning_result: dict,
        config: dict,
        gap_hints: list,
        ctx: BuildContext,
        *,
        service_risk_diverges: bool = False,
    ) -> AIActContentModel:
        risk_levels_raw = graph_result.get("risk_levels", [])
        active_risks = set(graph_result.get("active_risks", []))
        ai_usecase_type = config.get("ai_usecase_type")

        # PR-B Gate 1: operative AI responsibility from ai_config.project_level.
        project_level = (config.get("ai_config") or {}).get("project_level") or {}
        operative_responsible = project_level.get("operative_responsible") or None
        tech_responsible = project_level.get("tech_responsible") or None
        ai_literacy_measures = project_level.get("ai_literacy_measures")  # bool|None, keep False
        ai_literacy_note = project_level.get("ai_literacy_note") or None
        service_names = [s.get("name", "") for s in graph_result.get("services", [])]

        deployer_usecase: AIActUseCaseBlock | None = None
        indicated_usecases: list[AIActUseCaseBlock] = []
        all_usecases: list[AIActUseCaseBlock] = []
        art4_effective_date = "2025-02-02"

        lang = config.get("doc_language", "de") or "de"
        graph_data = self._fetch_graph_data(ai_usecase_type=ai_usecase_type,
                                            service_names=service_names)
        if graph_data:
            if ai_usecase_type:
                deployer_usecase = next(
                    (self._to_usecase_block(u, lang)
                     for u in graph_data["candidates"]
                     if u.get("type") == ai_usecase_type),
                    None,
                )
            else:
                indicated_usecases = [self._to_usecase_block(u, lang)
                                      for u in graph_data["indicated_usecases"]]
                all_usecases = [self._to_usecase_block(u, lang)
                                for u in graph_data["all_usecases"]]
            art4_effective_date = graph_data["art4_effective_date"]

        # PR G FIX 5: the AI-Act manifest pulls NO BfDI citations. The BfDI source
        # ("DSGVO–BDSG") has no AI-Act section — only chapters 3.1/3.2 (DSB-Pflichten,
        # Auftragsverarbeitung), which belong in AVV/VVT/DSFA, not here. bfdi_citations
        # keeps its empty default; the footer macro renders nothing for an empty list.
        # Annex III Nr. 4 = Beschäftigung (HR-Recruiting, automatisierte Bewerber-Bewertung).
        # Bias-Risiko ist hier juristisch zentral (Art. 22 DSGVO + Diskriminierungsverbot AGG).
        bias_risk_annex_iii_nr_4 = bool(
            deployer_usecase
            and (
                deployer_usecase.annex_iii_nr == "4"
                or (deployer_usecase.article and "Annex III Nr. 4" in deployer_usecase.article)
            )
        )

        return AIActContentModel(
            company=self._company_block(config, ctx),
            generation_date=ctx.generation_date,
            run_id=ctx.run_id,
            warn_header_gaps=self._required_gaps_for("AI_Act_Manifest", gap_hints),
            risk_levels=[
                AIActRiskLevelRow(service=r.get("service", ""), level=r.get("level", ""))
                for r in risk_levels_raw
            ],
            deployer_usecase=deployer_usecase,
            ai_usecase_type=ai_usecase_type,
            indicated_usecases=indicated_usecases,
            all_usecases=all_usecases,
            has_audit_trail_gap="NO_AI_AUDIT_TRAIL" in active_risks,
            art4_effective_date=art4_effective_date,
            law_references=[],
            bias_risk_annex_iii_nr_4=bias_risk_annex_iii_nr_4,
            operative_responsible=operative_responsible,
            tech_responsible=tech_responsible,
            ai_literacy_measures=ai_literacy_measures,
            ai_literacy_note=ai_literacy_note,
            service_risk_diverges=service_risk_diverges,
        )

    def _fetch_graph_data(
        self,
        ai_usecase_type: str | None,
        service_names: list[str],
    ) -> dict | None:
        """Single GraphClient context — all queries in one session.

        Returns None on graph failure (graceful fallback to empty-data render).
        """
        try:
            from src.graph.graph_client import GraphClient

            with GraphClient() as gc:
                result: dict = {
                    "candidates": [],
                    "indicated_usecases": [],
                    "all_usecases": [],
                    "art4_effective_date": "2025-02-02",
                }

                if ai_usecase_type:
                    result["candidates"] = (
                        gc.get_usecases_for_risk_level("Limited")
                        + gc.get_usecases_for_risk_level("High")
                        + gc.get_usecases_for_risk_level("Minimal")
                    )
                else:
                    result["indicated_usecases"] = gc.get_indicated_usecases(service_names)
                    result["all_usecases"] = (
                        gc.get_usecases_for_risk_level("High")
                        + gc.get_usecases_for_risk_level("Limited")
                        + gc.get_usecases_for_risk_level("Minimal")
                    )

                art4 = gc.get_law_text("EU AI Act", "4", prop="effective_date")
                if art4:
                    result["art4_effective_date"] = art4

                return result

        except Exception as exc:
            logger.warning("AIActBuilder graph fetch failed: %s", exc)
            return None

    # B-2/L5 (EN package): N1 marker — the EN doc NEVER silently shows German.
    # A German value without its _en twin renders this honest placeholder.
    _TRANSLATION_PENDING_EN = "☐ translation pending (German version exists)"

    def _lang_text(self, uc: dict, base: str, lang: str) -> str | None:
        """Language-pure field pick: EN → `_en` or pending-marker; DE → base."""
        if lang == "en":
            val = uc.get(f"{base}_en")
            if val:
                return val
            return self._TRANSLATION_PENDING_EN if uc.get(base) else None
        return uc.get(base)

    def _to_usecase_block(self, uc: dict, lang: str = "de") -> AIActUseCaseBlock:
        return AIActUseCaseBlock(
            type=uc.get("type", ""),
            # ADR-129 PR 12 (F8): field keeps its name; carries the doc-language title
            title_de=((uc.get("title_en") if lang == "en" else None)
                      or uc.get("title_de") or uc.get("type", "")),
            description_de=uc.get("description_de"),
            risk_level=uc.get("risk_level", "Minimal"),
            article=uc.get("article"),
            annex_iii_nr=str(uc.get("annex_iii_nr")) if uc.get("annex_iii_nr") else None,
            # B-2/L5: deployer obligations + reasoning language-pure (seeded
            # 20/20 deployer_action_en, 19/20 reason_en — the one held-back
            # reason renders the pending marker, per Thomas' accepted remnants)
            deployer_action=self._lang_text(uc, "deployer_action", lang),
            reason=self._lang_text(uc, "reason", lang),
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
