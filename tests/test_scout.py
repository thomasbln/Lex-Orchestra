"""
Tests: Infrastructure Scout — Signal Categories 2 + 3
======================================================
ADR-014: Security posture detection + AI deployment signals.
All tests use tmp_path — no network, no DB, no Neo4j.
"""

import pytest
from src.scout.lex_orchestra_scout import run_scout


def test_detects_hardcoded_api_key(tmp_path):
    """CRITICAL finding for hardcoded sk- key."""
    (tmp_path / "agent.py").write_text('api_key = "sk-abcdefghijklmnopqrstuvwxyz123456"')
    result = run_scout(repo_path=str(tmp_path), live_url=None)
    findings = result["security_findings"]
    assert any(f["severity"] == "CRITICAL" for f in findings)
    assert any("A.9.4.1" in f["iso_control"] for f in findings)


def test_skips_env_reference(tmp_path):
    """os.getenv() is not a hardcoded secret — must be skipped."""
    (tmp_path / "config.py").write_text('api_key = os.getenv("OPENAI_API_KEY")')
    result = run_scout(repo_path=str(tmp_path), live_url=None)
    assert not result["security_findings"]


def test_detects_system_prompt(tmp_path):
    """System prompt pattern → deployment signal with usecase_hint ai_assistant_general."""
    (tmp_path / "agent.py").write_text('system_prompt = "You are a helpful assistant."')
    result = run_scout(repo_path=str(tmp_path), live_url=None)
    signals = result["deployment_signals"]
    assert any(s["usecase_hint"] == "ai_assistant_general" for s in signals)
    assert all(s["verified"] is False for s in signals)


def test_detects_langchain_import(tmp_path):
    """LangChain import → service detected (openai or langchain)."""
    (tmp_path / "chain.py").write_text("from langchain.chat_models import ChatOpenAI")
    result = run_scout(repo_path=str(tmp_path), live_url=None)
    names = [s["name"].lower() for s in result["services"]]
    assert "openai" in names or "langchain" in names


def test_detects_docker_privileged(tmp_path):
    """privileged: true → HIGH security finding."""
    dc = tmp_path / "docker-compose.yml"
    dc.write_text("services:\n  app:\n    image: myapp\n    privileged: true\n")
    result = run_scout(repo_path=str(tmp_path), live_url=None)
    findings = result["security_findings"]
    assert any(
        f["severity"] == "HIGH" and "privileged" in f["description"].lower()
        for f in findings
    )


def test_finding_file_is_relative_path(tmp_path):
    """file field must be relative — not absolute path (ADR-001 PII concern)."""
    (tmp_path / "secret.py").write_text('key = "sk-abcdefghijklmnopqrstuvwxyz123456"')
    result = run_scout(repo_path=str(tmp_path), live_url=None)
    for finding in result["security_findings"]:
        assert not finding["file"].startswith("/"), (
            f"Finding file path must be relative, got: {finding['file']}"
        )


def test_run_scout_empty_repo(tmp_path):
    """Empty repo returns empty lists — no crash."""
    result = run_scout(repo_path=str(tmp_path), live_url=None)
    assert result["services"] == []
    assert result["security_findings"] == []
    assert result["deployment_signals"] == []
    assert result["risk_signals"] == []
