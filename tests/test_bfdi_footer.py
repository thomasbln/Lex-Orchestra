"""PR G FIX 2 — BfDICitation.excerpt truncates at a sentence boundary, never mid-word."""
from src.documents.builders.common.bfdi_footer import BfDICitation, _EXCERPT_LIMIT


def _cite(value: str) -> BfDICitation:
    return BfDICitation(
        source_section="3.2",
        source_pages="S. 12",
        value=value,
        law_refs=[],
        target_label="AVV (DocumentType)",
    )


def test_short_value_returned_verbatim():
    # Byte-stable: a value within the limit renders unchanged, no ellipsis.
    short = "Kurzer Hinweis zur Auftragsverarbeitung."
    assert _cite(short).excerpt == short


def test_value_at_limit_not_truncated():
    exact = "x" * _EXCERPT_LIMIT
    assert _cite(exact).excerpt == exact


def test_long_value_cut_at_sentence_boundary():
    s1 = "Der Verantwortliche bleibt für die Verarbeitung verantwortlich."
    s2 = "Davon zu trennen ist die Rolle des Auftragsverarbeiters, " + "der " * 120 + "handelt."
    out = _cite(s1 + " " + s2).excerpt
    assert out.endswith("…")
    # Cut at the end of the first full sentence, not mid-word.
    assert out == s1 + "…"


def test_no_sentence_boundary_falls_back_to_word():
    value = "wort " * 100  # 500 chars, no sentence-ending punctuation
    out = _cite(value).excerpt
    assert out.endswith("…")
    assert len(out) <= _EXCERPT_LIMIT + 1  # window + ellipsis
    assert not out[:-1].endswith("wor")    # no mid-word cut
    assert out[:-1].endswith("wort")


def test_never_cuts_mid_word():
    value = "Dies ist ein sehr langer Satz ohne fruehes Satzende " + "lang" * 100
    out = _cite(value).excerpt
    body = out.rstrip("…")
    # The body must not end inside a partial token of the trailing run.
    assert "lang" in body
    assert not body.endswith("la") and not body.endswith("lan")
