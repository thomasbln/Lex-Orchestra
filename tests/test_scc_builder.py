import dataclasses

import pytest

from src.documents.builders.scc_builder import SCCBuilder, SCCContentModel, SCCServiceRow
from src.documents.content_models import BuildContext
from src.scanner.gap_analyzer import GapHint
from tests.golden._helpers import _load_fixture, _load_golden

CTX = BuildContext(run_id="test00001", generation_date="2026-04-20", project_name="test")


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_scc_builder_returns_none_when_no_drittland():
    graph = {"services": [
        {"name": "Hetzner", "country": "Germany", "gdpr_adequate": True},
        {"name": "Supabase", "country": "Germany", "gdpr_adequate": True},
    ]}
    result = SCCBuilder().build(graph, {}, {}, [], CTX)
    assert result is None


def test_scc_builder_returns_none_when_services_empty():
    result = SCCBuilder().build({}, {}, {}, [], CTX)
    assert result is None


def test_scc_builder_returns_none_when_country_unknown():
    # country=None is unknown — not a confirmed Drittland-Transfer
    graph = {"services": [
        {"name": "Unknown", "country": None, "gdpr_adequate": False},
    ]}
    result = SCCBuilder().build(graph, {}, {}, [], CTX)
    assert result is None


def test_scc_builder_returns_model_for_drittland_services():
    graph = {"services": [
        {"name": "OpenAI", "country": "USA", "gdpr_adequate": False, "dpa_url": "https://openai.com/dpa"},
        {"name": "Hetzner", "country": "Germany", "gdpr_adequate": True, "dpa_url": None},
    ]}
    model = SCCBuilder().build(graph, {}, {}, [], CTX)
    assert isinstance(model, SCCContentModel)
    assert len(model.services_with_transfer) == 1
    assert model.services_with_transfer[0].name == "OpenAI"
    assert model.services_with_transfer[0].country == "USA"
    assert model.services_with_transfer[0].dpa_url == "https://openai.com/dpa"


def test_scc_builder_excludes_eu_services():
    graph = {"services": [
        {"name": "OpenAI", "country": "USA", "gdpr_adequate": False},
        {"name": "Stripe", "country": "USA", "gdpr_adequate": False},
        {"name": "Hetzner", "country": "Germany", "gdpr_adequate": True},
        {"name": "Supabase", "country": "Germany", "gdpr_adequate": True},
    ]}
    model = SCCBuilder().build(graph, {}, {}, [], CTX)
    assert model is not None
    names = [r.name for r in model.services_with_transfer]
    assert "OpenAI" in names
    assert "Stripe" in names
    assert "Hetzner" not in names
    assert "Supabase" not in names


def test_scc_builder_warn_header_only_required_gaps():
    gaps = [
        GapHint(id="a", severity="REQUIRED", doc_affected=["SCC"], article="Art. 46",
                gap_reason="", fix_url="", fix_label="", priority=1, affected_docs=[]),
        GapHint(id="b", severity="RECOMMENDED", doc_affected=["SCC"], article="Art. 46",
                gap_reason="", fix_url="", fix_label="", priority=2, affected_docs=[]),
    ]
    graph = {"services": [{"name": "OpenAI", "country": "USA", "gdpr_adequate": False}]}
    model = SCCBuilder().build(graph, {}, {}, gaps, CTX)
    assert model is not None
    assert len(model.warn_header_gaps) == 1
    assert model.warn_header_gaps[0].id == "a"


def test_select_services_for_scc_static_method():
    services = [
        {"name": "OpenAI", "country": "USA", "gdpr_adequate": False},
        {"name": "Hetzner", "country": "Germany", "gdpr_adequate": True},
        {"name": "Unknown", "country": None, "gdpr_adequate": False},
    ]
    result = SCCBuilder.select_services_for_scc(services)
    assert len(result) == 1
    assert result[0]["name"] == "OpenAI"


# ---------------------------------------------------------------------------
# Golden-file test
# ---------------------------------------------------------------------------

def test_scc_content_model_matches_golden():
    graph = _load_fixture("rand_industries_graph.json")
    config = _load_fixture("rand_industries_config.json")
    reasoning = _load_fixture("rand_industries_reasoning.json")
    gaps_raw = _load_fixture("rand_industries_gaps.json")
    gap_hints = [GapHint(**g) for g in gaps_raw]

    ctx = BuildContext(run_id="0158d042", generation_date="2026-04-20",
                       project_name="rand-industries")

    model = SCCBuilder().build(graph, reasoning, config, gap_hints, ctx)

    expected = _load_golden("rand_industries_scc_content_model.json")
    assert dataclasses.asdict(model) == expected


# ---------------------------------------------------------------------------
# Template render: inferred glyph (≈) + conditional legend
# ---------------------------------------------------------------------------

def _render_scc(model):
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader, ChainableUndefined

    templates_dir = Path(__file__).parents[1] / "src" / "templates"
    env = Environment(
        loader=FileSystemLoader([str(templates_dir / "de"), str(templates_dir)]),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=ChainableUndefined,
    )
    env.globals["has_signal"] = lambda name, min_confidence=0.5: False
    env.globals["inline_gap_marker"] = lambda gap_id: f"🔴 {gap_id}"
    return env.get_template("scc.md.j2").render(
        model=model, run_id="0158d042", generation_date="2026-04-20", lang="de"
    )


def _scc_model_from_fixtures():
    graph = _load_fixture("rand_industries_graph.json")
    config = _load_fixture("rand_industries_config.json")
    reasoning = _load_fixture("rand_industries_reasoning.json")
    gap_hints = [GapHint(**g) for g in _load_fixture("rand_industries_gaps.json")]
    ctx = BuildContext(run_id="0158d042", generation_date="2026-04-20",
                       project_name="rand-industries")
    return SCCBuilder().build(graph, reasoning, config, gap_hints, ctx)


def test_scc_render_marks_inferred_purpose_with_glyph_and_one_legend():
    model = _scc_model_from_fixtures()
    out = _render_scc(model)
    # Braintree/MongoDB/Segment carry the inferred purpose → glyph present
    assert "≈" in out
    # ADR-076 addendum: ≈ legend entry rendered exactly once via the unified legend() macro
    # (conditional, top of doc — not per-row).
    assert out.count("kein Einzelnachweis; zu bestätigen") == 1
    # An evidenced purpose must NOT carry the glyph
    assert "≈ Zahlungsabwicklung, Betrugsprävention" not in out


def test_scc_render_omits_legend_when_no_inferred_rows():
    model = _scc_model_from_fixtures()
    for row in model.services_with_transfer:
        row.processing_purpose_inferred = False
    out = _render_scc(model)
    assert "≈" not in out
    assert "kein Einzelnachweis; zu bestätigen" not in out
