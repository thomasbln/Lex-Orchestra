"""ADR-129 PR 4 — honest failed status: node guard, error propagation, reaper (audit K3)."""
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import src.interface.approve_api as api
import src.workflow.main as wf

client = TestClient(api.app, raise_server_exceptions=False)
RUN = "00000000-0000-0000-0000-00000000000b"


# ── _node_guard ──────────────────────────────────────────────────────────────

def test_node_guard_patches_failed_and_reraises():
    def broken_node(state):
        raise RuntimeError("supabase down")

    guarded = wf._node_guard("scout", broken_node)
    with patch.object(wf, "_update_step") as upd:
        with pytest.raises(RuntimeError, match="supabase down"):
            guarded({"run_id": RUN})
    upd.assert_called_once()
    kwargs = upd.call_args.kwargs
    assert kwargs["status"] == "failed"
    assert kwargs["error"].startswith("scout: ")
    assert upd.call_args.args[0] == RUN


def test_node_guard_transparent_on_success():
    guarded = wf._node_guard("scout", lambda s: {"ok": True})
    with patch.object(wf, "_update_step") as upd:
        assert guarded({"run_id": RUN}) == {"ok": True}
    upd.assert_not_called()


# ── _update_step error payload ───────────────────────────────────────────────

def test_update_step_sends_error_in_payload():
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["data"] = json.loads(req.data.decode("utf-8"))
        m = MagicMock()
        m.read.return_value = b""
        return m

    with patch.object(wf._urllib_request, "urlopen", side_effect=fake_urlopen):
        wf._update_step(RUN, status="failed", error="x" * 600)

    assert captured["data"]["status"] == "failed"
    assert captured["data"]["error"] == "x" * 500  # truncated to 500


# ── PATCH /scan/{run_id}/step persists error ─────────────────────────────────

def test_patch_step_persists_error_column():
    cur = MagicMock()
    cur.fetchone.return_value = (RUN,)
    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.cursor.return_value.__enter__.return_value = cur

    with patch.object(api, "SCAN_INTERNAL_SECRET", ""), \
         patch.object(api, "DB_URL", "postgresql://mock"), \
         patch.object(api.psycopg2, "connect", return_value=conn):
        r = client.patch(f"/scan/{RUN}/step", json={"status": "failed", "error": "graph_unavailable"})

    assert r.status_code == 200
    params = cur.execute.call_args.args[1]
    assert "graph_unavailable" in params
    assert "error" in cur.execute.call_args.args[0]  # SQL sets the error column


# ── reaper ───────────────────────────────────────────────────────────────────

def test_reap_stale_scan_runs_updates_with_reason():
    cur = MagicMock()
    cur.rowcount = 2
    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.cursor.return_value.__enter__.return_value = cur

    with patch.object(api, "DB_URL", "postgresql://mock"), \
         patch.object(api.psycopg2, "connect", return_value=conn):
        api._reap_stale_scan_runs(reason="stale_running")

    sql = cur.execute.call_args.args[0]
    assert "status = 'failed'" in sql
    assert cur.execute.call_args.args[1] == ("stale_running",)


# ── ADR-129 PR 5 — validator merges errors instead of overwriting ───────────

def test_validator_exception_merges_prior_errors():
    state = {
        "generated_docs": [{"id": "d1"}],
        "dry_run": False,
        "project_name": "rand-industries",
        "errors": ["Graph: down"],
    }
    with patch("src.agents.document_validator.DocumentValidator") as dv:
        dv.return_value.validate_all.side_effect = RuntimeError("boom")
        out = wf.node_document_validator(state)
    assert out["errors"][0] == "Graph: down"          # prior error preserved
    assert out["errors"][1].startswith("Validator: ")  # new error appended


def test_validator_no_partial_error_returns_elsewhere():
    """Guard: no OTHER node returns a partial dict carrying an 'errors' key
    without merging — the validator is the only partial-returning node."""
    import inspect, re
    src = inspect.getsource(wf)
    # every `return {...}` containing an errors key must also reference state.get("errors"
    partial_error_returns = re.findall(r'return \{[^}]*"errors":[^}]*\}', src)
    for ret in partial_error_returns:
        assert 'state.get("errors"' in ret, f"unmerged partial errors return: {ret}"


# ── ADR-129 PR 6 — Neo4j down → failed + 0 docs, never 'complete' ───────────

def test_graph_failed_skips_docgen_and_fails_run():
    state = {
        "run_id": RUN, "project_name": "rand-industries", "dry_run": False,
        "graph_result": {"services": [], "controls": [], "_graph_failed": True},
        "errors": ["Graph: connection refused"],
    }
    with patch.object(wf, "_update_step") as upd, \
         patch.object(wf, "_write_scan_result") as wsr, \
         patch.object(wf, "_write_measure_snapshot") as wms:
        out = wf.node_document_architect(state)

    assert out["generated_docs"] == []
    wsr.assert_not_called()
    wms.assert_not_called()
    statuses = [c.kwargs.get("status") for c in upd.call_args_list]
    assert "failed" in statuses and "complete" not in statuses
    failed_call = [c for c in upd.call_args_list if c.kwargs.get("status") == "failed"][0]
    assert "graph_unavailable" in failed_call.kwargs["error"]


def test_graph_ok_path_still_reaches_docgen():
    """Guard: without the flag the architect proceeds (mocked orchestrator)."""
    state = {
        "run_id": RUN, "project_name": "rand-industries", "dry_run": True,
        "graph_result": {"services": [], "controls": []},
        "errors": [],
    }
    with patch.object(wf, "_update_step") as upd:
        out = wf.node_document_architect(state)   # dry_run short-circuit is fine here
    statuses = [c.kwargs.get("status") for c in upd.call_args_list]
    assert "complete" in statuses


# ── ADR-129 PR 7 — wait-timeout must not clobber a completed run ─────────────

# PR N4 (re-audit B-8): these two tests previously re-implemented the guard in
# the test body and asserted on their own copy — deleting the production guard
# left them green. They now exercise the REAL _trigger_langgraph_scan except
# branch: an HTTP failure on the LangGraph wait triggers the flicker guard.

def _trigger_with_wait_error(status):
    with patch.object(api.http_requests, "post",
                      side_effect=RuntimeError("simulated wait timeout")), \
         patch.object(api, "_scan_results_status", return_value=status), \
         patch.object(api, "_scan_results_mark_failed") as mf:
        api._trigger_langgraph_scan("proj", "https://github.com/x/y", False, RUN)
    return mf


def test_wait_error_skips_mark_failed_when_run_completed():
    mf = _trigger_with_wait_error("complete")
    mf.assert_not_called()


def test_wait_error_marks_failed_when_still_running():
    mf = _trigger_with_wait_error("running")
    mf.assert_called_once()
    assert mf.call_args.args[0] == RUN


def test_wait_error_marks_failed_when_status_unknown():
    mf = _trigger_with_wait_error(None)
    mf.assert_called_once()


def test_scan_wait_timeout_default_generous():
    assert api.SCAN_WAIT_TIMEOUT >= 1800


# ── ADR-129 PR 8 — assistant disabled by default (chat-off v1.0) ─────────────

def test_assistant_message_disabled_returns_503():
    r = client.post("/assistant/message", json={"project_name": "rand-industries", "message": "hi"})
    assert r.status_code == 503
    assert "assistant_disabled" in r.text


def test_assistant_gaps_disabled_returns_503():
    r = client.get("/assistant/gaps/rand-industries")
    assert r.status_code == 503
    assert "assistant_disabled" in r.text


def test_assistant_enabled_flag_defaults_off():
    assert api.ASSISTANT_ENABLED is False


# ── _classify_scan_error (Launch-Gate row 51) ────────────────────────────────

def test_classify_timeout_names_the_budget():
    import requests
    msg = api._classify_scan_error(requests.exceptions.Timeout("read timed out"))
    assert msg.startswith(f"timeout after {api.SCAN_WAIT_TIMEOUT}s")


def test_classify_neo4j_class_is_specific_without_dsn():
    e = RuntimeError("Couldn't connect to bolt://neo4j:7687 (resolved to ...)")
    assert api._classify_scan_error(e) == "Neo4j unreachable"


def test_classify_ollama_class():
    e = RuntimeError("HTTPConnectionPool(host='ollama', port=11434): Max retries")
    assert api._classify_scan_error(e) == "LLM backend unreachable"


def test_classify_langgraph_connection_error():
    import requests
    e = requests.exceptions.ConnectionError("Connection refused")
    assert api._classify_scan_error(e) == "scan engine unreachable (LangGraph)"


def test_classify_unknown_is_generic_and_leaks_nothing():
    # dummy DSN uses the canonical whitelisted fixture form (user:password@localhost)
    e = RuntimeError("invalid input syntax for type uuid: postgresql://user:password@localhost/db")
    msg = api._classify_scan_error(e)
    assert msg == "internal error (see logs)"
    assert "postgresql" not in msg and "password" not in msg


# ── docgen crash / silent-empty must not end 'complete' (row 16 / audit K3) ──

def _docgen_state():
    return {"run_id": RUN, "project_name": "t", "dry_run": False,
            "graph_result": {"services": []}, "risk_signals": [], "errors": []}


def test_docgen_crash_marks_failed_not_complete():
    with patch.object(wf, "_update_step") as upd, \
         patch.object(wf, "_write_scan_result"), \
         patch.object(wf, "_write_measure_snapshot"), \
         patch("src.agents.document_architect.DocumentOrchestrator") as orch:
        orch.return_value.generate_all.side_effect = RuntimeError("jinja exploded")
        state = wf.node_document_architect(_docgen_state())
    assert state["generated_docs"] == []
    statuses = [c.kwargs.get("status") for c in upd.call_args_list]
    assert "failed" in statuses and "complete" not in statuses
    failed_call = [c for c in upd.call_args_list if c.kwargs.get("status") == "failed"][0]
    assert "jinja" not in failed_call.kwargs.get("error", "")  # no raw text on status page


def test_docgen_silent_empty_marks_failed():
    with patch.object(wf, "_update_step") as upd, \
         patch.object(wf, "_write_scan_result"), \
         patch.object(wf, "_write_measure_snapshot"), \
         patch("src.agents.document_architect.DocumentOrchestrator") as orch:
        orch.return_value.generate_all.return_value = []
        orch.return_value._write_scan_report.side_effect = RuntimeError("no report either")
        state = wf.node_document_architect(_docgen_state())
    assert state["generated_docs"] == []
    statuses = [c.kwargs.get("status") for c in upd.call_args_list]
    assert "failed" in statuses and "complete" not in statuses
