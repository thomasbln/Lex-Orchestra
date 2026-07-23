from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.scanner.gap_analyzer import GapHint


@dataclass
class BuildContext:
    """Orchestrator state per render run. Prevents config-hacks in builders."""
    run_id: str
    generation_date: str
    project_name: str


@dataclass
class CompanyBlock:
    name: str
    legal_form: str
    address: str
    zip_city: str
    contact_email: str
    website_url: str
    responsible_name: str | None
    responsible_title: str | None
    dpo_name: str | None
    dpo_email: str | None


@dataclass
class ServiceSummaryRow:
    name: str
    country: str | None
    gdpr_status: str       # "EU/EEA" | "SCC erforderlich" | "ausstehend"
    avv_required: bool
    dpa_url: str | None
    # ADR-115 A1: the EDPB-backed ACTS_AS role, or None for non-PSP services. A
    # "controller" carries no Art. 28 AVV obligation — the § 1 table renders a
    # cross-reference to § 1.1 instead of an AVV-Pflicht checkmark.
    acts_as_role: str | None = None


@dataclass
class DeletionRow:
    service: str
    # None = service has no retention period in the graph — the template renders
    # a visible gap marker instead of silently dropping the row (ADR-129 PR 15).
    period: str | None


@dataclass
class RetentionPolicyRow:
    """ADR-129 PR 15 (audit K24/F5): owner-maintained retention_policies row —
    rendered as-is (data-type-based; deliberately NOT mapped onto services)."""
    category: str
    duration: str
    source: str


@dataclass
class SubprocessorRow:
    name: str
    country: str | None
    dpa_url: str | None


@dataclass
class TransferReferenceBlock:
    mechanism: str
    scc_doc_ref: str           # e.g. "scc_0158d042.md"
    affected_service_count: int


@dataclass
class GapMarker:
    gap_id: str
    article: str
    fix_url: str


@dataclass
class ServiceDataBlock:
    """Per-service data category block for AVV § 2(1) (ADR-106 PR A1)."""
    service_name: str
    data_categories: list[str]
    # ADR-110: True → render a gap marker at this block's categories cell instead
    # of the list (payment integration mode could not be determined).
    data_categories_gap: bool = False
