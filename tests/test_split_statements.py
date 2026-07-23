"""Unit tests for _split_statements() in scripts/seed_both.py."""

from scripts.seed_both import _split_statements


def test_single_statement_no_semicolon():
    cypher = "MATCH (n) RETURN n"
    assert _split_statements(cypher) == ["MATCH (n) RETURN n"]


def test_inline_semicolon_at_end_of_line():
    cypher = "MATCH (a) SET a.x = 1;\nMATCH (b) SET b.x = 2;"
    stmts = _split_statements(cypher)
    assert len(stmts) == 2
    assert stmts[0] == "MATCH (a) SET a.x = 1"
    assert stmts[1] == "MATCH (b) SET b.x = 2"


def test_semicolon_on_own_line():
    cypher = "MATCH (a) SET a.x = 1\n;\nMATCH (b) SET b.x = 2\n;"
    stmts = _split_statements(cypher)
    assert len(stmts) == 2


def test_semicolon_inside_string_literal_preserved():
    cypher = 'MATCH (l) SET l.note_de = "Anwendungsbereich; Grundsatz";\nMATCH (m) SET m.x = 1;'
    stmts = _split_statements(cypher)
    assert len(stmts) == 2
    assert "Anwendungsbereich; Grundsatz" in stmts[0]


def test_comment_only_blocks_skipped():
    cypher = "// Section A\nMATCH (a) RETURN a;\n// orphan comment\n"
    stmts = _split_statements(cypher)
    assert len(stmts) == 1
    assert "MATCH (a)" in stmts[0]


def test_blank_blocks_skipped():
    cypher = "MATCH (a) RETURN a;\n\n   \n\nMATCH (b) RETURN b;"
    stmts = _split_statements(cypher)
    assert len(stmts) == 2


def test_12_legal_basis_backfill_count():
    import pathlib
    text = pathlib.Path(
        "src/graph/layers/10_jurisdiction/eu/12_legal_basis_backfill.cypher"
    ).read_text()
    assert len(_split_statements(text)) == 4


def test_14d_cellar_sync_count():
    import pathlib
    text = pathlib.Path(
        "src/graph/layers/10_jurisdiction/eu/14d_law_cellar_sync.cypher"
    ).read_text()
    assert len(_split_statements(text)) == 65
