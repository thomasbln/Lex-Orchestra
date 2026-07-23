# docs/gaps/

This directory holds **domain gap notices** — files that document points where a
Lex-Orchestra subagent (or Thomas) encountered knowledge it could not source
from existing graph data, ADRs, or `docs/sources/`.

**Read first:** `docs/principles/domain-gap-handling.md` — defines the principle,
format, and lifecycle.

---

## What lives here

**Active gaps** (`docs/gaps/*.md`): Open decisions blocking one or more tasks.
Each file follows the format defined in `domain-gap-handling.md`.

**Resolved gaps** (`docs/gaps/done/*.md`): Historical record of how gaps were
resolved (source acquired, ADR written, scope cut, external consulted).

## File naming

```
docs/gaps/YYYY-MM-DD-<topic>-<short-description>.md
```

Examples:
- `2026-06-15-avv-no-dsk-source.md`
- `2026-06-18-ai-act-gpai-boundary.md`
- `2026-07-02-stripe-country-property.md`

## When to add a gap notice

See `docs/principles/domain-gap-handling.md` § "When to write a gap notice".

Briefly: when an agent encounters regulatory, juristic, or domain-specific
knowledge that cannot be sourced from graph + ADRs + `docs/sources/` — stop,
document, do not improvise.

## How gaps get resolved

Each gap has a designated **decider** (Thomas, external legal expert, or
"needs research"). Resolution paths:

1. **Source acquisition** — add PDF to `docs/sources/`, update gap with reference
2. **Decision recording** — write an architecture decision record, link it from the gap
3. **Scope cut** — feature deferred, gap closed with "deferred" status
4. **External consultation** — document advice, update graph if applicable

After resolution: move file to `docs/gaps/done/` and append a Resolution
section per the format in `domain-gap-handling.md`.

## Why this exists

Lex's value proposition is **deterministic, evidence-based compliance outputs**.
The moment an agent fabricates a compliance fact from training data, that
proposition is broken. Gap notices are the operational mechanism that prevents
this — by making the discipline visible and resolvable instead of silent and
risky.
