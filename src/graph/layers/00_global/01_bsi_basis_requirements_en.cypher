// ============================================================
// BSI basis_requirements — EN (ADR-129 PR 11)
// Source: BSI IT-Grundschutz Compendium Edition 2022 (EN),
//         bsi_it_gs_comp_2022.pdf — bring your own licensed copy (BYOS)
// Titles VERBATIM from the official EN edition — never translated (source rule).
// Layout metadata stripped from headings: qualification letter (B)/(S)/(H) and
// [role] annotations are not part of the requirement title.
//
// Honest omissions (edition skew DE=Ed.2021 vs EN=Ed.2022, verified in the PDF):
//   - APP.3.1.A10, CON.3.A3, SYS.1.1.A3, SYS.1.1.A4 → officially ELIMINATED in Ed. 2022
//   - OPS.1.1.2: DE list carries old-scheme IDs (OPS.1.1.A*) that do not exist in
//     Ed. 2022 → NO basis_requirements_en (Re-Baseline track, session-continuity)
// SET (idempotent). NOT in make seed-all (Fujitsu track, ADR-130).
// ============================================================

MATCH (c:Control {framework: "BSI_Grundschutz", id: "APP.3.1"})
SET c.basis_requirements_en = [
    "APP.3.1.A1 Authentication",
    "APP.3.1.A4 Controlled Integration of Files and Content",
    "APP.3.1.A7 Protection Against Unauthorised Automated Use",
    "APP.3.1.A14 Protection of Confidential Data"
  ],
  c.basis_requirements_en_source = "BSI IT-Grundschutz Compendium Ed. 2022 (EN)";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "APP.3.2"})
SET c.basis_requirements_en = [
    "APP.3.2.A1 Secure Web Server Configuration",
    "APP.3.2.A2 Protection of Web Server Files",
    "APP.3.2.A3 Protecting File Uploads and Downloads",
    "APP.3.2.A4 Logging of Events",
    "APP.3.2.A5 Authentication",
    "APP.3.2.A7 Legal Framework Conditions for Websites",
    "APP.3.2.A11 Encryption via TLS"
  ],
  c.basis_requirements_en_source = "BSI IT-Grundschutz Compendium Ed. 2022 (EN)";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "APP.6"})
SET c.basis_requirements_en = [
    "APP.6.A1 Planning Software Use",
    "APP.6.A2 Drawing Up a Requirements Catalogue for Software",
    "APP.6.A3 Secure Procurement of Software",
    "APP.6.A4 Regulation of Software Installation and Configuration",
    "APP.6.A5 Secure Installation of Software"
  ],
  c.basis_requirements_en_source = "BSI IT-Grundschutz Compendium Ed. 2022 (EN)";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "CON.1"})
SET c.basis_requirements_en = [
    "CON.1.A1 Selecting Appropriate Cryptographic Methods",
    "CON.1.A2 Backups When Using Cryptographic Methods",
    "CON.1.A4 Appropriate Key Management",
    "CON.1.A5 Secure Deletion and Destruction of Cryptographic Keys"
  ],
  c.basis_requirements_en_source = "BSI IT-Grundschutz Compendium Ed. 2022 (EN)";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "CON.10"})
SET c.basis_requirements_en = [
    "CON.10.A1 Authentication for Web Applications",
    "CON.10.A2 Access Control for Web Applications",
    "CON.10.A3 Secure Session Management",
    "CON.10.A4 Controlled Integration of Content in Web Applications"
  ],
  c.basis_requirements_en_source = "BSI IT-Grundschutz Compendium Ed. 2022 (EN)";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "CON.2"})
SET c.basis_requirements_en = [
    "CON.2.A1 Implementing the German Standard Data Protection Model"
  ],
  c.basis_requirements_en_source = "BSI IT-Grundschutz Compendium Ed. 2022 (EN)";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "CON.3"})
SET c.basis_requirements_en = [
    "CON.3.A1 Determining the Factors That Influence Backups",
    "CON.3.A2 Establishment of Backup Procedures",
    "CON.3.A4 Creating Backup Plans",
    "CON.3.A5 Regular Backups",
    "CON.3.A6 Developing a Backup Concept"
  ],
  c.basis_requirements_en_source = "BSI IT-Grundschutz Compendium Ed. 2022 (EN)";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "DER.2.1"})
SET c.basis_requirements_en = [
    "DER.2.1.A1 Definition of a Security Incident",
    "DER.2.1.A2 Drawing Up a Policy for Handling Security Incidents",
    "DER.2.1.A3 Specification of Responsibilities and Contact Persons in the Event of Security Incidents",
    "DER.2.1.A4 Notification of Entities Affected by Security Incidents",
    "DER.2.1.A5 Remedial Action in Connection with Security incidents",
    "DER.2.1.A6 Recovering the Operating Environment After Security Incidents"
  ],
  c.basis_requirements_en_source = "BSI IT-Grundschutz Compendium Ed. 2022 (EN)";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "ISMS.1"})
SET c.basis_requirements_en = [
    "ISMS.1.A1 Acceptance of Overall Responsibility for Information Security by Top Management",
    "ISMS.1.A2 Defining Security Objectives and Strategy",
    "ISMS.1.A3 Drawing Up an Information Security Policy",
    "ISMS.1.A4 Appointment of a Chief Information Security Officer"
  ],
  c.basis_requirements_en_source = "BSI IT-Grundschutz Compendium Ed. 2022 (EN)";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "NET.1.1"})
SET c.basis_requirements_en = [
    "NET.1.1.A1 Security Policy for the Network",
    "NET.1.1.A2 Documentation of the Network",
    "NET.1.1.A3 Specification of Network Requirements",
    "NET.1.1.A4 Network Separation into Zones"
  ],
  c.basis_requirements_en_source = "BSI IT-Grundschutz Compendium Ed. 2022 (EN)";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "OPS.1.2.5"})
SET c.basis_requirements_en = [
    "OPS.1.2.5.A1 Planning the Use of Remote Maintenance",
    "OPS.1.2.5.A2 Establishing a Secure Connection for Remote Maintenance of Clients",
    "OPS.1.2.5.A3 Securing Interfaces for Remote Maintenance"
  ],
  c.basis_requirements_en_source = "BSI IT-Grundschutz Compendium Ed. 2022 (EN)";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "OPS.2.2"})
SET c.basis_requirements_en = [
    "OPS.2.2.A1 Drawing Up a Strategy for Cloud Usage",
    "OPS.2.2.A2 Drawing Up a Security Policy for Cloud Usage",
    "OPS.2.2.A3 Service Definition for Cloud Services by the Customer",
    "OPS.2.2.A4 Definition of Areas of Responsibility and Interfaces"
  ],
  c.basis_requirements_en_source = "BSI IT-Grundschutz Compendium Ed. 2022 (EN)";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "ORP.1"})
SET c.basis_requirements_en = [
    "ORP.1.A1 Specification of Responsibilities and Provisions",
    "ORP.1.A2 Assigning Responsibilities",
    "ORP.1.A3 Supervising or Escorting External Individuals",
    "ORP.1.A4 Separation of Roles Between Incompatible Tasks"
  ],
  c.basis_requirements_en_source = "BSI IT-Grundschutz Compendium Ed. 2022 (EN)";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "ORP.4"})
SET c.basis_requirements_en = [
    "ORP.4.A1 Regulation for Creating and Deleting Users and User Groups",
    "ORP.4.A2 Creating, Changing, and Revoking Authorisations",
    "ORP.4.A4 Distribution of Tasks and Separation of Roles",
    "ORP.4.A7 Assignment of Data Access Rights",
    "ORP.4.A8 Provisions Governing the Use of Passwords",
    "ORP.4.A9 Identification and Authentication",
    "ORP.4.A22 Regulating Password Quality"
  ],
  c.basis_requirements_en_source = "BSI IT-Grundschutz Compendium Ed. 2022 (EN)";

MATCH (c:Control {framework: "BSI_Grundschutz", id: "SYS.1.1"})
SET c.basis_requirements_en = [
    "SYS.1.1.A1 Appropriate Installation",
    "SYS.1.1.A2 User Authentication on Servers",
    "SYS.1.1.A6 Disabling Unnecessary Services"
  ],
  c.basis_requirements_en_source = "BSI IT-Grundschutz Compendium Ed. 2022 (EN)";
