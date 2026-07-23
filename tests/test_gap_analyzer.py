"""Tests for GapHint severity/id/article fields (ADR-098 Pre-Flight PF.1 + Task 1.3)."""
import dataclasses
import pytest


# ── helpers ────────────────────────────────────────────────────────────────────

def _hints_by_id(hints):
    return {h.id: h for h in hints}


def test_gap_hint_has_severity_field():
    from src.scanner.gap_analyzer import GapHint
    hint = GapHint(
        id="test_missing",
        severity="REQUIRED",
        article="DSGVO Art. 28 Abs. 3 lit. a",
        field="test_field",
        gap_reason="Missing test field",
        affected_docs=["AVV"],
        fix_url="/project/x/test",
        fix_label="Ergänzen",
        doc_affected=["AVV"],
        description="Test description",
        priority=1,
    )
    assert hint.severity == "REQUIRED"


def test_gap_hint_has_id_and_article_fields():
    from src.scanner.gap_analyzer import GapHint
    fields = {f.name for f in dataclasses.fields(GapHint)}
    assert "severity" in fields
    assert "id" in fields
    assert "article" in fields
    assert "doc_affected" in fields
    assert "description" in fields


def test_gap_hint_severity_default_is_recommended():
    from src.scanner.gap_analyzer import GapHint
    hint = GapHint(
        field="something",
        gap_reason="reason",
        affected_docs=[],
        fix_url="/fix",
        fix_label="Fix",
        priority=2,
    )
    assert hint.severity == "RECOMMENDED"


def test_gap_hint_required_severity():
    from src.scanner.gap_analyzer import GapHint
    hint = GapHint(
        id="retention_missing",
        severity="REQUIRED",
        article="DSGVO Art. 13 Abs. 2 lit. a",
        doc_affected=["VVT", "Datenschutzerklärung"],
        description="Retention periods missing",
        field="retention",
        gap_reason="No retention policies defined.",
        affected_docs=["VVT"],
        fix_url="/project/x/retention",
        fix_label="Add retention",
        priority=1,
    )
    assert hint.severity == "REQUIRED"
    assert hint.id == "retention_missing"
    assert hint.article == "DSGVO Art. 13 Abs. 2 lit. a"


# ── Task 1.3 Phase 1: AVV GapHint constructors ────────────────────────────────

def test_responsible_name_missing_emitted_when_absent():
    """responsible_name_missing emitted when config has no responsible_name."""
    from src.scanner.gap_analyzer import analyze_gaps
    hints = _hints_by_id(analyze_gaps(
        project_name="p", config={}, setup=None,
        retention_policies=[], services_detected=[],
    ))
    assert "responsible_name_missing" in hints
    h = hints["responsible_name_missing"]
    assert h.severity == "REQUIRED"
    assert h.article.startswith("DSGVO Art. 28")
    assert "AVV" in h.doc_affected


def test_responsible_name_missing_not_emitted_when_set():
    """responsible_name_missing NOT emitted when config.responsible_name is set."""
    from src.scanner.gap_analyzer import analyze_gaps
    hints = _hints_by_id(analyze_gaps(
        project_name="p",
        config={"responsible_name": "Jane Doe"},
        setup=None, retention_policies=[], services_detected=[],
    ))
    assert "responsible_name_missing" not in hints


def test_avv_instructing_persons_missing_emitted_when_absent():
    """avv_instructing_persons_missing emitted when config has no instructing_persons."""
    from src.scanner.gap_analyzer import analyze_gaps
    hints = _hints_by_id(analyze_gaps(
        project_name="p", config={}, setup=None,
        retention_policies=[], services_detected=[],
    ))
    assert "avv_instructing_persons_missing" in hints
    h = hints["avv_instructing_persons_missing"]
    assert h.severity == "REQUIRED"
    assert h.article.startswith("DSGVO Art. 28 Abs. 3")
    assert h.doc_affected == ["AVV"]


def test_avv_instructing_persons_missing_not_emitted_when_set():
    """avv_instructing_persons_missing NOT emitted when config.instructing_persons is non-empty list."""
    from src.scanner.gap_analyzer import analyze_gaps
    hints = _hints_by_id(analyze_gaps(
        project_name="p",
        config={"instructing_persons": [{"name": "Jane Doe", "title": "CEO"}]},
        setup=None, retention_policies=[], services_detected=[],
    ))
    assert "avv_instructing_persons_missing" not in hints


def test_avv_technical_measures_missing_emitted_when_tom_impl_empty():
    """avv_technical_measures_missing emitted when tom_implementations is {} (never configured)."""
    from src.scanner.gap_analyzer import analyze_gaps
    hints = _hints_by_id(analyze_gaps(
        project_name="p", config={"tom_implementations": {}}, setup=None,
        retention_policies=[], services_detected=[],
    ))
    assert "avv_technical_measures_missing" in hints
    h = hints["avv_technical_measures_missing"]
    assert h.severity == "RECOMMENDED"
    assert "TOM" in h.doc_affected


def test_avv_technical_measures_missing_not_emitted_when_configured():
    """avv_technical_measures_missing NOT emitted when tom_implementations has entries."""
    from src.scanner.gap_analyzer import analyze_gaps
    hints = _hints_by_id(analyze_gaps(
        project_name="p",
        config={"tom_implementations": {"encryption": "AES-256"}},
        setup=None, retention_policies=[], services_detected=[],
    ))
    assert "avv_technical_measures_missing" not in hints


def test_avv_data_subjects_missing_emitted_when_no_service_has_data_subjects():
    """avv_data_subjects_missing emitted when no service in services_detected has data_subjects."""
    from src.scanner.gap_analyzer import analyze_gaps
    hints = _hints_by_id(analyze_gaps(
        project_name="p", config={}, setup=None,
        retention_policies=[],
        services_detected=[{"name": "Stripe", "country": "USA"}],
    ))
    assert "avv_data_subjects_missing" in hints
    h = hints["avv_data_subjects_missing"]
    assert h.severity == "RECOMMENDED"
    assert "AVV" in h.doc_affected


def test_avv_data_subjects_missing_not_emitted_when_service_has_data_subjects():
    """avv_data_subjects_missing NOT emitted when at least one service has data_subjects."""
    from src.scanner.gap_analyzer import analyze_gaps
    hints = _hints_by_id(analyze_gaps(
        project_name="p", config={}, setup=None,
        retention_policies=[],
        services_detected=[{"name": "Stripe", "data_subjects": "Kunden"}],
    ))
    assert "avv_data_subjects_missing" not in hints


def test_retention_missing_doc_affected_includes_avv():
    """retention_missing doc_affected must include AVV (expanded in Task 1.3)."""
    from src.scanner.gap_analyzer import analyze_gaps
    hints = _hints_by_id(analyze_gaps(
        project_name="p", config={}, setup=None,
        retention_policies=[], services_detected=[],
    ))
    assert "retention_missing" in hints
    h = hints["retention_missing"]
    assert "AVV" in h.doc_affected
    assert h.article.startswith("DSGVO Art. 13")
    assert "Art. 28" in h.article


def test_vvt_purpose_missing_emitted_when_service_has_no_category():
    """vvt_purpose_missing emitted when service has neither processing_purpose nor category."""
    from src.scanner.gap_analyzer import analyze_gaps
    hints = _hints_by_id(analyze_gaps(
        project_name="p", config={}, setup=None,
        retention_policies=[],
        services_detected=[{"name": "AcmeTool"}],  # no purpose, no category
    ))
    assert "vvt_purpose_missing" in hints
    h = hints["vvt_purpose_missing"]
    assert h.severity == "RECOMMENDED"
    assert h.article.startswith("DSGVO Art. 30")


def test_vvt_purpose_missing_not_emitted_when_category_present():
    """vvt_purpose_missing NOT emitted when service has a category (_default_purpose covers it)."""
    from src.scanner.gap_analyzer import analyze_gaps
    hints = _hints_by_id(analyze_gaps(
        project_name="p", config={}, setup=None,
        retention_policies=[],
        services_detected=[{"name": "OpenAI", "category": "ai_llm"}],
    ))
    assert "vvt_purpose_missing" not in hints


def test_vvt_legal_basis_missing_emitted_when_service_has_no_legal_basis():
    """vvt_legal_basis_missing emitted when service has no legal_basis graph property."""
    from src.scanner.gap_analyzer import analyze_gaps
    hints = _hints_by_id(analyze_gaps(
        project_name="p", config={}, setup=None,
        retention_policies=[],
        services_detected=[{"name": "Stripe", "country": "USA"}],
    ))
    assert "vvt_legal_basis_missing" in hints
    h = hints["vvt_legal_basis_missing"]
    assert h.severity == "RECOMMENDED"
    assert h.article.startswith("DSGVO Art. 6")


def test_dsfa_data_subjects_missing_emitted_when_no_service_provides_them():
    """dsfa_data_subjects_missing emitted when no service has data_subjects."""
    from src.scanner.gap_analyzer import analyze_gaps
    hints = _hints_by_id(analyze_gaps(
        project_name="p", config={}, setup=None,
        retention_policies=[],
        services_detected=[{"name": "OpenAI"}],
    ))
    assert "dsfa_data_subjects_missing" in hints
    h = hints["dsfa_data_subjects_missing"]
    assert h.severity == "RECOMMENDED"
    assert h.article.startswith("DSGVO Art. 35")
    assert "DSFA" in h.doc_affected


def test_service_country_unknown_article_is_dsgvo_art44():
    """service_country_unknown has article DSGVO Art. 44 and RECOMMENDED severity."""
    from src.scanner.gap_analyzer import analyze_gaps
    hints = _hints_by_id(analyze_gaps(
        project_name="p", config={}, setup=None,
        retention_policies=[],
        services_detected=[{"name": "Stripe", "country": None}],
    ))
    assert "service_country_unknown" in hints
    h = hints["service_country_unknown"]
    assert h.severity == "RECOMMENDED"
    assert h.article == "DSGVO Art. 44"
    assert "AVV" in h.doc_affected


def test_analyze_gaps_returns_gap_hints_with_severity():
    """All GapHints returned by analyze_gaps() must have a severity field."""
    from src.scanner.gap_analyzer import analyze_gaps

    hints = analyze_gaps(
        project_name="test-project",
        config={},
        setup=None,
        retention_policies=[],
        services_detected=[],
    )
    for hint in hints:
        assert hasattr(hint, "severity"), f"GapHint missing severity: {hint}"
        assert hint.severity in ("REQUIRED", "RECOMMENDED"), (
            f"Invalid severity '{hint.severity}' on hint {hint.id}"
        )


# ── PR-B Gate 4: ai_config gap_ids with fix_url=/ai ────────────────────────────

_OPENAI = {"name": "OpenAI", "category": "ai_llm"}
_NON_AI = {"name": "PostgreSQL", "category": "database"}

# ADR-124: 9 gap_ids (3 project-level + 6 per_service). model + purpose added;
# review_date / ki_policy_review_date removed; ai_literacy_measures added;
# nutzergruppen→user_groups, grenzen→usage_limits.
_AI_GAP_IDS = {
    "ai_act_operative_responsible_missing",
    "ai_act_tech_responsible_missing",
    "ai_literacy_measures_missing",
    "ki_system_modell_version_missing",
    "ki_system_purpose_missing",
    "ki_system_user_groups_missing",
    "ki_system_usage_limits_missing",
    "ki_system_training_data_missing",
    "ki_system_logging_missing",
}


def test_ai_gaps_all_nine_emitted_when_ai_config_empty():
    """With an AI service detected but no ai_config, all 9 ADR-124 gap_ids are emitted, each linking to /ai."""
    from src.scanner.gap_analyzer import analyze_gaps
    hints = _hints_by_id(analyze_gaps(
        project_name="rand-industries", config={}, setup=None,
        retention_policies=[], services_detected=[_OPENAI, _NON_AI],
    ))
    emitted = _AI_GAP_IDS & hints.keys()
    assert emitted == _AI_GAP_IDS, f"missing: {_AI_GAP_IDS - emitted}"
    assert len(_AI_GAP_IDS) == 9
    for gid in _AI_GAP_IDS:
        assert hints[gid].fix_url.endswith("/project/rand-industries/ai")


def test_ai_gaps_corrected_article_strings():
    """ADR-124 legal cross-read: article anchors corrected (not Art.10/11/12)."""
    from src.scanner.gap_analyzer import analyze_gaps
    hints = _hints_by_id(analyze_gaps(
        project_name="p", config={}, setup=None,
        retention_policies=[], services_detected=[_OPENAI],
    ))
    assert hints["ki_system_training_data_missing"].article == "DSGVO Art. 5/6"
    assert hints["ki_system_logging_missing"].article == "EU AI Act Art. 26(6)"
    assert hints["ki_system_modell_version_missing"].article == "EU AI Act Art. 50 / DSGVO Art. 13"
    assert hints["ki_system_purpose_missing"].article == "EU AI Act Art. 6 / Anhang III"
    assert hints["ai_literacy_measures_missing"].article == "EU AI Act Art. 4"


def test_ai_gaps_tristate_false_is_not_a_gap():
    """ADR-124 tri-state: an explicit False on a bool field is an answer, NOT a gap.

    `not False` would wrongly flag it (the false-assertion trap avoided in the
    migration + toggle). Only `is None` (unset) is a gap.
    """
    from src.scanner.gap_analyzer import analyze_gaps
    config = {"ai_config": {
        "project_level": {"operative_responsible": "M", "tech_responsible": "L",
                          "ai_literacy_measures": False},
        "per_service": {"OpenAI": {"training_data": False, "logging": False,
                                   "model": "GPT-4o", "purpose": "customer_service_chatbot",
                                   "user_groups": "x", "usage_limits": "x"}},
    }}
    hints = _hints_by_id(analyze_gaps(
        project_name="p", config=config, setup=None,
        retention_policies=[], services_detected=[_OPENAI],
    ))
    assert "ki_system_training_data_missing" not in hints
    assert "ki_system_logging_missing" not in hints
    assert "ai_literacy_measures_missing" not in hints  # False is an answer
    assert _AI_GAP_IDS.isdisjoint(hints.keys())


def test_ai_gaps_none_emitted_when_no_ai_service():
    """No AI service → KI docs don't render → no AI gaps (would be false positives)."""
    from src.scanner.gap_analyzer import analyze_gaps
    hints = _hints_by_id(analyze_gaps(
        project_name="p", config={}, setup=None,
        retention_policies=[], services_detected=[_NON_AI],
    ))
    assert _AI_GAP_IDS.isdisjoint(hints.keys())


def test_ai_gaps_none_emitted_when_all_fields_set():
    """Fully populated ai_config (ADR-124 schema) → no AI gaps."""
    from src.scanner.gap_analyzer import analyze_gaps
    config = {"ai_config": {
        "project_level": {
            "operative_responsible": "M", "tech_responsible": "L",
            "ai_literacy_measures": True,
        },
        "per_service": {"OpenAI": {
            "model": "GPT-4o", "purpose": "customer_service_chatbot",
            "user_groups": "x", "usage_limits": "x",
            "training_data": True, "logging": True,
        }},
    }}
    hints = _hints_by_id(analyze_gaps(
        project_name="p", config=config, setup=None,
        retention_policies=[], services_detected=[_OPENAI],
    ))
    assert _AI_GAP_IDS.isdisjoint(hints.keys())


def test_ai_gaps_per_service_field_specific():
    """A per_service field set on the only AI service suppresses just that field's gap."""
    from src.scanner.gap_analyzer import analyze_gaps
    config = {"ai_config": {
        "project_level": {
            "operative_responsible": "M", "tech_responsible": "L",
            "ai_literacy_measures": True,
        },
        "per_service": {"OpenAI": {"user_groups": "HR-Team"}},
    }}
    hints = _hints_by_id(analyze_gaps(
        project_name="p", config=config, setup=None,
        retention_policies=[], services_detected=[_OPENAI],
    ))
    assert "ki_system_user_groups_missing" not in hints
    assert "ki_system_usage_limits_missing" in hints


def test_analyze_gaps_sorts_required_before_recommended():
    """ADR-086 Pre-Flight: severity drives sort, not legacy priority int.

    Verifies that a REQUIRED gap (regardless of its priority value) sorts
    before a RECOMMENDED gap.
    """
    from src.scanner.gap_analyzer import GapHint, _severity_order

    # _severity_order is the authoritative sort key
    assert _severity_order("REQUIRED") < _severity_order("RECOMMENDED")
    assert _severity_order("RECOMMENDED") < _severity_order("UNKNOWN")

    # End-to-end via the same sort key analyze_gaps uses
    hints = [
        GapHint(id="rec_low_prio", severity="RECOMMENDED", priority=1, field="z"),
        GapHint(id="req_high_prio", severity="REQUIRED", priority=3, field="a"),
    ]
    hints.sort(key=lambda h: (_severity_order(h.severity), h.id or h.field))
    assert hints[0].id == "req_high_prio"
    assert hints[1].id == "rec_low_prio"


# ── ADR-129 PR N2 (re-audit B-3): previously dead gap_ids now registered ──────

def test_vvt_data_subjects_missing_emitted_per_service():
    """One service without data_subjects → vvt id with the Art. 30(1)(c) citation."""
    from src.scanner.gap_analyzer import analyze_gaps
    hints = _hints_by_id(analyze_gaps(
        project_name="p", config={}, setup=None, retention_policies=[],
        services_detected=[
            {"name": "OK", "data_subjects": ["end_users"], "data_categories": "x"},
            {"name": "Naked", "data_subjects": [], "data_categories": "x"},
        ],
    ))
    assert "vvt_data_subjects_missing" in hints
    h = hints["vvt_data_subjects_missing"]
    assert h.article == "DSGVO Art. 30 Abs. 1 lit. c"
    assert "Naked" in h.description
    assert h.fix_url


def test_vvt_data_categories_missing_emitted_per_service():
    from src.scanner.gap_analyzer import analyze_gaps
    hints = _hints_by_id(analyze_gaps(
        project_name="p", config={}, setup=None, retention_policies=[],
        services_detected=[
            {"name": "Naked", "data_subjects": ["end_users"], "data_categories": None},
        ],
    ))
    assert "vvt_data_categories_missing" in hints
    assert hints["vvt_data_categories_missing"].article == "DSGVO Art. 30 Abs. 1 lit. c"


def test_vvt_graph_ids_not_emitted_when_all_populated():
    from src.scanner.gap_analyzer import analyze_gaps
    hints = _hints_by_id(analyze_gaps(
        project_name="p", config={}, setup=None, retention_policies=[],
        services_detected=[
            {"name": "OK", "data_subjects": ["end_users"], "data_categories": "x"},
        ],
    ))
    assert "vvt_data_subjects_missing" not in hints
    assert "vvt_data_categories_missing" not in hints


def test_avv_data_categories_missing_emitted_when_none_anywhere():
    from src.scanner.gap_analyzer import analyze_gaps
    hints = _hints_by_id(analyze_gaps(
        project_name="p", config={}, setup=None, retention_policies=[],
        services_detected=[{"name": "A", "data_subjects": ["end_users"]}],
    ))
    assert "avv_data_categories_missing" in hints
    assert hints["avv_data_categories_missing"].article.startswith("DSGVO Art. 28 Abs. 3")


def test_payment_integration_mode_unknown_emitted():
    """Mirrors payment_mode.resolve_payment_categories: is_gap ⇔ mode == unknown."""
    from src.scanner.gap_analyzer import analyze_gaps
    from src.documents.builders.common.payment_mode import PAYMENT_MODE_UNKNOWN
    hints = _hints_by_id(analyze_gaps(
        project_name="p", config={}, setup=None, retention_policies=[],
        services_detected=[
            {"name": "Stripe", "data_subjects": ["customers"], "data_categories": "x",
             "integration_mode": PAYMENT_MODE_UNKNOWN},
        ],
    ))
    assert "payment_integration_mode_unknown" in hints
    assert "Stripe" in hints["payment_integration_mode_unknown"].description


def test_payment_id_not_emitted_for_delegated_mode():
    from src.scanner.gap_analyzer import analyze_gaps
    hints = _hints_by_id(analyze_gaps(
        project_name="p", config={}, setup=None, retention_policies=[],
        services_detected=[
            {"name": "Stripe", "data_subjects": ["customers"], "data_categories": "x",
             "integration_mode": "delegated"},
        ],
    ))
    assert "payment_integration_mode_unknown" not in hints


def test_no_template_gap_id_is_dead():
    """Guard for the whole B-3 class: every inline_gap_marker('<id>') in any
    template must be producible by gap_analyzer (or be a render-only marker).
    A new template id without a producer degrades to a bare checkbox — silently."""
    import re
    from pathlib import Path
    import inspect
    import src.scanner.gap_analyzer as ga
    from src.agents.document_architect import DocumentOrchestrator

    template_ids = set()
    for tpl in Path("src/templates").rglob("*.j2"):
        template_ids |= set(re.findall(r"inline_gap_marker\('([a-z_0-9]+)'\)", tpl.read_text()))

    source = inspect.getsource(ga)
    producible = set(re.findall(r'id="([a-z_0-9]+)"', source))
    # dynamic ki_system ids are built from a tuple table (gap_analyzer ~:424)
    producible |= set(re.findall(r'"(ki_system_[a-z_0-9]+)"', source))
    render_only = set(DocumentOrchestrator._RENDER_ONLY_MARKERS)

    dead = template_ids - producible - render_only
    assert not dead, f"template gap_ids without a producer (bare-checkbox bug): {sorted(dead)}"
