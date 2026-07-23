import dataclasses
import json
from pathlib import Path

import pytest

from src.documents.builders.avv_builder import AVVBuilder, AVVContentModel
from src.documents.content_models import BuildContext, GapMarker, ServiceSummaryRow
from src.scanner.gap_analyzer import GapHint
from tests.golden._helpers import _load_fixture, _load_golden

CTX = BuildContext(run_id="test00001", generation_date="2026-04-20", project_name="test")


# ---------------------------------------------------------------------------
# Unit tests — no fixtures needed
# ---------------------------------------------------------------------------

def test_avv_builder_non_eu_service_gdpr_status():
    graph = {"services": [{"name": "Stripe", "country": "USA", "gdpr_adequate": False,
                           "dpa_required": True, "dpa_url": None}]}
    model = AVVBuilder().build(graph, {}, {}, [], CTX)
    assert model.services_summary[0].gdpr_status == "SCC erforderlich"


def test_avv_builder_eu_service_gdpr_status():
    graph = {"services": [{"name": "Hetzner", "country": "Germany", "gdpr_adequate": True,
                           "dpa_required": False, "dpa_url": "https://hetzner.de/dpa"}]}
    model = AVVBuilder().build(graph, {}, {}, [], CTX)
    assert model.services_summary[0].gdpr_status == "EU/EEA"


def test_avv_builder_unknown_country_gdpr_status():
    graph = {"services": [{"name": "Acme", "country": None, "gdpr_adequate": None}]}
    model = AVVBuilder().build(graph, {}, {}, [], CTX)
    assert model.services_summary[0].gdpr_status == "ausstehend"


def test_avv_builder_warn_header_only_required_gaps():
    gaps = [
        GapHint(id="a", severity="REQUIRED", doc_affected=["AVV"], article="Art. 1",
                gap_reason="", fix_url="", fix_label="", priority=1, affected_docs=[]),
        GapHint(id="b", severity="RECOMMENDED", doc_affected=["AVV"], article="Art. 2",
                gap_reason="", fix_url="", fix_label="", priority=2, affected_docs=[]),
        GapHint(id="c", severity="REQUIRED", doc_affected=["TOM"], article="Art. 3",
                gap_reason="", fix_url="", fix_label="", priority=1, affected_docs=[]),
    ]
    model = AVVBuilder().build({}, {}, {}, gaps, CTX)
    assert len(model.warn_header_gaps) == 1
    assert model.warn_header_gaps[0].id == "a"


def test_avv_builder_no_transfer_block_when_all_eu():
    graph = {"services": [{"name": "Hetzner", "country": "Germany", "gdpr_adequate": True}]}
    model = AVVBuilder().build(graph, {}, {}, [], CTX)
    assert model.transfer_block is None


def test_avv_builder_transfer_block_requires_mechanism():
    # non-EU services but no transfer_mechanism in docs_required → no block
    graph = {
        "services": [{"name": "Stripe", "country": "USA", "gdpr_adequate": False}],
        "docs_required": [],
    }
    model = AVVBuilder().build(graph, {}, {}, [], CTX)
    assert model.transfer_block is None


def test_avv_builder_transfer_block_set_when_non_eu_and_mechanism():
    graph = {
        "services": [{"name": "Stripe", "country": "USA", "gdpr_adequate": False}],
        "docs_required": [{"transfer_mechanism": "SCCs"}],
    }
    model = AVVBuilder().build(graph, {}, {}, [], CTX)
    assert model.transfer_block is not None
    assert model.transfer_block.mechanism == "SCCs"
    assert model.transfer_block.affected_service_count == 1


def test_avv_builder_instructing_persons_gap_marker_when_empty():
    model = AVVBuilder().build({}, {}, {}, [], CTX)
    assert isinstance(model.instructing_persons, GapMarker)
    assert model.instructing_persons.gap_id == "avv_instructing_persons_missing"


def test_avv_builder_instructing_persons_list_when_configured():
    config = {"instructing_persons": [{"name": "Misty Knight", "title": "CEO"}]}
    model = AVVBuilder().build({}, {}, config, [], CTX)
    assert isinstance(model.instructing_persons, list)
    assert len(model.instructing_persons) == 1


def test_avv_builder_deletion_periods_from_graph_services():
    """ADR-129 PR 15 (audit K24/F5): EVERY service appears in § 7 — a missing
    period stays None and renders a visible gap marker, never a silent drop."""
    graph = {"services": [
        {"name": "Stripe", "deletion_period": "7 Jahre"},
        {"name": "Redis", "deletion_period": None},
    ]}
    model = AVVBuilder().build(graph, {}, {}, [], CTX)
    assert len(model.deletion_periods) == 2
    by_name = {r.service: r.period for r in model.deletion_periods}
    assert by_name["Stripe"] == "7 Jahre"
    assert by_name["Redis"] is None


def test_avv_builder_owner_retention_rows_rendered_as_is():
    """ADR-129 PR 15: retention_policies rows ride along via config, no service mapping."""
    config = {"_retention_policies": [
        {"category": "invoices", "duration_days": 3650, "duration_raw": None, "source": "setup"},
        {"category": "logs", "duration_days": None, "duration_raw": "90 Tage", "source": "code"},
        {"category": "empty", "duration_days": None, "duration_raw": None, "source": "setup"},
    ]}
    model = AVVBuilder().build({}, {}, config, [], CTX)
    rows = {r.category: (r.duration, r.source) for r in model.owner_retention}
    assert rows["invoices"] == ("3650 Tage", "setup")
    assert rows["logs"] == ("90 Tage", "code")
    assert "empty" not in rows   # no duration at all → skipped, not an empty row


def test_avv_builder_returns_avvcontent_model():
    model = AVVBuilder().build({}, {}, {}, [], CTX)
    assert isinstance(model, AVVContentModel)


# ---------------------------------------------------------------------------
# Dedup tests
# ---------------------------------------------------------------------------

def test_avv_split_and_dedup_list_input():
    """_split_and_dedup must handle list[str] input without AttributeError (ADR-100 fix)."""
    from src.documents.builders.avv_builder import _split_and_dedup
    result = _split_and_dedup([["customers", "end_users"], ["end_users", "employees"]])
    assert result == ["customers", "employees", "end_users"]


def test_avv_split_and_dedup_mixed_str_and_list():
    """_split_and_dedup must handle mixed str and list[str] inputs."""
    from src.documents.builders.avv_builder import _split_and_dedup
    result = _split_and_dedup(["customers, end_users", ["employees"]])
    assert "customers" in result
    assert "end_users" in result
    assert "employees" in result


def test_avv_builder_list_data_subjects_not_gap_marker():
    """Services with list[str] data_subjects (ADR-100 format) must yield rendered DE str, not GapMarker."""
    graph = {"services": [
        {"data_subjects": ["customers", "end_users"]},
        {"data_subjects": ["employees"]},
    ]}
    model = AVVBuilder().build(graph, {}, {}, [], CTX)
    assert isinstance(model.data_subjects, str)
    assert "Kunden" in model.data_subjects


def test_avv_builder_list_data_subjects_dedup():
    """list[str] data_subjects from multiple services must dedup and render to DE correctly."""
    graph = {"services": [
        {"data_subjects": ["customers", "end_users"]},
        {"data_subjects": ["customers", "website_visitors"]},
    ]}
    model = AVVBuilder().build(graph, {}, {}, [], CTX)
    items = [i.strip() for i in model.data_subjects.split(",")]
    assert items.count("Kunden") == 1
    assert len(items) == 3


def test_avv_builder_dedups_comma_separated_data_subjects():
    """Services with overlapping comma-separated data_subjects must dedup on individual items."""
    graph = {"services": [
        {"data_subjects": "Endnutzer der Anwendung, registrierte Nutzer"},
        {"data_subjects": "Endnutzer der Anwendung, Entwickler"},
        {"data_subjects": "Endnutzer der Anwendung (indirekt)"},
    ]}
    model = AVVBuilder().build(graph, {}, {}, [], CTX)
    assert isinstance(model.data_subjects, str)
    items = [i.strip() for i in model.data_subjects.split(",")]
    assert items.count("Endnutzer der Anwendung") == 1
    assert "registrierte Nutzer" in items
    assert "Entwickler" in items
    assert "Endnutzer der Anwendung (indirekt)" in items


def test_avv_builder_dedups_case_insensitive():
    """Case-insensitive dedup: same item with different casing appears once, first-seen casing kept."""
    graph = {"services": [
        {"data_categories": "E-Mail-Adressen, Logs"},
        {"data_categories": "e-mail-adressen, Metadaten"},
    ]}
    model = AVVBuilder().build(graph, {}, {}, [], CTX)
    lowered = [c.lower() for c in model.data_categories]
    assert lowered.count("e-mail-adressen") == 1


# ---------------------------------------------------------------------------
# Golden-file test — requires rand-industries fixtures + golden baseline
# ---------------------------------------------------------------------------

def test_avv_content_model_matches_golden():
    graph = _load_fixture("rand_industries_graph.json")
    config = _load_fixture("rand_industries_config.json")
    gaps_raw = _load_fixture("rand_industries_gaps.json")
    gap_hints = [GapHint(**g) for g in gaps_raw]

    ctx = BuildContext(run_id="0158d042", generation_date="2026-04-20",
                       project_name="rand-industries")
    model = AVVBuilder().build(graph, {}, config, gap_hints, ctx)

    expected = _load_golden("rand_industries_avv_content_model.json")
    assert dataclasses.asdict(model) == expected


def test_avv_psp_role_controller_and_special_case():
    """ADR-115 A1: controller renders the EDPB role; special_case renders an
    honest review-needed line (carrying the seeded reasoning), not empty and not
    the generic 'Pflichtangabe fehlt'. Non-PSP services carry no role line."""
    graph = {"services": [
        {"name": "Stripe", "category": "payment", "gdpr_adequate": True,
         "acts_as_role": "controller",
         "acts_as_role_source": "EDPB 07/2020 Rn. 26 + Rn. 82"},
        {"name": "Klarna", "category": "payment", "gdpr_adequate": True,
         "acts_as_role": "special_case",
         "acts_as_role_source": "Klarna: BNPL + Art. 22 — gesonderte Prüfung"},
        {"name": "Redis", "category": "cache_db", "gdpr_adequate": True},
    ]}
    model = AVVBuilder().build(graph, {}, {}, [], CTX)
    by = {r.service_name: r for r in model.psp_roles}
    assert set(by) == {"Stripe", "Klarna"}  # Redis (no ACTS_AS role) excluded
    assert by["Stripe"].role == "controller"
    assert by["Stripe"].role_label == "Verantwortlicher"
    assert "EDPB" in by["Stripe"].role_source
    assert by["Klarna"].role == "special_case"
    assert by["Klarna"].role_label is None
    assert by["Klarna"].role_source  # honest reasoning, never empty


# ---------------------------------------------------------------------------
# PR 1 — Stripe correctness: § 1 table must not contradict § 1.1
# ---------------------------------------------------------------------------

def test_avv_controller_psp_carries_no_avv_obligation():
    """ADR-115 A1: a controller PSP gets avv_required=False and carries its role;
    dpa_required stays untouched. A payment service without a seeded role stays AV."""
    graph = {"services": [
        {"name": "Stripe", "country": "USA", "gdpr_adequate": False,
         "dpa_required": True, "acts_as_role": "controller"},
        {"name": "Braintree", "country": "USA", "gdpr_adequate": False,
         "dpa_required": True},
    ]}
    model = AVVBuilder().build(graph, {}, {}, [], CTX)
    by = {r.name: r for r in model.services_summary}
    assert by["Stripe"].avv_required is False
    assert by["Stripe"].acts_as_role == "controller"
    # generic property untouched (only the rendered flag is derived from the role)
    assert by["Braintree"].avv_required is True
    assert by["Braintree"].acts_as_role is None


def test_avv_special_case_psp_keeps_dpa_required_flag():
    """special_case (PayPal/Klarna) is out of the narrow controller scope: its
    avv_required still follows dpa_required (the honest review marker lives in § 1.1)."""
    graph = {"services": [
        {"name": "Klarna", "country": "Sweden", "gdpr_adequate": True,
         "dpa_required": True, "acts_as_role": "special_case"},
    ]}
    model = AVVBuilder().build(graph, {}, {}, [], CTX)
    assert model.services_summary[0].avv_required is True


def test_avv_render_controller_table_cell_cross_references_section_1_1():
    """The rendered § 1 table must show the cross-reference for a controller PSP,
    never an AVV-Pflicht ✅ that contradicts § 1.1."""
    from jinja2 import Environment, FileSystemLoader
    from pathlib import Path

    templates = Path(__file__).parents[1] / "src" / "templates"
    env = Environment(
        loader=FileSystemLoader([str(templates / "de"), str(templates)]),
        autoescape=False, trim_blocks=True, lstrip_blocks=True,
    )
    env.globals["inline_gap_marker"] = lambda gap_id: f"🔴 [{gap_id}]"

    graph = {"services": [
        {"name": "Stripe", "country": "USA", "gdpr_adequate": False,
         "dpa_required": True, "acts_as_role": "controller",
         "acts_as_role_source": "EDPB 07/2020 Rn. 26"},
    ]}
    model = AVVBuilder().build(graph, {}, {}, [], CTX)
    out = env.get_template("avv.md.j2").render(
        model=dataclasses.asdict(model),
        project_name="t", run_id="test0001", generation_date="2026-04-20",
        company_name="T", legal_form="", address="", zip_code="", city="",
        zip_city="", contact_email="", website_url="", responsible_name="",
        responsible_title="", fields={}, instructing_persons=[],
        transfer_mechanism=None, deletion_periods=[],
    )
    # the AVV-Pflicht cell for Stripe carries the cross-reference, not a ✅
    stripe_row = next(l for l in out.splitlines() if l.startswith("| Stripe "))
    assert "eigenverantwortlich (§ 1.1)" in stripe_row
    assert "✅" not in stripe_row
