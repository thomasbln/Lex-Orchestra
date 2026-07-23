"""
Layer 1 — Deterministic Regex Scanner (ADR-028)
================================================
Scans local repo files for risk-relevant patterns.
Output: list[SignalCat1] — structured signal dicts for scan_signals table.

ADR-001: evidence[] contains only relative file paths, never code content.
ADR-028: System-prompt content is NEVER extracted or forwarded.
         Only boolean has_system_prompt propagates to Layer 2/3.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Skip dirs (never scan these) ──────────────────────────────────────────────

SKIP_DIRS = {
    ".venv", "venv", "node_modules", "docs", "tests", "test",
    "fixtures", "mocks", "__mocks__", "spec", "__tests__",
    ".git", "__pycache__", ".mypy_cache", ".pytest_cache",
    "dist", "build", ".next", ".nuxt", ".claude",
}

SOURCE_EXTENSIONS = {
    "py", "ts", "js",
    "html", "htm", "php",   # inline scripts, hardcoded credentials, imprint/contact content
    "yml", "yaml", "json", "env", "example",
}

# ── Signal patterns (ADR-028 taxonomy) ────────────────────────────────────────

SIGNAL_PATTERNS: dict[str, list[str]] = {
    "personal_data": [
        r"req\.body\.(email|name|phone|address)",
        r"\buser_id\b",
        r"db\.insert\(user",
        r"INSERT INTO users",
        r"\.email\b",
        r"first_name|last_name|full_name",
    ],
    "decision_logic": [
        r"approveLoan|rejectApplication|approve\(|reject\(",
        r"if\s*\(\s*score\s*[><=]",
        r"hire\(|deny\(|disqualify\(",
        r"creditScore|riskScore|fraudScore",
    ],
    "ai_usage": [
        r"openai\.|anthropic\.",
        r"client\.messages\.create",
        r"ChatCompletion|completions\.create",
        r"from openai|import openai",
        r"from anthropic|import anthropic",
    ],
    "autonomy": [
        r"langgraph|autogen|crewai",
        r"system\.execute|auto_decide",
        r"AgentExecutor|run_agent",
        r"autonomous|agentic",
    ],
    "user_interaction": [
        r"@app\.(?:post|get)\(['\"]\/chat",
        r"\bchatbot\b",
        r"req\.body\.message",
        r"chat_history|conversation_history",
    ],
    "system_prompt": [
        r'"role"\s*:\s*"system"',
        r"SYSTEM_PROMPT\s*=",
        r"system\s*=\s*['\"`]",
        r"SystemMessage\(",
        r"system_prompt\s*=",
    ],
    "secret_detected": [
        r"sk-[a-zA-Z0-9]{20,}",
        r"AKIA[0-9A-Z]{16}",
        r"ghp_[a-zA-Z0-9]{36}",
        r"(?i)password\s*=\s*['\"][^'\"]{8,}['\"]",
        r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----",
    ],
    "docker_misconfiguration": [
        r"privileged:\s*true",
        r"/var/run/docker\.sock",
        r"0\.0\.0\.0:5432",
        r"0\.0\.0\.0:3306",
        r"network_mode:\s*host",
    ],
}

# Base confidence per signal type (ADR-027)
SIGNAL_CONFIDENCE: dict[str, float] = {
    "secret_detected":         0.95,
    "docker_misconfiguration": 0.90,
    "autonomy":                0.90,
    "decision_logic":          0.80,
    "system_prompt":           0.80,
    "personal_data":           0.70,
    "ai_usage":                0.70,
    "user_interaction":        0.70,
}

# Lines with these markers are skipped (references to env vars, not real values)
SKIP_MARKERS = [
    "os.getenv", "process.env", "os.environ",
    "example", "placeholder", "your_", "TODO", "FIXME",
    "<", ">",
]


def _iter_source_files(base: Path) -> list[Path]:
    """Yield source files skipping SKIP_DIRS."""
    results = []
    for path in base.rglob("*"):
        rel = path.relative_to(base)
        if any(skip in rel.parts for skip in SKIP_DIRS):
            continue
        if path.is_file() and path.suffix.lstrip(".") in SOURCE_EXTENSIONS:
            results.append(path)
    return results


def _rel(base: Path, path: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return path.name


def scan(base_path: Path, run_id: str = "unknown") -> tuple[list[dict], dict[str, str]]:
    """
    Layer 1 — scan source files for risk signals.

    Returns:
        (signals, content_snippets)
        signals: list of signal dicts (unchanged)
        content_snippets: {rel_path: first_500_chars} for ALL opened files (ADR-049 Option C).
                          Presidio runs on every snippet in Layer 2.
                          Content is NEVER stored beyond Layer 2 (ADR-001).
    """
    signals: list[dict] = []
    content_snippets: dict[str, str] = {}
    MAX_SNIPPET = 500
    files = _iter_source_files(base_path)
    logger.info("Layer 1: scanning %d files in %s", len(files), base_path)

    for signal_type, patterns in SIGNAL_PATTERNS.items():
        matches: list[str] = []
        snippets: list[str] = []                      # ADR-070: RAM-only, never persisted
        seen_snippet_files: set[str] = set()          # dedupe per (signal_type, file)

        for file_path in files:
            rel = _rel(base_path, file_path)
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # ADR-049 Option C: collect snippet for ALL opened files
            if rel not in content_snippets:
                content_snippets[rel] = content[:MAX_SNIPPET]

            all_lines = content.splitlines()          # split once for context slicing
            for idx, line in enumerate(all_lines):
                if signal_type == "secret_detected":
                    if any(m.lower() in line.lower() for m in SKIP_MARKERS):
                        continue

                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        matches.append(rel)
                        # ADR-070: first match per (signal_type, file) captures ±3 lines
                        if rel not in seen_snippet_files:
                            start = max(0, idx - 3)
                            end = min(len(all_lines), idx + 4)
                            snippets.append("\n".join(all_lines[start:end])[:300])
                            seen_snippet_files.add(rel)
                        break  # one match per line per signal_type

        if matches:
            unique_files = list(dict.fromkeys(matches))[:5]
            base_conf = SIGNAL_CONFIDENCE.get(signal_type, 0.70)
            confidence = min(base_conf + len(unique_files) * 0.01, 0.95)
            signals.append({
                "signal_type":       signal_type,
                "value":             "detected",
                "confidence":        round(confidence, 2),
                "evidence":          unique_files,   # paths only — ADR-001 unchanged
                "evidence_snippets": snippets[:5],   # ADR-070: RAM-only, never persisted
                "source":            "regex",
            })

    logger.info(
        "Layer 1: %d signals detected, %d files queued for Presidio content scan",
        len(signals), len(content_snippets),
    )

    try:
        from src.utils.scan_logger import log_layer1_complete
        log_layer1_complete(run_id, signals)
    except Exception:
        pass

    return signals, content_snippets


def extract_system_prompt(base_path: Path) -> tuple[str | None, str | None]:
    """
    Extract first system prompt found in the repo.
    Returns (raw_content, source) or (None, None) if not found.
    Truncates to 1024 chars — role classification needs only the beginning.
    NEVER logs extracted content (ADR-001).
    source: 'env' | 'python' | 'json'
    """
    patterns = {
        "env": [
            r'SYSTEM_PROMPT\s*=\s*["\'](.+?)["\']',
            r'SYSTEM_PROMPT\s*=\s*"""(.+?)"""',
        ],
        "python": [
            r'system_prompt\s*=\s*["\'](.+?)["\']',
            r'system_prompt\s*=\s*"""(.+?)"""',
            r'SYSTEM_PROMPT\s*=\s*["\'](.+?)["\']',
        ],
        "json": [
            r'"role"\s*:\s*"system"\s*,\s*"content"\s*:\s*"(.+?)"',
        ],
    }
    for file_path in _iter_source_files(base_path):
        try:
            content = file_path.read_text(errors="ignore")
            for source, pats in patterns.items():
                for pat in pats:
                    match = re.search(pat, content, re.DOTALL | re.IGNORECASE)
                    if match:
                        raw = match.group(1)[:1024]
                        # NEVER log content — only log that one was found
                        logger.info(
                            "system_prompt found in %s (source: %s, length: %d)",
                            file_path.name, source, len(raw),
                        )
                        return raw, source
        except Exception:
            continue
    return None, None
