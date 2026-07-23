"""Tests for ADR-027 scan_signals — Schicht 1 Regex Scanner."""
from pathlib import Path

from src.scout.lex_orchestra_scout import extract_risk_signals


def test_personal_data_detected(tmp_path):
    """personal_data signal detected from req.body.email pattern."""
    (tmp_path / "app.py").write_text("req.body.email")
    signals = extract_risk_signals(tmp_path)
    assert any(s["signal_type"] == "personal_data" for s in signals)


def test_secret_detected(tmp_path):
    """secret_detected signal from hardcoded API key pattern."""
    (tmp_path / "config.py").write_text('api_key = "sk-abcdefghijklmnopqrstuvwx"')
    signals = extract_risk_signals(tmp_path)
    assert any(s["signal_type"] == "secret_detected" for s in signals)


def test_confidence_bounded(tmp_path):
    """confidence must be between 0 and 1 for all signals."""
    (tmp_path / "app.py").write_text(
        "req.body.email\napproveLoan()\nopenai.\nlanggraph\nchatbot\n"
    )
    signals = extract_risk_signals(tmp_path)
    for s in signals:
        assert 0 <= s["confidence"] <= 1, f"Out of range: {s}"


def test_evidence_relative_paths_only(tmp_path):
    """evidence[] must contain relative paths, never absolute paths."""
    (tmp_path / "service.py").write_text("anthropic.Anthropic()")
    signals = extract_risk_signals(tmp_path)
    for s in signals:
        for ev in s.get("evidence", []):
            assert not ev.startswith("/"), f"Absolute path in evidence: {ev}"


def test_empty_dir_returns_no_signals(tmp_path):
    """Empty directory produces no signals."""
    signals = extract_risk_signals(tmp_path)
    assert signals == []


def test_source_field_is_regex(tmp_path):
    """source field must be 'regex' for Schicht 1."""
    (tmp_path / "app.py").write_text("langgraph")
    signals = extract_risk_signals(tmp_path)
    for s in signals:
        assert s["source"] == "regex"
