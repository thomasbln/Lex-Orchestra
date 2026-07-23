"""Pre-DSB sprint Schritt 2 — Markdown→PDF renderer.

The graceful-failure tests run everywhere. The real-render tests need
WeasyPrint's native libs (Pango/Cairo) which are baked into the lex-agent
image but usually absent on a dev Mac — they skip there, run in the container.
"""
import builtins

import pytest

from src.documents.pdf_renderer import render_md_to_pdf


def _has_weasyprint() -> bool:
    try:
        import weasyprint  # noqa: F401
        return True
    except Exception:
        return False


needs_weasyprint = pytest.mark.skipif(
    not _has_weasyprint(), reason="WeasyPrint native libs not installed (runs in container)"
)


# ── graceful failure (environment-independent) ───────────────────────────────

def test_returns_none_when_weasyprint_unavailable(tmp_path, monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "weasyprint":
            raise ImportError("simulated missing weasyprint")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    md = tmp_path / "doc.md"
    md.write_text("# Test\n\nHallo Welt", encoding="utf-8")
    assert render_md_to_pdf(md) is None


def test_returns_none_on_missing_source_file(tmp_path):
    # Never raises, even if the markdown file does not exist.
    assert render_md_to_pdf(tmp_path / "does_not_exist.md") is None


# ── real rendering (container only) ──────────────────────────────────────────

@needs_weasyprint
def test_renders_pdf_default_output_path(tmp_path):
    md = tmp_path / "doc.md"
    md.write_text("# Titel\n\nEin Absatz.", encoding="utf-8")
    out = render_md_to_pdf(md)
    assert out is not None and out.exists()
    assert out.suffix == ".pdf"
    assert out.read_bytes()[:5] == b"%PDF-"


@needs_weasyprint
def test_renders_umlauts_tables_and_emoji(tmp_path):
    md = tmp_path / "doc.md"
    md.write_text(
        "# Verhältnismäßigkeit\n\n"
        "| Feld | Inhalt |\n|---|---|\n"
        "| Maßnahme | ✅ umgesetzt |\n"
        "| Zweck | ≈ aus Kategorie abgeleitet |\n\n"
        "🔴 Pflichtangabe fehlt — Geschäftsführer eintragen.\n",
        encoding="utf-8",
    )
    out = render_md_to_pdf(md)
    assert out is not None and out.exists()
    assert out.stat().st_size > 1000  # a real rendered page, not an empty stub


@needs_weasyprint
def test_explicit_output_path_is_honoured(tmp_path):
    md = tmp_path / "doc.md"
    md.write_text("# X\n\nY", encoding="utf-8")
    target = tmp_path / "custom" / "out.pdf"
    target.parent.mkdir()
    out = render_md_to_pdf(md, output_path=target)
    assert out == target and target.exists()
