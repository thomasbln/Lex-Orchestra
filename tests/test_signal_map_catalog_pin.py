"""Pin SIGNAL_MAP's canonical names against the seed catalog.

Why this test exists (2026-07-28, ADR-130 addendum)
---------------------------------------------------
``SIGNAL_MAP`` maps a detected token to a *canonical service name*. That name is
then used as a graph key: ``graph_client.Q_META`` does a hard
``MATCH (s:Service {name: svc_name})``. A name that no seed source creates
therefore does not raise — it silently drops the service out of
``graph_result["services"]``, and the scan report is short by one row.

That is exactly what happened to ``"auth0"``, which mapped to the display label
``"Auth0 / Okta"`` while the catalog node is called ``"Auth0"``. Nothing failed;
the service just disappeared.

This test has no database dependency on purpose. It reads the *seed sources* —
the same files a fresh install replays — so it also fails on a machine whose
live graph happens to carry a hand-added node.

Catalog sources (all three are needed; a service created by only one of them is
still a real catalog entry):
  1. ``src/graph/layers/**/*.cypher`` — ``MERGE (s:Service {name: "..."})``
  2. ``seed_both.STUB_SERVICES``      — curated stubs (ADR-061)
  3. ``seed_both.PSP_ROLES``          — payment providers, created if missing
      (see the docstring at scripts/seed_both.py:1917)

If a fourth source appears, this test fails with the new name listed as
missing. That failure is the intended signal: add the source here.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts.seed_both import PSP_ROLES, STUB_SERVICES
from src.scout.signal_map import SIGNAL_MAP

REPO_ROOT = Path(__file__).resolve().parents[1]
LAYERS_DIR = REPO_ROOT / "src" / "graph" / "layers"

_SERVICE_MERGE = re.compile(r'Service \{name:\s*"([^"]+)"')


def catalog_names() -> set[str]:
    """Every Service name a fresh seed run creates."""
    names: set[str] = set()
    for path in sorted(LAYERS_DIR.rglob("*.cypher")):
        names |= set(_SERVICE_MERGE.findall(path.read_text(encoding="utf-8")))
    names |= {row[0] for row in STUB_SERVICES}
    names |= {row[0] for row in PSP_ROLES}
    return names


def test_layers_dir_is_readable():
    """Guard against a silent pass if the glob ever matches nothing."""
    assert LAYERS_DIR.is_dir(), f"layer dir missing: {LAYERS_DIR}"
    assert len(catalog_names()) > 50, "catalog extraction returned suspiciously few names"


def test_every_canonical_name_exists_in_the_catalog():
    """No SIGNAL_MAP target may be a name the seed never creates.

    A miss here is not cosmetic: Q_META drops the service silently, so the
    finding surfaces as a missing row in a customer document, not as an error.
    """
    catalog = catalog_names()
    canonical = {v for v in SIGNAL_MAP.values() if v}
    missing = sorted(canonical - catalog)
    assert not missing, (
        f"{len(missing)} SIGNAL_MAP target(s) have no Service node in any seed "
        f"source: {missing}. Either the name is a display label (fix the map) "
        f"or the catalog entry is missing (add it to a layer)."
    )


@pytest.mark.parametrize(
    "token,expected",
    [
        # The regression this test was written for.
        ("auth0", "Auth0"),
        # The two catalog gaps backported on 2026-07-28 — pinned so a future
        # catalog edit cannot quietly re-open them.
        ("redis", "Redis"),
        ("elasticsearch", "Elasticsearch"),
    ],
)
def test_known_regressions_stay_fixed(token, expected):
    assert SIGNAL_MAP[token] == expected


def test_no_canonical_name_looks_like_a_display_label():
    """Catch the *class* of the auth0 bug, not just the instance.

    A graph key is one product name. Separators like ``/`` or `` & `` mean a
    human wrote a label ("Auth0 / Okta") where a key belonged. This is a
    heuristic, so it allows the names the catalog genuinely carries.
    """
    catalog = catalog_names()
    suspicious = sorted(
        v
        for v in SIGNAL_MAP.values()
        if v and v not in catalog and (" / " in v or " & " in v or "," in v)
    )
    assert not suspicious, (
        f"canonical name(s) look like display labels, not catalog keys: "
        f"{suspicious}"
    )
