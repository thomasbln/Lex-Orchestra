"""Schema-explorer allowlist drift guards (finding 2026-07-19).

The registry counts labels label-agnostically, but /graph/nodes/{type} gates on
the static _ALLOWED_NODE_TYPES injection guard. Drift meant 8 seeded node types
(146 nodes, 30 %) rendered as "0 nodes" despite their registry counts. These
guards kill the class: a new seeded type without an allowlist entry turns the
live test red (in the NucBox battery), and the static pair forces conscious
maintenance of both lists.
"""

import os

import pytest

from src.interface.approve_api import _ALLOWED_NODE_TYPES

# Every label the v1.0 seed creates (mirrors the live graph, verified 2026-07-19).
KNOWN_SEEDED_LABELS = {
    "Service", "Control", "Measure", "Law", "Requirement", "ServiceCategory",
    "Requirement_B", "UseCase", "DocumentType", "SupervisoryAuthority",
    "HostingProvider", "ProcessingActivity", "Country", "DataSubject",
    "LegalBasis", "ProtectionGoal", "RiskLevel", "RetentionPeriod", "Risk",
    "TransferMechanism",
}


def test_known_seeded_labels_are_allowlisted():
    missing = KNOWN_SEEDED_LABELS - _ALLOWED_NODE_TYPES
    assert not missing, (
        f"seeded node types missing from _ALLOWED_NODE_TYPES (schema explorer "
        f"would show '0 nodes' for them): {sorted(missing)}"
    )


def test_no_phantom_allowlist_entries():
    phantom = _ALLOWED_NODE_TYPES - KNOWN_SEEDED_LABELS
    assert not phantom, (
        f"allowlist carries labels no seed creates (Framework/AiRisk class — "
        f"dead entries mask drift): {sorted(phantom)}"
    )


@pytest.mark.skipif(
    not (os.getenv("NEO4J_URI") and os.getenv("NEO4J_USERNAME") and os.getenv("NEO4J_PASSWORD")),
    reason="live Neo4j env not configured — integration guard",
)
def test_live_labels_subset_of_allowlist():
    """The drift-killer: every label in the live graph must be allowlisted."""
    from src.graph.graph_client import GraphClient

    gc = GraphClient()
    try:
        with gc._driver.session() as s:
            labels = {r["label"] for r in s.run("CALL db.labels() YIELD label RETURN label")}
    finally:
        gc.close()
    stray = labels - _ALLOWED_NODE_TYPES
    assert not stray, (
        f"live graph carries labels the schema explorer cannot list: {sorted(stray)} "
        f"— extend _ALLOWED_NODE_TYPES (and NODE_TYPE_META in schema/page.tsx)"
    )
