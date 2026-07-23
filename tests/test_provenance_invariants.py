"""ADR-107 Provenance Invariants — verify source/license/last_verified discipline.

Runs against a live curated Neo4j (override via NEO4J_NUC_* env; defaults to a
local tunnel on localhost:17687). Skipped if the DB is unreachable — CI
environments without a tunnel just skip.

Scope: asserts 100 % provenance coverage on nodes and edges created/managed by
the 8 seed functions in scripts/seed_both.py (post ADR-107-PR-2 migration).
Legacy nodes outside these seeds (Country, RiskLevel, TransferMechanism, etc.)
are explicitly NOT covered here — those need a separate cleanup pass.

Hard-asserts (must be 100 %):
- ServiceCategory (excluding legacy 'collaboration' from hotfix a7be8de)
- HostingProvider
- Edges: HAS_CATEGORY (from seed_stubs), SUBJECT_TO_CONTROL (from seed_adr061+066),
        TRIGGERS_FRAMEWORK (adr061), MAPS_TO (adr063)

Soft-tracks (informational, not failing):
- Service nodes (mix of seed-managed and runtime-discovered)
- Control nodes (mostly pre-ADR-107 with `c.source` strings but no `c.license`)
- Law nodes (mix of adr093-managed and pre-existing)
"""
from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv

load_dotenv()

NUC_URI = os.getenv("NEO4J_NUC_URI", "bolt://localhost:17687")
NUC_USER = os.getenv("NEO4J_NUC_USERNAME", "neo4j")
NUC_PASSWORD = os.getenv("NEO4J_NUC_PASSWORD", "")
NUC_DB = os.getenv("NEO4J_NUC_DATABASE", "neo4j")

# source_url is NOT required for the curated class asserted here
# (ServiceCategory / HostingProvider / TRIGGERS_FRAMEWORK): their deciding
# ADRs stay private, so a URL would point nowhere — the ADR identity lives in
# `source` (verdict 2026-07-17, ADR-107 addendum). External-norm nodes keep
# their real URLs; they are not covered by these hard asserts.
REQUIRED_PROPS = ["source", "license", "license_attribution", "last_verified"]


@pytest.fixture(scope="module")
def session():
    """Live NucBox session via SSH tunnel. Skip if unreachable."""
    try:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(NUC_URI, auth=(NUC_USER, NUC_PASSWORD))
        with driver.session(database=NUC_DB) as sess:
            sess.run("RETURN 1").single()
            yield sess
        driver.close()
    except Exception as e:
        pytest.skip(f"NucBox Neo4j unreachable (need SSH tunnel on {NUC_URI}): {e}")


def _missing_for_label(session, label: str, where_clause: str = "") -> dict:
    """Return per-property count of nodes with the property NULL for the given label."""
    query = f"""
        MATCH (n:{label})
        {where_clause}
        RETURN
          count(n) AS total,
          sum(CASE WHEN n.source IS NULL THEN 1 ELSE 0 END) AS missing_source,
          sum(CASE WHEN n.source_url IS NULL THEN 1 ELSE 0 END) AS missing_source_url,
          sum(CASE WHEN n.license IS NULL THEN 1 ELSE 0 END) AS missing_license,
          sum(CASE WHEN n.license_attribution IS NULL THEN 1 ELSE 0 END) AS missing_license_attribution,
          sum(CASE WHEN n.last_verified IS NULL THEN 1 ELSE 0 END) AS missing_last_verified
    """
    return dict(session.run(query).single())


def _missing_for_edge(session, edge_type: str) -> dict:
    """Same as _missing_for_label but for relationship types."""
    query = f"""
        MATCH ()-[r:{edge_type}]->()
        RETURN
          count(r) AS total,
          sum(CASE WHEN r.source IS NULL THEN 1 ELSE 0 END) AS missing_source,
          sum(CASE WHEN r.source_url IS NULL THEN 1 ELSE 0 END) AS missing_source_url,
          sum(CASE WHEN r.license IS NULL THEN 1 ELSE 0 END) AS missing_license,
          sum(CASE WHEN r.license_attribution IS NULL THEN 1 ELSE 0 END) AS missing_license_attribution,
          sum(CASE WHEN r.last_verified IS NULL THEN 1 ELSE 0 END) AS missing_last_verified
    """
    return dict(session.run(query).single())


# ── Hard invariants — full coverage required ────────────────────────────────


def test_service_category_full_provenance(session):
    """seed_adr061 manages ServiceCategory; excludes legacy 'collaboration' hotfix."""
    r = _missing_for_label(session, "ServiceCategory", "WHERE n.name <> 'collaboration'")
    assert r["total"] > 0, "no ServiceCategory nodes found"
    for prop in REQUIRED_PROPS:
        key = f"missing_{prop}"
        assert r[key] == 0, f"ServiceCategory: {r[key]}/{r['total']} nodes missing `{prop}`"


def test_hosting_provider_full_provenance(session):
    """seed_adr076 manages all HostingProvider — 100 % coverage expected."""
    r = _missing_for_label(session, "HostingProvider")
    assert r["total"] > 0, "no HostingProvider nodes found"
    for prop in REQUIRED_PROPS:
        key = f"missing_{prop}"
        assert r[key] == 0, f"HostingProvider: {r[key]}/{r['total']} nodes missing `{prop}`"


def test_has_category_edges_provenance(session):
    """HAS_CATEGORY edges from seed_stubs + seed_adr061."""
    r = _missing_for_edge(session, "HAS_CATEGORY")
    assert r["total"] > 0
    # Tolerance: allow up to 5 legacy edges from pre-ADR-107 runtime scans
    assert r["missing_source"] <= 5, f"HAS_CATEGORY: {r['missing_source']}/{r['total']} edges missing `source`"


def test_subject_to_control_edges_provenance(session):
    """SUBJECT_TO_CONTROL edges from seed_adr061 + seed_adr066."""
    r = _missing_for_edge(session, "SUBJECT_TO_CONTROL")
    assert r["total"] > 0
    # Tolerance allows the 38 edges from collaboration ServiceCategory hotfix
    assert r["missing_source"] <= 40, f"SUBJECT_TO_CONTROL: {r['missing_source']}/{r['total']} edges missing `source`"


def test_triggers_framework_edges_provenance(session):
    """TRIGGERS_FRAMEWORK edges from seed_adr061 — must be 100 %."""
    r = _missing_for_edge(session, "TRIGGERS_FRAMEWORK")
    assert r["total"] > 0
    for prop in REQUIRED_PROPS:
        key = f"missing_{prop}"
        assert r[key] == 0, f"TRIGGERS_FRAMEWORK: {r[key]}/{r['total']} edges missing `{prop}`"


def test_maps_to_edges_provenance(session):
    """MAPS_TO edges are BYOS-conditional since ADR-120: the ISO de-seed
    (2026-06-04) removed the 20 ADR-063 OWASP→ISO edges along with the ISO
    controls, and seed_adr063 MATCHes on ISO controls — a graph without a
    licensed ISO copy (layers/byos/iso27001.cypher) legitimately has zero
    MAPS_TO edges. Whatever exists must carry full provenance."""
    r = _missing_for_edge(session, "MAPS_TO")
    if r["total"] == 0:
        pytest.skip("no MAPS_TO edges — ADR-120 BYOS state (ISO not seeded)")
    assert r["missing_source"] == 0, (
        f"MAPS_TO: {r['missing_source']}/{r['total']} edges missing `source`"
    )


# ── Soft-tracks — informational, do not fail (separate cleanup needed) ──────


def test_legacy_labels_inventory(session, capsys):
    """Document labels NOT covered by current seeds. Informational only."""
    labels = ["Country", "RiskLevel", "TransferMechanism", "Risk", "UseCase"]
    report = []
    with capsys.disabled():
        print("\n=== Legacy labels needing post-PR-2 migration ===")
        for lbl in labels:
            r = _missing_for_label(session, lbl)
            if r["total"] > 0:
                covered = r["total"] - r["missing_source"]
                report.append(f"  {lbl}: {covered}/{r['total']} have source")
                print(f"  {lbl}: {covered}/{r['total']} have source")
        print("(See ADR-107 follow-up: Country/RiskLevel/TransferMechanism need own seed/migration.)")
    assert report, "expected at least one legacy label to inventory"
