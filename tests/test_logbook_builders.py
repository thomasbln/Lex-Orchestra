"""Tests for ADR-111 PR2 — AVV/VVT/SCC builders emit real logbook entries.

Granularity is per source node: a multi-service section yields one entry per
contributing service. Entries are read off the built model, so they reflect
exactly what was rendered (no parallel derivation, no drift).
"""

from src.documents.builders.avv_builder import AVVBuilder
from src.documents.builders.scc_builder import SCCBuilder
from src.documents.builders.vvt_builder import VVTBuilder
from src.documents.content_models import BuildContext
from src.documents.logbook import SourceType, Status, write_logbook

CTX = BuildContext(run_id="6a3e5e15", generation_date="2026-05-31", project_name="test")


def _stripe(**over):
    base = {
        "name": "Stripe",
        "country": "USA",
        "gdpr_adequate": False,
        "data_categories": "Zahlungsdaten, Kreditkartendaten (tokenisiert)",
        "source": "ADR-075 Service-Region + SCC-Annotations (kuratiert)",
        "license": "Lex-Orchestra internal + EU SCC Decision 2021/914",
        "last_verified": "2026-05-28",
    }
    base.update(over)
    return base


# -- AVV ----------------------------------------------------------------------

def test_avv_logbook_one_entry_per_contributing_service():
    graph = {"services": [
        _stripe(),
        {"name": "Postmark", "data_categories": "E-Mail-Adressen", "source": "seed"},
        {"name": "PostgreSQL", "data_categories": "Anwendungsdaten", "source": "seed"},
    ]}
    builder = AVVBuilder()
    model = builder.build(graph, {}, {}, [], CTX)
    entries = builder.logbook_entries(model, graph)

    cat_entries = [e for e in entries if e.section == "AVV § 2(1) Datenkategorien"]
    names = {e.source_key["name"] for e in cat_entries}
    assert names == {"Stripe", "Postmark", "PostgreSQL"}  # one per service, not one per section


def test_avv_logbook_stripe_entry_shape_and_provenance():
    graph = {"services": [_stripe()]}
    builder = AVVBuilder()
    model = builder.build(graph, {}, {}, [], CTX)
    entries = builder.logbook_entries(model, graph)

    stripe = next(e for e in entries if e.source_key.get("name") == "Stripe")
    assert stripe.source_type == SourceType.GRAPH_NODE
    assert stripe.source_key == {"label": "Service", "name": "Stripe"}
    assert stripe.status == Status.SOURCED
    assert stripe.provenance.source == "ADR-075 Service-Region + SCC-Annotations (kuratiert)"
    assert stripe.provenance.last_verified == "2026-05-28"
    assert stripe.provenance.seed_run_id is None  # ADR-107 Rest 1, honest empty


def test_avv_logbook_merchant_side_note_witnesses_divergence():
    """ADR-110 mode present → the note records the graph↔document divergence."""
    graph = {"services": [_stripe(integration_mode="merchant_side_possible")]}
    builder = AVVBuilder()
    model = builder.build(graph, {}, {}, [], CTX)
    entries = builder.logbook_entries(model, graph)

    stripe = next(e for e in entries if e.source_key.get("name") == "Stripe")
    assert stripe.status == Status.SOURCED
    assert stripe.note is not None
    assert "integration_mode=merchant_side_possible" in stripe.note
    assert "not applied" in stripe.note


def test_avv_logbook_payment_unknown_is_gap():
    graph = {"services": [_stripe(integration_mode="unknown")]}
    builder = AVVBuilder()
    model = builder.build(graph, {}, {}, [], CTX)
    entries = builder.logbook_entries(model, graph)

    stripe = next(e for e in entries if e.source_key.get("name") == "Stripe")
    assert stripe.status == Status.GAP
    assert "integration_mode=unknown" in (stripe.note or "")


def test_avv_logbook_data_subjects_gap_marker():
    """No data_subjects on any service → § 2 Betroffene Personen is a gap_marker."""
    graph = {"services": [_stripe(data_subjects=None)]}
    builder = AVVBuilder()
    model = builder.build(graph, {}, {}, [], CTX)
    entries = builder.logbook_entries(model, graph)

    gaps = [e for e in entries if e.source_type == SourceType.GAP_MARKER]
    assert any(e.source_key.get("gap_id") == "avv_data_subjects_missing"
               and e.status == Status.GAP for e in gaps)


def test_avv_logbook_service_without_license_records_null():
    """A service with source but no license records license=None (ADR-107 Rest 2)."""
    graph = {"services": [{"name": "Postmark", "data_categories": "E-Mail-Adressen",
                           "source": "seed"}]}
    builder = AVVBuilder()
    model = builder.build(graph, {}, {}, [], CTX)
    entries = builder.logbook_entries(model, graph)

    pm = next(e for e in entries if e.source_key.get("name") == "Postmark")
    assert pm.provenance.license is None


# -- VVT ----------------------------------------------------------------------

def test_vvt_logbook_one_entry_per_activity():
    graph = {"services": [
        _stripe(integration_mode="merchant_side_possible"),
        {"name": "Postmark", "data_categories": "E-Mail-Adressen", "source": "seed"},
    ]}
    builder = VVTBuilder()
    model = builder.build(graph, {}, {}, [], CTX)
    entries = builder.logbook_entries(model, graph)

    names = {e.source_key["name"] for e in entries}
    assert names == {"Stripe", "Postmark"}
    stripe = next(e for e in entries if e.source_key["name"] == "Stripe")
    assert "integration_mode=merchant_side_possible" in (stripe.note or "")


# -- SCC ----------------------------------------------------------------------

def test_scc_logbook_one_entry_per_drittland_service():
    graph = {"services": [
        _stripe(),  # USA, not gdpr_adequate → Drittland
        {"name": "Hetzner", "country": "Germany", "gdpr_adequate": True,
         "data_categories": "Serverdaten"},  # EU → excluded from SCC
    ]}
    builder = SCCBuilder()
    model = builder.build(graph, {}, {}, [], CTX)
    assert model is not None
    entries = builder.logbook_entries(model, graph)

    names = {e.source_key["name"] for e in entries}
    assert names == {"Stripe"}  # only the Drittland service
    assert all(e.section == "SCC Anhang I.B Transferbeschreibung" for e in entries)


# -- ADR-001 guard end-to-end -------------------------------------------------

def test_builder_entries_pass_adr001_guard_through_write(tmp_path):
    """The canonical names builders emit must serialize without tripping the guard."""
    graph = {"services": [_stripe(integration_mode="merchant_side_possible")]}
    builder = AVVBuilder()
    model = builder.build(graph, {}, {}, [], CTX)
    entries = builder.logbook_entries(model, graph)

    out = write_logbook("6a3e5e15-aaaa-4bbb-8ccc-ddddeeeeffff", "AVV", entries, tmp_path)
    assert out.exists()
