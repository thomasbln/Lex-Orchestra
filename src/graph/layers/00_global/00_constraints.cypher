// ============================================================
// LEX-ORCHESTRA — Layer 00: Uniqueness Constraints (Phase 0)
// ADR-130 D6 — FIRST manifest entry, before any MERGE.
//
// MERGE-idempotency is only as good as the node key it merges on;
// these nine constraints protect every MERGE key the seeds rely on.
// Constraints on empty labels are free — running this first means a
// buggy earlier run can never leave duplicates the constraint
// creation would then trip over.
//
// All Community-Edition compatible (uniqueness only). The ADR-100
// §4.2 relationship-existence constraint (legal_basis NOT NULL on
// SUBJECT_TO_CONTROL) requires Enterprise — enforcement stays in
// validate_graph() (seed_both.py, Phase 4).
//
// Canonical location for ALL constraints (supersedes
// the legacy constraints stub under scripts/, which held the first three — ADR-100).
// ============================================================

// ── the three pre-existing constraints (ADR-100), now owned here ──

CREATE CONSTRAINT service_name_unique IF NOT EXISTS
FOR (s:Service) REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT law_name_article_unique IF NOT EXISTS
FOR (l:Law) REQUIRE (l.name, l.article) IS UNIQUE;

CREATE CONSTRAINT risklevel_level_unique IF NOT EXISTS
FOR (rl:RiskLevel) REQUIRE rl.level IS UNIQUE;

// ── the six new ones (ADR-130 D6) — each mirrors its seed MERGE key ──

// Controls merge on {framework, id} everywhere (00_frameworks + seed_both)
CREATE CONSTRAINT control_framework_id_unique IF NOT EXISTS
FOR (c:Control) REQUIRE (c.framework, c.id) IS UNIQUE;

// Measures merge on {id} (SDM layer, seed_both.py)
CREATE CONSTRAINT measure_id_unique IF NOT EXISTS
FOR (m:Measure) REQUIRE m.id IS UNIQUE;

// ServiceCategories merge on {name} (seed_adr061)
CREATE CONSTRAINT servicecategory_name_unique IF NOT EXISTS
FOR (sc:ServiceCategory) REQUIRE sc.name IS UNIQUE;

// UseCases merge on {type} (10_eu_primary)
CREATE CONSTRAINT usecase_type_unique IF NOT EXISTS
FOR (u:UseCase) REQUIRE u.type IS UNIQUE;

// DocumentTypes merge on {type} (10_eu_primary, 10_de)
CREATE CONSTRAINT documenttype_type_unique IF NOT EXISTS
FOR (d:DocumentType) REQUIRE d.type IS UNIQUE;

// Requirements merge on {id, framework} at ALL 33 sites (32 layer + 1
// seed_both) — composite here, deviating from ADR-130 D6's shorthand
// "Requirement(id)" to follow D6's own rationale: the constraint must
// protect the actual MERGE key. Verified 2026-07-14: 0 duplicate
// (id, framework) pairs live; 45/45 distinct.
CREATE CONSTRAINT requirement_id_framework_unique IF NOT EXISTS
FOR (r:Requirement) REQUIRE (r.id, r.framework) IS UNIQUE;
