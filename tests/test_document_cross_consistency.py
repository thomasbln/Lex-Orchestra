"""
ADR-099 Cross-Document Consistency Tests.

Guarantees that AVV, VVT, SCC derive from the same service pool — no divergence
between documents. A service appearing in SCC MUST also be in AVV/VVT. A service
in AVV MUST appear in VVT (since VVT is always required under Art. 30 DSGVO).

These tests are the machine-readable enforcement of the ADR-099 Abnahme-Kriterium:
"Ein DSB liest AVV + VVT + SCC nebeneinander. Für jedes Service-Detail findet er
eine eindeutige Primär-Stelle — kein 'steht hier UND da, identisch'."
"""
import json
from pathlib import Path

import pytest

from src.documents.builders.avv_builder import AVVBuilder
from src.documents.builders.vvt_builder import VVTBuilder
from src.documents.builders.scc_builder import SCCBuilder
from src.documents.content_models import BuildContext
from src.scanner.gap_analyzer import GapHint
from tests.golden._helpers import _load_fixture

CTX = BuildContext(
    run_id="0158d042",
    generation_date="2026-04-20",
    project_name="rand-industries",
)


@pytest.fixture
def rand_industries_inputs():
    graph = _load_fixture("rand_industries_graph.json")
    config = _load_fixture("rand_industries_config.json")
    reasoning = _load_fixture("rand_industries_reasoning.json")
    gaps_raw = _load_fixture("rand_industries_gaps.json")
    gap_hints = [GapHint(**g) for g in gaps_raw]
    return graph, config, reasoning, gap_hints


# ---------------------------------------------------------------------------
# Service-set consistency
# ---------------------------------------------------------------------------

def test_vvt_activities_subset_of_avv_services(rand_industries_inputs):
    """Every VVT activity must have a corresponding AVV service — VVT ⊆ AVV."""
    graph, config, reasoning, gaps = rand_industries_inputs
    avv = AVVBuilder().build(graph, {}, config, gaps, CTX)
    vvt = VVTBuilder().build(graph, reasoning, config, gaps, CTX)

    avv_names = {r.name for r in avv.services_summary}
    vvt_names = {a.name for a in vvt.activities}

    missing = vvt_names - avv_names
    assert not missing, f"VVT activities not in AVV: {sorted(missing)}"


def test_scc_services_subset_of_avv(rand_industries_inputs):
    """Every SCC service must have a corresponding AVV service — SCC ⊆ AVV."""
    graph, config, reasoning, gaps = rand_industries_inputs
    avv = AVVBuilder().build(graph, {}, config, gaps, CTX)
    scc = SCCBuilder().build(graph, {}, config, gaps, CTX)

    avv_names = {r.name for r in avv.services_summary}
    scc_names = {r.name for r in scc.services_with_transfer} if scc else set()

    missing = scc_names - avv_names
    assert not missing, f"SCC services not in AVV: {sorted(missing)}"


def test_scc_services_subset_of_vvt(rand_industries_inputs):
    """Every SCC service must also appear in VVT — SCC ⊆ VVT."""
    graph, config, reasoning, gaps = rand_industries_inputs
    vvt = VVTBuilder().build(graph, reasoning, config, gaps, CTX)
    scc = SCCBuilder().build(graph, {}, config, gaps, CTX)

    vvt_names = {a.name for a in vvt.activities}
    scc_names = {r.name for r in scc.services_with_transfer} if scc else set()

    missing = scc_names - vvt_names
    assert not missing, f"SCC services not in VVT: {sorted(missing)}"


def test_scc_services_are_not_gdpr_adequate(rand_industries_inputs):
    """Every SCC service must have gdpr_status == 'SCC erforderlich' in AVV.

    If a service is in SCC but AVV shows it as EU/EEA-adequate, the builders
    disagree about what 'Drittland' means — architectural bug.
    """
    graph, config, reasoning, gaps = rand_industries_inputs
    avv = AVVBuilder().build(graph, {}, config, gaps, CTX)
    scc = SCCBuilder().build(graph, {}, config, gaps, CTX)

    if not scc:
        pytest.skip("No SCC generated for this fixture — no test needed")

    avv_by_name = {r.name: r for r in avv.services_summary}
    scc_names = {r.name for r in scc.services_with_transfer}

    for name in scc_names:
        avv_row = avv_by_name[name]
        assert avv_row.gdpr_status == "SCC erforderlich", (
            f"Service {name!r} is in SCC but AVV reports gdpr_status={avv_row.gdpr_status!r}. "
            f"Builders disagree about Drittland classification."
        )


def test_all_drittland_services_in_scc(rand_industries_inputs):
    """Every service that AVV flags as 'SCC erforderlich' must appear in SCC."""
    graph, config, reasoning, gaps = rand_industries_inputs
    avv = AVVBuilder().build(graph, {}, config, gaps, CTX)
    scc = SCCBuilder().build(graph, {}, config, gaps, CTX)

    scc_required_in_avv = {
        r.name for r in avv.services_summary
        if r.gdpr_status == "SCC erforderlich"
    }
    scc_actual = {r.name for r in scc.services_with_transfer} if scc else set()

    missing = scc_required_in_avv - scc_actual
    assert not missing, (
        f"AVV flags these as requiring SCCs but SCCBuilder did not emit them: {sorted(missing)}"
    )


# ---------------------------------------------------------------------------
# Count consistency
# ---------------------------------------------------------------------------

def test_service_counts_match_graph(rand_industries_inputs):
    """AVV.services_summary and VVT.activities cover the full graph service pool."""
    graph, config, reasoning, gaps = rand_industries_inputs
    avv = AVVBuilder().build(graph, {}, config, gaps, CTX)
    vvt = VVTBuilder().build(graph, reasoning, config, gaps, CTX)

    graph_count = len(graph.get("services", []))
    assert len(avv.services_summary) == graph_count, (
        f"AVV service count {len(avv.services_summary)} != graph {graph_count}"
    )
    assert len(vvt.activities) == graph_count, (
        f"VVT activities count {len(vvt.activities)} != graph {graph_count}"
    )


def test_vvt_non_eu_count_matches_scc_size(rand_industries_inputs):
    """VVT.non_eu_count must equal len(SCC.services_with_transfer), or SCC is None."""
    graph, config, reasoning, gaps = rand_industries_inputs
    vvt = VVTBuilder().build(graph, reasoning, config, gaps, CTX)
    scc = SCCBuilder().build(graph, {}, config, gaps, CTX)

    scc_count = len(scc.services_with_transfer) if scc else 0
    assert vvt.non_eu_count == scc_count, (
        f"VVT.non_eu_count={vvt.non_eu_count} but SCC has {scc_count} services. "
        f"Builders disagree on Drittland count."
    )


# ---------------------------------------------------------------------------
# Rand-industries-specific assertions (regression guard)
# ---------------------------------------------------------------------------

def test_rand_industries_has_11_services_across_all_builders(rand_industries_inputs):
    """Regression guard: rand-industries baseline is 11 services everywhere."""
    graph, config, reasoning, gaps = rand_industries_inputs
    avv = AVVBuilder().build(graph, {}, config, gaps, CTX)
    vvt = VVTBuilder().build(graph, reasoning, config, gaps, CTX)
    scc = SCCBuilder().build(graph, {}, config, gaps, CTX)

    assert len(avv.services_summary) == 11
    assert len(vvt.activities) == 11
    assert scc is not None, "rand-industries has 11 US services — SCC must be generated"
    assert len(scc.services_with_transfer) == 11


def test_rand_industries_all_services_non_eu(rand_industries_inputs):
    """Regression guard: all rand-industries services are USA → all require SCC."""
    graph, config, reasoning, gaps = rand_industries_inputs
    avv = AVVBuilder().build(graph, {}, config, gaps, CTX)

    for row in avv.services_summary:
        assert row.gdpr_status == "SCC erforderlich", (
            f"Service {row.name!r} unexpected gdpr_status: {row.gdpr_status!r}"
        )
