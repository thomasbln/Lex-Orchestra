"""Tests for ADR-032 — git_clone.py"""
import socket

import pytest
from pathlib import Path
from src.scout.git_clone import clone_repo, cleanup_clone


def _github_reachable() -> bool:
    try:
        socket.create_connection(("github.com", 443), timeout=3).close()
        return True
    except OSError:
        return False


requires_network = pytest.mark.skipif(
    not _github_reachable(), reason="github.com not reachable — network test"
)


def test_cleanup_nonexistent_path():
    """cleanup_clone must not raise on missing path."""
    cleanup_clone(Path("/tmp/lex-scan-doesnotexist"))


def test_cleanup_none():
    """cleanup_clone must not raise on None."""
    cleanup_clone(None)


@requires_network
def test_clone_invalid_url():
    """clone_repo returns None on invalid URL."""
    result = clone_repo("https://github.com/invalid/repo-doesnotexist-xyz", "test-run-id")
    assert result is None


@requires_network
def test_clone_and_cleanup_public_repo():
    """Clone a small public repo, verify path exists, then cleanup."""
    run_id = "test-adr032-abc"
    path = clone_repo(
        "https://github.com/octocat/Hello-World",
        run_id,
    )
    assert path is not None, "Clone should succeed for public repo"
    assert path.exists()
    assert (path / "README").exists() or any(path.iterdir())
    cleanup_clone(path)
    assert not path.exists(), "Clone should be deleted after cleanup"
