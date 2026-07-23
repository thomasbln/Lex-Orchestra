"""
Lex-Orchestra — Supabase Migration Runner
==========================================
Applies the relational schema to the configured PostgreSQL database:

    1. scripts/migrate.sql                 — consolidated base schema (tables up
                                             to the ~010 era, idempotent)
    2. supabase/migrations/*.sql (sorted)  — later migrations (011–024+), each
                                             file idempotent by convention
                                             (IF NOT EXISTS / DO-$$ guards /
                                             backfills that no-op on empty DBs)

Safe to re-run on fresh AND existing databases (cleanroom fix F18).

Each file runs as ONE statement batch in its own transaction — never split on
';' — because migrations contain DO $$ ... $$ blocks (016/017/022) whose bodies
contain semicolons. A naive splitter corrupts them (same failure class that
retired src/graph/seed.py, ADR-130 D3).

Usage:
    make db-migrate            # or: .venv/bin/python scripts/migrate.py

Connection: MCP_SUPABASE_URL preferred, fallback DATABASE_URL.
Note: Runs outside Docker — replaces 'supabase-db' hostname with 'localhost'.
"""

import logging
import os
import re
import sys
import time
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# ADR-053: docker/envs/.env is the single canonical env file. Load it by
# explicit path — a bare load_dotenv() searches upward from scripts/ and never
# reaches docker/envs/.env (cleanroom F18, same class as seed_both F3).
# Missing file → no-op, shell env still applies.
_REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_REPO_ROOT / "docker" / "envs" / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

MIGRATE_SQL = Path(__file__).parent / "migrate.sql"
MIGRATIONS_DIR = _REPO_ROOT / "supabase" / "migrations"


def _resolve_db_url() -> str:
    mcp_url = os.getenv("MCP_SUPABASE_URL", "")
    db_url = os.getenv("DATABASE_URL", "")
    if mcp_url:
        return mcp_url
    # migrate.py runs outside Docker — replace container hostname with localhost
    return db_url.replace("supabase-db", "localhost").replace("@db:", "@localhost:")


def _migration_files() -> list[Path]:
    """Base schema first, then the numbered migrations in order."""
    files = [MIGRATE_SQL]
    if MIGRATIONS_DIR.is_dir():
        files.extend(sorted(MIGRATIONS_DIR.glob("*.sql")))
    return files


def _wait_for_db(db_url: str, timeout_s: int = 90) -> None:
    """Wait until the database accepts TCP connections.

    On first boot the supabase-db container runs its own init machinery on a
    temporary server (unix socket only) and then restarts — `pg_isready`
    inside the container reports ready before TCP is. Running `make db-migrate`
    right after `docker compose up -d` must not race that window (F18).
    """
    deadline = time.monotonic() + timeout_s
    attempt = 0
    while True:
        attempt += 1
        try:
            psycopg2.connect(db_url, connect_timeout=3).close()
            return
        except psycopg2.OperationalError as exc:
            if time.monotonic() >= deadline:
                first_line = str(exc).splitlines()[0]
                print(f"ERROR: database not reachable after {timeout_s}s: {first_line}")
                print("Hint: is supabase-db running? Start it with: "
                      "cd docker && docker compose up -d supabase-db")
                sys.exit(1)
            if attempt == 1:
                logger.info("Waiting for database (first boot can take ~30s)...")
            time.sleep(2)


def run_migration(db_url: str) -> None:
    _wait_for_db(db_url)
    errors: list[tuple[str, str]] = []
    applied = 0

    for path in _migration_files():
        name = path.name
        if not path.is_file():
            errors.append((name, "file not found"))
            logger.error("  %-55s MISSING", name)
            continue
        sql_text = path.read_text(encoding="utf-8")
        # One transaction per file; never split on ';' (DO-$$ safety, see header)
        conn = psycopg2.connect(db_url)
        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                cur.execute(sql_text)
            conn.commit()
            applied += 1
            logger.info("  %-55s OK", name)
        except Exception as exc:
            conn.rollback()
            first_line = str(exc).splitlines()[0][:120]
            errors.append((name, first_line))
            logger.error("  %-55s FAILED: %s", name, first_line)
        finally:
            conn.close()

    print()
    print(f"Migration complete: {applied} file(s) applied, {len(errors)} error(s).")
    if errors:
        for name, msg in errors:
            print(f"  ERROR in {name}: {msg}")
        sys.exit(1)
    print("All migration files applied successfully.")


if __name__ == "__main__":
    db_url = _resolve_db_url()
    if not db_url:
        print(
            "ERROR: Set MCP_SUPABASE_URL or DATABASE_URL "
            "(docker/envs/.env, see .env.example)"
        )
        sys.exit(1)

    # Mask password in log output
    safe_url = re.sub(r":([^:@]+)@", ":***@", db_url)
    logger.info("Using DB: %s", safe_url)
    logger.info("Base SQL: %s", MIGRATE_SQL)
    logger.info("Migrations dir: %s", MIGRATIONS_DIR)
    print()

    run_migration(db_url)
