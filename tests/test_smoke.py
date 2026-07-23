"""
Smoke Tests — Infrastructure Connectivity
==========================================
Quick checks that all critical connections are working.
Runs in under 5 seconds. No full implementation required.

Run:
    pytest tests/test_smoke.py -v

Requirements:
    - NucBox reachable (sovereign profile, primary target)
    - Neo4j reachable (local container or Aura, NEO4J_URI in .env)
    - LangGraph Server running on the host (lex-agent container, port 8000)
    - approve_api running on the host (lex-agent, port 8001)
"""

import os
import pytest
import requests
from dotenv import load_dotenv

load_dotenv()

# Host under test — deliberately no default: without LEX_SMOKE_HOST the
# host-dependent smoke tests skip (works on any install, leaks no LAN IP).
NUC_HOST        = os.getenv("LEX_SMOKE_HOST", "")
LANGGRAPH_URL   = f"http://{NUC_HOST}:8000"
APPROVE_API_URL = f"http://{NUC_HOST}:8001"

requires_host = pytest.mark.skipif(
    not NUC_HOST, reason="LEX_SMOKE_HOST not set — host smoke tests skipped"
)


def test_env_supabase_url():
    """MCP_SUPABASE_URL or DATABASE_URL must be set in .env."""
    url = os.getenv("MCP_SUPABASE_URL") or os.getenv("DATABASE_URL")
    assert url, "Neither MCP_SUPABASE_URL nor DATABASE_URL found in .env"


def test_env_neo4j():
    """Neo4j credentials must be present in .env."""
    assert os.getenv("NEO4J_URI"),      "NEO4J_URI missing from .env"
    assert os.getenv("NEO4J_USERNAME"), "NEO4J_USERNAME missing from .env"
    assert os.getenv("NEO4J_PASSWORD"), "NEO4J_PASSWORD missing from .env"


def test_env_ollama():
    """Sovereign profile requires Ollama endpoint + model."""
    assert os.getenv("OLLAMA_URL"),   "OLLAMA_URL missing from .env (sovereign profile)"
    assert os.getenv("OLLAMA_MODEL"), "OLLAMA_MODEL missing from .env (sovereign profile)"


def test_supabase_connection():
    """Supabase DB on Pi is reachable and pgvector extension is active."""
    import psycopg2
    url = os.getenv("MCP_SUPABASE_URL") or os.getenv("DATABASE_URL")
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
    row = cur.fetchone()
    conn.close()
    assert row, "pgvector extension not active — see docs/setup/docker.md"


def test_asset_translator_setup():
    """AssetTranslator.setup() creates tables without error (idempotent)."""
    from src.graph.asset_translator import AssetTranslator
    t = AssetTranslator()
    t.setup()


def test_neo4j_connection():
    """Neo4j Aura is reachable and graph contains seeded nodes."""
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
    )
    with driver.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as session:
        total = session.run("MATCH (n) RETURN count(n) AS total").single()["total"]
    driver.close()
    assert total > 0, "Neo4j graph is empty — run: make seed-all"


# ── Pi Container Tests ────────────────────────────────────────────────────────

@requires_host
def test_langgraph_server_health():
    """LangGraph Server (lex-agent) is reachable and healthy."""
    try:
        resp = requests.get(f"{LANGGRAPH_URL}/ok", timeout=5)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        pytest.skip("LangGraph Server not reachable — start lex-agent container first")
    assert resp.status_code == 200, f"LangGraph Server unhealthy: {resp.status_code}"
    assert resp.json().get("ok") is True


@requires_host
def test_langgraph_graph_registered():
    """lex_workflow graph is registered in LangGraph Server."""
    try:
        resp = requests.post(f"{LANGGRAPH_URL}/assistants/search", json={}, timeout=5)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        pytest.skip("LangGraph Server not reachable — start lex-agent container first")
    assert resp.status_code == 200
    graph_ids = [a.get("graph_id") for a in resp.json()]
    assert "lex_workflow" in graph_ids, \
        f"lex_workflow not registered. Found: {graph_ids}"


def test_check_sources_script_exists():
    """check_sources.py must exist and be importable."""
    from scripts.check_sources import SOURCE_MAP, SOURCES_DIR
    assert len(SOURCE_MAP) >= 10
    assert SOURCES_DIR.exists()


@requires_host
def test_approve_api_cors():
    """CORS preflight on /config/project-tokens must return 200 with
    Access-Control-Allow-Origin header matching the dashboard origin."""
    origin = f"http://{NUC_HOST}:3000"
    try:
        resp = requests.options(
            f"{APPROVE_API_URL}/config/project-tokens",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
            timeout=5,
        )
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        pytest.skip("approve_api not reachable — start lex-agent container first")
    assert resp.status_code == 200, (
        f"CORS preflight failed: {resp.status_code} — CORSMiddleware not "
        f"accepting origin {origin}"
    )
    allow_origin = resp.headers.get("access-control-allow-origin")
    assert allow_origin == origin, (
        f"Access-Control-Allow-Origin mismatch: got {allow_origin!r}, "
        f"expected {origin!r}"
    )
