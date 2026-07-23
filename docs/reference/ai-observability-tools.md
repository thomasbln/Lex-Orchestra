# AI Observability Tools — Categories & Compliance Relevance

> Important for the Lex Scanner: these three tool categories are often confused.
> Each serves a different function — and covers different compliance requirements.

---

## Overview — Three Layers

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1 — Data Store (UUID-Only Pattern)                   │
│  Problem: PII lives in the graph / vector store             │
│  Solution: UUID-Only Pattern (architectural)                │
│  Tool:    No tool — design decision                         │
│  Norm:    DSGVO Art. 25 (Privacy by Design)                 │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 2 — Transport (PII Pre-Filter)                       │
│  Problem: User sends PII in the prompt to the LLM           │
│  Solution: Gateway filters PII BEFORE the LLM call         │
│  Tool:    Microsoft Presidio                                │
│  Norm:    DSGVO Art. 32 (technical safeguards)              │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 3 — Audit Trail (LLM Observability)                  │
│  Problem: No proof of what the AI decided                   │
│  Solution: Log every LLM call (hash, timestamp, UUID)       │
│  Tool:    Langfuse                                          │
│  Norm:    EU AI Act Art. 12 (logging obligation)            │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer 2 — Presidio (PII Pre-Filter / Gateway)

**What it is:** Open-source framework by Microsoft.
Runs as a proxy BEFORE the LLM API call.

**What it does:**
```
User types: "Analysiere Vertrag von Sarah Mueller"
     ↓
Presidio Analyzer detects: PERSON("Sarah Mueller")
     ↓
Presidio Anonymizer replaces: → "Analysiere Vertrag von [TOKEN_042]"
     ↓
[TOKEN_042] goes to OpenAI — no real name
     ↓
Response comes back with [TOKEN_042]
     ↓
De-anonymizer restores: "Sarah Mueller"
     ↓
Only within your perimeter
```

**Detected PII types out-of-the-box:**
- Names, email addresses, phone numbers
- Credit card numbers, IBAN
- Custom: PESEL, NIP, VAT-IDs (EU-specific)

**Deployment:** Docker / Kubernetes / Python package

**Compliance:** DSGVO Art. 25 + Art. 32

**When needed:** When user input (prompts) may contain PII
→ e.g. chat about customer data, contract analysis, support tickets

**NOT suitable for:** Audit trail / EU AI Act Art. 12

---

## Layer 3 — Langfuse (LLM Observability / Audit Trail)

**What it is:** Open-source LLM observability platform.
Runs IN PARALLEL to the LLM call — logs traces.

**What it does:**
```
LLM call is executed
     ↓ (parallel)
Langfuse logs:
  - Timestamp
  - Model (gpt-4, claude-3...)
  - Input hash (not the actual prompt)
  - Output hash (not the actual response)
  - Latency
  - Token count
  - User UUID (not actual name)
  - Consent status
  - Escalation flag
```

**What is NOT logged:** Actual prompt content (when correctly configured)
→ No PII in the audit trail

**Deployment:** Self-hosted Docker (recommended for DSGVO) or cloud (DE)

**Compliance:** EU AI Act Art. 12 (logging obligation for high-risk AI)

**Retention:** Configurable — minimum 90 days (DE procurement standard)

**When needed:** Whenever an LLM API is used
→ Especially critical: finance, insurance, HR, public sector

**Procurement question (Bundesnetzagentur standard):**
> "Can you provide the complete decision trail for an
> AI decision from 90 days ago?"

→ Without Langfuse: No → procurement exclusion

---

## What Sentry and Datadog Are NOT

| Tool | Category | Purpose | EU AI Act Art. 12? |
|---|---|---|---|
| **Sentry** | Error tracking | Exceptions, crashes, stack traces | ❌ No |
| **Datadog** | Infra monitoring | CPU, memory, logs, APM | ❌ No |
| **Langfuse** | LLM observability | Prompt traces, decision trail | ✅ Yes |

**Important:** Having Sentry in your code does NOT mean EU AI Act Art. 12
is satisfied. Sentry logs errors — not LLM decisions.

Sentry is even a **risk** when PII ends up in error logs
→ `PII_IN_LOGS` risk in Lex.

---

## How Lex Detects the Three Layers

### What Lex detects during a scan:

```
pgvector / Pinecone / Weaviate detected
     → 🔴 RAG_OVER_PII (layer 1 problem)
     → Recommendation: UUID-Only Pattern

Firebase + OpenAI detected (without Presidio)
     → 🟠 PII_IN_LLM_CONTEXT (layer 2 problem)
     → Recommendation: Presidio Gateway or post-retrieval join

OpenAI detected (without Langfuse/Helicone/etc.)
     → ⚠️ NO_AI_AUDIT_TRAIL (layer 3 problem)
     → Recommendation: Langfuse (DE, self-hostable)

Sentry + OpenAI detected
     → 🟠 PII_IN_LOGS (Sentry may log PII)
     → Recommendation: PII-free logging (UUID prefix only)
```

### Detection Signals in Code:

**Presidio detected when:**
```
presidio-analyzer in requirements.txt
presidio_analyzer in imports
```

**Langfuse detected when:**
```
langfuse in requirements.txt / package.json
from langfuse import ...
LANGFUSE_PUBLIC_KEY in .env.example
```

**Sentry detected when:**
```
sentry-sdk in requirements.txt
@sentry/nextjs in package.json
```

---

## Combination — Defense in Depth

Complete protection for an LLM stack:

```
User input
     ↓
[PRESIDIO]      ← Layer 2: remove PII from prompt
     ↓
UUID-only graph ← Layer 1: no PII in data store
     ↓
[LLM API call]
     ↓ (parallel)
[LANGFUSE]      ← Layer 3: log decision trail
     ↓
Post-retrieval join (app resolves UUIDs locally)
     ↓
Response to user
```

**Regulatory coverage:**
- DSGVO Art. 25 ✅ (Presidio + UUID-Only)
- DSGVO Art. 32 ✅ (Presidio + Langfuse)
- EU AI Act Art. 10 ✅ (UUID-Only + Presidio)
- EU AI Act Art. 12 ✅ (Langfuse)
- EU AI Act Art. 14 ✅ (Langfuse escalation flag)

---

## Links

- Presidio: https://microsoft.github.io/presidio/
- Langfuse: https://langfuse.com (self-hosted: https://langfuse.com/docs/deployment/self-host)
- EU AI Act Art. 12: https://eur-lex.europa.eu/eli/reg/2024/1689/oj

---

*Created: 2026-03-20*
*Relevant for: Lex-Scanner detection, compliance architecture*
