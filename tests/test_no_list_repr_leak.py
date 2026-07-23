"""ADR-106 PR C.1 Cleanup — Regression Guard against Python list-repr leaks.

Bug observed in scan 9e547a82: VVT rendered MongoDB.data_categories as
`['Anwendungsdaten', 'Datenbankinhalt', 'Logs']` — raw Python list repr
in a Markdown table cell because the value was list[str] and the template
did `{{ value }}` without join.

This test scans all `legal/drafts/*.md` files for table cells (lines
matching `| ... | <X> |` pattern) and asserts no cell contains a
Python-list-repr signature (`['...'` or `["..."`).

Skipped when no drafts exist (fresh clone, no scans run).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DRAFTS_DIR = REPO_ROOT / "legal" / "drafts"

# Pattern: inside any pipe-delimited Markdown table row, a Python list literal start
LIST_REPR_PATTERNS = [
    re.compile(r"\|\s*\[\s*['\"]"),       # `| ['Foo` or `| ["Foo`
    re.compile(r"\|\s*\(\s*['\"]"),       # `| ('Foo` — tuple repr (rarer)
]


def test_drafts_have_no_list_repr_in_table_cells():
    """Catch list[str] → __repr__ leaks like `['Anwendungsdaten', ...]`."""
    if not DRAFTS_DIR.exists():
        pytest.skip(f"{DRAFTS_DIR} does not exist")
    drafts = sorted(DRAFTS_DIR.glob("*.md"))
    if not drafts:
        pytest.skip("no drafts to check")

    failures: list[str] = []
    for draft in drafts:
        text = draft.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if "|" not in line:
                continue  # not a table row
            for pat in LIST_REPR_PATTERNS:
                if pat.search(line):
                    failures.append(f"{draft.name}:{lineno}: {line.strip()[:120]}")
                    break

    assert not failures, (
        f"Found {len(failures)} table cells with Python-list-repr leak. "
        f"Builder fields holding list[str] must be joined to a string before "
        f"rendering as a single-cell value.\n  " + "\n  ".join(failures[:10])
    )
