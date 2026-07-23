"""ADR-076: Three-layer generation — reconciliation + marker macro rendering.
ADR-098 PR 1: inline_gap_marker + warn-header + template marker integration.
"""
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

from src.agents.document_architect import (
    FieldSource,
    TOM_SECTION_ORDER,
    _field_with_source,
    _merge_sources,
)


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "src" / "templates"

# Universal minimal model satisfying model.* access across all 8 templates.
# Lists must be present (empty) so template for-loops don't raise UndefinedError.
_MINIMAL_MODEL: dict = {
    # AVV
    "services_summary": [],
    "data_categories": [],
    "data_subjects": None,
    "special_categories": False,
    "service_data_blocks": [],  # ADR-106 PR A1
    # DSFA
    "triggered_by_high_risk_usecase": False,
    "ai_usecase": None,
    "risks": {"rag_over_pii": False, "pii_in_llm_context": False, "pii_in_logs": False,
              "no_ai_audit_trail": False, "consent_management": False},
    "zweck": None,
    "rechtsgrundlage": None,
    "pii_services": [],
    "ai_services": [],
    "is_high_risk": False,
    "step2": {"notwendigkeit": "—", "verhaeltnismaessigkeit": "—",
              "datenminimierung": "—"},                                # ADR-106 PR A4
    "step4": [],                                                       # ADR-106 PR A4
    "step5": {"konsultation_erforderlich": False, "begruendung": "—"},  # ADR-106 PR A5
    # SCC
    "services_with_transfer": [],
    # KI System
    "service": {
        "name": "—", "country": None, "processing_purpose": None,
        "risk_level": None, "data_categories": None, "deletion_period": None,
        "dpa_url": None, "gdpr_adequate": True,
    },
    "implemented_measures": [],  # ADR-106 PR A6
    # AI Act Manifest
    "risk_levels": [],
    "deployer_usecase": None,
    "ai_usecase_type": None,
    "indicated_usecases": [],
    "all_usecases": [],
    "art4_effective_date": "2025-02-02",
    "has_audit_trail_gap": False,
    # VVT
    "activities": [],
    "scc_doc_ref": None,
    "non_eu_count": 0,
    # TOM
    "curated_controls": [],
    "sdm_defaults_by_section": {},  # ADR-106 PR D7
    # ADR-106 PR C5 — empty footer when no graph client available
    "bfdi_citations": [],
    # ADR-106 PR D6 — empty when no damage_scenarios triggered
    "damage_scenarios": [],
}


# ── _merge_sources reconciliation matrix ───────────────────────────────────

def test_merge_both_agree_code_wins_silent():
    code  = _field_with_source("bcrypt", FieldSource.CODE, evidence="pkg.json:23")
    setup = _field_with_source("bcrypt", FieldSource.Q)
    winner, warnings = _merge_sources(code, setup, "password_hashing")
    assert winner["source"] == "CODE"
    assert winner["evidence"] == "pkg.json:23"
    assert warnings == []


def test_merge_divergent_setup_wins_with_warning():
    code  = _field_with_source("Stripe", FieldSource.CODE)
    setup = _field_with_source("PayPal", FieldSource.Q)
    winner, warnings = _merge_sources(code, setup, "payment_provider")
    assert winner["value"] == "PayPal"
    assert winner["source"] == "Q"
    assert len(warnings) == 1
    w = warnings[0]
    assert w["severity"] == "warning"
    assert w["field"] == "payment_provider"
    assert w["code_value"] == "Stripe"
    assert w["setup_value"] == "PayPal"
    assert w["source_stage"] == "three_layer_reconcile"


def test_merge_only_setup_no_warning():
    setup = _field_with_source("thomas@example.com", FieldSource.Q)
    winner, warnings = _merge_sources(None, setup, "dpo_email")
    assert winner["source"] == "Q"
    assert warnings == []


def test_merge_only_code_no_warning():
    code = _field_with_source(True, FieldSource.CODE, evidence="nginx.conf:5")
    winner, warnings = _merge_sources(code, None, "tls_enabled")
    assert winner["source"] == "CODE"
    assert warnings == []


def test_merge_nothing_returns_missing_sentinel():
    winner, warnings = _merge_sources(None, None, "training_frequency")
    assert winner["source"] == "MISSING"
    assert winner["value"] is None
    assert warnings == []


# ── _marker.md.j2 macro rendering ─────────────────────────────────────────

@pytest.fixture
def jinja_env():
    # Mirror the DocumentOrchestrator Environment config (trim_blocks + lstrip_blocks)
    # so template whitespace behaves identically to production rendering.
    env = Environment(
        loader=FileSystemLoader([str(TEMPLATES_DIR / "de"), str(TEMPLATES_DIR)]),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    # Stubs for Jinja globals registered by DocumentOrchestrator.__init__.
    # Tests use a raw Environment — register minimal stubs so templates
    # that call these globals don't raise UndefinedError.
    env.globals["has_signal"] = lambda name, min_confidence=0.5: False
    env.globals["inline_gap_marker"] = lambda gap_id: f"🔴 {gap_id}"
    # de_date filter — mirrors document_architect's production registration (same
    # ISO→DD.MM.YYYY, defensive passthrough) so templates using `| de_date` (e.g.
    # ai_act_manifest.md.j2 art4 effective date) render exactly as in prod.
    def _de_date(value):
        if not value:
            return value
        try:
            from datetime import date
            return date.fromisoformat(str(value)).strftime("%d.%m.%Y")
        except (ValueError, TypeError):
            return value
    env.filters["de_date"] = _de_date
    return env


def _render(env, field, label, **ctx):
    tmpl = env.from_string(
        "{% import '_marker.md.j2' as m with context %}{{ m.render(f, label) }}"
    )
    return tmpl.render(
        f=field, label=label,
        lang=ctx.get("lang", "de"),
        run_id=ctx.get("run_id", "a3f2e1d4"),
        generation_date=ctx.get("generation_date", "2026-04-16"),
        setup_revision_short=ctx.get("setup_revision_short", "rev-07"),
        setup_revision_date=ctx.get("setup_revision_date", "2026-04-12"),
        setup_author=ctx.get("setup_author", ""),
    )


def test_marker_code_renders_german_by_default(jinja_env):
    field = _field_with_source(True, FieldSource.CODE, evidence="nginx.conf:5")
    out = _render(jinja_env, field, "TLS")
    assert "✓" in out
    assert "Im gescannten Code/in der Konfiguration gefunden" in out
    assert "Scan-Run" in out
    assert "Nachweis" in out
    assert "nginx.conf:5" in out


# ── inferred marker (≈) — tool-derived value, conditional legend ──────────────

def _render_inferred(env, what, lang="de"):
    # ADR-076 addendum: the inferred (≈) glyph is rendered by inferred_mark(); its legend
    # entry now lives in the unified legend() macro, called with ["inferred"].
    tmpl = env.from_string(
        "{% import '_marker.md.j2' as m with context %}"
        "{% if what == 'mark' %}{{ m.inferred_mark() }}{% else %}{{ m.legend(['inferred']) }}{% endif %}"
    )
    return tmpl.render(what=what, lang=lang)


def test_inferred_mark_is_glyph(jinja_env):
    assert _render_inferred(jinja_env, "mark").strip() == "≈"


def test_inferred_legend_de_carries_key_wording(jinja_env):
    out = _render_inferred(jinja_env, "legend")
    assert "≈" in out
    assert "aus der Dienst-Kategorie abgeleitet" in out
    assert "kein Einzelnachweis" in out   # the key phrase: not project-evidenced
    assert "zu bestätigen" in out


def test_inferred_legend_en(jinja_env):
    out = _render_inferred(jinja_env, "legend", lang="en")
    assert "no project-specific evidence" in out
    assert "to be confirmed" in out


def test_marker_code_renders_english_when_lang_en(jinja_env):
    field = _field_with_source(True, FieldSource.CODE, evidence="nginx.conf:5")
    out = _render(jinja_env, field, "TLS", lang="en")
    assert "Found in the scanned code/configuration" in out
    assert "Evidence" in out
    assert "Aus Scan" not in out


def test_marker_q_renders_german_provided(jinja_env):
    field = _field_with_source("ACME GmbH", FieldSource.Q)
    out = _render(
        jinja_env, field, "Unternehmen",
        setup_revision_short="rev-07",
        setup_revision_date="2026-04-12",
        setup_author="thomas@example.com",
    )
    assert "◆" in out
    # ADR-076 addendum: header carries the SHORT label; full wording lives in the legend.
    assert "Von Ihnen angegeben" in out
    assert "Setup-Revision" in out
    assert "rev-07" in out
    # author suffix ("· <author>") removed from header — redundant


def test_marker_std_delegated_renders_german(jinja_env):
    field = {
        "value": {
            "provider":  "AWS",
            "region":    "eu-central-1",
            "soc2":      True,
            "iso27001":  True,
        },
        "source":     "STD_DELEGATED",
        "evidence":   None,
        "confidence": None,
    }
    out = _render(jinja_env, field, "Physische Zutrittskontrolle")
    assert "⊘" in out
    assert "nicht zu führen" in out
    assert "Anbieter: AWS" in out
    assert "eu-central-1" in out
    assert "SOC 2 Type II" in out
    assert "ISO 27001" in out


def test_marker_unknown_lang_falls_back_to_german(jinja_env):
    """Any non-de/en lang falls back to DE labels (safer default)."""
    field = _field_with_source(True, FieldSource.CODE)
    out = _render(jinja_env, field, "TLS", lang="fr")
    assert "Im gescannten Code/in der Konfiguration gefunden" in out


def test_marker_pure_std_renders_nothing(jinja_env):
    """Plain STD fields get no marker block — they are regular contract text."""
    field = _field_with_source("Weisungsgebunden", FieldSource.STD)
    out = _render(jinja_env, field, "Weisungsgebundenheit").strip()
    assert out == ""


# ── tom.md.j2 integration ──────────────────────────────────────────────────

def _tom_base_ctx():
    """Minimum context for tom.md.j2 to render without Jinja KeyError."""
    return {
        "lang":                    "de",
        "run_id":                  "a3f2e1d4-1111-2222-3333-444455556666",
        "generation_date":         "2026-04-16",
        "project_name":            "acme",
        "company_name":             "ACME GmbH",
        "legal_form":               "GmbH",
        "address":                  "Musterstraße 1",
        "zip_code":                 "10115",
        "city":                     "Berlin",
        "zip_city":                 "",
        "contact_email":            "hello@acme.test",
        "website_url":              "https://acme.test",
        "responsible_name":         "Max Muster",
        "responsible_title":        "CEO",
        "dpo_name":                 "",
        "dpo_email":                "",
        "register_court":           "",
        "register_number":          "",
        "setup_revision_short":     "",
        "setup_revision_date":      "",
        "setup_author":             "",
        "project":                  {"on_prem": False, "hosting_provider": None, "hosting_region": None},
        "fields":                   {},
        "tom_section_order":        TOM_SECTION_ORDER,
        "controls_by_section":      {},
        "priority_actions":         [],
        "active_risks":             [],
        "model":                    {"curated_controls": [], "sdm_defaults_by_section": {}},
    }


def test_tom_renders_without_setup_no_markers(jinja_env):
    """No setup → no evidence-marker blocks in output.

    ADR-102 (doc quality enforcement) removed the static
    'Hosting-Provider nicht konfiguriert' filler string; with no provider and
    not on-prem the hosting row now renders the '—' no-data convention and no
    delegation text.
    """
    tmpl = jinja_env.get_template("tom.md.j2")
    out = tmpl.render(**_tom_base_ctx())
    assert "✓" not in out
    assert "⊘" not in out
    assert "> ? " not in out
    # No hosting provider + not on-prem → no delegation, no removed static string
    assert "Delegiert an" not in out
    assert "Hosting-Provider nicht konfiguriert" not in out


def test_tom_renders_hosting_delegation_when_setup_present(jinja_env):
    """Cloud hosting with known provider → delegation row + customer_info marker."""
    ctx = _tom_base_ctx()
    ctx["project"] = {
        "on_prem": False, "hosting_provider": "AWS", "hosting_region": "eu-central-1"
    }
    ctx["setup_revision_short"] = "rev-07ab"
    ctx["setup_revision_date"] = "2026-04-12"
    ctx["setup_author"] = "thomas@example.com"
    ctx["fields"] = {
        "customer_info": _field_with_source("ACME GmbH", FieldSource.Q),
        "hosting_delegation": {
            "value": {"provider": "AWS", "region": "eu-central-1",
                      "soc2": True, "iso27001": True},
            "source": "STD_DELEGATED",
            "evidence": None,
            "confidence": None,
        },
    }
    tmpl = jinja_env.get_template("tom.md.j2")
    out = tmpl.render(**ctx)
    # Hosting delegation row in TOM table
    assert "Delegiert an AWS" in out
    assert "eu-central-1" in out
    assert "physische Kontrollen" in out
    # Customer-info marker block (Q source → ◆; short header label per ADR-076 addendum)
    assert "> ◆ " in out
    assert "Von Ihnen angegeben" in out
    assert "rev-07ab" in out


def test_tom_renders_on_prem_physical_questionnaire(jinja_env):
    """On-prem → no delegation marker, table shows in-house controls text."""
    ctx = _tom_base_ctx()
    ctx["project"] = {"on_prem": True, "hosting_provider": None, "hosting_region": None}
    ctx["fields"] = {
        "physical_access": _field_with_source(
            "on_premise_questionnaire_pending", FieldSource.Q
        ),
    }
    tmpl = jinja_env.get_template("tom.md.j2")
    out = tmpl.render(**ctx)
    assert "⊘" not in out               # no STD_DELEGATED marker for on-prem
    assert "Eigenes Rechenzentrum" in out  # current on-prem table cell text


# ── Remaining 7 templates — customer_info marker presence ──────────────────

def _template_base_ctx():
    """Full context for the 7 non-TOM templates — includes model + all required keys."""
    ctx = _tom_base_ctx()
    ctx.update({
        "services": [],
        "ai_usecase": None,
        "active_risk_ids": [],
        "gaps": [],
        "service": {
            "name": "Stripe", "country": "USA",
            "processing_purpose": "Payment", "risk_level": "limited",
        },
        "model": dict(_MINIMAL_MODEL),
    })
    return ctx


@pytest.mark.parametrize("template_name", [
    "avv.md.j2",
    "vvt.md.j2",
    "dsfa.md.j2",
    "scc.md.j2",
    "ki_policy.md.j2",
    "ki_system.md.j2",
    "ai_act_manifest.md.j2",
])
def test_remaining_templates_render_customer_info_marker(jinja_env, template_name):
    """Each template shows the ? customer-info marker when setup data exists."""
    ctx = _template_base_ctx()
    ctx["fields"] = {"customer_info": _field_with_source("ACME GmbH", FieldSource.Q)}
    ctx["setup_revision_short"] = "rev-01ab"
    ctx["setup_revision_date"] = "2026-04-16"
    ctx["setup_author"] = "thomas@example.com"
    out = jinja_env.get_template(template_name).render(**ctx)
    assert "> ◆ " in out, f"{template_name} missing customer_info marker block"
    assert "Von Ihnen angegeben" in out
    assert "rev-01ab" in out


# ── project_setups overrides project_config for overlapping fields ─────────

def test_setup_dpo_name_wins_over_empty_config():
    """setup.dpo_name wins when project_config.dpo_name is NULL (ADR-076 Layer 2)."""
    from src.agents.document_architect import DocumentOrchestrator

    da = DocumentOrchestrator.__new__(DocumentOrchestrator)

    da._load_project_setup = lambda pn: {
        "dpo_name": "Thomas Rehmer",
        "dpo_email": "thomas@example.com",
        "on_prem": False, "hosting_provider": None, "hosting_region": None,
        "current_revision_id": None, "revision_created_at": None, "revision_created_by": None,
    }
    da._load_hosting_provider = lambda name: None

    config = {
        "company_name": "ACME GmbH",
        "dpo_name":  None,
        "dpo_email": None,
        "contact_email": None,
    }
    ctx = da._common_config_context("acme", "run-1234", config)

    assert ctx["dpo_name"]  == "Thomas Rehmer"
    assert ctx["dpo_email"] == "thomas@example.com"
    assert ctx["contact_email"] == "(E-Mail eintragen)"


def test_config_dpo_wins_when_setup_empty():
    """If setup.dpo_name is empty but config.dpo_name is set, config wins."""
    from src.agents.document_architect import DocumentOrchestrator

    da = DocumentOrchestrator.__new__(DocumentOrchestrator)
    da._load_project_setup = lambda pn: {
        "dpo_name": None, "dpo_email": None,
        "on_prem": False, "hosting_provider": None, "hosting_region": None,
        "current_revision_id": None, "revision_created_at": None, "revision_created_by": None,
    }
    da._load_hosting_provider = lambda name: None

    ctx = da._common_config_context("acme", "r", {
        "company_name": "ACME", "dpo_name": "Jane Doe", "dpo_email": "jane@acme.test",
    })
    assert ctx["dpo_name"] == "Jane Doe"
    assert ctx["dpo_email"] == "jane@acme.test"


@pytest.mark.parametrize("template_name", [
    "avv.md.j2",
    "vvt.md.j2",
    "dsfa.md.j2",
    "scc.md.j2",
    "ki_policy.md.j2",
    "ki_system.md.j2",
    "ai_act_manifest.md.j2",
])
def test_remaining_templates_no_marker_without_setup(jinja_env, template_name):
    """No setup data → no ✓/?/⊘ marker blocks in output."""
    ctx = _template_base_ctx()
    # fields is empty by default (no customer_info) — no marker.render() calls
    out = jinja_env.get_template(template_name).render(**ctx)
    assert "> ? " not in out
    assert "> ✓" not in out
    assert "> ⊘" not in out
