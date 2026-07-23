from __future__ import annotations
import dataclasses

from src.documents.builders.ki_system_builder import (
    AIServiceDetail,
    AIUseCaseBlock,
    KISystemBuilder,
    KISystemContentModel,
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


def test_ki_system_builds_for_single_service():
    service = {"name": "OpenAI", "category": "ai_llm", "country": "USA", "gdpr_adequate": False}
    model = KISystemBuilder().build(
        {"risk_levels": []}, {}, {}, [], CTX,
        service=service, ai_usecase=None,
    )
    assert model.service.name == "OpenAI"
    assert model.ai_usecase is None
    assert model.is_high_risk is False


def test_ki_system_resolves_risk_level_from_graph():
    service = {"name": "OpenAI", "category": "ai_llm"}
    graph = {"risk_levels": [{"service": "OpenAI", "level": "High"}]}
    model = KISystemBuilder().build(
        graph, {}, {}, [], CTX,
        service=service, ai_usecase=None,
    )
    assert model.service.risk_level == "High"


def test_ki_system_risk_level_none_when_not_in_graph():
    service = {"name": "OpenAI"}
    model = KISystemBuilder().build(
        {}, {}, {}, [], CTX,
        service=service, ai_usecase=None,
    )
    assert model.service.risk_level is None


def test_ki_system_high_risk_triggers_fra():
    service = {"name": "OpenAI"}
    ai_usecase = {"type": "hr_recruitment_screening", "risk_level": "High",
                  "title_de": "HR-Recruiting", "article": "Annex III Nr. 4",
                  "annex_iii_nr": 4}
    model = KISystemBuilder().build(
        {}, {}, {}, [], CTX,
        service=service, ai_usecase=ai_usecase,
    )
    assert model.is_high_risk is True
    assert model.requires_fundamental_rights_assessment is True
    assert model.ai_usecase.article == "Annex III Nr. 4"
    assert model.ai_usecase.annex_iii_nr == "4"


def test_ki_system_limited_risk_no_fra():
    service = {"name": "OpenAI"}
    ai_usecase = {"type": "customer_service_chatbot", "risk_level": "Limited",
                  "title_de": "Chatbot", "article": "Art. 50"}
    model = KISystemBuilder().build(
        {}, {}, {}, [], CTX,
        service=service, ai_usecase=ai_usecase,
    )
    assert model.is_high_risk is False
    assert model.requires_fundamental_rights_assessment is False


def test_ki_system_warn_header_only_required_gaps():
    gaps = [
        _gap("a", "REQUIRED", "KI_System_Dokumentation"),
        _gap("b", "RECOMMENDED", "KI_System_Dokumentation"),
        _gap("c", "REQUIRED", "AVV"),
    ]
    service = {"name": "OpenAI"}
    model = KISystemBuilder().build(
        {}, {}, {}, gaps, CTX,
        service=service, ai_usecase=None,
    )
    assert len(model.warn_header_gaps) == 1
    assert model.warn_header_gaps[0].id == "a"


def test_ki_system_includes_processing_purpose_and_deletion_period():
    service = {
        "name": "OpenAI",
        "category": "ai_llm",
        "processing_purpose": "KI-gestützte Textgenerierung",
        "deletion_period": "30 Tage",
    }
    model = KISystemBuilder().build(
        {}, {}, {}, [], CTX,
        service=service, ai_usecase=None,
    )
    assert model.service.processing_purpose == "KI-gestützte Textgenerierung"
    assert model.service.deletion_period == "30 Tage"


def test_ki_system_content_model_matches_golden():
    import json
    from pathlib import Path
    FIXTURE = Path(__file__).parent / "fixtures"
    GOLDEN = Path(__file__).parent / "golden"

    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    config = json.loads((FIXTURE / "rand_industries_config.json").read_text())

    service = next(
        s for s in graph.get("services", [])
        if s.get("category") == "ai_llm"
    )
    ctx = BuildContext(run_id="0158d042", generation_date="2026-04-20",
                       project_name="rand-industries")
    model = KISystemBuilder().build(
        graph, {}, config, [], ctx,
        service=service, ai_usecase=None,
    )
    expected = json.loads(
        (GOLDEN / "rand_industries_ki_system_openai_content_model.json").read_text()
    )
    assert dataclasses.asdict(model) == expected
