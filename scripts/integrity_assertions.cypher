// =====================================================================
// Lex-Orchestra — Graph Integrity Assertions (ADR-100)
// =====================================================================
//
// Runnable Cypher mirror of validate_graph() in scripts/seed_both.py.
// Each statement returns one row:
//   check_id     STRING  — ADR-100 section identifier
//   description  STRING  — human-readable invariant
//   status       STRING  — "PASS" | "FAIL"
//   violations   INT     — 0 on PASS
//   offenders    LIST    — up to 3 offending keys on FAIL, [] on PASS
//
// Usage:
//   cypher-shell -a bolt://<host>:7687 -u neo4j -p $NEO4J_PASSWORD -f scripts/integrity_assertions.cypher
//   or paste statements individually in Neo4j Browser
//   or run via MCP `read_neo4j_cypher` one statement at a time
//
// Read-only. Zero mutations.
//
// ADR references:
//   ADR-100  Graph Data Integrity
//   ADR-103  Subagent-Architektur Squid (Task 5 Phase-1 close-out)
//
// =====================================================================

// ---------------------------------------------------------------------
// ADR100-4.1a — Every :Service has non-null data_subjects (as a list)
// ---------------------------------------------------------------------
MATCH (s:Service)
WITH count(s) AS total,
     collect(CASE WHEN s.data_subjects IS NULL THEN s.name END) AS null_offenders,
     collect(CASE WHEN s.data_subjects IS NOT NULL AND NOT (s.data_subjects IS :: LIST<ANY>) THEN s.name END) AS type_offenders
WITH total,
     [x IN null_offenders WHERE x IS NOT NULL] + [x IN type_offenders WHERE x IS NOT NULL] AS offenders
RETURN
  'ADR100-4.1a'                                                       AS check_id,
  ':Service.data_subjects must be non-null list'                      AS description,
  CASE WHEN size(offenders) = 0 THEN 'PASS' ELSE 'FAIL' END           AS status,
  size(offenders)                                                     AS violations,
  offenders[..3]                                                      AS offenders;

// ---------------------------------------------------------------------
// ADR100-4.1b — data_subjects values must be in allowlist (PR-2 vocab)
// ---------------------------------------------------------------------
WITH ['customers','end_users','employees','website_visitors'] AS allowed
MATCH (s:Service) WHERE s.data_subjects IS NOT NULL
UNWIND s.data_subjects AS ds
WITH allowed, s, ds WHERE NOT ds IN allowed
WITH collect(DISTINCT s.name + ':' + ds) AS offenders
RETURN
  'ADR100-4.1b'                                                       AS check_id,
  ':Service.data_subjects element in allowlist'                       AS description,
  CASE WHEN size(offenders) = 0 THEN 'PASS' ELSE 'FAIL' END           AS status,
  size(offenders)                                                     AS violations,
  offenders[..3]                                                      AS offenders;

// ---------------------------------------------------------------------
// ADR100-4.2a — SUBJECT_TO_CONTROL must have legal_basis (non-null)
// ---------------------------------------------------------------------
MATCH (a)-[r:SUBJECT_TO_CONTROL]->(b)
WITH count(r) AS total,
     collect(CASE WHEN r.legal_basis IS NULL
                  THEN coalesce(a.name, a.id, 'unknown') + '->' + coalesce(b.name, b.id, 'unknown')
             END) AS raw_offenders
WITH total, [x IN raw_offenders WHERE x IS NOT NULL] AS offenders
RETURN
  'ADR100-4.2a'                                                       AS check_id,
  '[:SUBJECT_TO_CONTROL].legal_basis must be non-null'                AS description,
  CASE WHEN size(offenders) = 0 THEN 'PASS' ELSE 'FAIL' END           AS status,
  size(offenders)                                                     AS violations,
  offenders[..3]                                                      AS offenders;

// ---------------------------------------------------------------------
// ADR100-4.2b — legal_basis must be in 8-value allowlist
// ---------------------------------------------------------------------
WITH [
  'art_6_1_a_consent','art_6_1_b_contract','art_6_1_c_legal_obligation',
  'art_6_1_d_vital_interests','art_6_1_e_public_task','art_6_1_f_legitimate_interests',
  'art_9_2_special_category','art_88_employment_context'
] AS allowed
MATCH (a)-[r:SUBJECT_TO_CONTROL]->(b)
WHERE r.legal_basis IS NOT NULL AND NOT r.legal_basis IN allowed
WITH collect(coalesce(a.name, a.id, '?') + '->' + coalesce(b.name, b.id, '?') + ' [' + r.legal_basis + ']') AS offenders
RETURN
  'ADR100-4.2b'                                                       AS check_id,
  '[:SUBJECT_TO_CONTROL].legal_basis in DSGVO Art. 6/9/88 allowlist'  AS description,
  CASE WHEN size(offenders) = 0 THEN 'PASS' ELSE 'FAIL' END           AS status,
  size(offenders)                                                     AS violations,
  offenders[..3]                                                      AS offenders;

// ---------------------------------------------------------------------
// ADR100-4.3 — :UseCase must have exactly one [:CLASSIFIED_BY]->(:RiskLevel)
// ---------------------------------------------------------------------
MATCH (u:UseCase)
OPTIONAL MATCH (u)-[r:CLASSIFIED_BY]->(:RiskLevel)
WITH u, count(r) AS rel_count
WITH collect(CASE WHEN rel_count <> 1
                  THEN coalesce(u.type, u.name_de, u.name, 'unknown') + ' (' + toString(rel_count) + ')'
             END) AS raw_offenders
WITH [x IN raw_offenders WHERE x IS NOT NULL] AS offenders
RETURN
  'ADR100-4.3'                                                        AS check_id,
  ':UseCase must have exactly one [:CLASSIFIED_BY]->(:RiskLevel)'     AS description,
  CASE WHEN size(offenders) = 0 THEN 'PASS' ELSE 'FAIL' END           AS status,
  size(offenders)                                                     AS violations,
  offenders[..3]                                                      AS offenders;

// ---------------------------------------------------------------------
// ADR100-4.4a — :Law.note_de must be non-empty
// ---------------------------------------------------------------------
MATCH (l:Law)
WITH collect(CASE WHEN l.note_de IS NULL OR l.note_de = ''
                  THEN coalesce(l.name, '?') + ' ' + coalesce(l.article, '?')
             END) AS raw_offenders
WITH [x IN raw_offenders WHERE x IS NOT NULL] AS offenders
RETURN
  'ADR100-4.4a'                                                       AS check_id,
  ':Law.note_de must be non-empty'                                    AS description,
  CASE WHEN size(offenders) = 0 THEN 'PASS' ELSE 'FAIL' END           AS status,
  size(offenders)                                                     AS violations,
  offenders[..3]                                                      AS offenders;

// ---------------------------------------------------------------------
// ADR100-4.4b — Catalog-scoped concrete deadline_hours values
// ---------------------------------------------------------------------
// ADR-100 Amendment 2026-05-27: Neo4j cannot store keys with null value
// (SET x = null removes the property), so the original "key must be set
// to null" rule is unenforceable. Resolution: only Laws with a *concrete*
// value listed in ADR-100 §4.4 must have the key set to that value.
// The template catalog (internal working notes) is the
// "conscious decision" mechanism — adding a new template reference
// triggers a catalog review + potential ADR amendment.
//
// Today's concrete values:  DSGVO/33 deadline_hours=72
// ---------------------------------------------------------------------
WITH [
  {name: 'DSGVO', article: '33', expected: 72}
] AS expectations
UNWIND expectations AS exp
OPTIONAL MATCH (l:Law {name: exp.name, article: exp.article})
WITH exp, l
WITH collect(CASE
       WHEN l IS NULL THEN exp.name + '/' + exp.article + ' [node missing]'
       WHEN l.deadline_hours IS NULL OR l.deadline_hours <> exp.expected
         THEN exp.name + '/' + exp.article + ' [got=' + coalesce(toString(l.deadline_hours),'NULL') + ' expected=' + toString(exp.expected) + ']'
     END) AS raw_offenders
WITH [x IN raw_offenders WHERE x IS NOT NULL] AS offenders
RETURN
  'ADR100-4.4b'                                                       AS check_id,
  ':Law.deadline_hours matches ADR-100 §4.4 concrete values'          AS description,
  CASE WHEN size(offenders) = 0 THEN 'PASS' ELSE 'FAIL' END           AS status,
  size(offenders)                                                     AS violations,
  offenders[..3]                                                      AS offenders;

// ---------------------------------------------------------------------
// ADR100-4.4c — Catalog-scoped concrete retention_years values
// ---------------------------------------------------------------------
// Same rationale as 4.4b. Today's concrete values:
//   EU AI Act/12 retention_years=5
//   EU AI Act/72 retention_years=10  (node not yet seeded — skipped if absent)
// ---------------------------------------------------------------------
WITH [
  {name: 'EU AI Act', article: '12', expected: 5}
] AS expectations
UNWIND expectations AS exp
OPTIONAL MATCH (l:Law {name: exp.name, article: exp.article})
WITH exp, l
WITH collect(CASE
       WHEN l IS NULL THEN exp.name + '/' + exp.article + ' [node missing]'
       WHEN l.retention_years IS NULL OR l.retention_years <> exp.expected
         THEN exp.name + '/' + exp.article + ' [got=' + coalesce(toString(l.retention_years),'NULL') + ' expected=' + toString(exp.expected) + ']'
     END) AS raw_offenders
WITH [x IN raw_offenders WHERE x IS NOT NULL] AS offenders
RETURN
  'ADR100-4.4c'                                                       AS check_id,
  ':Law.retention_years matches ADR-100 §4.4 concrete values'         AS description,
  CASE WHEN size(offenders) = 0 THEN 'PASS' ELSE 'FAIL' END           AS status,
  size(offenders)                                                     AS violations,
  offenders[..3]                                                      AS offenders;

// ---------------------------------------------------------------------
// ADR100-4.4d — :Law.fetched_via in {cellar, gesetze-im-internet}
// ---------------------------------------------------------------------
WITH ['cellar','gesetze-im-internet'] AS allowed
MATCH (l:Law)
WHERE l.fetched_via IS NULL OR NOT l.fetched_via IN allowed
WITH collect(coalesce(l.name,'?') + ' ' + coalesce(l.article,'?') + ' [' + coalesce(l.fetched_via,'NULL') + ']') AS offenders
RETURN
  'ADR100-4.4d'                                                       AS check_id,
  ':Law.fetched_via must be in {cellar, gesetze-im-internet}'         AS description,
  CASE WHEN size(offenders) = 0 THEN 'PASS' ELSE 'FAIL' END           AS status,
  size(offenders)                                                     AS violations,
  offenders[..3]                                                      AS offenders;

// ---------------------------------------------------------------------
// ADR100-uniq — 3 uniqueness constraints must be active
// ---------------------------------------------------------------------
// Note: Neo4j 5.x does not allow `WITH` composition after `SHOW CONSTRAINTS`.
// We count matched constraint names directly; on FAIL inspect `present` to
// find which of the 3 expected names is missing.
// ---------------------------------------------------------------------
SHOW CONSTRAINTS YIELD name
WHERE name IN ['service_name_unique','law_name_article_unique','risklevel_level_unique']
RETURN
  'ADR100-uniq'                                                       AS check_id,
  '3 uniqueness constraints active (service / law / risklevel)'       AS description,
  CASE WHEN count(name) = 3 THEN 'PASS' ELSE 'FAIL' END                AS status,
  3 - count(name)                                                     AS violations,
  collect(name)                                                       AS present;
