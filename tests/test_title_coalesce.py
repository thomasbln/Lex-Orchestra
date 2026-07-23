"""ADR-117 PR 3 — lang-aware title coalesce (DB-free unit tests).

Verifies the title fallback chain + alias parameter without touching Neo4j.
"""
from src.graph.graph_client import TITLE_FALLBACK, _title_coalesce


def test_de_chain_is_title_de_only():
    # DE resolves to title_de (present on every control) -> byte-identical to the old
    # coalesce(c.title_de, ...) for DE output. title_en is NOT in the DE chain.
    assert TITLE_FALLBACK["de"] == ["title_de"]
    assert _title_coalesce("de", "c") == "coalesce(c.title_de, '')"


def test_en_chain_prefers_title_en_then_falls_back_to_de():
    # EN pulls title_en first; gap/empty EN falls back to title_de (documented
    # intermediate state until ADR-079 fills EN). Never null (trailing '').
    assert TITLE_FALLBACK["en"] == ["title_en", "title_de"]
    assert _title_coalesce("en", "c") == "coalesce(c.title_en, c.title_de, '')"


def test_alias_parameter_targets_the_query_node_variable():
    # Q_CONTROLS uses (c:Control) -> the coalesce must reference c., not the default n.
    assert _title_coalesce("en", "c").startswith("coalesce(c.title_en")
    assert _title_coalesce("en") == "coalesce(n.title_en, n.title_de, '')"


def test_no_legacy_title_property_in_any_chain():
    # The legacy `title` (c.title) is retired (PR 4) and must not appear anywhere —
    # it is null for ISO/NIST/Grundschutz and would yield empty titles.
    for lang, chain in TITLE_FALLBACK.items():
        assert "title" not in chain, f"{lang} chain still references legacy 'title'"


def test_unknown_lang_falls_back_to_title_de():
    assert _title_coalesce("xx", "c") == "coalesce(c.title_de, '')"
