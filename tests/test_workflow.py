"""
Tests: LangGraph Workflow — src/workflow/main.py
=================================================
Verifies:
  1. Workflow compiles without error
  2. Dry-run completes all 5 nodes with zero errors
  3. Scout fallback detects services from test fixtures
  4. Graph enrichment returns a result (even if empty)
  5. No PII leaks into graph_result (ADR-001)
  6. Checkpointer persists state to Supabase
  7. LangGraph Server responds at /ok (ADR-002 — server mode)
"""

import os
import uuid

import pytest
from src.workflow.main import build_workflow, LexState


@pytest.fixture(scope="module")
def app():
    """Workflow without checkpointer for fast unit tests."""
    return build_workflow(use_checkpointer=False)


def _base_state(project="test-project", repo_url="tests/fixtures", dry_run=True) -> LexState:
    return {
        "project_name":      project,
        "repo_url":          repo_url,
        "live_url":          None,
        "scan_depth":        "quick",
        "dry_run":           dry_run,
        "scout_result":       None,
        "security_findings":  None,
        "deployment_signals": None,
        "graph_result":       None,
        "reasoning_result":  None,
        "generated_docs":    [],
        "notification_sent":        False,
        "run_id":                   str(uuid.uuid4()),
        "errors":                   [],
        "validation_result":        None,
        "config_requested":         False,
        "validator_retries":        0,
        "pending_telegram_message": None,
    }


def test_workflow_builds(app):
    """Workflow compiles and returns a runnable graph."""
    assert app is not None


def test_dry_run_completes(app):
    """Dry-run passes all 5 nodes with zero errors."""
    result = app.invoke(_base_state())
    assert result["errors"] == [], f"Unexpected errors: {result['errors']}"


def test_scout_finds_fixtures(app):
    """Scout fallback detects services from tests/fixtures/."""
    result = app.invoke(_base_state(repo_url="tests/fixtures"))
    scout = result.get("scout_result") or {}
    assert scout.get("total_found", 0) > 0, "Scout found no services in fixtures"


def test_graph_enrichment_runs(app):
    """Graph enrichment completes and returns required fields."""
    result = app.invoke(_base_state())
    graph = result.get("graph_result")
    assert graph is not None
    assert "doc_types" in graph
    assert "overall_risk" in graph


def test_reasoning_result_present(app):
    """Reasoning result is populated after dry-run."""
    result = app.invoke(_base_state())
    reasoning = result.get("reasoning_result")
    assert reasoning is not None
    assert "summary" in reasoning


def test_no_pii_in_graph_result(app):
    """ADR-001: graph_result must not contain real asset names from fixtures."""
    result = app.invoke(_base_state(repo_url="tests/fixtures"))

    import json
    graph_str = json.dumps(result.get("graph_result") or {}).lower()

    # These values appear in tests/fixtures/env.example — must never reach graph_result
    forbidden = ["stripe_secret_key", "sk-live", "ghp_", "supersecret"]
    for term in forbidden:
        assert term not in graph_str, \
            f"PII leak detected in graph_result: '{term}' — ADR-001 violated"


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL checkpointer needs DATABASE_URL — integration test",
)
def test_with_checkpointer():
    """Workflow with PostgreSQL checkpointer stores state without error."""
    app = build_workflow(use_checkpointer=True)
    state = _base_state()
    config = {"configurable": {"thread_id": state["run_id"]}}
    result = app.invoke(state, config=config)
    assert result["errors"] == []


def test_langgraph_server_health():
    """ADR-002: LangGraph Server responds at GET /ok when running in server mode."""
    import requests
    import os

    server_url = os.getenv("LANGGRAPH_SERVER_URL", "http://localhost:8000")
    try:
        resp = requests.get(f"{server_url}/ok", timeout=5)
        assert resp.status_code == 200, f"Server returned {resp.status_code}"
    except requests.exceptions.ConnectionError:
        pytest.skip("LangGraph Server not running — start lex-agent container first")
