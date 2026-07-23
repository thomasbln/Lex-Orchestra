# Tests — Lex-Orchestra

~85 test files. The default battery is infrastructure-free: builder, unit and
linter suites run against `tests/fixtures/` and the golden content models in
`tests/golden/` with mocked DB/graph sessions.

Integration tests (graph / DB / LLM) skip with a reason when the required
environment is not configured:

| Dependency | Env vars |
|---|---|
| Neo4j | `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` |
| Postgres | `DATABASE_URL` (some suites: `MCP_SUPABASE_URL`) |
| Ollama | `OLLAMA_URL` + a pulled model |

Run everything:

```bash
.venv/bin/python -m pytest -q
```

Notes:

- `tests/conftest.py` loads `.env` via python-dotenv with `override=True` —
  the `.env` file is the single source of truth for test configuration.
- Golden fixtures: regenerate via `scripts/dump_fixtures.py` after intentional
  ContentModel changes, and review the diff before committing.
