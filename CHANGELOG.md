# Changelog

All notable changes to this project are documented here.
This project follows [Semantic Versioning](https://semver.org/).

## v1.3.3 — 2026-07-29

### Changed
- **Demo GIF spans the full column width.** The two fragment-suffixed image lines
  switched themes but could not carry a width, so the GIF rendered at its native
  size inside a wider column. Now a `<picture>` element with `width="100%"`, the
  same pattern the README already uses for the Scout architecture diagram.

### Removed
- `docs/assets/lex-demo-dark.mp4` and `lex-demo-light.mp4`. Built by the retired
  GIF tooling as social-post assets and shipped in every export since, but nothing
  referenced them. Export drops from 306 files to 304, about 900 KB lighter.

_No code path, seed step or documented command changed in this release._

## v1.3.2 — 2026-07-29

### Changed
- **Demo GIFs rebuilt from the current recordings.** The two README GIFs were a
  five-image slideshow assembled on 2026-07-23; they showed a scan with three
  documents and German document names. They now come from the same cut list as
  the demo video: a frozen install-success beat, the empty dashboard, the running
  scan and the generated documents — 28.4 s, dark and light frame variants.

### Added
- **Reproducible video pipeline** (`docs/internal/demo-videos/`, maintainer-only):
  a hand-maintained cut list plus a build script that renders the demo video and
  both GIFs deterministically from unmodified screen recordings.

### Deprecated
- `scripts/gif/` carries a RETIRED header pointing at the new pipeline. Kept, not
  deleted — the light/dark frame idea and the palette size came from it.

_No code path, seed step or documented command changed in this release._

## v1.3.1 — 2026-07-28

A bugfix release. Some services you use were being filed under the wrong name
internally, which quietly kept them out of your documents.

**Services with capital letters inside their name were dropped**

- When a service was detected through code analysis rather than through a
  dependency file, its name was rebuilt from a lowercase form. "OpenAI" became
  "Openai", "GitHub" became "Github", "PayPal" became "Paypal". None of those
  match the service catalog, so the service fell out of the processor list in
  the Data Processing Agreement, lost its controls in the technical measures
  document, and lost its row in the Standard Contractual Clauses.
- Affected: AWS, GitHub, HubSpot, Mistral AI, MongoDB Atlas, OpenAI, PayPal,
  SendGrid. A service whose name was already correct is now left alone instead
  of being rewritten.
- If you generated documents with v1.3.0 or earlier and any of these appear in
  your stack, run the scan again.

**MongoDB is no longer reported as MongoDB Atlas**

- A bare `mongodb` dependency resolved to "MongoDB Atlas" through a substring
  match. Whether you run MongoDB yourself or use Atlas cannot be told from a
  library, and naming the wrong one in a processing agreement is a factual
  claim we cannot support. It is now left unresolved, which is what the
  detection rules always intended.

**Two duplicate catalog entries merged**

- Chroma and ChromaDB were two entries for the same product; they are one now.
  MongoDB and MongoDB Atlas stay separate — they are genuinely two services.

## v1.3.0 — 2026-07-28

Your documents change what they say about the services you use. If you generated
documents with an earlier version, run the scan again.

**Unknown services are no longer described as harmless**

- A service the catalog did not know was listed as a "development tool without
  independent data processing". Nothing in the scan supported that claim about a
  third party — and two of the services it was applied to were Elasticsearch and
  Redis, both of which store data.
- Such services now appear in a block of their own, marked with the duty symbol
  (⚖️), saying what is actually known: not in the service catalog, role
  unverified, please assess whether they process personal data. They are
  deliberately kept out of the processor list — listing them there would be the
  same unfounded claim pointing the other way.

**Four services added to the catalog, one detection repaired**

- Elasticsearch, Redis, Slack and Google Cloud Authentication are now in the
  catalog. Elasticsearch and Redis had no entry at all, so every detection of
  them fell through.
- Auth0 was detected and then silently dropped, because the detection table
  pointed at a display label ("Auth0 / Okta") rather than the catalog name.

**More security controls reach your technical measures document**

- Five of the ten OWASP LLM Top 10 controls — LLM03, LLM04, LLM05, LLM07 and
  LLM10 — never reached a document. A rule in the graph seed ran before the
  controls it was meant to connect existed, so it quietly produced half its
  links. Projects using an AI service get a correspondingly longer document.
- Services added late in the seed, such as Replicate, had no controls attached
  at all for the same reason.

**Also**

- The NIS2 overview existed twice in the graph, once under an English and once
  under a German key. The duplicate is gone.
- Two display defects in the "Why this document?" box: a note could run into the
  previous sentence without a line break, and a count of one was written as a
  plural.

## v1.2.0 — 2026-07-28

English document output is now complete and is the default for new projects.

**English output**

- The scan report — the cover document of every run — is generated in English
  too. It was the ninth document type and the only one still German-only.
- The TOM section column shows English labels (equipment access control, user
  control, data access control, …) taken verbatim from the official English
  translation of the German Federal Data Protection Act, § 64(3).
- Document names in English texts match the documents you actually receive:
  DPA, RoPA, DPIA.
- Gap texts, the annex list and the affected-documents column are language-pure
  in both directions; norm citations name the law, not the document.
- PDFs carry an English footer and page count.

**Documents**

- The data protection impact assessment gains a step for the duty to seek the
  data protection officer's advice (Art. 35(2) GDPR) — the assessment
  documented the supervisory-authority consultation but had lost this one.
- Removed a leftover appendix that listed raw field identifiers and referred to
  commands that no longer exist. What is missing is shown by the status header,
  the markers in the document and the scan report.
- The document specification in the knowledge graph now matches the current
  section headings, so the completeness score reports real values again.

**Setup**

- New projects start in English. Existing projects keep their language — a
  project that never chose one still produces German documents.

## v1.1.3 — 2026-07-24

The footer still read `Release: v1.0.0` while the badge at the top of the README
had been kept current, so the page contradicted itself. Both now carry the same
number, the badge links to the releases page instead of nowhere, and the footer
points at this changelog.

## v1.1.2 — 2026-07-24

The uninstall commands now resolve the clone through `git rev-parse` instead of
counting `cd ..` steps and assuming the directory is called `Lex-Orchestra`.
Two ways the old form could miss: a clone under a different name was never the
target, and starting the one-liner from inside `docker/` pointed the delete at a
path that does not exist, which `rm -rf` accepts without a word. Both blocks now
work from any subdirectory of the clone, whatever you named it.

## v1.1.1 — 2026-07-24

The graph explorer's side panel showed German field values while the rest of the
dashboard was English. It picked the language itself instead of sharing the
Inspector's logic, and had the order inverted: a node with a perfectly good
`title_en` was displayed in German, and the German twin of an already-shown
English field appeared a second time in the property table.

Both views now use one helper. German-only fields such as `label_de` stay
visible, because no English variant exists for them yet and hiding them would
drop the information rather than translate it.

## v1.1.0 — 2026-07-24

**One environment template instead of three.** `docker/envs/.env.example` is now
the only template, and its active values are the sovereign stack: local Ollama,
local Neo4j, nothing leaving the network. Running against a cloud model or Neo4j
Aura is a commented block in the same file.

`.env.sovereign` and `.env.minimal` are gone. The first line of the quickstart
changes accordingly:

```bash
cp docker/envs/.env.example docker/envs/.env
```

The values you fill in are unchanged, and an existing `docker/envs/.env` keeps
working as it is. Three templates meant three copies of the same keys drifting
apart: the placeholder fixed in v1.0.14 was missing from two of them, and the
files had grown three different conventions for "you need to fill this in".

## v1.0.14 — 2026-07-24

Fixed a placeholder in the sovereign environment template that the setup
instructions could not catch. `DASHBOARD_BASE_URL` shipped as
`http://your-server-ip:3000`, while the documented step says to fill in the
`__SET_ME__` values, so the host stayed unset and the deep-links in generated
scan reports pointed at a hostname that does not exist. The placeholder now uses
the same convention as the rest of the file.

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
