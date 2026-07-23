# Lex-Orchestra — Context Graph

> Lex-Orchestra is not a Knowledge Graph.
> It is a **Context Graph** — a living knowledge model that not only stores
> rules but understands what applies to *this* project, *right now*,
> *with what degree of certainty*.

The graph knows not just what applies, but when it applies (enforcement dates on law
nodes), for whom it applies (jurisdiction layers), and where the knowledge comes from
(source and license provenance on nodes and relationships).

---

![Lex-Orchestra Context Graph — the four layers](../images/architecture-context-graph.svg)

---

## Understanding the Graph: The Subway Network

The best way to understand the compliance graph is not as a spreadsheet or a
list of rules — but as the **network map of a large subway system**.

**Stations** are the individual nodes. They can be:
- Technical components (`postgres`, `stripe`, `aws-s3`)
- Specific paragraphs from a law or framework (`GDPR Art. 28`, `BSI CON.3`)
- Use cases (`customer_service_chatbot`, `hr_recruitment_screening`)
- Your project's detected assets (`payment_service uuid-abc123`)

**Lines connecting the stations** are the edges in the graph — they represent
logical and legal dependencies. `Stripe → REQUIRES → AVV`,
`postgres → HAS_CATEGORY → database → SUBJECT_TO_CONTROL → BSI CON.3 (Backup Concept)`.

**Running a route** is what happens during a compliance scan:
The Infrastructure Scout identifies a technical entity — say, a Postgres database
running on a local SSD. This entity becomes a new station in the network.
The system then traces the lines: it follows the edges deterministically
from your detected component to the relevant regulatory nodes.

The result is not "this *might* be relevant" (probabilistic LLM guessing),
but a **mathematically precise path**: *because you use component X, you
necessarily trigger requirement Y from BSI CON.3 on backup concepts.*

This is the difference between a classic legal AI tool — which acts like a
doctor diagnosing by SMS questionnaire, guessing based on statistical patterns —
and Lex-Orchestra, which acts like an MRI scanner: it does not ask about your
architecture, it **measures** it.

```
Traditional LLM tool:   "Your setup might have compliance implications..."
Lex-Orchestra:          "Postgres + personal_data → GDPR Art. 32 + BSI CON.3
                          AVV required with: Stripe (dpa_url: stripe.com/de/legal/dpa)
                          source: EUR-Lex / BSI — last_verified on every node"
```

The law is not a text pasted over the top of your technology.
It becomes a **technical dependency** in your system — like a software library
you import. Deterministic. Traceable. Auditable.

---

## RAG → GraphRAG → Context Graph: The Progression

Most legal AI tools stop at step one. Lex-Orchestra is at step three.
Understanding the difference explains exactly *why* determinism matters in compliance.

### Step 1 — Standard RAG (Retrieval-Augmented Generation)

The dominant approach since 2023. Documents are converted into numerical vectors
(embeddings) and stored in a database. A question finds the most "similar" text chunks,
which are passed to an LLM as context.

**Works well for:** Summaries, "what does this law say?", document search.

**Fails at:**
- **Negative queries:** "Which contracts do NOT have audit rights?" — vectors cannot
  represent the *absence* of a relationship. The query returns contracts *mentioning*
  audit rights, the exact opposite of what was asked.
- **AND logic:** "Find contracts with Revenue Sharing AND Non-Compete" — similarity
  search cannot guarantee both conditions exist on the same document.
- **Boolean logic:** `NOT`, `AND`, `ONLY IF` — standard similarity does not understand
  logical operators.
- **Counting and aggregation:** You cannot reliably count across a set of vectors.

The core problem: **vector search finds similarity, but legal compliance needs structure.**
An LLM that is "85% confident" about a legal requirement is not an acceptable audit answer.

```
Standard RAG:   "Your setup might have compliance implications..."
                (probabilistic, no source, no trace, cannot be audited)
```

### Step 2 — GraphRAG

GraphRAG (Knowledge Graph + RAG) adds structure. Documents are not stored as text
chunks but as explicit relationships:

```
Contract → CONTAINS → Clause → OF_TYPE → "Audit Rights"
```

Now the impossible query becomes trivial:
```cypher
MATCH (c:Contract)
WHERE NOT EXISTS {
  MATCH (c)-[:CONTAINS]->(:Clause)-[:OF_TYPE]->(ct:ClauseType)
  WHERE ct.name = 'Audit Rights'
}
RETURN c.name
```
Result: mathematically precise, 100% recall, no hallucinations.

**GraphRAG is correct about *what* is in the documents.**
But it is still static — it stores facts, not context.

`Stripe → REQUIRES → AVV` — true for everyone, always, everywhere.

It does not know: *Does this AVV requirement apply to YOUR project? Are you in the EU?
Did you already sign it? Is the regulation still current? What is the confidence level?*

### Step 3 — Context Graph (what Lex-Orchestra builds)

A Context Graph is GraphRAG made *situational and temporal*.

It does not just store that `Stripe requires an AVV`.
It stores that **this specific project**, **scanned on this date**, **in this jurisdiction**,
**with this confidence level**, requires an AVV — and here is the DPA signing URL.

The differences in concrete terms:

| Dimension | Standard RAG | GraphRAG | Context Graph |
|---|---|---|---|
| Data structure | Flat vectors | Graph relationships | Graph + temporal + project state |
| Query logic | Semantic similarity | Structural patterns | Structural + boolean + temporal |
| Negative queries | ❌ fails | ✅ works | ✅ works |
| Personal to this project | ❌ generic | ❌ generic | ✅ scanner adds project nodes |
| Time-aware | ❌ static | ❌ static | ✅ `applies_from`, `confidence`, `last_verified` |
| Self-describing gaps | ❌ no | ❌ no | ✅ `KnowledgeSource {status: "missing"}` |
| Regulatory change detection | ❌ no | ❌ no | ✅ `NewsEvent -[:AMENDS]→ Law` |
| Auditability | ❌ black box | ⚠️ partial | ✅ every finding fully traceable |

```
GraphRAG:       "Stripe → REQUIRES → AVV"
                (correct, but generic — applies to everyone)

Context Graph:  "Project uuid-abc, scanned 2026-03-22, jurisdiction DE:
                 Stripe detected (confidence: 1.0, verified) → REQUIRES → AVV
                 DPA: https://stripe.com/de/legal/dpa
                 GDPR Art. 28 applies_from: 2018-05-25, confidence: 1.0
                 Previous scan: same finding (stable)"
```

The Context Graph is not just smarter retrieval. It is a living mirror of
one specific project's legal reality at one specific point in time.

> For the broader theoretical framing of Context Graphs and why this term
> is gaining traction in the industry, see the
> [Context Graph Manifesto](https://trustgraph.ai/news/context-graph-manifesto/)
> (TrustGraph, December 2025).

---

## What is the difference between Knowledge Graph and Context Graph?

A **Knowledge Graph** stores facts:
`Stripe → REQUIRES → AVV`

A **Context Graph** knows the context of those facts:
- *Why* does it apply? (Legal basis as a node, not a string)
- *Since when* does it apply? (Temporal properties on every Law node)
- *For whom exactly*? (ProjectAsset nodes from the scanner, UUID-based)
- *How reliable is the knowledge*? (confidence property, verified flag)
- *What is still missing*? (KnowledgeSource nodes with status: "missing")
- *For which jurisdiction*? (jurisdictions property on every Law node)

The core difference: a Knowledge Graph is a handbook.
A Context Graph is a mirror — personalised to the real infrastructure,
the real jurisdiction, the real point in time.

---

## The four layers of the Context Graph

### Layer 1 — Seed Layer Architecture ✅

```
Service → REQUIRES → DocumentType → BASED_ON → Law
```

~470 nodes on a fresh seed. Deterministic. Global-first, not EU-first.

The graph is structured as independent seed layers.
EU is one jurisdiction among many — not the universal default:

```
00_global/        OWASP, NIST CSF, BSI IT-Grundschutz   → applies worldwide
10_jurisdiction/  GDPR, AI Act, NIS2, CRA, DORA + German national law
20_frameworks/    BYOS slots: ISO 27001, BSI C5, AIC4   → license-gated, bring your own
```

A layer manifest controls what a deployment seeds; license-gated layers stay
empty until you bring the source yourself (BYOS).
Full catalogue: [../reference/graph-layers.md](../reference/graph-layers.md)

---

### Layer 2 — Temporal Graph + Confidence ✅ complete

Every `Law` node has a time dimension — all 55 Law nodes fully populated,
verified against official PDFs or EUR-Lex:

```cypher
(:Law {
  name: "CRA", article: "14",
  valid_from:    date("2024-12-10"),
  applies_from:  date("2026-09-11"),
  last_verified: date("2026-03-21"),
  confidence:    1.0,
  jurisdictions: ["EU"],
  source:        "EUR-Lex OJ:L_202402847"
})
```

What this enables:

```python
# graph_client.py
def get_upcoming_deadlines(self, days: int = 90) -> list[dict]:
    """Return laws whose applies_from is within N days from today."""
```

Output: `"CRA Art. 14 applies in 174 days — vulnerability reporting obligations"`

The graph now knows not just *what* applies — but *when* and *for whom*.

**Confidence scale:**

| Value | Meaning |
|---|---|
| `1.0` | Primary law — read directly from official PDF or EUR-Lex |
| `0.9` | Established secondary source or preliminary — `note_unverified` set |
| `0.7` | Partially superseded or uncertain (e.g. TMG replaced by DDG) |
| `0.5` | Training knowledge only — **not allowed in any layer file** |

---

### Layer 3 — Context Graph: Scanner + UseCase Nodes

Two components make the graph specific to *this* project:

**Scanner as input layer:**

Without scanner: generic graph, applies to everyone.
With scanner: project-specific graph, applies to *this* project.

```cypher
MERGE (p:Project {uuid: "uuid5(repo_url)"})
MERGE (a:ProjectAsset {uuid: "asset-uuid", type: "payment_service"})
MERGE (p)-[:HAS_ASSET {scanned_at: datetime()}]->(a)
MERGE (a)-[:MAPS_TO]->(s:Service {name: "Stripe"})
```

Neo4j never receives real file names or code. In the current release the
per-project scan state lives in local Postgres (scan signals) and is joined
with the graph at render time; `Project`/`ProjectAsset` nodes in the graph
itself are on the roadmap (see the table below).

Detection is layered and local: pattern matching against a curated signal map first;
anything unknown is classified by a local LLM (Gemma 4 via Ollama) running on your
machine. Only canonical service names and anonymised identifiers ever reach the graph —
never file names, variables, code content or secrets (the logbook and graph enforce
this as an invariant, not a convention).

**UseCase nodes — deployer risk classification:**

Provider risk (OpenAI = GPAI) is not the same as deployer risk.
A user building a chatbot with Claude has `Limited` risk (Art. 50),
not GPAI — that is Anthropic's concern.

```cypher
(:UseCase {
  type: "customer_service_chatbot",
  risk_level: "Limited",
  eu_ai_act_article: "50",
  reason: "Art. 50 — users must be informed they interact with AI"
})

(:UseCase {
  type: "hr_recruitment_screening",
  risk_level: "High",
  annex_iii_nr: "4",
  reason: "Annex III Nr. 4 — employment and personnel management"
})
```

What Layer 3 enables:
- **Rescan = delta**: new service → new edge → new `compliance_task`
- **Project-specific queries**: which obligations apply to *this* project?
- **Correct AI Act output**: deployer obligations, not provider obligations

---

### Layer 4 — Self-Describing Context Graph 🔲 planned

The design goal: the graph knows what it does not know — and detects when
knowledge becomes stale. Today every node carries source / license /
last_verified provenance; the gap and news nodes below are the next step.

```cypher
// Gap detection
MERGE (k:KnowledgeSource {name: "ISO 42001"})
SET k.status = "missing", k.priority = "high",
    k.reason = "AI Management System — relevant for EU AI Act Art. 9"
```

The Legal News Scanner (roadmap) will write `NewsEvent` nodes:

```cypher
MERGE (n:NewsEvent {source: "EUR-Lex", url: "...", date: date("2026-04-15")})
MERGE (n)-[:AMENDS]->(l:Law {name: "EU AI Act"})
SET n.verified = false
```

When a `NewsEvent -[:AMENDS]→ Law` is created:
- Law node confidence drops: `1.0 → 0.7`
- Affected generated documents get `staleness_flag: true`
- The dashboard flags it: *"EU AI Act changed — your docs may be outdated"*

After human verification:
- `confidence` returns to `1.0`, `note_unverified` cleared
- Documents can be regenerated with a re-scan

What this enables:
- **Gap detection as query**: `MATCH (k:KnowledgeSource {status: "missing"}) RETURN k`
- **Staleness detection**: `MATCH (n) WHERE n.note_unverified IS NOT NULL RETURN n`
- **Dynamic retrieval**: LLM in Node 3 queries graph structure, not just data

---

## Extension, not refactoring

All four layers are **additive**. No existing node or relationship needs to change.

| What | Type | Status |
|---|---|---|
| `applies_from`, `confidence`, `jurisdictions` on Law nodes | Extension | ✅ done |
| Seed layer architecture | Refactoring | ✅ done |
| UseCase nodes — deployer risk | Extension | ✅ done |
| `get_upcoming_deadlines()` in graph_client | Extension | 🔲 next |
| `KnowledgeSource` nodes | Extension | 🔲 next |
| `ProjectAsset` nodes (Scanner output) | Extension | 🔲 v1 |
| `NewsEvent` nodes + confidence decay | Extension | 🔲 v1 |
| `DataCategory` as real nodes (ontology) | **Refactoring** | optional |

The ontology layer (DataCategory, ProcessingBasis as nodes instead of strings)
is the only real refactoring — relevant only for the eRecht24 Delta Engine.

---

## Context Graph as prerequisite for the self-learning orchestrator

This is not a separate feature — it is the logical consequence.

An agent can only learn if it has a personalised, temporal context.
A static knowledge graph gives it no basis for change — no deltas,
no development, no user feedback.

The Context Graph is the infrastructure that makes self-learning possible:

```
Rescan → new ProjectAsset edge
         ↓
         delta to last scan detectable
         ↓
         compliance_task generated
         ↓
         user confirms or rejects in the dashboard
         ↓
         feedback signal: what was relevant, what was not?
         ↓
         Preference node per user
         ↓
         next scan weights findings by learned preferences
```

Without Layer 3 (ProjectAsset nodes from scanner) there is no delta.
Without delta there is no learning signal.
Without a learning signal the orchestrator remains static.

The self-learning orchestrator is the logical consequence of a complete
Context Graph — not a separate system.

---

## Where we are in the GraphRAG+ progression

Daniel Davis describes an 8-stage progression in the
[Context Graph Manifesto](https://trustgraph.ai/news/context-graph-manifesto/).
The stages from GraphRAG onwards are directly relevant to Lex-Orchestra:

| Stage | Davis | Lex-Orchestra |
|---|---|---|
| 3 — GraphRAG | Graph relationships replace text chunks | ✅ Neo4j property graph, Cypher traversal |
| 4 — Ontology RAG | Structured ontologies for precision retrieval | ✅ Law/Control/UseCase as typed node hierarchy |
| 5 — Specialised retrieval for data types | Temporal, accuracy-sensitive, anomaly retrieval | ✅ `applies_from`, `confidence`, deadline queries |
| 6 — Self-describing stores | Graph carries metadata about its own structure | ⚠️ partial: source/license/last_verified provenance on every node; `KnowledgeSource` gap nodes planned |
| 7 — Dynamic retrieval strategies | LLM derives retrieval logic it has never seen before | 🔲 planned: LLM generates Cypher from schema, not fixed methods |
| 8 — Closing the loop | System reingests its outputs to adjust future retrieval | 🔲 planned: preference notes + scan delta feedback |

Stages 3–5 are implemented, stage 6 partially (provenance metadata everywhere,
self-describing gap nodes planned). Stages 7–8 are the explicit next evolution.

**One architectural constraint shapes everything:** data sovereignty.
Lex-Orchestra's Context Graph operates under a hard constraint that most
GraphRAG implementations do not have — no user data, code, or infrastructure
details leave the local network. The graph receives only anonymised UUIDs
and asset types. This rules out cloud-based graph enrichment
approaches but makes the system deployable in compliance-sensitive environments
where sending proprietary code to an external service is not an option.

This is not a limitation of ambition — it is a deliberate design choice.
The Context Graph is useful precisely *because* it can reason about sensitive
infrastructure without ever seeing it.

---

## Summary

```
Layer 1 — Seed Layer Architecture    Handbook    (deterministic, global + jurisdictions)
Layer 2 — Temporal Graph             Calendar    (what applies, when, for whom, how certain)
Layer 3 — Context Graph              Mirror      (what applies to THIS project)
Layer 4 — Self-Describing            Compass     (what is missing or stale)
                                                          ↓
                                           Self-Learning Orchestrator
                                      (feedback via /approve + Preference nodes)
```

---

## Further reading

- [graph.md](graph.md) — Node types, schema, seed queries
- [../reference/graph-layers.md](../reference/graph-layers.md) — Layer catalogue, global structure, contribution guide
- [data-sovereignty.md](data-sovereignty.md) — What stays where
- [Context Graph Manifesto](https://trustgraph.ai/news/context-graph-manifesto/) — TrustGraph, Dec 2025 — industry framing of the Context Graph concept
- [GraphRAG for Legal AI: Why Knowledge Graphs Beat Vector Search](https://medium.com/@thomasrehmer/graphrag-for-legal-ai-why-knowledge-graphs-beat-vector-search-01436abfe095) — Thomas Rehmer, Dec 2025 — GraphRAG foundations + CUAD proof-of-concept
- [Claude + Neo4j with MCP: Turning Your Knowledge Graph into an AI Interface](https://medium.com/@thomasrehmer/claude-neo4j-with-mcp-turning-your-knowledge-graph-into-an-ai-interface-910ca04e9942) — Thomas Rehmer, Jan 2026 — MCP as natural language interface to the graph
- [Privacy by Architecture: Why Your Knowledge Graph Should Only Store UUIDs](https://medium.com/@thomasrehmer/privacy-by-architecture-why-your-knowledge-graph-should-only-store-uuids-a26fb375c908) — Thomas Rehmer, Feb 2026 — UUID-Only Pattern and PII separation
