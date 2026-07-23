"""Data-quality regression tests for the Lex-Orchestra graph (PR 7 invariants)."""

import inspect
import os

import pytest
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(dotenv_path=".env")

if not (os.getenv("NEO4J_URI") and os.getenv("NEO4J_USERNAME") and os.getenv("NEO4J_PASSWORD")):
    pytest.skip(
        "live Neo4j env not configured (NEO4J_URI/NEO4J_USERNAME/NEO4J_PASSWORD) — integration suite",
        allow_module_level=True,
    )


@pytest.fixture(scope="module")
def session():
    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]),
    )
    with driver.session(database=os.environ.get("NEO4J_DATABASE", "neo4j")) as s:
        yield s
    driver.close()


def test_service_nodes_have_no_legal_basis_property(session):
    """PR 7 Fix 4: legal_basis lives on SUBJECT_TO_CONTROL rel, not Service node."""
    count = session.run(
        "MATCH (s:Service) WHERE s.legal_basis IS NOT NULL RETURN count(s) AS n"
    ).single()["n"]
    assert count == 0, (
        f"{count} Service nodes have legacy s.legal_basis property. "
        "Authoritative source is SUBJECT_TO_CONTROL[legal_basis] via HAS_CATEGORY."
    )


def test_no_iso3_country_codes(session):
    """PR 7 Fix 5: Service.country uses full English names, not ISO-3."""
    iso3_codes = ["DEU", "FRA", "NLD", "ESP", "ITA", "GBR", "BVI"]
    count = session.run(
        "MATCH (s:Service) WHERE s.country IN $codes RETURN count(s) AS n",
        codes=iso3_codes,
    ).single()["n"]
    assert count == 0, f"{count} Service nodes still use ISO-3 country codes"


def test_no_duplicate_compliance_service_pairs(session):
    """PR 7 Fix 2/3: known compliance-duplicates merged."""
    known_duplicates = [("Chroma", "ChromaDB"), ("MongoDB", "MongoDB Atlas")]
    for legacy, canonical in known_duplicates:
        count = session.run(
            "MATCH (s:Service {name: $name}) RETURN count(s) AS n",
            name=legacy,
        ).single()["n"]
        assert count == 0, f"Legacy duplicate {legacy!r} still exists; {canonical!r} is canonical"


def test_validator_query_uses_elementId(session):
    """PR 7 Fix 1: validate_graph no longer uses deprecated id()."""
    from scripts.seed_both import validate_graph
    source = inspect.getsource(validate_graph)
    assert "elementId(" in source, "validate_graph should use elementId() not id()"
    assert "id(r)" not in source, "Deprecated id(r) call still present"


def test_acts_as_role_enum_and_source(session):
    """ADR-115 A1: every ACTS_AS edge has a valid role + non-empty role_source."""
    valid_roles = ["controller", "processor", "joint_controller", "special_case"]
    bad = session.run(
        "MATCH ()-[a:ACTS_AS]->() "
        "WHERE NOT a.role IN $roles OR a.role_source IS NULL OR a.role_source = '' "
        "RETURN count(a) AS n",
        roles=valid_roles,
    ).single()["n"]
    assert bad == 0, (
        f"{bad} ACTS_AS edges violate the invariant "
        f"(role in {valid_roles} + non-empty role_source)"
    )


def test_psp_launch_roles_present(session):
    """ADR-115 A1: the 6 launch PSPs carry the EDPB-verified role on
    ACTS_AS -> payment_processing (controller for pure PSPs, special_case for
    PayPal/Klarna), per the ADR-115 launch-role decision."""
    expected = {
        "Stripe": "controller",
        "Mollie": "controller",
        "Billwerk": "controller",
        "Digistore24": "controller",
        "PayPal": "special_case",
        "Klarna": "special_case",
    }
    rows = session.run(
        "MATCH (s:Service)-[a:ACTS_AS]->(pa:ProcessingActivity {id:'payment_processing'}) "
        "WHERE s.name IN $names "
        "RETURN s.name AS name, a.role AS role",
        names=list(expected.keys()),
    ).data()
    actual = {r["name"]: r["role"] for r in rows}
    for name, role in expected.items():
        assert actual.get(name) == role, (
            f"{name}: expected ACTS_AS role {role!r}, got {actual.get(name)!r}"
        )
