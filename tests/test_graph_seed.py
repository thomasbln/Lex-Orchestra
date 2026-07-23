"""
Tests: Graph Seed Validation
=============================
Validates the Neo4j knowledge graph after a full seed run.
Covers node counts, domain coverage, spot checks, relationship integrity,
confidence properties, and total graph size.

All tests hit a real Neo4j — no mocking. Skips when the env is not configured.
Run seed first if these fail: make seed-all
"""

import os

import pytest
from src.graph.graph_client import GraphClient

if not (os.getenv("NEO4J_URI") and os.getenv("NEO4J_USERNAME") and os.getenv("NEO4J_PASSWORD")):
    pytest.skip("live Neo4j env not configured — integration suite", allow_module_level=True)


@pytest.fixture(scope="module")
def graph():
    g = GraphClient()
    yield g
    g.close()


# ── Group 1 — Node counts per framework ───────────────────────────────────────

EXPECTED_CONTROL_COUNTS = [
    ("ISO_27001",       106),
    ("BSI_C5",          121),
    ("AIC4",             41),
    ("BSI_Grundschutz",  16),
    ("NIST_CSF_2",       12),
    ("OWASP_Top10",      10),
    ("OWASP_LLM_Top10",  10),
    ("OWASP_API_Top10",  10),
]


@pytest.mark.parametrize("framework,expected", EXPECTED_CONTROL_COUNTS)
def test_control_count_per_framework(graph, framework, expected):
    """Each framework has exactly the expected number of Control nodes."""
    with graph._driver.session() as session:
        result = session.run(
            "MATCH (c:Control {framework: $fw}) RETURN count(c) AS count",
            fw=framework,
        )
        count = result.single()["count"]
    assert count == expected, (
        f"{framework} has {count} Control nodes — expected {expected}. "
        f"Re-run: make seed-all"
    )


# ── Group 2 — C5 domain coverage ──────────────────────────────────────────────

C5_DOMAINS = [
    "OIS", "SP", "HR", "AM", "PS", "OPS", "IDM",
    "CRY", "COS", "PI", "DEV", "SSO", "SIM", "BCM",
    "COM", "INQ", "PSS",
]


@pytest.mark.parametrize("domain", C5_DOMAINS)
def test_c5_domain_has_controls(graph, domain):
    """Each of the 17 BSI C5 domains has at least one Control node."""
    with graph._driver.session() as session:
        result = session.run(
            "MATCH (c:Control {framework: 'BSI_C5'}) "
            "WHERE c.id STARTS WITH $prefix "
            "RETURN count(c) AS count",
            prefix=f"C5-{domain}-",
        )
        count = result.single()["count"]
    assert count >= 1, (
        f"C5 domain '{domain}' has no Control nodes. "
        f"Re-run: make seed-all"
    )


# ── Group 3 — AIC4 criterion area coverage ────────────────────────────────────

AIC4_AREAS = [
    "Preliminary Criteria",
    "Security and Robustness",
    "Performance and Functionality",
    "Reliability",
    "Data Quality",
    "Data Management",
    "Explainability",
    "Bias",
]


@pytest.mark.parametrize("area", AIC4_AREAS)
def test_aic4_area_has_controls(graph, area):
    """Each of the 8 AIC4 criterion areas has at least one Control node."""
    with graph._driver.session() as session:
        result = session.run(
            "MATCH (c:Control {framework: 'AIC4', area: $area}) RETURN count(c) AS count",
            area=area,
        )
        count = result.single()["count"]
    assert count >= 1, (
        f"AIC4 area '{area}' has no Control nodes. "
        f"Re-run: make seed-all"
    )


# ── Group 4 — Specific control spot checks ────────────────────────────────────

def test_c5_ois01_exists_with_correct_properties(graph):
    """C5-OIS-01 exists with correct title, source, and confidence."""
    with graph._driver.session() as session:
        result = session.run(
            "MATCH (c:Control {framework: 'BSI_C5', id: 'C5-OIS-01'}) "
            "RETURN c.title AS title, c.confidence AS confidence, c.source AS source"
        )
        row = result.single()
    assert row is not None, "C5-OIS-01 not found in graph"
    assert row["title"] == "Information Security Management System (ISMS)", \
        f"C5-OIS-01 title mismatch: {row['title']}"
    assert row["confidence"] == 1.0, \
        f"C5-OIS-01 confidence is {row['confidence']} — expected 1.0"
    assert row["source"] == "BSI C5:2020", \
        f"C5-OIS-01 source is '{row['source']}' — expected 'BSI C5:2020'"


def test_c5_ops10_exists_with_logging_title(graph):
    """C5-OPS-10 exists and its title relates to logging."""
    with graph._driver.session() as session:
        result = session.run(
            "MATCH (c:Control {framework: 'BSI_C5', id: 'C5-OPS-10'}) "
            "RETURN c.title AS title, c.confidence AS confidence"
        )
        row = result.single()
    assert row is not None, "C5-OPS-10 not found in graph"
    assert "Logging" in row["title"] or "logging" in row["title"], \
        f"C5-OPS-10 title does not mention logging: {row['title']}"
    assert row["confidence"] == 1.0


def test_aic4_pc01_exists_with_correct_properties(graph):
    """AIC4-PC-01 exists with correct title, area, and confidence."""
    with graph._driver.session() as session:
        result = session.run(
            "MATCH (c:Control {framework: 'AIC4', id: 'AIC4-PC-01'}) "
            "RETURN c.title AS title, c.area AS area, c.confidence AS confidence"
        )
        row = result.single()
    assert row is not None, "AIC4-PC-01 not found in graph"
    assert "Cloud Computing Compliance" in row["title"], \
        f"AIC4-PC-01 title unexpected: {row['title']}"
    assert row["area"] == "Preliminary Criteria", \
        f"AIC4-PC-01 area is '{row['area']}' — expected 'Preliminary Criteria'"
    assert row["confidence"] == 1.0


def test_aic4_sr01_exists_in_security_area(graph):
    """AIC4-SR-01 exists in the Security and Robustness area."""
    with graph._driver.session() as session:
        result = session.run(
            "MATCH (c:Control {framework: 'AIC4', id: 'AIC4-SR-01'}) RETURN c.area AS area"
        )
        row = result.single()
    assert row is not None, "AIC4-SR-01 not found in graph"
    assert row["area"] == "Security and Robustness", \
        f"AIC4-SR-01 area is '{row['area']}' — expected 'Security and Robustness'"


def test_aic4_bi04_exists_in_bias_area(graph):
    """AIC4-BI-04 exists in the Bias area."""
    with graph._driver.session() as session:
        result = session.run(
            "MATCH (c:Control {framework: 'AIC4', id: 'AIC4-BI-04'}) RETURN c.area AS area"
        )
        row = result.single()
    assert row is not None, "AIC4-BI-04 not found in graph"
    assert row["area"] == "Bias", \
        f"AIC4-BI-04 area is '{row['area']}' — expected 'Bias'"


# ── Group 5 — Relationship counts ─────────────────────────────────────────────

def test_maps_to_c5_iso27001_count(graph):
    """C5 → ISO 27001:2022 has exactly 190 MAPS_TO relationships.

    Both frameworks are license-gated (BYOS, ADR-118/ADR-120) — with 0 C5
    controls in the graph this is a valid de-seeded state and the test skips.
    """
    with graph._driver.session() as session:
        c5 = session.run(
            "MATCH (c:Control {framework: 'BSI_C5'}) RETURN count(c) AS n"
        ).single()["n"]
    if c5 == 0:
        pytest.skip("BSI C5 not seeded — valid BYOS state (ADR-118)")
    with graph._driver.session() as session:
        result = session.run(
            "MATCH (c:Control {framework: 'BSI_C5'})-[r:MAPS_TO]->(i:Control {framework: 'ISO_27001'}) "
            "RETURN count(r) AS count"
        )
        count = result.single()["count"]
    assert count == 190, (
        f"C5 → ISO 27001 MAPS_TO count is {count} — expected 190. "
        f"Source: C5_2020_Reference_Tables_ISO27001.xlsx"
    )


def test_maps_to_c5_grundschutz_count(graph):
    """C5 → BSI Grundschutz has exactly 62 MAPS_TO relationships.

    C5 is license-gated (BYOS, ADR-118) — with 0 C5 controls in the graph
    this is a valid de-seeded state and the test skips.
    """
    with graph._driver.session() as session:
        c5 = session.run(
            "MATCH (c:Control {framework: 'BSI_C5'}) RETURN count(c) AS n"
        ).single()["n"]
    if c5 == 0:
        pytest.skip("BSI C5 not seeded — valid BYOS state (ADR-118)")
    with graph._driver.session() as session:
        result = session.run(
            "MATCH (c:Control {framework: 'BSI_C5'})-[r:MAPS_TO]->(g:Control {framework: 'BSI_Grundschutz'}) "
            "RETURN count(r) AS count"
        )
        count = result.single()["count"]
    assert count == 62, (
        f"C5 → BSI Grundschutz MAPS_TO count is {count} — expected 62. "
        f"Source: C5_2020_Reference_Tables.xlsx"
    )


def test_aic4_requires_c5_count(graph):
    """AIC4 PC-01 REQUIRES all 121 C5 criteria."""
    with graph._driver.session() as session:
        result = session.run(
            "MATCH (a:Control {framework: 'AIC4', id: 'AIC4-PC-01'})-[r:REQUIRES]->(c:Control {framework: 'BSI_C5'}) "
            "RETURN count(r) AS count"
        )
        count = result.single()["count"]
    assert count == 121, (
        f"AIC4-PC-01 REQUIRES {count} C5 nodes — expected 121. "
        f"Re-run: make seed-all"
    )


def test_aic4_references_c5_count(graph):
    """AIC4 controls have exactly 26 inline REFERENCES to specific C5 criteria."""
    with graph._driver.session() as session:
        result = session.run(
            "MATCH (a:Control {framework: 'AIC4'})-[r:REFERENCES]->(c:Control {framework: 'BSI_C5'}) "
            "RETURN count(r) AS count"
        )
        count = result.single()["count"]
    assert count == 26, (
        f"AIC4 REFERENCES to C5 count is {count} — expected 26. "
        f"Source: AIC4 PDF inline citations (C5-XXX-YY pattern)"
    )


# ── Group 6 — MAPS_TO security level property ─────────────────────────────────

def test_maps_to_sn_values_valid(graph):
    """All MAPS_TO sn properties contain only valid BSI delta indicators."""
    valid_sn = {"0", "+", "-", "n/a"}
    with graph._driver.session() as session:
        result = session.run(
            "MATCH ()-[r:MAPS_TO]->() WHERE r.sn IS NOT NULL RETURN DISTINCT r.sn AS sn"
        )
        actual_sn = {row["sn"] for row in result}
    invalid = actual_sn - valid_sn
    assert not invalid, (
        f"Invalid sn values on MAPS_TO relationships: {invalid}. "
        f"Valid values: {valid_sn}"
    )


# ── Group 7 — Confidence integrity ────────────────────────────────────────────

def test_c5_confidence_all_1_0(graph):
    """All 121 BSI C5 Control nodes have confidence: 1.0."""
    with graph._driver.session() as session:
        result = session.run(
            "MATCH (c:Control {framework: 'BSI_C5'}) "
            "WHERE c.confidence <> 1.0 OR c.confidence IS NULL "
            "RETURN count(c) AS missing"
        )
        missing = result.single()["missing"]
    assert missing == 0, (
        f"{missing} BSI C5 nodes have confidence != 1.0. "
        f"All C5 criteria were read from official BSI XLSX source."
    )


def test_aic4_confidence_all_1_0(graph):
    """All 41 AIC4 Control nodes have confidence: 1.0."""
    with graph._driver.session() as session:
        result = session.run(
            "MATCH (c:Control {framework: 'AIC4'}) "
            "WHERE c.confidence <> 1.0 OR c.confidence IS NULL "
            "RETURN count(c) AS missing"
        )
        missing = result.single()["missing"]
    assert missing == 0, (
        f"{missing} AIC4 nodes have confidence != 1.0. "
        f"All AIC4 controls were read from official BSI PDF source."
    )


# ── Group 8 — Total graph size ────────────────────────────────────────────────

def test_total_node_count(graph):
    """Graph has at least 400 nodes after a full seed.

    Threshold, not an exact count: seed content evolves with every curation
    round (a fresh v1.0 seed lands at ~474 nodes), and exact-count asserts
    broke on every intentional change. The threshold still catches the real
    failure mode — an empty or partially seeded graph.
    """
    with graph._driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) AS total")
        total = result.single()["total"]
    assert total >= 400, (
        f"Graph has only {total} nodes — a full seed lands at ~474. "
        f"Run: make seed-all"
    )


def test_total_relationship_count_at_least_900(graph):
    """Graph has at least 900 relationships after full seed."""
    with graph._driver.session() as session:
        result = session.run("MATCH ()-[r]->() RETURN count(r) AS total")
        total = result.single()["total"]
    assert total >= 900, (
        f"Graph has only {total} relationships — expected >= 900. "
        f"Re-run: make seed-all"
    )
