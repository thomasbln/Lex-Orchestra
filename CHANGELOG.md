# Changelog

## ADR-101 — Source Content Re-Fetch Cycle (Draft, 2026-04-22)

- Proposes 90-day quarterly re-fetch cadence for `:Law` nodes (supersedes 180-day Doc Quality Principles default)
- Change-Flag + Review-Gate strategy: SHA-256 content hash detects upstream changes; `needs_review` flag blocks document generation until operator approves/rejects
- NucBox cron (`0 3 * * 1`) as execution environment; Telegram alerts for fetch failures
- Schema additions: `content_hash`, `status`, `pending_update`, `refetch_policy`, `last_reviewed_at` on `:Law` nodes
- Validator extension: 3 new checks (120d overdue WARN, 30d review backlog WARN, missing hash ERROR)
- EUR-Lex SOAP Webservice (registered 2026-04-22) reserved for ADR-103 (Event-Trigger Legal News Scout)
- Implementation deferred to subsequent PR; this is the decision document only

## ADR-100 — Graph Data Integrity

### PR 7 — Housekeeping (post-ADR-100) (2026-04-22)

Six data-quality fixes uncovered during the ADR-100 regression session:

- **Fix 1** — `validate_graph()`: `id(r)` → `elementId(r)` (deprecation removed).
  Error messages updated from `rel id=` to `rel elementId=`.
- **Fix 2** — Chroma/ChromaDB duplicate merged: ChromaDB is canonical (richer
  properties, deletion_period, dpa_url). Chroma DETACH DELETEd on both instances.
  All 4 outgoing relations (CAN_TRIGGER, LOCATED_IN, REQUIRES, HAS_CATEGORY)
  already existed on ChromaDB — no relation loss.
- **Fix 3** — MongoDB/MongoDB Atlas duplicate merged: MongoDB Atlas is canonical.
  MongoDB DETACH DELETEd on both instances. Service count: 67 → 65.
- **Fix 4** — Legacy `Service.legal_basis` property removed from all Service nodes
  (61 on NucBox, 56 on Aura). Authoritative source is
  `SUBJECT_TO_CONTROL[legal_basis]` via `(:Service)-[:HAS_CATEGORY]->(:ServiceCategory)`.
  Closes the 13 pre-existing contradictions between Service-node free-text and
  Category-level structured values.
  `Q_META` in `graph_client.py` updated to join via `HAS_CATEGORY` →
  `ServiceCategory` → `SUBJECT_TO_CONTROL` using `head(collect(stc.legal_basis))`.
  VVTBuilder now receives structured codes (e.g. `art_6_1_b_contract`) instead of
  German free-text — no downstream rendering change required (VVTActivity maps via
  template macros). Rand-industries regression: 13/13 green after fix.
- **Fix 5** — Country-code normalization on both instances:
  `DEU`→`Germany`, `FRA`→`France`, `NLD`→`Netherlands`, `BVI`→`British Virgin Islands`,
  `open_source` removed (pgvector had invalid country value).
  Telegram.country backfilled on Aura (was null). 7 distinct values, no ISO-3 codes.
- **Fix 6** — `tests/test_graph_data_quality.py` (new, 4 tests):
  `test_service_nodes_have_no_legal_basis_property`,
  `test_no_iso3_country_codes`,
  `test_no_duplicate_compliance_service_pairs`,
  `test_validator_query_uses_elementId`.
- `tests/test_adr100_regression_rand_industries.py`: `RAND_SERVICES` updated —
  `"MongoDB"` → `"MongoDB Atlas"` (canonical after Fix 3).
- `tests/test_document_pipeline.py`: `test_graph_client_returns_legal_basis_in_services`
  updated — assertion changed from `"Art. 6" in legal_basis` to `"art_6" in legal_basis`
  (structured code format from SUBJECT_TO_CONTROL rel).

Out of scope (deferred to ADR-102):
- Mistral AI / Mistral AI EU decomposition
- Integration-Catalog vs Compliance-Service schema separation
- `Service.category` property redundancy with `HAS_CATEGORY` relation

### PR 6.1 — Aura drift resolution (2026-04-22)

Triggered by PR 6 enabling reliable Aura validation for the first time.
58 pre-existing errors surfaced; fully resolved:

- **article_title**: 55 Law nodes on Aura were missing this property. Root
  cause: `14b_law_minimal_metadata.cypher` was applied to NucBox but never
  re-run on Aura post-migration. Fixed by copying directly from NucBox
  (55/55 nodes updated, 0 still missing).
- **CLASSIFIED_BY**: 3 UseCase nodes on Aura (healthcare_decision,
  critical_infrastructure_mgmt, law_enforcement_ai) had the node but no
  edge to RiskLevel. Fixed by copying from NucBox (3/3 wired,
  0 still missing).
- **Missing nodes**: 1 Service (Google Cloud Authentication) and 5 UseCases
  (justice_democratic_process, migration_border_control,
  realtime_remote_biometric_id, social_scoring_public, subliminal_manipulation)
  existed on NucBox but not Aura — added in GQ-005 but never synced.
  MERGEd to Aura with full properties + CLASSIFIED_BY edges.
- **Full drift check**: 12 property counts across both instances — all ✓.
  NucBox ↔ Aura: 55 Law, 67 Service, 20 UseCase, 100 SUBJECT_TO_CONTROL
  (all with legal_basis), 3 constraints.
- Aura validator: was 58 errors → 0 errors after sync.

### PR 6 — Hardening: _split_statements + AVVBuilder list[str] (2026-04-22)

- `scripts/seed_both.py`: `_split_statements(cypher_text)` added as shared utility.
  Splits on `;\s*(?:\n|$)` — handles both inline semicolons (`SET x = 1;\n`) and
  own-line semicolons (`\n;\n`). Preserves semicolons inside string literals
  (e.g. `"Anwendungsbereich; Grundsatz"`). Skips blank and comment-only blocks.
  `import re` added to module imports.
- `tests/test_split_statements.py` (new, 8 tests, all green):
  single statement, inline `;`, own-line `;`, string-literal preservation,
  comment-only block skip, blank block skip, `12_legal_basis_backfill.cypher` count=4,
  `14d_law_cellar_sync.cypher` count=65.
- `tests/test_avv_builder.py`: 4 new unit tests formalizing ADR-100 `list[str]`
  support in `AVVBuilder._split_and_dedup()`:
  `test_avv_split_and_dedup_list_input`, `test_avv_split_and_dedup_mixed_str_and_list`,
  `test_avv_builder_list_data_subjects_not_gap_marker`,
  `test_avv_builder_list_data_subjects_dedup` — 18/18 total AVVBuilder tests green.
- Root cause documented: PR 2 `legal_basis_backfill.cypher` silently failed on Aura
  because the inline Python runner used naive `cypher.split(";")`, truncating
  multi-line statements. `_split_statements` closes this class of bug permanently.

### ADR-100 Regression test — rand-industries (2026-04-22)

- `tests/test_adr100_regression_rand_industries.py` (new, 13 tests, all green)
- Covers graph query → content model (AVVBuilder, VVTBuilder) for 5 ADR-100 invariants:
  1. `overall_risk = "high"` for `hr_recruitment_screening` (not `"gpai"`, not `"minimal"`)
  2. `hr_recruitment_screening` in `usecase_risks` with `risk_level="High"`, `annex_iii_nr="4"`, `article="6"`
  3. All 11 services have `data_subjects` as non-empty `list[str]` from 4-value allowlist
  4. `AVVContentModel.data_subjects` is `str` (not `GapMarker`), all 11 services in summary
  5. All VVT activities have `data_subjects`; ≥7/11 have `legal_basis`
- **Side-fixes discovered during regression run:**
  - `AVVBuilder._split_and_dedup()` crashed on `list[str]` `data_subjects` (was written for old
    comma-string format — broke silently after ADR-100 PR 2). Fixed to handle both `str` and `list`.
  - Aura `SUBJECT_TO_CONTROL` rels had `legal_basis=null` on all 100 rels (PR 2 backfill from
    cypher file failed silently — semicolons in file split incorrectly). Applied directly via
    Python driver: 67 contract + 9 consent + 19 legit_interests + 5 employment = 100/100 set.

### ADR-100 — Status: Accepted (2026-04-22)

- All 5 PRs (+ 4.1, 4.2, 4.3) complete
- NucBox + Aura fully synchronized (55/55 Law nodes, 55/55 `note_de`, 55/55 `fetched_via`)
- Amendment sections integrated into ADR body: Community-Edition mitigation, CELLAR
  migration, property semantics, `data_subjects` vocabulary simplification, final graph
  state table
- Enforcement chain: `validate_graph()` (runtime) + pre-commit + Makefile
- ADR-101 forward reference added (180-day re-fetch cycle)

### PR 5 — CI enforcement (ADR-100 §6)

- `Makefile`: `seed-validate`, `seed-validate-aura`, `seed-validate-all` targets
  (call `seed_both.py --validate-only --target {nuc|aura}`).
- `.pre-commit-config.yaml` (new): `adr-100-graph-validator` hook fires only on
  changes under `src/graph/layers/*.cypher`; skips all other file types.
- `requirements.txt`: `pre-commit>=3.5.0` added to developer tooling section.
- Enforcement chain on Community Edition:
  `validate_graph()` (runtime) + pre-commit (developer) + Makefile (CI/manual).
  Closes the Community-Edition gap noted in PR 3 (relationship property existence
  constraints are Enterprise-only; `validate_graph()` enforces the same invariants
  at the application layer).
- Note: remote-targeting commands require an SSH tunnel port-forwarding
  Bolt (7687) to the target Neo4j host.

### PR 4.3 — Law-node sync from CELLAR JSON to NucBox + Aura

- **Discovery**: NucBox had 26 EUR-Lex nodes with `note_de=null` + stale `eur-lex.europa.eu`
  source URLs. Aura had 50 nodes (5 fewer than NucBox), `source_url`/`fetched_at`/
  `article_title` absent entirely, 4 nodes in `Art. X` format (patch 14a missing),
  `TTDSG/25` not yet renamed to `TDDDG/25`.
- **Aura pre-flight**: renamed `DSGVO/Art. 5→5`, `Art. 6→6`, `Art. 7→7`, `Art. 35→35`;
  `TTDSG/25` → `TDDDG/25`. 5 nodes renamed, 0 `Art.`/TTDSG remaining.
- **Aura MERGE**: 5 genuinely new nodes created with full properties from JSON:
  `DSGVO/33`, `EU AI Act/5`, `EU AI Act/11`, `EU AI Act/53`, `NIS2/Overview`.
  Aura now has 55 Law nodes (matches NucBox).
- **Sync**: `SET note_de, title_en, source_url, source_url_en, fetched_at, fetched_via='cellar'`
  for all 49 EUR-Lex nodes on both NucBox (49/49) and Aura (49/49).
- **Post-sync state**: Both instances — 49/49 `note_de`, 46/49 `title_en` (3 non-articles),
  49/49 `source_url` (Cellar URLs), 47/49 `source_url_en` (2 non-articles skipped),
  49/49 `fetched_via='cellar'`.
- `test_title_en_exists_for_eu_laws` passes on both instances.

### PR 4.3 addendum — materialized as 14d_law_cellar_sync.cypher

- `scripts/gen_14d_cypher.py` (new): reads `law-note-de-fetched.json`, emits
  `14d_law_cellar_sync.cypher` with 65 statements in 3 sections:
  A (5 legacy renames), B (5 ON CREATE MERGEs), C (55 MATCH/SET blocks).
- `src/graph/layers/10_jurisdiction/eu/14d_law_cellar_sync.cypher` (new, generated):
  reproducible sync artifact for the inline PR 4.3 work; re-runnable / idempotent.
- German law nodes (BGB, DDG, PAngV, TDDDG, UWG) now carry
  `fetched_via = "gesetze-im-internet"` for complete traceability.
- Post-apply state on both NucBox + Aura: `total=55, has_note_de=55, has_fetched_via=55`.
- Re-runnable for ADR-101 Rule 6 (180-day re-fetch cycle).

### PR 4.2 — CELLAR API migration (EUR-Lex fetcher)

- Root cause: `eur-lex.europa.eu` is behind AWS CloudFront WAF — HTTP 202 bot
  challenge for all scripted requests; no parser fix could address this.
- Fix: Replaced EUR-Lex scraper with CELLAR content-negotiation API
  (`publications.europa.eu/resource/celex/{id}`, `Accept: application/xhtml+xml`,
  `Accept-Language: de/en`). Returns stable Formex-based XHTML, no authentication.
- New `scripts/cellar_sparql.py`: `get_cellar_xhtml_urls()` + `fetch_cellar_xhtml()`
  with Retry (backoff on 429/503), 0.5 s delay, shared in-memory cache per run.
- New `_parse_cellar_article(html, article, lang)` parser: `oj-ti-art` → `eli-title`
  structure; whitespace normalization handles `\xa0` non-breaking space in article numbers.
- New `_parse_cellar_annex(html, annex_id)` parser: `oj-doc-ti` annex heading lookup.
- Old EUR-Lex parsers (`_parse_eurlex_article`, `_parse_eurlex_article_en`,
  `_parse_eurlex_annex`) removed; `SOURCE_URLS_EN` dict removed.
- `CELEX_IDS` dict maps law names to CELEX identifiers (6 laws: DSGVO, EU AI Act,
  DSA, DORA, NIS2, CRA). `SOURCE_URLS` now points to Cellar base URLs.
- `EMERGENCY_NOTE_DE_FALLBACK` + `EMERGENCY_TITLE_EN_FALLBACK` retained as resilient
  fallbacks (activate only if CELLAR parse fails — 0 fallbacks triggered in testing).
- Result: `fetch_law_note_de.py` 55/55 nodes, 0 errors; 47 EUR-Lex nodes parsed
  live from CELLAR (0 fallbacks); 46/49 have `title_en` (3 non-article entries skipped).
- Closes ADR-101 Rule 6 latent blocker.

### PR 4.1 — Pre-existing test fixes

- `test_compliance_requirements_stripe`: assertion updated from `"DPA"` to `"AVV"`
  (DocumentType merged in ADR-093 PR1)
- `fetch_law_note_de.py` extended: `SOURCE_URLS_EN` dict, `_parse_eurlex_article_en()`
  parser, `FIXED_TITLE_EN` fallback dict (46 EUR-Lex nodes), `title_en` + `source_url_en`
  fields in JSON output and `fetch_note_de()` return value
- `gen_14c_cypher.py` (new): generates `14c_law_title_en_backfill.cypher` from fetched JSON
- `14c_law_title_en_backfill.cypher`: backfills `title_en` + `source_url_en` for 45 Law nodes;
  applied to NucBox (90 props) and Aura (74 props + 4 extra `Art. X` format fixes)
- `test_title_en_exists_for_eu_laws` now passes — both NucBox and Aura: 0 missing
- `docs/internal/law-note-de-fetched.json` schema extended (`title_en`, `source_url_en`)

### PR 4 — graph_client.py CLASSIFIED_BY traversal (ADR-100 §4.3)

- `Q_USECASE_RISK` now traverses `(:UseCase)-[:CLASSIFIED_BY]->(:RiskLevel)`
  instead of reading `u.risk_level` property
- Override block in `get_compliance_requirements()` deleted (~12 LOC); replaced
  with a clean fold of `usecase_risks` into `overall_risk` via the same
  `DEPLOYER_RISK_PRIORITY` dict — graph edge is the single source of truth
- Early-exit guard extended to also pass through calls with only `usecase_types`
- `test_compliance_requirements_openai` updated: asserts `overall_risk != "gpai"`
  (GQ-003 was already closed; old assertion tested the buggy behavior)
- `DEPLOYER_RISK_PRIORITY` dict preserved (still used by both loops)
- `get_usecases_for_risk_level()` still reads `u.risk_level` property — valid
  (property coexists; migration to CLASSIFIED_BY deferred to a future PR)

### PR 3 — Schema constraints (ADR-100 §4.2 / §4.4)

- `scripts/constraints.cypher` created
- 3 uniqueness constraints applied to NucBox and Aura:
  `service_name_unique`, `law_name_article_unique`, `risklevel_level_unique`
- Relationship property existence constraint (`subject_to_control_legal_basis_required`)
  requires Neo4j Enterprise Edition — commented out; `validate_graph()` is the
  enforcement mechanism on Community Edition

### PR 2 — Data backfill (ADR-100 §4.1 / §4.2)

- `src/graph/layers/10_jurisdiction/eu/11_data_subjects_normalize.cypher`:
  55 Service nodes normalised from German free-text strings to `list[str]`
  allowlist values (`customers`, `end_users`, `employees`, `website_visitors`)
- `src/graph/layers/10_jurisdiction/eu/12_legal_basis_backfill.cypher`:
  100 `SUBJECT_TO_CONTROL` relationships backfilled with `legal_basis` by
  ServiceCategory default (art_6_1_b_contract / art_6_1_a_consent /
  art_6_1_f_legitimate_interests / art_88_employment_context)
- Both patches applied to NucBox and Aura

### PR 1 — Graph validator (ADR-100 §4)

- `validate_graph(session)` added to `scripts/seed_both.py`: 4 checks covering
  data_subjects allowlist, legal_basis presence, CLASSIFIED_BY edges, Law metadata
- `--validate-only` flag added to `seed_both.py` CLI
- `tests/test_seed_validator.py`: 20 tests, all green
