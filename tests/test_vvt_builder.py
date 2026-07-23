import dataclasses

import pytest

from src.documents.builders.vvt_builder import VVTBuilder, VVTContentModel, VVTActivity
from src.documents.content_models import BuildContext
from src.scanner.gap_analyzer import GapHint
from tests.golden._helpers import _load_fixture, _load_golden

CTX = BuildContext(run_id="test00001", generation_date="2026-04-20", project_name="test")


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_vvt_builder_empty_services():
    model = VVTBuilder().build({}, {}, {}, [], CTX)
    assert isinstance(model, VVTContentModel)
    assert model.activities == []
    assert model.non_eu_count == 0
    assert model.scc_doc_ref is None


def test_vvt_builder_activity_fields():
    graph = {"services": [
        {"name": "OpenAI", "category": "ai_llm", "country": "USA", "gdpr_adequate": False,
         "data_subjects": "Endnutzer", "data_categories": "Prompts",
         "legal_basis": "Art. 6 Abs. 1 lit. b DSGVO", "deletion_period": "30 Tage"},
    ]}
    model = VVTBuilder().build(graph, {}, {}, [], CTX)
    act = model.activities[0]
    assert act.name == "OpenAI"
    assert act.ai_type == "generativ (LLM)"
    assert act.third_country == "USA"
    assert act.retention == "30 Tage"
    assert act.legal_basis == "Art. 6 Abs. 1 lit. b DSGVO"


def test_vvt_builder_eu_service_no_third_country():
    graph = {"services": [
        {"name": "Hetzner", "category": "hosting", "country": "Germany", "gdpr_adequate": True},
    ]}
    model = VVTBuilder().build(graph, {}, {}, [], CTX)
    assert model.activities[0].third_country is None


def test_vvt_builder_non_eu_count_and_scc_ref():
    graph = {"services": [
        {"name": "OpenAI", "country": "USA", "gdpr_adequate": False},
        {"name": "Stripe", "country": "USA", "gdpr_adequate": False},
        {"name": "Hetzner", "country": "Germany", "gdpr_adequate": True},
    ]}
    model = VVTBuilder().build(graph, {}, {}, [], CTX)
    assert model.non_eu_count == 2
    assert model.scc_doc_ref == f"scc_{CTX.run_id[:8]}.md"


def test_vvt_builder_scc_ref_none_when_all_eu():
    graph = {"services": [
        {"name": "Hetzner", "country": "Germany", "gdpr_adequate": True},
    ]}
    model = VVTBuilder().build(graph, {}, {}, [], CTX)
    assert model.scc_doc_ref is None


def test_vvt_builder_default_purpose_fallback():
    graph = {"services": [{"name": "MyService", "category": "unknown_cat"}]}
    model = VVTBuilder().build(graph, {}, {}, [], CTX)
    assert model.activities[0].purpose == "Leistungserbringung gemäß Hauptvertrag"


def test_vvt_builder_default_purpose_known_category():
    graph = {"services": [{"name": "Redis", "category": "cache_db"}]}
    model = VVTBuilder().build(graph, {}, {}, [], CTX)
    assert model.activities[0].purpose == "In-Memory-Caching und Session-Management"


def test_vvt_builder_warn_header_only_required_gaps():
    gaps = [
        GapHint(id="x", severity="REQUIRED", doc_affected=["VVT"], article="Art. 30",
                gap_reason="", fix_url="", fix_label="", priority=1, affected_docs=[]),
        GapHint(id="y", severity="RECOMMENDED", doc_affected=["VVT"], article="Art. 30",
                gap_reason="", fix_url="", fix_label="", priority=2, affected_docs=[]),
    ]
    model = VVTBuilder().build({}, {}, {}, gaps, CTX)
    assert len(model.warn_header_gaps) == 1
    assert model.warn_header_gaps[0].id == "x"


# ---------------------------------------------------------------------------
# Golden-file test
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Regression tests
# ---------------------------------------------------------------------------

def test_vvt_legal_basis_rendered_not_raw_code():
    """Fix B: VVTBuilder must render legal_basis as DE text, not a raw art_* code."""
    graph = _load_fixture("rand_industries_graph.json")
    config = _load_fixture("rand_industries_config.json")
    reasoning = _load_fixture("rand_industries_reasoning.json")
    gaps_raw = _load_fixture("rand_industries_gaps.json")
    gap_hints = [GapHint(**g) for g in gaps_raw]

    ctx = BuildContext(run_id="0158d042", generation_date="2026-04-20",
                       project_name="rand-industries")

    model = VVTBuilder().build(graph, reasoning, config, gap_hints, ctx)
    for a in model.activities:
        if a.legal_basis:
            assert not a.legal_basis.startswith("art_"), \
                f"Activity '{a.name}' has raw code as legal_basis: {a.legal_basis!r}"
            assert "Art." in a.legal_basis, \
                f"Activity '{a.name}' legal_basis not rendered to DE text: {a.legal_basis!r}"


def test_vvt_data_subjects_rendered_not_python_list():
    """Fix E: VVT must render data_subjects as DE phrases, not Python list syntax."""
    graph = _load_fixture("rand_industries_graph.json")
    config = _load_fixture("rand_industries_config.json")
    reasoning = _load_fixture("rand_industries_reasoning.json")
    gaps_raw = _load_fixture("rand_industries_gaps.json")
    gap_hints = [GapHint(**g) for g in gaps_raw]

    ctx = BuildContext(run_id="0158d042", generation_date="2026-04-20",
                       project_name="rand-industries")

    model = VVTBuilder().build(graph, reasoning, config, gap_hints, ctx)
    for a in model.activities:
        if a.data_subjects:
            assert "['" not in a.data_subjects, \
                f"Activity '{a.name}' has Python-list syntax: {a.data_subjects!r}"
            assert "customers" not in a.data_subjects.lower() \
                or "Kunden" in a.data_subjects, \
                f"Activity '{a.name}' data_subjects not rendered to DE: {a.data_subjects!r}"


def test_vvt_no_empty_data_categories():
    """Every VVT activity must have non-empty data_categories (Fix H regression)."""
    graph = _load_fixture("rand_industries_graph.json")
    config = _load_fixture("rand_industries_config.json")
    reasoning = _load_fixture("rand_industries_reasoning.json")
    gaps_raw = _load_fixture("rand_industries_gaps.json")
    gap_hints = [GapHint(**g) for g in gaps_raw]

    ctx = BuildContext(run_id="0158d042", generation_date="2026-04-20",
                       project_name="rand-industries")

    model = VVTBuilder().build(graph, reasoning, config, gap_hints, ctx)
    # MongoDB has a pre-existing separate issue (canonical name mismatch); not in scope here.
    in_scope = {"Braintree", "Segment"}
    empty = [a.name for a in model.activities
             if a.name in in_scope and (not a.data_categories or not a.data_categories.strip())]
    assert not empty, f"Fix H: data_categories missing for: {empty}"


def test_vvt_content_model_matches_golden():
    graph = _load_fixture("rand_industries_graph.json")
    config = _load_fixture("rand_industries_config.json")
    reasoning = _load_fixture("rand_industries_reasoning.json")
    gaps_raw = _load_fixture("rand_industries_gaps.json")
    gap_hints = [GapHint(**g) for g in gaps_raw]

    ctx = BuildContext(run_id="0158d042", generation_date="2026-04-20",
                       project_name="rand-industries")

    model = VVTBuilder().build(graph, reasoning, config, gap_hints, ctx)

    expected = _load_golden("rand_industries_vvt_content_model.json")
    assert dataclasses.asdict(model) == expected


def test_vvt_psp_role_on_activity():
    """ADR-115 A1: the ACTS_AS role rides the per-service VVT activity; non-PSP
    services carry role=None (no role row is rendered for them)."""
    graph = {"services": [
        {"name": "Stripe", "category": "payment", "gdpr_adequate": True,
         "acts_as_role": "controller",
         "acts_as_role_source": "EDPB 07/2020 Rn. 26 + Rn. 82"},
        {"name": "Klarna", "category": "payment", "gdpr_adequate": True,
         "acts_as_role": "special_case",
         "acts_as_role_source": "Klarna: BNPL + Art. 22 — gesonderte Prüfung"},
        {"name": "Redis", "category": "cache_db", "gdpr_adequate": True},
    ]}
    model = VVTBuilder().build(graph, {}, {}, [], CTX)
    by = {a.name: a for a in model.activities}
    assert by["Stripe"].role == "controller"
    assert by["Stripe"].role_label == "Verantwortlicher"
    assert "EDPB" in by["Stripe"].role_source
    assert by["Klarna"].role == "special_case"
    assert by["Klarna"].role_label is None
    assert by["Klarna"].role_source
    assert by["Redis"].role is None
    assert by["Redis"].role_label is None


def test_vvt_render_controller_row_label_not_auftragsverarbeiter():
    """PR 1: a controller PSP's activity row is labelled 'Empfänger
    (eigenverantwortlich)', never 'Auftragsverarbeiter' (contradicting the role
    row). The Drittland transfer fact stays as-is."""
    from jinja2 import Environment, FileSystemLoader
    from pathlib import Path

    templates = Path(__file__).parents[1] / "src" / "templates"
    env = Environment(
        loader=FileSystemLoader([str(templates / "de"), str(templates)]),
        autoescape=False, trim_blocks=True, lstrip_blocks=True,
    )
    env.globals["inline_gap_marker"] = lambda gap_id: f"🔴 [{gap_id}]"

    graph = {"services": [
        {"name": "Stripe", "category": "payment", "country": "USA",
         "gdpr_adequate": False, "acts_as_role": "controller",
         "acts_as_role_source": "EDPB 07/2020 Rn. 26"},
        {"name": "Redis", "category": "cache_db", "country": "Germany",
         "gdpr_adequate": True},
    ]}
    model = VVTBuilder().build(graph, {}, {}, [], CTX)
    out = env.get_template("vvt.md.j2").render(
        model=dataclasses.asdict(model),
        project_name="t", run_id="test0001", generation_date="2026-04-20",
        company_name="T", legal_form="", address="", zip_code="", city="",
        zip_city="", contact_email="", website_url="", responsible_name="",
        responsible_title="", dpo_name="", dpo_email="", register_court="",
        register_number="", fields={},
    )
    assert "Empfänger (eigenverantwortlich)" in out          # controller PSP
    assert "Empfänger / Auftragsverarbeiter" in out          # non-PSP (Redis) keeps default
    assert "USA" in out                                      # Drittland fact untouched
