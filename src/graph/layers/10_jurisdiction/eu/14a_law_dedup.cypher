// ADR-100 §4.4 Patch 14a — Delete 4 duplicate "Art. N"-prefixed Law-nodes
// These duplicates carry 0 relationships and are safe to DETACH DELETE.
//
// Canonical nodes (keep, 16 properties each):  DSGVO/5, DSGVO/6, DSGVO/7, DSGVO/35
// Duplicates   (delete, 5 properties each):  DSGVO/"Art. 5", DSGVO/"Art. 6",
//                                             DSGVO/"Art. 7", DSGVO/"Art. 35"
//
// Idempotent: MATCH + DETACH DELETE is a no-op if nodes are already gone.
//
// SCOPE (clarified 2026-07-28): this file is a ONE-TIME MIGRATION for instances
// seeded before ADR-100, not a general dedup rule. No layer creates "Art. N"-
// prefixed DSGVO nodes any more, so on a fresh install it deletes nothing.
// It also runs BEFORE 14b/14d — a DELETE here can never catch a duplicate a
// later layer has not created yet. The general guard is validate_graph() §4.5
// in scripts/seed_both.py, which runs after every phase and REPORTS instead of
// deleting (picking a canonical key is a decision, not a seed side-effect).
// Do not grow this file into a dedup rule; it sits at the wrong point in time.

MATCH (l:Law)
WHERE l.name = "DSGVO" AND l.article IN ["Art. 5", "Art. 6", "Art. 7", "Art. 35"]
DETACH DELETE l;
