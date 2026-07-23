from __future__ import annotations

from dataclasses import dataclass

from src.documents.builders.base import DocumentBuilder
from src.documents.builders.common.bfdi_footer import BfDICitation, collect_bfdi_citations
from src.documents.content_models import BuildContext, CompanyBlock, GapMarker
from src.documents.legal_basis_map import (
    derive_legal_basis_for_usecase,
    render_data_subjects,
    render_legal_basis,
)


@dataclass
class DSFAAIServiceRow:
    """AI service appearing in DSFA § Systembeschreibung."""
    name: str
    category: str | None
    purpose: str
    country: str | None
    gdpr_adequate: bool


@dataclass
class DSFAUseCaseBlock:
    """AI use case for DSFA § Beschreibung der Verarbeitung."""
    type: str
    title_de: str
    description_de: str | None
    risk_level: str
    article: str | None
    annex_iii_nr: str | None


@dataclass
class DSFARisksBlock:
    """Flags derived from active_risks. Each flag triggers a section in dsfa.md.j2."""
    pii_in_llm_context: bool
    rag_over_pii: bool
    pii_in_logs: bool
    no_ai_audit_trail: bool
    consent_management: bool


@dataclass
class DSFAStep2Block:
    """Schritt 2 — Notwendigkeit / Verhältnismäßigkeit / Datenminimierung (ADR-106 PR A4)."""
    notwendigkeit: str
    verhaeltnismaessigkeit: str
    datenminimierung: str


@dataclass
class DSFAStep4Row:
    """Schritt 4 — Maßnahmen with Cross-Ref to TOM-Control (ADR-106 PR A4)."""
    measure: str
    status: str
    control_ref: str | None  # e.g. "CON.1 (BSI)", "8.24 (ISO 27001)"


@dataclass
class DSFAStep5Block:
    """Schritt 5 — Art. 36 Konsultations-Logik (ADR-106 PR A5).

    No aufsichtsbehoerde field: the bundesland column/UI does not exist
    (audit F3/K22), so it was hard-None at every construction site — the
    template renders an honest gap sentence instead (ADR-129 PR N3).
    """
    konsultation_erforderlich: bool
    begruendung: str


@dataclass
class DSFADamageScenario:
    """Fraunhofer-DSFA-Handbuch §6.3 Schadensszenario — ADR-106 PR D6.

    Pro Gewährleistungsziel wird der konkrete Schadens-Fall beschrieben:
    Wer (Risikoquelle) macht was (Aktion), und welcher Schaden entsteht.
    """
    gewaehrleistungsziel: str   # z.B. "Vertraulichkeit"
    risikoquelle: str           # z.B. "Externer Angreifer (Hacker)"
    schaden: str                # z.B. "PII-Datenleck mit Identitätsdiebstahl"
    wahrscheinlichkeit: str     # "niedrig" | "mittel" | "hoch"
    schwere: str                # "niedrig" | "mittel" | "hoch"
    measure_refs: list[str]     # Cross-Refs auf Measure.id from PR D1


@dataclass
class DSFAContentModel:
    """Every field here will be rendered by dsfa.md.j2. No extras, no guesses."""
    company: CompanyBlock
    generation_date: str
    run_id: str
    warn_header_gaps: list
    zweck: str | GapMarker
    rechtsgrundlage: str | GapMarker
    data_subjects: str | GapMarker
    ai_services: list[DSFAAIServiceRow]
    ai_usecase: DSFAUseCaseBlock | None
    pii_services: list[str]
    risks: DSFARisksBlock
    triggered_by_high_risk_usecase: bool
    step2: DSFAStep2Block                  # ADR-106 PR A4
    step4: list[DSFAStep4Row]              # ADR-106 PR A4
    step5: DSFAStep5Block                  # ADR-106 PR A5
    bfdi_citations: list[BfDICitation]     # ADR-106 PR C5
    damage_scenarios: list[DSFADamageScenario]  # ADR-106 PR D6 — Fraunhofer §6.3


_AI_PURPOSE_BY_CATEGORY: dict[str, str] = {
    "ai_llm":        "KI-gestützte Textgenerierung und -verarbeitung",
    "ai_platform":   "KI-Plattformdienste und Modellinferenz",
    "vector_db":     "Vektordatenbank für Embedding-Speicherung (RAG)",
    "observability": "LLM-Observability und KI-Audit-Trail (EU AI Act Art. 12)",
}

_PII_CATEGORIES = frozenset({"analytics", "crm", "crm_support", "email"})


def _collect_dedup_subjects(services: list[dict]) -> list[str]:
    """Collect and deduplicate data_subjects values from a list of service dicts."""
    seen: dict[str, str] = {}
    for svc in services:
        raw = svc.get("data_subjects")
        if not raw:
            continue
        items = raw if isinstance(raw, list) else [raw]
        for item in items:
            key = str(item).strip().lower()
            if key and key not in seen:
                seen[key] = str(item).strip()
    return sorted(seen.values())


class DSFABuilder(DocumentBuilder):

    def build(
        self,
        graph_result: dict,
        reasoning_result: dict,
        config: dict,
        gap_hints: list,
        ctx: BuildContext,
        *,
        ai_usecase: dict | None = None,
    ) -> DSFAContentModel:
        services = graph_result.get("services", [])
        active_risks = set(graph_result.get("active_risks", []))
        lang = config.get("doc_language", "de") or "de"

        ai_services = [
            s for s in services
            if s.get("ai_act_relevant") or s.get("category") == "ai_llm"
        ]

        zweck: str | GapMarker
        # B-2/L4 (EN package): description_de must NOT win in the EN doc —
        # there is no description_en in the graph, so the EN path uses the
        # title_en branch below (20/20 seeded). DE behaviour unchanged.
        if lang != "en" and ai_usecase and ai_usecase.get("description_de"):
            zweck = ai_usecase["description_de"]
        elif ai_usecase and (ai_usecase.get("title_de") or ai_usecase.get("title_en")):
            # ADR-129 PR 12 (F8): doc-language title, honest DE fallback
            zweck = ((ai_usecase.get("title_en") if lang == "en" else None)
                     or ai_usecase.get("title_de") or ai_usecase.get("title_en"))
        else:
            # ADR-129 PR 16 (audit K23/F4): the dead config.product_description read
            # is gone (column never existed); the purpose comes from the AI use case,
            # so the fix link points to the KI-Angaben section.
            zweck = GapMarker(
                gap_id="dsfa_zweck_missing",
                article="DSGVO Art. 35 Abs. 7 lit. a",
                fix_url=f"/project/{ctx.project_name}/ai",
            )

        rechtsgrundlage = self._resolve_rechtsgrundlage(active_risks, config, ctx, ai_usecase, services, lang)

        pii_svc_objects = [
            s for s in services
            if s.get("dpa_required") or s.get("category") in _PII_CATEGORIES
        ]
        pii_service_names = [s.get("name", "") for s in pii_svc_objects]

        all_subjects = _collect_dedup_subjects(pii_svc_objects)
        data_subjects_str = render_data_subjects(all_subjects, lang) or None
        data_subjects: str | GapMarker = data_subjects_str or GapMarker(
            gap_id="dsfa_data_subjects_missing",
            article="DSGVO Art. 35 Abs. 7 lit. a",
            fix_url=f"/project/{ctx.project_name}/company",
        )

        risks = DSFARisksBlock(
            pii_in_llm_context="PII_IN_LLM_CONTEXT" in active_risks,
            rag_over_pii="RAG_OVER_PII" in active_risks,
            pii_in_logs="PII_IN_LOGS" in active_risks,
            no_ai_audit_trail="NO_AI_AUDIT_TRAIL" in active_risks,
            consent_management="CONSENT_MANAGEMENT" in active_risks,
        )

        usecase_block = self._to_usecase_block(ai_usecase, lang) if ai_usecase else None
        triggered_by_high_risk = bool(usecase_block and usecase_block.risk_level == "High")

        step2 = self._build_step2(usecase_block, ai_services, pii_svc_objects, lang)
        step4 = self._build_step4(graph_result, services, risks, lang)
        step5 = self._build_step5(risks, triggered_by_high_risk, config, lang)
        bfdi_citations = collect_bfdi_citations(graph_result.get("_graph_client"), "DSFA")
        damage_scenarios = self._build_damage_scenarios(risks, triggered_by_high_risk, ai_services, lang)

        return DSFAContentModel(
            company=self._company_block(config, ctx),
            generation_date=ctx.generation_date,
            run_id=ctx.run_id,
            warn_header_gaps=self._required_gaps_for("DSFA", gap_hints),
            zweck=zweck,
            rechtsgrundlage=rechtsgrundlage,
            data_subjects=data_subjects,
            ai_services=[self._to_service_row(s) for s in ai_services],
            ai_usecase=usecase_block,
            pii_services=pii_service_names,
            risks=risks,
            triggered_by_high_risk_usecase=triggered_by_high_risk,
            step2=step2,
            step4=step4,
            step5=step5,
            bfdi_citations=bfdi_citations,
            damage_scenarios=damage_scenarios,
        )

    # ── ADR-106 PR A4: Schritt 2 / 4 Builder-Helper ──────────────────────────
    def _build_step2(
        self,
        usecase: DSFAUseCaseBlock | None,
        ai_services: list[dict],
        pii_services: list[dict],
        lang: str = "de",
    ) -> DSFAStep2Block:
        """Default-Block aus DSK-VVT-Hinweise + Fraunhofer-Methodik. Replaced by
        SDM-based content in PR D when ProcessingActivity + LegalBasis nodes seeded.
        ADR-129 PR 12: EN twins per lang (lex-authored class-B prose).
        """
        n_ai, n_pii = len(ai_services), len(pii_services)
        if lang == "en":
            if usecase and usecase.title_de:
                notw = (
                    f"The processing is necessary to achieve the purpose "
                    f"'{usecase.title_de}'. A less intrusive alternative was "
                    f"examined and is not available."
                )
            else:
                notw = (
                    "The processing is necessary to fulfil the stated purpose. "
                    "An alternative without personal data was examined and is not feasible."
                )
            ai_phrase = f"{n_ai} AI system" if n_ai == 1 else f"{n_ai} AI systems"
            pii_phrase = (
                f"{n_pii} PII-processing service" if n_pii == 1
                else f"{n_pii} PII-processing services"
            )
            verh = (
                "The interference with the rights and freedoms of the data subjects "
                "is proportionate to the purpose pursued. "
                f"{ai_phrase} and {pii_phrase} were reviewed for necessity."
            )
            datenmin = (
                "Only the data categories required for the purpose are processed "
                "(Art. 5(1)(c) GDPR). Pseudonymisation and anonymisation are used "
                "where technically possible."
            )
            return DSFAStep2Block(
                notwendigkeit=notw,
                verhaeltnismaessigkeit=verh,
                datenminimierung=datenmin,
            )
        if usecase and usecase.title_de:
            notw = (
                f"Die Verarbeitung ist erforderlich, um den Zweck "
                f"'{usecase.title_de}' zu erreichen. Eine weniger eingriffsintensive "
                f"Alternative wurde geprüft und ist nicht gegeben."
            )
        else:
            notw = (
                "Die Verarbeitung ist zur Erfüllung des angegebenen Zwecks erforderlich. "
                "Eine Alternative ohne personenbezogene Daten wurde geprüft und ist nicht möglich."
            )
        ai_phrase = f"{n_ai} KI-System" if n_ai == 1 else f"{n_ai} KI-Systeme"
        pii_phrase = (
            f"{n_pii} PII-verarbeitender Dienst" if n_pii == 1
            else f"{n_pii} PII-verarbeitende Dienste"
        )
        verh = (
            "Der Eingriff in Rechte und Freiheiten der betroffenen Personen steht "
            "in einem angemessenen Verhältnis zum verfolgten Zweck. "
            f"{ai_phrase} und {pii_phrase} wurden auf Notwendigkeit geprüft."
        )
        datenmin = (
            "Es werden nur die für den Zweck erforderlichen Datenkategorien "
            "verarbeitet (Art. 5 Abs. 1 lit. c DSGVO). Pseudonymisierung und "
            "Anonymisierung werden eingesetzt, wo technisch möglich."
        )
        return DSFAStep2Block(
            notwendigkeit=notw,
            verhaeltnismaessigkeit=verh,
            datenminimierung=datenmin,
        )

    def _build_step4(
        self,
        graph_result: dict,
        services: list[dict],
        risks: DSFARisksBlock,
        lang: str = "de",
    ) -> list[DSFAStep4Row]:
        """Maßnahmen-Tabelle mit Cross-Refs auf konkrete TOM-Controls aus dem
        Scan (re-use of graph_result['controls']). PR A4 implementation; will be
        replaced by Measure-Layer Cross-Refs in PR D.
        """
        en = lang == "en"
        rows: list[DSFAStep4Row] = [
            DSFAStep4Row(
                measure=("DPA concluded with all processors" if en
                         else "AVV mit allen Auftragsverarbeitern geschlossen"),
                status=("See DPA document" if en else "Siehe AVV-Dokument"),
                control_ref=("Art. 28 GDPR" if en else "Art. 28 DSGVO"),
            ),
        ]

        controls = graph_result.get("controls", [])
        relevant_frameworks = {"OWASP_LLM_Top10", "BSI_Grundschutz", "ISO_27001"}
        seen_ctrls: set[tuple[str, str]] = set()
        ctrl_summary: list[tuple[str, str]] = []
        for c in controls:
            fw = c.get("framework", "")
            cid = c.get("control_id", "")
            if fw not in relevant_frameworks or not cid:
                continue
            key = (fw, cid)
            if key in seen_ctrls:
                continue
            seen_ctrls.add(key)
            ctrl_summary.append((cid, fw))
            if len(ctrl_summary) >= 6:
                break
        if ctrl_summary:
            refs = ", ".join(f"{cid}" for cid, _ in ctrl_summary)
            rows.append(DSFAStep4Row(
                measure=("Technical and organisational measures (Art. 32 GDPR)" if en
                         else "Technische und organisatorische Maßnahmen (Art. 32 DSGVO)"),
                status=("See TOM document" if en else "Siehe TOM-Dokument"),
                control_ref=(f"incl. {refs}" if en else f"u.a. {refs}"),
            ))

        if risks.pii_in_llm_context or risks.rag_over_pii:
            rows.append(DSFAStep4Row(
                measure=("PII scrubbing before LLM calls (Presidio pre-filter / UUID-only pattern)" if en
                         else "PII-Scrubbing vor LLM-Aufruf (Presidio Pre-Filter / UUID-Only Pattern)"),
                status=("to be implemented" if en else "zu implementieren"),
                control_ref=("GDPR Art. 25 (privacy by design)" if en else "DSGVO Art. 25 (Privacy by Design)"),
            ))
        if risks.pii_in_logs:
            rows.append(DSFAStep4Row(
                measure=("Log scrubbing before delivery to external monitoring" if en
                         else "Log-Scrubbing vor externem Monitoring-Versand"),
                status=("to be implemented" if en else "zu implementieren"),
                control_ref=("GDPR Art. 32" if en else "DSGVO Art. 32"),
            ))
        if risks.no_ai_audit_trail:
            rows.append(DSFAStep4Row(
                measure=("AI audit trail (Langfuse or similar)" if en
                         else "KI-Audit-Trail (Langfuse o.ä.)"),
                status=("to be implemented" if en else "zu implementieren"),
                control_ref="EU AI Act Art. 12",
            ))

        return rows

    # ── ADR-106 PR D6: Fraunhofer-Schadensszenario-Pattern ──────────────────
    def _build_damage_scenarios(
        self,
        risks: DSFARisksBlock,
        triggered_by_high_risk: bool,
        ai_services: list[dict],
        lang: str = "de",
    ) -> list[DSFADamageScenario]:
        """Schadensszenarien pro berührtes Gewährleistungsziel.

        Methodik: Fraunhofer-DSFA-Handbuch §6.3 — für jedes betroffene
        Gewährleistungsziel wird ein konkreter Schadens-Pfad beschrieben
        (Risikoquelle → Aktion → Schaden) mit Wahrscheinlichkeit, Schwere
        und Cross-Refs auf konkrete Measures aus dem SDM-Layer (PR D1).
        """
        scenarios: list[DSFADamageScenario] = []
        en = lang == "en"

        # Vertraulichkeit — typischer Pfad bei AI-Services + PII
        if risks.pii_in_llm_context or risks.rag_over_pii or ai_services:
            scenarios.append(DSFADamageScenario(
                gewaehrleistungsziel="Confidentiality (Vt)" if en else "Vertraulichkeit (Vt)",
                risikoquelle=("External attacker / third-country authority / AI provider" if en
                              else "Externer Angreifer / Drittland-Behörde / KI-Anbieter"),
                schaden=("Unauthorised disclosure of personal data via LLM prompt or API leak; identity theft, reputational damage" if en
                         else "Unbefugte Kenntnisnahme personenbezogener Daten via LLM-Prompt oder API-Leak; Identitätsdiebstahl, Reputationsschaden"),
                wahrscheinlichkeit=(("high" if risks.pii_in_llm_context else "medium") if en
                                    else ("hoch" if risks.pii_in_llm_context else "mittel")),
                schwere="high" if en else "hoch",
                measure_refs=["d1.3-verschluesselung-krypto", "d1.7-datenmasken-pseudo", "d1.4-pseudonyme-anon"],
            ))

        # Integrität — Bias/Diskriminierung bei automatisierten Entscheidungen
        if triggered_by_high_risk:
            scenarios.append(DSFADamageScenario(
                gewaehrleistungsziel=("Integrity (Ig) + non-discrimination" if en
                                      else "Integrität (Ig) + Diskriminierungsfreiheit"),
                risikoquelle=("Biased model / flawed training data" if en
                              else "Verzerrtes Modell / fehlerhafte Trainings-Daten"),
                schaden=("Indirect discrimination against data subjects (gender, age, origin); unlawful decision violating AGG/GDPR Art. 22" if en
                         else "Mittelbare Diskriminierung der betroffenen Personen (Geschlecht, Alter, Herkunft); rechtswidrige Entscheidung gegen AGG/DSGVO Art. 22"),
                wahrscheinlichkeit="medium" if en else "mittel",
                schwere="high" if en else "hoch",
                measure_refs=["d1.2-sollverhalten-tests", "d1.2-sollverhalten-ablaeufe"],
            ))

        # Transparenz — Black-Box-LLM-Entscheidungen
        if ai_services:
            scenarios.append(DSFADamageScenario(
                gewaehrleistungsziel="Transparency (Tp)" if en else "Transparenz (Tp)",
                risikoquelle=("Black-box model without explainability" if en
                              else "Black-Box-Modell ohne Erklärbarkeit"),
                schaden=("Data subjects cannot follow the processing logic; the right of access under Art. 15 GDPR is effectively undermined" if en
                         else "Betroffene können die Verarbeitungslogik nicht nachvollziehen; Auskunftsrecht Art. 15 DSGVO faktisch ausgehebelt"),
                wahrscheinlichkeit="high" if en else "hoch",
                schwere="medium" if en else "mittel",
                measure_refs=["d1.5-dok-profiling", "d1.5-info-betroffene"],
            ))

        # Verfügbarkeit — falls Log-Risiken oder externe Monitoring-Abhängigkeit
        if risks.pii_in_logs:
            scenarios.append(DSFADamageScenario(
                gewaehrleistungsziel=("Availability (Vf) + Confidentiality (Vt)" if en
                                      else "Verfügbarkeit (Vf) + Vertraulichkeit (Vt)"),
                risikoquelle=("External monitoring tool (Sentry/Datadog) as third-country processor" if en
                              else "Externes Monitoring-Tool (Sentry/Datadog) als Drittland-Auftragsverarbeiter"),
                schaden=("PII in error logs ends up outside the EU perimeter; loss of data sovereignty" if en
                         else "PII in Error-Logs landen außerhalb des EU-Perimeters; Verlust der Datenherrschaft"),
                wahrscheinlichkeit="high" if en else "hoch",
                schwere="medium" if en else "mittel",
                measure_refs=["d1.3-verschluesselung-krypto", "d1.7-datenmasken-pseudo"],
            ))

        # Intervenierbarkeit — wenn KI-Audit-Trail fehlt
        if risks.no_ai_audit_trail:
            scenarios.append(DSFADamageScenario(
                gewaehrleistungsziel=("Intervenability (Iv) + Transparency (Tp)" if en
                                      else "Intervenierbarkeit (Iv) + Transparenz (Tp)"),
                risikoquelle=("Missing audit trail for AI decisions" if en
                              else "Fehlender Audit-Trail bei KI-Entscheidungen"),
                schaden=("Data subject rights under Art. 22(3) GDPR (right to intervene in automated decisions) unenforceable; EU AI Act Art. 12 violation" if en
                         else "Betroffenenrechte nach Art. 22 Abs. 3 DSGVO (Eingriffsrecht in automatisierte Entscheidung) nicht durchsetzbar; EU AI Act Art. 12 Verstoß"),
                wahrscheinlichkeit="high" if en else "hoch",
                schwere="high" if en else "hoch",
                measure_refs=["d1.5-protokoll-konzept", "d1.6-standard-abfrage-iface"],
            ))

        return scenarios

    # ── ADR-106 PR A5: Schritt 5 Art. 36 Konsultations-Logik ────────────────
    def _build_step5(
        self,
        risks: DSFARisksBlock,
        triggered_by_high_risk: bool,
        config: dict,
        lang: str = "de",
    ) -> DSFAStep5Block:
        """Art. 36 Konsultation erforderlich wenn HIGH-RISK-UseCase UND
        Restrisiken trotz Maßnahmen verbleiben (≥1 PII-Risk aktiv).

        SupervisoryAuthority-Lookup erfolgt in PR B4 (Bundesland → Aufsichtsbehörde-Seed).
        Bis dahin: nur Konsultations-Ja/Nein-Logik und Platzhalter.
        """
        has_residual_risk = any([
            risks.pii_in_llm_context,
            risks.rag_over_pii,
            risks.pii_in_logs,
            risks.no_ai_audit_trail,
        ])
        en = lang == "en"
        if triggered_by_high_risk and has_residual_risk:
            return DSFAStep5Block(
                konsultation_erforderlich=True,
                begruendung=(
                    "Despite technical and organisational measures, a high residual "
                    "risk to the rights and freedoms of data subjects remains "
                    "(high-risk AI under EU AI Act Annex III + active PII risks). "
                    "Prior consultation of the competent supervisory authority under "
                    "Art. 36(1) GDPR is required."
                    if en else
                    "Trotz technischer und organisatorischer Maßnahmen verbleibt "
                    "ein hohes Restrisiko für die Rechte und Freiheiten "
                    "betroffener Personen (Hochrisiko-KI nach EU AI Act Anhang III "
                    "+ aktive PII-Risiken). Vorherige Konsultation der zuständigen "
                    "Aufsichtsbehörde nach Art. 36 Abs. 1 DSGVO erforderlich."
                ),
            )
        if triggered_by_high_risk:
            return DSFAStep5Block(
                konsultation_erforderlich=False,
                begruendung=(
                    "High-risk AI under the EU AI Act detected; the implemented "
                    "technical and organisational measures reduce the residual risk "
                    "to an acceptable level. Consultation under Art. 36 GDPR is not "
                    "required; the risk assessment remains documented (Art. 35(7) "
                    "GDPR + accountability, Art. 5(2) GDPR)."
                    if en else
                    "Hochrisiko-KI nach EU AI Act erkannt; durch implementierte "
                    "technische und organisatorische Maßnahmen wird das Restrisiko "
                    "auf ein vertretbares Maß reduziert. Konsultation nach Art. 36 "
                    "DSGVO nicht erforderlich; Dokumentation der Risikobewertung "
                    "bleibt erhalten (Art. 35 Abs. 7 DSGVO + Rechenschaftspflicht "
                    "Art. 5 Abs. 2 DSGVO)."
                ),
            )
        return DSFAStep5Block(
            konsultation_erforderlich=False,
            begruendung=(
                "No high residual risk identified. Consultation of the supervisory "
                "authority under Art. 36 GDPR is not required. Reasoning: the risk "
                "analysis in step 3 shows no high residual risks after applying the "
                "measures from step 4."
                if en else
                "Kein hohes Restrisiko identifiziert. Konsultation der "
                "Aufsichtsbehörde nach Art. 36 DSGVO nicht erforderlich. "
                "Begründung: Risikoanalyse aus Schritt 3 ergibt keine hohen "
                "Restrisiken nach Anwendung der Maßnahmen aus Schritt 4."
            ),
        )

    def _resolve_rechtsgrundlage(
        self,
        active_risks: set[str],
        config: dict,
        ctx: BuildContext,
        ai_usecase: dict | None = None,
        services: list[dict] | None = None,
        lang: str = "de",
    ) -> str | GapMarker:
        # ADR-129 PR 16 (audit K23/F4): dead reads of non-existent config columns
        # (rechtsgrundlage, contract_processing) removed; derivation + honest gap only.
        derived = derive_legal_basis_for_usecase(ai_usecase, services or [], active_risks, lang)
        if derived:
            return derived
        return GapMarker(
            gap_id="dsfa_rechtsgrundlage_missing",
            article="DSGVO Art. 6",
            fix_url=f"/project/{ctx.project_name}/ai",
        )

    def _to_service_row(self, s: dict) -> DSFAAIServiceRow:
        category = s.get("category")
        purpose = s.get("purpose") or _AI_PURPOSE_BY_CATEGORY.get(
            category or "", "KI-basierte Leistungserbringung"
        )
        return DSFAAIServiceRow(
            name=s.get("name", ""),
            category=category,
            purpose=purpose,
            country=s.get("country"),
            gdpr_adequate=bool(s.get("gdpr_adequate")),
        )

    def _to_usecase_block(self, uc: dict, lang: str = "de") -> DSFAUseCaseBlock:
        return DSFAUseCaseBlock(
            type=uc.get("type", ""),
            # field keeps its historic name; it carries the DOC-LANGUAGE display
            # title (EN when lang='en' and seeded, DE fallback) — ADR-129 PR 12/F8
            title_de=((uc.get("title_en") if lang == "en" else None)
                      or uc.get("title_de") or uc.get("type", "")),
            description_de=uc.get("description_de"),
            risk_level=uc.get("risk_level", "Minimal"),
            article=uc.get("article"),
            annex_iii_nr=str(uc.get("annex_iii_nr")) if uc.get("annex_iii_nr") else None,
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
