"""ADR-107 Tier-B/C PDF Presence Check
========================================
Walks every `*.meta.yaml` sidecar in docs/sources/, identifies Tier-B and
Tier-C entries with `in_repo: false`, and verifies the user has placed the
expected PDF locally (`local_path_expected`).

Exit code:
  0 — all Tier-B/C PDFs present or no Tier-B/C entries
  1 — at least one Tier-B/C PDF missing

Output: per-source status with download/purchase URL for missing items.
Used by `make seed-extras` before any Tier-B/C-dependent seed runs.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    import yaml  # PyYAML
except ImportError:
    print("ERROR: PyYAML required. Install with `pip install pyyaml`.", file=sys.stderr)
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = REPO_ROOT / "docs" / "sources"


def main() -> int:
    if not SOURCES_DIR.exists():
        print(f"ERROR: {SOURCES_DIR} not found", file=sys.stderr)
        return 2

    sidecars = sorted(SOURCES_DIR.rglob("*.meta.yaml"))
    missing: list[dict] = []
    found: list[dict] = []
    tier_a = 0

    for sc in sidecars:
        try:
            with open(sc, "r", encoding="utf-8") as f:
                meta = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"WARN: cannot parse {sc}: {e}", file=sys.stderr)
            continue

        tier = meta.get("tier")
        in_repo = meta.get("in_repo", True)

        if tier == "A" or in_repo:
            tier_a += 1
            continue

        # Tier B or C — must have local PDF
        expected_path_str = meta.get("local_path_expected")
        if not expected_path_str:
            print(f"WARN: {sc.name}: tier={tier} but no local_path_expected — skipping", file=sys.stderr)
            continue

        # local_path_expected is relative to repo root
        local_path = REPO_ROOT / expected_path_str

        entry = {
            "sidecar": sc.relative_to(REPO_ROOT),
            "title": meta.get("title", "?"),
            "tier": tier,
            "expected": expected_path_str,
            "purchase_url": meta.get("purchase_url"),
            "source_url": meta.get("source_url"),
            "estimated_cost_eur": meta.get("estimated_cost_eur"),
        }

        if local_path.exists():
            found.append(entry)
        else:
            missing.append(entry)

    # Report
    print(f"\n=== ADR-107 Tier B/C PDF Presence Check ===")
    print(f"Tier-A (in repo, no action needed): {tier_a}")
    print(f"Tier-B/C with local PDF present:    {len(found)}")
    print(f"Tier-B/C with local PDF MISSING:    {len(missing)}")

    if found:
        print(f"\n✅ Found ({len(found)}):")
        for e in found:
            print(f"  [{e['tier']}] {e['title']}")
            print(f"      at {e['expected']}")

    if missing:
        print(f"\n❌ Missing ({len(missing)}):")
        for e in missing:
            print(f"  [{e['tier']}] {e['title']}")
            print(f"      expected at: {e['expected']}")
            if e["tier"] == "C":
                cost = f" (~{e['estimated_cost_eur']} EUR)" if e["estimated_cost_eur"] else ""
                print(f"      purchase{cost}: {e['purchase_url']}")
            else:
                print(f"      download: {e['source_url']}")
        print("\nSee docs/setup/source-materials.md for full per-source instructions.")
        return 1

    print("\nAll Tier-B/C PDFs accounted for. Safe to run `make seed-all` with extras.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
