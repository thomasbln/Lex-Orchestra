"""ADR-107 Master Seed Orchestrator
=====================================
Single entrypoint for reproducible graph bootstrap from Tier-A sources only.

Usage:
    python scripts/seed_master.py                                # full seed, default target=local
    python scripts/seed_master.py --target nuc --yes             # maintainer host (tunnel), no prompt
    python scripts/seed_master.py --module adr061 --target nuc   # single module (prompts)
    python scripts/seed_master.py --validate-only --target nuc   # only run ADR-100 invariants

Wraps the existing scripts/seed_both.py main() so all seed orchestration logic
lives in one place. Reason for thin wrapper rather than rename: seed_both.py
is still referenced by `make seed-validate*` targets and downstream tooling.
This file is the ADR-107-blessed entrypoint for fresh-clone bootstrap.

After `make seed-all` succeeds, the graph contains:
- 8 Tier-A seed-module outputs (ServiceCategory, BSI Bausteine, OWASP→ISO maps,
  curated Service stubs, Service-SCC annotations, HostingProvider catalog,
  Integration catalog, DocumentType + Law nodes from DSGVO/NIS2)
- Each node and edge carries source/source_url/license/license_attribution/
  last_verified properties per ADR-107 provenance discipline

Tier-B/C seed modules (BSI IT-Grundschutz Vollkorpus, ISO 27001, etc.) are NOT
run by this entrypoint. See `make seed-extras` and docs/setup/source-materials.md.
"""
from __future__ import annotations

import os
import sys

# Ensure scripts/ is on sys.path regardless of CWD invocation pattern.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Delegate to the canonical implementation. seed_both.main() handles argparse,
# --target/--module/--validate-only, idempotent MERGE-based execution per ADR-003.
from seed_both import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
