# lex-agent — LangGraph Workflow Container

LangGraph compliance-pipeline container (architecture detected automatically —
x86_64 or arm64, ADR-053).

## Prerequisites

- `docker_lex-net` Docker network exists: `docker network create docker_lex-net`
- `supabase-db` container is running (see `docker/supabase/`)
- `docker/envs/.env` filled (copy `docker/envs/.env.sovereign` as your starting point)

## Build & Start

```bash
cd docker/lex-agent
docker compose up -d --build
```

Build only (without starting):

```bash
docker build -t lex-agent docker/lex-agent/
```

## Run a Scan

```bash
# Dry-run — no LLM calls, no DB writes
docker exec lex-agent python -m src.workflow.main \
  --project "MyProject" --repo . --dry-run

# Full scan against a repo
docker exec lex-agent python -m src.workflow.main \
  --project "MyProject" \
  --repo https://github.com/user/project \
  --url https://myproject.de

# Scan Lex-Orchestra itself (self-scan)
docker exec lex-agent python -m src.workflow.main \
  --project "Lex-Orchestra" --repo . --dry-run
```

## Logs

```bash
docker logs lex-agent -f
docker logs lex-agent --tail 50
```

## Notes

### psycopg[binary] vs psycopg2-binary

Two PostgreSQL drivers are installed:

| Package | Used by |
|---|---|
| `psycopg2-binary` | `AssetTranslator` (sync, via requirements.txt) |
| `psycopg[binary]` | `langgraph-checkpoint-postgres` → `PostgresSaver` (async) |

Both are required. `psycopg[binary]` is installed explicitly in the Dockerfile
because `langgraph-checkpoint-postgres` does not pull it in automatically on ARM64.

### Live Code Reload

`../../src` is mounted to `/app/src` at runtime, so code changes on the host
are reflected immediately — no rebuild needed during development.

