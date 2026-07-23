// ============================================================
// LEX-ORCHESTRA — Layer 10: German National Law
// Applies to: DE-jurisdiction deployments
// jurisdictions: ["DE"]
// Sources: BGBl., gesetze-im-internet.de
// Idempotent: MERGE-only, safe to re-run
// ============================================================

// ============================================================
// 1. DDG § 5 — Impressumspflicht (canonical form, replaces TMG § 5)
// ============================================================

MERGE (l:Law {name: "DDG", article: "5"})
ON CREATE SET
  l.title         = "Impressumspflicht (Anbieterkennzeichnung)",
  l.short         = "DDG § 5",
  l.regulation    = "Digitale-Dienste-Gesetz (DDG)",
  l.source        = "BGBl. I 2024 Nr. 149 — gesetze-im-internet.de/ddg/",
  l.valid_from    = date("2024-05-14"),
  l.applies_from  = date("2024-05-14"),
  l.confidence    = 1.0,
  l.jurisdictions = ["DE"],
  l.last_verified = date("2026-03-21"),
  l.note_de       = "Ersetzt TMG § 5 seit 14.05.2024."
SET l.last_verified = date("2026-03-21");

// ============================================================
// 2. DE-specific Law nodes (from BLOCK B)
// ============================================================

// TDDDG (renamed from TTDSG 2024-05-14 — ADR-130 build-time fix: MERGEing
// the old name would resurrect a stale TTDSG node next to the renamed one)
MERGE (l:Law {name: "TDDDG", article: "25"})
ON CREATE SET l.title = "Schutz der Privatsphäre bei Endeinrichtungen (Cookies)",
              l.short = "TDDDG § 25"
SET l.jurisdictions = ["DE"];

MERGE (l:Law {name: "BGB", article: "305-310"})
ON CREATE SET l.title = "AGB-Recht — Einbeziehung und Inhaltskontrolle",
              l.short = "BGB §§ 305-310"
SET l.jurisdictions = ["DE"];

MERGE (l:Law {name: "BGB", article: "312g"})
ON CREATE SET l.title = "Widerrufsrecht bei Fernabsatzverträgen",
              l.short = "BGB § 312g"
SET l.jurisdictions = ["DE"];

MERGE (l:Law {name: "PAngV", article: "1"})
ON CREATE SET l.title = "Preisangabenpflicht gegenüber Verbrauchern",
              l.short = "PAngV § 1"
SET l.jurisdictions = ["DE"];

MERGE (l:Law {name: "UWG", article: "5a"})
ON CREATE SET l.title = "Irreführung durch Unterlassen (Impressum B2B)",
              l.short = "UWG § 5a"
SET l.jurisdictions = ["DE"];

// ============================================================
// 3. DE-specific DocumentType nodes (from BLOCK C)
// ============================================================

MERGE (d:DocumentType {type: "Impressum"})
ON CREATE SET d.name_de = "Impressum / Anbieterkennzeichnung",
              d.required_for = "Gesetzliche Pflicht für gewerbliche Websites (DDG § 5)",
              d.path_template = "/legal/impressum.md"
SET d.jurisdictions = ["DE"];

MERGE (d:DocumentType {type: "AGB"})
ON CREATE SET
  d.name_de = "Allgemeine Geschäftsbedingungen",
  d.required_for = "B2C-Shops, SaaS mit Endkunden, Marketplaces",
  d.business_types = ["shop", "saas_b2c", "marketplace"],
  d.legal_basis = "BGB §§ 305-310",
  d.path_template = "/legal/drafts/agb.md"
SET d.jurisdictions = ["DE"];

MERGE (d:DocumentType {type: "Widerrufsbelehrung"})
ON CREATE SET
  d.name_de = "Widerrufsbelehrung / Widerrufsformular",
  d.required_for = "Alle B2C-Fernabsatzverträge gem. §§ 312g, 355 BGB",
  d.business_types = ["shop", "saas_b2c"],
  d.legal_basis = "BGB §§ 312g, 355, 356",
  d.note = "14-Tage Widerrufsfrist. Muster-Widerrufsformular gesetzlich vorgeschrieben.",
  d.path_template = "/legal/drafts/widerruf.md"
SET d.jurisdictions = ["DE"];

MERGE (d:DocumentType {type: "Preisangaben"})
ON CREATE SET
  d.name_de = "Preisangaben / Preistransparenz",
  d.required_for = "B2C-Shops — Bruttopreise, Versandkosten, Grundpreise",
  d.business_types = ["shop"],
  d.legal_basis = "PAngV § 1",
  d.path_template = "/legal/drafts/preisangaben.md"
SET d.jurisdictions = ["DE"];

MERGE (d:DocumentType {type: "Lieferbedingungen"})
ON CREATE SET
  d.name_de = "Liefer- und Versandbedingungen",
  d.required_for = "Online-Shops mit physischem Warenversand",
  d.business_types = ["shop_physical"],
  d.legal_basis = "BGB § 312j",
  d.path_template = "/legal/drafts/lieferbedingungen.md"
SET d.jurisdictions = ["DE"];

// ============================================================
// 4. DE-specific Service nodes (from BLOCK A + SERVICE DATA PROPERTIES)
// ============================================================

MERGE (s:Service {name: "Hetzner"})
ON CREATE SET s.category = "hosting", s.country = "Germany", s.gdpr_adequate = true,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["hetzner.com", "hetzner.de"]
SET s.dpa_url = "https://www.hetzner.com/AV/",
    s.jurisdictions = ["EU", "global"];

MATCH (s:Service {name: "Hetzner"})
SET s.data_categories = "Server-Logs, IP-Adressen, technische Verbindungsdaten",
    s.data_subjects = "Endnutzer der Anwendung (indirekt)",
    s.processing_purpose = "Server-Hosting, Infrastruktur-Bereitstellung",
    s.deletion_period = "Gemäß Hetzner AV-Vertrag — Log-Daten 7 Tage default";

MERGE (s:Service {name: "Plausible"})
ON CREATE SET s.category = "analytics", s.country = "Germany", s.gdpr_adequate = true,
              s.dpa_required = true, s.ai_act_relevant = false, s.domains = ["plausible.io"]
SET s.dpa_url = "https://plausible.io/dpa",
    s.jurisdictions = ["EU", "global"];

MATCH (s:Service {name: "Plausible"})
SET s.data_categories = "IP-Adressen, Nutzungsverhalten, Seitenaufrufe, Session-Daten, Gerätedaten",
    s.data_subjects = "Website-Besucher, App-Nutzer",
    s.processing_purpose = "Web-Analyse, Nutzerverhalten, Produktanalyse",
    s.deletion_period = "Konfigurierbar, standard 12-24 Monate";

MERGE (s:Service {name: "Coolify"})
ON CREATE SET s.category = "hosting", s.country = "EU",
              s.gdpr_adequate = true, s.dpa_required = false,
              s.ai_act_relevant = false, s.domains = ["coolify.io"]
SET s.dpa_url = "https://coolify.io/docs/privacy",
    s.jurisdictions = ["EU", "global"];

// ============================================================
// 5. Cookie Consent Relationships (from NEUE RELATIONSHIPS / SHOP LEGAL DOCS)
// Note: Plausible intentionally excluded — cookieless analytics, no consent required
// ============================================================

MATCH (s:Service {name: "Mixpanel"}), (d:DocumentType {type: "Cookie_Consent"})
MERGE (s)-[:REQUIRES]->(d);

MATCH (s:Service {name: "PostHog"}), (d:DocumentType {type: "Cookie_Consent"})
MERGE (s)-[:REQUIRES]->(d);

MATCH (s:Service {name: "HubSpot"}), (d:DocumentType {type: "Cookie_Consent"})
MERGE (s)-[:REQUIRES]->(d);

MATCH (s:Service {name: "Intercom"}), (d:DocumentType {type: "Cookie_Consent"})
MERGE (s)-[:REQUIRES]->(d);

// ============================================================
// 6. SHOP LEGAL DOCS Relationships (from BLOCK)
// ============================================================

MATCH (d:DocumentType {type: "AGB"}), (l:Law {name: "BGB", article: "305-310"})
MERGE (d)-[:BASED_ON]->(l);

MATCH (d:DocumentType {type: "Widerrufsbelehrung"}), (l:Law {name: "BGB", article: "312g"})
MERGE (d)-[:BASED_ON]->(l);

MATCH (d:DocumentType {type: "Preisangaben"}), (l:Law {name: "PAngV", article: "1"})
MERGE (d)-[:BASED_ON]->(l);

// ============================================================
// 7. Impressum → DDG § 5 relationship
// ============================================================

MATCH (d:DocumentType {type: "Impressum"}), (l:Law {name: "DDG", article: "5"})
MERGE (d)-[:BASED_ON]->(l);

// Cookie_Consent → TDDDG § 25
MATCH (d:DocumentType {type: "Cookie_Consent"}), (l:Law {name: "TDDDG", article: "25"})
MERGE (d)-[:BASED_ON]->(l);

// ============================================================
// 8. Coolify → EU LOCATED_IN relationship (from NEW HOSTING SERVICES)
// ============================================================

MATCH (s:Service {name: "Coolify"}), (c:Country {name: "Germany"})
MERGE (s)-[:LOCATED_IN]->(c);
