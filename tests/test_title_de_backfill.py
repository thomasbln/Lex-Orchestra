"""F22 guard tests (Graph-Diff 2026-07-15, checklist row 46).

TITLE_FALLBACK["de"] reads ONLY title_de — the seed must therefore cover every
non-BSI control (BSI copies its German legacy `title` at seed time, the six
adr066 controls own their title_de). These tests pin the durable seed table so
the fix cannot silently regress: dropping an entry, a framework, or the module
from the seed chain turns them red (mutation-proven pattern, Nachschlag N4).

Dry tests — no database connection.
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from seed_both import MODULES, TITLE_DE_BACKFILL  # noqa: E402

EXPECTED_PER_FRAMEWORK = {
    "NIST_CSF_2": 12,
    "OWASP_API_Top10": 10,
    "OWASP_LLM_Top10": 10,
    "OWASP_Top10": 10,
}


def test_table_covers_all_non_bsi_controls():
    """42 entries: exactly the NIST + 3x OWASP control sets."""
    assert len(TITLE_DE_BACKFILL) == 42
    counts: dict[str, int] = {}
    for fw, _cid, _t in TITLE_DE_BACKFILL:
        counts[fw] = counts.get(fw, 0) + 1
    assert counts == EXPECTED_PER_FRAMEWORK


def test_keys_unique_and_titles_non_empty():
    keys = [(fw, cid) for fw, cid, _t in TITLE_DE_BACKFILL]
    assert len(keys) == len(set(keys)), "duplicate (framework, id) in TITLE_DE_BACKFILL"
    assert all(t.strip() for _fw, _cid, t in TITLE_DE_BACKFILL), "empty title_de value"


def test_module_registered_and_in_full_chain():
    """The module must exist AND run in `--module all` — a registry entry alone
    would seed nothing on a fresh install."""
    assert "title_de_backfill" in MODULES
    source = (REPO / "scripts" / "seed_both.py").read_text(encoding="utf-8")
    # once in MODULES, once in the "all" chain
    assert len(re.findall(r'"title_de_backfill"', source)) >= 2, (
        "title_de_backfill missing from the --module all chain"
    )


def test_f23a_edges_in_seed_tables():
    """Row 47a: the six PR-8-Fix-A SUBJECT_TO_CONTROL edges are seed-durable."""
    from seed_both import BSI_UPGRADES, CATEGORY_CONTROLS

    triples = set(CATEGORY_CONTROLS)
    for cat, cid in [
        ("media_storage", "CON.3"),
        ("search_db", "CON.1"),
        ("search_db", "APP.3.1"),
        ("security", "CON.1"),
    ]:
        assert (cat, cid, "BSI_Grundschutz") in triples, f"missing {cat}->{cid}"

    upgrades = {cid: cats for cats, cid in BSI_UPGRADES}
    assert "sms" in upgrades["OPS.1.2.4"], "sms->OPS.1.2.4 missing"
    assert "cdn_security" in upgrades["OPS.1.1.5"], "cdn_security->OPS.1.1.5 missing"
