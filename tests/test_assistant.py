"""Tests for ADR-091 — Lex Assistant LangGraph graph."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from src.workflow.assistant import (
    VALID_ACTION_TYPES,
    AssistantState,
    node_classify_intent,
    node_formulate_response,
    _resolve_service_names,
    build_assistant_workflow,
)

# ── Helpers ────────────────────────────────────────────────────────────────────

def _state(**kwargs) -> AssistantState:
    base: AssistantState = {
        "project_name": "test-project",
        "thread_id":    "asst-test-001",
        "message":      "",
        "intent":       "",
        "graph_context": {},
        "gap_hints":    [],
        "response":     "",
        "proposed_actions": [],
        "sources":      [],
        "chat_history": [],
        "scan_signals_context": [],
        "detected_services": [],
        "detected_services_detail": [],
        "service_compliance_context": {},
        "intentionally_empty_fields": [],
        "errors":       [],
    }
    base.update(kwargs)
    return base


requires_neo4j = pytest.mark.skipif(
    not os.getenv("NEO4J_URI"),
    reason="NEO4J_URI not set",
)
requires_supabase = pytest.mark.skipif(
    not (os.getenv("DATABASE_URL") or os.getenv("MCP_SUPABASE_URL")),
    reason="DATABASE_URL not set",
)
def _ollama_reachable() -> bool:
    """Probe Ollama endpoint with a 3s timeout — returns False when inside Docker hostname."""
    url = os.getenv("OLLAMA_URL", "")
    if not url:
        return False
    # Strip /api/generate to get the base URL for a HEAD probe
    base = url.split("/api/")[0] if "/api/" in url else url
    try:
        import urllib.request as _ur
        _ur.urlopen(base, timeout=3)
        return True
    except Exception:
        return False


requires_ollama = pytest.mark.skipif(
    not _ollama_reachable(),
    reason="Ollama not reachable from this host",
)


# ── Unit: node_classify_intent ─────────────────────────────────────────────────

def test_classify_orientierer_tom():
    result = node_classify_intent(_state(message="Was ist eine TOM?"))
    assert result["intent"] == "orientierer"


def test_classify_orientierer_iso():
    result = node_classify_intent(_state(message="Erkläre mir ISO 27001"))
    assert result["intent"] == "orientierer"


def test_classify_orientierer_art():
    result = node_classify_intent(_state(message="Was regelt Art. 28 DSGVO?"))
    assert result["intent"] == "orientierer"


def test_classify_orientierer_ai_act():
    result = node_classify_intent(_state(message="Was ist der AI Act Annex III?"))
    assert result["intent"] == "orientierer"


def test_classify_luecken_gaps_magic():
    result = node_classify_intent(_state(message="__gaps__"))
    assert result["intent"] == "luecken_fuehrer"


def test_classify_luecken_empty_message():
    result = node_classify_intent(_state(message=""))
    assert result["intent"] == "luecken_fuehrer"


def test_classify_luecken_keyword():
    result = node_classify_intent(_state(message="Was fehlt noch in meinem Projekt?"))
    assert result["intent"] == "luecken_fuehrer"


def test_classify_luecken_german_keyword():
    result = node_classify_intent(_state(message="Was sind die offenen Lücken?"))
    assert result["intent"] == "luecken_fuehrer"


def test_classify_unknown_routes_to_orientierer():
    # ADR-093: unknown messages default to orientierer (full-text graph search)
    result = node_classify_intent(_state(message="Hallo"))
    assert result["intent"] == "orientierer"

    result = node_classify_intent(_state(message="Wie ist das Wetter heute?"))
    assert result["intent"] == "orientierer"


def test_classify_scan_domain_sentinel_routes_to_empty():
    """Phase 2 magic string must be parsed but routed to empty until daten_sammler is implemented."""
    result = node_classify_intent(_state(message="__scan_domain:acme.example.com__"))
    assert result["intent"] == "empty"


# ── Unit: VALID_ACTION_TYPES filter ───────────────────────────────────────────

def test_proposed_actions_filter_unknown_types():
    """node_formulate_response must strip unknown action_types from proposed_actions."""
    state = _state(
        intent="orientierer",
        graph_context={"laws": [{"law": "DSGVO", "article": "Art. 5", "text": "Grundsätze..."}], "controls": [], "services": []},
        sources=["DSGVO:Art.5"],
    )
    with patch("src.workflow.assistant._call_ollama_assistant", return_value="Erklärung hier."):
        result = node_formulate_response(state)

    for action in result.get("proposed_actions", []):
        assert action["action_type"] in VALID_ACTION_TYPES, f"Invalid action_type: {action['action_type']}"


def test_valid_action_types_contains_expected():
    assert "navigate" in VALID_ACTION_TYPES
    assert "fill_field" in VALID_ACTION_TYPES
    assert "acknowledge" in VALID_ACTION_TYPES
    assert "ask_followup" in VALID_ACTION_TYPES


# ── Unit: Ollama fallback ──────────────────────────────────────────────────────

def test_ollama_unavailable_sets_error():
    state = _state(
        intent="orientierer",
        graph_context={"laws": [], "controls": [], "services": []},
    )
    with patch("src.workflow.assistant._call_ollama_assistant", side_effect=ConnectionRefusedError()):
        # _call_ollama_assistant catches exceptions internally — mock return None instead
        pass

    with patch("src.workflow.assistant._call_ollama_assistant", return_value=None):
        result = node_formulate_response(state)

    assert result.get("response") == ""
    assert "assistant_unavailable" in result.get("errors", [])


# ── Unit: empty intent static response ────────────────────────────────────────

def test_empty_intent_returns_static_no_ollama():
    """Empty intent must return a static response without calling Ollama."""
    state = _state(intent="empty")
    with patch("src.workflow.assistant._call_ollama_assistant") as mock_ollama:
        result = node_formulate_response(state)
        mock_ollama.assert_not_called()

    assert len(result.get("response", "")) > 10
    assert result.get("proposed_actions") == []


# ── Unit: no-scan early return ────────────────────────────────────────────────

def test_static_response_passes_through_formulate():
    """If a prior node wrote response (no-scan early return), formulate must pass through."""
    state = _state(
        intent="luecken_fuehrer",
        response="Kein Scan vorhanden.",
        proposed_actions=[{"action_type": "navigate", "label": "Scan starten", "payload": {"url": "/scan"}}],
    )
    with patch("src.workflow.assistant._call_ollama_assistant") as mock_ollama:
        result = node_formulate_response(state)
        mock_ollama.assert_not_called()

    assert result["response"] == "Kein Scan vorhanden."


# ── Integration: node_query_graph against live Neo4j ─────────────────────────

@requires_neo4j
def test_query_graph_iso27001():
    from src.workflow.assistant import node_query_graph
    state = _state(message="Was ist ISO 27001?", intent="orientierer")
    result = node_query_graph(state)
    ctx = result.get("graph_context", {})
    # At least controls or services should be non-empty for ISO 27001
    has_content = bool(ctx.get("controls")) or bool(ctx.get("laws")) or bool(ctx.get("services"))
    assert has_content, f"graph_context empty for 'Was ist ISO 27001?': {ctx}"


@requires_neo4j
def test_query_graph_article_lookup():
    from src.workflow.assistant import node_query_graph
    state = _state(message="Was sagt Art. 5 DSGVO?", intent="orientierer")
    result = node_query_graph(state)
    # sources should be populated
    assert isinstance(result.get("sources"), list)


# ── Integration: node_load_gaps against live Supabase ─────────────────────────

@requires_supabase
def test_load_gaps_returns_list():
    from src.workflow.assistant import node_load_gaps
    state = _state(project_name="lexscan-legal-risk-analyzer", intent="luecken_fuehrer")
    result = node_load_gaps(state)
    assert isinstance(result.get("gap_hints"), list)
    assert isinstance(result.get("detected_services"), list)
    assert isinstance(result.get("service_compliance_context"), dict)


# ── Unit: _resolve_service_names ──────────────────────────────────────────────

def test_resolve_service_names_matches_canonical():
    mock_gc = MagicMock()
    mock_gc.run_query.return_value = [
        {"input": "stripe", "canonical": "Stripe"},
        {"input": "AWS S3", "canonical": "AWS S3"},
    ]
    matched, unmatched = _resolve_service_names(mock_gc, ["stripe", "AWS S3", "unknownXYZ"])
    assert "Stripe" in matched
    assert "AWS S3" in matched
    assert "unknownXYZ" in unmatched
    assert len(matched) == 2


def test_resolve_service_names_empty_input():
    mock_gc = MagicMock()
    matched, unmatched = _resolve_service_names(mock_gc, [])
    assert matched == []
    assert unmatched == []
    mock_gc.run_query.assert_not_called()


# ── Unit: service block in node_formulate_response ───────────────────────────

def test_formulate_response_luecken_service_block_injected():
    from src.scanner.gap_analyzer import GapHint
    captured_prompt: list[str] = []

    def fake_ollama(prompt: str) -> str:
        captured_prompt.append(prompt)
        return "Testantwort."

    with patch("src.workflow.assistant._call_ollama_assistant", side_effect=fake_ollama):
        state = _state(
            intent="luecken_fuehrer",
            gap_hints=[
                GapHint(
                    field="company_name",
                    gap_reason="Missing.",
                    affected_docs=["AVV"],
                    fix_url="http://localhost:3000/project/test/company",
                    fix_label="Set company",
                    priority=1,
                )
            ],
            service_compliance_context={
                "docs_required": [
                    {"service": "Stripe", "doc_name_de": "Auftragsverarbeitungsvertrag", "doc_type": "AVV"},
                ]
            },
            detected_services_detail=[{"name": "Stripe", "evidence": []}],
        )
        result = node_formulate_response(state)

    assert captured_prompt, "Ollama was not called"
    prompt_used = captured_prompt[0]
    assert "Stripe" in prompt_used, "Service name missing from prompt"
    assert "Auftragsverarbeitungsvertrag" in prompt_used, "Doc name missing from prompt"
    assert result.get("response") == "Testantwort."


# ── Integration: node_formulate_response against live Ollama ─────────────────

@requires_ollama
def test_formulate_response_orientierer_returns_text():
    from src.workflow.assistant import node_formulate_response
    state = _state(
        intent="orientierer",
        message="Was ist eine TOM?",
        graph_context={
            "laws": [],
            "controls": [{"id": "ISO-27001-A5.1", "title": "Informationssicherheitsrichtlinie", "text": ""}],
            "services": [],
        },
        sources=["ISO_27001:ISO-27001-A5.1"],
    )
    result = node_formulate_response(state)
    assert len(result.get("response", "")) > 50, "Response too short — Ollama may not have answered"


@requires_ollama
def test_formulate_response_proposed_actions_valid():
    from src.workflow.assistant import node_formulate_response
    from src.scanner.gap_analyzer import GapHint
    state = _state(
        intent="luecken_fuehrer",
        gap_hints=[
            GapHint(
                field="company_name",
                gap_reason="Company name not configured.",
                affected_docs=["AVV", "TOM"],
                fix_url="http://localhost:3000/project/test/company",
                fix_label="Set company details",
                priority=1,
            )
        ],
    )
    result = node_formulate_response(state)
    for action in result.get("proposed_actions", []):
        assert action["action_type"] in VALID_ACTION_TYPES


# ── E2E: full graph invocation ────────────────────────────────────────────────

@requires_neo4j
@requires_ollama
def test_e2e_graph_orientierer():
    graph = build_assistant_workflow()
    initial: AssistantState = {
        "project_name": "test-project",
        "thread_id":    "asst-e2e-001",
        "message":      "Was ist eine TOM?",
        "intent":       "",
        "graph_context": {},
        "gap_hints":    [],
        "response":     "",
        "proposed_actions": [],
        "sources":      [],
        "intentionally_empty_fields": [],
        "errors":       [],
    }
    result = graph.invoke(initial)
    assert result["intent"] == "orientierer"
    assert len(result.get("response", "")) > 0
