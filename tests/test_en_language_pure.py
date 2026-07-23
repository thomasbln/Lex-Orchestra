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
