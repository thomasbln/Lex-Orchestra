"""Tests for ADR-028 Layer 2 — pii_filter (Presidio)."""
import pytest
from src.scanner.pii_filter import anonymize, anonymize_signals, is_available

_presidio_installed = is_available()
requires_presidio = pytest.mark.skipif(
    not _presidio_installed,
    reason="Presidio not installed (runs in lex-agent container only)",
)


@requires_presidio
def test_presidio_available():
    """Presidio must be installed in lex-agent container."""
    assert is_available()


@requires_presidio
def test_anonymize_email():
    result = anonymize("Send to thomas@lex-orchestra.com for review")
    assert "thomas@lex-orchestra.com" not in result
    assert "<EMAIL_ADDRESS>" in result


@requires_presidio
def test_anonymize_person():
    result = anonymize("Approved by Thomas Rehmer on Monday")
    assert "Thomas Rehmer" not in result


def test_anonymize_empty_string():
    assert anonymize("") == ""


def test_anonymize_no_pii():
    """Code without PII passes through unchanged."""
    text = "import anthropic\nclient = anthropic.Anthropic()"
    result = anonymize(text)
    assert "anthropic" in result


@requires_presidio
def test_anonymize_signals_cleans_evidence():
    signals = [{
        "signal_type": "personal_data",
        "evidence": ["src/app.py: thomas@example.com"],
        "confidence": 0.8,
        "source": "regex",
    }]
    cleaned = anonymize_signals(signals)
    assert "thomas@example.com" not in cleaned[0]["evidence"][0]


def test_anonymize_signals_does_not_mutate():
    """anonymize_signals must return new list, never mutate input."""
    original = [{"signal_type": "ai_usage", "evidence": ["src/app.py"], "confidence": 0.7}]
    cleaned = anonymize_signals(original)
    assert cleaned is not original
    assert cleaned[0] is not original[0]


def test_anonymize_signals_empty():
    assert anonymize_signals([]) == []
