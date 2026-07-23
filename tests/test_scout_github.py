"""
Tests: GitHub manifest discovery — ADR-078.

Covers _discover_github_manifests tree walker (dedup, depth, exclusions) and
the _scout_github integration with the root-only fallback on tree-API errors.
All tests mock network calls — no real GitHub requests.
"""

from unittest.mock import patch, MagicMock

import pytest

from src.workflow.main import (
    _discover_github_manifests,
    _fetch_github_tree,
    _scout_github,
)


# ── _discover_github_manifests (pure tree walker) ────────────────────────────

def test_monorepo_finds_backend_frontend_mobile():
    """Polyglot monorepo — every manifest found is returned, no dedup."""
    tree = [
        {"path": "backend/requirements.txt", "type": "blob"},
        {"path": "frontend/package.json",    "type": "blob"},
        {"path": "mobile/package.json",      "type": "blob"},
        {"path": ".env.example",             "type": "blob"},
        {"path": "README.md",                "type": "blob"},
    ]
    paths = _discover_github_manifests(tree)
    path_strs = [p for p, _ in paths]

    assert "backend/requirements.txt" in path_strs
    assert "frontend/package.json"    in path_strs
    assert "mobile/package.json"      in path_strs


def test_root_and_subdir_both_kept():
    """Next.js root + Node backend subdir — both package.json parsed."""
    tree = [
        {"path": "package.json",          "type": "blob"},
        {"path": "backend/package.json",  "type": "blob"},
    ]
    paths = _discover_github_manifests(tree)
    path_strs = [p for p, _ in paths]
    assert "package.json"         in path_strs
    assert "backend/package.json" in path_strs


def test_max_depth_filters_too_deep():
    tree = [
        {"path": "a/b/c/d/package.json", "type": "blob"},   # depth 4 → out
        {"path": "a/b/c/package.json",   "type": "blob"},   # depth 3 → in
    ]
    paths = _discover_github_manifests(tree)
    assert ("a/b/c/package.json", "package.json") in paths
    assert not any(p.startswith("a/b/c/d/") for p, _ in paths)


def test_deep_and_shallow_both_kept():
    """No dedup — even same-filename manifests at different depths are kept."""
    tree = [
        {"path": "apps/web/package.json",          "type": "blob"},
        {"path": "apps/web/internal/package.json", "type": "blob"},
    ]
    paths = _discover_github_manifests(tree)
    path_strs = [p for p, _ in paths]
    assert "apps/web/package.json"          in path_strs
    assert "apps/web/internal/package.json" in path_strs


def test_excluded_dirs_skipped():
    tree = [
        {"path": "node_modules/foo/package.json", "type": "blob"},
        {"path": "tests/fixtures/requirements.txt", "type": "blob"},
        {"path": "backend/requirements.txt", "type": "blob"},
    ]
    paths = _discover_github_manifests(tree)
    assert all("node_modules" not in p for p, _ in paths)
    assert all("tests/" not in p for p, _ in paths)
    assert ("backend/requirements.txt", "requirements.txt") in paths


def test_go_mod_is_multi_instance():
    """go.mod in multiple subdirs all survive (per-module, no dedup)."""
    tree = [
        {"path": "services/api/go.mod",     "type": "blob"},
        {"path": "services/worker/go.mod",  "type": "blob"},
    ]
    paths = _discover_github_manifests(tree)
    go_mods = [p for p, n in paths if n == "go.mod"]
    assert set(go_mods) == {"services/api/go.mod", "services/worker/go.mod"}


def test_requirements_variants_all_kept():
    """requirements-dev.txt and requirements-prod.txt are legit variants."""
    tree = [
        {"path": "requirements.txt",      "type": "blob"},
        {"path": "requirements-dev.txt",  "type": "blob"},
        {"path": "requirements-prod.txt", "type": "blob"},
    ]
    paths = _discover_github_manifests(tree)
    path_strs = [p for p, _ in paths]
    assert "requirements.txt"      in path_strs
    assert "requirements-dev.txt"  in path_strs
    assert "requirements-prod.txt" in path_strs


def test_non_blob_items_ignored():
    tree = [
        {"path": "frontend", "type": "tree"},
        {"path": "frontend/package.json", "type": "blob"},
    ]
    paths = _discover_github_manifests(tree)
    assert ("frontend/package.json", "package.json") in paths
    assert ("frontend", "frontend") not in paths


# ── _fetch_github_tree (error handling) ──────────────────────────────────────

def test_tree_api_error_returns_empty():
    with patch("requests.get", side_effect=ConnectionError("boom")):
        assert _fetch_github_tree("owner", "repo", "token") == []


def test_tree_api_non_200_returns_empty():
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    with patch("requests.get", return_value=mock_resp):
        assert _fetch_github_tree("owner", "repo", "token") == []


# ── _scout_github integration (with mocked network) ──────────────────────────

def _mock_reachability_200():
    """Return a MagicMock resembling a 200 OK /repos/{owner}/{repo} response."""
    m = MagicMock()
    m.status_code = 200
    m.text = "{}"
    return m


def test_scout_github_monorepo_dispatch(monkeypatch):
    """Tree returns monorepo layout — parsers dispatch, canonical set populated."""
    tree_blob = [
        {"path": "backend/requirements.txt", "type": "blob"},
        {"path": "frontend/package.json",    "type": "blob"},
    ]
    file_contents = {
        "backend/requirements.txt": "anthropic>=0.40\nfastapi\n",
        "frontend/package.json":    '{"dependencies":{"stripe":"^10.0"}}',
    }

    def fake_requests_get(url, headers=None, timeout=None):
        resp = MagicMock()
        if "/git/trees/" in url:
            resp.status_code = 200
            resp.json.return_value = {"tree": tree_blob}
        else:
            # Reachability check
            resp.status_code = 200
            resp.text = "{}"
        return resp

    def fake_fetch_file(owner, repo, path, token):
        return file_contents.get(path)

    monkeypatch.setattr("requests.get", fake_requests_get)
    monkeypatch.setattr("src.workflow.main._fetch_github_file", fake_fetch_file)
    monkeypatch.setattr(
        "src.scout.signal_map.canonical",
        lambda name: {"stripe": "Stripe", "anthropic": "Anthropic", "fastapi": None}.get(name),
    )
    monkeypatch.setattr(
        "src.scout.signal_map.canonical_with_fallback",
        lambda name, use_llm=True: (None, None, None),
    )

    result = _scout_github("owner", "repo", "token")

    assert "Stripe" in result["service_names"]
    assert "Anthropic" in result["service_names"]


def test_scout_github_root_fallback_on_tree_error(monkeypatch):
    """Tree-API fails → root-only fallback still finds root package.json."""
    file_contents = {
        "package.json": '{"dependencies":{"stripe":"^10.0"}}',
    }

    def fake_requests_get(url, headers=None, timeout=None):
        if "/git/trees/" in url:
            raise ConnectionError("tree down")
        resp = MagicMock()
        resp.status_code = 200
        resp.text = "{}"
        return resp

    def fake_fetch_file(owner, repo, path, token):
        return file_contents.get(path)

    monkeypatch.setattr("requests.get", fake_requests_get)
    monkeypatch.setattr("src.workflow.main._fetch_github_file", fake_fetch_file)
    monkeypatch.setattr(
        "src.scout.signal_map.canonical",
        lambda name: {"stripe": "Stripe"}.get(name),
    )
    monkeypatch.setattr(
        "src.scout.signal_map.canonical_with_fallback",
        lambda name, use_llm=True: (None, None, None),
    )

    result = _scout_github("owner", "repo", "token")
    assert "Stripe" in result["service_names"]


# ── Parser unit tests ────────────────────────────────────────────────────────

def test_parse_pyproject_toml():
    """PEP 621-style dependencies list (quoted entries) — matches existing regex."""
    from src.workflow.main import _parse_pyproject_toml
    content = '''[project]
name = "example"
dependencies = [
    "fastapi>=0.110",
    "anthropic>=0.40",
]
'''
    calls = []
    services: list = []
    _parse_pyproject_toml(content, "pyproject.toml", services, calls.append)
    assert "fastapi" in calls
    assert "anthropic" in calls


def test_parse_pipfile():
    from src.workflow.main import _parse_pipfile
    content = """
[packages]
requests = "*"
anthropic = ">=0.40"

[dev-packages]
pytest = "*"

[requires]
python_version = "3.11"
"""
    calls = []
    services: list = []
    _parse_pipfile(content, "Pipfile", services, calls.append)
    assert "requests" in calls
    assert "anthropic" in calls
    assert "pytest" in calls
    # python_version is in [requires], must not leak in
    assert "python_version" not in calls


def test_parse_go_mod():
    from src.workflow.main import _parse_go_mod
    content = """module example.com/foo

go 1.21

require (
    github.com/stripe/stripe-go v72.0.0
    github.com/sirupsen/logrus v1.9.0
)
"""
    calls = []
    services: list = []
    _parse_go_mod(content, "go.mod", services, calls.append)
    assert "stripe-go" in calls
    assert "logrus" in calls


# ── ADR-110: Stripe integration-mode derivation ──────────────────────────────
# Pure unit tests on _derive_stripe_integration_mode — no network, no pipeline.
# The function reads the raw scout services[] list (full package names + source)
# before the canonical set-collapse discards the raw name.

def test_integration_mode_stripe_js_is_delegated():
    """@stripe/stripe-js → card data flows browser→Stripe (delegated)."""
    from src.workflow.main import _derive_stripe_integration_mode
    services = [{"name": "@stripe/stripe-js", "source": "frontend/package.json"}]
    assert _derive_stripe_integration_mode(services) == "delegated"


def test_integration_mode_react_stripe_js_is_delegated():
    """@stripe/react-stripe-js is also a client-side JS package → delegated."""
    from src.workflow.main import _derive_stripe_integration_mode
    services = [{"name": "@stripe/react-stripe-js", "source": "package.json"}]
    assert _derive_stripe_integration_mode(services) == "delegated"


def test_integration_mode_bare_server_sdk_is_merchant_side():
    """Only the server SDK `stripe`, no *-js package → merchant_side_possible."""
    from src.workflow.main import _derive_stripe_integration_mode
    services = [{"name": "stripe", "source": "backend/requirements.txt"}]
    assert _derive_stripe_integration_mode(services) == "merchant_side_possible"


def test_integration_mode_composer_php_sdk_is_merchant_side():
    """ADR-110 ecosystem axis: composer stripe/stripe-php (parsed to short name
    'stripe-php') is a server SDK → merchant_side_possible, not unknown.
    Regression for the velstore finding (PHP/Laravel shop fell to unknown)."""
    from src.workflow.main import _derive_stripe_integration_mode
    services = [{"name": "stripe-php", "source": "composer.json"}]
    assert _derive_stripe_integration_mode(services) == "merchant_side_possible"


def test_integration_mode_php_sdk_plus_stripe_js_delegated_wins():
    """V2b still wins across ecosystems: composer server SDK + a JS client token
    (e.g. Stripe Elements loaded via @stripe/stripe-js) → delegated."""
    from src.workflow.main import _derive_stripe_integration_mode
    services = [
        {"name": "stripe-php",        "source": "composer.json"},
        {"name": "@stripe/stripe-js", "source": "package.json"},
    ]
    assert _derive_stripe_integration_mode(services) == "delegated"


def test_integration_mode_fullstack_delegated_wins():
    """V2b merge: frontend @stripe/stripe-js + backend stripe → delegated wins."""
    from src.workflow.main import _derive_stripe_integration_mode
    services = [
        {"name": "@stripe/stripe-js", "source": "frontend/package.json"},
        {"name": "stripe",            "source": "backend/requirements.txt"},
    ]
    assert _derive_stripe_integration_mode(services) == "delegated"


def test_integration_mode_no_stripe_returns_none():
    """No Stripe signal at all → no integration_mode."""
    from src.workflow.main import _derive_stripe_integration_mode
    services = [
        {"name": "openai",   "source": "requirements.txt"},
        {"name": "supabase", "source": "package.json"},
    ]
    assert _derive_stripe_integration_mode(services) is None


def test_integration_mode_indirect_stripe_package_is_unknown():
    """Stripe present but no decisive SDK signal (e.g. a stripe-* helper) → unknown."""
    from src.workflow.main import _derive_stripe_integration_mode
    services = [{"name": "stripe-event-types", "source": "package.json"}]
    assert _derive_stripe_integration_mode(services) == "unknown"


def test_integration_mode_handles_missing_name_key():
    """Defensive: a service entry without a name must not crash the derivation."""
    from src.workflow.main import _derive_stripe_integration_mode
    services = [{"source": "package.json"}, {"name": None}]
    assert _derive_stripe_integration_mode(services) is None
