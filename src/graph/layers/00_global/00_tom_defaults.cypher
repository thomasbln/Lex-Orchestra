// ============================================================
// TOM Default Measures — deterministic right column for TOM template
// SET (not ON CREATE) — always updated on re-seed.
// Source: OWASP LLM Top 10 v2025 + OWASP API Top 10 + BSI IT-Grundschutz
//
// Provenance convention (ADR-127 Phase 2): every default_tom_measure carries
//   default_tom_measure_source = "lex-llm-draft"
// — one uniform value, no curated/draft split (conservative + honest). c.source is
// NOT touched here; it holds the framework norm citation.
//
// ⚠️ Reproducibility: this cypher layer is NOT currently wired into `make seed-all`
// (seed_both.py applies python MODULES only, not cypher layers) — same gap class as
// 12_legal_basis_backfill.cypher. Tracked under the Seed-Reproducibility (Fujitsu) track.
// ============================================================

// ── OWASP LLM Top 10 ─────────────────────────────────────────────────────────

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM01"})
SET c.default_tom_measure =
  "Input-Validierung vor LLM-Übergabe: serverseitige Anonymisierung/Pseudonymisierung aller Assets. Regex-Blocklist für bekannte Injection-Pattern (Rollenübernahme, Jailbreak-Phrasen) als serverseitiger Pre-Filter.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM02"})
SET c.default_tom_measure =
  "System-Prompt enthält explizite Datenschutz-Instruktion. PII-Detection scannt alle API-Responses vor Weiterleitung an Client.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM03"})
SET c.default_tom_measure =
  "Dependency-Pinning in requirements.txt (==). Automatisierte Vulnerability-Scans in der CI/CD-Pipeline.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM04"})
SET c.default_tom_measure =
  "Trainingsdaten nur aus verifizierten Quellen. Embedding-Inputs vor Vektorspeicherung validieren. Similarity-Threshold (Cosine > 0.75) für RAG-Abrufe.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM05"})
SET c.default_tom_measure =
  "Output-Schema-Validierung (Pydantic) für alle LLM-Responses. HTML-Escaping vor Rendering. SQL-Parameterization vor Datenbankoperationen.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM06"})
SET c.default_tom_measure =
  "Tool-Use-Whitelist im System-Prompt. Serverseitige Allowlist für erlaubte Tool-Calls. Kein autonomer Datenbankschreibzugriff ohne explizite Nutzerbestätigung.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM07"})
SET c.default_tom_measure =
  "System-Prompt nicht an Client exponieren. API-Responses filtern: interne Metadaten (Modellparameter, system content) im Backend-Layer entfernen.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM08"})
SET c.default_tom_measure =
  "Similarity-Threshold für RAG-Abrufe (Cosine > 0.75). Chunk-Validierung auf Injection-Muster. Keine direkten User-Inputs als Embedding-Query ohne Sanitisierung.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM09"})
SET c.default_tom_measure =
  "Sichtbarer Disclaimer bei KI-generierten Inhalten. Bei faktenrelevanten Use-Cases: RAG-Grounding mit Quellenangabe. Vier-Augen-Prinzip bei kritischen Entscheidungen.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM10"})
SET c.default_tom_measure =
  "Pro Session: max_tokens-Limit (4096), Requests-per-Minute (10 RPM), tägliches Token-Budget (100k). In-Memory-Cache-basiertes Rate-Limiting.",
  c.default_tom_measure_source = "lex-llm-draft";

// ── OWASP API Security Top 10 ─────────────────────────────────────────────────

MATCH (c:Control {framework: "OWASP_API_Top10", id: "API1"})
SET c.default_tom_measure =
  "Session-zu-Konversations-ID-Bindung serverseitig. Nutzer A kann keine Konversationsdaten von Nutzer B abrufen — auch nicht durch conversation_id-Manipulation.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_API_Top10", id: "API2"})
SET c.default_tom_measure =
  "API-Keys ausschließlich als serverseitige Umgebungsvariablen. Kurzlebige JWTs (≤ 1h) für Endnutzer-Authentifizierung.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_API_Top10", id: "API3"})
SET c.default_tom_measure =
  "Response-Filterung im Backend: interne Metadaten (system prompt content, user_ids, Modellparameter) vor Client-Auslieferung entfernen.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_API_Top10", id: "API4"})
SET c.default_tom_measure =
  "Kombiniertes Limit: max_tokens + RPM + tägliches Token-Budget. Rate-Limiting-Middleware. Separates restriktiveres Limit für sensible Geschäftsflows.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_API_Top10", id: "API5"})
SET c.default_tom_measure =
  "RBAC: Admin-Rolle für System-Prompt-Änderungen, reguläre Nutzer nur Chat-Endpunkt. Middleware-Guard vor jedem Route-Handler.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_API_Top10", id: "API6"})
SET c.default_tom_measure =
  "Sensible Flows (automatisierte Entscheidungen, Massengenerierungen) durch zusätzliche Authentifizierung geschützt. Separates restriktiveres Rate-Limit.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_API_Top10", id: "API7"})
SET c.default_tom_measure =
  "URL-Allowlist für externe Inhalte. Blockierung interner IP-Ranges (RFC 1918) und Cloud-Metadaten-Endpunkte (169.254.169.254).",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_API_Top10", id: "API8"})
SET c.default_tom_measure =
  "HTTPS-only enforced. Explizite Timeouts (connect: 5s, read: 30s). Keine Debug-Informationen oder Stack-Traces in Produktions-Responses.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_API_Top10", id: "API9"})
SET c.default_tom_measure =
  "Service-Inventory mit eingesetzten Modellversionen. Alerting bei Deprecation-Notices. Geplante Review-Zyklen bei Modellwechsel.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_API_Top10", id: "API10"})
SET c.default_tom_measure =
  "Output-Schema-Validierung (Pydantic/Zod) für alle LLM-Outputs. Escaping vor SQL-Queries, HTML-Templates und Shell-Commands.",
  c.default_tom_measure_source = "lex-llm-draft";

// ── BSI IT-Grundschutz ────────────────────────────────────────────────────────

MATCH (c:Control {framework: "BSI_Grundschutz", id: "ORP.4"})
SET c.default_tom_measure =
  "Rollenkonzept dokumentiert. Zugriffe auf Produktivsysteme nur über authentifizierte Sessions. Berechtigungen nach Least-Privilege. Offboarding-Prozess definiert.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "CON.3"})
SET c.default_tom_measure =
  "Automatische tägliche Backups, AES-256-verschlüsselt. Backup-Test monatlich. Retention: 30 Tage.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "CON.1"})
SET c.default_tom_measure =
  "TLS 1.2+ für alle Verbindungen erzwungen. AES-256 für ruhende Daten. Schlüsselrotation jährlich oder bei Verdacht auf Kompromittierung.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "APP.3.1"})
SET c.default_tom_measure =
  "Input-Validierung für alle API-Endpunkte. OWASP Top 10 als Entwicklungsrichtlinie. Dependency-Updates automatisiert.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "OPS.1.1.5"})
SET c.default_tom_measure =
  "Zentrales Log-Management. Anomalie-Alerting für fehlgeschlagene Authentifizierungen (>5 in 5 Min). Log-Retention 90 Tage.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "DER.2.1"})
SET c.default_tom_measure =
  "Incident-Response-Plan dokumentiert. Meldekette definiert (DSGVO Art. 33: 72h). Post-Mortem nach jedem Sicherheitsvorfall.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "SYS.1.1"})
SET c.default_tom_measure =
  "Server-Hardening: SSH-Key-only, kein Root-Login, automatische Security-Updates aktiv. Firewall-Regeln: nur benötigte Ports offen.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "NET.1.1"})
SET c.default_tom_measure =
  "Netzwerksegmentierung mit isolierten Container-Netzwerken. Datenbank-Container nicht direkt extern erreichbar. Reverse-Proxy vor allen Services.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "CON.2"})
SET c.default_tom_measure =
  "Datenschutzkonzept dokumentiert. Datensparsamkeit implementiert: nur notwendige Felder gespeichert. Pseudonymisierung via UUID-Mapping.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "ORP.3"})
SET c.default_tom_measure =
  "Jährliche Datenschutz- und Sicherheitsschulung für alle Mitarbeitenden. Bestätigung dokumentiert. KI-Literacy-Schulung gem. EU AI Act Art. 4.",
  c.default_tom_measure_source = "lex-llm-draft";

// ── BSI IT-Grundschutz — ADR-127 Phase 2 (10 reachable controls wired in Phase 2.0) ──

MATCH (c:Control {framework: "BSI_Grundschutz", id: "APP.3.2"})
SET c.default_tom_measure =
  "TLS gemäß BSI TR-02102 mit Forward Secrecy erzwungen. Datei-Uploads auf Whitelist beschränkt. Zugriffsversuche werden protokolliert.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "APP.4.3"})
SET c.default_tom_measure =
  "Zugriffskontrolle via RBAC auf Tabellenebene. Sensible Felder bei Speicherung AES-256-verschlüsselt. DB-System regelmäßig gepatcht.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "CON.10"})
SET c.default_tom_measure =
  "Code-Review für alle Commits etabliert. Secrets serverseitig verwaltet, nie im Code. Schulung für kritische Module.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "OPS.1.1.2"})
SET c.default_tom_measure =
  "Admin-Zugänge über MFA und Just-in-Time-Access. Trennung von Entwicklungs-, Test- und Produktivumgebung. Alle Admin-Aktionen protokolliert.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "OPS.1.1.3"})
SET c.default_tom_measure =
  "Änderungen nur nach formaler Change-Freigabe. Patches in isolierter Testumgebung validiert. Rollback-Plan fester Teil jedes Change-Requests.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "OPS.1.2.4"})
SET c.default_tom_measure =
  "Zugriff ausschließlich über VPN mit MFA. Endgeräte mit Festplattenverschlüsselung und Endpoint-Schutz. Trennung privat/dienstlich erzwungen.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "OPS.1.2.5"})
SET c.default_tom_measure =
  "Fernwartung nur über verschlüsselte Kanäle mit expliziter Genehmigung. Zugriff zeitlich und funktional minimiert. Alle Sitzungen protokolliert.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "OPS.2.2"})
SET c.default_tom_measure =
  "Shared-Responsibility-Modell vertraglich definiert. Datenresidenz in der EU geregelt. Cloud-Sicherheit an BSI C5 orientiert.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "ORP.1"})
SET c.default_tom_measure =
  "Verantwortlichkeiten via RACI-Matrix für kritische Prozesse definiert. Funktionstrennung zwischen Entwicklung, Betrieb und Sicherheit umgesetzt.",
  c.default_tom_measure_source = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "SYS.2.1"})
SET c.default_tom_measure =
  "Clients durch Festplattenverschlüsselung und EDR geschützt. Automatische Updates für OS und Anwendungen aktiviert. Bildschirmsperre nach Inaktivität.",
  c.default_tom_measure_source = "lex-llm-draft";

// ── BSI IT-Grundschutz — EN measures (ADR-127 EN-Maßnahmen-Backbone, 19 reachable) ──
// default_tom_measure_en + default_tom_measure_source_en="lex-llm-draft". Parallel to DE.
// c.source + c.default_tom_measure (DE) untouched. SET (idempotent). NOT in make seed-all (Fujitsu-Track).

MATCH (c:Control {framework: "BSI_Grundschutz", id: "APP.3.1"})
SET c.default_tom_measure_en =
  "Input validation on all API endpoints. OWASP Top 10 as development guideline. Dependency updates automated.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "APP.3.2"})
SET c.default_tom_measure_en =
  "TLS per BSI TR-02102 with forward secrecy enforced. File uploads restricted to a whitelist. Access attempts logged.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "APP.4.3"})
SET c.default_tom_measure_en =
  "Access control via RBAC at table level. Sensitive fields AES-256-encrypted at rest. Database system patched regularly.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "CON.1"})
SET c.default_tom_measure_en =
  "TLS 1.2+ enforced on all connections. AES-256 for data at rest. Key rotation annually or on suspected compromise.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "CON.2"})
SET c.default_tom_measure_en =
  "Data protection concept documented. Data minimisation implemented: only necessary fields stored. Pseudonymisation via UUID mapping.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "CON.3"})
SET c.default_tom_measure_en =
  "Automated daily backups, AES-256-encrypted. Backup restore tested monthly. Retention: 30 days.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "CON.10"})
SET c.default_tom_measure_en =
  "Code review established for all commits. Secrets managed server-side, never in code. Training for critical modules.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "DER.2.1"})
SET c.default_tom_measure_en =
  "Incident response plan documented. Notification chain defined (GDPR Art. 33: 72h). Post-mortem after every security incident.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "OPS.1.1.2"})
SET c.default_tom_measure_en =
  "Admin access via MFA and just-in-time access. Separation of development, test and production environments. All admin actions logged.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "OPS.1.1.3"})
SET c.default_tom_measure_en =
  "Changes only after formal change approval. Patches validated in an isolated test environment. Rollback plan part of every change request.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "OPS.1.1.5"})
SET c.default_tom_measure_en =
  "Central log management. Anomaly alerting for failed authentications (>5 in 5 min). Log retention 90 days.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "OPS.1.2.4"})
SET c.default_tom_measure_en =
  "Access exclusively via VPN with MFA. Endpoints with full-disk encryption and endpoint protection. Private/business separation enforced.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "OPS.1.2.5"})
SET c.default_tom_measure_en =
  "Remote maintenance only over encrypted channels with explicit approval. Access minimised in time and scope. All sessions logged.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "OPS.2.2"})
SET c.default_tom_measure_en =
  "Shared-responsibility model defined contractually. Data residency in the EU stipulated. Cloud security aligned with BSI C5.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "ORP.1"})
SET c.default_tom_measure_en =
  "Responsibilities defined via RACI matrix for critical processes. Separation of duties between development, operations and security implemented.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "ORP.3"})
SET c.default_tom_measure_en =
  "Annual data protection and security training for all staff. Acknowledgement documented. AI literacy training per EU AI Act Art. 4.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "ORP.4"})
SET c.default_tom_measure_en =
  "Role concept documented. Production access only via authenticated sessions. Permissions follow least privilege. Offboarding process defined.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "SYS.1.1"})
SET c.default_tom_measure_en =
  "Server hardening: SSH-key-only, no root login, automatic security updates active. Firewall rules: only required ports open.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "SYS.2.1"})
SET c.default_tom_measure_en =
  "Clients protected by full-disk encryption and EDR. Automatic updates for OS and applications enabled. Screen lock after inactivity.",
  c.default_tom_measure_source_en = "lex-llm-draft";

// ── OWASP LLM/API — EN measures (ADR-129 PR 10, translated from the DE lex-llm-draft texts) ──
// Same convention as the BSI EN block above: default_tom_measure_en +
// default_tom_measure_source_en="lex-llm-draft". DE texts + c.source untouched.
// NET.1.1 stays EN-less on purpose (scan-unreachable). NOT in make seed-all (Fujitsu track).

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM01"})
SET c.default_tom_measure_en =
  "Input validation before LLM handover: server-side anonymisation/pseudonymisation of all assets. Regex blocklist for known injection patterns (role takeover, jailbreak phrases) as a server-side pre-filter.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM02"})
SET c.default_tom_measure_en =
  "System prompt contains an explicit data protection instruction. PII detection scans all API responses before forwarding to the client.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM03"})
SET c.default_tom_measure_en =
  "Dependency pinning in requirements.txt (==). Automated vulnerability scans in the CI/CD pipeline.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM04"})
SET c.default_tom_measure_en =
  "Training data from verified sources only. Embedding inputs validated before vector storage. Similarity threshold (cosine > 0.75) for RAG retrievals.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM05"})
SET c.default_tom_measure_en =
  "Output schema validation (Pydantic) for all LLM responses. HTML escaping before rendering. SQL parameterisation before database operations.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM06"})
SET c.default_tom_measure_en =
  "Tool-use whitelist in the system prompt. Server-side allowlist for permitted tool calls. No autonomous database write access without explicit user confirmation.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM07"})
SET c.default_tom_measure_en =
  "System prompt not exposed to the client. API responses filtered: internal metadata (model parameters, system content) removed in the backend layer.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM08"})
SET c.default_tom_measure_en =
  "Similarity threshold for RAG retrievals (cosine > 0.75). Chunk validation against injection patterns. No direct user inputs as embedding queries without sanitisation.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM09"})
SET c.default_tom_measure_en =
  "Visible disclaimer on AI-generated content. For fact-sensitive use cases: RAG grounding with source attribution. Four-eyes principle for critical decisions.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM10"})
SET c.default_tom_measure_en =
  "Per session: max_tokens limit (4096), requests per minute (10 RPM), daily token budget (100k). In-memory-cache-based rate limiting.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_API_Top10", id: "API1"})
SET c.default_tom_measure_en =
  "Server-side binding of session to conversation ID. User A cannot retrieve user B's conversation data — not even via conversation_id manipulation.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_API_Top10", id: "API2"})
SET c.default_tom_measure_en =
  "API keys exclusively as server-side environment variables. Short-lived JWTs (<= 1h) for end-user authentication.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_API_Top10", id: "API3"})
SET c.default_tom_measure_en =
  "Response filtering in the backend: internal metadata (system prompt content, user_ids, model parameters) removed before client delivery.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_API_Top10", id: "API4"})
SET c.default_tom_measure_en =
  "Combined limits: max_tokens + RPM + daily token budget. Rate-limiting middleware. Separate, stricter limit for sensitive business flows.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_API_Top10", id: "API5"})
SET c.default_tom_measure_en =
  "RBAC: admin role for system prompt changes, regular users chat endpoint only. Middleware guard before every route handler.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_API_Top10", id: "API6"})
SET c.default_tom_measure_en =
  "Sensitive flows (automated decisions, bulk generation) protected by additional authentication. Separate, stricter rate limit.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_API_Top10", id: "API7"})
SET c.default_tom_measure_en =
  "URL allowlist for external content. Blocking of internal IP ranges (RFC 1918) and cloud metadata endpoints (169.254.169.254).",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_API_Top10", id: "API8"})
SET c.default_tom_measure_en =
  "HTTPS-only enforced. Explicit timeouts (connect: 5s, read: 30s). No debug information or stack traces in production responses.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_API_Top10", id: "API9"})
SET c.default_tom_measure_en =
  "Service inventory with deployed model versions. Alerting on deprecation notices. Scheduled review cycles on model changes.",
  c.default_tom_measure_source_en = "lex-llm-draft";

MATCH (c:Control {framework: "OWASP_API_Top10", id: "API10"})
SET c.default_tom_measure_en =
  "Output schema validation (Pydantic/Zod) for all LLM outputs. Escaping before SQL queries, HTML templates and shell commands.",
  c.default_tom_measure_source_en = "lex-llm-draft";
