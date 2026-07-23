# Lex-Orchestra — self-hoster Makefile
# Host-agnostic targets only. Maintainer machinery (host-specific deploys,
# tunnels) lives in the maintainer include, pulled in via -include below —
# absent on an exported/public tree, and nothing here depends on it (ADR-130 D4).

.PHONY: dashboard-build audit-secrets seed-validate seed-all seed-extras seed-bootstrap db-migrate

dashboard-build:
	cd src/dashboard && npm run build

# ── ADR-130 Reproducibility — Seed Commands ───────────────────────────────────
# After git clone + docker compose up (local Neo4j profile), `make seed-all`
# reproduces the default graph from Tier-A sources alone: layer manifest
# (Phase 0/1) → Python modules → mutation layers (Phase 3) → ADR-100 validator.
# Verified by the ADR-130 D7 cleanroom gate. Tier-B/C extras require manual
# PDF download per docs/setup/source-materials.md, then `make seed-extras`.
#
# Default TARGET is `local` (bolt://localhost:7687, never prompts).
# Maintainer override: TARGET=nuc (SSH tunnel; prompts before writing).
#
# PYTHON defaults to the repo-local venv — Debian/Ubuntu/Mint ship no bare
# `python`, and PEP 668 blocks a system-wide pip install, so the dependencies
# live in .venv (see docs/setup/docker.md). Override with `make PYTHON=python3 …`
# if you manage the environment yourself (F4).
TARGET ?= local
PYTHON ?= .venv/bin/python

seed-all:
	$(PYTHON) scripts/seed_master.py --target $(TARGET) --module all

# ── ADR-100 Graph Integrity Validator ────────────────────────────────────────
# Runs validate_graph() — §4.1–§4.4 checks on the live graph, no writes.
# On success, prints the completion banner (reachable URLs). The banner is the
# recipe's last line, so it runs only if validation exits 0; it never fails the
# target itself (ready-banner.sh always exits 0 — pure post-setup info).
seed-validate:
	$(PYTHON) scripts/seed_both.py --validate-only --target $(TARGET)
	@sh scripts/ready-banner.sh

seed-extras:
	$(PYTHON) scripts/check_tier_bc_pdfs.py

# ── Relational Schema (Supabase/PostgreSQL) ──────────────────────────────────
# Applies scripts/migrate.sql + supabase/migrations/*.sql to the running
# supabase-db container. Idempotent — safe on fresh and existing databases (F18).
db-migrate:
	$(PYTHON) scripts/migrate.py

# Convenience: full seed + validation for fresh clones
seed-bootstrap: seed-all seed-validate

# ── ADR-083 Secret Storage Guards ────────────────────────────────────────────
# Fails if any public table has a plaintext-secret-shaped column
# (*_api_key, *_token, *_password, *_secret_plain). Run after every
# migration and in CI.
audit-secrets:
	$(PYTHON) scripts/audit_no_plaintext_secrets.py

# ── Maintainer targets (optional, not part of the public tree) ───────────────
-include Makefile.maintainer
