"""
ADR-100 Regression Test — Rand Industries end-to-end

Verifies that the ADR-100 graph changes (data_subjects normalisation,
legal_basis backfill, CLASSIFIED_BY traversal) propagate correctly through
the compliance pipeline for the Rand Industries example composition.

Scope: graph query → content model (builder layer).
Template rendering is out of scope (requires full DocumentOrchestrator
with DB access and gap registry — covered by the golden-file builder tests).

Requires: a live Neo4j (NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD in .env) —
skips with a reason otherwise.
"""

from __future__ import annotations

import os

import pytest

from src.documents.builders.avv_builder import AVVBuilder
from src.documents.builders.vvt_builder import VVTBuilder
from src.documents.content_models import BuildContext, GapMarker
from src.graph.graph_client import GraphClient
from tests.golden._helpers import _load_fixture

if not (os.getenv("NEO4J_URI") and os.getenv("NEO4J_USERNAME") and os.getenv("NEO4J_PASSWORD")):
    pytest.skip("live Neo4j env not configured — integration suite", allow_module_level=True)

# ---------------------------------------------------------------------------
# Services and use-cases present in the Rand Industries example app
# (confirmed from tests/fixtures/rand_industries_graph.json scanner output)
# ---------------------------------------------------------------------------
RAND_SERVICES = [
    "Braintree", "Elasticsearch", "MongoDB Atlas", "OpenAI", "Postmark",
    "Redis", "Resend", "Segment", "Sentry", "Stripe", "Supabase",
]
RAND_USECASES = ["hr_recruitment_screening"]


@pytest.fixture(scope="module")
def graph_result() -> dict:
    gc = GraphClient()
    result = gc.get_compliance_requirements(RAND_SERVICES, usecase_types=RAND_USECASES)
    gc.close()
    return result


@pytest.fixture(scope="module")
def avv_model(graph_result):
    config = _load_fixture("rand_industries_config.json")
    reasoning = _load_fixture("rand_industries_reasoning.json")
    ctx = BuildContext(
        run_id="adr100-regression",
        generation_date="2026-04-22",
        project_name="rand-industries",
    )
    return AVVBuilder().build(graph_result, reasoning, config, [], ctx)


@pytest.fixture(scope="module")
def vvt_model(graph_result):
    config = _load_fixture("rand_industries_config.json")
    reasoning = _load_fixture("rand_industries_reasoning.json")
    ctx = BuildContext(
        run_id="adr100-regression",
        generation_date="2026-04-22",
        project_name="rand-industries",
    )
    return VVTBuilder().build(graph_result, reasoning, config, [], ctx)


# ---------------------------------------------------------------------------
# §4.3 — overall_risk via CLASSIFIED_BY traversal
# GQ-003 regression: must NOT return "gpai" as overall_risk for a deployer
# with hr_recruitment_screening (High risk UseCase).
# ---------------------------------------------------------------------------

def test_overall_risk_is_high(graph_result):
    """CLASSIFIED_BY traversal must elevate overall_risk to 'high' for hr_recruitment_screening."""
    assert graph_result["overall_risk"] == "high", (
        f"Expected overall_risk='high', got {graph_result['overall_risk']!r} — "
        "CLASSIFIED_BY traversal may not be wired (ADR-100 §4.3)"
    )


def test_overall_risk_not_gpai(graph_result):
    """GQ-003 regression: deployer overall_risk must not equal 'gpai' (provider-side obligation)."""
    assert graph_result["overall_risk"] != "gpai", (
        "overall_risk='gpai' is GQ-003 regression — deployer risk must not equal provider risk level"
    )


def test_overall_risk_not_minimal(graph_result):
    """overall_risk must not be 'minimal' when a High-risk UseCase is present."""
    assert graph_result["overall_risk"] not in ("minimal", "Minimal"), (
        "overall_risk is 'minimal' despite hr_recruitment_screening — "
        "CLASSIFIED_BY edge or usecase risk fold is broken"
    )


def test_usecase_hr_screening_present(graph_result):
    """hr_recruitment_screening must appear in usecase_risks with High risk level."""
    hr = next(
        (u for u in graph_result.get("usecase_risks", [])
         if u["type"] == "hr_recruitment_screening"),
        None,
    )
    assert hr is not None, "hr_recruitment_screening missing from usecase_risks"
    assert hr["risk_level"] == "High", (
        f"Expected risk_level='High', got {hr['risk_level']!r} — CLASSIFIED_BY edge missing?"
    )


def test_usecase_hr_screening_annex_metadata(graph_result):
    """hr_recruitment_screening must carry Annex III Nr. 4 and EU AI Act Art. 6."""
    hr = next(u for u in graph_result["usecase_risks"]
              if u["type"] == "hr_recruitment_screening")
    assert hr["annex_iii_nr"] == "4", f"Expected annex_iii_nr='4', got {hr['annex_iii_nr']!r}"
    assert hr["article"] == "6", f"Expected article='6', got {hr['article']!r}"


# ---------------------------------------------------------------------------
# §4.1 — data_subjects as list[str] from 4-value allowlist
# ---------------------------------------------------------------------------

def test_all_services_have_data_subjects(graph_result):
    """Every service must have data_subjects populated (non-null, non-empty)."""
    missing = [
        s["name"] for s in graph_result["services"]
        if not s.get("data_subjects")
    ]
    assert not missing, f"Services missing data_subjects: {missing} — ADR-100 §4.1 backfill incomplete"


def test_data_subjects_are_lists(graph_result):
    """data_subjects must be list[str], not a comma-separated string (ADR-100 §4.1)."""
    for svc in graph_result["services"]:
        ds = svc.get("data_subjects")
        if ds:
            assert isinstance(ds, list), (
                f"{svc['name']}.data_subjects is {type(ds).__name__}, expected list"
            )


def test_data_subjects_from_allowlist(graph_result):
    """All data_subjects values must come from the 4-value allowlist."""
    ALLOWED = {"customers", "end_users", "employees", "website_visitors"}
    violations = []
    for svc in graph_result["services"]:
        for val in svc.get("data_subjects") or []:
            if val not in ALLOWED:
                violations.append(f"{svc['name']}: {val!r}")
    assert not violations, f"data_subjects outside allowlist: {violations}"


# ---------------------------------------------------------------------------
# AVV content model — §4.1 aggregate + §4.2 structure
# ---------------------------------------------------------------------------

def test_avv_data_subjects_is_string_not_gap_marker(avv_model):
    """AVV § 2 must render data_subjects as a string, not a GapMarker."""
    assert not isinstance(avv_model.data_subjects, GapMarker), (
        "AVV data_subjects is a GapMarker — data_subjects backfill did not propagate to builder"
    )
    assert isinstance(avv_model.data_subjects, str)


def test_avv_data_subjects_contains_expected_vocab(avv_model):
    """AVV § 2 data_subjects must include at least two vocabulary terms."""
    vocab_present = [v for v in ("Kunden", "Endnutzer", "Website-Besucher")
                     if v in avv_model.data_subjects]
    assert len(vocab_present) >= 2, (
        f"AVV data_subjects missing expected vocab. Got: {avv_model.data_subjects!r}"
    )


def test_avv_includes_all_services(avv_model):
    """AVV § 1 must list all 11 detected services."""
    avv_names = {s.name for s in avv_model.services_summary}
    for svc in RAND_SERVICES:
        assert svc in avv_names, f"Service {svc!r} missing from AVV services_summary"


# ---------------------------------------------------------------------------
# VVT content model — §4.1 data_subjects per activity
# ---------------------------------------------------------------------------

def test_vvt_all_activities_have_data_subjects(vvt_model):
    """Every VVT processing activity must have data_subjects populated."""
    missing = []
    for i, act in enumerate(vvt_model.activities):
        ds = getattr(act, "data_subjects", None)
        if not ds or isinstance(ds, GapMarker):
            missing.append(f"activity[{i}]")
    assert not missing, (
        f"VVT activities without data_subjects: {missing} — "
        "ADR-100 §4.1 data_subjects not flowing into VVT builder"
    )


def test_vvt_legal_basis_present_for_majority(vvt_model):
    """At least 7/11 VVT activities must have legal_basis (3 services lack Service-node property)."""
    with_lb = sum(
        1 for act in vvt_model.activities
        if getattr(act, "legal_basis", None)
        and not isinstance(getattr(act, "legal_basis"), GapMarker)
    )
    total = len(vvt_model.activities)
    assert with_lb >= 7, (
        f"Only {with_lb}/{total} VVT activities have legal_basis — "
        "expected at least 7 (3 services lack Service.legal_basis property)"
    )
