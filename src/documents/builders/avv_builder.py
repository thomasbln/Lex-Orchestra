from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import date

from src.documents.builders.base import DocumentBuilder
from src.documents.builders.common.bfdi_footer import BfDICitation, collect_bfdi_citations
from src.documents.builders.common.payment_mode import (
    integration_mode_note,
    resolve_payment_categories,
)
from src.documents.builders.common.psp_role import PSPRoleLine, psp_role_line
from src.documents.logbook import (
    LogbookEntry,
    SourceType,
    Status,
    extract_provenance,
)
from src.documents.content_models import (
    BuildContext,
    CompanyBlock,
    DeletionRow,
    GapMarker,
    ServiceDataBlock,
    ServiceSummaryRow,
    TransferReferenceBlock,
    RetentionPolicyRow,
)
from src.documents.legal_basis_map import render_data_subjects
from src.documents.purpose_map import pick_lang_text


def _owner_retention_rows(config: dict) -> list["RetentionPolicyRow"]:
    """ADR-129 PR 15: retention_policies rows attached by the architect under
    config['_retention_policies'] — rendered as-is, no service mapping invented."""
    rows = []
    # B-2/L11 (EN package): unit word language-pure (duration_raw stays owner text)
    days_word = "days" if (config.get("doc_language") or "de") == "en" else "Tage"
    for r in config.get("_retention_policies") or []:
        duration = r.get("duration_raw") or (
            f"{r['duration_days']} {days_word}" if r.get("duration_days") is not None else None
        )
        if not duration:
            continue
        rows.append(RetentionPolicyRow(
            category=str(r.get("category") or ""),
            duration=str(duration),
            source=str(r.get("source") or ""),
        ))
    return rows


@dataclass
class AVVContentModel:
    """Every field here will be rendered by avv.md.j2. No extras, no guesses."""
    company: CompanyBlock
    generation_date: str
    run_id: str
    warn_header_gaps: list               # REQUIRED GapHints for AVV
    services_summary: list[ServiceSummaryRow]   # § 1 — curated, not raw
    psp_roles: list[PSPRoleLine]                # § 1 — ADR-115 A1: EDPB controller/processor role
    data_subjects: str | GapMarker              # § 2
    data_categories: list[str]                  # § 2 — flat fallback (deprecated, ADR-106 PR A1)
    service_data_blocks: list[ServiceDataBlock] # § 2(1) — per-service grouping (ADR-106 PR A1)
    special_categories: bool                    # § 2
    instructing_persons: list | GapMarker       # § 3
    transfer_block: TransferReferenceBlock | None   # § 5, None = no transfer
    deletion_periods: list[DeletionRow]         # § 7, every service; period None = gap marker
    owner_retention: list[RetentionPolicyRow]   # ADR-129 PR 15: owner-maintained rows (as-is)
    bfdi_citations: list[BfDICitation]          # ADR-106 PR C5: BfDI footer block


def _split_and_dedup(values: list[str | list | None]) -> list[str]:
    """Split comma-separated strings or list[str] into items, dedup case-insensitive, preserve first-seen casing."""
    seen: dict[str, str] = {}
    for value in values:
        if not value:
            continue
        items = value if isinstance(value, list) else value.split(",")
        for item in items:
            item = str(item).strip()
            if not item:
                continue
            key = item.lower()
            if key not in seen:
                seen[key] = item
    return sorted(seen.values())


class AVVBuilder(DocumentBuilder):

    def build(
        self,
        graph_result: dict,
        reasoning_result: dict,
        config: dict,
        gap_hints: list,
        ctx: BuildContext,
    ) -> AVVContentModel:
        services = graph_result.get("services", [])
        non_eu = [s for s in services if not s.get("gdpr_adequate")]

        transfer_mechanism = next(
            (d.get("transfer_mechanism") for d in graph_result.get("docs_required", [])
             if d.get("transfer_mechanism")),
            None,
        )
        transfer_block = None
        if transfer_mechanism and non_eu:
            transfer_block = TransferReferenceBlock(
                mechanism=transfer_mechanism,
                scc_doc_ref=f"scc_{ctx.run_id[:8]}.md",
                affected_service_count=len(non_eu),
            )

        lang = config.get("doc_language", "de") or "de"
        all_subjects = _split_and_dedup(
            [s.get("data_subjects") for s in services]
        )
        data_subjects_str = render_data_subjects(all_subjects, lang) or None

        data_categories = _split_and_dedup(
            # B-2/L8: language-pure — EN aggregates the seeded _en twins
            [pick_lang_text(s.get("data_categories"), s.get("data_categories_en"), lang)
             for s in services]
        )

        # ADR-106 PR A1: per-service data category blocks (replaces the flat 29-bullet wall)
        # ADR-110: a payment integration mode overrides the static data_categories
        # for that service (delegated/merchant_side wording, or a gap for unknown).
        service_data_blocks: list[ServiceDataBlock] = []
        for s in services:
            override, is_gap = resolve_payment_categories(s, lang)
            if is_gap:
                service_data_blocks.append(
                    ServiceDataBlock(service_name=s.get("name", ""),
                                     data_categories=[], data_categories_gap=True)
                )
                continue
            if override is not None:
                service_data_blocks.append(
                    ServiceDataBlock(service_name=s.get("name", ""), data_categories=override)
                )
                continue
            raw = pick_lang_text(                              # B-2/L8
                s.get("data_categories"), s.get("data_categories_en"), lang
            )
            if not raw:
                continue
            cats = _split_and_dedup([raw])
            if cats:
                service_data_blocks.append(
                    ServiceDataBlock(service_name=s.get("name", ""), data_categories=cats)
                )

        instructing_persons = config.get("instructing_persons") or GapMarker(
            gap_id="avv_instructing_persons_missing",
            article="DSGVO Art. 28 Abs. 3 lit. a",
            fix_url=f"/project/{ctx.project_name}/company",
        )

        data_subjects: str | GapMarker
        if data_subjects_str:
            data_subjects = data_subjects_str
        else:
            data_subjects = GapMarker(
                gap_id="avv_data_subjects_missing",
                article="DSGVO Art. 28 Abs. 3",
                fix_url=f"/project/{ctx.project_name}/company",
            )

        # ADR-106 PR C5: collect BfDI footer citations (best-effort, no-op if
        # graph unreachable). graph_result can carry an optional `_graph_client`
        # if the orchestrator wants to enable BfDI footers; absent → empty list.
        bfdi_citations = collect_bfdi_citations(graph_result.get("_graph_client"), "AVV")

        return AVVContentModel(
            company=self._company_block(config, ctx),
            generation_date=ctx.generation_date,
            run_id=ctx.run_id,
            warn_header_gaps=self._required_gaps_for("AVV", gap_hints),
            services_summary=[self._to_summary_row(s, lang) for s in services],
            psp_roles=[pl for s in services if (pl := psp_role_line(s, lang))],
            data_subjects=data_subjects,
            data_categories=data_categories,
            service_data_blocks=service_data_blocks,
            special_categories=any(s.get("special_categories") for s in services),
            instructing_persons=instructing_persons,
            transfer_block=transfer_block,
            # ADR-129 PR 15 (audit K24/F5): EVERY service appears — a missing
            # period renders a visible gap marker instead of silently dropping
            # the row from § 7.
            deletion_periods=[
                DeletionRow(service=s.get("name", ""), period=s.get("deletion_period"))
                for s in services if s.get("name")
            ],
            owner_retention=_owner_retention_rows(config),
            bfdi_citations=bfdi_citations,
        )

    def logbook_entries(
        self, model: AVVContentModel, graph_result: dict
    ) -> list[LogbookEntry]:
        """ADR-111 PR2: one entry per *contributing source node*, read off the
        built model so the logbook reflects exactly what was rendered (no drift).

        § 2(1) data categories are fed by multiple services; the debugging value
        is seeing *which* service produced *which* claim — hence one graph_node
        entry per service block, not one collected entry per section.
        """
        svc_by_name = {s.get("name"): s for s in graph_result.get("services", [])}
        entries: list[LogbookEntry] = []

        for block in model.service_data_blocks:
            svc = svc_by_name.get(block.service_name, {})
            entries.append(LogbookEntry(
                section="AVV § 2(1) Datenkategorien",
                source_type=SourceType.GRAPH_NODE,
                source_key={"label": "Service", "name": block.service_name},
                status=Status.GAP if block.data_categories_gap else Status.SOURCED,
                provenance=extract_provenance(svc),
                note=integration_mode_note(svc),
            ))

        # § 2 Betroffene Personen — pure field gap (no service node behind it)
        if isinstance(model.data_subjects, GapMarker):
            entries.append(LogbookEntry(
                section="AVV § 2 Betroffene Personen",
                source_type=SourceType.GAP_MARKER,
                source_key={"gap_id": model.data_subjects.gap_id},
                status=Status.GAP,
            ))

        # § 3 Weisungsbefugte — config field, missing → gap
        if isinstance(model.instructing_persons, GapMarker):
            entries.append(LogbookEntry(
                section="AVV § 3 Weisungsbefugte",
                source_type=SourceType.GAP_MARKER,
                source_key={"gap_id": model.instructing_persons.gap_id},
                status=Status.GAP,
            ))

        return entries

    def _to_summary_row(self, s: dict, lang: str = "de") -> ServiceSummaryRow:
        en = lang == "en"
        if not s.get("country"):
            gdpr_status = "pending" if en else "ausstehend"
        elif s.get("gdpr_adequate"):
            gdpr_status = "EU/EEA"
        else:
            gdpr_status = "SCC required" if en else "SCC erforderlich"
        # ADR-115 A1: a service that is its own controller (EDPB-backed) is no
        # Auftragsverarbeiter i.S.v. Art. 28 — so it carries no AVV obligation,
        # and the § 1 table must not contradict § 1.1. We derive the flag from
        # the role; `dpa_required` itself stays untouched (generic property with
        # other consumers — pure read of the existing ACTS_AS edge, no graph write).
        role = s.get("acts_as_role")
        return ServiceSummaryRow(
            name=s.get("name", ""),
            country=s.get("country"),
            gdpr_status=gdpr_status,
            avv_required=bool(s.get("dpa_required")) and role != "controller",
            dpa_url=s.get("dpa_url"),
            acts_as_role=role,
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
