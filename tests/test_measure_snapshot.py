"""ADR-129 PR 2 — _write_measure_snapshot error-path behaviour (audit K1/K2).

The inheritance lookup is best-effort. On any failure the snapshot must
(a) roll back the aborted transaction so the graph-default INSERTs still land,
and (b) reset prev_run so the unconditional custom-carry cannot commit a
half-inherited state. Happy path: unchanged (covered by golden/E2E elsewhere).
"""
from unittest.mock import MagicMock, patch

import src.workflow.main as wf


def _state(n_controls: int = 3) -> dict:
    controls = [
        {"control_id": f"C{i}", "framework": "BSI_Grundschutz",
         "title_de": f"Control {i}", "default_tom_measure": f"Measure {i}"}
        for i in range(n_controls)
    ]
    return {
        "graph_result": {"controls": controls},
        "run_id": "00000000-0000-0000-0000-00000000000a",
        "project_name": "rand-industries",
    }


def _mock_conn(cur: MagicMock) -> MagicMock:
    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.cursor.return_value.__enter__.return_value = cur
    return conn


def _executed_sql(cur: MagicMock) -> list[str]:
    return [str(c.args[0]) for c in cur.execute.call_args_list if c.args]


def test_lookup_fail_still_writes_full_default_snapshot():
    """Test A: inheritance SELECT throws → rollback once, all default rows written,
    no custom-carry SELECT, no InFailedSqlTransaction cascade."""
    cur = MagicMock()
    calls = {"n": 0}

    def execute(sql, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:                      # first execute = inheritance SELECT
            raise RuntimeError("supabase hiccup")
        return None

    cur.execute.side_effect = execute
    cur.fetchall.return_value = []
    conn = _mock_conn(cur)

    with patch.object(wf, "DB_URL", "postgresql://mock"), \
         patch.object(wf.psycopg2, "connect", return_value=conn), \
         patch.object(wf, "_get_project_id", return_value="pid-1"):
        wf._write_measure_snapshot(_state(3))

    conn.rollback.assert_called_once()
    sql = _executed_sql(cur)
    inserts = [s for s in sql if "INSERT INTO owner_measures" in s]
    assert len(inserts) == 3                     # all graph-default rows written
    assert not any("custom-%" in s for s in sql)  # carry skipped (prev_run reset)
    conn.commit.assert_called_once()


def test_partial_fail_skips_custom_carry_entirely():
    """Test B: prev-run SELECT succeeds, edits SELECT throws → prev_run is reset,
    custom-carry skipped, snapshot still complete (no half-inherited state)."""
    cur = MagicMock()
    calls = {"n": 0}

    def execute(sql, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:                      # 1=prev-run SELECT ok, 2=edits SELECT fails
            raise RuntimeError("edits query broke")
        return None

    cur.execute.side_effect = execute
    cur.fetchone.return_value = ("11111111-1111-1111-1111-111111111111",)
    cur.fetchall.return_value = []
    conn = _mock_conn(cur)

    with patch.object(wf, "DB_URL", "postgresql://mock"), \
         patch.object(wf.psycopg2, "connect", return_value=conn), \
         patch.object(wf, "_get_project_id", return_value="pid-1"):
        wf._write_measure_snapshot(_state(2))

    conn.rollback.assert_called_once()
    sql = _executed_sql(cur)
    inserts = [s for s in sql if "INSERT INTO owner_measures" in s]
    assert len(inserts) == 2                     # full default snapshot
    assert not any("custom-%" in s for s in sql)  # carry NOT run on partial state
    conn.commit.assert_called_once()


def test_happy_path_inherits_edits_and_customs():
    """Guard: the fix must not change the happy path — edits inherited, carry runs."""
    cur = MagicMock()
    cur.fetchone.return_value = ("11111111-1111-1111-1111-111111111111",)
    # fetchall calls in order: prior edits, prior deleted, custom rows
    cur.fetchall.side_effect = [
        [("C0", "de", "owner text", "owner")],   # prior_edits
        [],                                       # prior_deleted
        [("custom-abc12345", "de", "txt", "Titel", "Custom")],  # custom rows
    ]
    conn = _mock_conn(cur)

    with patch.object(wf, "DB_URL", "postgresql://mock"), \
         patch.object(wf.psycopg2, "connect", return_value=conn), \
         patch.object(wf, "_get_project_id", return_value="pid-1"):
        wf._write_measure_snapshot(_state(2))

    conn.rollback.assert_not_called()
    sql = _executed_sql(cur)
    assert any("custom-%" in s for s in sql)      # carry ran
    inserts = [s for s in sql if "INSERT INTO owner_measures" in s]
    assert len(inserts) == 3                      # 2 defaults + 1 custom carry
    conn.commit.assert_called_once()
