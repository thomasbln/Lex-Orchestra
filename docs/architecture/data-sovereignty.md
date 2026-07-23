# Data Sovereignty — What stays where

> **"Your infrastructure stays your infrastructure."**
> No external service ever sees what runs in your stack,
> which keys you use, or which documents were generated.

## The three zones

```
ZONE 1 — YOUR NETWORK (your host)                     [private]
  Supabase (self-hosted)
  ├── Scout findings: "Stripe in package.json"
  ├── Generated documents: ToM, AVV, VVT (Markdown)
  ├── Compliance status per project
  ├── Agent memory: learned preferences
  └── LangGraph checkpoints: workflow state
  → NEVER leaves the network

ZONE 2 — GRAPH BRAIN (Neo4j — local container by default)  [abstract knowledge]
  Knowledge graph
  ├── Laws: GDPR Art. 28, EU AI Act, NIS2, CRA, BSI
  ├── Services: "Stripe" as a generic service type
  ├── UseCase nodes: deployer risk classification
  ├── DocumentTypes: AVV, SCC, ToM, VVT
  └── Relationships: REQUIRES, BASED_ON, IMPLEMENTS, CLASSIFIED_BY
  → Contains NOT ONE customer-specific data point
  → Optional managed cloud graph: same abstract content — nothing project-specific

ZONE 3 — LLM (Gemma 4 via Ollama — local by default)   [classification layer]
  Input:  "unknown dependency: 'stripe-php'"
  Output: canonical service name + category
  → Classifies unknown components — it does NOT write legal text
  → Documents are assembled deterministically from the graph
  → NEVER sees: customer, key, file, configuration, domain
```

## What the LLM sees — and what it does not

```
❌  LLM does NOT see:
    - That this is my-project.io
    - Which API key is active
    - Where a service is integrated (checkout.js, line 42)
    - IP addresses, ports, database paths
    - Finished compliance documents

✅  LLM sees ONLY:
    - dependency names it must classify ("stripe-php" → Stripe, payment)
    - abstract service types ("payment provider, USA")
```

**This is not a policy — it is architecture.**
The LLM structurally has no access to customer-specific data — and in the
default sovereign profile it runs on your own hardware, so nothing reaches
any LLM API at all.

## The UUID-Only Pattern

The mechanism that enforces this separation is the UUID-Only Pattern.
Every sensitive entity the Scout detects is immediately translated into
an anonymised UUID before anything leaves the local network:

```
Scout finds:           Local PostgreSQL:          Graph:
"STRIPE_SECRET_KEY"  → uuid: abc-123          →  {id: "abc-123",
 in checkout.js:42     name: "stripe_key"         type: "api_key",
                       file: "checkout.js"         encrypted: false}
                       line: 42

Neo4j returns:       → UUID lookup            → Document Architect:
Controls for           PostgreSQL fetches          assembles ToM/AVV
"abc-123"              full context               with real details
```

The LLM reasons about `abc-123`. The document is assembled locally with
real names. The LLM never sees the real names.

(In the current release the graph receives only canonical service names and
categories — the per-project asset detail, including any UUID mapping, stays
entirely in local Postgres.)

This is the same principle described as "Identity-Agnostic AI" in the
[Privacy by Architecture article](https://medium.com/@thomasrehmer/privacy-by-architecture-why-your-knowledge-graph-should-only-store-uuids-a26fb375c908)
(Thomas Rehmer, Feb 2026) — written before Lex-Orchestra existed, now
implemented as the core architectural constraint of the system.

**The threat model this defeats:**

- **Infrastructure leak:** A complete graph dump gives an attacker only
  anonymous UUIDs — no file names, no service names, no real structure.
- **Prompt injection:** An attacker cannot extract PII through clever prompts
  because it physically does not exist in the graph's context.
- **The logging trap:** PII never ends up in LLM provider error logs because
  it is never sent. Standard RAG systems silently violate GDPR every time an
  error is logged with real customer context in the payload.

## Data table

| Data category | Location | Reason |
|---|---|---|
| Source code | 100% local (your host) | Never in cloud |
| Secrets / API keys (values) | NOT stored | Only presence is detected |
| Tech entities (anonymised) | Neo4j (local by default) | Generic types only: "Stripe", "Postgres" |
| Regulatory logic (laws) | Neo4j (local by default) | Public knowledge |
| Project state | Supabase local | Proprietary infrastructure details |
| Generated documents | Local (`legal/drafts/` + dashboard) | Never leave the host |

## GDPR-compliant by design

| GDPR principle | Article | Implementation |
|---|---|---|
| Accountability | Art. 5 Para. 2 | Every decision traceable to a graph node |
| Data minimisation | Art. 5 Para. 1 lit. c | LLM receives only what it needs |
| Purpose limitation | Art. 5 Para. 1 lit. b | Customer data used locally for compliance only |
| Integrity & confidentiality | Art. 5 Para. 1 lit. f | Infrastructure details never leave the network |
| No third-country transfer | Art. 44 ff. | Neo4j: no customer reference. LLM: no customer reference |

## Source Verification Rule

All regulatory content written into the graph must come from a verified source
(the project's source verification rule):

- `confidence: 1.0` = read directly from the official source — EUR-Lex or the
  official PDF (registry: `docs/sources/SOURCES.md`)
- `confidence: 0.9` = preliminary, `note_unverified` property set
- `confidence: 0.5` = training knowledge only — **never written to the graph**

Query to find all nodes that need verification:
```cypher
MATCH (n)
WHERE n.note_unverified IS NOT NULL
RETURN labels(n)[0] AS type, n.confidence, n.note_unverified
```

## ADR-001: PII separation

The technical implementation is documented in ADR-001 (PII separation,
internal decision record).

**Core rule:** Neo4j and the LLM receive only UUIDs and anonymised asset types —
never file names, variable names, paths, or code snippets.

## Further reading

- [Privacy by Architecture: Why Your Knowledge Graph Should Only Store UUIDs](https://medium.com/@thomasrehmer/privacy-by-architecture-why-your-knowledge-graph-should-only-store-uuids-a26fb375c908) — Thomas Rehmer, Feb 2026 — the UUID-Only Pattern and Identity-Agnostic AI as published concept
