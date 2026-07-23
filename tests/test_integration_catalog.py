"""ADR-082 + ADR-083: Integration Catalog + Vault Secret Storage.

Behavioural tests covering the Phase-1 backend contracts:

1. The graph catalog holds the 6 seeded Service nodes with
   category='integration'.
2. Migration 016 landed: project_integrations + supabase_vault extension
   are present.
3. save + get integration key roundtrips through vault.secrets without
   ever exposing plaintext on project_integrations itself.
4. approve_api endpoints reject unknown integrations against the graph
   catalog.

Requires a real Supabase (NucBox) reachable via MCP_SUPABASE_URL or
DATABASE_URL and a real Neo4j. Test rows use UUID-suffixed names so
re-runs don't collide.
"""
from __future__ import annotations

import os
import uuid

import psycopg2
import pytest

from src.graph.graph_client import GraphClient


DB_URL = os.environ.get("MCP_SUPABASE_URL") or os.environ.get("DATABASE_URL")

if not (os.getenv("NEO4J_URI") and os.getenv("NEO4J_USERNAME") and os.getenv("NEO4J_PASSWORD")):
    pytest.skip("live Neo4j env not configured — integration suite", allow_module_level=True)


def _conn():
    if not DB_URL:
        pytest.skip("No DATABASE_URL / MCP_SUPABASE_URL in env")
    return psycopg2.connect(DB_URL)


def _cleanup_project(name: str) -> None:
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM project_config WHERE project_name = %s", (name,)
        )
        row = cur.fetchone()
        if not row:
            return
        project_id = row[0]
        cur.execute(
            "SELECT api_key_secret_id FROM project_integrations "
            "WHERE project_id = %s AND api_key_secret_id IS NOT NULL",
            (project_id,),
        )
        for (secret_id,) in cur.fetchall():
            cur.execute("DELETE FROM vault.secrets WHERE id = %s", (secret_id,))
        cur.execute("DELETE FROM project_config WHERE id = %s", (project_id,))
        conn.commit()


@pytest.fixture(scope="module")
def graph():
    g = GraphClient()
    yield g
    g.close()


# ── Contract 1: Catalog is seeded ───────────────────────────────────────────

REQUIRED_INTEGRATIONS = {
    "eRecht24", "Firecrawl", "Mistral AI EU", "Langfuse", "GitHub", "Telegram",
}


def test_catalog_contains_seeded_integrations(graph):
    rows = graph.run_query(
        "MATCH (svc:Service {category: 'integration'}) RETURN svc.name AS name"
    )
    names = {r["name"] for r in rows}
    missing = REQUIRED_INTEGRATIONS - names
    assert not missing, f"seeder missed: {missing} — run scripts/seed_both.py --module adr082"


def test_catalog_nodes_have_required_properties(graph):
    rows = graph.run_query("""
        MATCH (svc:Service {category: 'integration'})
        RETURN svc.name                 AS name,
               svc.subcategory          AS subcategory,
               svc.required_credentials AS required_credentials,
               svc.pricing_tier         AS pricing_tier,
               svc.documentation_url    AS documentation_url
    """)
    for r in rows:
        assert r["subcategory"], f"{r['name']}: subcategory missing"
        assert r["required_credentials"], f"{r['name']}: required_credentials missing"
        assert r["pricing_tier"], f"{r['name']}: pricing_tier missing"
        assert r["documentation_url"], f"{r['name']}: documentation_url missing"


# ── Contract 2: Migration 016 landed ────────────────────────────────────────

def test_project_integrations_table_exists():
    with _conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
              FROM information_schema.columns
             WHERE table_schema = 'public'
               AND table_name   = 'project_integrations'
        """)
        cols = {c for (c,) in cur.fetchall()}
    assert cols >= {
        "id", "project_id", "project_name", "integration", "enabled",
        "api_key_secret_id", "config", "connected_at",
    }


def test_vault_extension_installed():
    with _conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'supabase_vault'")
        assert cur.fetchone() is not None, (
            "supabase_vault not installed — migration 016 prerequisite failed"
        )


def test_erecht24_plaintext_columns_are_dropped():
    """ADR-083: plaintext *_api_key columns may not exist on project_config."""
    with _conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
              FROM information_schema.columns
             WHERE table_schema = 'public'
               AND table_name   = 'project_config'
               AND column_name IN ('erecht24_api_key', 'erecht24_domain')
        """)
        stragglers = [c for (c,) in cur.fetchall()]
    assert not stragglers, f"ADR-083 regression: {stragglers} on project_config"


# ── Contract 3: Vault roundtrip ─────────────────────────────────────────────

def test_secret_round_trip_via_vault():
    """save → reload via helpers; ciphertext only at rest on project_integrations."""
    from src.interface.approve_api import (
        _save_integration_key,
        _get_integration_key,
        _get_project_id_by_name,
    )
    suffix = uuid.uuid4().hex[:8]
    name = f"adr083-roundtrip-{suffix}"
    try:
        with _conn() as conn, conn.cursor() as cur:
            project_id = _get_project_id_by_name(name, cur)
            plaintext = f"sk-test-{suffix}"
            secret_id = _save_integration_key(cur, project_id, "erecht24", plaintext)
            assert uuid.UUID(secret_id)

            cur.execute(
                """
                INSERT INTO project_integrations
                      (project_id, project_name, integration, api_key_secret_id)
                VALUES (%s, %s, 'erecht24', %s)
                """,
                (project_id, name, secret_id),
            )
            retrieved = _get_integration_key(cur, project_id, "erecht24")
            assert retrieved == plaintext

            # project_integrations itself must NOT carry the plaintext.
            cur.execute(
                "SELECT api_key_secret_id FROM project_integrations "
                "WHERE project_id = %s AND integration = 'erecht24'",
                (project_id,),
            )
            row = cur.fetchone()
            assert str(row[0]) == secret_id
            conn.commit()
    finally:
        _cleanup_project(name)


# ── Contract 4: Endpoint validates against catalog ──────────────────────────

def test_upsert_rejects_unknown_integration():
    """ADR-082: the graph is authoritative for what integrations exist."""
    from fastapi.testclient import TestClient
    from src.interface.approve_api import app, IntegrationUpsertRequest  # noqa: F401

    suffix = uuid.uuid4().hex[:8]
    name = f"adr082-unknown-{suffix}"
    client = TestClient(app)
    try:
        r = client.post(
            f"/projects/{name}/integrations/NotInCatalog",
            json={"api_key": "x"},
        )
        assert r.status_code == 404
    finally:
        _cleanup_project(name)
