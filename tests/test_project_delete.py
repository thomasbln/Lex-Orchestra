"""ADR-125: Project deletion — hard delete + full Vault/filesystem cleanup.

DB-free unit tests for the deletion path in src/interface/approve_api.py:

1. _resolve_project_id is read-only (SELECT only, never an INSERT stub).
2. _collect_run_ids unions across the three run_id-bearing tables.
3. _collect_secret_ids gathers vault refs and drops NULLs.
4. _safe_draft_files matches by run_id whitelist AND blocks symlink escape
   via realpath containment (not a string-prefix check).
5. delete_project deletes files BEFORE the DB rows, and is self-healing when
   a file is already gone (no crash).
6. delete-preview returns blast-radius counts and 404s on a missing project.

These tests mock the DB layer with a fake cursor/connection so they run without
a live Supabase. A real-DB roundtrip lives in the integration suite.
"""
from __future__ import annotations

import os

import pytest

from src.interface import approve_api as api


PID = "11111111-1111-1111-1111-111111111111"
RID = "2d579cb5-aaaa-bbbb-cccc-000000000000"
SID = "99999999-9999-9999-9999-999999999999"


# ── Fake DB layer ───────────────────────────────────────────────────────────

class FakeCursor:
    """Minimal psycopg2 cursor: matches a query against a script of
    (substring → rows) and records execution order."""

    def __init__(self, script, events, on_execute=None):
        self._script = script            # list[(substr, rows)]
        self.events = events             # shared list of normalised SQL
        self._on_execute = on_execute
        self._last: list = []
        self.rowcount = 0

    def execute(self, query, params=None):
        norm = " ".join(query.split())
        self.events.append(norm)
        self._last = []
        self.rowcount = 0
        for substr, rows in self._script:
            if substr in norm:
                self._last = rows
                self.rowcount = len(rows)
                break
        if self._on_execute:
            self._on_execute(norm, params)

    def fetchone(self):
        return self._last[0] if self._last else None

    def fetchall(self):
        return list(self._last)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _patch_db(monkeypatch, cursor):
    monkeypatch.setattr(api, "DB_URL", "postgres://fake")
    monkeypatch.setattr(api.psycopg2, "connect", lambda _url: FakeConn(cursor))


# ── 1. Read-only resolver (no stub insert) ──────────────────────────────────

def test_resolve_project_id_returns_uuid_select_only():
    events: list[str] = []
    cur = FakeCursor([("id FROM project_config WHERE project_name", [(PID,)])], events)
    assert api._resolve_project_id("some-project", cur) == PID
    # Exactly one statement, and it is a SELECT — never an INSERT stub.
    assert len(events) == 1
    assert events[0].startswith("SELECT")
    assert "INSERT" not in events[0]


def test_resolve_project_id_missing_returns_none_no_insert():
    events: list[str] = []
    cur = FakeCursor([], events)  # no row matches
    assert api._resolve_project_id("ghost", cur) is None
    assert all("INSERT" not in e for e in events)


# ── 2. + 3. Collection helpers ──────────────────────────────────────────────

def test_collect_run_ids_unions_three_tables():
    events: list[str] = []
    other = "2d579cb5-eeee-ffff-0000-111111111111"
    cur = FakeCursor(
        [
            ("run_id FROM scan_results", [(RID,), (other,)]),
            ("run_id FROM generated_docs", [(RID,)]),  # duplicate collapses
            ("run_id FROM scan_signals", []),
        ],
        events,
    )
    assert api._collect_run_ids(cur, PID) == {RID, other}


def test_collect_secret_ids_drops_nulls():
    events: list[str] = []
    cur = FakeCursor(
        [
            ("api_key_secret_id FROM project_integrations", [(SID,)]),
            ("github_token_secret_id FROM project_tokens", [(None,)]),
            ("github_token_secret_id FROM project_repos", [(None,)]),
        ],
        events,
    )
    assert api._collect_secret_ids(cur, PID) == {SID}


# ── 4. Filesystem containment (security) ────────────────────────────────────

def test_safe_draft_files_matches_run_id_and_ignores_others(tmp_path, monkeypatch):
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    hit = drafts / "avv_2d579cb5.md"
    hit.write_text("x")
    (drafts / "tom_ffffffff.md").write_text("x")  # non-matching run_id
    monkeypatch.setattr(api, "LEGAL_DRAFTS_DIR", drafts)

    result = api._safe_draft_files({RID})
    names = {p.name for p in result}
    assert "avv_2d579cb5.md" in names
    assert "tom_ffffffff.md" not in names


def test_safe_draft_files_blocks_symlink_escape(tmp_path, monkeypatch):
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text("do not touch")

    # A symlink inside drafts whose NAME matches the run_id but resolves outside.
    evil = drafts / "avv_2d579cb5_evil.md"
    evil.symlink_to(secret)
    monkeypatch.setattr(api, "LEGAL_DRAFTS_DIR", drafts)

    result = api._safe_draft_files({RID})
    # realpath containment excludes the escaping symlink; the outside file survives.
    assert all(p.name != "avv_2d579cb5_evil.md" for p in result)
    assert secret.exists()


def test_safe_draft_files_missing_dir_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "LEGAL_DRAFTS_DIR", tmp_path / "does-not-exist")
    assert api._safe_draft_files({RID}) == []


def test_safe_draft_files_empty_run_ids_returns_empty(tmp_path, monkeypatch):
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    (drafts / "avv_2d579cb5.md").write_text("x")
    monkeypatch.setattr(api, "LEGAL_DRAFTS_DIR", drafts)
    assert api._safe_draft_files(set()) == []


# ── 5. delete_project order + self-healing ──────────────────────────────────

def _delete_script(docs=2, signals=1, scans=1):
    return [
        ("id FROM project_config WHERE project_name", [(PID,)]),
        ("run_id FROM scan_results", [(RID,)]),
        ("run_id FROM generated_docs", []),
        ("run_id FROM scan_signals", []),
        ("api_key_secret_id FROM project_integrations", [(SID,)]),
        ("github_token_secret_id FROM project_tokens", []),
        ("github_token_secret_id FROM project_repos", []),
        ("DELETE FROM generated_docs", [(1,)] * docs),   # rowcount = docs
        ("DELETE FROM scan_signals", [(1,)] * signals),
        ("DELETE FROM scan_results", [(1,)] * scans),
    ]


def test_delete_project_removes_files_before_db_rows(tmp_path, monkeypatch):
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    draft = drafts / "avv_2d579cb5.md"
    draft.write_text("x")
    monkeypatch.setattr(api, "LEGAL_DRAFTS_DIR", drafts)

    def assert_file_gone_before_db(norm, params):
        # When the first DB row delete fires, the file must already be unlinked.
        if norm.startswith("DELETE FROM generated_docs"):
            assert not draft.exists(), "DB delete ran before filesystem cleanup"

    events: list[str] = []
    cur = FakeCursor(_delete_script(), events, on_execute=assert_file_gone_before_db)
    _patch_db(monkeypatch, cur)

    out = api.delete_project("some-project")

    assert out["ok"] is True
    assert out["deleted"] == {
        "scans": 1, "signals": 1, "docs": 2, "vault_secrets": 1, "files": 1,
    }
    assert not draft.exists()
    # Vault delete precedes the project_config delete; project_config is last.
    deletes = [e for e in events if e.startswith("DELETE")]
    assert deletes[0].startswith("DELETE FROM vault.secrets")
    assert deletes[-1].startswith("DELETE FROM project_config")


def test_delete_project_self_heals_when_file_already_gone(tmp_path, monkeypatch):
    drafts = tmp_path / "drafts"
    drafts.mkdir()  # no draft file present — simulates a prior partial run
    monkeypatch.setattr(api, "LEGAL_DRAFTS_DIR", drafts)

    events: list[str] = []
    cur = FakeCursor(_delete_script(), events)
    _patch_db(monkeypatch, cur)

    out = api.delete_project("some-project")
    assert out["ok"] is True
    assert out["deleted"]["files"] == 0  # nothing on disk, no crash


def test_delete_project_404_when_missing(monkeypatch):
    events: list[str] = []
    cur = FakeCursor([], events)  # resolver finds nothing
    _patch_db(monkeypatch, cur)
    with pytest.raises(api.HTTPException) as exc:
        api.delete_project("ghost")
    assert exc.value.status_code == 404


# ── 6. delete-preview ───────────────────────────────────────────────────────

def test_delete_preview_returns_counts(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "LEGAL_DRAFTS_DIR", tmp_path / "drafts")  # no files
    events: list[str] = []
    cur = FakeCursor(
        [
            ("id FROM project_config WHERE project_name", [(PID,)]),
            ("COUNT(*) FROM scan_results", [(3,)]),
            ("COUNT(*) FROM scan_signals", [(11,)]),
            ("COUNT(*) FROM generated_docs", [(8,)]),
            ("api_key_secret_id FROM project_integrations", [(SID,)]),
            ("github_token_secret_id FROM project_tokens", []),
            ("github_token_secret_id FROM project_repos", []),
            ("run_id FROM scan_results", []),
            ("run_id FROM generated_docs", []),
            ("run_id FROM scan_signals", []),
        ],
        events,
    )
    _patch_db(monkeypatch, cur)

    out = api.project_delete_preview("some-project")
    assert out == {
        "project_name": "some-project",
        "scans": 3, "signals": 11, "docs": 8,
        "vault_secrets": 1, "files": 0,
    }


def test_delete_preview_404_when_missing(monkeypatch):
    events: list[str] = []
    cur = FakeCursor([], events)
    _patch_db(monkeypatch, cur)
    with pytest.raises(api.HTTPException) as exc:
        api.project_delete_preview("ghost")
    assert exc.value.status_code == 404
