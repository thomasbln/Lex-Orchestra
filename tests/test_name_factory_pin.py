"""Pin the name factories against the seed catalog (ADR-130 A1.8 follow-up).

Why
---
A detected service name is a graph key: ``graph_client.Q_META`` runs a hard
``MATCH (s:Service {name: nm})``. A name no catalog entry carries does not
raise — the service silently drops out of ``graph_result["services"]``, and the
DPA processor list is short by one row.

Until 2026-07-28 ``asset_translator._canonical_name`` ended in ``known.title()``
over a lowercase token set. That produced ``Openai``, ``Aws``, ``Github``,
``Paypal``, ``Hubspot``, ``Sendgrid``, ``Mistral Ai`` and ``Mongodb Atlas`` —
eight spellings the catalog does not know. 86 rows in the live ``assets`` table
still carry ``Openai`` from that era.

Two separate assertions live here, on purpose:

* **The bar** (``test_every_emittable_name_is_a_catalog_name``) — no exceptions,
  must always be green. If a factory can emit it, the catalog must know it.
* **The ratchet** (``test_catalog_coverage_does_not_regress``) — how much of the
  catalog is reachable at all. Allowed to be below 100 %, not allowed to fall.

DB-free: reads the seed sources, so a hand-added node on one machine cannot mask
a gap.
"""

from __future__ import annotations

import re
from pathlib import Path

from scripts.seed_both import ADR_082_INTEGRATIONS, PSP_ROLES, STUB_SERVICES
from src.graph.asset_translator import CANONICAL_MAP, EXTRA_CATALOG_NAMES
from src.scout.lex_orchestra_scout import LLM_CALL_PATTERNS
from src.scout.signal_map import SIGNAL_MAP, canonical

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
    names |= {entry["name"] for entry in ADR_082_INTEGRATIONS}
    return names


def emittable_names() -> dict[str, str]:
    """{name: which factory can emit it} — deterministic paths only.

    The Gemma4 echo (``llm_classifier``) is deliberately excluded: its output is
    a function of a model, not of a table, so it cannot be enumerated. That is a
    known gap, tracked separately — see the backlog entry on the fourth name
    factory.
    """
    out: dict[str, str] = {}
    for value in SIGNAL_MAP.values():
        if value:
            out.setdefault(value, "signal_map.SIGNAL_MAP")
    for value in EXTRA_CATALOG_NAMES.values():
        out.setdefault(value, "asset_translator.EXTRA_CATALOG_NAMES")
    for value in CANONICAL_MAP.values():
        if value:
            out.setdefault(value, "asset_translator.CANONICAL_MAP")
    for _pattern, raw, _category in LLM_CALL_PATTERNS:
        hit = canonical(raw)
        if hit:
            out.setdefault(hit, "scout.LLM_CALL_PATTERNS")
    return out


# ── The bar: no exceptions ───────────────────────────────────────────────────

def test_sources_are_readable():
    """Guard against a silent pass if an extraction ever returns nothing."""
    assert len(catalog_names()) > 50
    assert len(emittable_names()) > 30


def test_every_emittable_name_is_a_catalog_name():
    """A name a factory can produce that the catalog does not carry is a
    silent drop, not an error — which is exactly why it needs a test."""
    catalog = catalog_names()
    strays = sorted(
        f"{name!r} (from {origin})"
        for name, origin in emittable_names().items()
        if name not in catalog
    )
    assert not strays, (
        f"{len(strays)} name(s) can be emitted but do not exist in the seed "
        f"catalog: {strays}. Either the spelling is wrong (fix the table) or the "
        f"catalog entry is missing (add it to a layer)."
    )


def test_known_spelling_regressions_stay_fixed():
    """The eight Klasse-A names that `.title()` used to mangle."""
    from src.graph.asset_translator import _canonical_name

    for name in ["OpenAI", "AWS", "GitHub", "HubSpot",
                 "Mistral AI", "MongoDB Atlas", "PayPal", "SendGrid"]:
        assert _canonical_name(name) == name, f"{name} was mangled again"
        assert _canonical_name(name.lower()) == name, f"{name.lower()} did not resolve"


def test_mongodb_does_not_resolve_to_atlas():
    """ADR-072: library presence cannot tell self-hosted MongoDB from Atlas,
    so naming a processor would be a false claim. The old backwards substring
    match ("mongodb" is contained in "mongodb atlas") did exactly that."""
    from src.graph.asset_translator import _canonical_name

    for probe in ["mongodb", "MongoDB", "pymongo", "mongoose", "mongodb-memory-server"]:
        assert _canonical_name(probe) is None, f"{probe} resolved to a processor name"


def test_unknown_token_has_no_canonical_name():
    """An unknown service must stay unknown — that is what puts it in the
    `unclassified` block with the duty marker instead of a false claim."""
    from src.graph.asset_translator import _canonical_name

    for probe in ["acme-widget", "cohere", "zendesk", "gitlab"]:
        assert _canonical_name(probe) is None


# ── The ratchet: a number that may only go up ────────────────────────────────

# Catalog entries no deterministic path can produce ON PURPOSE. Each line needs
# a source. This is NOT a parking lot for missing tokens — those belong in the
# coverage number below, where they stay visible as work.
DELIBERATELY_UNREACHABLE = {
    "MongoDB": (
        "ADR-072, signal_map.py note 'mongodb (JS), pymongo, motor all "
        "intentionally unmapped' — library presence cannot distinguish "
        "self-hosted from Atlas; detection is category-only by design. "
        "ADR-130 A1.8."
    ),
    "Mistral AI EU": (
        "ADR-082 marketplace catalog entry, not a scanned compliance service — "
        "seed_both.py:1190/1228 and 11_data_subjects_normalize.cypher."
    ),
    "eRecht24": "ADR-082 § Graph Model — dashboard Marketplace card, not a scan target.",
    "Firecrawl": "ADR-082 § Graph Model — dashboard Marketplace card, not a scan target.",
    "Langfuse": "ADR-082 § Graph Model — dashboard Marketplace card, not a scan target.",
    "Telegram": "ADR-082 § Graph Model — dashboard Marketplace card, not a scan target.",
}

# Measured 2026-07-28: 49 of 64 scored catalog entries. Raise this when tokens
# are added; never lower it. Lowering it is how a coverage gap becomes invisible.
MIN_REACHABLE = 49


def test_every_deliberate_exception_carries_a_reason():
    for name, reason in DELIBERATELY_UNREACHABLE.items():
        assert len(reason) > 40, f"{name}: reason too thin to survive a cleanup"
        assert name in catalog_names(), f"{name} is not a catalog entry at all"


def test_catalog_coverage_does_not_regress():
    """How many catalog entries a deterministic path can produce.

    Below 100 % by design: 15 entries have no detection token yet (AWS RDS,
    Cloudinary, Fly.io, Render, …). They are a backlog, deliberately left in the
    denominator so the gap stays countable rather than disappearing into an
    exception list.
    """
    catalog = catalog_names()
    reachable = catalog & set(emittable_names())
    scored = catalog - set(DELIBERATELY_UNREACHABLE)
    assert len(reachable) >= MIN_REACHABLE, (
        f"catalog coverage fell to {len(reachable)}/{len(scored)} "
        f"(floor {MIN_REACHABLE}). Missing: {sorted(scored - reachable)}"
    )
