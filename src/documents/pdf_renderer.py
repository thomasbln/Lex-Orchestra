"""Markdown → HTML → PDF rendering via WeasyPrint.

Pre-DSB sprint Schritt 2. Renders the generated compliance drafts to print-ready
A4 PDF. Engine choice (WeasyPrint over pandoc/xelatex) validated by probe render:
tables, page-breaks, German umlauts, colour emoji (🔴 ✅ ⚠️) and the ≈ inferred
marker all render correctly.

Imports are lazy so the module loads (and tests run) on machines without
WeasyPrint's native libs installed; render_md_to_pdf then returns None and logs
a warning rather than raising — a missing PDF never breaks document generation.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Stylesheet lives next to this module so it is volume-mounted with src/ and can
# be tuned without an image rebuild.
DEFAULT_CSS = Path(__file__).parent / "styles" / "lex-doc.css"

_MD_EXTENSIONS = ["tables", "fenced_code", "sane_lists", "nl2br"]


def render_md_to_pdf(
    md_path: Path | str,
    output_path: Path | str | None = None,
    css_path: Path | str | None = None,
) -> Path | None:
    """Render a Markdown file to PDF. Returns the PDF path, or None on failure.

    output_path defaults to md_path with a .pdf suffix.
    css_path defaults to styles/lex-doc.css.
    """
    md_path = Path(md_path)
    out_path = Path(output_path) if output_path else md_path.with_suffix(".pdf")
    css = Path(css_path) if css_path else DEFAULT_CSS

    try:
        import markdown
        from weasyprint import CSS, HTML
    except Exception as exc:  # ImportError or missing native libs
        logger.warning("PDF rendering unavailable (WeasyPrint/markdown import failed): %s", exc)
        return None

    try:
        text = md_path.read_text(encoding="utf-8")
        body = markdown.markdown(text, extensions=_MD_EXTENSIONS)
        html_doc = (
            '<!DOCTYPE html><html lang="de"><head>'
            '<meta charset="utf-8"></head><body>'
            f"{body}</body></html>"
        )
        stylesheets = [CSS(filename=str(css))] if css.exists() else []
        HTML(string=html_doc, base_url=str(md_path.parent)).write_pdf(
            str(out_path), stylesheets=stylesheets
        )
        return out_path
    except Exception as exc:
        logger.warning("PDF rendering failed for %s: %s", md_path.name, exc)
        return None
