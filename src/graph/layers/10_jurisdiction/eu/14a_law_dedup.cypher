// ADR-100 §4.4 Patch 14a — Delete 4 duplicate "Art. N"-prefixed Law-nodes
// These duplicates carry 0 relationships and are safe to DETACH DELETE.
//
// Canonical nodes (keep, 16 properties each):  DSGVO/5, DSGVO/6, DSGVO/7, DSGVO/35
// Duplicates   (delete, 5 properties each):  DSGVO/"Art. 5", DSGVO/"Art. 6",
//                                             DSGVO/"Art. 7", DSGVO/"Art. 35"
//
// Idempotent: MATCH + DETACH DELETE is a no-op if nodes are already gone.

MATCH (l:Law)
WHERE l.name = "DSGVO" AND l.article IN ["Art. 5", "Art. 6", "Art. 7", "Art. 35"]
DETACH DELETE l;
