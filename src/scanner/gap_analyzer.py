"""ADR-086: Gap analysis for scan report.

Inspects project state (config, setup, retention policies, detected services)
to identify missing data that would improve generated documents. Emits
structured GapHint objects with dashboard deep-links and priority levels.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field as dc_field
from typing import Literal

logger = logging.getLogger(__name__)

DASHBOARD_BASE = os.environ.get("DASHBOARD_BASE_URL", "http://localhost:3000")


@dataclass
class GapHint:
    # ADR-098: new fields for warn-header and inline-gap-marker
    id: str = ""
    severity: Literal["REQUIRED", "RECOMMENDED"] = "RECOMMENDED"
    article: str = ""                    # e.g. "DSGVO Art. 28 Abs. 3 lit. a"
    doc_affected: list = dc_field(default_factory=list)
    description: str = ""
    # B-2/L2 (EN package): English twin for the EN warn-header. Every creation
    # site MUST set it (guard test counts sites) — the EN render never falls
    # back to German silently (language-pure cut, N1).
    description_en: str = ""
    # existing fields kept for backwards compatibility
    field: str = ""
    gap_reason: str = ""
    affected_docs: list = dc_field(default_factory=list)
    fix_url: str = ""
    fix_label: str = ""
    priority: int = 2                    # 1=critical, 2=important, 3=nice-to-have (deprecated, use severity)


_SEVERITY_ORDER = {"REQUIRED": 0, "RECOMMENDED": 1}


def _severity_order(s: str) -> int:
    return _SEVERITY_ORDER.get(s, 2)


def _url(project_name: str, section: str) -> str:
    return f"{DASHBOARD_BASE}/project/{project_name}/{section}"


# ── Gap detectors ──────────────────────────────────────────────────────────────

def _check_company_gaps(config: dict, project_name: str) -> list[GapHint]:
    hints = []
    if not config.get("company_name"):
        hints.append(GapHint(
            id="company_name_missing",
            severity="REQUIRED",
            article="§ 5 Abs. 1 Nr. 2 DDG",
            doc_affected=["Impressum", "AVV", "TOM", "VVT"],
            description="Unternehmensname",
            description_en="Company name",
            field="company_name",
            gap_reason="Company name not configured — required in all generated documents.",
            affected_docs=["Impressum", "AVV", "TOM", "VVT"],
            fix_url=_url(project_name, "company"),
            fix_label="Set company details",
            priority=1,
        ))
    if not config.get("address") or not config.get("city"):
        hints.append(GapHint(
            id="address_missing",
            severity="REQUIRED",
            article="§ 5 Abs. 1 Nr. 1 DDG",
            doc_affected=["Impressum"],
            description="Vollständige Anschrift",
            description_en="Full postal address",
            field="address",
            gap_reason="Legal address missing — required for Impressum per DDG § 5.",
            affected_docs=["Impressum"],
            fix_url=_url(project_name, "company"),
            fix_label="Add address",
            priority=1,
        ))
    if not config.get("dpo_name") or not config.get("dpo_email"):
        hints.append(GapHint(
            id="dpo_missing",
            severity="RECOMMENDED",
            article="DSGVO Art. 37",
            doc_affected=["AVV", "VVT", "DSFA"],
            description="Datenschutzbeauftragter (falls gesetzlich erforderlich)",
            description_en="Data protection officer (where legally required)",
            field="dpo",
            gap_reason="Data Protection Officer not set — required in AVV signature block and VVT.",
            affected_docs=["AVV", "VVT", "DSFA"],
            fix_url=_url(project_name, "company"),
            fix_label="Set DPO",
            priority=2,
        ))
    if not config.get("register_court") or not config.get("register_number"):
        hints.append(GapHint(
            id="register_missing",
            severity="RECOMMENDED",
            article="§ 5 Abs. 1 Nr. 4 DDG",
            doc_affected=["Impressum"],
            description="Handelsregistereintrag (für eingetragene Unternehmen)",
            description_en="Commercial register entry (for registered companies)",
            field="register",
            gap_reason="Handelsregister details missing — required in Impressum for commercial entities.",
            affected_docs=["Impressum"],
            fix_url=_url(project_name, "company"),
            fix_label="Add register info",
            priority=2,
        ))
    return hints


def _check_hosting_gaps(setup: dict | None, project_name: str) -> list[GapHint]:
    hints = []
    if not setup or not setup.get("hosting_provider"):
        hints.append(GapHint(
            id="hosting_provider_missing",
            severity="REQUIRED",
            article="DSGVO Art. 32 Abs. 1 (TOM-Nachweispflicht)",
            doc_affected=["TOM"],
            description="Primärer Hosting-Provider (TOM § 1.1 Zutrittskontrolle)",
            description_en="Primary hosting provider (TOM § 1.1 physical access control)",
            field="hosting_provider",
            gap_reason="Primary hosting provider not selected — TOM § 1.1 delegation block incomplete.",
            affected_docs=["TOM § 1.1"],
            fix_url=_url(project_name, "hosting"),
            fix_label="Select hosting provider",
            priority=1,
        ))
    if setup and not setup.get("hosting_region") and not setup.get("on_prem"):
        hints.append(GapHint(
            id="hosting_region_missing",
            severity="RECOMMENDED",
            article="DSGVO Art. 44",
            doc_affected=["TOM", "AVV"],
            description="Hosting-Region (für Drittland-Transfer-Assessment)",
            description_en="Hosting region (for the third-country transfer assessment)",
            field="hosting_region",
            gap_reason="Hosting region missing — relevant for third-country-transfer assessment.",
            affected_docs=["TOM", "AVV § 5"],
            fix_url=_url(project_name, "hosting"),
            fix_label="Set hosting region",
            priority=2,
        ))
    return hints


def _check_retention_gaps(retention_policies: list, project_name: str) -> list[GapHint]:
    hints = []
    if not retention_policies:
        hints.append(GapHint(
            id="retention_missing",
            severity="REQUIRED",
            article="DSGVO Art. 13 Abs. 2 lit. a; Art. 28 Abs. 3 lit. g; Art. 30 Abs. 1 lit. f",
            doc_affected=["AVV", "VVT", "Datenschutzerklärung"],
            description="Speicherfristen / Löschkonzept",
            description_en="Retention periods / deletion concept",
            field="retention",
            gap_reason="No retention policies defined — privacy policy and VVT cannot state storage periods.",
            affected_docs=["AVV", "VVT", "Datenschutzerklärung"],
            fix_url=_url(project_name, "retention"),
            fix_label="Add retention policies",
            priority=1,
        ))
    elif len(retention_policies) < 3:
        hints.append(GapHint(
            id="retention_coverage_low",
            severity="RECOMMENDED",
            article="DSGVO Art. 30 Abs. 1 lit. f",
            doc_affected=["VVT"],
            description=f"Nur {len(retention_policies)} Löschfrist-Einträge — empfohlen: Logs, Accounts, Transaktionen",
            description_en=f"Only {len(retention_policies)} retention entries — recommended: logs, accounts, transactions",
            field="retention_coverage",
            gap_reason=f"Only {len(retention_policies)} retention entr{'y' if len(retention_policies) == 1 else 'ies'}. Consider adding entries for logs, accounts, and purchases.",
            affected_docs=["VVT"],
            fix_url=_url(project_name, "retention"),
            fix_label="Add more retention entries",
            priority=3,
        ))
    return hints


def _check_service_gaps(services_detected: list[dict], project_name: str) -> list[GapHint]:
    hints = []
    failed = [s for s in services_detected if s.get("enrichment_status") == "failed"]
    if failed:
        names = ", ".join(s.get("name", "?") for s in failed[:5])
        hints.append(GapHint(
            id="service_enrichment_failed",
            severity="RECOMMENDED",
            article="",
            doc_affected=["AVV", "SCC"],
            description=f"Service-Metadaten konnten nicht abgerufen werden: {names}",
            description_en=f"Service metadata could not be retrieved: {names}",
            field="service_enrichment",
            gap_reason=f"Could not auto-fetch metadata for: {names}. Using static fallback which may be outdated.",
            affected_docs=["AVV § 1", "SCC"],
            fix_url=_url(project_name, "integrations"),
            fix_label="Review service details manually",
            priority=2,
        ))
    no_country = [s for s in services_detected if not s.get("country")]
    if no_country:
        names = ", ".join(s.get("name", "?") for s in no_country[:5])
        hints.append(GapHint(
            id="service_country_unknown",
            severity="RECOMMENDED",
            article="DSGVO Art. 44",
            doc_affected=["AVV", "SCC"],
            description=f"Herkunftsland unbekannt für: {names}",
            description_en=f"Country of origin unknown for: {names}",
            field="service_country",
            gap_reason=f"Country unknown for: {names}. Third-country transfer assessment incomplete.",
            affected_docs=["AVV", "SCC"],
            fix_url=_url(project_name, "integrations"),
            fix_label="Fill service countries",
            priority=1,
        ))
    return hints


def _check_avv_required_gaps(config: dict, services_detected: list[dict], project_name: str) -> list[GapHint]:
    """AVV-specific gaps: responsible name, instructing_persons, TOM config, data subjects."""
    hints = []
    if not config.get("responsible_name"):
        hints.append(GapHint(
            id="responsible_name_missing",
            severity="REQUIRED",
            article="DSGVO Art. 28 Abs. 3; Art. 30 Abs. 1 lit. a; § 5 DDG",
            doc_affected=["AVV", "TOM", "VVT", "DSFA", "KI_Policy", "AI_Act_Manifest", "KI_System_Dokumentation"],
            description="Verantwortliche Person (Unterzeichner)",
            description_en="Responsible person (signatory)",
            field="responsible_name",
            gap_reason="Responsible name not set — required as signatory in all legal documents.",
            affected_docs=["AVV", "TOM", "VVT", "DSFA"],
            fix_url=_url(project_name, "company"),
            fix_label="Set responsible person",
            priority=1,
        ))
    # instructing_persons: JSONB array in project_config, default [] — empty list = not configured
    instructing_persons = config.get("instructing_persons") or []
    if not instructing_persons:
        hints.append(GapHint(
            id="avv_instructing_persons_missing",
            severity="REQUIRED",
            article="DSGVO Art. 28 Abs. 3 Satz 2 lit. a",
            doc_affected=["AVV"],
            description="Weisungsberechtigte Person(en) auf Seiten des Verantwortlichen",
            description_en="Person(s) authorised to issue instructions on the controller's side",
            field="instructing_persons",
            gap_reason="No instructing persons defined — AVV Art. 28(3) Satz 2 lit. a control mechanism incomplete.",
            affected_docs=["AVV"],
            fix_url=_url(project_name, "instructing_persons"),
            fix_label="Weisungsberechtigte ergänzen",
            priority=1,
        ))
    # tom_implementations: JSONB in project_config, {} means not configured
    tom_impl = config.get("tom_implementations") or {}
    if not tom_impl:
        hints.append(GapHint(
            id="avv_technical_measures_missing",
            severity="RECOMMENDED",
            article="DSGVO Art. 28 Abs. 3 lit. c; Art. 32",
            doc_affected=["TOM"],
            description="TOM-Implementierungen nicht konfiguriert — im TOM-Setup ergänzen",
            description_en="TOM implementations not configured — add them in the TOM setup",
            field="tom_implementations",
            gap_reason="tom_implementations not configured — AVV cannot reference concrete TOM measures.",
            affected_docs=["TOM"],
            fix_url=_url(project_name, "hosting"),
            fix_label="TOM-Implementierungen ergänzen",
            priority=2,
        ))
    # data_subjects: derived from services_detected graph data, not project_config
    if not any(s.get("data_subjects") for s in services_detected):
        hints.append(GapHint(
            id="avv_data_subjects_missing",
            severity="RECOMMENDED",
            article="DSGVO Art. 28 Abs. 3",
            doc_affected=["AVV"],
            description="Kein Service liefert Betroffenen-Kategorien aus dem Graph",
            description_en="No service provides data-subject categories from the graph",
            field="data_subjects",
            gap_reason="No service provides data_subjects from graph — AVV § 1 Abs. 2 description of affected persons incomplete.",
            affected_docs=["AVV"],
            fix_url=_url(project_name, "integrations"),
            fix_label="Service-Details ergänzen",
            priority=2,
        ))
    # ADR-129 PR N2 (re-audit B-3): the AVV § 2 else-branch renders this id —
    # it must be registered or the marker degrades to a bare checkbox.
    if not any(s.get("data_categories") for s in services_detected):
        hints.append(GapHint(
            id="avv_data_categories_missing",
            severity="RECOMMENDED",
            article="DSGVO Art. 28 Abs. 3 Satz 1",
            doc_affected=["AVV"],
            description="Kein Service liefert Datenkategorien aus dem Graph",
            description_en="No service provides data categories from the graph",
            field="data_categories",
            gap_reason="No service provides data_categories from graph — AVV § 2 description of data types incomplete.",
            affected_docs=["AVV"],
            fix_url=_url(project_name, "integrations"),
            fix_label="Service-Details ergänzen",
            priority=2,
        ))
    return hints


def _check_vvt_gaps(services_detected: list[dict], project_name: str) -> list[GapHint]:
    """VVT-specific gaps: purpose and legal_basis from graph Service nodes."""
    hints = []
    # purpose: _default_purpose() covers all known categories — only gap if no category AND no explicit purpose
    no_purpose = [
        s for s in services_detected
        if not s.get("processing_purpose") and not s.get("category")
    ]
    if no_purpose:
        names = ", ".join(s.get("name", "?") for s in no_purpose[:5])
        hints.append(GapHint(
            id="vvt_purpose_missing",
            severity="RECOMMENDED",
            article="DSGVO Art. 30 Abs. 1 lit. b; Art. 13 Abs. 1 lit. c; Art. 28 Abs. 3",
            doc_affected=["VVT", "AVV", "Datenschutzerklärung"],
            description=f"{len(no_purpose)} Service(s) ohne Verarbeitungszweck: {names}",
            description_en=f"{len(no_purpose)} service(s) without a processing purpose: {names}",
            field="processing_purpose",
            gap_reason=f"Services without processing_purpose or category — no fallback possible: {names}.",
            affected_docs=["VVT"],
            fix_url=_url(project_name, "integrations"),
            fix_label="Service-Kategorien ergänzen",
            priority=2,
        ))
    # legal_basis comes from Q_META: HAS_CATEGORY→ServiceCategory→SUBJECT_TO_CONTROL[legal_basis].
    # Null only for services whose HAS_CATEGORY edge is absent (uncatalogued integrations).
    no_legal_basis = [s for s in services_detected if not s.get("legal_basis")]
    if no_legal_basis:
        names = ", ".join(s.get("name", "?") for s in no_legal_basis[:5])
        hints.append(GapHint(
            id="vvt_legal_basis_missing",
            severity="RECOMMENDED",
            article="DSGVO Art. 6 Abs. 1; Art. 30 Abs. 1 lit. a; Art. 13 Abs. 1 lit. c",
            doc_affected=["VVT", "Datenschutzerklärung"],
            description=f"Rechtsgrundlage fehlt im Graph für: {names}",
            description_en=f"Legal basis missing in the graph for: {names}",
            field="legal_basis",
            gap_reason=f"Services without legal_basis in graph — VVT cannot state legal ground: {names}.",
            affected_docs=["VVT"],
            fix_url=_url(project_name, "integrations"),
            fix_label="Service-Rechtsgrundlagen ergänzen",
            priority=2,
        ))
    # ADR-129 PR N2 (re-audit B-3): the VVT per-activity cells render these two ids
    # (PR 14) — unregistered they degrade to a bare checkbox WITHOUT the
    # Art. 30 Abs. 1 lit. c citation the cell exists to carry. Per-service
    # condition mirrors legal_basis: one service without the value renders one
    # marker in its row.
    no_data_subjects = [s for s in services_detected if not s.get("data_subjects")]
    if no_data_subjects:
        names = ", ".join(s.get("name", "?") for s in no_data_subjects[:5])
        hints.append(GapHint(
            id="vvt_data_subjects_missing",
            severity="RECOMMENDED",
            article="DSGVO Art. 30 Abs. 1 lit. c",
            doc_affected=["VVT"],
            description=f"Betroffenen-Kategorien fehlen im Graph für: {names}",
            description_en=f"Data-subject categories missing in the graph for: {names}",
            field="data_subjects",
            gap_reason=f"Services without data_subjects in graph — VVT Art. 30(1)(c) categories of data subjects incomplete: {names}.",
            affected_docs=["VVT"],
            fix_url=_url(project_name, "integrations"),
            fix_label="Service-Details ergänzen",
            priority=2,
        ))
    no_data_categories = [s for s in services_detected if not s.get("data_categories")]
    if no_data_categories:
        names = ", ".join(s.get("name", "?") for s in no_data_categories[:5])
        hints.append(GapHint(
            id="vvt_data_categories_missing",
            severity="RECOMMENDED",
            article="DSGVO Art. 30 Abs. 1 lit. c",
            doc_affected=["VVT"],
            description=f"Datenkategorien fehlen im Graph für: {names}",
            description_en=f"Data categories missing in the graph for: {names}",
            field="data_categories",
            gap_reason=f"Services without data_categories in graph — VVT Art. 30(1)(c) categories of personal data incomplete: {names}.",
            affected_docs=["VVT"],
            fix_url=_url(project_name, "integrations"),
            fix_label="Service-Details ergänzen",
            priority=2,
        ))
    # ADR-110/ADR-129 PR N2: the payment data-categories cell renders this id when
    # the PSP integration mode is `unknown` (VVT + AVV § 2) — register it so the
    # marker carries citation + fix link instead of a bare checkbox. Condition
    # mirrors payment_mode.resolve_payment_categories (is_gap ⇔ mode == unknown).
    from src.documents.builders.common.payment_mode import PAYMENT_MODE_UNKNOWN
    mode_unknown = [
        s for s in services_detected
        if s.get("integration_mode") == PAYMENT_MODE_UNKNOWN
    ]
    if mode_unknown:
        names = ", ".join(s.get("name", "?") for s in mode_unknown[:5])
        hints.append(GapHint(
            id="payment_integration_mode_unknown",
            severity="RECOMMENDED",
            article="DSGVO Art. 30 Abs. 1 lit. c; Art. 28 Abs. 3 Satz 1",
            doc_affected=["VVT", "AVV"],
            description=f"Zahlungs-Integrationsart nicht verifiziert für: {names}",
            description_en=f"Payment integration mode not verified for: {names}",
            field="integration_mode",
            gap_reason=f"Payment integration mode unknown — data categories depend on delegated vs merchant-side integration: {names}.",
            affected_docs=["VVT", "AVV"],
            fix_url=_url(project_name, "integrations"),
            fix_label="Integrationsart prüfen",
            priority=2,
        ))
    return hints


def _check_dsfa_gaps(services_detected: list[dict], project_name: str) -> list[GapHint]:
    """DSFA-specific gaps: data subjects from graph Service nodes."""
    hints = []
    if not any(s.get("data_subjects") for s in services_detected):
        hints.append(GapHint(
            id="dsfa_data_subjects_missing",
            severity="RECOMMENDED",
            article="DSGVO Art. 35 Abs. 7 lit. a",
            doc_affected=["DSFA"],
            description="Kein Service liefert Betroffenen-Kategorien aus dem Graph",
            description_en="No service provides data-subject categories from the graph",
            field="data_subjects",
            gap_reason="No service provides data_subjects — DSFA Art. 35(7)(a) description of data subjects incomplete.",
            affected_docs=["DSFA"],
            fix_url=_url(project_name, "integrations"),
            fix_label="Service-Details ergänzen",
            priority=2,
        ))
    return hints


def _check_ai_gaps(config: dict, services_detected: list[dict], project_name: str) -> list[GapHint]:
    """EU-AI-Act deployer-input gaps from ai_config (PR-B Gate 4).

    Registers the 8 ai_config gap_ids so their inline_gap_marker() in the KI
    templates resolves to a clickable /ai deep-link instead of a bare ✏️.
    Emitted ONLY when AI services are actually detected — mirrors the KI-document
    gating in document_architect: with no AI services the four KI docs don't render,
    so their markers would never resolve and the gaps would be false positives.

    project_level fields → one gap each. per_service fields share ONE gap_id per
    field across all services (the template marker id is not service-specific); the
    gap is emitted when ANY detected AI service leaves that field empty.
    """
    from src.graph.graph_client import is_ai_service

    ai_services = [s for s in services_detected if is_ai_service(s)]
    if not ai_services:
        return []

    hints: list[GapHint] = []
    ai_cfg = config.get("ai_config") or {}
    project_level = ai_cfg.get("project_level") or {}
    per_service = ai_cfg.get("per_service") or {}

    # ── project-level (3) ──────────────────────────────────────────────────
    if not project_level.get("operative_responsible"):
        hints.append(GapHint(
            id="ai_act_operative_responsible_missing",
            severity="RECOMMENDED",
            article="EU AI Act Art. 26",
            doc_affected=["AI_Act_Manifest"],
            description="Operative KI-Verantwortung (benannte Person)",
            description_en="Operational AI responsibility (named person)",
            field="ai_config.project_level.operative_responsible",
            gap_reason="operative_responsible not set in ai_config — AI-Act manifest §1 role assignment incomplete.",
            affected_docs=["AI_Act_Manifest"],
            fix_url=_url(project_name, "ai"),
            fix_label="KI-Verantwortung ergänzen",
            priority=2,
        ))
    if not project_level.get("tech_responsible"):
        hints.append(GapHint(
            id="ai_act_tech_responsible_missing",
            severity="RECOMMENDED",
            article="EU AI Act Art. 26",
            doc_affected=["AI_Act_Manifest"],
            description="Technische KI-Verantwortung (benannte Person)",
            description_en="Technical AI responsibility (named person)",
            field="ai_config.project_level.tech_responsible",
            gap_reason="tech_responsible not set in ai_config — AI-Act manifest §1 role assignment incomplete.",
            affected_docs=["AI_Act_Manifest"],
            fix_url=_url(project_name, "ai"),
            fix_label="KI-Verantwortung ergänzen",
            priority=2,
        ))
    # ADR-124: ai_literacy_measures (Art. 4) replaces ki_policy_review_date. Tri-state:
    # only `is None` (unset) is a gap — an explicit False ("not yet done") is a valid
    # answer the template surfaces as a compliance note, not a missing-input gap.
    if project_level.get("ai_literacy_measures") is None:
        hints.append(GapHint(
            id="ai_literacy_measures_missing",
            severity="RECOMMENDED",
            article="EU AI Act Art. 4",
            doc_affected=["AI_Act_Manifest", "KI_Policy"],
            description="KI-Kompetenzmaßnahmen (AI Literacy)",
            description_en="AI literacy measures (Art. 4)",
            field="ai_config.project_level.ai_literacy_measures",
            gap_reason="ai_literacy_measures not set in ai_config — Art. 4 AI-literacy declaration missing.",
            affected_docs=["AI_Act_Manifest", "KI_Policy"],
            fix_url=_url(project_name, "ai"),
            fix_label="KI-Kompetenz angeben",
            priority=2,
        ))

    # ── per-service (6) — one gap_id per field; emit if ANY AI service lacks it ──
    # ADR-124: model + purpose added (required); review_date removed; nutzergruppen→
    # user_groups, grenzen→usage_limits. Article strings corrected per legal cross-read
    # (training_data = DSGVO not Art.10/provider; logging = Art.26(6); model = Art.50).
    # training_data/logging are tri-state bool → only `is None` is a gap (an explicit
    # False is a valid answer, NOT a missing-input gap). String fields: empty/None → gap.
    _TRISTATE_FIELDS = {"training_data", "logging"}
    per_service_fields = [
        ("model", "ki_system_modell_version_missing", "EU AI Act Art. 50 / DSGVO Art. 13", "Modell / Version des KI-Systems", "Model / version of the AI system", 2),
        ("purpose", "ki_system_purpose_missing", "EU AI Act Art. 6 / Anhang III", "Einsatzzweck des KI-Systems", "Purpose of the AI system", 2),
        ("user_groups", "ki_system_user_groups_missing", "DSGVO Art. 30", "Nutzergruppen des KI-Systems", "User groups of the AI system", 2),
        ("usage_limits", "ki_system_usage_limits_missing", "EU AI Act Art. 26(1)", "Grenzen des KI-Systems", "Limits of the AI system", 2),
        ("training_data", "ki_system_training_data_missing", "DSGVO Art. 5/6", "Trainings-/Fine-Tuning-Daten", "Training/fine-tuning data", 2),
        ("logging", "ki_system_logging_missing", "EU AI Act Art. 26(6)", "Protokollierung (Logging)", "Logging", 2),
    ]
    for fld, gid, article, desc, desc_en, prio in per_service_fields:
        def _is_missing(svc_cfg: dict, _fld: str = fld) -> bool:
            value = svc_cfg.get(_fld)
            if _fld in _TRISTATE_FIELDS:
                return value is None          # explicit False is an answer, not a gap
            return not value                  # string: empty / None → gap
        missing = [
            s.get("name", "?") for s in ai_services
            if _is_missing(per_service.get(s.get("name")) or {})
        ]
        if missing:
            names = ", ".join(missing[:5])
            hints.append(GapHint(
                id=gid,
                severity="RECOMMENDED",
                article=article,
                doc_affected=["KI_System_Dokumentation"],
                description=f"{desc} fehlt für: {names}",
                description_en=f"{desc_en} missing for: {names}",
                field=f"ai_config.per_service.{fld}",
                gap_reason=f"{fld} not set in ai_config.per_service for: {names}.",
                affected_docs=["KI_System_Dokumentation"],
                fix_url=_url(project_name, "ai"),
                fix_label="KI-System-Angaben ergänzen",
                priority=prio,
            ))
    return hints


def _check_repo_extraction_gaps(extraction_summary: dict | None, project_name: str) -> list[GapHint]:
    hints = []
    if not extraction_summary or extraction_summary.get("extractions_count", 0) == 0:
        hints.append(GapHint(
            id="repo_legal_docs_missing",
            severity="RECOMMENDED",
            article="",
            doc_affected=["Impressum", "Datenschutzerklärung"],
            description="Keine Rechts-Artefakte im Repo (privacy.html, impressum.*)",
            description_en="No legal artifacts in the repository (privacy.html, impressum.*)",
            field="repo_legal_docs",
            gap_reason="No legal artifacts found in repo (privacy.html, impressum.*, DPA.*). Fields must be entered manually.",
            affected_docs=["Impressum", "Datenschutzerklärung"],
            fix_url=_url(project_name, "company"),
            fix_label="Enter details manually",
            priority=3,
        ))
    return hints


# ── Orchestration ──────────────────────────────────────────────────────────────

def analyze_gaps(
    project_name: str,
    config: dict,
    setup: dict | None,
    retention_policies: list,
    services_detected: list[dict],
    extraction_summary: dict | None = None,
) -> list[GapHint]:
    """Run all gap detectors and return a combined, priority-sorted hint list."""
    hints: list[GapHint] = []
    hints.extend(_check_company_gaps(config, project_name))
    hints.extend(_check_hosting_gaps(setup, project_name))
    hints.extend(_check_retention_gaps(retention_policies, project_name))
    hints.extend(_check_avv_required_gaps(config, services_detected, project_name))
    hints.extend(_check_service_gaps(services_detected, project_name))
    hints.extend(_check_vvt_gaps(services_detected, project_name))
    hints.extend(_check_dsfa_gaps(services_detected, project_name))
    hints.extend(_check_ai_gaps(config, services_detected, project_name))
    hints.extend(_check_repo_extraction_gaps(extraction_summary, project_name))
    hints.sort(key=lambda h: (_severity_order(h.severity), h.id or h.field))
    return hints


def top_n_actions(hints: list[GapHint], n: int = 3) -> list[GapHint]:
    """Return the top N highest-priority hints for the report summary block."""
    return hints[:n]


def load_retention_policies(project_name: str) -> list[dict]:
    """Load retention_policies rows for a project from Supabase."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        return []
    try:
        import psycopg2
        import psycopg2.extras
        with psycopg2.connect(db_url) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM retention_policies WHERE project_name = %s",
                    (project_name,),
                )
                return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        logger.warning("Could not load retention_policies for %s: %s", project_name, e)
        return []
