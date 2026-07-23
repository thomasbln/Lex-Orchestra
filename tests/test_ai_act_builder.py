from __future__ import annotations
import dataclasses
from unittest.mock import MagicMock, patch

from src.documents.builders.ai_act_builder import (
    AIActBuilder,
    AIActContentModel,
    AIActUseCaseBlock,
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


def _mock_gc(**query_returns):
    """Build a MagicMock that behaves like a GraphClient context manager."""
    gc = MagicMock()
    gc.get_usecases_for_risk_level = MagicMock(
        side_effect=lambda lvl: query_returns.get(f"uc_{lvl}", []),
    )
    gc.get_indicated_usecases = MagicMock(
        return_value=query_returns.get("indicated", []),
    )
    gc.get_law_text = MagicMock(return_value=query_returns.get("art4"))
    ctx_mgr = MagicMock()
    ctx_mgr.__enter__ = MagicMock(return_value=gc)
    ctx_mgr.__exit__ = MagicMock(return_value=False)
    return ctx_mgr


def test_ai_act_uses_single_graph_context():
    """_fetch_graph_data must open exactly ONE GraphClient context."""
    config = {"ai_usecase_type": "hr_recruitment_screening"}
    with patch("src.graph.graph_client.GraphClient") as gc_cls:
        gc_cls.return_value = _mock_gc(
            uc_High=[{"type": "hr_recruitment_screening", "title_de": "HR",
                      "risk_level": "High"}],
            uc_Limited=[], uc_Minimal=[],
            art4="2025-02-02",
        )
        AIActBuilder().build({"services": []}, {}, config, [], CTX)
        assert gc_cls.call_count == 1


def test_ai_act_deployer_usecase_resolved_from_config():
    config = {"ai_usecase_type": "hr_recruitment_screening"}
    with patch("src.graph.graph_client.GraphClient") as gc_cls:
        gc_cls.return_value = _mock_gc(
            uc_High=[{"type": "hr_recruitment_screening", "title_de": "HR",
                      "risk_level": "High", "article": "Annex III Nr. 4"}],
            uc_Limited=[], uc_Minimal=[],
        )
        model = AIActBuilder().build({"services": []}, {}, config, [], CTX)

    assert model.deployer_usecase is not None
    assert model.deployer_usecase.title_de == "HR"


def test_ai_act_deployer_usecase_reason_passed_through():
    """PR G FIX 2: UseCase.reason from the graph reaches the §3 Begründung block."""
    config = {"ai_usecase_type": "hr_recruitment_screening"}
    with patch("src.graph.graph_client.GraphClient") as gc_cls:
        gc_cls.return_value = _mock_gc(
            uc_High=[{"type": "hr_recruitment_screening", "title_de": "HR",
                      "risk_level": "High", "article": "Annex III Nr. 4",
                      "reason": "Anhang III Nr. 4: Beschäftigung, Personalmanagement"}],
            uc_Limited=[], uc_Minimal=[],
        )
        model = AIActBuilder().build({"services": []}, {}, config, [], CTX)

    assert model.deployer_usecase is not None
    assert model.deployer_usecase.reason == "Anhang III Nr. 4: Beschäftigung, Personalmanagement"


def test_ai_act_indicated_usecases_when_no_config():
    with patch("src.graph.graph_client.GraphClient") as gc_cls:
        gc_cls.return_value = _mock_gc(
            indicated=[{"type": "customer_service_chatbot", "title_de": "Chatbot",
                        "risk_level": "Limited"}],
            uc_High=[], uc_Limited=[], uc_Minimal=[],
        )
        model = AIActBuilder().build(
            {"services": [{"name": "OpenAI"}]}, {}, {}, [], CTX,
        )

    assert len(model.indicated_usecases) == 1
    assert model.deployer_usecase is None


def test_ai_act_audit_trail_gap_flag():
    graph = {"services": [], "active_risks": ["NO_AI_AUDIT_TRAIL"]}
    with patch("src.graph.graph_client.GraphClient") as gc_cls:
        gc_cls.return_value = _mock_gc()
        model = AIActBuilder().build(graph, {}, {}, [], CTX)

    assert model.has_audit_trail_gap is True


def test_ai_act_graceful_fallback_on_graph_failure():
    with patch("src.graph.graph_client.GraphClient") as gc_cls:
        gc_cls.side_effect = Exception("connection refused")
        model = AIActBuilder().build({"services": []}, {}, {}, [], CTX)

    assert model.deployer_usecase is None
    assert model.indicated_usecases == []
    assert model.all_usecases == []
    assert model.art4_effective_date == "2025-02-02"


def test_ai_act_law_references_stub_present():
    """ADR-098 PR 3 stub: law_references field exists and defaults to []."""
    with patch("src.graph.graph_client.GraphClient") as gc_cls:
        gc_cls.return_value = _mock_gc()
        model = AIActBuilder().build({"services": []}, {}, {}, [], CTX)

    assert model.law_references == []
    fields = {f.name for f in dataclasses.fields(AIActContentModel)}
    assert "law_references" in fields


def test_ai_act_risk_levels_mapped_from_graph():
    graph = {"services": [], "risk_levels": [
        {"service": "OpenAI", "level": "High"},
        {"service": "Mixpanel", "level": "Limited"},
    ]}
    with patch("src.graph.graph_client.GraphClient") as gc_cls:
        gc_cls.return_value = _mock_gc()
        model = AIActBuilder().build(graph, {}, {}, [], CTX)

    assert len(model.risk_levels) == 2
    assert model.risk_levels[0].service == "OpenAI"


def test_ai_act_warn_header_only_required_gaps():
    gaps = [
        _gap("a", "REQUIRED", "AI_Act_Manifest"),
        _gap("b", "RECOMMENDED", "AI_Act_Manifest"),
        _gap("c", "REQUIRED", "AVV"),
    ]
    with patch("src.graph.graph_client.GraphClient") as gc_cls:
        gc_cls.return_value = _mock_gc()
        model = AIActBuilder().build({"services": []}, {}, {}, gaps, CTX)

    assert len(model.warn_header_gaps) == 1
    assert model.warn_header_gaps[0].id == "a"
