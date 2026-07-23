# Testing

## Strategy

Lex-Orchestra tests on two levels:

**Unit tests** — individual modules in isolation  
**Integration tests** — full workflow against real infrastructure (they skip with a reason when the environment is not configured)

No DB mocking — tests run against the real Supabase instance. This is intentional: mocking the database would not reliably verify PII separation.

## Directory

```
tests/
├── fixtures/                 ← Sample files for Scout tests
│   ├── docker-compose.yml    ← Typical stack with known services
│   ├── package.json          ← NPM project with sub-processors
│   └── env.example           ← .env with credential patterns (fake values only)
│
├── test_smoke.py             ← ✅ Infrastructure connectivity checks
├── test_asset_translator.py  ← ✅ PII separation
├── test_graph_client.py      ← ✅ Neo4j queries
├── test_workflow.py          ← ✅ Full scan workflow
└── test_scout.py             ← 🔲 TODO: Infrastructure scanner
```

## Running tests

```bash
# Install once
pip install pytest pytest-asyncio --break-system-packages

# Smoke tests (run first)
pytest tests/test_smoke.py -v

# All tests
pytest tests/ -v
```

## Key assertions per module

### test_asset_translator.py — PII-separation verification

The most critical test in the system:

```python
def test_anonymize_no_real_names():
    """Core assertion: anonymize() must never return real asset names."""
    anon = translator.anonymize(records)
    for item in anon:
        assert item.get("name") not in real_names
```

If this test fails → PII leak → the UUID-Only Pattern is violated.

### test_graph_client.py

- Connection to Neo4j
- `get_compliance_requirements(["Stripe"])` → returns AVV, SCC
- `get_compliance_requirements(["OpenAI"])` → returns GPAI risk level
- MERGE idempotency: running the query twice produces no duplicates

### test_workflow.py

- `build_workflow()` compiles without error
- Dry-run invocation → all 5 nodes complete, zero errors
- `graph_result` contains no PII from fixture files
- Checkpointer persists state to Supabase

## CI/CD (Phase 3)

Planned: GitHub Action on `git push` → `pytest tests/` runs automatically.  
Prerequisite: Pi as self-hosted runner or tests against a staging DB.
