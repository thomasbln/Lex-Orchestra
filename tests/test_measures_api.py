"""ADR-129 PR 1 — measures endpoint input validation (audit K9 + NTH).

Validation tests run without a DB: Literal/max_length reject at the Pydantic
layer (422 before the handler body), and the per-action guards fire before the
DB_URL check. The delete-rowcount test mocks psycopg2.
"""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

import src.interface.approve_api as api

client = TestClient(api.app, raise_server_exceptions=False)

RUN = "00000000-0000-0000-0000-000000000001"


def _post(payload: dict):
    return client.post(f"/scan/{RUN}/measures", json=payload)


def test_unknown_lang_rejected_422():
    r = _post({"action": "edit", "control_id": "LLM01", "lang": "fr", "text": "x"})
    assert r.status_code == 422


def test_unknown_action_rejected_422():
    r = _post({"action": "explode", "control_id": "LLM01"})
    assert r.status_code == 422


def test_overlong_text_rejected_422():
    r = _post({"action": "edit", "control_id": "LLM01", "text": "x" * 2001})
    assert r.status_code == 422


def test_overlong_title_rejected_422():
    r = _post({"action": "add", "title": "t" * 201, "text": "x"})
    assert r.status_code == 422


def test_edit_without_control_id_rejected_422():
    r = _post({"action": "edit", "text": "x"})
    assert r.status_code == 422


def test_add_without_title_rejected_422():
    r = _post({"action": "add", "text": "some measure text"})
    assert r.status_code == 422


def test_add_without_text_rejected_422():
    r = _post({"action": "add", "title": "Custom measure"})
    assert r.status_code == 422


def test_delete_reports_rowcount_of_measure_delete():
    """audit NTH: `updated` must reflect the owner_measures DELETE, not the
    deleted_controls cleanup that runs afterwards (which is usually 0 rows).

    PR N4 (re-audit B-8): rowcount was a static MagicMock attribute (always 1),
    so the test passed whether production read it after the first or the second
    DELETE. It now differs per statement — only the correct capture point passes."""
    cur = MagicMock()
    cur.fetchone.return_value = ("rand-industries",)

    def _execute(sql, params=None):
        s = " ".join(sql.split())
        if s.startswith("DELETE FROM owner_measures"):
            cur.rowcount = 1          # the measure delete — this is `updated`
        elif s.startswith("DELETE FROM deleted_controls"):
            cur.rowcount = 0          # cleanup usually hits nothing — the old bug read THIS
        else:
            cur.rowcount = -1
    cur.execute.side_effect = _execute
    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.cursor.return_value.__enter__.return_value = cur

    with patch.object(api, "DB_URL", "postgresql://mock"), \
         patch.object(api.psycopg2, "connect", return_value=conn), \
         patch.object(api, "_get_project_id_by_name", return_value="pid-1"):
        r = _post({"action": "delete", "control_id": "custom-abc12345"})

    assert r.status_code == 200
    body = r.json()
    assert body["updated"] == 1
    assert body["control_id"] == "custom-abc12345"


def test_internal_error_detail_is_generic():
    """audit NTH: 500 must not leak psycopg2 internals to the client."""
    with patch.object(api, "DB_URL", "postgresql://mock"), \
         patch.object(api.psycopg2, "connect", side_effect=RuntimeError("secret dsn detail")):
        r = _post({"action": "edit", "control_id": "LLM01", "text": "x"})
    assert r.status_code == 500
    assert "secret dsn detail" not in r.text
    assert r.json()["detail"] == "internal error"


# ── ADR-129 PR N5 (re-audit B-5/B-6): edit never empties ─────────────────────

def test_edit_without_text_and_title_rejected_422():
    """B-5: a text-less, title-less edit only flipped edited_flag/source — reject."""
    r = _post({"action": "edit", "control_id": "LLM01", "lang": "de"})
    assert r.status_code == 422


def _capture_edit_sql(payload):
    cur = MagicMock()
    cur.fetchone.return_value = ("rand-industries",)
    executed = []

    def _execute(sql, params=None):
        executed.append((" ".join(sql.split()), params))
        cur.rowcount = 1
    cur.execute.side_effect = _execute
    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.cursor.return_value.__enter__.return_value = cur
    with patch.object(api, "DB_URL", "postgresql://mock"), \
         patch.object(api.psycopg2, "connect", return_value=conn), \
         patch.object(api, "_get_project_id_by_name", return_value="pid-1"):
        r = _post(payload)
    assert r.status_code == 200
    return next(s for s, _ in executed if s.startswith("UPDATE owner_measures"))


def test_edit_title_only_cannot_null_the_body():
    """B-5: the UPDATE must coalesce text — a title-only edit keeps the body."""
    sql = _capture_edit_sql({"action": "edit", "control_id": "custom-abc12345",
                             "lang": "de", "title": "Neuer Titel"})
    assert "text = COALESCE(NULLIF(%s, ''), text)" in sql, \
        f"text can be NULLed by a title-only edit: {sql}"


def test_edit_empty_title_cannot_clobber():
    """B-6: '' is not a value — a cleared title keeps the old one (no anonymous
    doc row, no editor-invisible custom)."""
    sql = _capture_edit_sql({"action": "edit", "control_id": "custom-abc12345",
                             "lang": "de", "text": "T", "title": ""})
    assert "title = COALESCE(NULLIF(%s, ''), title)" in sql, \
        f"empty title clobbers the stored title: {sql}"
