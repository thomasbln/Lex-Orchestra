"""ADR-079 PR 1 — render-time control-title resolution.

The scan stores both `title_de` and `title_en` on each control dict; the
render layer picks the language via `resolve_control_title`. These tests pin
the language behaviour the document builders rely on.
"""
from src.graph.graph_client import resolve_control_title


def test_de_picks_title_de():
    c = {"title_de": "Netzsicherheit", "title_en": "Networks security"}
    assert resolve_control_title(c, "de") == "Netzsicherheit"


def test_en_picks_title_en_first():
    c = {"title_de": "Netzsicherheit", "title_en": "Networks security"}
    assert resolve_control_title(c, "en") == "Networks security"


def test_en_falls_back_to_de_when_title_en_empty():
    # The en_null=1 live case: one control has an empty title_en.
    c = {"title_de": "Netzsicherheit", "title_en": ""}
    assert resolve_control_title(c, "en") == "Netzsicherheit"


def test_en_falls_back_to_de_when_title_en_missing():
    c = {"title_de": "Netzsicherheit"}
    assert resolve_control_title(c, "en") == "Netzsicherheit"


def test_default_lang_is_de():
    c = {"title_de": "Netzsicherheit", "title_en": "Networks security"}
    assert resolve_control_title(c) == "Netzsicherheit"


def test_unknown_lang_falls_back_to_de():
    c = {"title_de": "Netzsicherheit", "title_en": "Networks security"}
    assert resolve_control_title(c, "xx") == "Netzsicherheit"


def test_fully_missing_title_is_empty_string_not_none():
    assert resolve_control_title({}, "de") == ""
    assert resolve_control_title({"title_de": "", "title_en": ""}, "en") == ""
