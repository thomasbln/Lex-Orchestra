# logs/

Machine-local operational logs (graph curation history). Nothing in this directory
is required to run Lex-Orchestra — runtime scan logs live in `legal/logs/`.

The scan log (`legal/logs/lex-scan.log`) is an append-only audit trail: entries
survive project deletion by design (deleting a project removes its data, documents
and secrets — not the audit history). Log events carry no PII, file contents or
code (ADR-001); they reference runs only by ID.

How every graph write is provenance-tracked: see [docs/architecture/trust.md](../docs/architecture/trust.md).
