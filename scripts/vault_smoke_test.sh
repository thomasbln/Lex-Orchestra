#!/usr/bin/env bash
# scripts/vault_smoke_test.sh
# Verifies that supabase_vault is functional on the target Postgres before
# any production migration touches it. Required precondition for ADR-083
# (Secret Storage via Supabase Vault).
#
# Usage (from your dev machine, against NucBox):
#   ssh <host> "cd ~/Projects/Lex-Orchestra && bash scripts/vault_smoke_test.sh"
#
# Usage (locally, on a host that has docker exec access to supabase-db):
#   bash scripts/vault_smoke_test.sh
#
# Override the psql invocation via PSQL_CMD if you don't use docker:
#   PSQL_CMD="psql -h localhost -U postgres -d postgres" bash scripts/vault_smoke_test.sh
#
# Exit codes:
#   0 — all checks passed, vault is ready for migration 016
#   1 — at least one check failed, do NOT run migration 016

set -euo pipefail

PSQL_CMD="${PSQL_CMD:-docker exec -i supabase-db psql -U postgres -d postgres -t -A}"

PASS=0
FAIL=0

green()  { printf '\033[32m✅ %s\033[0m\n' "$1"; }
red()    { printf '\033[31m❌ %s\033[0m\n' "$1"; }
yellow() { printf '\033[33m⚠️  %s\033[0m\n' "$1"; }

pass() { green "$1"; PASS=$((PASS+1)); }
fail() { red "$1";   FAIL=$((FAIL+1)); }

run_sql() {
  # Pipe SQL into the configured psql command. Trim trailing whitespace.
  echo "$1" | $PSQL_CMD 2>&1 | tr -d '[:space:]'
}

# Each smoke run uses a unique secret name so concurrent runs don't collide.
SECRET_NAME="vault-smoke-$(date +%s)-$$"
SECRET_PLAINTEXT="sk-smoke-$(openssl rand -hex 8 2>/dev/null || echo 'fallback-12345')"

echo ""
echo "── Vault Smoke Test (ADR-083 precondition) ──────"
echo "Target psql: $PSQL_CMD"
echo "Test secret name: $SECRET_NAME"
echo ""

# ─── Check 1: Extension installed ─────────────────────────────────────────────
echo "── 1. supabase_vault extension"
INSTALLED=$(run_sql "SELECT installed_version FROM pg_available_extensions WHERE name = 'supabase_vault';")
if [[ -n "$INSTALLED" && "$INSTALLED" != "NULL" ]]; then
  pass "supabase_vault installed (version: $INSTALLED)"
else
  fail "supabase_vault NOT installed — migration 016 will fail. Upgrade Supabase image first."
  echo ""
  echo "── Result: 0 passed, 1 failed ──"
  exit 1
fi

# ─── Check 2: Schema objects ──────────────────────────────────────────────────
echo ""
echo "── 2. vault schema objects"
SECRETS_TABLE=$(run_sql "SELECT to_regclass('vault.secrets')::text;")
if [[ "$SECRETS_TABLE" == "vault.secrets" ]]; then
  pass "vault.secrets table exists"
else
  fail "vault.secrets table MISSING"
fi

DECRYPTED_VIEW=$(run_sql "SELECT to_regclass('vault.decrypted_secrets')::text;")
if [[ "$DECRYPTED_VIEW" == "vault.decrypted_secrets" ]]; then
  pass "vault.decrypted_secrets view exists"
else
  fail "vault.decrypted_secrets view MISSING"
fi

# ─── Check 3: create_secret round-trip ────────────────────────────────────────
echo ""
echo "── 3. vault.create_secret round-trip"
SECRET_ID=$(run_sql "SELECT vault.create_secret('$SECRET_PLAINTEXT', '$SECRET_NAME');")
if [[ -n "$SECRET_ID" && "$SECRET_ID" != "NULL" ]]; then
  pass "vault.create_secret returned UUID: $SECRET_ID"
else
  fail "vault.create_secret returned no UUID"
  echo "── Result: $PASS passed, $FAIL failed ──"
  exit 1
fi

# ─── Check 4: Ciphertext at rest in vault.secrets ─────────────────────────────
echo ""
echo "── 4. ciphertext at rest"
RAW_SECRET=$(run_sql "SELECT secret FROM vault.secrets WHERE id = '$SECRET_ID'::uuid;")
if [[ -z "$RAW_SECRET" || "$RAW_SECRET" == "NULL" ]]; then
  fail "vault.secrets row not readable — unexpected RLS configuration"
elif [[ "$RAW_SECRET" == *"$SECRET_PLAINTEXT"* ]]; then
  fail "PLAINTEXT FOUND IN vault.secrets — vault is not encrypting!"
else
  pass "vault.secrets contains ciphertext only (no plaintext leak)"
fi

# ─── Check 5: Decrypt round-trip ──────────────────────────────────────────────
echo ""
echo "── 5. decrypt round-trip"
DECRYPTED=$(run_sql "SELECT decrypted_secret FROM vault.decrypted_secrets WHERE id = '$SECRET_ID'::uuid;")
if [[ "$DECRYPTED" == "$SECRET_PLAINTEXT" ]]; then
  pass "vault.decrypted_secrets returns the original plaintext"
else
  fail "Decrypt mismatch. Expected '$SECRET_PLAINTEXT', got '$DECRYPTED'"
fi

# ─── Check 6: Cleanup (delete_secret) ─────────────────────────────────────────
echo ""
echo "── 6. cleanup"
DELETE_RESULT=$(run_sql "DELETE FROM vault.secrets WHERE id = '$SECRET_ID'::uuid RETURNING id;")
if [[ -n "$DELETE_RESULT" && "$DELETE_RESULT" != "NULL" ]]; then
  pass "test secret deleted ($DELETE_RESULT)"
else
  yellow "Cleanup did not return a deleted ID — manual check recommended"
fi

# Verify it's actually gone
STILL_THERE=$(run_sql "SELECT id FROM vault.secrets WHERE id = '$SECRET_ID'::uuid;")
if [[ -z "$STILL_THERE" || "$STILL_THERE" == "NULL" ]]; then
  pass "test secret no longer exists in vault.secrets"
else
  fail "test secret still present after delete — manual cleanup needed for $SECRET_ID"
fi

# ─── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "── Result: $PASS passed, $FAIL failed ──"
if [[ $FAIL -eq 0 ]]; then
  echo ""
  green "Vault is ready. Safe to run migration 016."
  exit 0
else
  echo ""
  red "Vault preconditions NOT met. Do NOT run migration 016 until fixed."
  exit 1
fi
