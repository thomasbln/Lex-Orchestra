<p align="center">
  <img src="docs/images/logo.svg" alt="Lex-Orchestra" width="120">
</p>

# Lex-Orchestra

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)
[![Status: Pre-release](https://img.shields.io/badge/Status-Pre--release-orange)]()
[![Data: Stays local](https://img.shields.io/badge/Data-Stays%20local-green)]()

<!-- tagline slot — final one-liner pending (Thomas' call); replace the two lines below when it lands -->
**Local compliance agent for software teams.**
From git push to legal draft — on your own hardware.

A single line of code can trigger a GDPR violation that costs your company millions.
Most developers find out months later — from a lawyer.

Lex-Orchestra scans your code repository, detects which laws apply, and generates
pre-filled legal documents — DPA, TOM, records of processing, DPIA, SCC assessment,
AI Act manifest and more — automatically, in German and English.
Your source code never leaves your network. Not as a policy. As an architectural constraint.

One scan. Nine document types. Two languages. Fully local.

![Lex-Orchestra — repo in, compliance docs out](docs/assets/lex-demo-dark.gif#gh-dark-mode-only)
![Lex-Orchestra — repo in, compliance docs out](docs/assets/lex-demo-light.gif#gh-light-mode-only)

![Lex-Orchestra Architecture — Sense, Know, Act](docs/images/architecture.svg)


## The problem

Every current approach to software compliance is broken. Questionnaire tools ask you
to describe your infrastructure from memory — you forget the analytics pixel you added
in March, and the tool has no way to know. Cloud-based LLM tools guess compliance
probabilistically — an AI that is "85% confident" about a legal requirement is not an
auditable answer, it is a liability. Code upload tools ask you to hand your IP and
secrets to a third party to check for privacy violations — you violate data sovereignty
to verify data sovereignty.

In code we trust. The infrastructure speaks for itself.


## Legal moves into the pipeline

In the old world, legal was the bottleneck at the end of the pipeline. A developer
ships, weeks later legal reviews, finds gaps, sends it back. The legal team spent most
of their time just capturing what the infrastructure actually does — reconstructing
configurations, chasing down which services process what data, filling in the blanks
from memory.

With Lex-Orchestra, legal moves into the pipeline — at commit time, not after
deployment. The system already knows what runs. Documents are pre-filled, referenced,
and carry explicit gap markers where only a human can decide. The legal team's job
shifts from data collection to review and sign-off.

Ready for legal review — not for legal discovery.


## How it works

```
git push  -->  Scout (local)  -->  Context Graph (local)  -->  Documents  -->  Dashboard
                    |
          Source code never leaves your network
```

### The Scout

The Scout reads your repository directly — docker-compose files, package manifests
(npm, pip, poetry, composer, go), .env patterns, Dockerfiles. It detects services
automatically against a curated catalogue of 67 processors, including a direct link
to each processor's DPA signing page. No forms.
No memory. The code is the real data flow.

Detection is layered and local: pattern matching against a curated signal map first;
anything unknown is classified by a local LLM (Gemma 4 via Ollama) running on your
machine. Only canonical service names and anonymised identifiers ever reach the graph —
never file names, variables, code content or secrets (the logbook and graph enforce
this as an invariant, not a convention).

The Scout does not ask what you use. It sees it.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/architecture-scout-layers-dark.svg">
  <img src="docs/images/architecture-scout-layers.svg" alt="Scout — layered local analysis pipeline">
</picture>

### The Context Graph

The Context Graph is not a feature. It is the engine that makes the whole system work.

Built on Neo4j (a local container by default), the Context Graph maps your
infrastructure to legal requirements deterministically. It does not guess. It
traverses verified legal norms against your actual stack. Every finding is traceable
to a specific node and an official source. The graph either finds a path from your
detected component to a legal requirement — or it does not.

The graph knows not just what applies, but when it applies (enforcement dates on law
nodes), for whom it applies (jurisdiction layers), and where the knowledge comes from
(source and license provenance on nodes and relationships).

Provider risk and deployer risk are correctly separated. Using an LLM API does not
make you a GPAI provider — that is the model vendor's concern. If you build a customer
service chatbot, your obligation is Art. 50 transparency, not GPAI systemic-risk
reporting. The graph knows the difference.

### Privacy by architecture

The default profile is fully sovereign: Neo4j runs as a local container, the LLM runs
locally via Ollama, documents are assembled deterministically from the graph. In this
setup nothing leaves your network at all. If you opt into a cloud-hosted graph
instead, it receives anonymised UUIDs and abstract asset types only — compliance
logic, not your infrastructure details.

This is not a privacy policy. It is an architectural constraint.


## What it looks like in practice

You use Stripe and Supabase. Your system includes an AI component.

```
Stripe detected       → GDPR Art. 44 ff. (third-country transfer)
                      → Standard Contractual Clauses assessed
                      → DPA missing — signing link included

Supabase detected     → GDPR Art. 28 (processor)
                      → DPA missing — signing link included

AI service detected   → EU AI Act Art. 50 (transparency obligation)
                      → AI Act manifest + AI policy generated
                      → Risk level: limited
```

Nine documents generated, in German or English. Ready for review.

Documents land in `legal/drafts/` as Markdown and PDF, with a per-document provenance
logbook. The dashboard (port 3000) shows scan status, gaps with fix links, and lets
you edit the technical-measures catalogue before re-rendering.


## Data boundary

| Stays local (always) | Optional cloud graph receives (anonymised only) |
|---|---|
| Source code and git repository | UUIDs and abstract asset types |
| docker-compose, .env, Dockerfiles | — |
| Generated legal documents + PDFs | — |
| Scan results and project state (Postgres) | — |
| LLM classification (Ollama, local) | — |
| Real file names, variables, secrets | Never sent anywhere |

In the default sovereign profile there is no cloud component at all.


## How Lex-Orchestra compares

| Dimension | Typical compliance tools | Lex-Orchestra |
|---|---|---|
| How it decides | LLM guesses probabilistically | Context Graph traverses deterministically |
| Where your code goes | Uploaded to cloud for analysis | Never leaves your network |
| When compliance happens | Legal reviews after deployment | Integrated at commit time |
| What you get for a missing DPA | "You need a DPA with Stripe" | Pre-filled DPA draft with direct signing link |
| How often it runs | Once a year, maybe | Re-scan on demand, delta on every run |
| Auditability | Black box — no trace | Every finding traceable to a graph node and source |


## What's in the knowledge graph

| Content | Coverage | Source |
|---|---|---|
| GDPR, EU AI Act, NIS2, CRA, DORA, DSA + German national law (BGB, UWG, TTDSG, PAngV, DDG) | 55+ law articles with enforcement dates | EUR-Lex / official texts |
| BSI IT-Grundschutz | 22 controls (titles + mappings; full requirement texts are license-gated — bring your own Kompendium copy) | BSI |
| NIST CSF 2.0 | 12 functions/categories | NIST |
| OWASP Top 10 (Web, LLM, API) | 30 controls | OWASP |
| EU AI Act use cases | 20 (Annex III + Art. 5 prohibited) | EUR-Lex |
| Services | 67 curated processors with DPA links, data categories, deletion periods | provider trust pages, DPF list |

ISO 27001, BSI C5 and BSI AIC4 are **bring-your-own-standard**: the content is
license-gated, so the repo ships the seed slots but not the licensed texts.

Every node and relationship carries source, license and last-verified provenance.


## Why open source

Compliance should not depend on black boxes.
It should be inspectable, verifiable, and open.

Regulation defines obligations — but how those obligations are derived should be
transparent.

Lex-Orchestra is built as open compliance infrastructure:

- every mapping is visible
- every decision is traceable
- every component can be inspected

AGPL-3.0 ensures that improvements remain open. Anyone who takes this code, modifies
it, and offers it as a service must publish their changes. The compliance logic stays
open.

Grounded in European regulation and aligned with global standards like ISO 27001,
NIST, and OWASP.

The graph schema, scanner logic, and document templates are open source.
Curated control mappings, DPA registries, and jurisdiction layers are available under
a commercial license.


## Quickstart

Full setup guide: **[docs/setup/README.md](docs/setup/README.md)** · tested on
x86_64 Linux with Docker; 16 GB RAM recommended. aarch64 is untested — the base
images are multi-arch, so it should build, but there is no verified run yet.

```bash
git clone https://github.com/thomasbln/Lex-Orchestra.git
cd Lex-Orchestra

# Configure environment (fill in the __SET_ME__ values)
cp docker/envs/.env.sovereign docker/envs/.env

# Create the shared network + start the stack (sovereign: local Neo4j + Ollama)
docker network create docker_lex-net
cd docker && docker compose --profile with-neo4j --profile with-ollama up -d && cd ..

# Pull the local inference model — 9.6 GB, one-time.
# Expect ~10–15 minutes on a typical connection; check progress with:
#   docker exec ollama ollama list
docker exec ollama ollama pull gemma4:e4b

# Apply the database schema + seed the knowledge graph (host venv)
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
make db-migrate      # relational schema (projects, scans, documents)
make seed-all        # knowledge graph (layer manifest + modules + validator)

# Validate graph invariants
make seed-validate
```

Then open `http://<your-host>:3000`, create a project, and run the first scan.

**What to expect:** the first scan on CPU-only hardware takes a few minutes — measured
4 min 02 s end-to-end on a 12-core mini PC (no GPU), including local LLM
classification and rendering of all nine documents. The status page tracks each step
live; nothing is hanging.

### Uninstall

Lex-Orchestra leaves nothing behind outside its clone directory — no configs in your
home directory, no system services, no cron jobs (the optional systemd autostart unit
is only installed if you copied it yourself — disable it first if you did).

```bash
cd docker && docker compose --profile with-neo4j --profile with-ollama down -v
# removes containers, network, and ALL volumes — including the graph and the model
docker rmi $(docker images -q 'docker-*' 'ollama/*' 'neo4j*')   # optional: images too
cd .. && cd .. && sudo rm -rf Lex-Orchestra
```

The `sudo` is honest, not lazy: the database volume directory (`pgdata`) and generated
`legal/` files are written by containers and end up root-owned on the host. If you
prefer to avoid sudo, delete them from a throwaway container first.

### Security posture (self-hosters)

The backend API (`approve_api`, port **8001**) and the dashboard (port **3000**)
are **unauthenticated by design** — Lex-Orchestra is built for a trusted
private network (LAN/VPN). Anyone who can reach port 8001 can trigger scans,
edit measures and re-render documents. Before deploying:

- Bind the services to `localhost` or a private interface — **never expose
  ports 8001/3000 directly to the internet.**
- For remote access, put an authenticating reverse proxy (Basic Auth, OIDC,
  Tailscale/VPN) in front.
- The internal LangGraph engine (port 8000) is not published outside the
  container at all; the only built-in guard is the internal `X-Scan-Secret`
  header on the scan step endpoint.


## Documentation

| Section | Description |
|---|---|
| [docs/setup/](docs/setup/) | Hardware, credentials, Docker, troubleshooting |
| [docs/architecture/context-graph.md](docs/architecture/context-graph.md) | Context Graph: RAG → GraphRAG → Context Graph |
| [docs/architecture/data-sovereignty.md](docs/architecture/data-sovereignty.md) | Data sovereignty: what stays where |
| [docs/architecture/trust.md](docs/architecture/trust.md) | Trust statement: verifiable claims, not promises |
| [docs/reference/](docs/reference/) | Service registry, scan strategy |


## Status and roadmap

**Operational today:** full pipeline — repository scan, deterministic graph matching,
nine document types (DPA/AVV, TOM, records of processing, DPIA, SCC assessment,
AI policy, AI system documentation, AI Act manifest, scan report) in German and
English, Markdown + PDF, per-document provenance logbook, editable measures
catalogue, live scan status page.

**Next:** a Legal News Scanner that alerts you when regulatory changes affect your
specific stack, a CI/CD hook for GitHub Actions, and webhook notifications.

**Further ahead:** US law coverage and additional jurisdiction layers.

Status: Pre-release · License: AGPL-3.0 · Partner access available on request


## Learn more

- [Context Graph deep dive](docs/architecture/context-graph.md) — from RAG to GraphRAG to Context Graph, and why it matters for compliance
- [Data sovereignty — what stays where](docs/architecture/data-sovereignty.md) — the three zones, the UUID-only pattern, and the threat model it defeats

---

> Generated documents are pre-filled drafts. Built directly from your infrastructure
> scan and knowledge graph. Each document must be reviewed by a qualified legal
> professional before use or filing.

AGPL-3.0 — Built by Thomas Rehmer — Neo4j — LangGraph — Ollama
