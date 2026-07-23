from __future__ import annotations
import dataclasses

from src.documents.builders.ki_policy_builder import (
    AIServiceRow,
    KIPolicyBuilder,
    KIPolicyContentModel,
)
from src.documents.content_models import BuildContext
from src.scanner.gap_analyzer import GapHint

CTX = BuildContext(
    run_id="test00001",
    generation_date="2026-04-20",
    project_name="test-project",
)


def _gap(id: str, severity: str, doc: str) -> GapHint:
    return GapHint(id=id, severity=severity, doc_affected=[doc], affected_docs=[doc])


def test_ki_policy_builds_ai_services_from_input():
    graph = {"services": [
        {"name": "OpenAI", "category": "ai_llm", "country": "USA", "gdpr_adequate": False},
    ]}
    model = KIPolicyBuilder().build(graph, {}, {}, [], CTX)
    assert len(model.ai_services) == 1
    assert model.ai_services[0].name == "OpenAI"


def test_ki_policy_empty_services_when_no_input():
    model = KIPolicyBuilder().build({"services": []}, {}, {}, [], CTX)
    assert model.ai_services == []


def test_ki_policy_has_drittland_flag_true_for_non_eu():
    graph = {"services": [
        {"name": "OpenAI", "category": "ai_llm", "country": "USA", "gdpr_adequate": False},
    ]}
    model = KIPolicyBuilder().build(graph, {}, {}, [], CTX)
    assert model.has_drittland is True
    assert model.has_llm is True


def test_ki_policy_has_drittland_false_for_eu_only():
    graph = {"services": [
        {"name": "Langfuse", "category": "observability", "country": "Germany", "gdpr_adequate": True},
    ]}
    model = KIPolicyBuilder().build(graph, {}, {}, [], CTX)
    assert model.has_drittland is False


def test_ki_policy_has_llm_false_when_no_llm():
    graph = {"services": [
        {"name": "Langfuse", "category": "observability", "country": "Germany", "gdpr_adequate": True},
    ]}
    model = KIPolicyBuilder().build(graph, {}, {}, [], CTX)
    assert model.has_llm is False


def test_ki_policy_warn_header_only_required_gaps():
    gaps = [
        _gap("a", "REQUIRED", "KI_Policy"),
        _gap("b", "RECOMMENDED", "KI_Policy"),
        _gap("c", "REQUIRED", "AVV"),
    ]
    model = KIPolicyBuilder().build({"services": []}, {}, {}, gaps, CTX)
    assert len(model.warn_header_gaps) == 1
    assert model.warn_header_gaps[0].id == "a"


def test_ki_policy_purpose_falls_back_to_category_default():
    graph = {"services": [
        {"name": "OpenAI", "category": "ai_llm", "country": "USA", "gdpr_adequate": False},
    ]}
    model = KIPolicyBuilder().build(graph, {}, {}, [], CTX)
    assert "KI-gestützte Textgenerierung" in model.ai_services[0].purpose


def test_ki_policy_purpose_prefers_service_property():
    graph = {"services": [
        {"name": "OpenAI", "category": "ai_llm", "country": "USA", "gdpr_adequate": False,
         "purpose": "Custom purpose"},
    ]}
    model = KIPolicyBuilder().build(graph, {}, {}, [], CTX)
    assert model.ai_services[0].purpose == "Custom purpose"


def test_ki_policy_content_model_matches_golden():
    import json
    from pathlib import Path
    FIXTURE = Path(__file__).parent / "fixtures"
    GOLDEN = Path(__file__).parent / "golden"

    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    config = json.loads((FIXTURE / "rand_industries_config.json").read_text())
    gaps = json.loads((FIXTURE / "rand_industries_gaps.json").read_text())

    # Replicate what generate_all does: filter ai-relevant services before passing
    ai_services = [
        s for s in graph.get("services", [])
        if s.get("ai_act_relevant") or s.get("category") == "ai_llm"
    ]
    graph_for_builder = {"services": ai_services}

    gap_hints = [GapHint(**g) if isinstance(g, dict) else g for g in gaps]

    ctx = BuildContext(run_id="0158d042", generation_date="2026-04-20",
                       project_name="rand-industries")
    model = KIPolicyBuilder().build(graph_for_builder, {}, config, gap_hints, ctx)
    expected = json.loads(
        (GOLDEN / "rand_industries_ki_policy_content_model.json").read_text()
    )
    assert dataclasses.asdict(model) == expected
