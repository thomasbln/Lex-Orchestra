"""ADR-129 re-audit B-1 — language-pure owner texts (PR N1).

The doctrine under test:
1. A custom measure authored in one language appears in the OTHER language's TOM
   as title + translation-pending marker — never the other-language text, never a
   silent drop (the empty-concrete filter must not eat the row).
2. The marker is render-only (resolved in inline_gap_marker BEFORE the registry
   lookup, localised) — nothing is ever stored for the missing language.
3. The measures-API edit action upserts language-pure: writing the first text of
   a language creates that language's row from the sibling row's identity —
   default_text stays NULL, the sibling's text is never copied.
4. Graph controls keep the K20/F1 behaviour: no owner edit in the render lang →
   graph default of the render lang (no marker; rule 6 narrows rule 4 to customs).

No DB required — loader tests mock psycopg2, builder tests inject synthetic
control dicts, API tests mock the connection (same style as test_measures_api).
"""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from jinja2 import Environment, FileSystemLoader

import src.interface.approve_api as api
from src.documents.builders.common.owner_measures import load_custom_measures
from src.documents.builders.tom_builder import TOMBuilder
from src.documents.content_models import BuildContext

client = TestClient(api.app, raise_server_exceptions=False)

RUN = "00000000-0000-0000-0000-000000000001"
CTX = BuildContext(run_id="test00001", generation_date="2026-07-12", project_name="test")

DE_MARKER = "☐ Übersetzung ausstehend (englische Fassung vorhanden)"
EN_MARKER = "☐ translation pending (German version exists)"


# ---------------------------------------------------------------------------
# Loader: cross-lang grouping + translation_pending
# ---------------------------------------------------------------------------

def _mock_conn(rows):
    cur = MagicMock()
    cur.fetchall.return_value = rows
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cur


def test_loader_de_only_custom_is_pending_in_en():
    rows = [("custom-abc12345", "de", "Custom", "Notfallplan", "Wöchentliche Backups")]
    conn, _ = _mock_conn(rows)
    with patch.dict("os.environ", {"MCP_SUPABASE_URL": "postgresql://x"}), \
         patch("psycopg2.connect", return_value=conn):
        out = load_custom_measures("test", RUN, "en")
    assert len(out) == 1
    c = out[0]
    assert c["translation_pending"] is True
    assert c["text"] == ""                      # never the DE text
    assert c["default_tom_measure"] == ""
    assert c["title_de"] == "Notfallplan"       # title fallback: row stays identifiable


def test_loader_active_lang_text_wins_no_pending():
    rows = [
        ("custom-abc12345", "de", "Custom", "Notfallplan", "Wöchentliche Backups"),
        ("custom-abc12345", "en", "Custom", "Contingency plan", "Weekly backups"),
    ]
    conn, _ = _mock_conn(rows)
    with patch.dict("os.environ", {"MCP_SUPABASE_URL": "postgresql://x"}), \
         patch("psycopg2.connect", return_value=conn):
        out = load_custom_measures("test", RUN, "en")
    assert len(out) == 1
    assert out[0]["translation_pending"] is False
    assert out[0]["text"] == "Weekly backups"
    assert out[0]["title_en"] == "Contingency plan"


def test_loader_symmetric_en_only_custom_pending_in_de():
    rows = [("custom-def67890", "en", "Custom", "Key rotation", "Rotate secrets quarterly")]
    conn, _ = _mock_conn(rows)
    with patch.dict("os.environ", {"MCP_SUPABASE_URL": "postgresql://x"}), \
         patch("psycopg2.connect", return_value=conn):
        out = load_custom_measures("test", RUN, "de")
    assert out[0]["translation_pending"] is True
    assert out[0]["text"] == ""
    assert out[0]["title_de"] == "Key rotation"


# ---------------------------------------------------------------------------
# Builder: pending row survives the empty-concrete filter; graph controls don't flag
# ---------------------------------------------------------------------------

def _build_with_pending_custom(lang):
    graph = {"controls": [
        {"control_id": "LLM01", "framework": "OWASP_LLM_Top10", "title_de": "Prompt Injection",
         "title_en": "Prompt Injection", "default_tom_measure": "Input-Validierung",
         "default_tom_measure_en": "Input validation"},
    ]}
    pending_custom = {
        "control_id": "custom-abc12345", "framework": "Custom",
        "title_de": "Notfallplan", "title_en": "Notfallplan",
        "text": "", "default_tom_measure": "",
        "translation_pending": True, "service": "—",
    }
    with patch("src.documents.builders.common.owner_measures.load_custom_measures",
               return_value=[pending_custom]), \
         patch("src.documents.builders.common.owner_measures.load_owner_measures",
               return_value=({}, set())):
        return TOMBuilder().build(graph, {}, {"doc_language": lang}, [], CTX)


def test_builder_pending_custom_survives_empty_filter():
    model = _build_with_pending_custom("en")
    customs = [r for r in model.curated_controls if r.measure == "Notfallplan"]
    assert len(customs) == 1, "translation-pending custom must not be dropped"
    assert customs[0].translation_pending is True
    assert customs[0].concrete == ""


def test_builder_graph_control_falls_to_lang_default_no_flag():
    model = _build_with_pending_custom("en")
    llm = [r for r in model.curated_controls if "LLM01" in r.measure]
    assert len(llm) == 1
    assert llm[0].translation_pending is False       # rule 6: graph default, no marker
    assert llm[0].concrete == "Input validation"


def test_builder_deactivated_pending_custom_stays_gone():
    """Rule 5: deactivation is language-agnostic — it beats translation-pending."""
    graph = {"controls": []}
    pending_custom = {
        "control_id": "custom-abc12345", "framework": "Custom",
        "title_de": "Notfallplan", "title_en": "Notfallplan",
        "text": "", "default_tom_measure": "",
        "translation_pending": True, "service": "—",
    }
    with patch("src.documents.builders.common.owner_measures.load_custom_measures",
               return_value=[pending_custom]), \
         patch("src.documents.builders.common.owner_measures.load_owner_measures",
               return_value=({}, {"custom-abc12345"})):
        model = TOMBuilder().build(graph, {}, {"doc_language": "en"}, [], CTX)
    assert all(r.measure != "Notfallplan" for r in model.curated_controls)


# ---------------------------------------------------------------------------
# Marker: render-only, localised, resolved before the registry
# ---------------------------------------------------------------------------

def test_inline_gap_marker_translation_pending_localised():
    from src.agents.document_architect import DocumentOrchestrator
    da = DocumentOrchestrator.__new__(DocumentOrchestrator)   # no __init__: pure method test
    da._gap_registry = {}
    da._current_lang = "de"
    assert da.inline_gap_marker("translation_pending") == DE_MARKER
    da._current_lang = "en"
    assert da.inline_gap_marker("translation_pending") == EN_MARKER


def test_template_renders_marker_not_empty_cell():
    """The real de/en TOM row: flagged row → localised marker in the concrete cell."""
    from pathlib import Path
    from src.agents.document_architect import DocumentOrchestrator
    templates = Path("src/templates")
    for lang, marker in (("de", DE_MARKER), ("en", EN_MARKER)):
        da = DocumentOrchestrator.__new__(DocumentOrchestrator)
        da._gap_registry = {}
        da._current_lang = lang
        env = Environment(
            loader=FileSystemLoader([str(templates / lang), str(templates)]),
            autoescape=False, trim_blocks=True, lstrip_blocks=True,
        )
        env.globals["has_signal"] = lambda name, min_confidence=0.5: False
        env.globals["inline_gap_marker"] = da.inline_gap_marker
        model = _build_with_pending_custom(lang)
        # render only the curated-controls loop line, with the real row objects
        row_tpl = env.from_string(
            "{% for ctrl in model.curated_controls %}"
            "| {{ ctrl.measure }} | {{ inline_gap_marker('translation_pending') "
            "if ctrl.translation_pending else ctrl.concrete }} |\n{% endfor %}"
        )
        out = row_tpl.render(model=model)
        assert f"| Notfallplan | {marker} |" in out
        assert "| Notfallplan |  |" not in out


# ---------------------------------------------------------------------------
# API: language-pure edit upsert
# ---------------------------------------------------------------------------

def _api_conn(update_rowcounts):
    """Mock connection whose cursor yields the given rowcounts per execute."""
    cur = MagicMock()
    cur.fetchone.return_value = ("test-project",)
    rowcounts = iter(update_rowcounts)
    executed = []

    def _execute(sql, params=None):
        executed.append((" ".join(sql.split()), params))
        try:
            cur.rowcount = next(rowcounts)
        except StopIteration:
            cur.rowcount = 0
    cur.execute.side_effect = _execute
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, executed


def test_edit_missing_lang_row_upserts_from_sibling():
    # execute sequence: SELECT project (rowcount irrelevant), UPDATE → 0, INSERT..SELECT → 1
    conn, executed = _api_conn([1, 0, 1])
    with patch.object(api, "DB_URL", "postgresql://x"), \
         patch.object(api, "_get_project_id_by_name", return_value="pid"), \
         patch("psycopg2.connect", return_value=conn):
        r = client.post(f"/scan/{RUN}/measures", json={
            "action": "edit", "control_id": "custom-abc12345",
            "lang": "en", "text": "Weekly backups",
        })
    assert r.status_code == 200
    assert r.json()["updated"] == 1
    sqls = [s for s, _ in executed]
    assert any(s.startswith("INSERT INTO owner_measures") and "SELECT" in s for s in sqls), \
        "missing-lang edit must create the row from the sibling"
    insert_sql = next(s for s in sqls if s.startswith("INSERT INTO owner_measures"))
    assert "default_text" not in insert_sql, "no snapshot copy — default_text stays NULL"


def test_edit_existing_row_updates_no_insert():
    conn, executed = _api_conn([1, 1])   # SELECT, UPDATE → 1
    with patch.object(api, "DB_URL", "postgresql://x"), \
         patch.object(api, "_get_project_id_by_name", return_value="pid"), \
         patch("psycopg2.connect", return_value=conn):
        r = client.post(f"/scan/{RUN}/measures", json={
            "action": "edit", "control_id": "ORP.4", "lang": "de", "text": "Neu",
        })
    assert r.status_code == 200
    assert r.json()["updated"] == 1
    assert not any(s.startswith("INSERT INTO owner_measures") for s, _ in executed)


def test_edit_unknown_control_stays_updated_zero():
    conn, _ = _api_conn([1, 0, 0])   # SELECT, UPDATE → 0, INSERT..SELECT matches nothing → 0
    with patch.object(api, "DB_URL", "postgresql://x"), \
         patch.object(api, "_get_project_id_by_name", return_value="pid"), \
         patch("psycopg2.connect", return_value=conn):
        r = client.post(f"/scan/{RUN}/measures", json={
            "action": "edit", "control_id": "GHOST-1", "lang": "en", "text": "x",
        })
    assert r.status_code == 200
    assert r.json()["updated"] == 0, "unknown control_id must stay an honest no-op"
