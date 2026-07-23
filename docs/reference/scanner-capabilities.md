# Lex-Orchestra — Scanner Capabilities

> What does Lex detect during a scan? What gets generated from it?
> This file is the central reference for developers, partners, and demo preparation.

---

## How the Scanner Works

```
/scan https://github.com/user/repo
         ↓
1. Scout      — reads files in the repo
2. Graph      — matches against Neo4j Legal Brain
3. Matching   — deterministic graph traversal decides what applies
4. Documents  — generates drafts locally
5. Notify     — scan status page + Supabase
```

All deterministic — no LLM guessing during detection,
only during document generation.

---

## Detected File Types / Sources

| File | What is detected |
|---|---|
| `requirements.txt` | Python packages → services |
| `package.json` | npm packages → services |
| `composer.json` | PHP packages → services |
| `docker-compose.yml` | Container images → services |
| `.env.example` | API keys → services |
| `*.sql` / `migrations/` | pgvector extension, database types |
| `*.py` / `*.ts` / `*.js` | Code patterns (pgvector, match_documents) |

---

## Detected Services (54 Nodes in the Graph)

### AI / LLM
| Service | Country | AVV | SCC | Risk |
|---|---|---|---|---|
| Anthropic | USA | ✅ | ✅ | GPAI |
| OpenAI | USA | ✅ | ✅ | GPAI |
| Google Gemini | USA | ✅ | ✅ | GPAI |
| Mistral AI | FR | ✅ | — | GPAI |
| Hugging Face | USA | ✅ | ✅ | GPAI |

### Database / BaaS
| Service | Country | AVV | Note |
|---|---|---|---|
| Supabase | USA | ✅ | pgvector → RAG risk |
| Firebase | USA | ✅ | NoSQL |
| Neon | USA | ✅ | Serverless Postgres |
| PlanetScale | USA | ✅ | MySQL-compatible |
| MongoDB Atlas | USA | ✅ | Vector search possible |
| MariaDB | FI | ✅ | EU provider |
| AWS RDS | USA | ✅ | pgvector possible |

### Vector Databases (RAG Risk)
| Service | Country | AVV | RAG Risk |
|---|---|---|---|
| pgvector | Open Source | — | 🔴 Critical |
| Pinecone | USA | ✅ | 🔴 Critical |
| Weaviate | NL | ✅ | 🔴 Critical |
| Qdrant | DE | ✅ | 🔴 Critical |
| ChromaDB | USA | ✅ | 🔴 Critical |

### Payment
| Service | Country | AVV | SCC |
|---|---|---|---|
| Stripe | USA | ✅ | ✅ |
| PayPal | USA | ✅ | ✅ |

### Hosting / Cloud
| Service | Country | AVV | GDPR-adequate |
|---|---|---|---|
| Hetzner | DE | ✅ | ✅ |
| Vercel | USA | ✅ | — |
| AWS | USA | ✅ | — |
| Azure | USA | ✅ | — |
| DigitalOcean | USA | ✅ | — |
| Render / Railway / Fly.io | USA | ✅ | — |
| Coolify | Open Source | — | self-hosted |

### Email / SMS
| Service | Country | AVV |
|---|---|---|
| SendGrid / Twilio | USA | ✅ |
| Postmark / Resend | USA | ✅ |
| Mailchimp | USA | ✅ |

### Analytics
| Service | Country | Cookie Consent |
|---|---|---|
| Google Analytics | USA | ✅ required |
| Mixpanel / PostHog | USA | ✅ required |
| **Plausible** | **DE** | **✅ NOT required** (cookieless) |

### Monitoring / Observability
| Service | Country | AVV | EU AI Act Art. 12 |
|---|---|---|---|
| Sentry | USA | ✅ | partial |
| Datadog | USA | ✅ | partial |
| **Langfuse** | **DE** | **✅** | **✅ compliant** |

### Auth / CRM
| Service | Country | AVV | Cookie Consent |
|---|---|---|---|
| Auth0 / Clerk | USA | ✅ | — |
| HubSpot | USA | ✅ | ✅ required |
| Intercom | USA | ✅ | ✅ required |

---

## Detected Risks (Risk Nodes)

### 🔴 Critical

**RAG_OVER_PII**
- Signal: `vector_db` or `pgvector` + LLM API detected
- Meaning: Embeddings may contain PII —
  during RAG queries, PII lands directly in the LLM prompt
- Norm: DSGVO Art. 25 + Art. 32 + EU AI Act Art. 10
- Measure: UUID-Only Pattern, PII scrubbing before embedding

**NO_AI_AUDIT_TRAIL**
- Signal: LLM API detected + no logging tool (Langfuse/Sentry/Datadog)
- Meaning: No decision trail for AI decisions
- Procurement question: "Show me the decision trail from 90 days ago"
- Norm: EU AI Act Art. 12 + Art. 14 + DSGVO Art. 22
- Measure: Langfuse (DE, self-hostable) recommended

### 🟠 High

**PII_IN_LLM_CONTEXT**
- Signal: LLM API + database/BaaS detected (without vector DB)
- Meaning: PII could reach the LLM context unfiltered
- Norm: DSGVO Art. 25 + Art. 32
- Measure: UUID-Only Pattern (ADR-001) or Presidio Gateway

**PII_IN_LOGS**
- Signal: LLM API + monitoring (Sentry/Datadog) detected
- Meaning: PII could end up in error logs
- Norm: DSGVO Art. 32
- Measure: PII-free logging (UUID prefix only)

---

## Generated Documents

| Document | When generated | Content from Graph |
|---|---|---|
| **AVV** | Whenever AVV-required services present | Data categories, data subjects, deletion periods, DPA links per service |
| **ToM** | Always | OWASP LLM/API/ISO controls + risk sections |
| **SCC** | USA services detected | Module 2 recommendation + TIA checklist |
| **AI Act Manifest** | LLM detected | GPAI classification + audit trail section |

### AVV automatically includes:
- Company data from `project_config` (company, address, email)
- Data categories per service from Neo4j
- Data subjects per service
- Deletion periods per service (§ 7)
- Direct DPA link per service ("→ Sign AVV: URL")
- Open items checklist

### ToM automatically includes:
- OWASP LLM Top 10 controls (when LLM detected)
- OWASP API Top 10 controls
- ISO 27001 relevant controls
- BSI Grundschutz modules
- RAG-over-PII section (when vector_db detected)
- PII-in-LLM section (when DB + LLM detected)
- Audit trail section (when no logging detected)

---

## Generated Tasks (compliance_tasks — Phase 2)

LangGraph generates structured tasks after each scan:

| Priority | Example Task | Trigger |
|---|---|---|
| 🔴 High | Implement cookie banner | Google Analytics detected |
| 🔴 High | Create AGB | Stripe + shop detected |
| 🔴 High | Set up audit trail | LLM without Langfuse |
| 🟠 Medium | Sign Anthropic AVV | DPA not signed |
| 🟡 Low | Release AI Act Manifest | GPAI classification |

---

## Legal Gap Detection (Phase 2)

Based on `business_type` from `project_config`:

| business_type | Required Documents |
|---|---|
| `shop` | AGB + Widerruf + Preisangaben + Lieferbedingungen |
| `saas_b2c` | AGB + Widerruf |
| `b2b_api` | AVV + ToM + SCC (when USA services) |

Cookie consent required when detected:
- Google Analytics, Mixpanel, PostHog, HubSpot, Intercom
- **Exception:** Plausible = cookieless → no consent needed

---

## Regulations in the Knowledge Graph (30 Law Nodes)

| Law | Articles in Graph | Relevant for |
|---|---|---|
| DSGVO | Art. 5, 13, 14, 22, 25, 28, 30, 32, 37, 46 | All |
| EU AI Act | Art. 6, 10, 12, 14, 51, 52 | LLM stacks |
| NIS2 | Art. 2, 3, 4, 6, 7, 10, 21, 23, 24, 27, 32 | Critical infrastructure |
| CRA | Annex I, Art. 13, Art. 14 | Digital products (from Sep 2026) |
| BGB | §§ 305-310, 312g | Shops |
| TTDSG | § 25 | Cookie consent |
| PAngV | § 1 | Price disclosure |
| TMG/DDG | § 5 | Impressum |

---

## Frameworks in the Knowledge Graph (71 Control Nodes)

| Framework | Controls | Source |
|---|---|---|
| OWASP LLM Top 10 | 10/10 | PDF v2025 |
| OWASP Web Top 10 | 10/10 | PDF 2025 |
| OWASP API Top 10 | 10/10 | Official |
| NIST CSF 2.0 | 12 | PDF (NIST) |
| ISO 27001 | 13 | PDF 2013 |
| BSI Grundschutz | 16 | PDF Edition 2023 |

---

## Deep Scan — pgvector Detection

The Scout looks beyond package names for these signals:

```
CREATE EXTENSION IF NOT EXISTS vector   ← SQL migrations
CREATE EXTENSION vector
from pgvector                           ← Python imports
from pgvector.django import VectorField
VectorField(                            ← Django/Models
match_documents                         ← Supabase RAG
match_embeddings
similarity_search
ankane/pgvector                         ← Docker images
pgvector/pgvector
```

---

## Sources / PDFs in docs/sources/

| File | Content | In Graph |
|---|---|---|
| `dsgvo.pdf` | DSGVO full text | ✅ |
| `euaiact.pdf` | EU AI Act | ✅ |
| `CELEX_32022L2555_DE_TXT.pdf` | NIS2 | ✅ |
| `cyber-resilience-act-2024-2847.pdf` | CRA | ✅ |
| `IT_Grundschutz_Kompendium.pdf` | BSI (858 pages) | ✅ |
| `nist-csf-2.0.pdf` | NIST CSF 2.0 | ✅ |
| `ISO-27001.pdf` | ISO 27001:2013 | ✅ |
| `OWASP-Top-10-for-LLMs-v2025.pdf` | OWASP LLM | ✅ |
| `owasp-api-security-top-10.pdf` | OWASP API | ✅ |
| `202512 - OWASP Top 10 2025.pdf` | OWASP Web | ✅ |

---

*Created: 2026-03-20*
*Updated: after each new detection capability*
