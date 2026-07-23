"""ADR-106 PR 0 Encoding Regression Guard
=========================================
The pasted scan `2168ece0` from 2026-05-28 showed `Ãnderung` (UTF-8-as-Latin1
double-encoding) and `ï»¿` (UTF-8 BOM displayed as Latin-1). Investigation
showed all 944 then-existing draft files were actually clean UTF-8 with no
BOM, so the original symptom was downstream (Telegram delivery / IDE
display) rather than pipeline-internal.

This test locks in the discipline: ALL files in `legal/drafts/` must be
clean UTF-8 without BOM, and templates in `src/templates/` must be the same.
Catches any future regression where someone changes Jinja2 config, template
encoding, or file-writer behavior.

Skipped when legal/drafts/ has no files (e.g., fresh clone, CI without scans).
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DRAFTS_DIR = REPO_ROOT / "legal" / "drafts"
TEMPLATES_DIR = REPO_ROOT / "src" / "templates"

UTF8_BOM = b"\xef\xbb\xbf"

# Markers that indicate UTF-8 was decoded as Latin-1 and re-encoded:
# "Ã¤" = "ä" (0xC3 0xA4) read as Latin-1 + re-encoded
# "ï»¿" = BOM (0xEF 0xBB 0xBF) read as Latin-1
DOUBLE_ENCODE_MARKERS = ["Ã¤", "Ã¶", "Ã¼", "ÃŸ", "Ã„", "Ã–", "Ãœ", "â€"]


def _check_file(path: Path) -> list[str]:
    """Return list of issues found in the file."""
    issues = []
    raw = path.read_bytes()
    if raw.startswith(UTF8_BOM):
        issues.append("starts with UTF-8 BOM")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        issues.append(f"not valid UTF-8: {e}")
        return issues
    for marker in DOUBLE_ENCODE_MARKERS:
        if marker in text:
            issues.append(f"contains double-encoded marker {marker!r}")
            break
    return issues


def test_all_jinja_templates_are_clean_utf8():
    """Every src/templates/*.j2 must be clean UTF-8 without BOM or double-encoding."""
    templates = sorted(TEMPLATES_DIR.glob("*.j2"))
    assert templates, "no Jinja templates found — repo structure changed?"
    failures = []
    for tpl in templates:
        issues = _check_file(tpl)
        if issues:
            failures.append(f"{tpl.name}: {', '.join(issues)}")
    assert not failures, "Template encoding issues:\n  " + "\n  ".join(failures)


def test_all_drafts_are_clean_utf8():
    """Every legal/drafts/*.md (if any) must be clean UTF-8 without BOM or double-encoding."""
    if not DRAFTS_DIR.exists():
        pytest.skip(f"{DRAFTS_DIR} does not exist (fresh clone, no scans run yet)")
    drafts = sorted(DRAFTS_DIR.glob("*.md"))
    if not drafts:
        pytest.skip(f"{DRAFTS_DIR} is empty (no scans run yet)")
    failures = []
    for draft in drafts:
        issues = _check_file(draft)
        if issues:
            failures.append(f"{draft.name}: {', '.join(issues)}")
    assert not failures, f"Draft encoding issues in {len(failures)}/{len(drafts)} files:\n  " + "\n  ".join(failures[:20])


def test_document_architect_writes_utf8_explicitly():
    """Grep-style assertion: document_architect.py must use encoding='utf-8' on every write."""
    arch = REPO_ROOT / "src" / "agents" / "document_architect.py"
    if not arch.exists():
        pytest.skip(f"{arch} not found")
    text = arch.read_text(encoding="utf-8")
    write_calls = [line for line in text.splitlines() if ".write_text(" in line]
    bare_writes = [line for line in write_calls if "encoding=" not in line]
    assert not bare_writes, (
        f"document_architect.py has {len(bare_writes)} write_text() calls without "
        f"explicit encoding=: \n  " + "\n  ".join(bare_writes[:5])
    )
