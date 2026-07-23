// ============================================================
// LEX-ORCHESTRA — Layer 10: EU Primary Law
// Applies to: any EU-market deployment
// jurisdictions: ["EU"]
// Sources: EUR-Lex (official) — see l.source on each node
// Idempotent: MERGE-only, safe to re-run
// ============================================================


// ============================================================
// BLOCK B — RECHTSQUELLEN UND ARTIKEL (EU-scope only)
// ============================================================

// DSGVO — 7 articles

MERGE (l:Law {name: "DSGVO", article: "28"})
ON CREATE SET l.title = "Auftragsverarbeiter (DPA-Pflicht)",
              l.short = "DSGVO Art. 28"
SET l.jurisdictions = ["EU"];

MERGE (l:Law {name: "DSGVO", article: "46"})
ON CREATE SET l.title = "Übermittlung vorbehaltlich geeigneter Garantien (SCCs)",
              l.short = "DSGVO Art. 46"
SET l.jurisdictions = ["EU"];

MERGE (l:Law {name: "DSGVO", article: "13"})
ON CREATE SET l.title = "Informationspflicht bei Direkterhebung",
              l.short = "DSGVO Art. 13"
SET l.jurisdictions = ["EU"];

MERGE (l:Law {name: "DSGVO", article: "14"})
ON CREATE SET l.title = "Informationspflicht bei Dritterhebung",
              l.short = "DSGVO Art. 14"
SET l.jurisdictions = ["EU"];

MERGE (l:Law {name: "DSGVO", article: "30"})
ON CREATE SET l.title = "Verzeichnis von Verarbeitungstätigkeiten (VVT)",
              l.short = "DSGVO Art. 30"
SET l.jurisdictions = ["EU"];

MERGE (l:Law {name: "DSGVO", article: "32"})
ON CREATE SET l.title = "Sicherheit der Verarbeitung (TOM)",
              l.short = "DSGVO Art. 32"
SET l.jurisdictions = ["EU"];

MERGE (l:Law {name: "DSGVO", article: "37"})
ON CREATE SET l.title = "Benennung eines Datenschutzbeauftragten",
              l.short = "DSGVO Art. 37"
SET l.jurisdictions = ["EU"];

// EU AI Act

MERGE (l:Law {name: "EU AI Act", article: "4"})
ON CREATE SET l.created_at = datetime()
SET l.title            = "Measures for users",
    l.short            = "EU AI Act Art. 4",
    l.regulation       = "Verordnung (EU) 2024/1689",
    l.effective_date   = "2025-02-02",
    l.enforcement_note = "AI Literacy — alle Deployer müssen angemessene KI-Kompetenz sicherstellen",
    l.jurisdictions    = ["EU"],
    l.last_verified    = date("2026-04-19");

MERGE (l:Law {name: "EU AI Act", article: "5"})
ON CREATE SET l.created_at = datetime()
SET l.title            = "Prohibited AI practices",
    l.short            = "EU AI Act Art. 5",
    l.regulation       = "Verordnung (EU) 2024/1689",
    l.effective_date   = "2025-02-02",
    l.enforcement_note = "Verbotene KI-Praktiken — sofortige Geltung ab 02.02.2025",
    l.jurisdictions    = ["EU"],
    l.last_verified    = date("2026-04-19");

MERGE (l:Law {name: "EU AI Act", article: "6"})
ON CREATE SET l.created_at = datetime()
SET l.title            = "Classification rules for high-risk AI systems",
    l.short            = "EU AI Act Art. 6",
    l.regulation       = "Verordnung (EU) 2024/1689",
    l.effective_date   = "2026-08-02",
    l.enforcement_note = "Hochrisiko-KI — Annex III Nr. 1–8",
    l.jurisdictions    = ["EU"],
    l.last_verified    = date("2026-04-19");

// Art. 50 — Transparenzpflichten (finale Nummerierung, EU) 2024/1689)
MERGE (l:Law {name: "EU AI Act", article: "50"})
ON CREATE SET l.created_at = datetime()
SET l.title            = "Transparency obligations for providers and deployers of certain AI systems",
    l.short            = "EU AI Act Art. 50",
    l.regulation       = "Verordnung (EU) 2024/1689",
    l.source           = "EUR-Lex OJ:L_202401689, Art. 50",
    l.valid_from       = date("2024-08-01"),
    l.effective_date   = "2025-08-02",
    l.enforcement_note = "Transparenzpflichten + GPAI-Modelle",
    l.confidence       = 1.0,
    l.jurisdictions    = ["EU"],
    l.last_verified    = date("2026-04-19");

// Art. 52 — Procedure (GPAI with systemic risk — corrected from draft-era title)
MERGE (l:Law {name: "EU AI Act", article: "52"})
SET l.title        = "Procedure",
    l.short        = "EU AI Act Art. 52",
    l.note_de      = "Art. 52 finale Verordnung (EU) 2024/1689. Frühere Quellen nutzen Entwurfsnummerierung wo Art. 52 = Transparenzpflichten (jetzt Art. 50).",
    l.confidence   = 1.0,
    l.last_verified = date("2026-03-21");

MERGE (l:Law {name: "EU AI Act", article: "51"})
ON CREATE SET l.title = "Klassifizierung von GPAI-Modellen",
              l.short = "EU AI Act Art. 51"
SET l.jurisdictions = ["EU"];

// DDG § 5 — kept for backwards compatibility (replaces TMG § 5 since 2024-05-14)

MERGE (l:Law {name: "DDG", article: "5"})
ON CREATE SET
  l.title        = "Impressumspflicht (Anbieterkennzeichnung)",
  l.short        = "DDG § 5",
  l.regulation   = "Digitale-Dienste-Gesetz (DDG)",
  l.source       = "BGBl. I 2024 Nr. 149 — gesetze-im-internet.de/ddg/",
  l.valid_from   = date("2024-05-14"),
  l.applies_from = date("2024-05-14"),
  l.confidence   = 1.0,
  l.note_de      = "Ersetzt TMG § 5 seit 14.05.2024."
SET l.last_verified = date("2026-03-21"),
    l.jurisdictions = ["EU"];

// NIS2 — articles from BLOCK I

MERGE (l:Law {name: "NIS2", article: "21"})
ON CREATE SET l.title = "Risikomanagement-Maßnahmen für die Netz- und Informationssicherheit",
              l.short = "NIS2 Art. 21",
              l.source_pdf = "CELEX_32022L2555_DE_TXT.pdf", l.text = ""
SET l.jurisdictions = ["EU"];

MERGE (l:Law {name: "NIS2", article: "23"})
ON CREATE SET l.title = "Meldepflichten bei erheblichen Sicherheitsvorfällen",
              l.short = "NIS2 Art. 23",
              l.source_pdf = "CELEX_32022L2555_DE_TXT.pdf", l.text = ""
SET l.jurisdictions = ["EU"];

MERGE (l:Law {name: "NIS2", article: "24"})
ON CREATE SET l.title = "Governance: Verantwortung der Leitungsorgane",
              l.short = "NIS2 Art. 24",
              l.source_pdf = "CELEX_32022L2555_DE_TXT.pdf", l.text = ""
SET l.jurisdictions = ["EU"];

MERGE (l:Law {name: "NIS2", article: "27"})
ON CREATE SET l.title = "Registrierung wesentlicher und wichtiger Einrichtungen",
              l.short = "NIS2 Art. 27",
              l.source_pdf = "CELEX_32022L2555_DE_TXT.pdf", l.text = ""
SET l.jurisdictions = ["EU"];

MERGE (l:Law {name: "NIS2", article: "32"})
ON CREATE SET l.title = "Aufsichtsmaßnahmen für wesentliche Einrichtungen",
              l.short = "NIS2 Art. 32",
              l.source_pdf = "CELEX_32022L2555_DE_TXT.pdf", l.text = ""
SET l.jurisdictions = ["EU"];

// NIS2 — additional articles from BLOCK M

MERGE (l:Law {name: "NIS2", article: "2"})
ON CREATE SET
  l.title      = "Anwendungsbereich",
  l.short      = "NIS2 Art. 2",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555"
ON MATCH SET
  l.title      = "Anwendungsbereich",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555"
SET l.jurisdictions = ["EU"];

MERGE (l:Law {name: "NIS2", article: "3"})
ON CREATE SET
  l.title      = "Wesentliche und wichtige Einrichtungen",
  l.short      = "NIS2 Art. 3",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555"
ON MATCH SET
  l.title      = "Wesentliche und wichtige Einrichtungen",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555"
SET l.jurisdictions = ["EU"];

MERGE (l:Law {name: "NIS2", article: "4"})
ON CREATE SET
  l.title      = "Sektorspezifische Rechtsakte der Union",
  l.short      = "NIS2 Art. 4",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555"
ON MATCH SET
  l.title      = "Sektorspezifische Rechtsakte der Union",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555"
SET l.jurisdictions = ["EU"];

MERGE (l:Law {name: "NIS2", article: "6"})
ON CREATE SET
  l.title      = "Begriffsbestimmungen",
  l.short      = "NIS2 Art. 6",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555"
ON MATCH SET
  l.title      = "Begriffsbestimmungen",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555"
SET l.jurisdictions = ["EU"];

MERGE (l:Law {name: "NIS2", article: "7"})
ON CREATE SET
  l.title      = "Nationale Cybersicherheitsstrategie",
  l.short      = "NIS2 Art. 7",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555"
ON MATCH SET
  l.title      = "Nationale Cybersicherheitsstrategie",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555"
SET l.jurisdictions = ["EU"];

MERGE (l:Law {name: "NIS2", article: "10"})
ON CREATE SET
  l.title      = "Computer-Notfallteams (CSIRTs)",
  l.short      = "NIS2 Art. 10",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555"
ON MATCH SET
  l.title      = "Computer-Notfallteams (CSIRTs)",
  l.regulation = "Richtlinie (EU) 2022/2555",
  l.source     = "CELEX:32022L2555"
SET l.jurisdictions = ["EU"];

// Update existing NIS2 articles with source + regulation
MATCH (l:Law {name: "NIS2"})
WHERE l.article IN ["21","23","24","27","32"]
SET l.source     = "CELEX:32022L2555",
    l.regulation = "Richtlinie (EU) 2022/2555";

// ============================================================
// BLOCK K — CRA (Cyber Resilience Act, Regulation (EU) 2024/2847)
// Source: EUR-Lex OJ:L_202402847 (downloaded 2026-03-20)
// ============================================================

// CRA Law nodes
MERGE (l:Law {name: "CRA", article: "Annex I"})
ON CREATE SET
  l.title = "Grundlegende Cybersicherheitsanforderungen für Produkte mit digitalen Elementen",
  l.short = "CRA Anhang I",
  l.regulation = "Verordnung (EU) 2024/2847",
  l.in_force = "2024-12-10",
  l.applies_from = "2027-12-11",
  l.source = "EUR-Lex OJ:L_202402847"
SET l.jurisdictions = ["EU"];

MERGE (l:Law {name: "CRA", article: "13"})
ON CREATE SET
  l.title = "Pflichten der Hersteller",
  l.short = "CRA Art. 13",
  l.regulation = "Verordnung (EU) 2024/2847",
  l.applies_from = "2027-12-11",
  l.note = "Risikobewertung, Dokumentation, Supply-Chain-Sorgfalt, mind. 5 Jahre Support",
  l.source = "EUR-Lex OJ:L_202402847"
SET l.jurisdictions = ["EU"];

MERGE (l:Law {name: "CRA", article: "14"})
ON CREATE SET
  l.title = "Meldepflichten der Hersteller — Schwachstellen und Sicherheitsvorfälle",
  l.short = "CRA Art. 14",
  l.regulation = "Verordnung (EU) 2024/2847",
  l.applies_from = "2026-09-11",
  l.note = "24h Frühwarnung, 72h Vollmeldung, 14 Tage Abschlussbericht",
  l.source = "EUR-Lex OJ:L_202402847"
SET l.jurisdictions = ["EU"];

// CRA Annex I Part I — Essential cybersecurity requirements (product properties)
MERGE (r:Requirement {id: "CRA-I-1a", framework: "CRA"})
ON CREATE SET
  r.title = "Keine bekannten ausnutzbaren Schwachstellen bei Marktbereitstellung",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part I",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I §2(a)";

MERGE (r:Requirement {id: "CRA-I-1b", framework: "CRA"})
ON CREATE SET
  r.title = "Sichere Standardkonfiguration und Reset-Möglichkeit",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part I",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I §2(b)";

MERGE (r:Requirement {id: "CRA-I-1c", framework: "CRA"})
ON CREATE SET
  r.title = "Sicherheitsaktualisierungen möglich, inkl. automatische Updates als Standard",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part I",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I §2(c)";

MERGE (r:Requirement {id: "CRA-I-1d", framework: "CRA"})
ON CREATE SET
  r.title = "Zugriffskontrolle — Authentifizierung, Identitäts- und Zugangsverwaltung",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part I",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I §2(d)";

MERGE (r:Requirement {id: "CRA-I-1e", framework: "CRA"})
ON CREATE SET
  r.title = "Vertraulichkeit — Verschlüsselung gespeicherter und übertragener Daten",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part I",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I §2(e)";

MERGE (r:Requirement {id: "CRA-I-1f", framework: "CRA"})
ON CREATE SET
  r.title = "Datenintegrität — Schutz vor unbefugter Manipulation, Änderungen melden",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part I",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I §2(f)";

MERGE (r:Requirement {id: "CRA-I-1g", framework: "CRA"})
ON CREATE SET
  r.title = "Datenminimierung — Verarbeitung auf erforderliches Maß beschränken",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part I",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I §2(g)";

MERGE (r:Requirement {id: "CRA-I-1h", framework: "CRA"})
ON CREATE SET
  r.title = "Verfügbarkeit — DoS-Resilienz, Verfügbarkeit wesentlicher Funktionen nach Sicherheitsvorfall",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part I",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I §2(h)";

MERGE (r:Requirement {id: "CRA-I-1j", framework: "CRA"})
ON CREATE SET
  r.title = "Minimale Angriffsfläche — auch bei externen Schnittstellen",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part I",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I §2(j)";

MERGE (r:Requirement {id: "CRA-I-1l", framework: "CRA"})
ON CREATE SET
  r.title = "Sicherheits-Logging und -Monitoring mit Opt-out-Mechanismus",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part I",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I §2(l)";

// CRA Annex I Part II — Vulnerability handling requirements
MERGE (r:Requirement {id: "CRA-II-1", framework: "CRA"})
ON CREATE SET
  r.title = "SBOM erstellen — Schwachstellen und Komponenten dokumentieren",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part II",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I Part II §1";

MERGE (r:Requirement {id: "CRA-II-2", framework: "CRA"})
ON CREATE SET
  r.title = "Schwachstellen unverzüglich behandeln und beheben, Sicherheitsupdates bereitstellen",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part II",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I Part II §2";

MERGE (r:Requirement {id: "CRA-II-3", framework: "CRA"})
ON CREATE SET
  r.title = "Regelmäßige Sicherheitstests und -prüfungen",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part II",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I Part II §3";

MERGE (r:Requirement {id: "CRA-II-5", framework: "CRA"})
ON CREATE SET
  r.title = "Strategie für koordinierte Offenlegung von Schwachstellen (CVD-Policy)",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part II",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I Part II §5";

MERGE (r:Requirement {id: "CRA-II-7", framework: "CRA"})
ON CREATE SET
  r.title = "Sicherer Update-Verteilungsmechanismus für Sicherheitsupdates",
  r.level = "ESSENTIAL",
  r.annex = "Annex I Part II",
  r.source = "CRA Regulation (EU) 2024/2847 Annex I Part II §7";

// Link requirements to Law node
MATCH (l:Law {name: "CRA", article: "Annex I"}), (r:Requirement {framework: "CRA"})
WHERE r.annex IN ["Annex I Part I", "Annex I Part II"]
MERGE (l)-[:CONTAINS]->(r);

// CRA → BSI relationships
MATCH (c:Control {framework: "BSI_Grundschutz", id: "DER.2.1"}),
      (l:Law {name: "CRA", article: "14"})
MERGE (c)-[:IMPLEMENTS]->(l);

MATCH (c:Control {framework: "BSI_Grundschutz", id: "CON.1"}),
      (l:Law {name: "CRA", article: "Annex I"})
MERGE (c)-[:IMPLEMENTS]->(l);

MATCH (c:Control {framework: "BSI_Grundschutz", id: "APP.3.1"}),
      (l:Law {name: "CRA", article: "Annex I"})
MERGE (c)-[:IMPLEMENTS]->(l);

MATCH (c:Control {framework: "BSI_Grundschutz", id: "ORP.4"}),
      (l:Law {name: "CRA", article: "Annex I"})
MERGE (c)-[:IMPLEMENTS]->(l);

// CRA → ISO 27001 relationships
MATCH (c:Control {framework: "ISO_27001"}),
      (l:Law {name: "CRA", article: "Annex I"})
WHERE c.id IN ["A.8.8", "A.8.25", "A.8.27", "A.5.7"]
MERGE (c)-[:IMPLEMENTS]->(l);


// ============================================================
// BLOCK L — DORA (Digital Operational Resilience Act, Regulation (EU) 2022/2554)
// Source: EUR-Lex OJ:L_202202554 — Amtsblatt L 333/1, 27.12.2022
// applies_from: 2025-01-17 (Art. 64 — verified from PDF)
// Scope: Financial sector — banks, insurance, fintech, payment institutions,
//        crypto-asset service providers, investment firms (Art. 2)
// ============================================================

// DORA Law nodes

MERGE (l:Law {name: "DORA", article: "5"})
ON CREATE SET
  l.title        = "Governance und Organisation",
  l.short        = "DORA Art. 5",
  l.description  = "IKT-Governance — Leitungsorgan trägt Gesamtverantwortung für IKT-Risikomanagement",
  l.source       = "EUR-Lex OJ:L_202202554",
  l.confidence   = 1.0,
  l.valid_from   = date("2022-12-27"),
  l.applies_from = date("2025-01-17"),
  l.last_verified = date("2026-03-21"),
  l.jurisdictions = ["EU"],
  l.sector       = "financial"
SET l.jurisdictions = ["EU"];

MERGE (l:Law {name: "DORA", article: "6"})
ON CREATE SET
  l.title        = "IKT-Risikomanagementrahmen",
  l.short        = "DORA Art. 6",
  l.description  = "Finanzunternehmen müssen einen IKT-Risikomanagementrahmen einrichten, aufrechterhalten und weiterentwickeln",
  l.source       = "EUR-Lex OJ:L_202202554",
  l.confidence   = 1.0,
  l.valid_from   = date("2022-12-27"),
  l.applies_from = date("2025-01-17"),
  l.last_verified = date("2026-03-21"),
  l.jurisdictions = ["EU"],
  l.sector       = "financial"
SET l.jurisdictions = ["EU"];

MERGE (l:Law {name: "DORA", article: "17"})
ON CREATE SET
  l.title        = "Prozess für die Behandlung IKT-bezogener Vorfälle",
  l.short        = "DORA Art. 17",
  l.description  = "Finanzunternehmen müssen einen Prozess für die Verwaltung IKT-bezogener Vorfälle einrichten",
  l.source       = "EUR-Lex OJ:L_202202554",
  l.confidence   = 1.0,
  l.valid_from   = date("2022-12-27"),
  l.applies_from = date("2025-01-17"),
  l.last_verified = date("2026-03-21"),
  l.jurisdictions = ["EU"],
  l.sector       = "financial"
SET l.jurisdictions = ["EU"];

MERGE (l:Law {name: "DORA", article: "19"})
ON CREATE SET
  l.title        = "Meldung schwerwiegender IKT-bezogener Vorfälle",
  l.short        = "DORA Art. 19",
  l.description  = "Meldung schwerwiegender IKT-bezogener Vorfälle und freiwillige Meldung erheblicher Cyberbedrohungen an zuständige Behörde",
  l.source       = "EUR-Lex OJ:L_202202554",
  l.confidence   = 1.0,
  l.valid_from   = date("2022-12-27"),
  l.applies_from = date("2025-01-17"),
  l.last_verified = date("2026-03-21"),
  l.jurisdictions = ["EU"],
  l.sector       = "financial"
SET l.jurisdictions = ["EU"];

MERGE (l:Law {name: "DORA", article: "24"})
ON CREATE SET
  l.title        = "Allgemeine Anforderungen für das Testen der digitalen operationalen Resilienz",
  l.short        = "DORA Art. 24",
  l.description  = "Finanzunternehmen müssen ein solides und umfassendes Programm für das Testen der digitalen operationalen Resilienz einrichten",
  l.source       = "EUR-Lex OJ:L_202202554",
  l.confidence   = 1.0,
  l.valid_from   = date("2022-12-27"),
  l.applies_from = date("2025-01-17"),
  l.last_verified = date("2026-03-21"),
  l.jurisdictions = ["EU"],
  l.sector       = "financial"
SET l.jurisdictions = ["EU"];

MERGE (l:Law {name: "DORA", article: "28"})
ON CREATE SET
  l.title        = "Allgemeine Prinzipien des IKT-Drittparteienrisikomanagements",
  l.short        = "DORA Art. 28",
  l.description  = "Finanzunternehmen müssen IKT-Drittparteienrisiken als integralen Bestandteil ihres IKT-Risikomanagements verwalten — vertragliche Anforderungen an IKT-Dienstleister",
  l.source       = "EUR-Lex OJ:L_202202554",
  l.confidence   = 1.0,
  l.valid_from   = date("2022-12-27"),
  l.applies_from = date("2025-01-17"),
  l.last_verified = date("2026-03-21"),
  l.jurisdictions = ["EU"],
  l.sector       = "financial"
SET l.jurisdictions = ["EU"];

// DORA DocumentTypes

MERGE (d:DocumentType {type: "DORA_ICT_Risk_Management_Framework"})
ON CREATE SET
  d.name_de      = "IKT-Risikomanagementrahmen",
  d.required_for = "Finanzunternehmen — Nachweis eines etablierten IKT-Risikomanagementrahmens (DORA Art. 6)",
  d.path_template = "/legal/drafts/dora_ict_risk_framework.md"
SET d.jurisdictions = ["EU"];

MERGE (d:DocumentType {type: "DORA_ICT_Incident_Report"})
ON CREATE SET
  d.name_de      = "IKT-Vorfallsmeldung",
  d.required_for = "Finanzunternehmen — Meldung schwerwiegender IKT-bezogener Vorfälle an Aufsichtsbehörde (DORA Art. 19)",
  d.path_template = "/legal/drafts/dora_incident_report.md"
SET d.jurisdictions = ["EU"];

// DORA — DocumentType REQUIRES relationships
MATCH (d:DocumentType {type: "DORA_ICT_Risk_Management_Framework"}), (l:Law {name: "DORA", article: "6"})
MERGE (d)-[:REQUIRED_BY]->(l);

MATCH (d:DocumentType {type: "DORA_ICT_Incident_Report"}), (l:Law {name: "DORA", article: "19"})
MERGE (d)-[:REQUIRED_BY]->(l);

// DORA Art. 28 — Payment processors MAY_REQUIRE compliance
// Stripe is an IKT-Drittdienstleister for financial sector clients
MATCH (s:Service {name: "Stripe"}), (l:Law {name: "DORA", article: "28"})
MERGE (s)-[:MAY_REQUIRE]->(l);


// ============================================================
// BLOCK C — DOKUMENT-TYPEN (EU-scope only)
// Excluded: Impressum, AGB, Widerrufsbelehrung, Preisangaben, Lieferbedingungen (DE-specific)
// ============================================================

MERGE (d:DocumentType {type: "AVV"})
SET d.name_de = "Auftragsverarbeitungsvertrag",
    d.legal_basis = "DSGVO Art. 28",
    d.required_for = "Alle Auftragsverarbeiter die personenbezogene Daten verarbeiten",
    d.path_template = "/legal/drafts/avv_{run_id}.md",
    d.jurisdictions = ["EU"],
    d.required_sections = [
      "§1 Anwendungsbereich",
      "§2 Konkretisierung des Auftragsinhalts",
      "§3 Verpflichtungen und Weisungsbefugnis",
      "§4 Technisch-organisatorische Maßnahmen",
      "§5 Drittlandtransfer",
      "§6 Mitteilung bei Verstößen",
      "§7 Löschung und Rückgabe von Daten",
      "§8 Subunternehmen",
      "§9 Datenschutzkontrolle",
      "§10 Haftung und Schadenersatz",
      "§11 Schlussbestimmungen"
    ],
    d.required_project_config_fields = [
      "company_name", "address", "responsible_name",
      "responsible_title", "contact_email"
    ];

MERGE (d:DocumentType {type: "SCC"})
ON CREATE SET d.name_de = "Standardvertragsklauseln (EU-US)",
              d.required_for = "Datentransfer in Drittländer ohne Angemessenheitsbeschluss",
              d.path_template = "/legal/drafts/scc_{service}.md"
SET d.jurisdictions = ["EU"];

MERGE (d:DocumentType {type: "TOM"})
SET d.name_de = "Technisch-organisatorische Maßnahmen",
    d.legal_basis = "DSGVO Art. 32",
    d.required_for = "Nachweis angemessener Sicherheit gem. DSGVO Art. 32",
    d.path_template = "/legal/drafts/tom_{run_id}.md",
    d.jurisdictions = ["EU"],
    d.required_sections = [
      "1.1 Zutrittskontrolle",
      "1.2 Zugangskontrolle",
      "1.3 Zugriffskontrolle",
      "1.4 Trennungskontrolle",
      "1.5 Pseudonymisierung",
      "2.1 Weitergabekontrolle",
      "2.2 Eingangskontrolle",
      "3.1 Verfügbarkeitskontrolle",
      "4.1 Datenschutz-Maßnahmen",
      "4.2 Incident-Response-Management",
      "4.3 Privacy by Design/Default",
      "4.4 Auftragskontrolle"
    ],
    d.required_project_config_fields = [
      "company_name", "responsible_name", "dpo_name", "dpo_email"
    ];

MERGE (d:DocumentType {type: "Datenschutzerklaerung"})
ON CREATE SET d.name_de = "Datenschutzerklärung",
              d.required_for = "Informationspflicht gegenüber Betroffenen",
              d.path_template = "/legal/datenschutz.md"
SET d.jurisdictions = ["EU"];

MERGE (d:DocumentType {type: "AI_Act_Manifest"})
SET d.name_de = "EU AI Act Risiko-Manifest",
    d.legal_basis = "EU AI Act Art. 6, 50",
    d.required_for = "Transparenzpflicht für KI-Systeme gem. EU AI Act",
    d.path_template = "/legal/drafts/ai_act_manifest_{run_id}.md",
    d.jurisdictions = ["EU"],
    d.required_sections = [
      "1. Rollen- und Verantwortlichkeitsklärung",
      "2. Eingesetzte KI-Systeme (Provider-Perspektive)",
      "3. Deployer-Risiko und Anwendungsfall",
      "4. Governance- und Kontrollmechanismen",
      "5. AI Literacy — Schulungsmaßnahmen"
    ],
    d.required_project_config_fields = [
      "responsible_name", "responsible_title", "dpo_name", "dpo_email"
    ];

MERGE (d:DocumentType {type: "VVT"})
SET d.name_de = "Verzeichnis von Verarbeitungstätigkeiten",
    d.legal_basis = "DSGVO Art. 30",
    d.required_for = "Dokumentationspflicht gem. DSGVO Art. 30",
    d.path_template = "/legal/drafts/vvt_{run_id}.md",
    d.jurisdictions = ["EU"],
    d.required_sections = [
      "Verantwortlicher",
      "Verarbeitungszweck",
      "Rechtsgrundlage",
      "Betroffene Personen",
      "Datenkategorien",
      "Empfänger",
      "Drittlandtransfer",
      "Löschfristen",
      "Technische Maßnahmen",
      "Auftragsverarbeiter"
    ],
    d.required_project_config_fields = [
      "company_name", "address", "responsible_name", "contact_email"
    ];

MERGE (d:DocumentType {type: "DSFA"})
SET d.name_de = "Datenschutz-Folgenabschätzung",
    d.legal_basis = "DSGVO Art. 35",
    d.required_for = "Hochrisiko-Verarbeitungen, insb. KI mit PII",
    d.path_template = "/legal/drafts/dsfa_{run_id}.md",
    d.jurisdictions = ["EU"],
    d.required_sections = [
      "Beschreibung der Verarbeitung",
      "Notwendigkeit und Verhältnismäßigkeit",
      "Risikobewertung",
      "Maßnahmen zur Risikobehandlung",
      "Konsultation Datenschutzbeauftragter"
    ],
    d.required_project_config_fields = [
      "company_name", "responsible_name", "dpo_name", "dpo_email"
    ];

MERGE (d:DocumentType {type: "KI_Policy"})
SET d.name_de = "KI-Nutzungsrichtlinie",
    d.legal_basis = "EU AI Act Art. 4, 26",
    d.required_for = "Deployer-Pflicht: KI-Kompetenz + interne Governance",
    d.path_template = "/legal/drafts/ki_policy_{run_id}.md",
    d.jurisdictions = ["EU"],
    d.required_sections = [
      "Geltungsbereich und Zweck",
      "Erlaubte und verbotene KI-Nutzung",
      "Freigabeprozess für neue KI-Systeme",
      "Pflichten der Mitarbeitenden",
      "Datenschutz im KI-Kontext"
    ],
    d.required_project_config_fields = [
      "company_name", "responsible_name"
    ];

MERGE (d:DocumentType {type: "KI_System_Dokumentation"})
SET d.name_de = "KI-System-Dokumentation",
    d.legal_basis = "EU AI Act Art. 13, 16, 53",
    d.required_for = "Transparenz + technische Dokumentation für KI-Systeme",
    d.path_template = "/legal/drafts/ki_system_{service}_{run_id}.md",
    d.jurisdictions = ["EU"],
    d.required_sections = [
      "System-Beschreibung und Zweck",
      "Risikostufe (EU AI Act)",
      "Technische Spezifikation",
      "Datengrundlage",
      "Menschliche Aufsicht"
    ],
    d.required_project_config_fields = [
      "company_name", "responsible_name", "ai_usecase_type"
    ];

MERGE (d:DocumentType {type: "Cookie_Consent"})
ON CREATE SET d.name_de = "Cookie-Einwilligung / Consent Banner",
              d.required_for = "Nicht-notwendige Cookies gem. TTDSG § 25",
              d.path_template = "/legal/drafts/cookie_check.md"
SET d.jurisdictions = ["EU"];

MERGE (d:DocumentType {type: "Audit_Report"})
ON CREATE SET d.name_de = "Compliance Audit Report",
              d.required_for = "Interner Nachweis der Compliance-Prüfung",
              d.path_template = "/legal/audit_report.md"
SET d.jurisdictions = ["global"];


// ============================================================
// DocumentType → Law BASED_ON Relationships (EU-level only)
// ============================================================

MATCH (d:DocumentType {type: "AVV"}), (l:Law {name: "DSGVO", article: "28"})
MERGE (d)-[:BASED_ON]->(l);

MATCH (d:DocumentType {type: "SCC"}), (l:Law {name: "DSGVO", article: "46"})
MERGE (d)-[:BASED_ON]->(l);

MATCH (d:DocumentType {type: "TOM"}), (l:Law {name: "DSGVO", article: "32"})
MERGE (d)-[:BASED_ON]->(l);

MATCH (d:DocumentType {type: "Datenschutzerklaerung"}), (l:Law {name: "DSGVO", article: "13"})
MERGE (d)-[:BASED_ON]->(l);
MATCH (d:DocumentType {type: "Datenschutzerklaerung"}), (l:Law {name: "DSGVO", article: "14"})
MERGE (d)-[:BASED_ON]->(l);

MATCH (d:DocumentType {type: "VVT"}), (l:Law {name: "DSGVO", article: "30"})
MERGE (d)-[:BASED_ON]->(l);

MATCH (d:DocumentType {type: "AI_Act_Manifest"}), (l:Law {name: "EU AI Act", article: "50"})
MERGE (d)-[:BASED_ON]->(l);

MATCH (d:DocumentType {type: "AI_Act_Manifest"}), (l:Law {name: "EU AI Act", article: "6"})
MERGE (d)-[:BASED_ON]->(l);


// ============================================================
// Country → TransferMechanism Relationships
// ============================================================

MATCH (c:Country {requires_sccs: true}), (t:TransferMechanism {name: "SCCs"})
MERGE (c)-[:REQUIRES_MECHANISM]->(t);

MATCH (c:Country {gdpr_adequate: true}), (t:TransferMechanism {name: "Angemessenheitsbeschluss"})
WHERE c.name IN ["UK", "Canada"]
MERGE (c)-[:COVERED_BY]->(t);


// ============================================================
// NIS2 → DocumentType REQUIRES Relationships
// ============================================================

MATCH (l:Law {name: "NIS2", article: "21"}),
      (d:DocumentType {type: "TOM"})
MERGE (l)-[:REQUIRES]->(d);

MATCH (l:Law {name: "NIS2", article: "23"}),
      (d:DocumentType {type: "Audit_Report"})
MERGE (l)-[:REQUIRES]->(d);

// ============================================================
// BLOCK Q — EU AI ACT USE CASE NODES (DEPLOYER PERSPECTIVE)
// Source: EU AI Act (EU) 2024/1689
// Deployer risk classification — NOT provider/model risk
// Limited risk: Art. 50 (finale Nummerierung, aus euaiact.pdf verifiziert)
// High risk: Art. 6 + Annex III (aus euaiact.pdf verifiziert, confidence 1.0)
// ============================================================

// --- Limited Risk (Art. 50 — Transparency obligations, finale Verordnung) ---
MERGE (u:UseCase {type: "customer_service_chatbot"})
SET u.title_de          = "Kundenservice-Chatbot / FAQ-Bot",
    u.risk_level        = "Limited",
    u.eu_ai_act_article = "50",
    u.reason            = "Transparenzpflicht: Nutzer müssen informiert werden, dass sie mit einem KI-System interagieren",
    u.deployer_action   = "Hinweis 'Sie sprechen mit einer KI' vor oder bei Gesprächsbeginn anzeigen",
    u.confidence        = 1.0,
    u.source            = "EU AI Act (EU) 2024/1689, Art. 50 Abs. 1",
    u.note_unverified   = null;

MERGE (u:UseCase {type: "ai_content_generator"})
SET u.title_de          = "KI-generierte Inhalte (Text, Bild, Audio, Video)",
    u.risk_level        = "Limited",
    u.eu_ai_act_article = "50",
    u.reason            = "Deepfake-Kennzeichnungspflicht: synthetische Inhalte müssen als KI-generiert markiert werden",
    u.deployer_action   = "Maschinenlesbare Markierung + sichtbarer Hinweis auf KI-Generierung",
    u.confidence        = 1.0,
    u.source            = "EU AI Act (EU) 2024/1689, Art. 50 Abs. 2",
    u.note_unverified   = null;

MERGE (u:UseCase {type: "ai_assistant_general"})
SET u.title_de          = "Allgemeiner KI-Assistent",
    u.risk_level        = "Limited",
    u.eu_ai_act_article = "50",
    u.reason            = "Transparenzpflicht bei KI-Interaktion",
    u.deployer_action   = "Nutzer informieren dass sie mit KI interagieren",
    u.confidence        = 1.0,
    u.source            = "EU AI Act (EU) 2024/1689, Art. 50 Abs. 1",
    u.note_unverified   = null;

// Re-classified 2026-07-19 (legal review): Annex III No. 1(c) high risk;
// prohibited in workplace/education contexts (Art. 5(1)(f)); Art. 50(3)
// transparency applies IN ADDITION, it does not replace the risk class.
MERGE (u:UseCase {type: "emotion_recognition_system"})
SET u.title_de          = "Emotionserkennungssystem",
    u.risk_level        = "High",
    u.eu_ai_act_article = "6",
    u.annex_iii_nr      = "1c",
    u.reason            = "Anhang III Nr. 1 lit. c: Emotionserkennung — Hochrisiko; am Arbeitsplatz und in Bildungseinrichtungen verboten (Art. 5 Abs. 1 lit. f); zusätzlich Transparenzpflicht nach Art. 50 Abs. 3",
    u.deployer_action   = "Einsatzkontext prüfen: Arbeitsplatz/Bildung = verboten (Art. 5 Abs. 1 lit. f); sonst Hochrisiko-Pflichten (Art. 26) und Betroffene nach Art. 50 Abs. 3 informieren",
    u.confidence        = 1.0,
    u.source            = "EU AI Act (EU) 2024/1689, Art. 5 Abs. 1 lit. f, Art. 6 i.V.m. Anhang III Nr. 1 lit. c, Art. 50 Abs. 3",
    u.note_unverified   = null;

// --- High Risk (Art. 6 + Annex III — confirmed from official PDF) ---
MERGE (u:UseCase {type: "hr_recruitment_screening"})
SET u.title_de          = "KI-gestütztes Bewerbungsscreening und Personalauswahl",
    u.risk_level        = "High",
    u.eu_ai_act_article = "6",
    u.annex_iii_nr      = "4",
    u.reason            = "Anhang III Nr. 4: Beschäftigung, Personalmanagement und Zugang zur Selbstständigkeit",
    u.deployer_action   = "Konformitätsbewertung, Registrierung EU-Datenbank, menschliche Aufsicht, technische Dokumentation",
    u.confidence        = 1.0,
    u.source            = "EU AI Act (EU) 2024/1689, Art. 6 i.V.m. Anhang III Nr. 4";

MERGE (u:UseCase {type: "hr_performance_evaluation"})
SET u.title_de          = "KI-gestützte Leistungsbewertung und Mitarbeiterüberwachung",
    u.risk_level        = "High",
    u.eu_ai_act_article = "6",
    u.annex_iii_nr      = "4",
    u.reason            = "Anhang III Nr. 4: Überwachung und Bewertung von Beschäftigten",
    u.deployer_action   = "Konformitätsbewertung, menschliche Aufsicht, Grundrechte-Folgenabschätzung",
    u.confidence        = 1.0,
    u.source            = "EU AI Act (EU) 2024/1689, Art. 6 i.V.m. Anhang III Nr. 4";

MERGE (u:UseCase {type: "credit_scoring"})
SET u.title_de          = "Kreditwürdigkeitsprüfung und Kreditscoring",
    u.risk_level        = "High",
    u.eu_ai_act_article = "6",
    u.annex_iii_nr      = "5",
    u.reason            = "Anhang III Nr. 5: Zugang zu wesentlichen privaten und öffentlichen Dienstleistungen",
    u.deployer_action   = "Konformitätsbewertung, Registrierung EU-Datenbank, Erklärbarkeit der Entscheidung",
    u.confidence        = 1.0,
    u.source            = "EU AI Act (EU) 2024/1689, Art. 6 i.V.m. Anhang III Nr. 5";

MERGE (u:UseCase {type: "education_assessment"})
SET u.title_de          = "KI-gestützte Bildungs- und Prüfungsbewertung",
    u.risk_level        = "High",
    u.eu_ai_act_article = "6",
    u.annex_iii_nr      = "3",
    u.reason            = "Anhang III Nr. 3: Bildung und Berufsausbildung",
    u.deployer_action   = "Konformitätsbewertung, menschliche Aufsicht, Transparenz gegenüber Betroffenen",
    u.confidence        = 1.0,
    u.source            = "EU AI Act (EU) 2024/1689, Art. 6 i.V.m. Anhang III Nr. 3";

MERGE (u:UseCase {type: "biometric_categorization"})
SET u.title_de          = "Biometrische Kategorisierung und Identifikation",
    u.risk_level        = "High",
    u.eu_ai_act_article = "6",
    u.annex_iii_nr      = "1",
    u.reason            = "Anhang III Nr. 1: Biometrie",
    u.deployer_action   = "Konformitätsbewertung, strenge Datenschutzprüfung, ggf. DSFA erforderlich",
    u.confidence        = 1.0,
    u.source            = "EU AI Act (EU) 2024/1689, Art. 6 i.V.m. Anhang III Nr. 1";

MERGE (u:UseCase {type: "healthcare_decision"})
SET u.title_de          = "KI-gestützte medizinische Diagnose und Behandlungsentscheidung",
    u.risk_level        = "High",
    u.eu_ai_act_article = "6",
    u.annex_iii_nr      = "2",
    u.reason            = "Anhang III Nr. 2: Sicherheitskomponenten und Medizinprodukte",
    u.deployer_action   = "Konformitätsbewertung, klinische Bewertung, DSFA erforderlich, menschliche Aufsicht durch medizinisches Fachpersonal",
    u.confidence        = 1.0,
    u.source            = "EU AI Act (EU) 2024/1689, Art. 6 i.V.m. Anhang III Nr. 2";

MERGE (u:UseCase {type: "critical_infrastructure_mgmt"})
SET u.title_de          = "KI im Betrieb kritischer Infrastrukturen",
    u.risk_level        = "High",
    u.eu_ai_act_article = "6",
    u.annex_iii_nr      = "2",
    u.reason            = "Anhang III Nr. 2: Kritische Infrastruktur (Energie, Wasser, Verkehr)",
    u.deployer_action   = "Konformitätsbewertung, Sicherheitsanalyse, Notfallplan, Registrierung EU-Datenbank",
    u.confidence        = 1.0,
    u.source            = "EU AI Act (EU) 2024/1689, Art. 6 i.V.m. Anhang III Nr. 2";

MERGE (u:UseCase {type: "law_enforcement_ai"})
SET u.title_de          = "KI für strafverfolgungsbehördliche Zwecke",
    u.risk_level        = "High",
    u.eu_ai_act_article = "6",
    u.annex_iii_nr      = "6",
    u.reason            = "Anhang III Nr. 6: Strafverfolgung",
    u.deployer_action   = "Strenge Konformitätsbewertung, Grundrechte-Folgenabschätzung, Genehmigung Aufsichtsbehörde erforderlich",
    u.confidence        = 1.0,
    u.source            = "EU AI Act (EU) 2024/1689, Art. 6 i.V.m. Anhang III Nr. 6";

// --- Minimal Risk (Erwägungsgrund 47) ---
MERGE (u:UseCase {type: "spam_filter"})
SET u.title_de          = "Spam- und Content-Filter",
    u.risk_level        = "Minimal",
    u.eu_ai_act_article = "null",
    u.reason            = "Kein regulatorischer Anwendungsfall — minimales Risiko",
    u.deployer_action   = "Keine Pflichten. Freiwilliger Verhaltenskodex empfohlen.",
    u.confidence        = 1.0,
    u.source            = "EU AI Act (EU) 2024/1689, Erwägungsgrund 47";

MERGE (u:UseCase {type: "recommendation_engine"})
SET u.title_de          = "Empfehlungssystem (Produkte, Inhalte)",
    u.risk_level        = "Minimal",
    u.eu_ai_act_article = "null",
    u.reason            = "Kein regulatorischer Anwendungsfall sofern keine Hochrisiko-Kriterien erfüllt",
    u.deployer_action   = "Keine Pflichten. Transparenz gegenüber Nutzern empfohlen.",
    u.confidence        = 1.0,
    u.source            = "EU AI Act (EU) 2024/1689, Erwägungsgrund 47";

MERGE (u:UseCase {type: "ai_autonomous_agent"})
SET u.title_de          = "Autonomer KI-Agent",
    u.risk_level        = "Limited",
    u.eu_ai_act_article = "50",
    u.reason            = "Transparenzpflicht: Nutzer müssen informiert werden, dass sie mit einem autonomen KI-System interagieren",
    u.deployer_action   = "Nutzer informieren dass sie mit einem autonomen KI-Agenten interagieren. Menschliche Aufsicht für kritische Aktionen sicherstellen.",
    u.confidence        = 1.0,
    u.source            = "EU AI Act (EU) 2024/1689, Art. 50 Abs. 1",
    u.jurisdictions     = ["EU"];

// --- Relationships ---
MATCH (u:UseCase {risk_level: "Limited"}), (r:RiskLevel {level: "Limited"})
MERGE (u)-[:CLASSIFIED_BY]->(r);

MATCH (u:UseCase {risk_level: "High"}), (r:RiskLevel {level: "High"})
MERGE (u)-[:CLASSIFIED_BY]->(r);

MATCH (u:UseCase {risk_level: "Minimal"}), (r:RiskLevel {level: "Minimal"})
MERGE (u)-[:CLASSIFIED_BY]->(r);

// Emotion recognition was mis-classified Limited until 2026-07-19 — remove the
// stale Limited edge a re-seed would otherwise resurrect next to the High edge.
MATCH (u:UseCase {type: "emotion_recognition_system"})-[e:CLASSIFIED_BY]->(:RiskLevel {level: "Limited"})
DELETE e;

// Remove stale REQUIRES_COMPLIANCE → Art. 52 for Limited UseCases (draft-era artifact)
MATCH (u:UseCase)-[r:REQUIRES_COMPLIANCE]->(l:Law {name: "EU AI Act", article: "52"})
WHERE u.risk_level = "Limited"
DELETE r;

MATCH (u:UseCase), (l:Law {name: "EU AI Act", article: "50"})
WHERE u.eu_ai_act_article = "50"
MERGE (u)-[:REQUIRES_COMPLIANCE]->(l);

MATCH (u:UseCase), (l:Law {name: "EU AI Act", article: "6"})
WHERE u.eu_ai_act_article = "6"
MERGE (u)-[:REQUIRES_COMPLIANCE]->(l);

MATCH (u:UseCase {risk_level: "High"}), (d:DocumentType {type: "AI_Act_Manifest"})
MERGE (u)-[:REQUIRES]->(d);

MATCH (u:UseCase {risk_level: "Limited"}), (d:DocumentType {type: "AI_Act_Manifest"})
MERGE (u)-[:REQUIRES]->(d);

MATCH (s:Service {category: "ai_llm"}), (u:UseCase {type: "customer_service_chatbot"})
MERGE (s)-[:CAN_INDICATE]->(u);

MATCH (s:Service {category: "ai_llm"}), (u:UseCase {type: "ai_assistant_general"})
MERGE (s)-[:CAN_INDICATE]->(u);

MATCH (s:Service {category: "ai_llm"}), (u:UseCase {type: "ai_content_generator"})
MERGE (s)-[:CAN_INDICATE]->(u);

// ============================================================
// JURISDICTION NORMALIZATION — EU-layer nodes
// ============================================================

MATCH (u:UseCase)
SET u.jurisdictions = ["EU"];

MATCH (r:Requirement {framework: "CRA"})
SET r.jurisdictions = ["EU"];

// ============================================================
// GQ-005 — Annex III Nr. 7+8 + Art. 5 Unacceptable Risk
// ============================================================

// Ensure Unacceptable RiskLevel node exists
MERGE (r:RiskLevel {level: "Unacceptable"})
SET r.eu_ai_act_article = "5",
    r.description       = "Prohibited AI practices under Art. 5 EU AI Act",
    r.updated_at        = datetime();

// ── Annex III Nr. 7 — Migration / Asylum / Border Control ───────
MERGE (uc1:UseCase {type: "migration_border_control"})
ON CREATE SET uc1.created_at = datetime()
SET uc1.title_de           = "KI-gestützte Migrationskontrolle und Asylverfahren",
    uc1.risk_level         = "High",
    uc1.eu_ai_act_article  = "6",
    uc1.annex_iii_nr       = "7",
    uc1.reason             = "Anhang III Nr. 7: Migration, Asyl und Grenzschutzmanagement",
    uc1.source             = "EU AI Act, Annex III, Nr. 7",
    uc1.confidence         = 1.0,
    uc1.jurisdictions      = ["EU"],
    uc1.deployer_action    = "Konformitätsbewertung + EU-Datenbankregistrierung erforderlich",
    uc1.scout_signals      = ["asylum", "migration", "border", "visa", "refugee",
                              "asyl", "grenze", "einreise", "aufenthalt"],
    uc1.deployer_checklist = [
        "Technische Dokumentation gem. Art. 11 EU AI Act",
        "Konformitätsbewertung gem. Art. 43 EU AI Act",
        "Registrierung EU-Datenbank gem. Art. 49 EU AI Act",
        "Grundrechte-Folgenabschätzung gem. Art. 27 EU AI Act",
        "Menschliche Aufsicht sicherstellen gem. Art. 26 EU AI Act",
        "DSFA gem. DSGVO Art. 35 (besondere Kategorien personenbezogener Daten)"
    ],
    uc1.last_verified      = "2026-04-18",
    uc1.updated_at         = datetime(),
    uc1.updated_by         = "seed_gq005";

// ── Annex III Nr. 8 — Justice / Democratic Processes ────────────
MERGE (uc2:UseCase {type: "justice_democratic_process"})
ON CREATE SET uc2.created_at = datetime()
SET uc2.title_de           = "KI in der Rechtspflege und demokratischen Entscheidungsfindung",
    uc2.risk_level         = "High",
    uc2.eu_ai_act_article  = "6",
    uc2.annex_iii_nr       = "8",
    uc2.reason             = "Anhang III Nr. 8: Rechtspflege und demokratische Prozesse",
    uc2.source             = "EU AI Act, Annex III, Nr. 8",
    uc2.confidence         = 1.0,
    uc2.jurisdictions      = ["EU"],
    uc2.deployer_action    = "Konformitätsbewertung + EU-Datenbankregistrierung erforderlich",
    uc2.scout_signals      = ["verdict", "sentencing", "judicial", "court", "election",
                              "urteil", "gericht", "richter", "wahl", "abstimmung",
                              "legal_decision", "case_outcome"],
    uc2.deployer_checklist = [
        "Technische Dokumentation gem. Art. 11 EU AI Act",
        "Konformitätsbewertung gem. Art. 43 EU AI Act",
        "Registrierung EU-Datenbank gem. Art. 49 EU AI Act",
        "Grundrechte-Folgenabschätzung gem. Art. 27 EU AI Act",
        "Menschliche Aufsicht sicherstellen gem. Art. 26 EU AI Act",
        "Unabhängige Überprüfung durch qualifiziertes Personal sicherstellen"
    ],
    uc2.last_verified      = "2026-04-18",
    uc2.updated_at         = datetime(),
    uc2.updated_by         = "seed_gq005";

// ── Art. 5(1)(c) — Social Scoring by Public Authorities ─────────
MERGE (uc3:UseCase {type: "social_scoring_public"})
ON CREATE SET uc3.created_at = datetime()
SET uc3.title_de           = "Social Scoring durch öffentliche Stellen",
    uc3.risk_level         = "Unacceptable",
    uc3.eu_ai_act_article  = "5",
    uc3.annex_iii_nr       = null,
    uc3.reason             = "Art. 5 Abs. 1 lit. c: Bewertung natürlicher Personen durch öffentliche Stellen — VERBOTEN",
    uc3.source             = "EU AI Act, Art. 5(1)(c)",
    uc3.confidence         = 1.0,
    uc3.jurisdictions      = ["EU"],
    uc3.deployer_action    = "VERBOTEN — Einsatz nicht zulässig",
    uc3.scout_signals      = ["social_score", "citizen_score", "trustworthiness_rating",
                              "behavior_score", "sozialkredit"],
    uc3.last_verified      = "2026-04-18",
    uc3.updated_at         = datetime(),
    uc3.updated_by         = "seed_gq005";

// ── Art. 5(1)(a) — Subliminal Manipulation ──────────────────────
MERGE (uc4:UseCase {type: "subliminal_manipulation"})
ON CREATE SET uc4.created_at = datetime()
SET uc4.title_de           = "Unterschwellige Manipulation von Personen",
    uc4.risk_level         = "Unacceptable",
    uc4.eu_ai_act_article  = "5",
    uc4.annex_iii_nr       = null,
    uc4.reason             = "Art. 5 Abs. 1 lit. a: Manipulation außerhalb des Bewusstseins — VERBOTEN",
    uc4.source             = "EU AI Act, Art. 5(1)(a)",
    uc4.confidence         = 1.0,
    uc4.jurisdictions      = ["EU"],
    uc4.deployer_action    = "VERBOTEN — Einsatz nicht zulässig",
    uc4.scout_signals      = ["subliminal", "subconscious", "covert_influence",
                              "dark_pattern", "manipulation_signal"],
    uc4.last_verified      = "2026-04-18",
    uc4.updated_at         = datetime(),
    uc4.updated_by         = "seed_gq005";

// ── Art. 5(1)(d) — Real-Time Remote Biometric Identification ────
MERGE (uc5:UseCase {type: "realtime_remote_biometric_id"})
ON CREATE SET uc5.created_at = datetime()
SET uc5.title_de           = "Echtzeit-Fernidentifikation biometrischer Merkmale im öffentlichen Raum",
    uc5.risk_level         = "Unacceptable",
    uc5.eu_ai_act_article  = "5",
    uc5.annex_iii_nr       = null,
    uc5.reason             = "Art. 5 Abs. 1 lit. d: Echtzeit-biometrische Fernidentifikation im öffentlichen Raum — grundsätzlich VERBOTEN (Ausnahmen Art. 5 Abs. 2)",
    uc5.source             = "EU AI Act, Art. 5(1)(d)",
    uc5.confidence         = 1.0,
    uc5.jurisdictions      = ["EU"],
    uc5.deployer_action    = "VERBOTEN (Ausnahmen nur für Strafverfolgung gem. Art. 5 Abs. 2)",
    uc5.scout_signals      = ["facial_recognition", "live_surveillance", "cctv_ai",
                              "biometric_identification", "gesichtserkennung",
                              "crowd_surveillance", "public_space_biometric"],
    uc5.last_verified      = "2026-04-18",
    uc5.updated_at         = datetime(),
    uc5.updated_by         = "seed_gq005";

// ── Edges: CLASSIFIED_BY ─────────────────────────────────────────
MATCH (uc:UseCase) WHERE uc.type IN ["migration_border_control", "justice_democratic_process"]
MATCH (rl:RiskLevel {level: "High"})
MERGE (uc)-[:CLASSIFIED_BY]->(rl);

MATCH (uc:UseCase) WHERE uc.type IN [
    "social_scoring_public", "subliminal_manipulation", "realtime_remote_biometric_id"
]
MATCH (rl:RiskLevel {level: "Unacceptable"})
MERGE (uc)-[:CLASSIFIED_BY]->(rl);

// ── Edges: REQUIRES_COMPLIANCE ───────────────────────────────────
MATCH (uc:UseCase) WHERE uc.type IN ["migration_border_control", "justice_democratic_process"]
MATCH (law:Law {name: "EU AI Act", article: "6"})
MERGE (uc)-[:REQUIRES_COMPLIANCE]->(law);

MATCH (uc:UseCase) WHERE uc.type IN [
    "social_scoring_public", "subliminal_manipulation", "realtime_remote_biometric_id"
]
MATCH (law:Law {name: "EU AI Act", article: "5"})
MERGE (uc)-[:REQUIRES_COMPLIANCE]->(law);

// ── Edges: REQUIRES DocumentType ────────────────────────────────
MATCH (uc:UseCase) WHERE uc.type IN ["migration_border_control", "justice_democratic_process"]
MATCH (d:DocumentType {type: "AI_Act_Manifest"})
MERGE (uc)-[:REQUIRES]->(d);
