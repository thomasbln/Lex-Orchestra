from __future__ import annotations

import logging
from dataclasses import dataclass

from src.documents.builders.base import DocumentBuilder
from src.documents.content_models import BuildContext
from src.scanner.gap_analyzer import GapHint, _severity_order, top_n_actions

logger = logging.getLogger(__name__)


_RISK_LABELS: dict[str, str] = {
    "gpai":    "GPAI — General Purpose AI (EU AI Act Art. 51)",
    "high":    "HIGH RISK (EU AI Act Annex III)",
    "limited": "LIMITED RISK (EU AI Act Art. 50)",
    "minimal": "MINIMAL RISK",
}

_USECASE_LABELS: dict[str, tuple[str, str, str]] = {
    "hr_recruitment_screening":     ("HR-Recruiting / Bewerbungsauswahl", "HIGH RISK", "Annex III Nr. 4"),
    "credit_scoring":               ("Kredit-Scoring", "HIGH RISK", "Annex III Nr. 5"),
    "education_assessment":         ("Bildungsbewertung", "HIGH RISK", "Annex III Nr. 3"),
    "healthcare_decision":          ("Medizinische Entscheidung", "HIGH RISK", "Annex III Nr. 2"),
    "biometric_categorization":     ("Biometrische Identifikation", "PROHIBITED", "Art. 5"),
    "critical_infrastructure_mgmt": ("Kritische Infrastruktur", "HIGH RISK", "Annex III Nr. 2"),
    "law_enforcement_ai":           ("Strafverfolgung", "HIGH RISK", "Annex III Nr. 6"),
    "customer_service_chatbot":     ("Kundenservice-Chatbot", "LIMITED RISK", "Art. 50"),
    "ai_content_generator":         ("Content-Generierung", "LIMITED RISK", "Art. 50"),
    "ai_assistant_general":         ("Allgemeiner KI-Assistent", "LIMITED RISK", "Art. 50"),
}

# Mixed-case keys — match generate_all() output. No .lower() needed.
_DOC_LABELS: dict[str, str] = {
    "AVV":                     "AVV — Auftragsverarbeitungsvertrag (Art. 28 DSGVO)",
    "TOM":                     "TOM — Technische und Organisatorische Maßnahmen (Art. 32 DSGVO)",
    "VVT":                     "VVT — Verzeichnis von Verarbeitungstätigkeiten (Art. 30 DSGVO)",
    "SCC":                     "SCC — Standardvertragsklauseln für Drittlandtransfer (Art. 46 DSGVO)",
    "DSFA":                    "DSFA — Datenschutz-Folgenabschätzung (Art. 35 DSGVO)",
    "AI_Act_Manifest":         "EU AI Act Risiko-Manifest",
    "KI_Policy":               "KI-Nutzungsrichtlinie (EU AI Act Art. 4 + 26)",
    "KI_System_Dokumentation": "KI-System-Dokumentation (EU AI Act Art. 11)",
}

_RISK_DESCRIPTIONS: dict[str, str] = {
    "PII_IN_LLM_CONTEXT": "Personenbezogene Daten könnten in den KI-Kontext gelangen (DSGVO Art. 25)",
    "PII_IN_LOGS":        "PII in Monitoring-Logs erkannt — Log-Scrubbing empfohlen (DSGVO Art. 32)",
    "NO_AI_AUDIT_TRAIL":  "Kein Audit Trail für KI-Entscheidungen — Langfuse empfohlen (EU AI Act Art. 12)",
    "MISSING_AVV":        "Auftragsverarbeitungsvertrag fehlt für erkannte Sub-Prozessoren",
    "MISSING_SCC":        "Standardvertragsklauseln für Drittlandtransfer fehlen",
}

_SIGNAL_LABELS: dict[str, str] = {
    "ai_usage":           "KI-API-Nutzung erkannt (OpenAI, Anthropic o.ä.)",
    "personal_data":      "Verarbeitung personenbezogener Daten erkannt",
    "system_prompt":      "System-Prompt gefunden → KI-Verwendungszweck klassifiziert",
    "system_prompt_role": "KI-Verwendungszweck automatisch klassifiziert",
    "decision_logic":     "Automatisierte Entscheidungslogik erkannt",
    "secret_detected":    "⚠️ Mögliche Credentials/API-Keys im Code erkannt",
    "autonomy":           "Autonomes KI-Verhalten erkannt",
    "user_interaction":   "Nutzerinteraktion mit KI erkannt",
}


@dataclass
class TopActionRow:
    index: int
    fix_label: str
    icon: str
    gap_reason: str
    affected_docs: list[str]
    fix_url: str


@dataclass
class SignalRow:
    label: str
    confidence_pct: int


@dataclass
class ActiveRiskRow:
    id: str
    description: str


@dataclass
class UseCaseRiskRow:
    level_upper: str
    article: str
    annex_iii_nr: str
    title: str
    deployer_action: str


@dataclass
class RepoExtractionsBlock:
    count_ok: int
    count_total: int
    count_merged: int
    count_skipped: int
    source_files: list[str]
    merged_fields: list[str]


@dataclass
class AllGapRow:
    index: int
    fix_label: str
    severity_label: str
    gap_reason: str
    affected_docs: list[str]
    fix_url: str


@dataclass
class Ebene0Breakdown:
    """ADR-121 Ebene-0 full provenance breakdown — the scan-report's own anatomy.

    Unlike the per-doc head box, the scan report carries the complete N / X /
    Differenz / other split (it is the natural home for it). other_services is
    surfaced explicitly — under-detection stays visible, never silently dropped.
    """
    n: int
    x: int
    differenz: int
    processors: list[str]
    tooling: list[str]
    other_services: list[str]
    x_drittland: int
    third_country: list[str]


@dataclass
class ScanReportContentModel:
    """Every field here will be rendered by scan_report.md.j2. No extras."""
    project_name: str
    run_id_short: str
    run_date: str
    top_actions: list[TopActionRow]
    service_names: list[str]
    top_signals: list[SignalRow]
    usecase_display: str | None
    repo_extractions: RepoExtractionsBlock | None
    risk_display: str
    active_risks_count: int
    controls_count: int
    active_risks: list[ActiveRiskRow]
    usecase_high_risk_blocks: list[UseCaseRiskRow]
    generated_doc_labels: list[str]
    generated_doc_count: int
    immediate_actions: list[str]
    short_term_actions: list[str]
    long_term_actions: list[str]
    all_gaps: list[AllGapRow]
    all_gaps_count: int
    # Pre-DSB sprint 1.5c: transparency for intentionally-omitted KI docs.
    # None when AI services were detected (or KI docs were generated).
    ki_docs_skipped_note: str | None
    # ADR-121 Ebene-0: full provenance breakdown. None when unavailable.
    ebene0: Ebene0Breakdown | None


class ScanReportBuilder(DocumentBuilder):
    """Builds ScanReportContentModel from graph + gap_hints + generated_doc_types.

    Called AFTER generate_all() — receives the list of actually generated documents.
    Signature extends the 5-arg ABC with kw-only args for scan-report specifics.
    """

    def build(
        self,
        graph_result: dict,
        reasoning_result: dict,
        config: dict,
        gap_hints: list[GapHint],
        ctx: BuildContext,
        *,
        risk_signals: list[dict] | None = None,
        repo_extraction_summary: dict | None = None,
        generated_doc_types: list[str] | None = None,
        provenance: dict | None = None,
    ) -> ScanReportContentModel:
        signals = risk_signals or []
        ebene0 = None
        if provenance and provenance.get("n", 0):
            ebene0 = Ebene0Breakdown(
                n=provenance["n"], x=provenance["x"], differenz=provenance["differenz"],
                processors=provenance["processors"], tooling=provenance["tooling"],
                other_services=provenance["other_services"],
                x_drittland=provenance["x_drittland"], third_country=provenance["third_country"],
            )
        extractions = repo_extraction_summary or {}
        gen_types = generated_doc_types or []

        # CRITICAL: top_n_actions() does not sort — it slices hints[:n].
        # gap_hints from _gap_registry.values() are insertion-order (detector-order),
        # not severity-order. Sort here so REQUIRED gaps always come first.
        gap_hints_sorted = sorted(
            gap_hints,
            key=lambda h: (_severity_order(h.severity), h.id or h.field or ""),
        )

        crit_count = sum(1 for g in gap_hints_sorted if g.severity == "REQUIRED")
        logger.info("Gap analysis: %d hints (%d required)", len(gap_hints_sorted), crit_count)

        top_3 = top_n_actions(gap_hints_sorted, 3)
        top_actions = [
            TopActionRow(
                index=i + 1,
                fix_label=h.fix_label,
                icon=self._severity_icon(h.severity),
                gap_reason=h.gap_reason,
                affected_docs=h.affected_docs,
                fix_url=h.fix_url,
            )
            for i, h in enumerate(top_3)
        ]

        services = graph_result.get("services", [])
        service_names = [s.get("name", s.get("canonical_name", "?")) for s in services]

        # Mirror the gating rule in document_architect.generate_all: KI docs render
        # only when AI services are detected. Surface the omission transparently
        # rather than letting the absence look like an oversight.
        ai_services_detected = any(
            s.get("ai_act_relevant") or s.get("category") == "ai_llm" for s in services
        )
        _KI_DOC_TYPES = {"AI_Act_Manifest", "KI_Policy", "KI_System_Dokumentation", "DSFA"}
        ki_docs_skipped_note = None
        if not ai_services_detected and not (_KI_DOC_TYPES & set(gen_types)):
            ki_docs_skipped_note = (
                "KI-spezifische Dokumente (KI-Policy, KI-System-Dokumentation, DSFA, "
                "EU-AI-Act-Manifest) wurden bewusst ausgelassen — im Code wurden keine "
                "KI-Dienste erkannt. Eine DSFA oder ein AI-Act-Manifest ohne erkannte "
                "KI-Verarbeitung würde Pflichten suggerieren, die hier nicht bestehen."
            )

        top_signal_dicts = sorted(
            signals, key=lambda s: s.get("confidence", 0), reverse=True
        )[:5]
        top_signals = [
            SignalRow(
                label=_SIGNAL_LABELS.get(s.get("signal_type", ""), s.get("signal_type", "?")),
                confidence_pct=int(s.get("confidence", 0) * 100),
            )
            for s in top_signal_dicts
        ]

        usecase_display = self._usecase_display(config)
        repo_extractions = self._repo_extractions_block(extractions)

        overall_risk = graph_result.get("overall_risk", "—")
        usecase_risks_from_graph = graph_result.get("usecase_risks", [])
        risk_display = self._risk_display(overall_risk, usecase_risks_from_graph)

        active_risks_raw = graph_result.get("active_risks", [])
        active_risks = [
            ActiveRiskRow(id=r, description=_RISK_DESCRIPTIONS.get(r, r))
            for r in active_risks_raw
        ]

        usecase_high_risk_blocks = [
            UseCaseRiskRow(
                level_upper=(uc.get("risk_level") or "HIGH").upper(),
                article=uc.get("article", "Art. 6"),
                annex_iii_nr=str(uc.get("annex_iii_nr", "?")),
                title=uc.get("title_de") or uc.get("type", "?"),
                deployer_action=uc.get("deployer_action", ""),
            )
            for uc in usecase_risks_from_graph
            if (uc.get("risk_level") or "").lower() in ("high", "unacceptable")
        ]

        generated_doc_labels = [_DOC_LABELS.get(dt, dt) for dt in gen_types]

        usecase_type = config.get("ai_usecase_type")
        immediate_actions, short_term_actions, long_term_actions = self._action_lists(
            gap_hints_sorted, active_risks_raw, usecase_type,
        )

        all_gaps = [
            AllGapRow(
                index=i + 1,
                fix_label=h.fix_label,
                severity_label=self._severity_label(h.severity),
                gap_reason=h.gap_reason,
                affected_docs=h.affected_docs,
                fix_url=h.fix_url,
            )
            for i, h in enumerate(gap_hints_sorted)
        ]

        return ScanReportContentModel(
            project_name=ctx.project_name,
            run_id_short=ctx.run_id[:8],
            run_date=ctx.generation_date,
            top_actions=top_actions,
            service_names=service_names,
            top_signals=top_signals,
            usecase_display=usecase_display,
            repo_extractions=repo_extractions,
            risk_display=risk_display,
            active_risks_count=len(active_risks_raw),
            controls_count=len(graph_result.get("controls", [])),
            active_risks=active_risks,
            usecase_high_risk_blocks=usecase_high_risk_blocks,
            generated_doc_labels=generated_doc_labels,
            generated_doc_count=len(gen_types),
            immediate_actions=immediate_actions,
            short_term_actions=short_term_actions,
            long_term_actions=long_term_actions,
            all_gaps=all_gaps,
            all_gaps_count=len(gap_hints_sorted),
            ki_docs_skipped_note=ki_docs_skipped_note,
            ebene0=ebene0,
        )

    # ─── Helpers ───────────────────────────────────────────────────────────────

    def _severity_icon(self, severity: str) -> str:
        return {"REQUIRED": "🔴", "RECOMMENDED": "🟡"}.get(severity, "⚪")

    def _severity_label(self, severity: str) -> str:
        return {"REQUIRED": "🔴 erforderlich", "RECOMMENDED": "🟡 empfohlen"}.get(severity, "⚪ optional")

    def _risk_display(self, overall_risk: str, usecase_risks: list[dict]) -> str:
        base = _RISK_LABELS.get(
            (overall_risk or "").lower(),
            overall_risk or "Nicht klassifiziert",
        )
        high_ucs = [
            uc for uc in usecase_risks
            if (uc.get("risk_level") or "").lower() in ("high", "unacceptable")
        ]
        if high_ucs and (overall_risk or "").lower() not in ("high", "unacceptable"):
            uc = high_ucs[0]
            lvl = (uc.get("risk_level") or "high").upper()
            return (
                f"{lvl} RISK (EU AI Act {uc.get('article', 'Art. 6')}, "
                f"Annex III Nr. {uc.get('annex_iii_nr', '?')})"
            )
        return base

    def _usecase_display(self, config: dict) -> str | None:
        usecase_type = config.get("ai_usecase_type")
        if not usecase_type or usecase_type not in _USECASE_LABELS:
            return None
        label, risk, article = _USECASE_LABELS[usecase_type]
        confidence = config.get("ai_usecase_confidence")
        conf_str = f" (Konfidenz: {confidence:.0%})" if confidence else ""
        return f"{label} — {risk} ({article}){conf_str}"

    def _repo_extractions_block(self, extractions: dict) -> RepoExtractionsBlock | None:
        if not extractions.get("extractions_count", 0):
            return None
        return RepoExtractionsBlock(
            count_ok=extractions.get("extractions_successful", 0),
            count_total=extractions.get("extractions_count", 0),
            count_merged=extractions.get("fields_merged", 0),
            count_skipped=extractions.get("fields_skipped", 0),
            source_files=extractions.get("source_files", []),
            merged_fields=extractions.get("merged_fields", []),
        )

    def _action_lists(
        self,
        gap_hints_sorted: list[GapHint],
        active_risks: list[str],
        usecase_type: str | None,
    ) -> tuple[list[str], list[str], list[str]]:
        immediate: list[str] = [
            "Alle generierten Entwürfe durch Rechtsberater prüfen lassen",
        ]
        for h in gap_hints_sorted:
            if h.severity == "REQUIRED" and h.fix_label not in immediate:
                immediate.append(h.fix_label)

        short_term: list[str] = []
        if usecase_type and "hr_recruitment" in usecase_type:
            short_term.extend([
                "HR-KI-System bei EU-Datenbank registrieren (AI Act Annex III)",
                "Konformitätsbewertung durch benannte Stelle durchführen",
                "Grundrechte-Folgenabschätzung dokumentieren",
                "DSFA vor Inbetriebnahme abschließen",
            ])
        if "NO_AI_AUDIT_TRAIL" in active_risks:
            short_term.append("Langfuse (oder gleichwertiges Tool) für AI Act Art. 12 Audit Trail integrieren")
        if "PII_IN_LLM_CONTEXT" in active_risks:
            short_term.append("UUID-Only Pattern implementieren — PII nie direkt in LLM-Kontext")
        for h in gap_hints_sorted:
            if h.severity == "RECOMMENDED" and h.fix_label not in short_term:
                short_term.append(h.fix_label)

        long_term: list[str] = [
            "KI-Nutzungsrichtlinie intern kommunizieren und schulen (AI Act Art. 4)",
            "Regelmäßigen Review-Zyklus für alle Dokumente einplanen (mind. jährlich)",
            "Datenschutzerklärung auf Website aktualisieren",
        ]
        return immediate, short_term, long_term
