"""ADR-127 — render-safe text for Markdown table cells.

A Markdown table row must live on a single line; a literal newline inside a cell
splits the row (the part after the newline becomes a new table row), and a literal
pipe shifts the columns (the cell content bleeds into the next column). Owner-authored
measure text and titles may contain both, so convert them at the RENDER layer — the
stored DB text stays raw. Newlines become <br> (WeasyPrint renders the break inside
the cell), pipes are backslash-escaped. No other HTML manipulation.
"""
from __future__ import annotations


def cell_text(s: str | None) -> str:
    """Markdown-table-cell safety: | → \\| and newline → <br>. None/empty → ''.

    Pipe escape runs BEFORE the newline conversion — the inserted <br> tag
    contains no pipe, so the order keeps the two replacements independent.
    Call exactly once per flow (double application would escape the backslash).
    """
    return ((s or "").replace("\r\n", "\n")
            .replace("|", "\\|")
            .replace("\n", "<br>"))
