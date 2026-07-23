"""ADR-110 Phase 3 — payment integration-mode render in AVV / VVT / SCC builders.

The mode is derived in the scanner (covered by tests/test_scout_github.py) and
attached to graph_result["services"][i]["integration_mode"] (covered by
tests/test_document_pipeline.py). Here we test the *render* side: each of the
three builders turns the mode into the verbatim wording or a gap, identically.
DB-free — builders are pure given a graph_result dict.
"""
from __future__ import annotations

import pytest

from src.documents.builders.avv_builder import AVVBuilder
from src.documents.builders.scc_builder import SCCBuilder
from src.documents.builders.vvt_builder import VVTBuilder
from src.documents.builders.common.payment_mode import (
    PAYMENT_MODE_DELEGATED,
    PAYMENT_MODE_MERCHANT_SIDE,
    PAYMENT_MODE_UNKNOWN,
    resolve_payment_categories,
)
from src.documents.content_models import BuildContext

CTX = BuildContext(run_id="test0110", generation_date="2026-05-31", project_name="test")

# Stripe as the scanner would hand it to the builders: US (non-EU → SCC-relevant),
# the static graph data_categories string, plus the ADR-110 render-time mode.
def _stripe(mode: str | None) -> dict:
    s = {
        "name": "Stripe",
        "country": "USA",
        "gdpr_adequate": False,
        "dpa_required": True,
        "data_categories": "Zahlungsdaten, Kreditkartendaten (tokenisiert), "
                           "Rechnungsadressen, Transaktionsdaten",
        "data_subjects": "Kunden",
        "category": "payment",
    }
    if mode is not None:
        s["integration_mode"] = mode
    return s


def _graph(mode: str | None) -> dict:
    return {"services": [_stripe(mode)], "docs_required": [], "doc_types": [],
            "controls": [], "risk_levels": [], "overall_risk": "limited"}


# ── resolve_payment_categories (the shared decision) ─────────────────────────

def test_resolve_delegated_returns_override_no_gap():
    override, is_gap = resolve_payment_categories(_stripe(PAYMENT_MODE_DELEGATED))
    assert is_gap is False
    assert override and "direkt vom Zahlungsdienstleister" in override[0]
    assert "Kreditkartendaten" not in override[0]


def test_resolve_merchant_side_mentions_card_data_marked():
    override, is_gap = resolve_payment_categories(_stripe(PAYMENT_MODE_MERCHANT_SIDE))
    assert is_gap is False
    assert override and "[Hinweis]" in override[0] and "Kartendaten" in override[0]


def test_resolve_unknown_is_gap_no_override():
    override, is_gap = resolve_payment_categories(_stripe(PAYMENT_MODE_UNKNOWN))
    assert override is None and is_gap is True


def test_resolve_no_mode_keeps_original():
    override, is_gap = resolve_payment_categories(_stripe(None))
    assert override is None and is_gap is False


# ── AVV builder ──────────────────────────────────────────────────────────────

def test_avv_delegated_drops_card_data():
    model = AVVBuilder().build(_graph(PAYMENT_MODE_DELEGATED), {}, {}, [], CTX)
    block = next(b for b in model.service_data_blocks if b.service_name == "Stripe")
    assert block.data_categories_gap is False
    assert not any("Kreditkartendaten" in c for c in block.data_categories)
    assert any("direkt vom Zahlungsdienstleister" in c for c in block.data_categories)


def test_avv_unknown_sets_gap():
    model = AVVBuilder().build(_graph(PAYMENT_MODE_UNKNOWN), {}, {}, [], CTX)
    block = next(b for b in model.service_data_blocks if b.service_name == "Stripe")
    assert block.data_categories_gap is True
    assert block.data_categories == []


def test_avv_no_mode_keeps_card_data():
    model = AVVBuilder().build(_graph(None), {}, {}, [], CTX)
    block = next(b for b in model.service_data_blocks if b.service_name == "Stripe")
    assert any("Kreditkartendaten" in c for c in block.data_categories)


# ── VVT builder ──────────────────────────────────────────────────────────────

def test_vvt_delegated_drops_card_data():
    model = VVTBuilder().build(_graph(PAYMENT_MODE_DELEGATED), {}, {}, [], CTX)
    act = next(a for a in model.activities if a.name == "Stripe")
    assert act.data_categories_gap is False
    assert "Kreditkartendaten" not in (act.data_categories or "")
    assert "direkt vom Zahlungsdienstleister" in act.data_categories


def test_vvt_unknown_sets_gap():
    model = VVTBuilder().build(_graph(PAYMENT_MODE_UNKNOWN), {}, {}, [], CTX)
    act = next(a for a in model.activities if a.name == "Stripe")
    assert act.data_categories_gap is True


# ── SCC builder (only third-country services; Stripe US qualifies) ───────────

def test_scc_delegated_drops_card_data():
    model = SCCBuilder().build(_graph(PAYMENT_MODE_DELEGATED), {}, {}, [], CTX)
    row = next(r for r in model.services_with_transfer if r.name == "Stripe")
    assert row.data_categories_gap is False
    assert not any("Kreditkartendaten" in c for c in row.data_categories)


def test_scc_merchant_side_keeps_marked_card_data():
    model = SCCBuilder().build(_graph(PAYMENT_MODE_MERCHANT_SIDE), {}, {}, [], CTX)
    row = next(r for r in model.services_with_transfer if r.name == "Stripe")
    assert any("[Hinweis]" in c for c in row.data_categories)


def test_scc_unknown_sets_gap():
    model = SCCBuilder().build(_graph(PAYMENT_MODE_UNKNOWN), {}, {}, [], CTX)
    row = next(r for r in model.services_with_transfer if r.name == "Stripe")
    assert row.data_categories_gap is True


# ── Vocabulary single-source guard ───────────────────────────────────────────

def test_mode_literals_single_sourced_with_scanner():
    """The scanner (producer) and builders (consumers) must share one vocabulary."""
    from src.workflow import main
    assert main.PAYMENT_MODE_DELEGATED == PAYMENT_MODE_DELEGATED
    assert main.PAYMENT_MODE_MERCHANT_SIDE == PAYMENT_MODE_MERCHANT_SIDE
    assert main.PAYMENT_MODE_UNKNOWN == PAYMENT_MODE_UNKNOWN
