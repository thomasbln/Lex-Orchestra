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

# EN close-out (scan-report package): EN twin — lex-authored class-B labels.
# Guard test asserts key parity with the DE dict.
_USECASE_LABELS_EN: dict[str, tuple[str, str, str]] = {
    "hr_recruitment_screening":     ("HR recruiting / applicant screening", "HIGH RISK", "Annex III no. 4"),
    "credit_scoring":               ("Credit scoring", "HIGH RISK", "Annex III no. 5"),
    "education_assessment":         ("Educational assessment", "HIGH RISK", "Annex III no. 3"),
    "healthcare_decision":          ("Medical decision-making", "HIGH RISK", "Annex III no. 2"),
    "biometric_categorization":     ("Biometric identification", "PROHIBITED", "Art. 5"),
    "critical_infrastructure_mgmt": ("Critical infrastructure", "HIGH RISK", "Annex III no. 2"),
    "law_enforcement_ai":           ("Law enforcement", "HIGH RISK", "Annex III no. 6"),
    "customer_service_chatbot":     ("Customer service chatbot", "LIMITED RISK", "Art. 50"),
    "ai_content_generator":         ("Content generation", "LIMITED RISK", "Art. 50"),
    "ai_assistant_general":         ("General AI assistant", "LIMITED RISK", "Art. 50"),
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

# Labels match the EN doc H1s (en/*.md.j2) so the annex list names what the
# reader actually receives — DPA / RoPA / DPIA acronyms per the H1s
# (unification decision 2026-07-28; dict KEYS stay the internal doc types).
_DOC_LABELS_EN: dict[str, str] = {
    "AVV":                     "DPA — Data Processing Agreement (Art. 28 GDPR)",
    "TOM":                     "TOM — Technical and Organisational Measures (Art. 32 GDPR)",
    "VVT":                     "RoPA — Record of Processing Activities (Art. 30 GDPR)",
    "SCC":                     "SCC — Standard Contractual Clauses for third-country transfers (Art. 46 GDPR)",
    "DSFA":                    "DPIA — Data Protection Impact Assessment (Art. 35 GDPR)",
    "AI_Act_Manifest":         "EU AI Act Risk Manifest",
    "KI_Policy":               "AI Usage Policy (EU AI Act Art. 4 + 26)",
    "KI_System_Dokumentation": "AI System Documentation (EU AI Act Art. 11)",
}

_RISK_DESCRIPTIONS: dict[str, str] = {
    "PII_IN_LLM_CONTEXT": "Personenbezogene Daten könnten in den KI-Kontext gelangen (DSGVO Art. 25)",
    "PII_IN_LOGS":        "PII in Monitoring-Logs erkannt — Log-Scrubbing empfohlen (DSGVO Art. 32)",
    "NO_AI_AUDIT_TRAIL":  "Kein Audit Trail für KI-Entscheidungen — Langfuse empfohlen (EU AI Act Art. 12)",
    "MISSING_AVV":        "Auftragsverarbeitungsvertrag fehlt für erkannte Sub-Prozessoren",
    "MISSING_SCC":        "Standardvertragsklauseln für Drittlandtransfer fehlen",
}

_RISK_DESCRIPTIONS_EN: dict[str, str] = {
    "PII_IN_LLM_CONTEXT": "Personal data could reach the AI context (GDPR Art. 25)",
    "PII_IN_LOGS":        "PII detected in monitoring logs — log scrubbing recommended (GDPR Art. 32)",
    "NO_AI_AUDIT_TRAIL":  "No audit trail for AI decisions — Langfuse recommended (EU AI Act Art. 12)",
    "MISSING_AVV":        "Data processing agreement missing for detected sub-processors",
    "MISSING_SCC":        "Standard contractual clauses for third-country transfers missing",
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

_SIGNAL_LABELS_EN: dict[str, str] = {
    "ai_usage":           "AI API usage detected (OpenAI, Anthropic, or similar)",
    "personal_data":      "Processing of personal data detected",
    "system_prompt":      "System prompt found → AI use case classified",
    "system_prompt_role": "AI use case classified automatically",
    "decision_logic":     "Automated decision logic detected",
    "secret_detected":    "⚠️ Possible credentials/API keys detected in code",
    "autonomy":           "Autonomous AI behaviour detected",
    "user_interaction":   "User interaction with AI detected",
}

# GapHint.affected_docs carries the German doc identifiers — render-boundary
# display maps (unification decision 2026-07-28: the affected column names the
# documents the reader actually holds; no raw underscore keys in user text).
# Complete key inventory (AST over gap_analyzer, 2026-07-28): AI_Act_Manifest,
# AVV, AVV § 1, AVV § 5, DSFA, Datenschutzerklärung, Impressum, KI_Policy,
# KI_System_Dokumentation, SCC, TOM, TOM § 1.1, VVT. TOM and Impressum stay;
# keys not in the map pass through unchanged.
_AFFECTED_DOC_EN: dict[str, str] = {
    "Datenschutzerklärung":     "Privacy policy",
    "AVV":                      "DPA",
    "VVT":                      "RoPA",
    "DSFA":                     "DPIA",
    "AVV § 1":                  "DPA § 1",
    "AVV § 5":                  "DPA § 5",
    "AI_Act_Manifest":          "EU AI Act Risk Manifest",
    "KI_Policy":                "AI Usage Policy",
    "KI_System_Dokumentation":  "AI System Documentation",
}

# DE display twin — readable German names for the underscore doc-type keys
# (matches the _DOC_LABELS name parts); everything else passes through.
_AFFECTED_DOC_DE: dict[str, str] = {
    "AI_Act_Manifest":          "EU AI Act Risiko-Manifest",
    "KI_Policy":                "KI-Nutzungsrichtlinie",
    "KI_System_Dokumentation":  "KI-System-Dokumentation",
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

    ``unclassified`` was called ``tooling`` until 2026-07-28 and was rendered as
    a fact ("development tools without independent data processing"). It never
    was one — see the rationale in ``graph_client._classify_provenance``.
    """
    n: int
    x: int
    differenz: int
    processors: list[str]
    unclassified: list[str]
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
        # EN close-out (analysis 2026-07-28, C4): the scan report follows
        # doc_language like every other builder — DE default unchanged.
        lang = config.get("doc_language", "de") or "de"
        en = lang == "en"
        signals = risk_signals or []
        ebene0 = None
        if provenance and provenance.get("n", 0):
            ebene0 = Ebene0Breakdown(
                n=provenance["n"], x=provenance["x"], differenz=provenance["differenz"],
                processors=provenance["processors"],
                unclassified=provenance["unclassified"],
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
                # Language-pure pick (B-2/L2 pattern): EN reads the _en twin,
                # never the German string — a site-count guard test keeps every
                # creation site carrying both.
                fix_label=(h.fix_label_en if en else h.fix_label),
                icon=self._severity_icon(h.severity),
                gap_reason=(h.gap_reason_en if en else h.gap_reason),
                affected_docs=self._affected_docs(h, lang),
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
                "AI-specific documents (AI policy, AI system documentation, DPIA, "
                "EU AI Act manifest) were deliberately omitted — no AI services were "
                "detected in the code. A DPIA or an AI Act manifest without detected "
                "AI processing would suggest obligations that do not exist here."
            ) if en else (
                "KI-spezifische Dokumente (KI-Policy, KI-System-Dokumentation, DSFA, "
                "EU-AI-Act-Manifest) wurden bewusst ausgelassen — im Code wurden keine "
                "KI-Dienste erkannt. Eine DSFA oder ein AI-Act-Manifest ohne erkannte "
                "KI-Verarbeitung würde Pflichten suggerieren, die hier nicht bestehen."
            )

        top_signal_dicts = sorted(
            signals, key=lambda s: s.get("confidence", 0), reverse=True
        )[:5]
        signal_labels = _SIGNAL_LABELS_EN if en else _SIGNAL_LABELS
        top_signals = [
            SignalRow(
                label=signal_labels.get(s.get("signal_type", ""), s.get("signal_type", "?")),
                confidence_pct=int(s.get("confidence", 0) * 100),
            )
            for s in top_signal_dicts
        ]

        usecase_display = self._usecase_display(config, lang)
        repo_extractions = self._repo_extractions_block(extractions)

        overall_risk = graph_result.get("overall_risk", "—")
        usecase_risks_from_graph = graph_result.get("usecase_risks", [])
        risk_display = self._risk_display(overall_risk, usecase_risks_from_graph, lang)

        active_risks_raw = graph_result.get("active_risks", [])
        risk_descriptions = _RISK_DESCRIPTIONS_EN if en else _RISK_DESCRIPTIONS
        active_risks = [
            ActiveRiskRow(id=r, description=risk_descriptions.get(r, r))
            for r in active_risks_raw
        ]

        usecase_high_risk_blocks = [
            UseCaseRiskRow(
                level_upper=(uc.get("risk_level") or "HIGH").upper(),
                article=uc.get("article", "Art. 6"),
                annex_iii_nr=str(uc.get("annex_iii_nr", "?")),
                # ADR-129 PR 12 (F8) pattern: doc-language title, honest DE
                # fallback (title_en is seeded 20/20 — the fallback is a guard,
                # not the expected path).
                title=((uc.get("title_en") if en else None)
                       or uc.get("title_de") or uc.get("type", "?")),
                # Language-pure deployer obligation (B-2/L5 pattern): EN reads
                # deployer_action_en (seeded 20/20, wired via Q_USECASE_RISK);
                # a German value without its twin renders the honest pending
                # marker, never silent German.
                deployer_action=self._lang_field(uc, "deployer_action", lang) or "",
            )
            for uc in usecase_risks_from_graph
            if (uc.get("risk_level") or "").lower() in ("high", "unacceptable")
        ]

        doc_labels = _DOC_LABELS_EN if en else _DOC_LABELS
        generated_doc_labels = [doc_labels.get(dt, dt) for dt in gen_types]

        usecase_type = config.get("ai_usecase_type")
        immediate_actions, short_term_actions, long_term_actions = self._action_lists(
            gap_hints_sorted, active_risks_raw, usecase_type, lang,
        )

        all_gaps = [
            AllGapRow(
                index=i + 1,
                fix_label=(h.fix_label_en if en else h.fix_label),
                severity_label=self._severity_label(h.severity, lang),
                gap_reason=(h.gap_reason_en if en else h.gap_reason),
                affected_docs=self._affected_docs(h, lang),
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

    # B-2/L5 twin (see ai_act_builder._lang_text): the EN doc NEVER silently
    # shows German — a German value without its `_en` twin renders this marker.
    _TRANSLATION_PENDING_EN = "☐ translation pending (German version exists)"

    def _lang_field(self, row: dict, base: str, lang: str) -> str | None:
        """Language-pure field pick: EN → `_en` or pending-marker; DE → base."""
        if lang == "en":
            val = row.get(f"{base}_en")
            if val:
                return val
            return self._TRANSLATION_PENDING_EN if row.get(base) else None
        return row.get(base)

    def _affected_docs(self, h: GapHint, lang: str) -> list[str]:
        """affected_docs for display — both languages map the raw identifiers
        to readable doc names (_AFFECTED_DOC_EN / _AFFECTED_DOC_DE); unmapped
        keys pass through unchanged."""
        table = _AFFECTED_DOC_EN if lang == "en" else _AFFECTED_DOC_DE
        return [table.get(d, d) for d in h.affected_docs]

    def _severity_icon(self, severity: str) -> str:
        return {"REQUIRED": "🔴", "RECOMMENDED": "🟡"}.get(severity, "⚪")

    def _severity_label(self, severity: str, lang: str = "de") -> str:
        if lang == "en":
            return {"REQUIRED": "🔴 required", "RECOMMENDED": "🟡 recommended"}.get(severity, "⚪ optional")
        return {"REQUIRED": "🔴 erforderlich", "RECOMMENDED": "🟡 empfohlen"}.get(severity, "⚪ optional")

    def _risk_display(self, overall_risk: str, usecase_risks: list[dict], lang: str = "de") -> str:
        base = _RISK_LABELS.get(
            (overall_risk or "").lower(),
            overall_risk or ("Not classified" if lang == "en" else "Nicht klassifiziert"),
        )
        high_ucs = [
            uc for uc in usecase_risks
            if (uc.get("risk_level") or "").lower() in ("high", "unacceptable")
        ]
        if high_ucs and (overall_risk or "").lower() not in ("high", "unacceptable"):
            uc = high_ucs[0]
            lvl = (uc.get("risk_level") or "high").upper()
            nr_word = "no." if lang == "en" else "Nr."
            return (
                f"{lvl} RISK (EU AI Act {uc.get('article', 'Art. 6')}, "
                f"Annex III {nr_word} {uc.get('annex_iii_nr', '?')})"
            )
        return base

    def _usecase_display(self, config: dict, lang: str = "de") -> str | None:
        usecase_type = config.get("ai_usecase_type")
        labels = _USECASE_LABELS_EN if lang == "en" else _USECASE_LABELS
        if not usecase_type or usecase_type not in labels:
            return None
        label, risk, article = labels[usecase_type]
        confidence = config.get("ai_usecase_confidence")
        conf_word = "confidence" if lang == "en" else "Konfidenz"
        conf_str = f" ({conf_word}: {confidence:.0%})" if confidence else ""
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
        lang: str = "de",
    ) -> tuple[list[str], list[str], list[str]]:
        en = lang == "en"

        def _label(h: GapHint) -> str:
            return h.fix_label_en if en else h.fix_label

        immediate: list[str] = [
            "Have all generated drafts reviewed by legal counsel" if en
            else "Alle generierten Entwürfe durch Rechtsberater prüfen lassen",
        ]
        for h in gap_hints_sorted:
            if h.severity == "REQUIRED" and _label(h) not in immediate:
                immediate.append(_label(h))

        short_term: list[str] = []
        if usecase_type and "hr_recruitment" in usecase_type:
            short_term.extend([
                "Register the HR AI system in the EU database (AI Act Annex III)",
                "Carry out a conformity assessment via a notified body",
                "Document a fundamental rights impact assessment",
                "Complete the DPIA before putting the system into operation",
            ] if en else [
                "HR-KI-System bei EU-Datenbank registrieren (AI Act Annex III)",
                "Konformitätsbewertung durch benannte Stelle durchführen",
                "Grundrechte-Folgenabschätzung dokumentieren",
                "DSFA vor Inbetriebnahme abschließen",
            ])
        if "NO_AI_AUDIT_TRAIL" in active_risks:
            short_term.append(
                "Integrate Langfuse (or an equivalent tool) for the AI Act Art. 12 audit trail" if en
                else "Langfuse (oder gleichwertiges Tool) für AI Act Art. 12 Audit Trail integrieren"
            )
        if "PII_IN_LLM_CONTEXT" in active_risks:
            short_term.append(
                "Implement the UUID-only pattern — never put PII directly into the LLM context" if en
                else "UUID-Only Pattern implementieren — PII nie direkt in LLM-Kontext"
            )
        for h in gap_hints_sorted:
            if h.severity == "RECOMMENDED" and _label(h) not in short_term:
                short_term.append(_label(h))

        long_term: list[str] = [
            "Communicate and train the AI usage policy internally (AI Act Art. 4)",
            "Schedule a regular review cycle for all documents (at least annually)",
            "Update the privacy policy on the website",
        ] if en else [
            "KI-Nutzungsrichtlinie intern kommunizieren und schulen (AI Act Art. 4)",
            "Regelmäßigen Review-Zyklus für alle Dokumente einplanen (mind. jährlich)",
            "Datenschutzerklärung auf Website aktualisieren",
        ]
        return immediate, short_term, long_term
