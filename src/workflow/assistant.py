"""
Lex Assistant — LangGraph Graph (ADR-091)
==========================================
Standalone graph for two assistant roles:
  - Orientierer  : explain compliance terms on demand (Neo4j graph-first)
  - Lücken-Führer: surface project gaps after a scan (gap_analyzer)

Phase 2 (not here): Daten-Sammler via lex-extractor (ADR-090).

Interaction pattern: synchronous request/response (not a background pipeline).
Registered alongside lex_workflow in langgraph.json.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Optional

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

from src.graph.graph_client import GraphClient
from src.llm import complete_ollama, resolve_ollama_endpoint
from src.scanner.gap_analyzer import GapHint, analyze_gaps

load_dotenv()

logger = logging.getLogger(__name__)

# ADR-127 Phase 1: endpoint lookup centralized in src/llm; resolves byte-identically
# to the prior os.getenv("OLLAMA_URL", <default>) — site reads OLLAMA_URL only.
OLLAMA_URL = resolve_ollama_endpoint(
    full_env="OLLAMA_URL", full_default="http://host.docker.internal:11434/api/generate"
)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e4b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))
DB_URL = os.getenv("DATABASE_URL") or os.getenv("MCP_SUPABASE_URL", "")
DASHBOARD_BASE = os.environ.get("DASHBOARD_BASE_URL", "http://localhost:3000")

# ── Frontend contract ──────────────────────────────────────────────────────────

VALID_ACTION_TYPES = frozenset({
    "navigate",     # open a specific workspace section
    "fill_field",   # suggest a value for a form field (Phase 2)
    "acknowledge",  # mark a gap as "intentionally empty" (Phase 2)
    "ask_followup", # offer a specific follow-up question
})

# ── Fulltext index bootstrap (ADR-093) ────────────────────────────────────────

_indexes_ensured = False


def _ensure_fulltext_indexes() -> None:
    """Create Neo4j fulltext indexes if absent (idempotent, once per process).

    law_text covers note_de (PR4 Law nodes use note_de, older ones use text).
    doctype_text added in PR4 to make DocumentType.description_de searchable.
    If law_text already exists without note_de, drop and recreate it.
    """
    global _indexes_ensured
    if _indexes_ensured:
        return
    try:
        with GraphClient() as gc:
            gc.run_query(
                "CREATE FULLTEXT INDEX control_text IF NOT EXISTS "
                "FOR (n:Control) ON EACH [n.title_de, n.title_en, n.description]"
            )
            # Drop old law_text (created without note_de) and recreate with note_de included
            gc.run_query("DROP INDEX law_text IF EXISTS")
            gc.run_query(
                "CREATE FULLTEXT INDEX law_text IF NOT EXISTS "
                "FOR (n:Law) ON EACH [n.title, n.title_de, n.text, n.note_de]"
            )
            gc.run_query(
                "CREATE FULLTEXT INDEX doctype_text IF NOT EXISTS "
                "FOR (n:DocumentType) ON EACH [n.name_de, n.description_de]"
            )
        _indexes_ensured = True
        logger.info("Fulltext indexes ensured (law_text+note_de, doctype_text)")
    except Exception as e:
        logger.warning("_ensure_fulltext_indexes failed: %s", e)


# ── Intent keyword sets ────────────────────────────────────────────────────────

_LUECKEN_KEYWORDS = frozenset({
    "lücke", "lücken", "luecke", "luecken", "gap", "gaps", "fehlend", "fehlt", "missing",
    "was fehlt", "was ist noch", "was muss", "vervollständig",
    "unvollständig", "nicht ausgefüllt",
})

_ORIENTIERER_KEYWORDS = frozenset({
    "tom", "avv", "dsgvo", "gdpr", "scc", "art.", "art ", "iso", "bsi",
    "owasp", "ai act", "nis2", "dsfa", "dpo", "annex", "gpai",
    "datenschutz", "compliance", "verarbeitung", "processor", "controller",
    "auftragsverarbeitung", "technische", "organisatorische", "massnahme",
    "hochrisiko", "high-risk", "annex iii", "artikel", "verordnung",
    "richtlinie", "directive", "regulation", "bcr", "binding corporate",
    "standardvertragsklausel", "standard contractual",
    # Retention / storage
    "retention", "aufbewahrung", "aufbewahrungsfrist", "speicherfrist",
    "löschfrist", "löschung", "speicherdauer", "speicherung",
})

# ── State ──────────────────────────────────────────────────────────────────────

class AssistantState(TypedDict):
    # Input
    project_name: str
    thread_id:    str
    message:      str

    # Intermediate
    intent:        str          # "orientierer" | "luecken_fuehrer" | "empty"
    graph_context: dict         # {"laws": [...], "controls": [...], "services": [...]}
    gap_hints:     list         # list[GapHint]

    # Output
    response:         str
    proposed_actions: list      # [{action_type, label, payload}]
    sources:          list      # graph node refs cited

    # Conversation memory — persists across turns (not reset in node_start)
    chat_history:          list   # [{"role": "user"|"assistant", "content": str}]

    # Scan context — loaded fresh each turn by node_load_gaps
    scan_signals_context:  list   # scan_signals rows (signal_type != 'service_detected')

    # ADR-094: service names and compliance context from last scan
    detected_services:          list   # canonical service names ["Stripe", "AWS S3", ...]
    detected_services_detail:   list   # [{"name": str, "evidence": list[str]}]
    service_compliance_context: dict   # from gc.get_compliance_requirements()

    # Phase 2 hook — populated from project_config if column exists; empty otherwise
    intentionally_empty_fields: list

    # Meta
    errors: list


# ── DB helper (ADR-080: project_name → project_config.id UUID) ────────────────

def _get_project_id(cur, project_name: str) -> str:
    """Resolve project_name → project_config.id.
    Workflow-local duplicate of approve_api._get_project_id_by_name —
    no cross-import between workflow/ and interface/ layers.
    """
    cur.execute("SELECT id FROM project_config WHERE project_name = %s", (project_name,))
    row = cur.fetchone()
    if row:
        return str(row[0])
    cur.execute(
        "INSERT INTO project_config (project_name) VALUES (%s) "
        "ON CONFLICT (project_name) DO UPDATE SET project_name = EXCLUDED.project_name "
        "RETURNING id",
        (project_name,),
    )
    return str(cur.fetchone()[0])


# ── Ollama helper (local copy — NOT imported from llm_classifier) ─────────────

def _call_ollama_assistant(prompt: str) -> Optional[str]:
    """Call Ollama with the assistant prompt. Returns text or None on error.

    Uses num_predict=512 for conversational responses (vs. num_predict=8 in
    llm_classifier which only needs a single classification token).
    """
    try:
        # ADR-127 Phase 1: transport via central client; post-processing unchanged.
        data = complete_ollama(
            prompt,
            endpoint=OLLAMA_URL,
            model=OLLAMA_MODEL,
            options={"temperature": 0.3, "num_predict": 800},
            timeout=OLLAMA_TIMEOUT,
        )
        if data.get("error"):
            logger.warning("Ollama returned error field: %s", data["error"])
            return None
        text = data.get("response", "").strip()
        # Reject known Ollama internal error strings that land in the response field
        if not text or not data.get("done", True) or "timeout" in text.lower():
            logger.warning("Ollama returned incomplete/error response (done=%s): %s", data.get("done"), text[:80])
            return None
        return text
    except Exception as e:
        logger.warning("Ollama assistant call failed: %s", e)
        return None


# ── Nodes ──────────────────────────────────────────────────────────────────────

def node_start(state: AssistantState) -> dict:
    """Reset per-turn output fields; preserve chat_history across turns; ensure indexes."""
    _ensure_fulltext_indexes()
    return {
        "response": "",
        "proposed_actions": [],
        "gap_hints": [],
        "graph_context": {},
        "errors": [],
        "scan_signals_context": [],
    }


def node_classify_intent(state: AssistantState) -> dict:
    """Deterministic keyword-based intent classification — no LLM.

    Magic strings for programmatic triggers (frontend bypasses keyword matching):
      "__gaps__"               → luecken_fuehrer  (scan complete → gap walkthrough)
      "__scan_domain:<url>__"  → daten_sammler    (Phase 2; routed to empty until ADR-090)
    Pattern: Phase 2 adds new intent branch + handler; classify_intent unchanged.
    """
    msg = (state.get("message") or "").strip()
    msg_lower = msg.lower()

    if not msg or msg == "__gaps__" or any(k in msg_lower for k in _LUECKEN_KEYWORDS):
        return {"intent": "luecken_fuehrer"}

    # Phase 2 sentinel — parse but route to empty until daten_sammler is implemented
    if re.match(r"^__scan_domain:.+__$", msg):
        logger.info("daten_sammler sentinel received — Phase 2 not yet implemented, routing to empty")
        return {"intent": "empty"}

    if any(k in msg_lower for k in _ORIENTIERER_KEYWORDS):
        return {"intent": "orientierer"}

    return {"intent": "orientierer"}


def _route_intent(state: AssistantState) -> str:
    return state.get("intent", "empty")


def node_query_graph(state: AssistantState) -> dict:
    """Orientierer: query Neo4j for laws, controls, and services matching the user's question."""
    message = state.get("message", "")
    graph_context: dict = {"laws": [], "controls": [], "services": []}
    sources: list = []

    try:
        with GraphClient() as gc:
            # Extract article numbers: "Art. 5", "Artikel 13", "Art.28"
            article_matches = re.findall(r"[Aa]rt(?:ikel)?\.?\s*(\d+[a-z]?)", message)

            # Extract known framework names — sorted longest-first to prevent "owasp" swallowing "owasp llm"
            framework_map = {
                "iso 27001":  "ISO_27001",  "iso27001":    "ISO_27001",
                "owasp llm":  "OWASP_LLM_Top10",
                "owasp":      "OWASP_Top10",
                "bsi c5":     "BSI_C5",     "bsi":         "BSI_C5",
                "nic4":       "AIC4",       "aic4":        "AIC4",
                "nis2":       "NIS2",
                "nist ai":    "NIST_AI_RMF","nist":        "NIST_CSF_2",
                "c5":         "BSI_C5",
            }
            msg_lower = message.lower()
            matched_framework = None
            for k in sorted(framework_map, key=len, reverse=True):
                if k in msg_lower:
                    matched_framework = framework_map[k]
                    break

            # Query laws for matched articles (DSGVO / EU AI Act context)
            for article_num in article_matches[:3]:
                for law_name in ("DSGVO", "EU_AI_ACT"):
                    # Law article nodes are keyed bare-number ("5"), not "Art. 5"
                    # (ADR-126 Addendum 1b consolidated the split nodes). Display label
                    # below stays "Art. N"; only the lookup key is bare.
                    text = gc.get_law_text(law_name, f"{article_num}")
                    if text:
                        graph_context["laws"].append({
                            "law": law_name,
                            "article": f"Art. {article_num}",
                            "text": text,
                        })
                        sources.append(f"{law_name}:Art.{article_num}")

            # Query controls for matched framework
            if matched_framework:
                controls = gc.get_controls_for_framework(matched_framework)[:10]
                graph_context["controls"] = controls
                sources.extend(f"{matched_framework}:{c.get('id', '')}" for c in controls)

                # If no controls found, also fetch overview law node for this regulation
                if not controls:
                    for article_label in ("Überblick", "Overview"):
                        law_name = matched_framework.split("_")[0]  # "NIS2", "DSGVO", etc.
                        text = gc.get_law_text(law_name, article_label)
                        if text:
                            graph_context["laws"].append({
                                "law": law_name,
                                "article": article_label,
                                "text": text,
                            })
                            sources.append(f"{law_name}:{article_label}")
                            break

            # Fallback: full-text search when no article/framework matched (or framework had no results)
            if not graph_context["laws"] and not graph_context["controls"]:
                search_term = message[:120]
                ft_controls = gc.search_controls_by_keyword(search_term, limit=8)
                ft_laws = gc.search_laws_by_keyword(search_term, limit=3)
                ft_doctypes = gc.search_doctypes_by_keyword(search_term, limit=3)
                graph_context["controls"] = ft_controls
                graph_context["laws"] = ft_laws
                graph_context["doctypes"] = ft_doctypes
                sources.extend(f"{c.get('framework','?')}:{c.get('id','')}" for c in ft_controls[:5])
                sources.extend(f"{l.get('law','?')}:{l.get('article','')}" for l in ft_laws[:3])
                sources.extend(f"DocumentType:{d.get('type','')}" for d in ft_doctypes[:3])

    except Exception as e:
        logger.warning("node_query_graph failed: %s", e)

    return {"graph_context": graph_context, "sources": sources}


def _resolve_service_names(gc: GraphClient, raw_names: list[str]) -> tuple[list[str], list[str]]:
    """Resolve raw service names to canonical graph names (case-insensitive).

    Returns (matched_canonical_names, unmatched_names).
    """
    if not raw_names:
        return [], []
    rows = gc.run_query(
        "UNWIND $names AS n "
        "MATCH (s:Service) WHERE toLower(s.name) = toLower(n) "
        "RETURN n AS input, s.name AS canonical",
        {"names": raw_names},
    )
    matched_canonicals = [r["canonical"] for r in rows]
    matched_inputs = {r["input"].lower() for r in rows}
    unmatched = [n for n in raw_names if n.lower() not in matched_inputs]
    return matched_canonicals, unmatched


def node_load_gaps(state: AssistantState) -> dict:
    """Lücken-Führer: load project state from Supabase and run gap analysis."""
    project_name = state["project_name"]
    gap_hints: list[GapHint] = []
    sources: list = []
    proposed_actions: list = []

    scan_signals_context: list = []
    detected_services: list = []
    detected_services_detail: list = []
    service_compliance_context: dict = {}

    if not DB_URL:
        logger.warning("node_load_gaps: DATABASE_URL not set")
        return {
            "gap_hints": [],
            "sources": [],
            "proposed_actions": [{
                "action_type": "navigate",
                "label": "Configure database connection",
                "payload": {"url": f"{DASHBOARD_BASE}/project/{project_name}/company"},
            }],
        }

    try:
        with psycopg2.connect(DB_URL) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Load project_config
                cur.execute(
                    "SELECT * FROM project_config WHERE project_name = %s",
                    (project_name,),
                )
                config_row = cur.fetchone()
                config = dict(config_row) if config_row else {}

                if not config:
                    return {
                        "gap_hints": [],
                        "sources": [],
                        "response": (
                            f"Das Projekt '{project_name}' ist noch nicht konfiguriert. "
                            "Lege zuerst die Projektdetails an."
                        ),
                        "proposed_actions": [{
                            "action_type": "navigate",
                            "label": "Projekt anlegen",
                            "payload": {"url": f"{DASHBOARD_BASE}/setup"},
                        }],
                    }

                project_id = str(config.get("id", ""))

                # Load project_setup (most recent)
                setup: dict = {}
                if project_id:
                    cur.execute(
                        "SELECT * FROM project_setups WHERE project_id = %s "
                        "ORDER BY updated_at DESC LIMIT 1",
                        (project_id,),
                    )
                    setup_row = cur.fetchone()
                    setup = dict(setup_row) if setup_row else {}

                # Load user-confirmed retention policies only (source='setup').
                # Code-detected policies (source='code') are not counted —
                # users must explicitly review and save them to close this gap.
                cur.execute(
                    "SELECT * FROM retention_policies "
                    "WHERE project_name = %s AND source = 'setup'",
                    (project_name,),
                )
                retention_policies = [dict(r) for r in cur.fetchall()]

                # Check whether a completed scan exists (no services_detected column —
                # scan_results tracks counts only; service details are in scan_signals)
                cur.execute(
                    """
                    SELECT run_id, started_at
                    FROM scan_results
                    WHERE project_name = %s
                      AND status = 'complete'
                    ORDER BY started_at DESC
                    LIMIT 1
                    """,
                    (project_name,),
                )
                scan_row = cur.fetchone()

                # Load scan_signals for assistant context (ADR-093)
                if scan_row:
                    cur.execute(
                        """
                        SELECT signal_type, value, confidence
                        FROM scan_signals
                        WHERE run_id = %s AND signal_type != 'service_detected'
                        ORDER BY confidence DESC
                        LIMIT 20
                        """,
                        (str(scan_row["run_id"]),),
                    )
                    scan_signals_context = [dict(r) for r in cur.fetchall()]

                    # ADR-094: load detected service names
                    cur.execute(
                        """
                        SELECT value AS service_name, evidence
                        FROM scan_signals
                        WHERE run_id = %s AND signal_type = 'service_detected'
                        ORDER BY confidence DESC
                        """,
                        (str(scan_row["run_id"]),),
                    )
                    for r in cur.fetchall():
                        detected_services.append(r["service_name"])
                        detected_services_detail.append({
                            "name": r["service_name"],
                            "evidence": list(r["evidence"] or []),
                        })

    except Exception as e:
        logger.warning("node_load_gaps DB error: %s", e)
        return {
            "gap_hints": [],
            "sources": [],
            "detected_services": [],
            "detected_services_detail": [],
            "service_compliance_context": {},
            "errors": [f"db_error: {e}"],
        }

    # ADR-094: resolve service names against graph and fetch compliance requirements
    if detected_services:
        try:
            with GraphClient() as gc:
                canonical, unmatched = _resolve_service_names(gc, detected_services)
                if unmatched:
                    logger.warning("Service names not in graph (unmatched): %s", unmatched)
                if canonical:
                    service_compliance_context = gc.get_compliance_requirements(canonical)
        except Exception as e:
            logger.warning("Service compliance lookup failed (non-fatal): %s", e)

    # Edge case: no completed scan yet
    if not scan_row:
        return {
            "gap_hints": [],
            "sources": [],
            "response": (
                f"Für das Projekt '{project_name}' liegt noch kein abgeschlossener Scan vor. "
                "Starte erst einen Scan — dann kann ich dir genau sagen, was fehlt."
            ),
            "proposed_actions": [{
                "action_type": "navigate",
                "label": "Scan starten",
                "payload": {"url": f"{DASHBOARD_BASE}/project/{project_name}/scan"},
            }],
        }

    services_detected: list = []  # passed to _check_service_gaps for structural enrichment gaps
    sources.append(f"scan:{scan_row.get('run_id', '')}")

    try:
        gap_hints = analyze_gaps(
            project_name=project_name,
            config=config,
            setup=setup or None,
            retention_policies=retention_policies,
            services_detected=services_detected,
        )
    except Exception as e:
        logger.warning("analyze_gaps failed: %s", e)

    sources.extend(f"gap:{h.field}" for h in gap_hints)

    proposed_actions = [
        {
            "action_type": "navigate",
            "label": h.fix_label,
            "payload": {"url": h.fix_url},
        }
        for h in gap_hints[:5]
    ]

    return {
        "gap_hints": gap_hints,
        "sources": sources,
        "proposed_actions": proposed_actions,
        "scan_signals_context": scan_signals_context,
        "detected_services": detected_services,
        "detected_services_detail": detected_services_detail,
        "service_compliance_context": service_compliance_context,
    }


def node_formulate_response(state: AssistantState) -> dict:
    """Formulate the final natural-language response via Gemma4.

    Builds the prompt from available context depending on intent.
    Empty intent returns a static string without an Ollama call.
    Ollama errors are captured gracefully — no exceptions raised.
    """
    intent = state.get("intent", "empty")
    message = state.get("message", "")
    gap_hints: list[GapHint] = state.get("gap_hints") or []
    graph_context: dict = state.get("graph_context") or {}
    sources: list = state.get("sources") or []
    existing_response: str = state.get("response") or ""
    existing_proposed: list = state.get("proposed_actions") or []
    existing_errors: list = state.get("errors") or []

    # If a prior node already wrote a static response (e.g. "no scan yet"), pass through
    if existing_response:
        proposed_actions = [
            a for a in existing_proposed
            if a.get("action_type") in VALID_ACTION_TYPES
        ]
        return {"response": existing_response, "proposed_actions": proposed_actions}

    if intent == "empty":
        return {
            "response": (
                "Ich bin der Lex Compliance-Assistent. Stelle mir eine Frage zu "
                "DSGVO, EU AI Act, ISO 27001, TOM, AVV oder anderen Compliance-Themen — "
                "oder schreibe 'Was fehlt noch?' um deine offenen Lücken zu sehen."
            ),
            "proposed_actions": [],
        }

    chat_history: list = state.get("chat_history") or []
    history_lines = []
    for turn in chat_history[-3:]:
        role = "Nutzer" if turn.get("role") == "user" else "Assistent"
        history_lines.append(f"{role}: {turn.get('content', '')[:200]}")
    history_section = ("\nBisherige Unterhaltung:\n" + "\n".join(history_lines) + "\n") if history_lines else ""

    scan_signals_context: list = state.get("scan_signals_context") or []

    response_text: Optional[str] = None

    if intent == "orientierer":
        laws = graph_context.get("laws") or []
        controls = graph_context.get("controls") or []
        services = graph_context.get("services") or []

        doctypes = graph_context.get("doctypes") or []

        facts_lines = []
        for law in laws[:3]:
            facts_lines.append(f"Gesetz: {law.get('law')} {law.get('article')}")
            if law.get("text"):
                facts_lines.append(f"Text: {law['text'][:400]}")
            elif law.get("short"):
                facts_lines.append(f"Zusammenfassung: {law['short'][:400]}")
        for ctrl in controls[:5]:
            facts_lines.append(f"Control: {ctrl.get('id')} — {ctrl.get('title')}")
            if ctrl.get("text"):
                facts_lines.append(f"  Beschreibung: {ctrl['text'][:200]}")
        for dt in doctypes[:3]:
            facts_lines.append(f"Dokument: {dt.get('name_de')} ({dt.get('type')})")
            if dt.get("description_de"):
                facts_lines.append(f"  Erklärung: {dt['description_de'][:400]}")
        for svc in services[:3]:
            facts_lines.append(f"Service: {svc.get('name')} (Kategorie: {svc.get('category')})")

        facts_block = "\n".join(facts_lines) if facts_lines else "(Keine direkten Graph-Treffer)"

        prompt = (
            "Du bist ein präziser EU-Datenschutz- und AI-Compliance-Experte. "
            "Beantworte die Frage des Nutzers klar und knapp auf Deutsch. "
            "Nutze ausschließlich die folgenden Fakten aus dem Compliance-Graph. "
            "Erfinde keine Informationen.\n\n"
            f"Fakten aus dem Graph:\n{facts_block}\n"
            f"{history_section}\n"
            f"Frage: {message}\n\n"
            "Antwort (max. 3 Absätze):"
        )

    elif intent == "luecken_fuehrer":
        if not gap_hints:
            return {
                "response": (
                    "Super — für dieses Projekt sind keine offenen Pflichtfelder gefunden worden. "
                    "Alle relevanten Angaben sind vorhanden."
                ),
                "proposed_actions": [],
            }

        gap_lines = []
        for h in gap_hints[:8]:
            prio_label = {1: "🔴 Pflicht", 2: "🟡 Wichtig", 3: "🟢 Empfohlen"}.get(h.priority, "")
            gap_lines.append(
                f"- {prio_label} [{h.field}]: {h.gap_reason}"
            )
        gap_block = "\n".join(gap_lines)

        signals_lines = [
            f"- {s.get('signal_type')}: {s.get('value')} (conf={s.get('confidence', 0):.2f})"
            for s in scan_signals_context[:10]
        ]
        signals_block = ("\nErkannte Scan-Signale:\n" + "\n".join(signals_lines)) if signals_lines else ""

        # ADR-094: service compliance block
        svc_compliance = state.get("service_compliance_context") or {}
        detail_list = state.get("detected_services_detail") or []
        evidence_by_service = {s["name"]: s.get("evidence", []) for s in detail_list}
        service_lines = []
        for doc in (svc_compliance.get("docs_required") or []):
            svc_name = doc.get("service", "")
            doc_name = doc.get("doc_name_de") or doc.get("doc_type", "?")
            evidence = evidence_by_service.get(svc_name, [])
            evidence_str = f" (in {evidence[0]})" if evidence else ""
            if svc_name and doc_name:
                service_lines.append(f"- {svc_name}: benötigt {doc_name}{evidence_str}")
        service_block = ""
        if service_lines:
            service_block = "Erkannte Services und erforderliche Dokumente:\n" + "\n".join(service_lines[:6]) + "\n\n"

        prompt = (
            "Du bist ein präziser EU-Datenschutz-Compliance-Assistent. "
            "Erkläre dem Nutzer auf Deutsch, welche Felder fehlen und warum sie relevant sind. "
            "Weise klar auf Felder hin, die nach DSGVO oder EU AI Act rechtlich zwingend sind "
            "(wo bekannt), und unterscheide sie von empfohlenen Angaben. "
            "Sei konkret und handlungsorientiert. Max. 4 Sätze gesamt.\n\n"
            f"{service_block}"
            f"Offene Lücken:\n{gap_block}\n"
            f"{signals_block}\n\n"
            "Zusammenfassung für den Nutzer:"
        )
    else:
        prompt = ""

    if prompt:
        response_text = _call_ollama_assistant(prompt)

    if response_text is None:
        return {
            "response": "",
            "proposed_actions": [],
            "errors": existing_errors + ["assistant_unavailable"],
        }

    # Append Python-side source note (orientierer only — keeps Gemma prompt clean)
    final_response = response_text
    if intent == "orientierer" and sources:
        source_str = ", ".join(str(s) for s in sources[:5])
        final_response = f"{response_text}\n\nQuelle: {source_str}"

    # Update conversation memory
    new_history = list(chat_history) + [
        {"role": "user",      "content": message},
        {"role": "assistant", "content": response_text},
    ]

    # Build and validate proposed_actions
    raw_actions = existing_proposed or [
        {
            "action_type": "navigate",
            "label": h.fix_label,
            "payload": {"url": h.fix_url},
        }
        for h in gap_hints[:3]
    ]
    proposed_actions = [
        a for a in raw_actions
        if a.get("action_type") in VALID_ACTION_TYPES
    ]

    return {
        "response": final_response,
        "proposed_actions": proposed_actions,
        "chat_history": new_history,
    }


# ── Graph ──────────────────────────────────────────────────────────────────────

def build_assistant_workflow():
    """Build and compile the Lex Assistant LangGraph graph.

    LangGraph Server manages its own state store — no checkpointer injected here.
    Langfuse tracing is opt-in via LANGFUSE_ENABLED=true env var.
    """
    workflow = StateGraph(AssistantState)

    workflow.add_node("start",                node_start)
    workflow.add_node("classify_intent",      node_classify_intent)
    workflow.add_node("query_graph",          node_query_graph)
    workflow.add_node("load_gaps",            node_load_gaps)
    workflow.add_node("formulate_response",   node_formulate_response)

    workflow.set_entry_point("start")
    workflow.add_edge("start", "classify_intent")

    workflow.add_conditional_edges(
        "classify_intent",
        _route_intent,
        {
            "orientierer":    "query_graph",
            "luecken_fuehrer":"load_gaps",
            "empty":          "formulate_response",
        },
    )

    workflow.add_edge("query_graph", "formulate_response")
    workflow.add_edge("load_gaps",   "formulate_response")
    workflow.add_edge("formulate_response", END)

    # Langfuse tracing deferred: LangGraph 0.7.x compile() doesn't accept callbacks.
    # Re-enable when upgrading to langgraph-api 0.8.x (compile supports RunnableConfig).
    return workflow.compile()
