"""ADR-129 PR 14 + PR N4 — VVT cells never silently empty (audit K25/F6).

Fixture-driven, no DB. PR N4 (re-audit B-8): the original harness stubbed
inline_gap_marker to echo the gap_id, so `assert gap_id in cell` tested the
stub, not production — it stayed green while production rendered a bare
checkbox without the Art. 30 citation. The render now binds the REAL
inline_gap_marker with a registry populated by the REAL analyze_gaps, so the
assertions cover the full chain analyzer → registry → marker → template.
"""
import dataclasses

from src.documents.builders.vvt_builder import VVTBuilder
from src.documents.content_models import BuildContext
from tests.test_doc_linter import _base_ctx, _make_jinja

CTX = BuildContext(run_id="test00001", generation_date="2026-07-05", project_name="test")

SPARSE_SERVICE = {  # graph node without legal_basis / data_subjects / data_categories
    "name": "SparseSvc", "category": "database",
    "gdpr_adequate": True, "dpa_required": True,
}


def _render(services):
    from src.agents.document_architect import DocumentOrchestrator
    from src.scanner.gap_analyzer import analyze_gaps

    env = _make_jinja()
    # real marker + real registry (PR N4) — same wiring as generate_all()
    da = DocumentOrchestrator.__new__(DocumentOrchestrator)
    da._current_lang = "de"
    da._gap_registry = {g.id: g for g in analyze_gaps(
        project_name="test", config={}, setup=None, retention_policies=[],
        services_detected=services,
    )}
    env.globals["inline_gap_marker"] = da.inline_gap_marker
    model = VVTBuilder().build({"services": services}, {}, {}, [], CTX)
    ctx = _base_ctx()
    ctx["model"] = dataclasses.asdict(model)
    return env.get_template("vvt.md.j2").render(**ctx)


def test_vvt_sparse_service_shows_markers_with_citation():
    """The K25 point: the marker must carry the article citation + fix link —
    not a bare checkbox (that was re-audit finding B-3)."""
    out = _render([SPARSE_SERVICE])
    for row_label, citation in [
        ("**Rechtsgrundlage**", "Art. 6 Abs. 1"),
        ("**Betroffene Personen**", "Art. 30 Abs. 1 lit. c"),
        ("**Datenkategorien**", "Art. 30 Abs. 1 lit. c"),
    ]:
        line = next(l for l in out.splitlines() if row_label in l)
        cell = line.split("|")[2].strip()
        assert cell, f"silent empty cell for {row_label}"
        assert "☐" in cell, f"no marker for {row_label}: {cell!r}"
        assert citation in cell, f"marker without citation for {row_label}: {cell!r}"
        assert "ergänzen](" in cell, f"marker without fix link for {row_label}: {cell!r}"


def test_vvt_filled_values_render_without_marker():
    svc = dict(SPARSE_SERVICE, legal_basis="art_6_1_b_contract",
               data_subjects=["customers"], data_categories="Bestandsdaten")
    out = _render([svc])
    line = next(l for l in out.splitlines() if "**Rechtsgrundlage**" in l)
    assert "Art. 6 Abs. 1 lit. b" in line and "☐" not in line
    line = next(l for l in out.splitlines() if "**Betroffene Personen**" in l)
    assert "Kunden" in line and "☐" not in line
