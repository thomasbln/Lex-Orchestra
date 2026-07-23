# Trust Architecture

> **Lex-Orchestra is a compliance tool. Trust is not a feature — it is a
> precondition. This document is how we earn it.**

Every claim below is backed by a specific architectural choice, not a
policy statement. Each section names the ADR(s) that implement it, so a
reviewer can verify the code matches the promise.

---

## 1. Source transparency

**Claim:** Every line of Lex-Orchestra is auditable.

- MIT-licensed, public on GitHub.
- No closed binaries, no obfuscated WASM blobs, no opaque
  third-party services on the critical path.
- The same image you run locally is the image any reviewer can build
  from source.

→ Verifiable in the public repository. There is no "private" version
with different behaviour.

---

## 2. Data sovereignty

**Claim:** Your infrastructure stays your infrastructure.

Two supported deployment profiles:

| Profile | LLM | Graph | Delivery | External calls during a scan |
|---|---|---|---|---|
| **Sovereign** (default) | Ollama + Gemma 4 E4B (local) | Neo4j local container | Dashboard + `legal/drafts/` | Zero |
| **API-backend** (optional) | Cloud LLM via `ANTHROPIC_API_KEY` (non-default) | Neo4j local container or external | Dashboard + `legal/drafts/` | LLM API only, with §3 guarantees |

The sovereign profile is the default. The paid Lex-Orchestra MCP — when
it exists — is an addition, never a substitution. You can always run
the same Lex-Orchestra entirely on your hardware with no outbound
traffic during a scan.

→ Verifiable in code: [`docker/envs/.env.sovereign`](../../docker/envs/.env.sovereign)
and the `with-ollama` / `with-neo4j` profiles in
[`docker/docker-compose.yml`](../../docker/docker-compose.yml). The model client
is [`src/llm/__init__.py`](../../src/llm/__init__.py) — it reads `OLLAMA_URL`,
not a cloud endpoint.

---

## 3. PII separation — UUID-Only Pattern

**Claim:** No customer-identifying data ever reaches the cloud graph or
the LLM. Structurally, not by policy.

The Scout finds entities locally (e.g. `STRIPE_SECRET_KEY` in
`checkout.js:42`). Before anything leaves the local network, those
entities are translated into anonymous UUIDs:

```
Scout finds:           Local Postgres:           Neo4j (cloud or local):
STRIPE_SECRET_KEY  →   uuid: abc-123        →   {id: "abc-123",
in checkout.js:42      name: "stripe_key"        type: "api_key",
                       file: "checkout.js"        encrypted: false}
                       line: 42
```

The LLM reasons about `abc-123`. The document is assembled locally with
the real names. The LLM never sees the real names, the file paths, the
domain, or the keys.

**Threat model this defeats:**

- **Infrastructure leak:** A complete graph dump gives an attacker only
  anonymous UUIDs.
- **Prompt injection:** An attacker cannot extract PII through clever
  prompts because it physically does not exist in the graph's context.
- **The logging trap:** PII never ends up in LLM provider error logs —
  it is never sent.

→ Verifiable in code: [`src/graph/asset_translator.py`](../../src/graph/asset_translator.py)
(`anonymize()`), guarded by
[`tests/test_asset_translator.py`](../../tests/test_asset_translator.py) — the
test asserts that no real asset name survives anonymisation. See
also [Data Sovereignty](data-sovereignty.md) for the full data-by-zone
breakdown.

---

## 4. Secret storage — no plaintext API keys

**Claim:** No third-party credential is ever stored in plaintext,
anywhere in the system. This covers integration API keys (e.g. Firecrawl,
Langfuse) and repository access tokens (GitHub Personal Access Tokens).
Including database backups.

All credentials are stored via the **Supabase Vault** extension:

- AES-256-GCM authenticated encryption
- Encryption keys held outside the database by the Supabase service
  layer
- `pg_dump` of any Lex-Orchestra deployment contains ciphertext only
- Decrypt is gated by Postgres row-level security to the backend
  `service_role` — a compromised dashboard session structurally cannot
  read keys

The schema convention is `*_secret_id UUID` referencing
`vault.secrets`. There is no `*_api_key`, `*_token`, or `*_password`
`TEXT` column anywhere in the application schema. The CI audit script
[`scripts/audit_no_plaintext_secrets.py`](../../scripts/audit_no_plaintext_secrets.py)
blocks regressions — a PR that reintroduces such a column fails the
audit job before it can merge.

→ Verifiable in code: the `*_secret_id` convention in
[`src/interface/approve_api.py`](../../src/interface/approve_api.py), proven
end-to-end by [`scripts/vault_smoke_test.sh`](../../scripts/vault_smoke_test.sh)
(checks that no plaintext survives at rest). First consumers: API-key
integrations and GitHub PATs on `project_tokens` / `project_repos`.

---

## 5. Audit trail — append-only history

**Claim:** Every configuration change and every scan result is recorded
and reversible.

- `project_setup_revisions` is append-only. Edits to project setup
  (DPO, hosting, retention) never overwrite the previous state — they
  insert a new revision row with a `valid_from` timestamp.
- `scan_results` and `scan_signals` are also append-only. Re-running a
  scan does not overwrite the previous one.
- Every generated document is filed under `legal/drafts/` with a
  scan-ID suffix. The document that an auditor reviews is the one that
  was generated at that point in time, with that input.
- The scan log (`legal/logs/`) is append-only and survives project
  deletion by design: deleting a project removes its data, documents
  and secrets — not the audit history. Log events carry no PII or code
  (they reference runs by ID only), so retention does not conflict
  with erasure.

→ Verifiable in code:
[`supabase/migrations/014_project_setups.sql`](../../supabase/migrations/014_project_setups.sql)
(`retention_policies`, append-only revisions) and the setup endpoints in
[`src/interface/approve_api.py`](../../src/interface/approve_api.py).

---

## 6. Evidence markers — honest documents

**Claim:** Every generated compliance document tells you which facts
came from where, and which ones are missing.

The three-layer generation renders three explicit markers
into every TOM, AVV, VVT, DSFA, SCC, KI-Policy, KI-System, and AI-Act
Manifest:

| Marker | Meaning |
|---|---|
| ✓ | Fact is verified — comes from the curated knowledge graph or from a confirmed customer setup |
| ? | Fact is user-supplied and unverified — the operator typed it, the system has not confirmed it |
| ⊘ | Fact is missing — the document section needs human input before sign-off |

There is no LLM hallucination passed off as a verified fact. There is
no silent "best guess" filling in for missing data. Every assertion in
a generated document is traceable to its source layer.

→ Verifiable in code: [`src/templates/_marker.md.j2`](../../src/templates/_marker.md.j2)
defines the marker vocabulary; injection happens in
[`src/agents/document_architect.py`](../../src/agents/document_architect.py).

---

## 7. No hidden telemetry

**Claim:** Lex-Orchestra does not phone home. There is no analytics
SDK, no remote error reporting, no usage metrics endpoint.

The operator chooses what, if anything, to share:

- **GitHub issues** for bug reports — explicit, manual.
- **Optional "suggest to public catalog"** flow for missing
  hosting providers / regions (planned). Pre-fills a GitHub issue,
  user clicks Submit. Never automatic.

In particular, the system explicitly **does not** maintain a central
log of which hosting providers or regions users add as custom entries.
The price is that the curated catalog grows from public contributions
and operator review, not from silent telemetry. We consider this the
correct trade-off for a compliance tool.

→ Convention encoded throughout the codebase: there is no telemetry client,
no analytics endpoint and no phone-home call anywhere in the tree.

---

## 8. Knowledge provenance — verified sources only

**Claim:** Every legal fact in the knowledge graph is traceable to an
official source.

Confidence levels are properties on every regulatory node:

| `confidence` | Meaning | Allowed? |
|---|---|---|
| `1.0` | Read directly from the official source — EUR-Lex or the official PDF (registry: `docs/sources/SOURCES.md`) | yes |
| `0.9` | Preliminary, `note_unverified` property set | yes, with marker |
| `0.5` | LLM training knowledge only | **no — never written to the graph** |

This rules out the largest class of compliance-LLM failure mode:
generated text that *sounds* like the law but cites a fictional
article. The graph cannot serve a fact unless someone read it from
the source first.

→ Implemented as the project's source verification rule (every regulatory
value traced to an official source before it enters the graph); visible
in any node's `source` and provenance properties.

---

## Comparison — what this looks like next to alternatives

| Property | Lex-Orchestra | Closed-source compliance SaaS | LLM-only "compliance assistant" |
|---|---|---|---|
| Source code review | ✓ public | ✗ proprietary | ✗ proprietary prompt + closed model |
| Data residency | ✓ operator's hardware | usually vendor cloud | LLM provider cloud |
| Customer PII reaches the LLM | ✗ structurally impossible | unclear, ToS-dependent | yes, by design |
| Plaintext secrets in DB | ✗ Vault-encrypted | unknown, vendor-internal | n/a (no DB layer) |
| Audit trail of generated docs | ✓ append-only, file + DB | usually yes (paid tier) | ✗ chat history only |
| Hallucination guardrails | ✓ Evidence markers + verified-source rule | yes (template-based, no LLM) | ✗ none |
| Vendor lock-in | ✗ MIT, self-hostable | yes | yes |

The right column is what a customer who has tried "ChatGPT for our
GDPR docs" actually sees in production. The middle column is the
status quo for everything else. The left column is what this project
exists to make available.

---

## Reading order

If you want to verify the claims here, read in this order:

1. [Data Sovereignty](data-sovereignty.md) — what data lives where, with examples
2. [`src/graph/asset_translator.py`](../../src/graph/asset_translator.py) — PII separation in code
3. [`scripts/audit_no_plaintext_secrets.py`](../../scripts/audit_no_plaintext_secrets.py) — secret storage convention
4. [`src/templates/_marker.md.j2`](../../src/templates/_marker.md.j2) — evidence markers in generated documents
5. [`docker/envs/.env.sovereign`](../../docker/envs/.env.sovereign) — the sovereign profile
6. [Privacy by Architecture](https://medium.com/@thomasrehmer/privacy-by-architecture-why-your-knowledge-graph-should-only-store-uuids-a26fb375c908) — the published concept behind the UUID-Only Pattern
