"""Tests for ADR-028 Layer 3 — llm_classifier (Phi-4-mini)."""
import pytest
from src.scanner.llm_classifier import (
    classify, classify_all, compute_dsfa_trigger, is_available, _parse_output
)

requires_ollama = pytest.mark.skipif(
    not is_available(),
    reason="Ollama not available — run on Pi",
)


# ── Pure logic tests (no Ollama needed) ──────────────────────────────────────

def test_parse_output_strips_punctuation():
    assert _parse_output("yes.", {"yes", "no"}) == "yes"
    assert _parse_output("No,", {"yes", "no"}) == "no"


def test_parse_output_unknown_returns_none():
    assert _parse_output("maybe", {"yes", "no"}) == "none"


def test_parse_output_none_input():
    assert _parse_output(None, {"yes", "no"}) == "none"


def test_dsfa_trigger_art9():
    assert compute_dsfa_trigger({
        "art9_category": "health", "decision_logic": "no", "autonomy_level": "none"
    })


def test_dsfa_trigger_autonomous_decision():
    assert compute_dsfa_trigger({
        "art9_category": "none", "decision_logic": "yes", "autonomy_level": "autonomous"
    })


def test_dsfa_trigger_false():
    assert not compute_dsfa_trigger({
        "art9_category": "none", "decision_logic": "no", "autonomy_level": "none"
    })


def test_classify_invalid_task_key():
    assert classify("nonexistent_task", "some text") == "none"


# ── Ollama integration tests (Pi only) ──────────────────────────────────────

@requires_ollama
def test_classify_decision_logic_yes():
    assert classify("decision_logic", "if score > 0.8: approveLoan(user_id)") == "yes"


@requires_ollama
def test_classify_decision_logic_no():
    result = classify("decision_logic", "def greet(name): return f'Hello {name}'")
    assert result == "no"


@requires_ollama
def test_classify_returns_allowed_value():
    allowed = {"hr", "marketing", "legal", "customer_service", "content_generation", "general", "none"}
    assert classify("prompt_role", "You are a helpful assistant.") in allowed


@requires_ollama
def test_classify_all_has_all_tasks():
    result = classify_all("import openai")
    assert set(result.keys()) == {"prompt_role", "decision_logic", "art9_category", "autonomy_level"}
