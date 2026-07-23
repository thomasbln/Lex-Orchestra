"""Unit tests for DocumentOrchestrator helpers."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.scanner.gap_analyzer import GapHint


# ── Task 1.7: generate_all() gap_registry wiring ─────────────────────────────

_MINIMAL_GRAPH = {
    "doc_types": ["AVV"],
    "services": [{"name": "Stripe", "dpa_url": "https://stripe.com/dpa"}],
    "controls": [],
    "risk_levels": [],
    "overall_risk": "minimal",
    "active_risks": [],
    "usecase_risks": [],
}


def test_generate_all_populates_gap_registry_before_rendering():
    """_gap_registry must be non-empty before any _write_* method executes."""
    from src.agents.document_architect import DocumentOrchestrator

    arch = DocumentOrchestrator()
    registry_at_write: dict = {}

    def spy_write_avv(*args, **kwargs):
        registry_at_write["avv"] = dict(arch._gap_registry)
        return Path("/tmp/fake_avv.md")

    with patch.object(arch, "_load_project_config", return_value={}), \
         patch.object(arch, "_load_project_setup", return_value=None), \
         patch("src.agents.document_architect.load_retention_policies", return_value=[]), \
         patch.object(arch, "_save_doc", return_value={}), \
         patch.object(arch, "_write_avv", side_effect=spy_write_avv):
        arch.generate_all(
            graph_result=_MINIMAL_GRAPH,
            reasoning_result={},
            project_name="test-project",
            run_id="test-run-id",
        )

    assert registry_at_write.get("avv") is not None, "_write_avv was never called"
    assert len(registry_at_write["avv"]) > 0, (
        f"_gap_registry was empty when _write_avv ran: {registry_at_write}"
    )


def test_gap_registry_matches_scan_report_gaps():
    """After generate_all(), _gap_registry must equal an independent analyze_gaps() call."""
    from src.agents.document_architect import DocumentOrchestrator
    from src.scanner.gap_analyzer import analyze_gaps, load_retention_policies

    arch = DocumentOrchestrator()
    config = {}
    setup = None
    retention: list = []
    extraction = {"extractions_count": 0}
    services = [{"name": "Stripe", "dpa_url": "https://stripe.com/dpa"}]

    graph_result = {**_MINIMAL_GRAPH, "services": services}

    with patch.object(arch, "_load_project_config", return_value=config), \
         patch.object(arch, "_load_project_setup", return_value=setup), \
         patch("src.agents.document_architect.load_retention_policies", return_value=retention), \
         patch.object(arch, "_save_doc", return_value={}), \
         patch.object(arch, "_write_avv", return_value=Path("/tmp/fake_avv.md")):
        arch.generate_all(
            graph_result=graph_result,
            reasoning_result={},
            project_name="test-project",
            run_id="test-run-id",
            extraction_summary=extraction,
        )

    independent_gaps = analyze_gaps(
        project_name="test-project",
        config=config,
        setup=setup,
        retention_policies=retention,
        services_detected=services,
        extraction_summary=extraction,
    )

    assert set(arch._gap_registry.keys()) == {g.id for g in independent_gaps}


def test_has_signal_checks_service_categories():
    """has_signal('ai_llm') must return True when graph_result contains
    service_categories=['ai_llm'], even if risk_signals is empty.

    Fix requires:
    1. get_compliance_requirements() returns 'service_categories' key
    2. generate_all() sets self._current_service_categories from graph_result
    3. _has_signal() checks _current_service_categories as fallback
    """
    from src.agents.document_architect import DocumentOrchestrator

    architect = DocumentOrchestrator()

    graph_result = {
        "doc_types": [],
        "services": [],
        "controls": [],
        "risk_levels": [],
        "overall_risk": "minimal",
        "active_risks": [],
        "usecase_risks": [],
        "service_categories": ["ai_llm", "nosql_db"],
    }

    # Patch DB writes so generate_all() doesn't need a live Supabase
    with patch.object(architect, "_load_project_config", return_value={}), \
         patch.object(architect, "_save_doc", return_value={}):
        architect.generate_all(
            graph_result=graph_result,
            reasoning_result={},
            project_name="test-project",
            run_id="test-run-id",
            risk_signals=[],
        )

    # After generate_all() the Jinja global has_signal should recognise
    # service category names — check via the internal closure directly.
    has_signal = architect._jinja.globals["has_signal"]
    assert has_signal("ai_llm"), "ai_llm is in service_categories but has_signal() returned False"
    assert has_signal("nosql_db"), "nosql_db is in service_categories but has_signal() returned False"
    assert not has_signal("payment_gateway"), "payment_gateway not in categories, must be False"


# ── Task 1.2: inline_gap_marker + _prepend_warn_header ────────────────────────

def test_inline_gap_marker_returns_required_marker():
    """inline_gap_marker() for a REQUIRED gap renders 🔴 marker with article."""
    from src.agents.document_architect import DocumentOrchestrator

    arch = DocumentOrchestrator.__new__(DocumentOrchestrator)
    arch._gap_registry = {
        "avv_instructing_persons_missing": GapHint(
            id="avv_instructing_persons_missing",
            severity="REQUIRED",
            article="DSGVO Art. 28 Abs. 3 Satz 2 lit. a",
            description="Weisungsberechtigte Person",
            fix_url="/project/x/company",
        )
    }
    result = arch.inline_gap_marker("avv_instructing_persons_missing")
    assert "🔴 PFLICHTANGABE FEHLT" in result
    assert "DSGVO Art. 28 Abs. 3 Satz 2 lit. a" in result


def test_inline_gap_marker_unknown_id_returns_fallback():
    """inline_gap_marker() for an unknown gap_id returns a safe fallback string."""
    from src.agents.document_architect import DocumentOrchestrator

    arch = DocumentOrchestrator.__new__(DocumentOrchestrator)
    arch._gap_registry = {}
    result = arch.inline_gap_marker("nonexistent_gap")
    assert "🔴 PFLICHTANGABE FEHLT" in result


def test_warn_header_rendered_when_required_gaps_present():
    """_prepend_warn_header() prepends warn block when REQUIRED gap targets this doc."""
    from src.agents.document_architect import DocumentOrchestrator

    arch = DocumentOrchestrator()
    required_gap = GapHint(
        id="avv_instructing_persons_missing",
        severity="REQUIRED",
        article="DSGVO Art. 28 Abs. 3 Satz 2 lit. a",
        doc_affected=["AVV"],
        description="Weisungsberechtigte Person",
        fix_url="/project/x/company",
    )
    result = arch._prepend_warn_header("AVV", "body content", [required_gap])
    assert "NICHT UNTERSCHRIFTSREIF" in result
    assert "body content" in result
    assert result.index("NICHT UNTERSCHRIFTSREIF") < result.index("body content")


def test_warn_header_not_rendered_for_recommended_only():
    """_prepend_warn_header() returns body unchanged when only RECOMMENDED gaps present."""
    from src.agents.document_architect import DocumentOrchestrator

    arch = DocumentOrchestrator()
    rec_gap = GapHint(
        id="dpo_missing",
        severity="RECOMMENDED",
        doc_affected=["AVV"],
        article="DSGVO Art. 37",
        description="Datenschutzbeauftragter",
        fix_url="/project/x/company",
    )
    result = arch._prepend_warn_header("AVV", "body content", [rec_gap])
    assert "NICHT UNTERSCHRIFTSREIF" not in result
    assert result == "body content"


def test_warn_header_not_rendered_when_required_gap_targets_other_doc():
    """_prepend_warn_header() ignores REQUIRED gaps not in doc_affected for this doc."""
    from src.agents.document_architect import DocumentOrchestrator

    arch = DocumentOrchestrator()
    wrong_doc_gap = GapHint(
        id="hosting_provider_missing",
        severity="REQUIRED",
        doc_affected=["TOM"],
        article="DSGVO Art. 32 Abs. 1",
        description="Hosting Provider",
        fix_url="/project/x/hosting",
    )
    result = arch._prepend_warn_header("AVV", "body content", [wrong_doc_gap])
    assert "NICHT UNTERSCHRIFTSREIF" not in result
    assert result == "body content"


# ── Phase 3: _prepend_warn_header wired into all 8 _write_* methods ──────────

def _make_required_gap(doc_type: str) -> GapHint:
    return GapHint(
        id=f"test_{doc_type.lower()}_required",
        severity="REQUIRED",
        doc_affected=[doc_type],
        article="DSGVO Art. 28",
        description="Test REQUIRED field",
        fix_url=f"/project/test/{doc_type.lower()}",
    )


def _arch_with_gap(gap: GapHint):
    """Return a DocumentOrchestrator.__new__ instance with gap pre-loaded in registry."""
    from src.agents.document_architect import DocumentOrchestrator
    arch = DocumentOrchestrator()
    arch._gap_registry = {gap.id: gap}
    return arch


@pytest.mark.parametrize("doc_type,template,write_method,extra_kwargs", [
    ("AVV",  "avv.md.j2",  "_write_avv",  {}),
    ("TOM",  "tom.md.j2",  "_write_tom",  {}),
    ("VVT",  "vvt.md.j2",  "_write_vvt",  {}),
    ("DSFA", "dsfa.md.j2", "_write_dsfa", {}),
    ("SCC",  "scc.md.j2",  "_write_scc",  {}),
])
def test_write_method_adds_warn_header_when_required_gap_matches(
    doc_type, template, write_method, extra_kwargs, tmp_path
):
    """_write_<doc> must prepend warn header when REQUIRED gap targets that doc_type."""
    from src.agents.document_architect import DocumentOrchestrator

    gap = _make_required_gap(doc_type)
    arch = _arch_with_gap(gap)
    arch.DRAFTS_DIR = tmp_path

    config = {"doc_language": "de"}
    # SCC requires at least one Drittland service (country known + not gdpr_adequate)
    scc_services = [{"name": "OpenAI", "country": "USA", "gdpr_adequate": False, "dpa_url": None}]
    graph_result = {
        "services": scc_services if write_method == "_write_scc" else [],
        "controls": [], "doc_types": [doc_type],
        "active_risks": [], "overall_risk": "minimal", "risk_levels": [],
        "docs_required": [], "usecase_risks": [],
    }

    method = getattr(arch, write_method)
    # Call each write method with its specific signature
    if write_method == "_write_avv":
        path = method("test-project", "testrunid1234", graph_result, config)
    elif write_method == "_write_tom":
        path = method("test-project", "testrunid1234", graph_result, {}, config)
    elif write_method == "_write_vvt":
        path = method("test-project", "testrunid1234", graph_result, config)
    elif write_method == "_write_dsfa":
        path = method("test-project", "testrunid1234", graph_result, [], None, config)
    elif write_method == "_write_scc":
        path = method("test-project", "testrunid1234", graph_result, config)

    content = path.read_text(encoding="utf-8")
    assert "NICHT UNTERSCHRIFTSREIF" in content, (
        f"Warn header missing in {doc_type} output when REQUIRED gap '{gap.id}' present"
    )


def test_write_avv_no_warn_header_when_no_required_gaps(tmp_path):
    """_write_avv must not contain warn header when _gap_registry has only RECOMMENDED gaps."""
    from src.agents.document_architect import DocumentOrchestrator

    arch = DocumentOrchestrator()
    arch._gap_registry = {
        "rec_gap": GapHint(
            id="rec_gap", severity="RECOMMENDED", doc_affected=["AVV"],
            article="DSGVO Art. 5", description="Optional", fix_url="/fix",
        )
    }
    arch.DRAFTS_DIR = tmp_path

    config = {"doc_language": "de"}
    graph_result = {
        "services": [], "controls": [], "doc_types": ["AVV"],
        "active_risks": [], "overall_risk": "minimal", "risk_levels": [],
        "docs_required": [], "usecase_risks": [],
    }
    path = arch._write_avv("test-project", "testrunid1234", graph_result, config)
    content = path.read_text(encoding="utf-8")
    assert "NICHT UNTERSCHRIFTSREIF" not in content
