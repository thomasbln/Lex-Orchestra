"""ADR-129 PR 1 — cell_text render-layer escaping (audit B3/K7)."""
from src.documents.builders.common.cell_safe import cell_text


def test_cell_text_escapes_pipe_and_newline():
    assert cell_text("foo\nbar|baz") == "foo<br>bar\\|baz"


def test_cell_text_none_and_empty():
    assert cell_text(None) == ""
    assert cell_text("") == ""


def test_cell_text_crlf_normalised():
    assert cell_text("a\r\nb") == "a<br>b"


def test_cell_text_pipe_only():
    assert cell_text("a|b") == "a\\|b"


def test_cell_text_plain_text_untouched():
    assert cell_text("Verschlüsselung at rest (AES-256).") == "Verschlüsselung at rest (AES-256)."
