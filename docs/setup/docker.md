# Docker Services

All containers run on your host and are defined in a single root compose file,
`docker/docker-compose.yml`, which `include:`s one compose file per service.
Run `docker compose` from the `docker/` directory.

## requirements.txt lives in the repo root

`requirements.txt` intentionally lives in the **root of the repo** and must not
be moved. It is read in two places:

1. **Docker build** — the `lex-agent` Dockerfile copies it directly:
   ```dockerfile
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   ```
   Without it, `docker compose up --build` fails.

2. **Host install** — for running `make seed-all` outside Docker, see
   [4. Seed the graph from the host](#4-seed-the-graph-from-the-host) below.

---

## 1. Create the Docker network (once)

Every compose file attaches to an external network named `docker_lex-net`
(the `docker_` prefix is deliberate — all seven service composes declare it).
Create it once, before starting any container:

```bash
docker network create docker_lex-net
```

## 2. Start the stack

### Sovereign profile (recommended — fully local, nothing leaves your host)

The local Neo4j and Ollama containers are gated behind compose **profiles**, so a
minimal cloud-backed deployment can skip them. The sovereign path is not a hidden
opt-in — you must pass **both** profile flags:

```bash
cd docker
docker compose --profile with-neo4j --profile with-ollama up -d
```

Starts: `supabase-db`, `neo4j`, `ollama`, `lex-agent`, `lex-dashboard`.

Requires `NEO4J_BACKEND=local` and `LLM_BACKEND=local` in `docker/envs/.env`
(copy `docker/envs/.env.sovereign` as your starting point and fill in the
`__SET_ME__` values).

### API-backend profile (BYOK cloud LLM + external Neo4j)

Bringing your own LLM API key and Neo4j instance? Omit the profile flags — only
the three core services start:

```bash
cd docker
docker compose up -d          # supabase-db, lex-agent, lex-dashboard
```

Set `LLM_BACKEND=api` and `NEO4J_BACKEND=aura` (or `custom`) in
`docker/envs/.env`.

## 3. Pull the inference model (sovereign profile, once)

The Ollama container starts empty. Pull the default model before the first scan —
it is a **9.6 GB** download; expect ~10–15 minutes on a typical connection:

```bash
docker exec ollama ollama pull gemma4:e4b
# check what has arrived:
docker exec ollama ollama list
```

`OLLAMA_KEEP_ALIVE=-1` keeps it resident afterwards. (The `ollama-warmup`
container fires a best-effort warm-up request on startup; it becomes effective
once the model is present.)

**First-scan expectation:** on CPU-only hardware the first full scan takes a few
minutes — measured 4 min 02 s end-to-end on a 12-core mini PC without GPU,
including local LLM classification and rendering of all nine documents. The scan
status page tracks each step live (the default `SCAN_WAIT_TIMEOUT=1800` has
ample headroom).

### Enable pgvector (once)

```bash
docker exec supabase-db psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

> LangGraph checkpoint tables are created automatically on the first workflow run.

## 4. Apply the database schema + seed the graph (host)

Both steps run on the **host** and connect to the containers on `localhost`.
Debian/Ubuntu/Mint ship no bare `python`, and PEP 668 blocks a system-wide
`pip install`, so install the dependencies into a repo-local virtualenv:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

make db-migrate      # relational schema: migrate.sql + supabase/migrations (idempotent)
make seed-all        # graph: layer manifest + modules + ADR-100 validator (ADR-130)
make seed-validate   # re-run the §4.1–§4.4 invariants, no writes
```

`db-migrate` creates every table the pipeline writes (projects, scan results,
generated docs, owner measures, …) in the `supabase-db` container. Without it,
project creation and scans fail with "relation does not exist".

`make` picks up `.venv/bin/python` automatically (override with
`make PYTHON=... seed-all`). `TARGET` defaults to `local`
(`bolt://localhost:7687`); set `NEO4J_PASSWORD` in `docker/envs/.env` to match
the container's `NEO4J_AUTH`.

### Install Pandoc (host binary, once)

`pypandoc` in `requirements.txt` is only the Python wrapper; the Pandoc binary
is installed separately:

```bash
sudo apt-get install -y pandoc
pandoc --version   # verify
```

> Pandoc is only needed for Markdown → PDF export in the Document Architect.
> Everything else works without it.

## Check container status

```bash
docker compose -f docker/docker-compose.yml ps
```

## Restart after a git pull

```bash
cd docker
docker compose --profile with-neo4j --profile with-ollama up -d --build
```

## Troubleshooting

**Docker CE fails to start on Linux Mint / Ubuntu after replacing `docker.io`:**
if you uninstalled the distro's `docker.io` package and installed the official
`docker-ce`, systemd may keep the old failed unit state and refuse to start the
new daemon. Fix:

```bash
sudo systemctl reset-failed docker.service
sudo systemctl start docker
```

## ARM64 note (aarch64 hosts)

- Use `psycopg2-binary` instead of `psycopg2` — native ARM64 wheels available.
- `lxml` builds from source if no wheel exists → may take a few minutes.
- `langgraph` and all core dependencies ship ARM64 wheels.

## Security posture

`approve_api` (:8001) and the dashboard (:3000) ship **without authentication**
(trusted-LAN design, ADR-129 PR 17 / audit K10). Do not port-forward or expose
them to the internet. For remote access use an authenticating reverse proxy or
a VPN (e.g. Tailscale). `X-Scan-Secret` only guards the internal
`PATCH /scan/{run_id}/step` endpoint — nothing else.

### CORS (dashboard ↔ API)

By default `approve_api` accepts browser requests from **every private-network
origin** — RFC 1918 addresses (`10.x`, `172.16–31.x`, `192.168.x`), `localhost`
and `*.local` mDNS names, any port. That matches the trusted-LAN design above:
open the dashboard from any machine in your LAN and it just works (F24 — the
old default was a hardcoded host list, and the dashboard on any other host
showed "0 configured" because the browser silently blocked the API responses).

Set `CORS_ORIGINS` in `docker/envs/.env` (comma-separated exact origins,
e.g. `https://compliance.example.com`) **only** when you deliberately expose
the dashboard beyond the LAN — behind an authenticating reverse proxy, per the
posture above. An explicit list replaces the private-network default entirely.
