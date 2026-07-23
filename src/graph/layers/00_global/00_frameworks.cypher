// ============================================================
// LEX-ORCHESTRA — Layer 00: Global Frameworks
// Applies to: all deployments worldwide
// jurisdictions: ["global"]
// Sources: OWASP (official PDFs), NIST CSWP 29, BSI Edition 2023
// ISO 27001 moved to byos/iso27001.cypher (ADR-120 BYOS, ADR-130 D2)
// Idempotent: MERGE-only, safe to re-run
// ============================================================

// ============================================================
// BLOCK F — OWASP CONTROLS (Web Top 10 + LLM Top 10)
// ============================================================

// OWASP Web Top 10 (2021)
MERGE (c:Control {framework: "OWASP_Top10", id: "A01"})
ON CREATE SET c.title = "Broken Access Control",
              c.severity = "critical", c.dsgvo_article = "32";

MERGE (c:Control {framework: "OWASP_Top10", id: "A02"})
ON CREATE SET c.title = "Cryptographic Failures",
              c.severity = "critical", c.dsgvo_article = "32";

MERGE (c:Control {framework: "OWASP_Top10", id: "A03"})
ON CREATE SET c.title = "Injection (SQL, XSS, Command)",
              c.severity = "critical", c.dsgvo_article = "32";

MERGE (c:Control {framework: "OWASP_Top10", id: "A05"})
ON CREATE SET c.title = "Security Misconfiguration",
              c.severity = "high", c.dsgvo_article = "32";

MERGE (c:Control {framework: "OWASP_Top10", id: "A07"})
ON CREATE SET c.title = "Identification and Authentication Failures",
              c.severity = "high", c.dsgvo_article = "32";

MERGE (c:Control {framework: "OWASP_Top10", id: "A09"})
ON CREATE SET c.title = "Security Logging and Monitoring Failures",
              c.severity = "medium", c.dsgvo_article = "30";

// OWASP Top 10 for LLM Applications (v1.1)
MERGE (c:Control {framework: "OWASP_LLM_Top10", id: "LLM01"})
ON CREATE SET c.title = "Prompt Injection",
              c.severity = "critical", c.dsgvo_article = "32", c.eu_ai_act = "Art. 6";

MERGE (c:Control {framework: "OWASP_LLM_Top10", id: "LLM02"})
ON CREATE SET c.title = "Insecure Output Handling",
              c.severity = "high", c.dsgvo_article = "32";

MERGE (c:Control {framework: "OWASP_LLM_Top10", id: "LLM06"})
ON CREATE SET c.title = "Sensitive Information Disclosure",
              c.severity = "critical", c.dsgvo_article = "32";

MERGE (c:Control {framework: "OWASP_LLM_Top10", id: "LLM08"})
ON CREATE SET c.title = "Excessive Agency",
              c.severity = "high", c.dsgvo_article = "25", c.eu_ai_act = "Art. 14";

MERGE (c:Control {framework: "OWASP_LLM_Top10", id: "LLM09"})
ON CREATE SET c.title = "Overreliance",
              c.severity = "medium", c.eu_ai_act = "Art. 14";

// OWASP Controls → Laws
MATCH (c:Control {framework: "OWASP_Top10"}), (l:Law {name: "DSGVO", article: "32"})
WHERE c.dsgvo_article = "32"
MERGE (c)-[:IMPLEMENTS]->(l);

MATCH (c:Control {framework: "OWASP_Top10", id: "A09"}), (l:Law {name: "DSGVO", article: "30"})
MERGE (c)-[:IMPLEMENTS]->(l);

MATCH (c:Control {framework: "OWASP_LLM_Top10"}), (l:Law {name: "DSGVO", article: "32"})
WHERE c.dsgvo_article = "32"
MERGE (c)-[:IMPLEMENTS]->(l);

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM08"}), (l:Law {name: "DSGVO", article: "25"})
MERGE (c)-[:IMPLEMENTS]->(l);

MATCH (c:Control {framework: "OWASP_LLM_Top10"}), (l:Law {name: "EU AI Act", article: "6"})
WHERE c.eu_ai_act = "Art. 6"
MERGE (c)-[:IMPLEMENTS]->(l);

// AI Services → LLM Controls (müssen LLM Top 10 beachten)
MATCH (s:Service {ai_act_relevant: true}), (c:Control {framework: "OWASP_LLM_Top10"})
MERGE (s)-[:REQUIRES_CONTROL]->(c);


// ============================================================
// BLOCK G — moved out (ADR-130 D2): ISO 27001 is BYOS (ADR-120).
// Content lives in the licensed BYOS ISO copy (layers/byos/, not shipped
// in the public repo) — NEVER part of the default seed manifest.
// ============================================================


// ============================================================
// BLOCK H — BSI IT-GRUNDSCHUTZ KERN-BAUSTEINE
// Source: IT-Grundschutz Kompendium Edition 2023 (BSI)
// BASIS requirements extracted from official PDF
// ============================================================

// ORP.1 — Organisation
MERGE (c:Control {framework: "BSI_Grundschutz", id: "ORP.1"})
ON CREATE SET c.title = "Organisation", c.severity = "high"
SET c.description        = "Grundlegende organisatorische Regelungen für Informationssicherheit. Festlegung von Verantwortlichkeiten, Zuständigkeiten und Prozessen als Basis des Sicherheitsmanagements.",
    c.basis_requirements = [
      "ORP.1.A1 Festlegung von Verantwortlichkeiten und Regelungen",
      "ORP.1.A2 Zuweisung der Zuständigkeiten",
      "ORP.1.A3 Beaufsichtigung oder Begleitung von Fremdpersonen",
      "ORP.1.A4 Funktionstrennung zwischen unvereinbaren Aufgaben"
    ],
    c.source = "BSI IT-Grundschutz-Kompendium Edition 2023";

// OPS.1.1.2 — Ordnungsgemäße IT-Administration (official Baustein ID; no standalone OPS.1.1 exists — ADR-126 Phase 3b)
MERGE (c:Control {framework: "BSI_Grundschutz", id: "OPS.1.1.2"})
ON CREATE SET c.title = "Ordnungsgemäße IT-Administration", c.severity = "high"
SET c.description        = "Sichere und geregelte Administration von IT-Systemen. Personalauswahl, Administrationskennungen und Schutz privilegierter Zugriffe.",
    c.basis_requirements = [
      "OPS.1.1.A1 Personalauswahl für administrative Tätigkeiten",
      "OPS.1.1.A2 Regelungen für IT-Administrationstätigkeiten",
      "OPS.1.1.A3 Geregelte Einweisung von IT-Administrationspersonal",
      "OPS.1.1.A5 Administrationskennungen",
      "OPS.1.1.A6 Schutz administrativer Kennungen"
    ],
    c.source = "BSI IT-Grundschutz-Kompendium Edition 2023";

// SYS.1.1 — Allgemeiner Server
MERGE (c:Control {framework: "BSI_Grundschutz", id: "SYS.1.1"})
ON CREATE SET c.title = "Allgemeiner Server", c.severity = "high"
SET c.description        = "Grundlegende Sicherheitsanforderungen für Server. Geeigneter Aufstellungsort, Benutzerauthentisierung, Rechtevergabe und Rollentrennung.",
    c.basis_requirements = [
      "SYS.1.1.A1 Geeigneter Aufstellungsort",
      "SYS.1.1.A2 Benutzerauthentisierung an Servern",
      "SYS.1.1.A3 Restriktive Rechtevergabe",
      "SYS.1.1.A4 Rollentrennung",
      "SYS.1.1.A6 Abschaltung nicht benötigter Dienste"
    ],
    c.source = "BSI IT-Grundschutz-Kompendium Edition 2023";

// NET.1.1 — Netzarchitektur und -design
MERGE (c:Control {framework: "BSI_Grundschutz", id: "NET.1.1"})
ON CREATE SET c.title = "Netzarchitektur und -design", c.severity = "high"
SET c.description        = "Planung und Dokumentation sicherer Netzinfrastrukturen. Sicherheitsrichtlinie, Dokumentation, Anforderungsspezifikation und Netztrennung in Sicherheitszonen.",
    c.basis_requirements = [
      "NET.1.1.A1 Sicherheitsrichtlinie für das Netz",
      "NET.1.1.A2 Dokumentation des Netzes",
      "NET.1.1.A3 Anforderungsspezifikation für das Netz",
      "NET.1.1.A4 Netztrennung in Sicherheitszonen"
    ],
    c.source = "BSI IT-Grundschutz-Kompendium Edition 2023";

// CON.10 — Entwicklung von Webanwendungen
MERGE (c:Control {framework: "BSI_Grundschutz", id: "CON.10"})
ON CREATE SET c.title = "Entwicklung von Webanwendungen", c.severity = "high"
SET c.description        = "Sicherheitsanforderungen für die Entwicklung von Webanwendungen. Schulung, Authentisierung, Schutz vertraulicher Daten und kontrolliertes Einbinden von Inhalten.",
    c.basis_requirements = [
      "CON.10.A1 Schulung zu webanwendungsspezifischen Sicherheitsmechanismen",
      "CON.10.A2 Authentisierung bei Webanwendungen",
      "CON.10.A3 Schutz vertraulicher Daten",
      "CON.10.A4 Kontrolliertes Einbinden von Dateien und Inhalten bei Webanwendungen"
    ],
    c.source = "BSI IT-Grundschutz-Kompendium Edition 2023";

// CON.2 — enrich existing stub with PDF data
MERGE (c:Control {framework: "BSI_Grundschutz", id: "CON.2"})
ON CREATE SET c.title = "Datenschutz", c.severity = "critical"
SET c.description = "Schutz natürlicher Personen bei Datenverarbeitung. Umsetzung des Standard-Datenschutzmodells (SDM) gem. DSGVO-Anforderungen.",
    c.basis_requirements = ["CON.2.A1 Umsetzung Standard-Datenschutzmodell"],
    c.source = "BSI IT-Grundschutz-Kompendium Edition 2023";

// APP.3.1 — Webanwendungen und Webservices
MERGE (c:Control {framework: "BSI_Grundschutz", id: "APP.3.1"})
ON CREATE SET
  c.title = "Webanwendungen und Webservices",
  c.severity = "high",
  c.description = "Sichere Nutzung von Webanwendungen und Webservices über HTTP(S). Schützt Informationen durch Authentisierung, Eingabevalidierung und sichere Architektur.",
  c.basis_requirements = [
    "APP.3.1.A1 Authentisierung",
    "APP.3.1.A4 Kontrolliertes Einbinden von Dateien und Inhalten",
    "APP.3.1.A7 Schutz vor unerlaubter automatisierter Nutzung",
    "APP.3.1.A14 Schutz vertraulicher Daten"
  ],
  c.source = "BSI IT-Grundschutz-Kompendium Edition 2023";

MERGE (r:Requirement {id: "APP.3.1.A1", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Authentisierung", r.level = "BASIS";
MATCH (c:Control {id: "APP.3.1", framework: "BSI_Grundschutz"}), (r:Requirement {id: "APP.3.1.A1", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

MERGE (r:Requirement {id: "APP.3.1.A4", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Kontrolliertes Einbinden von Dateien und Inhalten", r.level = "BASIS";
MATCH (c:Control {id: "APP.3.1", framework: "BSI_Grundschutz"}), (r:Requirement {id: "APP.3.1.A4", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

MERGE (r:Requirement {id: "APP.3.1.A14", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Schutz vertraulicher Daten", r.level = "BASIS";
MATCH (c:Control {id: "APP.3.1", framework: "BSI_Grundschutz"}), (r:Requirement {id: "APP.3.1.A14", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

// APP.3.2 — Webserver
MERGE (c:Control {framework: "BSI_Grundschutz", id: "APP.3.2"})
ON CREATE SET
  c.title = "Webserver",
  c.severity = "high",
  c.description = "Sicherer Betrieb von Webservern. Sichere Konfiguration, TLS-Verschlüsselung, Zugriffsschutz und Protokollierung von Ereignissen.",
  c.basis_requirements = [
    "APP.3.2.A1 Sichere Konfiguration eines Webservers",
    "APP.3.2.A2 Schutz der Webserver-Dateien",
    "APP.3.2.A3 Absicherung von Datei-Uploads und -Downloads",
    "APP.3.2.A4 Protokollierung von Ereignissen",
    "APP.3.2.A5 Authentisierung",
    "APP.3.2.A7 Rechtliche Rahmenbedingungen für Webangebote",
    "APP.3.2.A11 Verschlüsselung über TLS"
  ],
  c.source = "BSI IT-Grundschutz-Kompendium Edition 2023";

MERGE (r:Requirement {id: "APP.3.2.A1", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Sichere Konfiguration eines Webservers", r.level = "BASIS";
MATCH (c:Control {id: "APP.3.2", framework: "BSI_Grundschutz"}), (r:Requirement {id: "APP.3.2.A1", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

MERGE (r:Requirement {id: "APP.3.2.A11", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Verschlüsselung über TLS", r.level = "BASIS";
MATCH (c:Control {id: "APP.3.2", framework: "BSI_Grundschutz"}), (r:Requirement {id: "APP.3.2.A11", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

// APP.6 — Allgemeine Software
MERGE (c:Control {framework: "BSI_Grundschutz", id: "APP.6"})
ON CREATE SET
  c.title = "Allgemeine Software",
  c.severity = "medium",
  c.description = "Sicherer Einsatz von Software — von der Planung über sichere Beschaffung bis zur Installation und Konfiguration jeglicher Softwaretypen.",
  c.basis_requirements = [
    "APP.6.A1 Planung des Software-Einsatzes",
    "APP.6.A2 Erstellung eines Anforderungskatalogs für Software",
    "APP.6.A3 Sichere Beschaffung von Software",
    "APP.6.A4 Regelung für die Installation und Konfiguration von Software",
    "APP.6.A5 Sichere Installation von Software"
  ],
  c.source = "BSI IT-Grundschutz-Kompendium Edition 2023";

// CON.1 — Kryptokonzept
MERGE (c:Control {framework: "BSI_Grundschutz", id: "CON.1"})
ON CREATE SET
  c.title = "Kryptokonzept",
  c.severity = "high",
  c.description = "Kryptografische Maßnahmen für Vertraulichkeit, Integrität und Authentizität. Auswahl geeigneter Verfahren und sicheres Schlüsselmanagement.",
  c.basis_requirements = [
    "CON.1.A1 Auswahl geeigneter kryptografischer Verfahren",
    "CON.1.A2 Datensicherung beim Einsatz kryptografischer Verfahren",
    "CON.1.A4 Geeignetes Schlüsselmanagement"
  ],
  c.source = "BSI IT-Grundschutz-Kompendium Edition 2023";

MERGE (r:Requirement {id: "CON.1.A1", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Auswahl geeigneter kryptografischer Verfahren", r.level = "BASIS";
MATCH (c:Control {id: "CON.1", framework: "BSI_Grundschutz"}), (r:Requirement {id: "CON.1.A1", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

MERGE (r:Requirement {id: "CON.1.A4", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Geeignetes Schlüsselmanagement", r.level = "BASIS";
MATCH (c:Control {id: "CON.1", framework: "BSI_Grundschutz"}), (r:Requirement {id: "CON.1.A4", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

// CON.3 — Datensicherungskonzept
MERGE (c:Control {framework: "BSI_Grundschutz", id: "CON.3"})
ON CREATE SET
  c.title = "Datensicherungskonzept",
  c.severity = "high",
  c.description = "Systematische Datensicherung zur Minimierung von Datenverlust. Einflussfaktoren erheben und Verfahrensweisen für Backups festlegen.",
  c.basis_requirements = [
    "CON.3.A1 Erhebung der Einflussfaktoren für Datensicherungen",
    "CON.3.A2 Festlegung der Verfahrensweisen für die Datensicherung"
  ],
  c.source = "BSI IT-Grundschutz-Kompendium Edition 2023";

MERGE (r:Requirement {id: "CON.3.A1", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Erhebung der Einflussfaktoren für Datensicherungen", r.level = "BASIS";
MATCH (c:Control {id: "CON.3", framework: "BSI_Grundschutz"}), (r:Requirement {id: "CON.3.A1", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

MERGE (r:Requirement {id: "CON.3.A2", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Festlegung der Verfahrensweisen für die Datensicherung", r.level = "BASIS";
MATCH (c:Control {id: "CON.3", framework: "BSI_Grundschutz"}), (r:Requirement {id: "CON.3.A2", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

// ORP.4 — Identitäts- und Berechtigungsmanagement
MERGE (c:Control {framework: "BSI_Grundschutz", id: "ORP.4"})
ON CREATE SET
  c.title = "Identitäts- und Berechtigungsmanagement",
  c.severity = "high",
  c.description = "Zugang zu Ressourcen auf berechtigte Personen einschränken. IAM-Prozesse, Passwortrichtlinien und Funktionstrennung.",
  c.basis_requirements = [
    "ORP.4.A1 Regelung für die Einrichtung und Löschung von Benutzenden",
    "ORP.4.A2 Einrichtung, Änderung und Entzug von Berechtigungen",
    "ORP.4.A4 Aufgabenverteilung und Funktionstrennung",
    "ORP.4.A7 Vergabe von Zugriffsrechten",
    "ORP.4.A8 Regelung des Passwortgebrauchs",
    "ORP.4.A9 Identifikation und Authentisierung",
    "ORP.4.A22 Regelung zur Passwortqualität"
  ],
  c.source = "BSI IT-Grundschutz-Kompendium Edition 2023";

MERGE (r:Requirement {id: "ORP.4.A2", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Einrichtung, Änderung und Entzug von Berechtigungen", r.level = "BASIS";
MATCH (c:Control {id: "ORP.4", framework: "BSI_Grundschutz"}), (r:Requirement {id: "ORP.4.A2", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

MERGE (r:Requirement {id: "ORP.4.A9", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Identifikation und Authentisierung", r.level = "BASIS";
MATCH (c:Control {id: "ORP.4", framework: "BSI_Grundschutz"}), (r:Requirement {id: "ORP.4.A9", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

// ISMS.1 — Sicherheitsmanagement
MERGE (c:Control {framework: "BSI_Grundschutz", id: "ISMS.1"})
ON CREATE SET
  c.title = "Sicherheitsmanagement",
  c.severity = "critical",
  c.description = "Informationssicherheitsmanagement — Planungs-, Lenkungs- und Kontrollaufgaben für einen wirksamen und durchdachten Sicherheitsprozess.",
  c.basis_requirements = [
    "ISMS.1.A1 Übernahme der Gesamtverantwortung für Informationssicherheit durch die Leitung",
    "ISMS.1.A2 Festlegung der Sicherheitsziele und -strategie",
    "ISMS.1.A3 Erstellung einer Leitlinie zur Informationssicherheit",
    "ISMS.1.A4 Benennung eines oder einer Informationssicherheitsbeauftragten"
  ],
  c.source = "BSI IT-Grundschutz-Kompendium Edition 2023";

MERGE (r:Requirement {id: "ISMS.1.A4", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Benennung eines oder einer Informationssicherheitsbeauftragten", r.level = "BASIS";
MATCH (c:Control {id: "ISMS.1", framework: "BSI_Grundschutz"}), (r:Requirement {id: "ISMS.1.A4", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

// OPS.1.2.5 — Fernwartung
MERGE (c:Control {framework: "BSI_Grundschutz", id: "OPS.1.2.5"})
ON CREATE SET
  c.title = "Fernwartung",
  c.severity = "high",
  c.description = "Sicherer Einsatz von Fernwartung — zeitlich begrenzter Remote-Zugriff auf IT-Systeme. Planung, Absicherung der Schnittstellen und Dokumentation.",
  c.basis_requirements = [
    "OPS.1.2.5.A1 Planung des Einsatzes der Fernwartung",
    "OPS.1.2.5.A2 Sicherer Verbindungsaufbau bei der Fernwartung von Clients",
    "OPS.1.2.5.A3 Absicherung der Schnittstellen zur Fernwartung"
  ],
  c.source = "BSI IT-Grundschutz-Kompendium Edition 2023";

MERGE (r:Requirement {id: "OPS.1.2.5.A3", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Absicherung der Schnittstellen zur Fernwartung", r.level = "BASIS";
MATCH (c:Control {id: "OPS.1.2.5", framework: "BSI_Grundschutz"}), (r:Requirement {id: "OPS.1.2.5.A3", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

// OPS.2.2 — Cloud-Nutzung
MERGE (c:Control {framework: "BSI_Grundschutz", id: "OPS.2.2"})
ON CREATE SET
  c.title = "Cloud-Nutzung",
  c.severity = "high",
  c.description = "Sicheres Cloud Computing — dynamische IT-Dienstleistungen über das Netz. Strategie, Sicherheitsrichtlinie, Service-Definition und Verantwortungsbereiche.",
  c.basis_requirements = [
    "OPS.2.2.A1 Erstellung einer Strategie für die Cloud-Nutzung",
    "OPS.2.2.A2 Erstellung einer Sicherheitsrichtlinie für die Cloud-Nutzung",
    "OPS.2.2.A3 Service-Definition für Cloud-Dienste",
    "OPS.2.2.A4 Festlegung von Verantwortungsbereichen und Schnittstellen"
  ],
  c.source = "BSI IT-Grundschutz-Kompendium Edition 2023";

MERGE (r:Requirement {id: "OPS.2.2.A1", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Erstellung einer Strategie für die Cloud-Nutzung", r.level = "BASIS";
MATCH (c:Control {id: "OPS.2.2", framework: "BSI_Grundschutz"}), (r:Requirement {id: "OPS.2.2.A1", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

MERGE (r:Requirement {id: "OPS.2.2.A2", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Erstellung einer Sicherheitsrichtlinie für die Cloud-Nutzung", r.level = "BASIS";
MATCH (c:Control {id: "OPS.2.2", framework: "BSI_Grundschutz"}), (r:Requirement {id: "OPS.2.2.A2", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

// DER.2.1 — Behandlung von Sicherheitsvorfällen
MERGE (c:Control {framework: "BSI_Grundschutz", id: "DER.2.1"})
ON CREATE SET
  c.title = "Behandlung von Sicherheitsvorfällen",
  c.severity = "critical",
  c.description = "Schnelle und effiziente Behandlung von Sicherheitsvorfällen. Definition, Verantwortlichkeiten, Behebung und Wiederherstellung der Betriebsumgebung.",
  c.basis_requirements = [
    "DER.2.1.A1 Definition eines Sicherheitsvorfalls",
    "DER.2.1.A2 Erstellung einer Richtlinie zur Behandlung von Sicherheitsvorfällen",
    "DER.2.1.A3 Festlegung von Verantwortlichkeiten und Ansprechpersonen",
    "DER.2.1.A4 Benachrichtigung betroffener Stellen bei Sicherheitsvorfällen",
    "DER.2.1.A5 Behebung von Sicherheitsvorfällen",
    "DER.2.1.A6 Wiederherstellung der Betriebsumgebung nach Sicherheitsvorfällen"
  ],
  c.source = "BSI IT-Grundschutz-Kompendium Edition 2023";

MERGE (r:Requirement {id: "DER.2.1.A1", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Definition eines Sicherheitsvorfalls", r.level = "BASIS";
MATCH (c:Control {id: "DER.2.1", framework: "BSI_Grundschutz"}), (r:Requirement {id: "DER.2.1.A1", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);

MERGE (r:Requirement {id: "DER.2.1.A5", framework: "BSI_Grundschutz"})
ON CREATE SET r.title = "Behebung von Sicherheitsvorfällen", r.level = "BASIS";
MATCH (c:Control {id: "DER.2.1", framework: "BSI_Grundschutz"}), (r:Requirement {id: "DER.2.1.A5", framework: "BSI_Grundschutz"})
MERGE (c)-[:HAS_REQUIREMENT]->(r);


// ============================================================
// BLOCK J — OWASP API SECURITY TOP 10 (2023)
// ============================================================

MERGE (c:Control {framework: "OWASP_API_Top10", id: "API1"})
ON CREATE SET c.title = "Broken Object Level Authorization",
              c.severity = "critical", c.dsgvo_article = "32",
              c.source_pdf = "owasp-api-security-top-10.pdf", c.text = "";

MERGE (c:Control {framework: "OWASP_API_Top10", id: "API2"})
ON CREATE SET c.title = "Broken Authentication",
              c.severity = "critical", c.dsgvo_article = "32",
              c.source_pdf = "owasp-api-security-top-10.pdf", c.text = "";

MERGE (c:Control {framework: "OWASP_API_Top10", id: "API3"})
ON CREATE SET c.title = "Broken Object Property Level Authorization",
              c.severity = "high", c.dsgvo_article = "32",
              c.source_pdf = "owasp-api-security-top-10.pdf", c.text = "";

MERGE (c:Control {framework: "OWASP_API_Top10", id: "API4"})
ON CREATE SET c.title = "Unrestricted Resource Consumption",
              c.severity = "high", c.dsgvo_article = "32",
              c.source_pdf = "owasp-api-security-top-10.pdf", c.text = "";

MERGE (c:Control {framework: "OWASP_API_Top10", id: "API5"})
ON CREATE SET c.title = "Broken Function Level Authorization",
              c.severity = "critical", c.dsgvo_article = "32",
              c.source_pdf = "owasp-api-security-top-10.pdf", c.text = "";

MERGE (c:Control {framework: "OWASP_API_Top10", id: "API6"})
ON CREATE SET c.title = "Unrestricted Access to Sensitive Business Flows",
              c.severity = "high", c.dsgvo_article = "32",
              c.source_pdf = "owasp-api-security-top-10.pdf", c.text = "";

MERGE (c:Control {framework: "OWASP_API_Top10", id: "API7"})
ON CREATE SET c.title = "Server Side Request Forgery",
              c.severity = "high", c.dsgvo_article = "32",
              c.source_pdf = "owasp-api-security-top-10.pdf", c.text = "";

MERGE (c:Control {framework: "OWASP_API_Top10", id: "API8"})
ON CREATE SET c.title = "Security Misconfiguration",
              c.severity = "high", c.dsgvo_article = "32",
              c.source_pdf = "owasp-api-security-top-10.pdf", c.text = "";

MERGE (c:Control {framework: "OWASP_API_Top10", id: "API9"})
ON CREATE SET c.title = "Improper Inventory Management",
              c.severity = "medium", c.dsgvo_article = "32",
              c.source_pdf = "owasp-api-security-top-10.pdf", c.text = "";

MERGE (c:Control {framework: "OWASP_API_Top10", id: "API10"})
ON CREATE SET c.title = "Unsafe Consumption of APIs",
              c.severity = "medium", c.dsgvo_article = "32",
              c.source_pdf = "owasp-api-security-top-10.pdf", c.text = "";


// ============================================================
// UPDATE EXISTING NODES — source_pdf + text Properties
// ============================================================

// Bestehende Law-Nodes nachpflegen
MATCH (l:Law {name: "DSGVO"})
SET l.source_pdf = "dsgvo.pdf", l.text = coalesce(l.text, "");

MATCH (l:Law {name: "EU AI Act"})
SET l.source_pdf = "euaiact.pdf", l.text = coalesce(l.text, "");

MATCH (l:Law {name: "DDG"})
SET l.source_pdf = "", l.text = coalesce(l.text, "");

MATCH (l:Law {name: "UWG"})
SET l.source_pdf = "", l.text = coalesce(l.text, "");

MATCH (l:Law {name: "TDDDG"})
SET l.source_pdf = "", l.text = coalesce(l.text, "");

// Bestehende Control-Nodes nachpflegen
MATCH (c:Control {framework: "OWASP_Top10"})
SET c.source_pdf = "202512 - OWASP Top 10 2025 by Miglen Evlogiev.pdf",
    c.text = coalesce(c.text, "");

MATCH (c:Control {framework: "OWASP_LLM_Top10"})
SET c.source_pdf = "OWASP-Top-10-for-LLMs-v2025.pdf",
    c.text = coalesce(c.text, "");


// ============================================================
// NEUE RELATIONSHIPS
// ============================================================

// ISO→DSGVO edge moved to byos/iso27001.cypher (ADR-130 D2)

// BSI Grundschutz Bausteine → DSGVO Art. 32: IMPLEMENTS (select controls)
MATCH (c:Control {framework: "BSI_Grundschutz"}), (l:Law {name: "DSGVO", article: "32"})
WHERE c.id IN ["CON.1", "CON.3", "ORP.4", "DER.2.1", "APP.3.1", "APP.3.2", "ISMS.1"]
MERGE (c)-[:IMPLEMENTS]->(l);

// BSI → ToM DocumentType: CONTRIBUTES_TO
MATCH (c:Control {framework: "BSI_Grundschutz"}), (d:DocumentType {type: "TOM"})
WHERE c.id IN ["APP.3.1", "APP.3.2", "CON.1", "CON.3", "ORP.4", "ISMS.1", "DER.2.1"]
MERGE (c)-[:CONTRIBUTES_TO]->(d);

// NIS2→ISO edge moved to byos/iso27001.cypher (ADR-130 D2)

// OWASP API Controls → DSGVO Art. 32: IMPLEMENTS
MATCH (c:Control {framework: "OWASP_API_Top10"}), (l:Law {name: "DSGVO", article: "32"})
MERGE (c)-[:IMPLEMENTS]->(l);

// AI Services → OWASP API Controls: REQUIRES_CONTROL
MATCH (s:Service {ai_act_relevant: true}), (c:Control {framework: "OWASP_API_Top10"})
MERGE (s)-[:REQUIRES_CONTROL]->(c);


// ============================================================
// BLOCK L — NIST CSF 2.0 (CSWP 29, February 2024)
// Source: https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf
// ============================================================

// 6 Core Functions — exact titles from PDF
MERGE (c:Control {framework: "NIST_CSF_2", id: "GV"})
ON CREATE SET
  c.title = "GOVERN",
  c.severity = "critical",
  c.description = "The organization's cybersecurity risk management strategy, expectations, and policy are established, communicated, and monitored",
  c.categories = ["GV.OC", "GV.RM", "GV.RR", "GV.PO", "GV.OV", "GV.SC"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

MERGE (c:Control {framework: "NIST_CSF_2", id: "ID"})
ON CREATE SET
  c.title = "IDENTIFY",
  c.severity = "high",
  c.description = "The organization's current cybersecurity risks are understood",
  c.categories = ["ID.AM", "ID.RA", "ID.IM"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

MERGE (c:Control {framework: "NIST_CSF_2", id: "PR"})
ON CREATE SET
  c.title = "PROTECT",
  c.severity = "high",
  c.description = "Safeguards to manage the organization's cybersecurity risks are used",
  c.categories = ["PR.AA", "PR.AT", "PR.DS", "PR.PS", "PR.IR"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

MERGE (c:Control {framework: "NIST_CSF_2", id: "DE"})
ON CREATE SET
  c.title = "DETECT",
  c.severity = "high",
  c.description = "Possible cybersecurity attacks and compromises are found and analyzed",
  c.categories = ["DE.CM", "DE.AE"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

MERGE (c:Control {framework: "NIST_CSF_2", id: "RS"})
ON CREATE SET
  c.title = "RESPOND",
  c.severity = "high",
  c.description = "Actions regarding a detected cybersecurity incident are taken",
  c.categories = ["RS.MA", "RS.AN", "RS.CO", "RS.MI"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

MERGE (c:Control {framework: "NIST_CSF_2", id: "RC"})
ON CREATE SET
  c.title = "RECOVER",
  c.severity = "high",
  c.description = "Assets and operations affected by a cybersecurity incident are restored",
  c.categories = ["RC.RP", "RC.CO"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

// Key Subcategories — web apps + AI relevant (PR + DE focus)
MERGE (c:Control {framework: "NIST_CSF_2", id: "PR.AA"})
ON CREATE SET
  c.title = "Identity Management, Authentication, and Access Control",
  c.severity = "high",
  c.description = "Access to physical and logical assets is limited to authorized users, services, and hardware and managed commensurate with the assessed risk of unauthorized access",
  c.subcategories = ["PR.AA-01", "PR.AA-03", "PR.AA-05"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

MERGE (c:Control {framework: "NIST_CSF_2", id: "PR.DS"})
ON CREATE SET
  c.title = "Data Security",
  c.severity = "high",
  c.description = "Data are managed consistent with the organization's risk strategy to protect the confidentiality, integrity, and availability of information",
  c.subcategories = ["PR.DS-01", "PR.DS-02", "PR.DS-10", "PR.DS-11"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

MERGE (c:Control {framework: "NIST_CSF_2", id: "PR.PS"})
ON CREATE SET
  c.title = "Platform Security",
  c.severity = "high",
  c.description = "Hardware, software, and services of physical and virtual platforms are managed consistent with the organization's risk strategy",
  c.subcategories = ["PR.PS-01", "PR.PS-04", "PR.PS-06"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

MERGE (c:Control {framework: "NIST_CSF_2", id: "DE.CM"})
ON CREATE SET
  c.title = "Continuous Monitoring",
  c.severity = "high",
  c.description = "Assets are monitored to find anomalies, indicators of compromise, and other potentially adverse events",
  c.subcategories = ["DE.CM-01", "DE.CM-03", "DE.CM-09"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

MERGE (c:Control {framework: "NIST_CSF_2", id: "RS.MA"})
ON CREATE SET
  c.title = "Incident Management",
  c.severity = "high",
  c.description = "Responses to detected cybersecurity incidents are managed",
  c.subcategories = ["RS.MA-01", "RS.MA-02", "RS.MA-03"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

MERGE (c:Control {framework: "NIST_CSF_2", id: "ID.RA"})
ON CREATE SET
  c.title = "Risk Assessment",
  c.severity = "high",
  c.description = "The cybersecurity risk to the organization, assets, and individuals is understood",
  c.subcategories = ["ID.RA-01", "ID.RA-03", "ID.RA-05", "ID.RA-08"],
  c.source = "NIST CSF 2.0 CSWP 29 (February 2024)";

// NIST CSF → CRA: IMPLEMENTS
MATCH (c:Control {framework: "NIST_CSF_2"}),
      (l:Law {name: "CRA", article: "Annex I"})
WHERE c.id IN ["PR", "DE", "RS", "PR.AA", "PR.DS", "DE.CM"]
MERGE (c)-[:IMPLEMENTS]->(l);

// NIST CSF → DSGVO Art. 32: IMPLEMENTS
MATCH (c:Control {framework: "NIST_CSF_2"}),
      (l:Law {name: "DSGVO", article: "32"})
WHERE c.id IN ["PR.DS", "PR.AA", "DE.CM", "RS.MA"]
MERGE (c)-[:IMPLEMENTS]->(l);

// Parent → subcategory: CONTAINS
MATCH (parent:Control {framework: "NIST_CSF_2", id: "PR"}),
      (child:Control {framework: "NIST_CSF_2"})
WHERE child.id IN ["PR.AA", "PR.DS", "PR.PS"]
MERGE (parent)-[:CONTAINS]->(child);

MATCH (parent:Control {framework: "NIST_CSF_2", id: "DE"}),
      (child:Control {framework: "NIST_CSF_2", id: "DE.CM"})
MERGE (parent)-[:CONTAINS]->(child);

MATCH (parent:Control {framework: "NIST_CSF_2", id: "RS"}),
      (child:Control {framework: "NIST_CSF_2", id: "RS.MA"})
MERGE (parent)-[:CONTAINS]->(child);

MATCH (parent:Control {framework: "NIST_CSF_2", id: "ID"}),
      (child:Control {framework: "NIST_CSF_2", id: "ID.RA"})
MERGE (parent)-[:CONTAINS]->(child);


// ============================================================
// BLOCK M — OWASP LLM Top 10 v2025 + Web Top 10 2025
//            (OWASP parts only — NIS2 additions excluded)
// Source: OWASP-Top-10-for-LLMs-v2025.pdf, 202512-OWASP-Top-10-2025.pdf
// ============================================================

// ── OWASP LLM Top 10 v2025 — missing 5 controls ────────────────────────────

MERGE (c:Control {framework: "OWASP_LLM_Top10", id: "LLM03"})
ON CREATE SET
  c.title       = "Supply Chain",
  c.severity    = "high",
  c.description = "LLM supply chains are susceptible to vulnerabilities affecting the integrity of training data, models, and deployment platforms.",
  c.source      = "OWASP Top 10 for LLM Applications v2025"
ON MATCH SET
  c.title       = "Supply Chain",
  c.source      = "OWASP Top 10 for LLM Applications v2025";

MERGE (c:Control {framework: "OWASP_LLM_Top10", id: "LLM04"})
ON CREATE SET
  c.title       = "Data and Model Poisoning",
  c.severity    = "high",
  c.description = "Data poisoning occurs when pre-training, fine-tuning, or embedding data is manipulated to introduce vulnerabilities, backdoors, or biases.",
  c.source      = "OWASP Top 10 for LLM Applications v2025"
ON MATCH SET
  c.title       = "Data and Model Poisoning",
  c.source      = "OWASP Top 10 for LLM Applications v2025";

MERGE (c:Control {framework: "OWASP_LLM_Top10", id: "LLM05"})
ON CREATE SET
  c.title       = "Improper Output Handling",
  c.severity    = "high",
  c.description = "Insufficient validation, sanitization, and handling of LLM outputs before passing downstream to other components and systems.",
  c.source      = "OWASP Top 10 for LLM Applications v2025"
ON MATCH SET
  c.title       = "Improper Output Handling",
  c.source      = "OWASP Top 10 for LLM Applications v2025";

MERGE (c:Control {framework: "OWASP_LLM_Top10", id: "LLM07"})
ON CREATE SET
  c.title       = "System Prompt Leakage",
  c.severity    = "medium",
  c.description = "System prompts used to steer LLM behavior may contain sensitive information that was not intended to be discovered.",
  c.source      = "OWASP Top 10 for LLM Applications v2025"
ON MATCH SET
  c.title       = "System Prompt Leakage",
  c.source      = "OWASP Top 10 for LLM Applications v2025";

MERGE (c:Control {framework: "OWASP_LLM_Top10", id: "LLM10"})
ON CREATE SET
  c.title       = "Unbounded Consumption",
  c.severity    = "high",
  c.description = "LLM applications that allow excessive and uncontrolled inferences, leading to denial of service, financial damage, and model cloning.",
  c.source      = "OWASP Top 10 for LLM Applications v2025"
ON MATCH SET
  c.title       = "Unbounded Consumption",
  c.source      = "OWASP Top 10 for LLM Applications v2025";

// Update source on existing 5 LLM controls
MATCH (c:Control {framework: "OWASP_LLM_Top10"})
WHERE c.id IN ["LLM01","LLM02","LLM06","LLM08","LLM09"]
SET c.source = "OWASP Top 10 for LLM Applications v2025";

// ── OWASP Web Top 10 2025 — add 4 missing + update all titles ──────────────

MERGE (c:Control {framework: "OWASP_Top10", id: "A04"})
ON CREATE SET
  c.title       = "Cryptographic Failures",
  c.severity    = "high",
  c.description = "Cryptographic failures exposing sensitive data — includes weak algorithms, unencrypted transmissions, and improper certificate validation.",
  c.source      = "OWASP Top 10 Web Application Security Risks 2025"
ON MATCH SET
  c.title       = "Cryptographic Failures",
  c.source      = "OWASP Top 10 Web Application Security Risks 2025";

MERGE (c:Control {framework: "OWASP_Top10", id: "A06"})
ON CREATE SET
  c.title       = "Insecure Design",
  c.severity    = "high",
  c.description = "Missing or ineffective security control design — risks from insecure development lifecycle and missing threat modeling.",
  c.source      = "OWASP Top 10 Web Application Security Risks 2025"
ON MATCH SET
  c.title       = "Insecure Design",
  c.source      = "OWASP Top 10 Web Application Security Risks 2025";

MERGE (c:Control {framework: "OWASP_Top10", id: "A08"})
ON CREATE SET
  c.title       = "Integrity Failures",
  c.severity    = "high",
  c.description = "Code or infrastructure not protecting against integrity violations — relies on untrusted sources for plugins, libraries, and modules.",
  c.source      = "OWASP Top 10 Web Application Security Risks 2025"
ON MATCH SET
  c.title       = "Integrity Failures",
  c.source      = "OWASP Top 10 Web Application Security Risks 2025";

MERGE (c:Control {framework: "OWASP_Top10", id: "A10"})
ON CREATE SET
  c.title       = "Mishandling of Exceptions",
  c.severity    = "medium",
  c.description = "Improper prevention, detection, or recovery from unexpected conditions leads to crashes, logic bugs, broken auth, and data loss.",
  c.source      = "OWASP Top 10 Web Application Security Risks 2025"
ON MATCH SET
  c.title       = "Mishandling of Exceptions",
  c.source      = "OWASP Top 10 Web Application Security Risks 2025";

// Update titles + source on existing 6 Web controls to 2025 version
MATCH (c:Control {framework: "OWASP_Top10", id: "A01"})
SET c.title = "Broken Access Control",
    c.source = "OWASP Top 10 Web Application Security Risks 2025";

MATCH (c:Control {framework: "OWASP_Top10", id: "A02"})
SET c.title = "Security Misconfiguration",
    c.source = "OWASP Top 10 Web Application Security Risks 2025";

MATCH (c:Control {framework: "OWASP_Top10", id: "A03"})
SET c.title = "Software Supply Chain Failures",
    c.source = "OWASP Top 10 Web Application Security Risks 2025";

MATCH (c:Control {framework: "OWASP_Top10", id: "A05"})
SET c.title = "Injection",
    c.source = "OWASP Top 10 Web Application Security Risks 2025";

MATCH (c:Control {framework: "OWASP_Top10", id: "A07"})
SET c.title = "Authentication Failures",
    c.source = "OWASP Top 10 Web Application Security Risks 2025";

MATCH (c:Control {framework: "OWASP_Top10", id: "A09"})
SET c.title = "Logging and Alerting Failures",
    c.source = "OWASP Top 10 Web Application Security Risks 2025";

// ── OWASP LLM Top 10 — fix titles on existing controls to v2025 ─────────────
// v1 had different numbering — v2025 reorganized:
// LLM02: Insecure Output Handling → Sensitive Information Disclosure
// LLM06: Sensitive Information Disclosure → Excessive Agency
// LLM08: Excessive Agency → Vector and Embedding Weaknesses
// LLM09: Overreliance → Misinformation

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM02"})
SET c.title = "Sensitive Information Disclosure",
    c.source = "OWASP Top 10 for LLM Applications v2025";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM06"})
SET c.title = "Excessive Agency",
    c.source = "OWASP Top 10 for LLM Applications v2025";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM08"})
SET c.title = "Vector and Embedding Weaknesses",
    c.source = "OWASP Top 10 for LLM Applications v2025";

MATCH (c:Control {framework: "OWASP_LLM_Top10", id: "LLM09"})
SET c.title = "Misinformation",
    c.source = "OWASP Top 10 for LLM Applications v2025";

// ============================================================
// JURISDICTION NORMALIZATION — all Controls in this file are global standards
// ============================================================

MATCH (c:Control)
WHERE c.framework IN ["OWASP_Top10", "OWASP_LLM_Top10",
                      "OWASP_API_Top10", "NIST_CSF_2", "BSI_Grundschutz"]
SET c.jurisdictions = ["global"];

MATCH (r:Requirement)
WHERE r.framework IN ["BSI_Grundschutz"]
SET r.jurisdictions = ["global"];
