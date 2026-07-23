"""
Tests: AssetTranslator — ADR-001 PII Separation
================================================
Verifies:
  1. Tables are created on setup (idempotent)
  2. Assets are stored and assigned a UUID
  3. anonymize() never returns real asset names
  4. resolve() returns full local details by UUID
  5. Storing the same asset twice does not create duplicates
"""

import os
import uuid

import pytest
from src.graph.asset_translator import AssetTranslator, _canonical_name

if not (os.getenv("DATABASE_URL") or os.getenv("MCP_SUPABASE_URL")):
    pytest.skip(
        "live Postgres env not configured (DATABASE_URL/MCP_SUPABASE_URL) — integration suite",
        allow_module_level=True,
    )


PROJECT_ID = str(uuid.uuid4())

SAMPLE_SERVICES = [
    {"name": "Stripe", "category": "payment", "type": "service",
     "source": "package.json", "confidence": 1.0},
    {"name": "OpenAI", "category": "ai_llm", "type": "service",
     "source": "docker-compose.yml", "confidence": 0.95},
    {"name": "my-internal-db", "category": "database", "type": "service",
     "source": "docker-compose.yml", "confidence": 0.8},
]


@pytest.fixture(scope="module")
def translator():
    t = AssetTranslator()
    t.setup()
    return t


def test_setup_creates_tables(translator):
    """setup() completes without error and is safe to call multiple times."""
    translator.setup()  # idempotent — no error on repeated calls


def test_store_returns_records(translator):
    """store_assets() returns one AssetRecord per service with UUID and name set."""
    records = translator.store_assets(PROJECT_ID, SAMPLE_SERVICES)
    assert len(records) == 3
    for r in records:
        assert r.uuid  # UUID must be assigned
        assert r.name  # real name stored locally


def test_anonymize_no_real_names(translator):
    """ADR-001 core assertion: anonymize() must never expose real asset names."""
    records = translator.store_assets(PROJECT_ID, SAMPLE_SERVICES)
    anon = translator.anonymize(records)

    real_names = {s["name"] for s in SAMPLE_SERVICES}

    for item in anon:
        # No real name may appear in the anonymized output
        assert "name" not in item or item.get("name") not in real_names, \
            f"Real name found in anonymized output: {item}"
        # Only allowed fields
        allowed = {"uuid", "type", "category", "encrypted", "public", "canonical_name"}
        assert set(item.keys()) <= allowed, \
            f"Unexpected fields in anonymized output: {set(item.keys()) - allowed}"


def test_resolve_returns_full_details(translator):
    """resolve() returns complete local asset details by UUID."""
    records = translator.store_assets(PROJECT_ID, SAMPLE_SERVICES)
    record = records[0]

    resolved = translator.resolve(record.uuid)
    assert resolved is not None
    assert resolved["name"] == record.name
    assert str(resolved["id"]) == record.uuid


def test_idempotent_store(translator):
    """Storing the same assets twice returns the same UUIDs — no duplicates."""
    records1 = translator.store_assets(PROJECT_ID, SAMPLE_SERVICES)
    records2 = translator.store_assets(PROJECT_ID, SAMPLE_SERVICES)

    uuids1 = {r.uuid for r in records1}
    uuids2 = {r.uuid for r in records2}
    assert uuids1 == uuids2, "Duplicate UUIDs created on second store — idempotency violated"


def test_canonical_name_known_service():
    """Known services are mapped to their canonical Neo4j seed name."""
    assert _canonical_name("Stripe") == "Stripe"
    assert _canonical_name("stripe-js") == "Stripe"
    assert _canonical_name("OpenAI") == "Openai"


def test_canonical_name_unknown_service():
    """Unknown services return None — no graph match attempted."""
    assert _canonical_name("my-internal-db") is None
    assert _canonical_name("custom-auth-service") is None


def test_get_project_assets(translator):
    """get_project_assets() returns all assets for a given project."""
    translator.store_assets(PROJECT_ID, SAMPLE_SERVICES)
    assets = translator.get_project_assets(PROJECT_ID)
    assert len(assets) >= len(SAMPLE_SERVICES)
    for asset in assets:
        assert asset["project_id"] == PROJECT_ID
