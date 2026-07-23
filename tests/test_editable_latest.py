"""Row 58 (2026-07-19) — "latest editable run" must not depend on started_at alone.

Direct-path runs (pipeline `_write_scan_result` without the POST /scan lifecycle)
historically wrote started_at=NULL; `ORDER BY started_at DESC NULLS LAST` then
demoted the real newest snapshot run and the measures button pointed at an old
run. Guards (mutation pattern — reverting either fix turns them red):

1. the editable query coalesces started_at with completed_at,
2. `_write_scan_result` sets started_at itself and keeps an existing value.
"""

import inspect
from unittest.mock import MagicMock, patch

import src.interface.approve_api as approve_api
import src.workflow.main as wf_main


def test_editable_query_coalesces_started_at():
    src = inspect.getsource(approve_api.list_docs)
    assert "COALESCE(sr.started_at, sr.completed_at)" in src, (
        "editable_run_ids query must order by COALESCE(started_at, completed_at) — "
        "started_at alone demotes direct-path runs (NULLS LAST, row 58)"
    )


def test_runs_meta_query_coalesces_started_at():
    src = inspect.getsource(approve_api._scan_runs_meta)
    assert "COALESCE(started_at, completed_at)" in src, (
        "scan-select runs[] metadata (shared /docs+/logs helper) must sort by "
        "COALESCE(started_at, completed_at)"
    )


def test_write_scan_result_sets_started_at_defensively():
    """The SQL actually executed must insert started_at and keep an existing one."""
    captured: list[str] = []

    fake_cur = MagicMock()
    fake_cur.execute.side_effect = lambda sql, *a, **k: captured.append(sql)
    fake_conn = MagicMock()
    fake_conn.__enter__.return_value = fake_conn
    fake_conn.cursor.return_value.__enter__.return_value = fake_cur

    state = {
        "run_id": "00000000-0000-0000-0000-000000000000",
        "project_name": "guard-test",
        "graph_result": {}, "scout_result": {},
    }
    with patch.object(wf_main, "DB_URL", "postgresql://guard"), \
         patch.object(wf_main.psycopg2, "connect", return_value=fake_conn), \
         patch.object(wf_main, "_get_project_id", return_value=None):
        wf_main._write_scan_result(state)  # type: ignore[arg-type]

    insert_sql = next((s for s in captured if "INSERT INTO scan_results" in s), None)
    assert insert_sql is not None, "no scan_results INSERT executed"
    assert "started_at" in insert_sql.split("VALUES")[0], (
        "direct-path INSERT must set started_at itself"
    )
    assert "COALESCE(scan_results.started_at, EXCLUDED.started_at)" in insert_sql, (
        "ON CONFLICT must keep the lifecycle's original started_at and only fill NULL"
    )
