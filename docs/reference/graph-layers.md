# Graph Layer Catalogue

> Reference: ADR-009 — Scalable Context Graph: Seed Layer Architecture

Lex-Orchestra's knowledge graph is built from named layers.
Each layer is an idempotent Cypher file that can be loaded independently.
Layers follow the MERGE-over-CREATE principle (ADR-003) — safe to re-run at any time.

---

## Layer Structure

```
src/graph/layers/
│
├── 00_global/                         Universal — no jurisdiction assumed
│   ├── 00_frameworks.cypher           ISO 27001, OWASP, NIST CSF, BSI
│   └── 00_services_global.cypher      Stripe, AWS, OpenAI, Anthropic...
│
├── 10_jurisdiction/                   One file per country or region
│   ├── eu/
│   │   ├── 10_eu_primary.cypher       DSGVO, EU AI Act, CRA, NIS2
│   │   ├── 10_de.cypher               DDG, TTDSG, BGB, UWG, PAngV
│   │   ├── 10_at.cypher               ECG § 5, AT-specific law
│   │   └── 10_fr.cypher               LCEN Art. 6, FR-specific law
│   ├── us/
│   │   ├── 10_us_federal.cypher       FTC Act, CCPA federal layer
│   │   └── 10_us_ca.cypher            California Consumer Privacy Act
│   ├── uk/
│   │   └── 10_uk_gdpr.cypher          UK GDPR post-Brexit
│   └── apac/
│       ├── 10_sg.cypher               Singapore PDPA
│       ├── 10_au.cypher               Australian Privacy Act 1988
│       └── 10_jp.cypher               Japan APPI
│
├── 20_frameworks/                     Opt-in industry/certification frameworks
│   ├── 20_iso42001.cypher             AI Management System Standard
│   ├── 20_hipaa.cypher                Healthcare (US + global)
│   ├── 20_soc2.cypher                 US SaaS certification
│   ├── 20_pci_dss.cypher              Payment Card Industry
│   └── 20_etsi_303645.cypher          IoT Security (CRA-relevant)
│
└── 30_services/                       Regional service additions
    ├── 30_services_de.cypher          Hetzner, Plausible, DE-specific
    └── 30_services_us.cypher          US-regional services
```

---

## Layer Catalogue

### 00_global — Universal Foundation

These layers contain no jurisdiction-specific law.
They apply to every Lex-Orchestra deployment worldwide.

#### `00_frameworks.cypher`

| Content | Nodes | Source |
|---|---|---|
| ISO 27001:2013 Annex A Controls | ~13 | ISO |
| BSI IT-Grundschutz 2023 | ~16 | BSI (official PDF) |
| OWASP LLM Top 10 v2025 | 10 | OWASP |
| OWASP Web Top 10 2025 | 10 | OWASP |
| OWASP API Security Top 10 | 10 | OWASP |
| NIST CSF 2.0 | 12 | NIST CSWP 29 |

`jurisdictions: ["global"]` on all nodes.

#### `00_services_global.cypher`

All services available worldwide regardless of user jurisdiction.
Includes `data_categories`, `data_subjects`, `dpa_url`, `deletion_period`.

| Category | Services |
|---|---|
| AI/LLM | OpenAI, Anthropic, Google Gemini, Mistral AI, Hugging Face |
| Cloud | AWS, Google Cloud, Azure, DigitalOcean |
| Auth | Auth0, Clerk |
| Payment | Stripe, PayPal |
| Email | Resend, SendGrid, Mailchimp, Postmark, Twilio |
| Monitoring | Sentry, Datadog |
| VCS/CI | GitHub, GitHub Actions |
| Storage | AWS S3, Cloudinary |
| Vector DB | Pinecone, Weaviate, Qdrant, ChromaDB, pgvector |
| Observability | Langfuse |

---

### 10_jurisdiction — National and Regional Law

#### `eu/10_eu_primary.cypher`

EU primary law — applies to any EU-market deployment.

| Law | Articles | applies_from | Source |
|---|---|---|---|
| DSGVO | 13, 14, 28, 30, 32, 37, 46 | 2018-05-25 | EUR-Lex OJ:L_201611977 |
| EU AI Act | 4, 6, 9, 12, 14, 26, 51, 52 | staged per Art. 113 | EUR-Lex OJ:L_202401689 |
| CRA | 13, 14, Annex I | staged | EUR-Lex OJ:L_202402847 |
| NIS2 | 2, 3, 4, 6, 7, 10, 21, 23, 24, 27, 32 | 2024-10-18 | CELEX:32022L2555 |

EU AI Act staged timeline (Art. 113):

| Article | applies_from | Note |
|---|---|---|
| Art. 4 (AI Literacy) | 2025-02-02 | Already in force |
| Art. 51 (GPAI) | 2025-08-02 | Already in force |
| Art. 9, 12, 14, 26, 52 | 2026-08-02 | Main application date |
| Art. 6 Abs. 1 (High-Risk) | 2027-08-02 | Extended transition |

#### `eu/10_de.cypher`

German national implementation + DE-only law.

| Law | Article | applies_from | Note |
|---|---|---|---|
| DDG | § 5 | 2024-05-14 | Replaces TMG § 5 — Impressumspflicht |
| TTDSG | § 25 | 2021-12-01 | Cookie-Einwilligung |
| BGB | §§ 305-310 | — | AGB-Recht, fortlaufend geändert |
| BGB | § 312g | — | Widerrufsrecht |
| PAngV | § 1 | 2022-05-28 | Preisangaben B2C |
| UWG | § 5a | — | Irreführung durch Unterlassen |

DE-specific DocumentTypes: `Impressum`, `AGB`, `Widerrufsbelehrung`, `Preisangaben`
DE-specific Services: `Hetzner`, `Plausible`

#### `us/10_us_federal.cypher` *(planned)*

| Law | Scope |
|---|---|
| FTC Act § 5 | Unfair/deceptive practices — data security |
| CCPA | California Consumer Privacy Act — B2C |

#### `uk/10_uk_gdpr.cypher` *(planned)*

UK GDPR — post-Brexit, Adequacy Decision since 2021 (under review 2025).
Largely mirrors EU GDPR with UK-specific derogations.

#### `apac/10_sg.cypher` *(planned)*

Singapore Personal Data Protection Act (PDPA) 2012, amended 2021.

#### `apac/10_au.cypher` *(planned)*

Australian Privacy Act 1988 + Australian Privacy Principles (APPs).

---

### 20_frameworks — Opt-In Industry Frameworks

#### `20_iso42001.cypher` *(planned)*

ISO 42001:2023 — AI Management System Standard.
Relevant for any organization deploying AI systems.
Complements EU AI Act Art. 9 (Risk Management).

#### `20_hipaa.cypher` *(planned)*

US Health Insurance Portability and Accountability Act.
Required for any SaaS handling Protected Health Information (PHI).

#### `20_soc2.cypher` *(planned)*

SOC 2 Type II — Trust Service Criteria.
Relevant for US SaaS products selling to enterprise customers.

#### `20_pci_dss.cypher` *(planned)*

Payment Card Industry Data Security Standard v4.0.
Required if handling raw card data (most use Stripe — then not required).

#### `20_etsi_303645.cypher` *(planned)*

ETSI EN 303 645 — Cybersecurity for Consumer IoT.
Relevant for CRA compliance of IoT products.

---

### 30_services — Regional Service Additions

#### `30_services_de.cypher`

Services primarily used by German-market deployments.

| Service | Category | Note |
|---|---|---|
| Hetzner | hosting | DE, DSGVO-konform, AVV vorhanden |
| Plausible | analytics | DE, cookieless — no Cookie_Consent required |
| Coolify | hosting | EU, self-hosted option |

---

## Context Graph Property Guarantee

Every Law node in every layer — regardless of origin — must carry:

```cypher
{
  source:        string,    // mandatory — official source identifier
  confidence:    float,     // 1.0 / 0.9 / 0.7 — see scale below
  valid_from:    date,      // when regulation entered into force
  applies_from:  date,      // when obligations become enforceable
  last_verified: date,      // last manual review date
  jurisdictions: [string]   // ["DE"], ["EU"], ["US-CA"], ["global"]
}
```

**Confidence scale:**

| Value | Meaning |
|---|---|
| `1.0` | Primary law — directly from official source (EUR-Lex, BGBl., NIST.gov) |
| `0.9` | Established secondary source (BSI, BfDI, official authority publication) |
| `0.7` | Secondary or partially superseded (e.g. TMG — replaced by DDG) |
| `0.5` | Unverified — **not allowed in any layer file** |

`validate_layer.py` enforces this before any layer touches the graph.

---

## Adding a Custom Layer

Any Lex-Orchestra instance can extend the graph with custom controls,
internal policies, or additional frameworks — without modifying core files.

### Step 1 — Create your Cypher file

```cypher
// my_company/internal_controls.cypher
// Custom security controls for Acme Corp

MERGE (c:Control {framework: "ACME_INTERNAL", id: "AC-001"})
ON CREATE SET
  c.title        = "Data Retention Policy",
  c.severity     = "high",
  c.jurisdictions = ["DE"],
  c.source       = "Acme Corp Security Policy v2.1",
  c.confidence   = 0.9,
  c.last_verified = date("2026-03-21");
```

### Step 2 — Validate

```bash
python scripts/validate_layer.py my_company/internal_controls.cypher
# ✅ MERGE-only: passed
# ✅ Mandatory properties: passed
# Ready to import.
```

### Step 3 — Import

```bash
python scripts/import_layer.py my_company/internal_controls.cypher
# Importing: my_company/internal_controls.cypher
# ✅ Done — 1 node written.
```

### Step 4 — Register in seed_config.yaml (optional)

```yaml
custom_layers:
  - "./my_company/internal_controls.cypher"
```

This ensures the layer is re-applied on every `python src/graph/seed.py` run.

---

## Contributing a New Jurisdiction or Framework Layer

If you want to contribute a new layer to the Lex-Orchestra open source project:

1. Create the file in the correct directory (`10_jurisdiction/` or `20_frameworks/`)
2. Every Law node must have all mandatory Context Graph properties
3. Run `scripts/validate_layer.py` — must pass with zero errors
4. Add an entry to this catalogue (this file)
5. Open a Pull Request with the layer file + catalogue update

Source requirements for contributed layers:
- All `applies_from` dates must reference the official legislation text
- `source` must be a verifiable identifier (EUR-Lex ELI, official gazette, etc.)
- No `confidence` below `0.7` in contributed files

### When you add a new PDF to docs/sources/

1. Add the file to `scripts/check_sources.py` `SOURCE_MAP`
2. Run `python scripts/check_sources.py` to confirm it appears as "missing"
3. Read the PDF, extract relevant nodes
4. Add nodes to the correct layer file
5. Run `python src/graph/seed.py` to import
6. Run `python scripts/check_sources.py` to confirm status changes to "imported"

---

## Current Status

| Layer | Status | Nodes |
|---|---|---|
| `00_global/00_frameworks.cypher` | ✅ exists (in monolith) | ISO, OWASP, NIST, BSI |
| `00_global/00_services_global.cypher` | ✅ exists (in monolith) | ~54 services |
| `10_eu_primary.cypher` | ✅ exists (in monolith) | DSGVO, AI Act, CRA, NIS2 |
| `10_de.cypher` | ✅ exists (in monolith) | DDG, TTDSG, BGB, UWG, PAngV |
| `10_at.cypher` | 🔲 planned | — |
| `10_fr.cypher` | 🔲 planned | — |
| `10_us_federal.cypher` | 🔲 planned | — |
| `10_uk_gdpr.cypher` | 🔲 planned | — |
| `10_sg.cypher` | 🔲 planned | — |
| `20_iso42001.cypher` | 🔲 planned | — |
| `20_hipaa.cypher` | 🔲 planned | — |
| `20_soc2.cypher` | 🔲 planned | — |
| `20_pci_dss.cypher` | 🔲 planned | — |
| `20_etsi_303645.cypher` | 🔲 planned | — |

**Migration note:** All layers currently exist as one monolithic file
(`src/graph/neo4j_seed.cypher`). Phase 1 of ADR-009 splits this into
the structure above. See ADR-009 for the migration plan.
