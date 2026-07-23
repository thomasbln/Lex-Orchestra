"""Resurrection guards for the seed layer files (ADR-130 D2 + build-time fixes).

Three frameworks were deliberately removed from the default graph — ISO 27001
(ADR-120, BYOS), BSI C5 (ADR-118), AIC4 (ADR-126 Phase 0.5). A seed layer that
re-creates them silently reverts an accepted ADR. Likewise, `Service.legal_basis`
was retired in ADR-100 PR 7 (authoritative source: SUBJECT_TO_CONTROL[legal_basis]),
and the TTDSG→TDDDG law rename (14b/14d) must not be undone by 10_de re-MERGEing
the old name.

All tests are dry — file reads only, no DB.
"""

import re
from pathlib import Path

import pytest
import yaml

from scripts.seed_both import _split_statements


def _without_comments(text: str) -> str:
    """Cypher text with // comment lines removed — guards ban identifiers in
    statements, not prose in comments (tombstones may name what they replaced)."""
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("//")
    )

LAYERS = Path(__file__).parents[1] / "src" / "graph" / "layers"
FRAMEWORKS = LAYERS / "00_global" / "00_frameworks.cypher"
SERVICES_GLOBAL = LAYERS / "00_global" / "00_services_global.cypher"
DE = LAYERS / "10_jurisdiction" / "eu" / "10_de.cypher"
BYOS_ISO = LAYERS / "byos" / "iso27001.cypher"
SEED_CONFIG = Path(__file__).parents[1] / "src" / "graph" / "seed_config.yaml"


# ── D2: ISO leaves the default frameworks layer ───────────────────────────────

def test_frameworks_layer_contains_no_iso_identifier():
    """No ISO_27001 statement may remain in the default frameworks layer.

    The guard bans the machine identifier (framework key), not prose — the
    tombstone comments referencing the BYOS file are allowed.
    """
    assert "ISO_27001" not in FRAMEWORKS.read_text(encoding="utf-8")


def test_byos_iso_file_carries_the_moved_content():
    if not BYOS_ISO.exists():
        pytest.skip("BYOS ISO copy not present — valid state in the public export tree (ADR-120: licensed standards are not shipped)")
    text = BYOS_ISO.read_text(encoding="utf-8")
    stmts = _split_statements(text)
    # _split_statements keeps leading section comments inside a statement block,
    # so membership (not startswith) is the correct predicate.
    control_merges = [s for s in stmts if 'MERGE (c:Control {framework: "ISO_27001"' in s]
    assert len(control_merges) == 13, "Block G is 13 Annex-A controls"
    assert len(stmts) == 17, "13 controls + 2 edge statements + 2 normalizations"
    # BYOS file must never MERGE into another framework
    assert "BSI_Grundschutz" not in text
    assert "NIST_CSF_2" not in text


def test_byos_file_is_self_declared_non_manifest():
    """The header must carry the manifest ban — it is the human-facing guard."""
    if not BYOS_ISO.exists():
        pytest.skip("BYOS ISO copy not present — valid state in the public export tree (ADR-120: licensed standards are not shipped)")
    header = BYOS_ISO.read_text(encoding="utf-8")[:1200]
    assert "NEVER" in header and "manifest" in header
    assert "ADR-120" in header


# ── ADR-100 PR 7: Service.legal_basis stays dead ──────────────────────────────

def test_services_global_never_sets_service_legal_basis():
    """`s.legal_basis` was removed from the graph in ADR-100 PR 7 — a re-seed
    writing it is drift by design. TransferMechanism `t.legal_basis` is a
    different, live property and stays."""
    text = SERVICES_GLOBAL.read_text(encoding="utf-8")
    assert re.search(r"s\.legal_basis\s*=", text) is None
    # the allowed property is still there (guard against over-deletion)
    assert re.search(r"t\.legal_basis\s*=", text) is not None


# ── TTDSG→TDDDG rename durability ─────────────────────────────────────────────

def test_10_de_merges_tdddg_not_ttdsg():
    """10_de re-MERGEing TTDSG would resurrect the pre-rename node next to the
    renamed TDDDG one (14b/14d rename legacy nodes; they keep matching TTDSG
    on purpose — only 10_de must stop creating it)."""
    text = _without_comments(DE.read_text(encoding="utf-8"))
    assert "TTDSG" not in text
    assert 'MERGE (l:Law {name: "TDDDG", article: "25"})' in text


def test_frameworks_update_block_targets_tdddg():
    assert 'MATCH (l:Law {name: "TTDSG"})' not in FRAMEWORKS.read_text(encoding="utf-8")


# ── D6: constraints layer (Phase 0) ───────────────────────────────────────────

CONSTRAINTS = LAYERS / "00_global" / "00_constraints.cypher"

EXPECTED_CONSTRAINT_KEYS = {
    # name → (label, properties) — each mirrors its seed MERGE key
    "service_name_unique": ("Service", "s.name IS UNIQUE"),
    "law_name_article_unique": ("Law", "(l.name, l.article) IS UNIQUE"),
    "risklevel_level_unique": ("RiskLevel", "rl.level IS UNIQUE"),
    "control_framework_id_unique": ("Control", "(c.framework, c.id) IS UNIQUE"),
    "measure_id_unique": ("Measure", "m.id IS UNIQUE"),
    "servicecategory_name_unique": ("ServiceCategory", "sc.name IS UNIQUE"),
    "usecase_type_unique": ("UseCase", "u.type IS UNIQUE"),
    "documenttype_type_unique": ("DocumentType", "d.type IS UNIQUE"),
    "requirement_id_framework_unique": ("Requirement", "(r.id, r.framework) IS UNIQUE"),
}


def test_constraints_layer_has_exactly_nine_idempotent_constraints():
    """ADR-130 D6/D7: nine constraints, all IF NOT EXISTS, nothing else."""
    text = CONSTRAINTS.read_text(encoding="utf-8")
    stmts = _split_statements(text)
    assert len(stmts) == 9
    for s in stmts:
        body = _without_comments(s)
        assert "CREATE CONSTRAINT" in body and "IF NOT EXISTS" in body
        assert "MERGE" not in body and "DELETE" not in body


def test_constraints_cover_every_seed_merge_key():
    text = CONSTRAINTS.read_text(encoding="utf-8")
    for name, (label, require) in EXPECTED_CONSTRAINT_KEYS.items():
        assert name in text, f"constraint {name} missing"
        assert f":{label})" in text
        assert require in text, f"{name}: expected key shape '{require}'"


# ── §4.1: seed tables must not write validator-red Service values ────────────

def test_service_data_subjects_seed_values_are_allowlisted():
    """pr_c1_5_subjects MATCH-SETs Service.data_subjects unconditionally on every
    full seed. German values here ("Endnutzer", …) made every seed run re-write
    §4.1-red state and would fail the D7 cleanroom (found 2026-07-14).
    ProcessingActivity.typical_data_subjects is DE content by design and exempt.
    """
    from scripts.seed_both import ALLOWED_DATA_SUBJECTS, SERVICE_DATA_SUBJECTS

    for name, subjects in SERVICE_DATA_SUBJECTS:
        unknown = set(subjects) - ALLOWED_DATA_SUBJECTS
        assert not unknown, f"{name}: non-allowlist data_subjects {sorted(unknown)}"


# ── seed_config durability convention ─────────────────────────────────────────

def test_seed_config_active_frameworks_exclude_deseeded():
    cfg = yaml.safe_load(SEED_CONFIG.read_text(encoding="utf-8"))
    active = cfg.get("frameworks") or []
    for banned in ("iso27001", "bsi_c5", "aic4"):
        assert banned not in active, f"{banned} was deseeded — resurrection ban"
    assert "owasp" in active
