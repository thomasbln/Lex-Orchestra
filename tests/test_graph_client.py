"""
Tests: GraphClient — Neo4j Queries
====================================
Verifies:
  1. Connection to Neo4j succeeds
  2. get_compliance_requirements() returns expected documents and controls
  3. Known services resolve to correct requirements
  4. get_schema_summary() reflects seeded node types
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


def test_connection(graph):
    """Neo4j is reachable and graph contains nodes."""
    summary = graph.get_schema_summary()
    assert "nodes" in summary
    total = sum(n["count"] for n in summary["nodes"])
    assert total > 0, "Graph is empty — run: make seed-all"


def test_compliance_requirements_stripe(graph):
    """Stripe requires AVV and SCC per DSGVO Art. 28 + Art. 46 (DPA merged to AVV in ADR-093 PR1)."""
    result = graph.get_compliance_requirements(["Stripe"])
    assert "AVV" in result["doc_types"]
    assert "SCC" in result["doc_types"]


def test_compliance_requirements_openai(graph):
    """OpenAI triggers AI_Act_Manifest and GPAI risk level. overall_risk excludes gpai
    (provider-side obligation, not deployer's — ADR-100 / GQ-003)."""
    result = graph.get_compliance_requirements(["OpenAI"])
    assert "AI_Act_Manifest" in result["doc_types"]
    risk_levels = [r["level"] for r in result["risk_levels"]]
    assert "GPAI" in risk_levels
    assert result["overall_risk"] != "gpai"


def test_compliance_requirements_multiple(graph):
    """Multiple services in one call returns combined requirements."""
    result = graph.get_compliance_requirements(["Stripe", "OpenAI", "Sentry"])
    assert len(result["services"]) >= 2
    assert len(result["doc_types"]) >= 2


def test_compliance_empty_input(graph):
    """Empty service list returns empty result without error."""
    result = graph.get_compliance_requirements([])
    assert result["doc_types"] == []
    assert result["controls"] == []


def test_controls_for_framework(graph):
    """ISO 27001 controls are present in the graph."""
    controls = graph.get_controls_for_framework("ISO_27001")
    assert len(controls) > 0
    assert all("id" in c and "title" in c for c in controls)


def test_schema_summary(graph):
    """Graph contains all expected node types from the seed."""
    summary = graph.get_schema_summary()
    labels = {n["label"] for n in summary["nodes"]}
    for expected in ["Service", "Law", "DocumentType", "Country", "RiskLevel"]:
        assert expected in labels, f"Node type '{expected}' missing from graph"


def test_get_usecases_for_risk_level_limited(graph):
    """UseCase query returns Limited risk nodes."""
    usecases = graph.get_usecases_for_risk_level("Limited")
    assert len(usecases) >= 3
    types = [u["type"] for u in usecases]
    assert "customer_service_chatbot" in types


def test_get_usecases_for_risk_level_high(graph):
    """UseCase query returns High risk nodes with annex_iii_nr."""
    usecases = graph.get_usecases_for_risk_level("High")
    assert len(usecases) >= 3
    hr = next(u for u in usecases if u["type"] == "hr_recruitment_screening")
    assert hr["annex_iii_nr"] == "4"


def test_limited_usecase_references_art50(graph):
    """Limited risk UseCases must reference Art. 50, not Art. 52."""
    usecases = graph.get_usecases_for_risk_level("Limited")
    for u in usecases:
        assert u["article"] == "50", \
            f"UseCase {u['type']} references Art. {u['article']} — expected Art. 50"


def test_dora_law_nodes_exist(graph):
    """DORA Law nodes exist with correct applies_from and confidence."""
    with graph._driver.session() as session:
        result = session.run(
            "MATCH (l:Law {name: 'DORA'}) RETURN l.article AS article, "
            "l.applies_from AS applies_from, l.confidence AS confidence "
            "ORDER BY l.article"
        )
        rows = result.data()

    assert len(rows) == 6, f"Expected 6 DORA Law nodes, got {len(rows)}"

    articles = {r["article"] for r in rows}
    assert articles == {"5", "6", "17", "19", "24", "28"}, \
        f"Unexpected DORA articles: {articles}"

    for row in rows:
        assert str(row["applies_from"]) == "2025-01-17", \
            f"DORA Art. {row['article']} has wrong applies_from: {row['applies_from']}"
        assert row["confidence"] == 1.0, \
            f"DORA Art. {row['article']} has confidence {row['confidence']} — expected 1.0"


def test_get_upcoming_deadlines_returns_cra(graph):
    """CRA Art. 14 applies 2026-09-11 — must appear in 365-day window."""
    deadlines = graph.get_upcoming_deadlines(days=365)
    names = [(d["name"], d["article"]) for d in deadlines]
    assert ("CRA", "14") in names, f"CRA Art. 14 not found in: {names}"
    cra = next(d for d in deadlines if d["name"] == "CRA" and d["article"] == "14")
    assert cra["days_until"] > 0
    assert cra["applies_from"] == "2026-09-11"


def test_get_upcoming_deadlines_ordering(graph):
    """Results must be ordered by applies_from ascending."""
    deadlines = graph.get_upcoming_deadlines(days=730)
    dates = [d["applies_from"] for d in deadlines]
    assert dates == sorted(dates)


def test_get_compliance_requirements_for_jurisdiction_stub(graph):
    """Jurisdiction filter must return a valid dict with laws and jurisdiction keys."""
    result = graph.get_compliance_requirements_for_jurisdiction(["Stripe"], jurisdiction="DE")
    assert "laws" in result
    assert result["jurisdiction"] == "DE"
    for law in result["laws"]:
        jurisdictions = law.get("jurisdictions") or []
        assert any(j in {"DE", "EU", "global"} for j in jurisdictions), \
            f"Non-DE law slipped through: {law}"


def test_title_en_exists_for_eu_laws(graph):
    """EU AI Act and GDPR Law nodes must have title_en after translation."""
    with graph._driver.session() as session:
        result = session.run("""
            MATCH (l:Law)
            WHERE l.name IN ["DSGVO", "EU AI Act"]
              AND l.title_en IS NULL
            RETURN count(l) AS missing
        """).single()
    assert result["missing"] == 0, "Some EU law nodes missing title_en"


def test_document_type_nodes_have_required_sections(graph):
    """All core DocumentType nodes must have required_sections defined in graph."""
    with graph._driver.session() as session:
        result = session.run("""
            MATCH (d:DocumentType)
            WHERE d.required_sections IS NULL
              AND d.type IN ["AVV", "TOM", "VVT", "AI_Act_Manifest",
                             "DSFA", "KI_Policy", "KI_System_Dokumentation"]
            RETURN count(d) AS missing
        """).single()
    assert result["missing"] == 0, \
        "Some core DocumentType nodes are missing required_sections — re-run seed.py"
