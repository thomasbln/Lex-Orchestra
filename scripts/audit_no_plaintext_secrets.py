#!/usr/bin/env python3
"""ADR-083 guard: fail if any public table has a plaintext-secret-shaped column.

Convention: secrets live in vault.secrets; application tables hold
*_secret_id UUID references only. This script catches regressions where
a migration re-introduces a plaintext TEXT column like `*_api_key` or
`*_token`.

Exit code 0 = clean, 1 = violations found.
"""
from __future__ import annotations

import os
import sys

import psycopg2


FORBIDDEN_SUFFIXES = ("_api_key", "_token", "_password", "_secret_plain")


def main() -> int:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("MCP_SUPABASE_URL")
    if not dsn:
        print("ERROR: DATABASE_URL or MCP_SUPABASE_URL must be set", file=sys.stderr)
        return 2

    conn = psycopg2.connect(dsn)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_schema, table_name, column_name
                  FROM information_schema.columns
                 WHERE table_schema = 'public'
                   AND data_type IN ('text', 'character varying')
                   AND (
                          column_name LIKE %s
                       OR column_name LIKE %s
                       OR column_name LIKE %s
                       OR column_name LIKE %s
                   )
                   AND column_name NOT LIKE '%%_secret_id'
                 ORDER BY table_schema, table_name, column_name
                """,
                tuple(f"%{s}" for s in FORBIDDEN_SUFFIXES),
            )
            violations = cur.fetchall()
    finally:
        conn.close()

    if violations:
        print("PLAINTEXT SECRET COLUMNS DETECTED — see ADR-083:")
        for schema, table, column in violations:
            print(f"  {schema}.{table}.{column}")
        return 1

    print("No plaintext secret columns. ADR-083 convention upheld.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
