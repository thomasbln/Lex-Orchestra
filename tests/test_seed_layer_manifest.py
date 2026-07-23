"""ADR-130 D1/D3 — layer manifest + runner wiring in seed_both.py.

All dry: mocked sessions, file reads, zero DB writes. The first real execution
of the full manifest is the D7 Fujitsu cleanroom — deliberately not a test.
"""

import pytest

from scripts.seed_both import (
    LAYERS_DIR,
    LAYERS_PHASE_0,
    LAYERS_PHASE_1,
    LAYERS_PHASE_3,
    _split_statements,
    apply_layer,
    run,
)

MANIFEST = LAYERS_PHASE_0 + LAYERS_PHASE_1 + LAYERS_PHASE_3


# ── fakes ─────────────────────────────────────────────────────────────────────

class FakeResult:
    def __init__(self):
        self.consumed = False

    def consume(self):
        self.consumed = True

    def __iter__(self):
        return iter([])


class FakeSession:
    """Records every executed statement; optionally explodes at one index."""

    def __init__(self, fail_at: int | None = None):
        self.statements: list[str] = []
        self.fail_at = fail_at

    def run(self, stmt, **params):
        self.statements.append(stmt)
        if self.fail_at is not None and len(self.statements) == self.fail_at:
            raise RuntimeError("syntax error (simulated)")
        return FakeResult()


# ── D1: the manifest is the resurrection gate ─────────────────────────────────

def test_manifest_never_lists_banned_sources():
    """ISO (ADR-120 BYOS), C5 (ADR-118), AIC4 (ADR-126 P0.5) are unlistable —
    and 14c stays out until Law.title_en has a consumer."""
    for rel in MANIFEST:
        low = rel.lower()
        assert "byos" not in low, f"BYOS layer in manifest: {rel}"
        assert "20_bsi_c5" not in low, f"C5 resurrection: {rel}"
        assert "20_aic4" not in low, f"AIC4 resurrection: {rel}"
        assert "14c" not in low, f"14c has no consumer yet: {rel}"


def test_manifest_paths_exist_and_split_cleanly():
    for rel in set(MANIFEST):
        path = LAYERS_DIR / rel
        assert path.is_file(), f"manifest entry missing on disk: {rel}"
        assert len(_split_statements(path.read_text(encoding="utf-8"))) > 0


def test_manifest_matches_the_normative_adr130_order():
    """Literal pin of the ADR-130 execution order — a new layer must be added
    HERE consciously, with its phase position (no glob sweeps it in)."""
    assert LAYERS_PHASE_0 == ["00_global/00_constraints.cypher"]
    assert LAYERS_PHASE_1 == [
        "00_global/00_services_global.cypher",
        "10_jurisdiction/eu/10_eu_primary.cypher",
        "10_jurisdiction/eu/10_de.cypher",
        "00_global/00_frameworks.cypher",
        "00_global/00_services_global.cypher",  # 2nd pass resolves the cycle
    ]
    assert LAYERS_PHASE_3 == [
        "00_global/00_tom_defaults.cypher",
        "00_global/01_bsi_basis_requirements_en.cypher",
        "10_jurisdiction/eu/11_data_subjects_normalize.cypher",
        "10_jurisdiction/eu/12_legal_basis_backfill.cypher",
        "10_jurisdiction/eu/14a_law_dedup.cypher",
        "10_jurisdiction/eu/14b_law_minimal_metadata.cypher",
        "10_jurisdiction/eu/14d_law_cellar_sync.cypher",
    ]


EXPECTED_STATEMENT_COUNTS = {
    # Drift guard: pinned from the ADR-130 read-of-truth inventory (post-D2
    # split). A conscious layer edit updates this table in the same commit.
    "00_global/00_constraints.cypher": 9,
    "00_global/00_services_global.cypher": 186,
    # 124 since 2026-07-19: +1 stale-Limited-edge cleanup for the re-classified
    # emotion_recognition_system UseCase (Annex III 1(c) High, Art. 5(1)(f)).
    "10_jurisdiction/eu/10_eu_primary.cypher": 124,
    "10_jurisdiction/eu/10_de.cypher": 26,
    "00_global/00_frameworks.cypher": 128,
    "00_global/00_tom_defaults.cypher": 79,
    "00_global/01_bsi_basis_requirements_en.cypher": 15,
    "10_jurisdiction/eu/11_data_subjects_normalize.cypher": 13,
    "10_jurisdiction/eu/12_legal_basis_backfill.cypher": 4,
    "10_jurisdiction/eu/14a_law_dedup.cypher": 1,
    "10_jurisdiction/eu/14b_law_minimal_metadata.cypher": 56,
    "10_jurisdiction/eu/14d_law_cellar_sync.cypher": 65,
}


def test_manifest_statement_counts_pinned():
    assert set(EXPECTED_STATEMENT_COUNTS) == set(MANIFEST)
    for rel, expected in EXPECTED_STATEMENT_COUNTS.items():
        got = len(_split_statements((LAYERS_DIR / rel).read_text(encoding="utf-8")))
        assert got == expected, f"{rel}: {got} statements (pinned {expected})"


# ── D3: apply_layer executes per statement, aborts hard ──────────────────────

def test_apply_layer_executes_every_statement():
    session = FakeSession()
    result = apply_layer(session, "00_global/00_constraints.cypher")
    assert result == "9 statements"
    assert len(session.statements) == 9
    assert all("CREATE CONSTRAINT" in s for s in session.statements)


def test_apply_layer_aborts_on_first_failing_statement():
    """No continue-on-error: a half-applied foundation layer makes Phase-2
    modules MATCH nothing and no-op silently — the run must die loudly."""
    session = FakeSession(fail_at=3)
    with pytest.raises(RuntimeError, match=r"statement 3/9"):
        apply_layer(session, "00_global/00_constraints.cypher")
    assert len(session.statements) == 3, "must stop at the failing statement"


# ── D3: run(with_layers=True) — full-sequence order + validator gate ─────────

@pytest.fixture
def wired_run(monkeypatch):
    """run() against fakes: records the global execution order."""
    import scripts.seed_both as sb

    order: list[str] = []
    session = FakeSession()

    def fake_get_driver(target):
        class _Driver:
            def session(self, database=None):
                class _Ctx:
                    def __enter__(self_inner):
                        return session

                    def __exit__(self_inner, *a):
                        return False

                return _Ctx()

            def close(self):
                pass

        return _Driver(), "neo4j"

    def fake_apply_layer(sess, rel_path):
        order.append(f"layer:{rel_path}")
        return "ok"

    def fake_module(sess):
        order.append("module:adr061")
        return "ok"

    monkeypatch.setattr(sb, "get_driver", fake_get_driver)
    monkeypatch.setattr(sb, "apply_layer", fake_apply_layer)
    monkeypatch.setattr(sb, "MODULES", {"adr061": fake_module})
    return sb, order


def test_run_with_layers_executes_the_adr130_sequence(wired_run, monkeypatch):
    sb, order = wired_run
    monkeypatch.setattr(sb, "validate_graph", lambda s: (order.append("validate"), [])[1])

    run("nuc", ["adr061"], with_layers=True)

    expected = (
        [f"layer:{p}" for p in LAYERS_PHASE_0 + LAYERS_PHASE_1]
        + ["module:adr061"]
        + [f"layer:{p}" for p in LAYERS_PHASE_3]
        + ["validate"]
    )
    assert order == expected


def test_run_with_layers_raises_on_validation_errors(wired_run, monkeypatch):
    sb, order = wired_run
    monkeypatch.setattr(sb, "validate_graph", lambda s: ["Service 'X': data_subjects is null"])

    with pytest.raises(RuntimeError, match="validation failed: 1 error"):
        run("nuc", ["adr061"], with_layers=True)


def test_run_without_layers_is_the_historical_module_only_path(wired_run, monkeypatch):
    sb, order = wired_run
    monkeypatch.setattr(
        sb, "validate_graph",
        lambda s: pytest.fail("validate_graph must not run without layers"),
    )

    run("nuc", ["adr061"], with_layers=False)

    assert order == ["module:adr061"], "no layers, no validator — unchanged behaviour"
