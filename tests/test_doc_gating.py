"""Pre-DSB sprint Schritt 1.5 — minimal KI-doc gating.

The four AI/KI documents (AI_Act_Manifest, KI_Policy, KI_System, DSFA) must
render ONLY when AI services are detected. An AI Act manifest or a DSFA for an
AI-free stack asserts obligations that do not apply.
"""
from pathlib import Path
from unittest.mock import patch

from src.agents.document_architect import DocumentOrchestrator

_NO_AI_GRAPH = {
    "doc_types": ["AVV", "TOM", "AI_Act_Manifest"],
    "services": [
        {"name": "Stripe", "category": "payment", "dpa_url": "https://stripe.com/dpa",
         "gdpr_adequate": False, "country": "USA"},
        {"name": "Postmark", "category": "email", "gdpr_adequate": True},
    ],
    "controls": [], "risk_levels": [], "overall_risk": "limited",
    "active_risks": [], "usecase_risks": [],
    "_graph_client": None,
}

_AI_GRAPH = {
    "doc_types": ["AVV", "TOM", "AI_Act_Manifest"],
    "services": [
        {"name": "Stripe", "category": "payment", "gdpr_adequate": False, "country": "USA"},
        {"name": "OpenAI", "category": "ai_llm", "ai_act_relevant": True,
         "gdpr_adequate": False, "country": "USA"},
    ],
    "controls": [], "risk_levels": [], "overall_risk": "high",
    "active_risks": [], "usecase_risks": [],
    "_graph_client": None,
}

_AI_WRITERS = (
    "_write_ai_act_manifest",
    "_write_ki_policy",
    "_write_ki_system_doc",
    "_write_dsfa",
)


def _run(graph: dict):
    arch = DocumentOrchestrator()
    calls: set[str] = set()

    def _spy(name):
        def _fn(*args, **kwargs):
            calls.add(name)
            return Path(f"/tmp/fake_{name}.md")
        return _fn

    writers = ("_write_avv", "_write_tom", "_write_vvt", *_AI_WRITERS)
    with patch.object(arch, "_load_project_config", return_value={}), \
         patch.object(arch, "_load_project_setup", return_value=None), \
         patch.object(arch, "_resolve_ai_usecase", return_value=None), \
         patch("src.agents.document_architect.load_retention_policies", return_value=[]), \
         patch.object(arch, "_save_doc", return_value={}):
        for w in writers:
            patch.object(arch, w, side_effect=_spy(w)).start()
        arch.generate_all(
            graph_result=graph, reasoning_result={},
            project_name="test-gating", run_id="test-run-id",
        )
    patch.stopall()
    return calls


def test_no_ai_suppresses_all_four_ki_docs():
    calls = _run(_NO_AI_GRAPH)
    for w in _AI_WRITERS:
        assert w not in calls, f"{w} ran for an AI-free stack"
    # The non-AI docs still generate
    assert "_write_avv" in calls
    assert "_write_tom" in calls
    assert "_write_vvt" in calls


def test_ai_detected_generates_ki_docs():
    calls = _run(_AI_GRAPH)
    assert "_write_ai_act_manifest" in calls
    assert "_write_ki_policy" in calls
    assert "_write_ki_system_doc" in calls
