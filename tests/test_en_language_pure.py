"""EN package guards (B-2, checklist rows 10/11) — language-pure render path.

Dry guards for the leak classes fixed on 2026-07-16. The render-level EN
linter lives in test_doc_linter.py (lang-parametrised); these tests pin the
SOURCES so a future edit cannot silently reopen a leak class.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_gap_hint_sites_carry_description_en():
    """L2: every GapHint creation site sets description_en — a new hint without
    the EN twin turns this red instead of leaking German into the EN warn-header."""
    src = (REPO / "src" / "scanner" / "gap_analyzer.py").read_text(encoding="utf-8")
    de_sites = len(re.findall(r"\bdescription=", src))
    en_sites = len(re.findall(r"\bdescription_en=", src))
    assert de_sites == en_sites, (
        f"description= sites ({de_sites}) != description_en= sites ({en_sites}) — "
        "add the English twin (B-2/L2)"
    )
    assert de_sites >= 26  # regression floor: the 2026-07-16 inventory


def test_gap_hint_sites_carry_fix_label_and_gap_reason_en():
    """Scan-report EN close-out: every GapHint creation site sets fix_label_en
    AND gap_reason_en — same guard pattern as description_en (B-2/L2). A new
    hint without the twins turns this red instead of leaking German into the
    EN scan report (or English into the DE one)."""
    src = (REPO / "src" / "scanner" / "gap_analyzer.py").read_text(encoding="utf-8")
    label_de = len(re.findall(r"\bfix_label=", src))
    label_en = len(re.findall(r"\bfix_label_en=", src))
    reason_de = len(re.findall(r"\bgap_reason=", src))
    reason_en = len(re.findall(r"\bgap_reason_en=", src))
    assert label_de == label_en, (
        f"fix_label= sites ({label_de}) != fix_label_en= sites ({label_en})"
    )
    assert reason_de == reason_en, (
        f"gap_reason= sites ({reason_de}) != gap_reason_en= sites ({reason_en})"
    )
    assert label_de >= 26  # regression floor: the 2026-07-28 inventory


def test_scan_report_builder_label_dicts_cover_same_keys():
    """Scan-report EN close-out: the EN twin dicts cover every key of the DE
    dicts (L3/L6 pattern) — a new label without its twin turns this red."""
    import sys
    sys.path.insert(0, str(REPO))
    from src.documents.builders.scan_report_builder import (
        _DOC_LABELS, _DOC_LABELS_EN,
        _RISK_DESCRIPTIONS, _RISK_DESCRIPTIONS_EN,
        _SIGNAL_LABELS, _SIGNAL_LABELS_EN,
        _USECASE_LABELS, _USECASE_LABELS_EN,
    )
    assert set(_DOC_LABELS) == set(_DOC_LABELS_EN)
    assert set(_RISK_DESCRIPTIONS) == set(_RISK_DESCRIPTIONS_EN)
    assert set(_SIGNAL_LABELS) == set(_SIGNAL_LABELS_EN)
    assert set(_USECASE_LABELS) == set(_USECASE_LABELS_EN)
    assert all(v.strip() for v in _DOC_LABELS_EN.values())
    assert all(v.strip() for v in _RISK_DESCRIPTIONS_EN.values())
    assert all(v.strip() for v in _SIGNAL_LABELS_EN.values())


def test_ebene0_usecase_dicts_cover_same_doc_types():
    """L6: the EN dict must cover every doc type the DE dict covers."""
    import sys
    sys.path.insert(0, str(REPO))
    from src.agents.document_architect import _EBENE0_USECASE, _EBENE0_USECASE_EN
    assert set(_EBENE0_USECASE) == set(_EBENE0_USECASE_EN)
    assert all(v.strip() for v in _EBENE0_USECASE_EN.values())


def test_ai_purpose_dicts_cover_same_categories():
    """L3: EN purpose map covers every category of the DE map."""
    import sys
    sys.path.insert(0, str(REPO))
    from src.documents.builders.ki_policy_builder import (
        _AI_PURPOSE_BY_CATEGORY, _AI_PURPOSE_BY_CATEGORY_EN,
    )
    assert set(_AI_PURPOSE_BY_CATEGORY) == set(_AI_PURPOSE_BY_CATEGORY_EN)


def test_service_en_descriptor_table_shape():
    """L8: the descriptor table is well-formed and chain-registered — no dupes,
    every entry carries data_categories_en, module runs in `--module all`."""
    import sys
    sys.path.insert(0, str(REPO / "scripts"))
    from seed_both import SERVICE_EN_DESCRIPTORS, MODULES
    names = [n for n, _p, _c in SERVICE_EN_DESCRIPTORS]
    assert len(names) == len(set(names)), "duplicate service in SERVICE_EN_DESCRIPTORS"
    assert len(names) >= 50  # regression floor: the 2026-07-16 export inventory
    assert all(c.strip() for _n, _p, c in SERVICE_EN_DESCRIPTORS)
    assert "service_en_descriptors" in MODULES
    src = (REPO / "scripts" / "seed_both.py").read_text(encoding="utf-8")
    assert len(re.findall(r'"service_en_descriptors"', src)) >= 2, "missing from --module all chain"


def test_psp_roles_tuples_carry_role_source_en():
    """L9: every PSP_ROLES tuple has the 9-field shape incl. role_source_en."""
    import sys
    sys.path.insert(0, str(REPO / "scripts"))
    from seed_both import PSP_ROLES
    for t in PSP_ROLES:
        assert len(t) == 9, f"PSP_ROLES tuple for {t[0]} lacks role_source_en"
        assert t[4], f"empty role_source_en for {t[0]}"


def test_render_fallback_stays_de_when_doc_language_absent():
    """The 'no silent switch' guard (2026-07-28): NEW projects default to EN
    (setup form + DB column default), but a config WITHOUT doc_language must
    still render German. Existing projects that never chose a language keep
    their documents — the render-time fallback is a separate decision from the
    new-project default and must not be flipped along with it."""
    import sys
    sys.path.insert(0, str(REPO))
    src_files = list((REPO / "src" / "documents" / "builders").glob("*_builder.py"))
    src_files.append(REPO / "src" / "agents" / "document_architect.py")
    for f in src_files:
        text = f.read_text(encoding="utf-8")
        assert 'doc_language", "en"' not in text, (
            f"{f.name}: render fallback flipped to EN — existing projects "
            "without a stored doc_language would silently switch language"
        )
        assert 'doc_language") or "en"' not in text, f"{f.name}: same, or-form"

    # Behavioural probe on the builder that carries the most language logic.
    from src.documents.builders.tom_builder import TOMBuilder
    from src.documents.content_models import BuildContext
    ctx = BuildContext(run_id="langguard", generation_date="2026-07-28",
                       project_name="p")
    model = TOMBuilder().build({"controls": [], "services": []}, {}, {}, [], ctx)
    assert model.company.address == "(Adresse eintragen)", (
        "empty config must render the German placeholder — the render fallback "
        "is the existing-project path"
    )


def test_new_project_surfaces_default_to_en():
    """The other side of the separation: every NEW-project surface says EN."""
    setup = (REPO / "src" / "dashboard" / "app" / "setup" / "page.tsx").read_text(encoding="utf-8")
    assert setup.count("doc_language: 'en'") == 2, (
        "setup form must default to EN in both places (initial state + example app)"
    )
    # value assignments only — the TS union type line `doc_language: 'de' | 'en'`
    # is a declaration, not a default.
    assert "doc_language: 'de'," not in setup, "a DE default survived in the setup form"
    schema = (REPO / "scripts" / "migrate.sql").read_text(encoding="utf-8")
    assert "doc_language    TEXT DEFAULT 'en'" in schema
    mig = REPO / "supabase" / "migrations" / "025_doc_language_default_en.sql"
    assert mig.exists() and "SET DEFAULT 'en'" in mig.read_text(encoding="utf-8")
