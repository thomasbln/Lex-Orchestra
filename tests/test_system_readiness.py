"""First-start readiness (Launch-Gate 'Erstkontakt') — three lights + scan gate."""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

import src.interface.approve_api as api

client = TestClient(api.app, raise_server_exceptions=False)


def _mock_graph(count):
    gc = MagicMock()
    gc.run_query.return_value = [{"c": count}]
    return gc


def _pg_returning(pg, value):
    pg.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value.fetchone.return_value = value


def test_readiness_all_green(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "local")
    monkeypatch.setenv("OLLAMA_MODEL", "gemma4:e4b")
    tags = MagicMock()
    tags.json.return_value = {"models": [{"name": "gemma4:e4b"}]}
    tags.raise_for_status.return_value = None
    with patch.object(api, "_get_graph_client", return_value=_mock_graph(474)), \
         patch.object(api, "DB_URL", "postgresql://x"), \
         patch.object(api.psycopg2, "connect") as pg, \
         patch.object(api.http_requests, "get", return_value=tags):
        _pg_returning(pg, (True,))
        r = client.get("/system/readiness")
    assert r.status_code == 200
    body = r.json()
    assert body["ready"] is True
    assert body["checks"]["graph"]["detail"] == "474 nodes"
    assert r.headers["cache-control"] == "no-store"


def test_readiness_model_missing_is_honest(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "local")
    tags = MagicMock()
    tags.json.return_value = {"models": []}
    tags.raise_for_status.return_value = None
    with patch.object(api, "_get_graph_client", return_value=_mock_graph(474)), \
         patch.object(api, "DB_URL", "postgresql://x"), \
         patch.object(api.psycopg2, "connect") as pg, \
         patch.object(api.http_requests, "get", return_value=tags):
        _pg_returning(pg, (True,))
        body = client.get("/system/readiness").json()
    assert body["ready"] is False
    assert "pull likely in progress" in body["checks"]["llm"]["detail"]


def test_readiness_llm_model_override_probe(monkeypatch):
    """Read-only test hook: probe a nonexistent model without touching the real one."""
    monkeypatch.setenv("LLM_BACKEND", "local")
    tags = MagicMock()
    tags.json.return_value = {"models": [{"name": "gemma4:e4b"}]}
    tags.raise_for_status.return_value = None
    with patch.object(api, "_get_graph_client", return_value=_mock_graph(474)), \
         patch.object(api, "DB_URL", "postgresql://x"), \
         patch.object(api.psycopg2, "connect") as pg, \
         patch.object(api.http_requests, "get", return_value=tags):
        _pg_returning(pg, (True,))
        body = client.get("/system/readiness?llm_model=nonexistent:model").json()
    assert body["ready"] is False
    assert body["checks"]["llm"]["ok"] is False


def test_readiness_graph_empty_names_the_fix():
    with patch.object(api, "_get_graph_client", return_value=_mock_graph(0)):
        body = api._system_readiness()
    assert body["checks"]["graph"]["ok"] is False
    assert "make seed-all" in body["checks"]["graph"]["detail"]


def test_scan_gate_refuses_while_preparing():
    not_ready = {"ready": False, "checks": {"llm": {"ok": False, "detail": "x"},
                                            "graph": {"ok": True, "detail": "y"},
                                            "database": {"ok": True, "detail": "z"}}}
    with patch.object(api, "_system_readiness", return_value=not_ready), \
         patch.object(api, "DB_URL", "postgresql://x"), \
         patch.object(api.psycopg2, "connect") as pg:
        _pg_returning(pg, ("https://github.com/x/y",))
        r = client.post("/scan", json={"project_name": "p", "dry_run": False})
    assert r.status_code == 503
    assert r.json()["detail"] == "system preparing: llm"


def test_scan_gate_lets_dry_run_through():
    """infra-check uses dry_run — it must not need graph/LLM readiness."""
    with patch.object(api, "_system_readiness") as ready_probe, \
         patch.object(api, "DB_URL", "postgresql://x"), \
         patch.object(api.psycopg2, "connect") as pg:
        _pg_returning(pg, ("https://github.com/x/y",))
        r = client.post("/scan", json={"project_name": "p", "dry_run": True})
    ready_probe.assert_not_called()
    assert r.status_code in (200, 500)  # gate skipped; downstream may fail in mock env
