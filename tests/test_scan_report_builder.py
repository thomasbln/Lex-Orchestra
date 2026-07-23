from __future__ import annotations
import dataclasses

from src.documents.builders.scan_report_builder import (
    ScanReportBuilder,
    ScanReportContentModel,
    TopActionRow,
    SignalRow,
    ActiveRiskRow,
    RepoExtractionsBlock,
)
from src.documents.content_models import BuildContext
from src.scanner.gap_analyzer import GapHint

CTX = BuildContext(
    run_id="0158d042-abcd",
    generation_date="2026-04-21",
    project_name="rand-industries",
)


def _gap(
    id: str,
    priority: int,
    fix_label: str,
    doc: str = "AVV",
) -> GapHint:
    # GapHint has both `doc_affected` (ADR-098) and `affected_docs` (legacy).
    # Builder reads `affected_docs`. Populate both for full fidelity.
    return GapHint(
        id=id,
        severity="REQUIRED" if priority == 1 else "RECOMMENDED",
        doc_affected=[doc],
        affected_docs=[doc],
        priority=priority,
        article="x",
        fix_label=fix_label,
        fix_url=f"/fix/{id}",
        gap_reason=f"reason for {id}",
    )


def test_scan_report_run_id_shortened():
    model = ScanReportBuilder().build({}, {}, {}, [], CTX)
    assert model.run_id_short == "0158d042"


def test_scan_report_top_actions_max_3():
    gaps = [_gap(f"g{i}", 1, f"Fix {i}") for i in range(5)]
    model = ScanReportBuilder().build({}, {}, {}, gaps, CTX)
    assert len(model.top_actions) <= 3


def test_scan_report_top_actions_priority_1_first():
    """Builder must sort by severity before top_n_actions slice.

    Verifies the fix for top_n_actions() not sorting internally.
    Fixture aligns priority=1 with severity=REQUIRED via _gap helper.
    """
    gaps = [
        _gap("low", 3, "nice to have"),
        _gap("crit", 1, "critical"),
        _gap("mid", 2, "medium"),
    ]
    model = ScanReportBuilder().build({}, {}, {}, gaps, CTX)
    assert model.top_actions[0].fix_label == "critical"
    assert model.top_actions[0].icon == "🔴"


def test_scan_report_service_names_extracted():
    graph = {"services": [
        {"name": "OpenAI"},
        {"canonical_name": "Stripe"},
        {},
    ]}
    model = ScanReportBuilder().build(graph, {}, {}, [], CTX)
    assert model.service_names == ["OpenAI", "Stripe", "?"]


def test_scan_report_signal_labels_resolved():
    signals = [
        {"signal_type": "ai_usage", "confidence": 0.95},
        {"signal_type": "unknown_type", "confidence": 0.3},
    ]
    model = ScanReportBuilder().build({}, {}, {}, [], CTX, risk_signals=signals)
    assert model.top_signals[0].label.startswith("KI-API-Nutzung")
    assert model.top_signals[0].confidence_pct == 95
    assert model.top_signals[1].label == "unknown_type"


def test_scan_report_signals_limited_to_5():
    signals = [{"signal_type": "ai_usage", "confidence": 0.5} for _ in range(10)]
    model = ScanReportBuilder().build({}, {}, {}, [], CTX, risk_signals=signals)
    assert len(model.top_signals) == 5


def test_scan_report_signals_sorted_by_confidence():
    signals = [
        {"signal_type": "personal_data", "confidence": 0.4},
        {"signal_type": "ai_usage", "confidence": 0.9},
    ]
    model = ScanReportBuilder().build({}, {}, {}, [], CTX, risk_signals=signals)
    assert model.top_signals[0].confidence_pct == 90


def test_scan_report_usecase_display_resolves():
    config = {"ai_usecase_type": "hr_recruitment_screening", "ai_usecase_confidence": 0.85}
    model = ScanReportBuilder().build({}, {}, config, [], CTX)
    assert "HR-Recruiting" in model.usecase_display
    assert "HIGH RISK" in model.usecase_display
    assert "85%" in model.usecase_display


def test_scan_report_usecase_display_none_for_unknown():
    config = {"ai_usecase_type": "totally_unknown_type"}
    model = ScanReportBuilder().build({}, {}, config, [], CTX)
    assert model.usecase_display is None


def test_scan_report_risk_display_uses_label_map():
    graph = {"overall_risk": "gpai"}
    model = ScanReportBuilder().build(graph, {}, {}, [], CTX)
    assert "GPAI" in model.risk_display


def test_scan_report_usecase_risk_override():
    """ADR-060: UseCase HIGH RISK overrides lower overall_risk."""
    graph = {
        "overall_risk": "limited",
        "usecase_risks": [
            {"risk_level": "High", "article": "Art. 6", "annex_iii_nr": 4},
        ],
    }
    model = ScanReportBuilder().build(graph, {}, {}, [], CTX)
    assert "HIGH RISK" in model.risk_display
    assert "Annex III Nr. 4" in model.risk_display


def test_scan_report_active_risks_resolved():
    graph = {"active_risks": ["PII_IN_LLM_CONTEXT", "NO_AI_AUDIT_TRAIL"]}
    model = ScanReportBuilder().build(graph, {}, {}, [], CTX)
    assert len(model.active_risks) == 2
    assert "KI-Kontext" in model.active_risks[0].description
    assert "Langfuse" in model.active_risks[1].description


def test_scan_report_generated_doc_labels_resolved():
    """_DOC_LABELS uses mixed-case keys matching generate_all() output."""
    model = ScanReportBuilder().build(
        {}, {}, {}, [], CTX,
        generated_doc_types=["AVV", "TOM", "KI_Policy"],
    )
    assert "Auftragsverarbeitungsvertrag" in model.generated_doc_labels[0]
    assert "Technische und Organisatorische" in model.generated_doc_labels[1]
    assert "KI-Nutzungsrichtlinie" in model.generated_doc_labels[2]
    assert model.generated_doc_count == 3


def test_scan_report_immediate_actions_include_baseline():
    model = ScanReportBuilder().build({}, {}, {}, [], CTX)
    assert any("Rechtsberater" in a for a in model.immediate_actions)


def test_scan_report_immediate_actions_include_priority_1_gaps():
    gaps = [
        _gap("crit1", 1, "Fix critical thing"),
        _gap("low", 3, "nice-to-have"),
    ]
    model = ScanReportBuilder().build({}, {}, {}, gaps, CTX)
    assert any("critical thing" in a for a in model.immediate_actions)
    assert not any("nice-to-have" in a for a in model.immediate_actions)


def test_scan_report_short_term_hr_actions():
    config = {"ai_usecase_type": "hr_recruitment_screening"}
    model = ScanReportBuilder().build({}, {}, config, [], CTX)
    assert any("HR-KI-System" in a for a in model.short_term_actions)
    assert any("DSFA" in a for a in model.short_term_actions)


def test_scan_report_short_term_audit_trail():
    graph = {"active_risks": ["NO_AI_AUDIT_TRAIL"]}
    model = ScanReportBuilder().build(graph, {}, {}, [], CTX)
    assert any("Langfuse" in a for a in model.short_term_actions)


def test_scan_report_repo_extractions_block():
    extractions = {
        "extractions_count": 5,
        "extractions_successful": 4,
        "fields_merged": 12,
        "fields_skipped": 2,
        "source_files": ["docs/privacy.md"],
        "merged_fields": ["company_name", "contact_email"],
    }
    model = ScanReportBuilder().build(
        {}, {}, {}, [], CTX,
        repo_extraction_summary=extractions,
    )
    assert model.repo_extractions is not None
    assert model.repo_extractions.count_ok == 4
    assert "docs/privacy.md" in model.repo_extractions.source_files


def test_scan_report_repo_extractions_none_when_empty():
    model = ScanReportBuilder().build({}, {}, {}, [], CTX)
    assert model.repo_extractions is None


def test_scan_report_all_gaps_sorted_and_indexed():
    """all_gaps is sorted by priority, indexed 1..N."""
    gaps = [
        _gap("c", 3, "C (low)"),
        _gap("a", 1, "A (crit)"),
        _gap("b", 2, "B (mid)"),
    ]
    model = ScanReportBuilder().build({}, {}, {}, gaps, CTX)
    assert len(model.all_gaps) == 3
    assert model.all_gaps[0].index == 1
    assert model.all_gaps[0].fix_label == "A (crit)"
    assert model.all_gaps[1].fix_label == "B (mid)"
    assert model.all_gaps[2].fix_label == "C (low)"
    assert model.all_gaps_count == 3


def _minimal_graph(services):
    return {"services": services, "controls": [], "active_risks": [],
            "usecase_risks": [], "overall_risk": "limited"}


def _ctx():
    return BuildContext(run_id="g0000001", generation_date="2026-04-21",
                        project_name="shop")


def test_ki_docs_skipped_note_present_for_no_ai_stack():
    graph = _minimal_graph([{"name": "Stripe", "category": "payment"}])
    model = ScanReportBuilder().build(
        graph, {}, {}, [], _ctx(), generated_doc_types=["AVV", "TOM", "VVT"]
    )
    assert model.ki_docs_skipped_note is not None
    assert "ausgelassen" in model.ki_docs_skipped_note


def test_ki_docs_skipped_note_none_when_ai_present():
    graph = _minimal_graph(
        [{"name": "OpenAI", "category": "ai_llm", "ai_act_relevant": True}]
    )
    model = ScanReportBuilder().build(
        graph, {}, {}, [], _ctx(), generated_doc_types=["AVV", "KI_Policy"]
    )
    assert model.ki_docs_skipped_note is None


def test_ki_docs_skipped_note_none_when_ki_doc_generated_anyway():
    # Defensive: if a KI doc was generated, never claim it was skipped.
    graph = _minimal_graph([{"name": "Stripe", "category": "payment"}])
    model = ScanReportBuilder().build(
        graph, {}, {}, [], _ctx(), generated_doc_types=["AVV", "DSFA"]
    )
    assert model.ki_docs_skipped_note is None


def test_scan_report_content_model_matches_golden():
    """Golden-file regression test."""
    import json
    from pathlib import Path
    FIXTURE = Path(__file__).parent / "fixtures"
    GOLDEN = Path(__file__).parent / "golden"

    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    config = json.loads((FIXTURE / "rand_industries_config.json").read_text())
    gaps_raw = json.loads((FIXTURE / "rand_industries_gaps.json").read_text())
    gap_hints = [GapHint(**g) if isinstance(g, dict) else g for g in gaps_raw]

    ctx = BuildContext(
        run_id="0158d042", generation_date="2026-04-21",
        project_name="rand-industries",
    )
    model = ScanReportBuilder().build(
        graph, {}, config, gap_hints, ctx,
        generated_doc_types=["AVV", "TOM", "VVT", "AI_Act_Manifest", "KI_Policy"],
    )
    expected = json.loads(
        (GOLDEN / "rand_industries_scan_report_content_model.json").read_text()
    )
    assert dataclasses.asdict(model) == expected


# ── ADR-086 Pre-Flight: severity propagation ──────────────────────────────────

def test_action_lists_groups_by_severity():
    """REQUIRED gaps land in immediate; RECOMMENDED in short_term."""
    gaps = [
        _gap("req1", priority=1, fix_label="Required A"),   # severity=REQUIRED
        _gap("rec1", priority=2, fix_label="Recommended B"),  # severity=RECOMMENDED
        _gap("rec2", priority=3, fix_label="Recommended C"),  # severity=RECOMMENDED (was priority=3)
    ]
    # Force the priority=3 gap to severity=RECOMMENDED explicitly
    gaps[2].severity = "RECOMMENDED"
    model = ScanReportBuilder().build({}, {}, {}, gaps, CTX)
    assert "Required A" in model.immediate_actions
    assert "Recommended B" in model.short_term_actions
    assert "Recommended C" in model.short_term_actions
    assert "Required A" not in model.short_term_actions
    assert "Recommended B" not in model.immediate_actions


def test_severity_icon_and_label():
    """Direct test of helper mapping — REQUIRED→🔴, RECOMMENDED→🟡, unknown→⚪."""
    b = ScanReportBuilder()
    assert b._severity_icon("REQUIRED") == "🔴"
    assert b._severity_icon("RECOMMENDED") == "🟡"
    assert b._severity_icon("UNKNOWN") == "⚪"
    assert b._severity_label("REQUIRED") == "🔴 erforderlich"
    assert b._severity_label("RECOMMENDED") == "🟡 empfohlen"
    assert b._severity_label("UNKNOWN") == "⚪ optional"
