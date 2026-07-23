// ADR-100 §4.2 — legal_basis backfill on SUBJECT_TO_CONTROL relationships
// Defaults applied per source ServiceCategory.
// Applied: 2026-04-22

// ── art_6_1_b_contract — core service delivery ─────────────────────────────
// collaboration added 2026-06-04 (PR 0.5 / ISO-Deseed): messaging/collaboration SaaS =
// contractual service delivery; was graph-drift (node present, never in seed source).
MATCH (sc:ServiceCategory)-[r:SUBJECT_TO_CONTROL]->(:Control)
WHERE sc.name IN [
  "auth", "baas", "cache_db", "cloud", "collaboration", "crm", "crm_support",
  "database", "email", "hosting", "media_storage", "nosql_db",
  "payment", "search_db", "sms", "storage", "vector_db"
]
SET r.legal_basis = "art_6_1_b_contract";

// ── art_6_1_a_consent — opt-in required ────────────────────────────────────
MATCH (sc:ServiceCategory)-[r:SUBJECT_TO_CONTROL]->(:Control)
WHERE sc.name IN ["analytics", "email_marketing"]
SET r.legal_basis = "art_6_1_a_consent";

// ── art_6_1_f_legitimate_interests — operational/internal ──────────────────
MATCH (sc:ServiceCategory)-[r:SUBJECT_TO_CONTROL]->(:Control)
WHERE sc.name IN [
  "ai_llm", "ai_platform", "cdn_security",
  "monitoring", "observability", "security"
]
SET r.legal_basis = "art_6_1_f_legitimate_interests";

// ── art_88_employment_context — developer / commit data ────────────────────
MATCH (sc:ServiceCategory)-[r:SUBJECT_TO_CONTROL]->(:Control)
WHERE sc.name IN ["ci_cd", "vcs"]
SET r.legal_basis = "art_88_employment_context";
