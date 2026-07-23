"""ADR-130 D4/D5 — target split (local default) + remote-write confirm guard.

All dry: argparse surface, env resolution and guard logic only. No driver is
ever connected (neo4j drivers are lazy; resolve_target_env touches no network).
"""

import pytest

from scripts.seed_both import (
    LOCAL_DEFAULT_URI,
    confirm_remote_write,
    parse_args,
    resolve_target_env,
)


# ── D4: argparse surface ──────────────────────────────────────────────────────

def test_default_target_is_local():
    args = parse_args([])
    assert args.target == "local"
    assert args.module == "all"
    assert args.yes is False


def test_target_both_no_longer_exists():
    """'both' wrote to the deprecated Aura uninvited — removed entirely."""
    with pytest.raises(SystemExit):
        parse_args(["--target", "both"])


def test_aura_write_run_is_rejected():
    with pytest.raises(SystemExit):
        parse_args(["--target", "aura", "--module", "adr061"])


def test_aura_validate_only_is_allowed():
    args = parse_args(["--target", "aura", "--validate-only"])
    assert args.target == "aura"
    assert args.validate_only is True


# ── D4: local env resolution — no URI redirect ────────────────────────────────

def test_local_defaults_to_localhost_bolt(monkeypatch):
    for var in ("NEO4J_LOCAL_URI", "NEO4J_LOCAL_USERNAME", "NEO4J_LOCAL_PASSWORD",
                "NEO4J_URI", "NEO4J_USERNAME"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NEO4J_PASSWORD", "pw")

    uri, user, pwd, db = resolve_target_env("local")

    assert uri == LOCAL_DEFAULT_URI == "bolt://localhost:7687"
    assert user == "neo4j"
    assert pwd == "pw"
    assert db == "neo4j"


def test_local_uri_never_falls_back_to_generic_neo4j_uri(monkeypatch):
    """The generic NEO4J_URI can point at a remote instance (it did: NucBox,
    ADR-119). A 'local' run silently writing remote is the incident class the
    target split kills — the URI must ignore the generic variable."""
    monkeypatch.delenv("NEO4J_LOCAL_URI", raising=False)
    monkeypatch.setenv("NEO4J_URI", "neo4j+s://remote.databases.neo4j.io")
    monkeypatch.setenv("NEO4J_PASSWORD", "pw")

    uri, *_ = resolve_target_env("local")

    assert uri == LOCAL_DEFAULT_URI


def test_local_explicit_override_wins(monkeypatch):
    monkeypatch.setenv("NEO4J_LOCAL_URI", "bolt://neo4j:7687")
    monkeypatch.setenv("NEO4J_LOCAL_PASSWORD", "s3cret")
    monkeypatch.setenv("NEO4J_LOCAL_USERNAME", "admin")

    uri, user, pwd, _ = resolve_target_env("local")

    assert (uri, user, pwd) == ("bolt://neo4j:7687", "admin", "s3cret")


def test_local_without_any_password_fails_actionably(monkeypatch):
    for var in ("NEO4J_LOCAL_PASSWORD", "NEO4J_PASSWORD"):
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(ValueError, match="NEO4J_LOCAL_PASSWORD or NEO4J_PASSWORD"):
        resolve_target_env("local")


def test_nuc_keeps_the_historical_prefix_convention(monkeypatch):
    monkeypatch.setenv("NEO4J_NUC_URI", "bolt://localhost:17687")
    monkeypatch.setenv("NEO4J_NUC_USERNAME", "neo4j")
    monkeypatch.setenv("NEO4J_NUC_PASSWORD", "pw")

    uri, *_ = resolve_target_env("nuc")

    assert uri == "bolt://localhost:17687"


# ── D5: confirm guard ─────────────────────────────────────────────────────────

def test_local_never_prompts(monkeypatch):
    monkeypatch.setattr("sys.stdin", None)  # any prompt attempt would explode
    assert confirm_remote_write("local", 30, True, assume_yes=False) is True


def test_yes_flag_skips_the_prompt_for_remote():
    assert confirm_remote_write("nuc", 30, True, assume_yes=True) is True


def test_non_tty_remote_without_yes_refuses(monkeypatch):
    class FakeStdin:
        def isatty(self):
            return False

    monkeypatch.setenv("NEO4J_NUC_URI", "bolt://localhost:17687")
    monkeypatch.setenv("NEO4J_NUC_USERNAME", "neo4j")
    monkeypatch.setenv("NEO4J_NUC_PASSWORD", "pw")
    monkeypatch.setattr("sys.stdin", FakeStdin())

    assert confirm_remote_write("nuc", 30, True, assume_yes=False) is False


@pytest.mark.parametrize("answer,expected", [("y", True), ("yes", True), ("", False), ("n", False)])
def test_tty_remote_prompt_honours_the_answer(monkeypatch, answer, expected):
    class FakeStdin:
        def isatty(self):
            return True

    monkeypatch.setenv("NEO4J_NUC_URI", "bolt://localhost:17687")
    monkeypatch.setenv("NEO4J_NUC_USERNAME", "neo4j")
    monkeypatch.setenv("NEO4J_NUC_PASSWORD", "pw")
    monkeypatch.setattr("sys.stdin", FakeStdin())
    monkeypatch.setattr("builtins.input", lambda _: answer)

    assert confirm_remote_write("nuc", 30, True, assume_yes=False) is expected
