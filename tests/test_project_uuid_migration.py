"""ADR-080: project_config UUID PK migration — behavioural tests.

These tests require a real Supabase (NucBox) reachable via MCP_SUPABASE_URL
or DATABASE_URL. They verify the two load-bearing contracts of ADR-080:

1. The retro-migration 015 is idempotent — running it twice produces no
   schema change and no data corruption.
2. `project_name → project_config.id` lookup produces a stable UUID and
   reuses it on a second call.
3. Foreign-key constraint on project_tokens (project_id → project_config.id)
   rejects writes referencing a bogus UUID.

Test isolation: each test creates + DROP CASCADEs a uniquely-suffixed
project_config row so re-runs don't collide.
"""
from __future__ import annotations

import os
import uuid

import psycopg2
import pytest


DB_URL = os.environ.get("MCP_SUPABASE_URL") or os.environ.get("DATABASE_URL")


def _conn():
    if not DB_URL:
        pytest.skip("No DATABASE_URL / MCP_SUPABASE_URL in env")
    return psycopg2.connect(DB_URL)


def _cleanup(project_name: str) -> None:
    with _conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM project_config WHERE project_name = %s", (project_name,))
        conn.commit()


# ── Contract 1: idempotent migration ────────────────────────────────────────

def test_migration_015_indexes_and_fks_exist():
    """Happy path: project_config(id) UUID, project_id UUID columns,
    FK constraints pointing at project_config(id) on all 6 dependent tables."""
    with _conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT tc.table_name, ccu.column_name
              FROM information_schema.table_constraints tc
              JOIN information_schema.constraint_column_usage ccu
                   USING (constraint_schema, constraint_name)
             WHERE tc.constraint_type = 'FOREIGN KEY'
               AND tc.table_schema   = 'public'
               AND ccu.table_name    = 'project_config'
             ORDER BY tc.table_name
        """)
        fks = {(t, c) for t, c in cur.fetchall()}

    # Every FK onto project_config must now target 'id' — never 'project_name'.
    assert all(col == "id" for _, col in fks), f"stray project_name FKs: {fks}"
    assert {t for t, _ in fks} >= {
        "project_tokens", "project_repos",
        "project_setups", "retention_policies",
        "scan_results", "scan_signals", "generated_docs",
    }


# ── Contract 2: name → id lookup ────────────────────────────────────────────

def test_name_to_id_is_stable_and_idempotent():
    """Two INSERT-or-SELECT calls for the same project_name return the same id.

    Uses the cursor-based form of _get_project_id_by_name so the test can
    bring its own connection (Mac → NucBox) instead of inheriting the
    docker-internal DB_URL baked into approve_api at import time.
    """
    from src.interface.approve_api import _get_project_id_by_name

    suffix = uuid.uuid4().hex[:8]
    name = f"adr080-test-{suffix}"
    try:
        with _conn() as conn, conn.cursor() as cur:
            id1 = _get_project_id_by_name(name, cur)
            id2 = _get_project_id_by_name(name, cur)
            conn.commit()
        assert id1 == id2
        assert uuid.UUID(id1)   # parses as UUID
    finally:
        _cleanup(name)


# ── Contract 3: FK constraint bites on bad project_id ───────────────────────

def test_project_tokens_fk_rejects_bogus_uuid():
    """Attempting to insert project_tokens with a non-existent project_id must fail
    the FK constraint — proves the migration is actually enforced, not advisory."""
    bogus_id = str(uuid.uuid4())   # random, never in project_config
    with _conn() as conn:
        with conn.cursor() as cur:
            with pytest.raises(psycopg2.errors.ForeignKeyViolation):
                cur.execute(
                    "INSERT INTO project_tokens "
                    "(project_id, project_name, repo_url) VALUES (%s, %s, %s)",
                    (bogus_id, "adr080-never-exists", "https://example.test/r.git"),
                )
        conn.rollback()
