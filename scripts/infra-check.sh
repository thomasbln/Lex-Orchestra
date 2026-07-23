#!/usr/bin/env bash
# scripts/infra-check.sh
# Automated infrastructure health check for Lex-Orchestra.
# Run on the host: bash scripts/infra-check.sh

set -euo pipefail

PASS=0
FAIL=0
WARN=0

green()  { echo -e "\033[32m✅ $1\033[0m"; }
red()    { echo -e "\033[31m❌ $1\033[0m"; }
yellow() { echo -e "\033[33m⚠️  $1\033[0m"; }

pass() { green "$1"; PASS=$((PASS+1)); }
fail() { red "$1";  FAIL=$((FAIL+1)); }
warn() { yellow "$1"; WARN=$((WARN+1)); }

echo ""
echo "── 1. Container Status ──────────────────────────"

EXPECTED=(lex-agent supabase-db docker-lex-dashboard-1)
for name in "${EXPECTED[@]}"; do
  status=$(docker inspect "$name" --format '{{.State.Health.Status}} {{.State.Status}}' 2>/dev/null || echo "missing")
  if [[ "$status" == "missing" ]]; then
    fail "$name: NOT FOUND"
  elif [[ "$status" == *"unhealthy"* ]]; then
    fail "$name: UNHEALTHY"
  elif [[ "$status" == *"starting"* ]]; then
    warn "$name: still starting (may need more time)"
  elif [[ "$status" == *"running"* ]] || [[ "$status" == *"healthy"* ]]; then
    pass "$name: OK ($status)"
  else
    warn "$name: $status"
  fi
done

echo ""
echo "── 2. Network — all on docker_lex-net ──────────"

NETWORK="docker_lex-net"
NET_CONTAINERS=$(docker network inspect "$NETWORK" --format '{{range .Containers}}{{.Name}} {{end}}' 2>/dev/null || echo "")

for name in "${EXPECTED[@]}"; do
  if echo "$NET_CONTAINERS" | grep -q "$name"; then
    pass "$name: on $NETWORK"
  else
    fail "$name: NOT on $NETWORK (network mismatch!)"
  fi
done

# Orphaned networks warning
ORPHANED=$(docker network ls --format '{{.Name}}' | grep -E '^lex-net$' || true)
if [[ -n "$ORPHANED" ]]; then
  warn "Orphaned networks found: $ORPHANED — run: docker network rm $ORPHANED"
else
  pass "No orphaned networks"
fi

echo ""
echo "── 3. Service Endpoints ─────────────────────────"

# LangGraph — :8000 is container-internal only (no published port, no auth),
# so probe it from inside the lex-agent container.
if docker exec lex-agent python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/ok', timeout=5)" > /dev/null 2>&1; then
  pass "LangGraph :8000 reachable (in-container)"
else
  fail "LangGraph :8000 unreachable (in-container)"
fi

# approve_api
if curl -sf http://localhost:8001/config/projects > /dev/null 2>&1; then
  pass "approve_api :8001 reachable"
else
  fail "approve_api :8001 unreachable"
fi

# Dashboard
if curl -sf http://localhost:3000 > /dev/null 2>&1; then
  pass "Dashboard :3000 reachable"
else
  fail "Dashboard :3000 unreachable"
fi

echo ""
echo "── 5. Project Config ────────────────────────────"

PROJECTS=$(curl -sf http://localhost:8001/config/projects 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('projects',[])), 'project(s):', ', '.join(p['project_name'] for p in d.get('projects',[])))" 2>/dev/null || echo "ERROR")
if echo "$PROJECTS" | grep -q "0 project"; then
  warn "No projects configured — run wizard at http://<your-host>:3000/setup"
else
  pass "Projects: $PROJECTS"
fi

echo ""
echo "── 6. POST /scan — Pipeline Trigger ────────────"
# CRITICAL TEST: Caught bug where run_id was truncated ([:8]) causing
# LangGraph to silently reject thread creation with "Invalid thread ID".
# Pipeline returned {"ok":true} but no scan ran. dry_run=true avoids
# actual LangGraph execution — only validates the endpoint + UUID format.

SCAN_RESULT=$(curl -sf -X POST http://localhost:8001/scan \
  -H 'Content-Type: application/json' \
  -d '{"project_name": "rand-industries", "dry_run": true}' 2>/dev/null || echo "FAILED")

if echo "$SCAN_RESULT" | grep -q '"ok":true'; then
  RUN_ID=$(echo "$SCAN_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('run_id',''))" 2>/dev/null || echo "")
  UUID_REGEX='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  if [[ ${#RUN_ID} -eq 36 ]] && echo "$RUN_ID" | grep -qE "$UUID_REGEX"; then
    pass "POST /scan: ok, run_id=$RUN_ID (valid UUID)"
  else
    fail "POST /scan: ok=true but run_id='$RUN_ID' is not a valid UUID — LangGraph will silently fail"
  fi
else
  if echo "$SCAN_RESULT" | grep -q "0 project\|no project\|not found"; then
    warn "POST /scan: no project configured — add rand-industries first"
  else
    fail "POST /scan: FAILED — $SCAN_RESULT"
  fi
fi

echo ""
echo "────────────────────────────────────────────────"
echo "Results: ✅ $PASS passed  ❌ $FAIL failed  ⚠️  $WARN warnings"
echo ""

if [[ $FAIL -gt 0 ]]; then
  echo "❌ Infrastructure check FAILED — fix issues above before running /scan"
  exit 1
else
  echo "✅ Infrastructure ready — /scan should work"
  exit 0
fi
