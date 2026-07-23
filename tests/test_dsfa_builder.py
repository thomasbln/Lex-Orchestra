from __future__ import annotations
import dataclasses

from src.documents.builders.dsfa_builder import (
    DSFABuilder,
    DSFAContentModel,
    DSFARisksBlock,
)
from src.documents.content_models import BuildContext, GapMarker
from src.scanner.gap_analyzer import GapHint

CTX = BuildContext(
    run_id="test00001",
    generation_date="2026-04-20",
    project_name="test-project",
)


def _gap(id: str, severity: str, doc: str) -> GapHint:
    return GapHint(id=id, severity=severity, doc_affected=[doc], affected_docs=[doc])


def test_dsfa_zweck_from_usecase():
    ai_usecase = {"type": "hr_screening", "description_de": "HR-Bewerberauswahl",
                  "risk_level": "High"}
    model = DSFABuilder().build({"services": []}, {}, {}, [], CTX, ai_usecase=ai_usecase)
    assert model.zweck == "HR-Bewerberauswahl"


def test_dsfa_zweck_ignores_phantom_product_description_column():
    """ADR-129 PR 16 (audit K23/F4): config.product_description never existed as a
    column — the dead read is gone; without a use case the zweck is an honest gap."""
    config = {"product_description": "SaaS-Produkt"}
    model = DSFABuilder().build({"services": []}, {}, config, [], CTX)
    assert isinstance(model.zweck, GapMarker)


def test_dsfa_zweck_missing_returns_gap_marker():
    model = DSFABuilder().build({"services": []}, {}, {}, [], CTX)
    assert isinstance(model.zweck, GapMarker)
    assert model.zweck.gap_id == "dsfa_zweck_missing"
    assert model.zweck.fix_url.endswith("/ai")   # points to the KI-Angaben section


def test_dsfa_rechtsgrundlage_from_consent_risk():
    graph = {"services": [], "active_risks": ["CONSENT_MANAGEMENT"]}
    model = DSFABuilder().build(graph, {}, {}, [], CTX)
    assert "Einwilligung" in model.rechtsgrundlage


def test_dsfa_rechtsgrundlage_phantom_columns_ignored():
    """ADR-129 PR 16: dead reads (contract_processing, rechtsgrundlage) removed —
    phantom config keys no longer influence the legal basis."""
    model = DSFABuilder().build(
        {"services": []}, {}, {"contract_processing": True,
                               "rechtsgrundlage": "Art. 6 Abs. 1 lit. f DSGVO"}, [], CTX,
    )
    assert isinstance(model.rechtsgrundlage, GapMarker)
    assert model.rechtsgrundlage.fix_url.endswith("/ai")


def test_dsfa_rechtsgrundlage_missing_returns_gap_marker():
    model = DSFABuilder().build({"services": []}, {}, {}, [], CTX)
    assert isinstance(model.rechtsgrundlage, GapMarker)


def test_dsfa_filters_ai_services():
    graph = {"services": [
        {"name": "OpenAI", "category": "ai_llm"},
        {"name": "Stripe", "category": "payment"},
        {"name": "Langfuse", "category": "observability", "ai_act_relevant": True},
    ]}
    model = DSFABuilder().build(graph, {}, {}, [], CTX)
    names = {s.name for s in model.ai_services}
    assert names == {"OpenAI", "Langfuse"}


def test_dsfa_pii_services_from_categories():
    graph = {"services": [
        {"name": "Mailgun", "category": "email"},
        {"name": "Mixpanel", "category": "analytics"},
        {"name": "Hetzner", "category": "hosting"},
    ]}
    model = DSFABuilder().build(graph, {}, {}, [], CTX)
    assert "Mailgun" in model.pii_services
    assert "Mixpanel" in model.pii_services
    assert "Hetzner" not in model.pii_services


def test_dsfa_pii_services_include_dpa_required():
    graph = {"services": [
        {"name": "Braintree", "category": "payment", "dpa_required": True},
    ]}
    model = DSFABuilder().build(graph, {}, {}, [], CTX)
    assert "Braintree" in model.pii_services


def test_dsfa_risk_flags_from_active_risks():
    graph = {"services": [], "active_risks": ["PII_IN_LLM_CONTEXT", "NO_AI_AUDIT_TRAIL"]}
    model = DSFABuilder().build(graph, {}, {}, [], CTX)
    assert model.risks.pii_in_llm_context is True
    assert model.risks.no_ai_audit_trail is True
    assert model.risks.rag_over_pii is False
    assert model.risks.pii_in_logs is False


def test_dsfa_triggered_by_high_risk_usecase():
    ai_usecase = {"type": "hr", "risk_level": "High", "title_de": "HR"}
    model = DSFABuilder().build({"services": []}, {}, {}, [], CTX, ai_usecase=ai_usecase)
    assert model.triggered_by_high_risk_usecase is True


def test_dsfa_warn_header_only_required_gaps():
    gaps = [
        _gap("a", "REQUIRED", "DSFA"),
        _gap("b", "RECOMMENDED", "DSFA"),
        _gap("c", "REQUIRED", "AVV"),
    ]
    model = DSFABuilder().build({"services": []}, {}, {}, gaps, CTX)
    assert len(model.warn_header_gaps) == 1
    assert model.warn_header_gaps[0].id == "a"


def test_dsfa_content_model_matches_golden():
    import json
    from pathlib import Path
    FIXTURE = Path(__file__).parent / "fixtures"
    GOLDEN = Path(__file__).parent / "golden"

    graph = json.loads((FIXTURE / "rand_industries_graph.json").read_text())
    config = json.loads((FIXTURE / "rand_industries_config.json").read_text())
    gaps_raw = json.loads((FIXTURE / "rand_industries_gaps.json").read_text())
    gap_hints = [GapHint(**g) if isinstance(g, dict) else g for g in gaps_raw]

    ai_usecase = {"type": "hr_recruitment_screening", "risk_level": "High",
                  "title_de": "HR-Recruiting", "description_de": "Bewerberauswahl",
                  "article": "Annex III Nr. 4", "annex_iii_nr": 4}
    ctx = BuildContext(run_id="0158d042", generation_date="2026-04-20",
                       project_name="rand-industries")
    model = DSFABuilder().build(graph, {}, config, gap_hints, ctx, ai_usecase=ai_usecase)
    expected = json.loads(
        (GOLDEN / "rand_industries_dsfa_content_model.json").read_text()
    )
    assert dataclasses.asdict(model) == expected


# ── ADR-129 PR 16 (audit K8): high-risk row driven by the existing model flag ──

def test_dsfa_template_high_risk_row_renders_from_usecase_flag():
    """de/dsfa.md.j2 referenced non-existent model.is_high_risk (silently falsy);
    it now uses triggered_by_high_risk_usecase — the row must render WITHOUT any
    decision_logic signal."""
    import dataclasses as _dc
    from tests.test_doc_linter import _base_ctx, _make_jinja

    graph = {"services": [], "active_risks": []}
    ai_usecase = {"type": "hr_recruitment_screening", "title_de": "Bewerbungsscreening",
                  "risk_level": "High"}
    model = DSFABuilder().build(graph, {}, {}, [], CTX, ai_usecase=ai_usecase)
    assert model.triggered_by_high_risk_usecase is True

    env = _make_jinja()
    ctx = _base_ctx()
    ctx["model"] = _dc.asdict(model)
    out = env.get_template("dsfa.md.j2").render(**ctx)
    # High-risk drives the Fraunhofer damage-scenario table (builder always emits
    # the integrity/discrimination scenario for high-risk) — the static fallback
    # row is the else-branch for scenario-less runs. Both paths now reference a
    # REAL model field (the dead model.is_high_risk ref is gone).
    assert "Diskriminierungsfreiheit" in out
    assert "model.is_high_risk" not in open("src/templates/de/dsfa.md.j2").read()
