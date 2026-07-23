# Neo4j Knowledge Graph

> Neo4j is the **long-term memory** of the agent.
> All deterministic compliance knowledge lives here —
> not in the LLM, not in Postgres, but in the graph.
>
> **Concept:** Lex-Orchestra uses Neo4j not as a simple Knowledge Graph
> but as a **Context Graph** — see [context-graph.md](context-graph.md).
>
> **Scale:** The graph uses a seed layer architecture (ADR-009).
> EU is one jurisdiction among many — see ADR-009
> and [../reference/graph-layers.md](../reference/graph-layers.md).

## Two data stores — clear roles

| Store | Role | Contains |
|---|---|---|
| **Neo4j** (local container by default) | Knowledge | Laws, controls, service mappings, relationships |
| **Supabase** (local) | State + output | Scout findings, documents, compliance status |

## Node types

### Layer 1 — Technical (static)

```cypher
(:Service {
  name: "Stripe",
  category: "payment",
  country: "USA",
  gdpr_adequate: false,
  avv_required: true,
  dpa_url: "https://stripe.com/de/legal/dpa",
  ai_act_relevant: false
})
```

### Layer 2 — Legal (static, initially seeded)

```cypher
(:Law {
  name: "GDPR", article: "28",
  title: "Controller-Processor (DPA obligation)",
  applies_from: date("2018-05-25"),
  confidence: 1.0,
  jurisdictions: ["EU"],
  source: "EUR-Lex OJ:L_201611977, Art. 99"
})

(:DocumentType { type: "AVV", name_de: "Auftragsverarbeitungsvertrag" })
(:RiskLevel { level: "GPAI", act: "EU_AI_Act" })
```

### Layer 3 — Geopolitical

```cypher
(:Country { name: "USA", gdpr_adequate: false, requires_sccs: true })
(:TransferMechanism { name: "SCCs", legal_basis: "GDPR Art. 46 Para. 2 lit. c" })
```

### Layer 4 — Compliance controls

```cypher
(:Control { framework: "ISO_27001", id: "A.8.1", title: "Inventory of Assets" })
(:Control { framework: "BSI_Grundschutz", id: "ORP.4", title: "IAM" })
```

### Layer 5 — Dynamic (Context Graph extensions)

```cypher
// Temporal (Layer 2) — all Law nodes have applies_from
(:Law { name: "CRA", article: "14", applies_from: date("2026-09-11"), confidence: 1.0 })

// UseCase nodes — deployer risk classification (ADR-010)
(:UseCase { type: "customer_service_chatbot", risk_level: "Limited", eu_ai_act_article: "50" })
(:UseCase { type: "hr_recruitment_screening", risk_level: "High", annex_iii_nr: "4" })

// Scanner output (Layer 3)
(:Project { uuid: "..." })
(:ProjectAsset { uuid: "...", type: "payment_service" })

// News Scout (Layer 4 — ADR-011)
(:NewsEvent { source: "EUR-Lex", date: date("2026-03-15"), verified: false })
(:KnowledgeSource { name: "ISO 42001", status: "missing", priority: "high" })
```

## Relationships

```cypher
(Service)-[:REQUIRES]->(DocumentType)
(Service)-[:LOCATED_IN]->(Country)
(Service)-[:TRIGGERS_RISK]->(RiskLevel)        // provider risk
(Service)-[:CAN_INDICATE]->(UseCase)           // deployment signal
(DocumentType)-[:BASED_ON]->(Law)
(Country)-[:REQUIRES_MECHANISM]->(TransferMechanism)
(Control)-[:IMPLEMENTS]->(Law)
(UseCase)-[:CLASSIFIED_BY]->(RiskLevel)        // deployer risk
(UseCase)-[:REQUIRES_COMPLIANCE]->(Law)

// Context Graph extensions
(Project)-[:HAS_ASSET {scanned_at: datetime()}]->(ProjectAsset)
(ProjectAsset)-[:MAPS_TO]->(Service)
(NewsEvent)-[:AMENDS]->(Law)
(NewsEvent)-[:MAY_AFFECT]->(Law)
```

## dpa_url — direct link to the provider's DPA

Every `avv_required = true` service has a `dpa_url` property with a direct
link to the provider's DPA. The scout detects a service → Neo4j returns the
link immediately → the AVV draft shows exactly where the
user needs to sign their DPA.

```cypher
MATCH (s:Service)
WHERE s.avv_required = true
RETURN s.name, s.country, s.gdpr_adequate, s.dpa_url
ORDER BY s.country, s.name
```

Full registry: **[docs/reference/dpa-url-registry.md](../reference/dpa-url-registry.md)**

## Write permissions — three-tier model (ADR-005)

| Tier | Who | What | When |
|---|---|---|---|
| 1 | `make seed-all` (seed manifest) | Static foundation (layer files) | Once / on schema change |
| 2 | `news_scout.py` (planned) | New norms, rulings from RSS | Automatic, periodic |
| 3 | `main.py` | New services from repo scans | On-demand, per scan |

> Tiers 2+3 write with `verified=false`. Thomas reviews flagged nodes before they gain trust.
> Only `verified=true` nodes flow into document generation.

## Core principles

1. **MERGE over CREATE** — graph is idempotent, no seed creates duplicates (ADR-003)
2. **Only LangGraph writes** — UI layers are read-only (ADR-004)
3. **No PII** — Neo4j never receives file names, paths, or customer data (ADR-001)
4. **Temporal** — all Law nodes have `applies_from`, `confidence`, `source` (Layer 2 complete)
5. **Explicit jurisdictions** — every Law node has `jurisdictions: ["DE"]` / `["EU"]` / `["global"]`
6. **Source-verified** — all regulatory content from official sources (EUR-Lex or official PDFs — registry: `docs/sources/SOURCES.md`)

## Seeding

```bash
# Standard (fresh install)
make seed-all        # layer manifest + modules + ADR-100 validator
make seed-validate   # graph invariants, read-only

# Configuration: src/graph/seed_config.yaml
# Layer catalogue: docs/reference/graph-layers.md
```

Seed architecture: layer files under `src/graph/layers/` (ADR-009).

## Regulatory knowledge in the graph

### Global (00_global) — applies worldwide

| Source | Status | Jurisdiction |
|--------|--------|---|
| ISO 27001 | 🔒 BYOS — license-gated, not shipped (ADR-120) | global |
| BSI IT-Grundschutz Ed. 2022 | ✅ seeded (titles + EN basis requirements) | global |
| OWASP LLM Top 10 v2025 | ✅ seeded | global |
| OWASP API Security Top 10 | ✅ seeded | global |
| OWASP Web Top 10 2025 | ✅ seeded | global |
| NIST CSF 2.0 | ✅ seeded | global |

### EU Primary Law (10_eu_primary)

| Source | Status | applies_from |
|--------|--------|---|
| GDPR | ✅ seeded | 2018-05-25 |
| EU AI Act | ✅ seeded | staged per Art. 113 |
| NIS2 | ✅ seeded | 2024-10-18 |
| CRA | ✅ seeded | staged |

### DE National Law (10_de)

| Source | Status | applies_from |
|--------|--------|---|
| DDG § 5 (formerly TMG) | ✅ seeded | 2024-05-14 |
| TDDDG § 25 (formerly TTDSG) | ✅ seeded | 2021-12-01 |
| BGB, PAngV, UWG | ✅ seeded | — |

### Planned / pending

| Source | Layer | Priority |
|--------|-------|---|
| ISO 27001:2022 | 00_global | high |
| ISO 42001 | 20_frameworks | high |
| ETSI EN 303 645 | 20_frameworks | medium |
| HIPAA | 20_frameworks | on first US user |
| SOC2 | 20_frameworks | on first US user |

## Example queries

```cypher
// Compliance check for detected services
MATCH (s:Service)-[:REQUIRES]->(d:DocumentType)-[:BASED_ON]->(l:Law)
WHERE s.name IN ["Stripe", "Supabase", "OpenAI", "Resend", "Vercel"]
RETURN s.name AS service, d.type AS document, l.short AS legal_basis
ORDER BY s.name
```

```cypher
// Upcoming deadlines — Context Graph Layer 2
MATCH (l:Law)
WHERE l.applies_from IS NOT NULL
  AND l.applies_from >= date()
  AND l.applies_from <= date() + duration({days: 180})
RETURN l.name, l.article, l.title, l.applies_from, l.jurisdictions
ORDER BY l.applies_from
```

```cypher
// What is missing or unverified in the knowledge model?
MATCH (n)
WHERE n.note_unverified IS NOT NULL
RETURN labels(n)[0] AS type, n.confidence AS confidence, n.note_unverified AS note
```

---

## Further reading

- [context-graph.md](context-graph.md) — Concept, four layers, self-learning
- [../reference/graph-layers.md](../reference/graph-layers.md) — Layer catalogue, global structure
- ADR-009 — Architecture decision
- ADR-010 — UseCase deployer risk
- ADR-011 — NewsEvent + confidence decay
- [../reference/dpa-url-registry.md](../reference/dpa-url-registry.md) — DPA links for all services
