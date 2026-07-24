# Changelog

All notable changes to this project are documented here.
This project follows [Semantic Versioning](https://semver.org/).

## v1.0.13 — 2026-07-24

The README demonstrated its central claim three times without ever naming it: the
repository already holds the record of what runs, so compliance is a question of
reading it rather than remembering it. The problem section now says so.

## v1.0.12 — 2026-07-24

The Context Graph now carries the weight it should: the problem section says what
the tool puts in place of the broken approaches, and the practice example shows the
graph doing the work rather than storing it. "Deterministic" was doing less with
each repetition, so it stays only where it earns its place.

## v1.0.11 — 2026-07-24

The intro now says what Lex-Orchestra is before it says what it does: a
self-hosted platform rather than a service you upload code to. The Context
Graph is named in the opening paragraphs instead of appearing halfway down.

## v1.0.10 — 2026-07-24

The quickstart now shows what a finished install looks like: a screenshot of the
post-setup banner with the four reachable services and the next steps.

## v1.0.9 — 2026-07-24

Housekeeping. The release badge tracked v1.0.0 while the repository was at
v1.0.8, and the changelog had not been updated since the first release; both
now reflect the actual state. The `v1.0.2` tag pointed at the `v1.0.1` commit
and was moved to the commit it belongs to.

## v1.0.8 — 2026-07-24

Documentation only. Em-dashes in the README replaced with commas, colons and
parentheses where those carry the sentence better.

## v1.0.7 — 2026-07-24

Documentation only. Reduced repetitive phrasing patterns in the README.

## v1.0.6 — 2026-07-24

README intro states who the project is for and what the generated documents are
and are not: drafts for legal review, not legal advice.

## v1.0.5 — 2026-07-23

Post-setup banner reworked: ASCII banner, direct links to the Neo4j browser and
Supabase, and a clearer list of next steps.

## v1.0.4 — 2026-07-23

- **Post-setup banner.** `make seed-validate` now prints the reachable URLs of a
  finished install instead of leaving you to guess the ports
  (`scripts/ready-banner.sh`).
- **Uninstall section corrected.** `docker network rm docker_lex-net` added — the
  compose files declare the network external, so `down -v` never removed it and
  the documented uninstall left it behind. The optional image-removal line was
  broken: `docker images -q` accepts at most one positional argument, so the
  three-pattern form errored out and never removed a single image; it now uses
  repeated `--filter=reference` piped through `xargs -r`. Added an "In a hurry?"
  one-liner.

## v1.0.3 — 2026-07-23

Demo GIF re-rendered with a step bar and captions, so the five frames say where
you are and how many stations there are.

## v1.0.2 — 2026-07-23

Architecture diagrams corrected to match what the release actually ships: pure
flow instead of an implied comparison, English-only labels, no inventory counts
and no phantom node.

## v1.0.1 — 2026-07-23

Post-release documentation polish.

- Internal decision-record references removed from all exported prose — they
  pointed at documents that are not part of the public repository. The export
  gate now rejects them outright.
- Trust claims point at verifiable code paths instead of internal references.
- README gained a contents index, a skip-to-quickstart link and a repository
  structure section; the quickstart moved to the top and the longer prose moved
  into `docs/architecture/`.
- Generated documents reference the repository instead of the retired domain.
- This changelog starts at v1.0.0; the pre-release history is not part of the
  public repository.

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
