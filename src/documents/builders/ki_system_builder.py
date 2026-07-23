from __future__ import annotations

from dataclasses import dataclass, field

from src.documents.builders.base import DocumentBuilder
from src.documents.builders.common.cell_safe import cell_text
from src.documents.content_models import BuildContext, CompanyBlock
from src.documents.purpose_map import pick_lang_text
from src.graph.graph_client import resolve_control_title


@dataclass
class AIServiceDetail:
    """Single AI service with risk-assessment detail for KI_System_Dokumentation."""
    name: str
    category: str | None
    country: str | None
    gdpr_adequate: bool
    dpa_url: str | None
    risk_level: str | None
    data_categories: str | None
    special_categories: bool
    processing_purpose: str | None
    deletion_period: str | None


@dataclass
class AIUseCaseBlock:
    """AI use case classification from graph (Annex III / Art. 50)."""
    type: str
    title_de: str
    description_de: str | None
    risk_level: str
    article: str | None
    annex_iii_nr: str | None
    deployer_action: str | None


@dataclass
class KISystemMeasureRow:
    """§ 7 row — concrete TOM measure attributable to this service (ADR-106 PR A6)."""
    control_id: str
    framework_label: str
    measure: str
    concrete: str | None


@dataclass
class KISystemContentModel:
    """Every field here will be rendered by ki_system.md.j2. No extras, no guesses."""
    company: CompanyBlock
    generation_date: str
    run_id: str
    warn_header_gaps: list
    service: AIServiceDetail
    ai_usecase: AIUseCaseBlock | None
    is_high_risk: bool
    requires_fundamental_rights_assessment: bool
    implemented_measures: list[KISystemMeasureRow]   # ADR-106 PR A6
    # ADR-124 Gate B: deployer per-service input from ai_config.per_service[<service.name>].
    # Flat (not in AIServiceDetail) — the ai_config read lives in build() where `config`
    # is available. Real fields, asdict-safe (no @property — asdict drops properties).
    model_name: str | None = None       # JSONB key "model" — the LLM model (deployer-stated)
    purpose: str | None = None          # JSONB key "purpose" — UseCase.type (drives ai_usecase)
    user_groups: str | None = None      # renamed from nutzergruppen
    usage_limits: str | None = None     # renamed from grenzen
    training_data: bool | None = None   # tri-state: True / False / None (unset → gap)
    logging: bool | None = None         # tri-state: True / False / None (unset → gap)
    # review_date removed (ADR-124) — replaced by a risk-gated default sentence in the template
    # ADR-124 Doc-Polish: the project-wide scanner risk (ai_usecase_type → risk_level), passed
    # in by the orchestrator (the only layer that sees both). Counterpart to this doc's
    # per-service ai_usecase.risk_level — the template shows a divergence hint when they differ.
    # None when no project-wide classification exists (no comparison → no hint).
    project_risk_level: str | None = None


class KISystemBuilder(DocumentBuilder):

    def build(
        self,
        graph_result: dict,
        reasoning_result: dict,
        config: dict,
        gap_hints: list,
        ctx: BuildContext,
        *,
        service: dict,
        ai_usecase: dict | None = None,
        project_risk_level: str | None = None,
    ) -> KISystemContentModel:
        """Build per-service. `service` and `ai_usecase` are keyword args because
        this builder has a narrower scope than the others — it's called once per
        detected AI service."""
        service_detail = self._to_service_detail(
            service, graph_result, config.get("doc_language", "de") or "de"
        )
        usecase_block = self._to_usecase_block(ai_usecase, config.get("doc_language", "de") or "de") if ai_usecase else None
        is_high_risk = bool(usecase_block and usecase_block.risk_level == "High")
        # ADR-127 P4.3: owner overlay (best-effort) — shared source with TOM per (control_id, run_id, lang).
        from src.documents.builders.common.owner_measures import load_owner_measures
        _lang = config.get("doc_language", "de") or "de"
        owner_edits, deleted_controls = load_owner_measures(ctx.project_name, ctx.run_id, _lang)
        implemented_measures = self._collect_service_measures(
            service, graph_result, config, owner_edits, deleted_controls
        )

        # PR-B Gate 2b: per-service deployer input, keyed by exact service name.
        ps = ((config.get("ai_config") or {}).get("per_service") or {}).get(service.get("name")) or {}

        return KISystemContentModel(
            company=self._company_block(config, ctx),
            generation_date=ctx.generation_date,
            run_id=ctx.run_id,
            warn_header_gaps=self._required_gaps_for("KI_System_Dokumentation", gap_hints),
            service=service_detail,
            ai_usecase=usecase_block,
            is_high_risk=is_high_risk,
            requires_fundamental_rights_assessment=is_high_risk,
            implemented_measures=implemented_measures,
            model_name=ps.get("model") or None,
            purpose=ps.get("purpose") or None,
            user_groups=ps.get("user_groups") or None,
            usage_limits=ps.get("usage_limits") or None,
            # bool fields: no `or None` — that would collapse an explicit False ("Nein")
            # to None. The migration coerced legacy strings to null, so values are now
            # True / False / None (tri-state).
            training_data=ps.get("training_data"),
            logging=ps.get("logging"),
            project_risk_level=project_risk_level,
        )

    # ── ADR-106 PR A6: § 7 Render — controls attributable to this AI service ─
    def _collect_service_measures(
        self,
        service: dict,
        graph_result: dict,
        config: dict,
        owner_edits: dict[str, str] | None = None,
        deleted_controls: set[str] | None = None,
    ) -> list[KISystemMeasureRow]:
        owner_edits = owner_edits or {}
        deleted_controls = deleted_controls or set()
        """For the given AI service, return TOM-controls that map to it from the
        scan. Uses the existing graph_result['controls'] join — no new query.
        Controls match by service.name in row['service'] or by ServiceCategory
        (row['service'] starts with 'category:').
        """
        service_name = service.get("name", "")
        service_category = service.get("category", "")
        framework_labels = {
            "BSI_Grundschutz": "BSI IT-Grundschutz",
            "ISO_27001": "ISO 27001",
            "OWASP_LLM_Top10": "OWASP LLM Top 10",
            "OWASP_API_Top10": "OWASP API Top 10",
            "NIST_CSF_2": "NIST CSF 2.0",
        }
        tom_impl = config.get("tom_implementations") or {}
        lang = config.get("doc_language", "de") or "de"
        rows: list[KISystemMeasureRow] = []
        seen: set[tuple[str, str]] = set()
        for c in graph_result.get("controls", []):
            svc_label = c.get("service", "")
            is_match = (
                svc_label == service_name
                or (service_category and svc_label == f"category:{service_category}")
            )
            if not is_match:
                continue
            fw = c.get("framework", "")
            cid = c.get("control_id", "")
            if cid in deleted_controls:   # ADR-127 P4.3: owner-deactivated → real skip (lang-agnostic)
                continue
            key = (fw, cid)
            if key in seen:
                continue
            seen.add(key)
            rows.append(KISystemMeasureRow(
                control_id=cid,
                framework_label=framework_labels.get(fw, fw),
                measure=f"{cid} — {resolve_control_title(c, lang)}",
                # ADR-127: \n → <br> (render-layer); `or None` preserves the nullable cell.
                # ADR-129 PR 9 (F1): EN default when present, DE fallback.
                concrete=cell_text(
                    owner_edits.get(cid)
                    # B-2 (EN package): legacy lang-less layer never leaks to EN
                    or (tom_impl.get(cid) if lang != "en" else None)
                    or (c.get("default_tom_measure_en") if lang == "en" else None)
                    or c.get("default_tom_measure")
                ) or None,
            ))
            if len(rows) >= 12:
                break
        return rows

    def _to_service_detail(self, service: dict, graph_result: dict, lang: str = "de") -> AIServiceDetail:
        risk_entry = next(
            (r for r in graph_result.get("risk_levels", [])
             if r.get("service") == service.get("name")),
            None,
        )
        return AIServiceDetail(
            name=service.get("name", ""),
            category=service.get("category"),
            country=service.get("country"),
            gdpr_adequate=bool(service.get("gdpr_adequate")),
            dpa_url=service.get("dpa_url"),
            risk_level=risk_entry["level"] if risk_entry else None,
            # B-2/L8 (EN package): language-pure descriptor pick; deletion_period
            # stays German by accepted remnant L14.
            data_categories=pick_lang_text(
                service.get("data_categories"), service.get("data_categories_en"), lang
            ),
            special_categories=bool(service.get("special_categories")),
            processing_purpose=pick_lang_text(
                service.get("processing_purpose"), service.get("processing_purpose_en"), lang
            ),
            deletion_period=service.get("deletion_period"),
        )

    def _to_usecase_block(self, uc: dict, lang: str = "de") -> AIUseCaseBlock:
        return AIUseCaseBlock(
            type=uc.get("type", ""),
            # ADR-129 PR 12 (F8): field keeps its name; carries the doc-language title
            title_de=((uc.get("title_en") if lang == "en" else None)
                      or uc.get("title_de") or uc.get("type", "")),
            description_de=uc.get("description_de"),
            risk_level=uc.get("risk_level", "Minimal"),
            article=uc.get("article"),
            annex_iii_nr=str(uc.get("annex_iii_nr")) if uc.get("annex_iii_nr") else None,
            deployer_action=uc.get("deployer_action"),
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
