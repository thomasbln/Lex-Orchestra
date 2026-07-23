import dataclasses
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.documents.builders.tom_builder import (
    TOMBuilder,
    TOMContentModel,
    TOMControlRow,
    TOMSectionRow,
    _get_tom_section,
)
from src.documents.content_models import BuildContext
from src.scanner.gap_analyzer import GapHint
from tests.golden._helpers import _load_fixture, _load_golden

CTX = BuildContext(run_id="test00001", generation_date="2026-04-20", project_name="test")


# ---------------------------------------------------------------------------
# _get_tom_section unit tests
# ---------------------------------------------------------------------------

def test_get_tom_section_owasp_llm():
    ctrl = {"control_id": "LLM01", "framework": "OWASP_LLM_Top10"}
    assert _get_tom_section(ctrl) == "4.1 Datenschutz-Maßnahmen"


def test_get_tom_section_iso_access():
    ctrl = {"control_id": "8.3", "framework": "ISO_27001"}
    assert _get_tom_section(ctrl) == "1.3 Zugriffskontrolle"


def test_get_tom_section_bsi_prefix():
    ctrl = {"control_id": "DER.2.1", "framework": "BSI_Grundschutz"}
    assert _get_tom_section(ctrl) == "4.2 Incident-Response-Management"


# ---------------------------------------------------------------------------
# TOMBuilder unit tests
# ---------------------------------------------------------------------------

def test_tom_builder_filters_empty_concrete():
    graph = {"controls": [
        {"control_id": "8.3", "framework": "ISO_27001", "title_de": "Endpoint", "default_tom_measure": "Impl A"},
        {"control_id": "8.4", "framework": "ISO_27001", "title_de": "Empty", "default_tom_measure": None},
        {"control_id": "8.5", "framework": "ISO_27001", "title_de": "Also empty", "default_tom_measure": ""},
    ]}
    model = TOMBuilder().build(graph, {}, {}, [], CTX)
    assert len(model.curated_controls) == 1
    assert model.curated_controls[0].concrete == "Impl A"


def test_tom_builder_framework_label_set_correctly():
    graph = {"controls": [
        {"control_id": "LLM01", "framework": "OWASP_LLM_Top10", "title_de": "Prompt Injection",
         "default_tom_measure": "Input validation"},
    ]}
    model = TOMBuilder().build(graph, {}, {}, [], CTX)
    assert model.curated_controls[0].framework_label == "OWASP LLM Top 10"


def test_tom_builder_sections_overview_ordering():
    graph = {"controls": [
        {"control_id": "LLM01", "framework": "OWASP_LLM_Top10", "title_de": "A", "default_tom_measure": "x"},
        {"control_id": "8.3", "framework": "ISO_27001", "title_de": "B", "default_tom_measure": "y"},
    ]}
    model = TOMBuilder().build(graph, {}, {}, [], CTX)
    sections = [r.section for r in model.sections_overview]
    # ISO 8.3 → Zugriffskontrolle (1.3), LLM01 → Datenschutz-Maßnahmen (4.1)
    assert sections.index("1.3 Zugriffskontrolle") < sections.index("4.1 Datenschutz-Maßnahmen")


def test_tom_builder_risk_flags_pii_in_llm():
    graph = {"active_risks": ["PII_IN_LLM_CONTEXT"]}
    model = TOMBuilder().build(graph, {}, {}, [], CTX)
    assert model.pii_in_llm_risk is True
    assert model.rag_over_pii_risk is False
    assert model.pii_in_logs_risk is False


def test_tom_builder_risk_flags_rag_over_pii():
    graph = {"active_risks": ["RAG_OVER_PII", "PII_IN_LOGS"]}
    model = TOMBuilder().build(graph, {}, {}, [], CTX)
    assert model.rag_over_pii_risk is True
    assert model.pii_in_logs_risk is True
    assert model.pii_in_llm_risk is False


def test_tom_builder_warn_header_only_required_gaps():
    gaps = [
        GapHint(id="a", severity="REQUIRED", doc_affected=["TOM"], article="Art. 32",
                gap_reason="", fix_url="", fix_label="", priority=1, affected_docs=[]),
        GapHint(id="b", severity="RECOMMENDED", doc_affected=["TOM"], article="Art. 32",
                gap_reason="", fix_url="", fix_label="", priority=2, affected_docs=[]),
    ]
    model = TOMBuilder().build({}, {}, {}, gaps, CTX)
    assert len(model.warn_header_gaps) == 1
    assert model.warn_header_gaps[0].id == "a"


def test_tom_builder_bsi_defaults_graceful_on_graphclient_failure():
    graph = {"controls": [
        {"control_id": "OPS.1.1", "framework": "BSI_Grundschutz", "title_de": "IT-Admin",
         "default_tom_measure": "Service accounts mit minimalen Rechten"},
    ]}
    with patch("src.documents.builders.tom_builder.TOMBuilder._load_bsi_defaults", return_value={}):
        model = TOMBuilder().build(graph, {}, {}, [], CTX)
    assert len(model.curated_controls) == 1
    assert model.curated_controls[0].bsi_default == ""   # empty, not an exception


def test_tom_builder_hosting_delegation_passthrough():
    hd = {"value": {"provider": "Hetzner", "region": "DE"}, "source": "STD_DELEGATED"}
    model = TOMBuilder().build({}, {}, {}, [], CTX, hosting_delegation=hd)
    assert model.hosting_delegation == hd


def test_tom_builder_returns_tom_content_model():
    model = TOMBuilder().build({}, {}, {}, [], CTX)
    assert isinstance(model, TOMContentModel)


# ---------------------------------------------------------------------------
# Golden-file test
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Regression tests
# ---------------------------------------------------------------------------

def test_tom_no_validation_message_in_controls_column():
    """1.1 Zutrittskontrolle table row must render '—', not the validation message (Fix I regression).

    The string 'Hosting-Provider nicht konfiguriert' may only appear in the warn-header
    (injected from gap hints), never hardcoded in a table cell.
    """
    from pathlib import Path
    template_path = Path(__file__).parent.parent / "src" / "templates" / "de" / "tom.md.j2"
    source = template_path.read_text()
    assert "Hosting-Provider nicht konfiguriert" not in source, (
        "Validation message must not be hardcoded in tom.md.j2 — use '—' in the else branch. "
        "The message may only appear via warn-header gap hints."
    )


def test_tom_content_model_matches_golden():
    graph = _load_fixture("rand_industries_graph.json")
    config = _load_fixture("rand_industries_config.json")
    reasoning = _load_fixture("rand_industries_reasoning.json")
    gaps_raw = _load_fixture("rand_industries_gaps.json")
    gap_hints = [GapHint(**g) for g in gaps_raw]

    ctx = BuildContext(run_id="0158d042", generation_date="2026-04-20",
                       project_name="rand-industries")

    with patch("src.documents.builders.tom_builder.TOMBuilder._load_bsi_defaults", return_value={}):
        model = TOMBuilder().build(graph, reasoning, config, gap_hints, ctx)

    expected = _load_golden("rand_industries_tom_content_model.json")
    assert dataclasses.asdict(model) == expected


# ---------------------------------------------------------------------------
# ADR-129 PR 1 — owner-editable titles are render-escaped (audit B3)
# ---------------------------------------------------------------------------

def test_tom_builder_escapes_pipe_and_newline_in_title():
    """A custom measure title with newline/pipe must not split the table row."""
    graph = {"controls": [{
        "control_id": "custom-abc12345", "framework": "Custom",
        "title_de": "foo\nbar|baz", "title_en": "foo\nbar|baz",
        "default_tom_measure": "Eigene Umsetzung.", "service": "—",
    }]}
    model = TOMBuilder().build(graph, {}, {}, [], CTX)
    rows = [r for r in model.curated_controls if "custom-abc12345" in r.measure or "foo" in r.measure]
    assert len(rows) == 1
    m = rows[0].measure
    assert "\n" not in m                 # one Markdown line — row cannot split
    assert "<br>" in m                   # newline converted, not dropped
    assert "\\|" in m and "bar|baz" not in m   # pipe escaped — columns intact


# ---------------------------------------------------------------------------
# ADR-129 PR 9 — EN renders default_tom_measure_en with DE fallback (F1)
# ---------------------------------------------------------------------------

def test_tom_builder_en_uses_en_measure_with_de_fallback():
    graph = {"controls": [
        {"control_id": "LLM01", "framework": "OWASP_LLM_Top10", "title_de": "T", "title_en": "T",
         "default_tom_measure": "DE-Text", "default_tom_measure_en": "EN text"},
        {"control_id": "LLM02", "framework": "OWASP_LLM_Top10", "title_de": "T2", "title_en": "T2",
         "default_tom_measure": "Nur DE"},
    ]}
    model = TOMBuilder().build(graph, {}, {"doc_language": "en"}, [], CTX)
    concrete = {r.measure.split(" — ")[0]: r.concrete for r in model.curated_controls}
    assert concrete["LLM01"] == "EN text"
    assert concrete["LLM02"] == "Nur DE"     # honest fallback, not an empty cell


def test_tom_builder_de_ignores_en_measure():
    graph = {"controls": [
        {"control_id": "LLM01", "framework": "OWASP_LLM_Top10", "title_de": "T", "title_en": "T",
         "default_tom_measure": "DE-Text", "default_tom_measure_en": "EN text"},
    ]}
    model = TOMBuilder().build(graph, {}, {}, [], CTX)
    assert model.curated_controls[0].concrete == "DE-Text"
