from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.documents.builders.base import DocumentBuilder
from src.documents.builders.common.payment_mode import (
    integration_mode_note,
    resolve_payment_categories,
)
from src.documents.content_models import BuildContext, CompanyBlock
from src.documents.logbook import (
    LogbookEntry,
    SourceType,
    Status,
    extract_provenance,
)
from src.documents.legal_basis_map import render_data_subjects
from src.documents.purpose_map import pick_lang_text, resolve_processing_purpose

logger = logging.getLogger(__name__)


@dataclass
class SCCServiceRow:
    name: str
    country: str | None
    dpa_url: str | None
    # ADR-106 PR E2 — extra per-service detail for Modul-2 Anhänge
    data_categories: list[str] = field(default_factory=list)
    # ADR-110: True → gap marker at the categories cell (mode unknown)
    data_categories_gap: bool = False
    # Pre-DSB sprint: rendered DE phrase (label-mapped + deduped), not raw keys.
    data_subjects: str = ""
    processing_purpose: str | None = None
    processing_purpose_inferred: bool = False  # True when category-derived, not graph-evidenced
    dpf_status: str | None = None   # Data Privacy Framework status (US-spezifisch)


@dataclass
class SCCContentModel:
    """Every field here will be rendered by scc.md.j2 — ADR-106 PR E2.

    Modul-2 Anhänge per Durchführungsbeschluss 2021/914:
    - Anhang I.A: Parteien (Exporteur + Importeure)
    - Anhang I.B: Beschreibung des Transfers (data_categories, subjects, Zweck)
    - Anhang I.C: Zuständige Aufsichtsbehörde — honest gap text only; the
      bundesland column/UI field does not exist (audit F3), so the former
      graph lookup could never run (ADR-129 PR N3 removed the dead strand)
    - Anhang II: TOM-Referenz (Crossref auf tom_*.md)
    - Anhang III: Liste der Sub-Auftragsverarbeiter
    """
    company: CompanyBlock
    generation_date: str
    run_id: str
    warn_header_gaps: list
    services_with_transfer: list[SCCServiceRow]
    has_us_transfers: bool                                  # triggers TIA block


class SCCBuilder(DocumentBuilder):

    @staticmethod
    def select_services_for_scc(services: list[dict]) -> list[dict]:
        """Return services that require SCCs: country known + not GDPR-adequate (Drittland)."""
        return [
            s for s in services
            if bool(s.get("country")) and not s.get("gdpr_adequate")
        ]

    def build(
        self,
        graph_result: dict,
        reasoning_result: dict,
        config: dict,
        gap_hints: list,
        ctx: BuildContext,
    ) -> SCCContentModel | None:
        services = graph_result.get("services", [])
        drittland = self.select_services_for_scc(services)
        if not drittland:
            return None

        lang = config.get("doc_language", "de") or "de"
        rows = [self._to_row(s, lang) for s in drittland]

        has_us = any(s.get("country") and "USA" in s["country"].upper() for s in drittland)

        return SCCContentModel(
            company=self._company_block(config, ctx),
            generation_date=ctx.generation_date,
            run_id=ctx.run_id,
            warn_header_gaps=self._required_gaps_for("SCC", gap_hints),
            services_with_transfer=rows,
            has_us_transfers=has_us,
        )

    def logbook_entries(
        self, model: SCCContentModel, graph_result: dict
    ) -> list[LogbookEntry]:
        """ADR-111 PR2: one graph_node entry per Drittland service in Anhang I.B,
        read off the built model so the logbook reflects exactly what was
        rendered (no drift)."""
        svc_by_name = {s.get("name"): s for s in graph_result.get("services", [])}
        entries: list[LogbookEntry] = []
        for row in model.services_with_transfer:
            svc = svc_by_name.get(row.name, {})
            entries.append(LogbookEntry(
                section="SCC Anhang I.B Transferbeschreibung",
                source_type=SourceType.GRAPH_NODE,
                source_key={"label": "Service", "name": row.name},
                status=Status.GAP if row.data_categories_gap else Status.SOURCED,
                provenance=extract_provenance(svc),
                note=integration_mode_note(svc),
            ))
        return entries

    def _to_row(self, s: dict, lang: str = "de") -> SCCServiceRow:
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
            override if override is not None
            else self._normalize_list(raw_cats)
        )
        return SCCServiceRow(
            name=s.get("name", ""),
            country=s.get("country"),
            dpa_url=s.get("dpa_url"),
            data_categories=data_categories,
            data_categories_gap=is_gap,
            data_subjects=render_data_subjects(
                self._normalize_list(s.get("data_subjects")), lang
            ),
            processing_purpose=purpose,
            processing_purpose_inferred=purpose_inferred,
            dpf_status=self._dpf_status_for(s, lang),
        )

    @staticmethod
    def _normalize_list(value) -> list[str]:
        """Tolerant: list[str] | str | None → list[str]."""
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v).strip() for v in value if v]
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return [str(value)]

    @staticmethod
    def _dpf_status_for(service: dict, lang: str = "de") -> str | None:
        """ADR-106 PR E2 — best-effort DPF (Data Privacy Framework) flag for US services.

        Today this is a heuristic; the canonical answer needs a per-service DPF
        registration check (out of scope for E2). Returns None = 'unbekannt, prüfen'.
        """
        country = (service.get("country") or "").upper()
        if "USA" not in country:
            return None
        return ("to be verified" if lang == "en" else "zu prüfen")  # neutral default; full DPF lookup post-release

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
