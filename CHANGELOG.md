# Changelog

All notable changes to this project are documented here.
This project follows [Semantic Versioning](https://semver.org/).

## v1.0.0 — 2026-07-23

First public release.

### What it does

- **Repository scan → compliance documents.** Point Lex-Orchestra at a git
  repository; it detects the services and data flows in use and generates nine
  document types (DPA, TOM, records of processing, DPIA, SCC assessment,
  AI Act manifest, AI policy, AI system documentation, scan report) as Markdown
  and PDF, in German and English.
- **Fully local by default.** The sovereign profile runs a local LLM (Gemma 4 E4B
  via Ollama) and a local Neo4j container. Source code never leaves the network —
  the knowledge graph stores UUIDs and anonymised asset types, never file names,
  paths or code.
- **Knowledge graph instead of prompt guessing.** Compliance decisions come from
  a curated graph (services → categories → controls → laws), not from a model's
  best guess. Documents carry explicit evidence markers and gap markers where
  only a human can decide.
- **Audit trail.** Every scan writes a queryable trace of the graph queries and
  the returned nodes behind each generated document.

### Included frameworks

BSI IT-Grundschutz (22 controls), NIST CSF 2.0 (12), OWASP Top 10 / API Top 10 /
LLM Top 10 (30), plus EU law nodes (GDPR, AI Act, NIS2, DORA, DSA, CRA).

ISO 27001, BSI C5 and AIC4 are **bring your own source** — their control texts are
license-gated and are not shipped. See [docs/sources/SOURCES.md](docs/sources/SOURCES.md).

### Requirements

x86_64 Linux with Docker, 16 GB RAM recommended, Python 3.12+. A first scan takes
about four minutes on a CPU-only mini PC, including local LLM classification and
rendering of all nine documents. See [docs/setup/README.md](docs/setup/README.md).

### Known limitations

- aarch64 is untested — the base images are multi-arch, but there is no verified run.
- The backend API (port 8001) and the dashboard (port 3000) are unauthenticated by
  design and expect a trusted private network. Do not expose them to the internet.
- Generated documents are drafts for legal review, not legal advice.
