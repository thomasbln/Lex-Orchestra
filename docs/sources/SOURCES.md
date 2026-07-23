# Source Registry — Lex-Orchestra

Central pointer list for regulatory sources whose authoritative text lives at a
**stable, free, permanent URL/DOI**. For these, no local PDF copy is kept in
`docs/sources/` — the graph carries the source provenance, and this file maps each
identifier to its canonical online location.

**Scope:** Only sources that are (a) referenced in the graph by URL (not by local path),
(b) **not** read by any seed script / `pdf_ingest.py`, and (c) backed by a stable free
URL/DOI. Sources read by path, builder/template provenance, BSI-licensed material
(unclear license), and point-in-time snapshots remain as local files — see notes below.

Last updated: 2026-07-19

---

## EU regulations — EUR-Lex (CELEX permalink = permanent identifier)

CELEX numbers are permanent EUR-Lex identifiers; the `?uri=CELEX:<n>` form resolves
to the current consolidated text in the requested language. Free reuse under the
EUR-Lex reuse policy.

| Identifier | CELEX | Language | URL |
|---|---|---|---|
| DSGVO / GDPR | 32016R0679 | EN | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32016R0679 |
| EU AI Act | 32024R1689 | EN | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689 |
| NIS2 Directive | 32022L2555 | EN | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022L2555 |
| DSA — Digital Services Act | 32022R2065 | EN | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022R2065 |
| DORA | 32022R2554 | EN | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022R2554 |
| DORA | 32022R2554 | DE | https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32022R2554 |
| CRA — Cyber Resilience Act | 32024R2847 | EN | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R2847 |
| CRA — Cyber Resilience Act | 32024R2847 | DE | https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32024R2847 |

> **DE counterparts still local (read by `pdf_ingest.py`):** `dsgvo.pdf` (CELEX 32016R0679 DE),
> `euaiact.pdf` (CELEX 32024R1689 DE), `CELEX_32022L2555_DE_TXT.pdf` (NIS2 DE) — these populate
> Law-node `text` and must stay. Their EN title provenance is the EUR-Lex EN URLs above.

---

## Frameworks — stable DOI / project URL

| Identifier | Version | URL/DOI | Note |
|---|---|---|---|
| NIST CSF 2.0 (CSWP 29) | 2.0, Feb 2024 | https://doi.org/10.6028/NIST.CSWP.29 | DOI resolves permanently to the PDF. US-Gov, free. |
| OWASP Top 10 (Web) | **2025** | https://owasp.org/Top10/ | ⚠️ Project URL always points to the *latest* version (today 2025, later 2027) — **not version-pinned**. Local snapshot retained: `202512 - OWASP Top 10 2025 by Miglen Evlogiev.pdf`. |

---

## Living lists — local snapshot retained

| Identifier | URL | Snapshot |
|---|---|---|
| EU-US Data Privacy Framework participant list | https://www.dataprivacyframework.gov/list | Local `DataPrivacyFrameworkParticipantsList.xlsx`, **checked 2026-06-04** (pinned for reproducibility — the online list changes over time). |

---

## BYOS — license-gated (not in public repo)

BSI / ISO material whose commercial-reuse licence is unclear is **not shipped** in the
repo. It lives locally in `docs/proprietär/` (gitignored), the user places the file
themselves (Bring-Your-Own-Source). The graph carries only provenance — BSI Baustein
**titles are seeded free** (`seed_adr066`, MERGE, no full-text), the licensed full text
is never embedded. Precedent: ISO 27001 is BYOS.

| Source | Edition | Download | Licence note |
|---|---|---|---|
| BSI IT-Grundschutz-Kompendium | Edition 2023 | https://www.bsi.bund.de/IT-Grundschutz/ | BYOS, licence-gated: commercial use needs a BSI licence contract (precedent SAVISCON); non-commercial free. § 5 UrhG classification disputed. |
| BSI IT-Grundschutz-Kompendium (DE) | Edition 2022 | https://www.bsi.bund.de/SharedDocs/Downloads/DE/BSI/Grundschutz/IT-GS-Kompendium/IT_Grundschutz_Kompendium_Edition2022.pdf?__blob=publicationFile&v=5 | BYOS, same BSI licence terms. Same-edition pair with the EN-2022 below (zero-skew re-baseline source for `basis_requirements` / `basis_requirements_en`). |
| BSI IT-Grundschutz Compendium (EN) | Edition 2022 | https://www.bsi.bund.de/SharedDocs/Downloads/EN/BSI/Grundschutz/International/bsi_it_gs_comp_2022.pdf?__blob=publicationFile&v=2 | BYOS, same BSI licence terms. EN translation of the DE-2022 edition; verified DE-2022 ≡ EN-2022 across all 16 seeded Bausteine (Basic-requirement sets identical). |
| AI-Cloud-Service-Compliance-Criteria-Catalogue (AIC4) | — | https://www.bsi.bund.de/ | same BSI licence terms |
| ISO/IEC 27001 (2022) · 42001 (2023) · 22989 | — | purchase via ISO / Beuth | proprietary, purchase required |

> **Carry-forward (stale seed path):** `pdf_ingest.py` `PDF_REGISTRY["bsi"]`
> ([pdf_ingest.py:382](../../src/graph/pdf_ingest.py#L382)) still names
> `IT_Grundschutz_Kompendium.pdf`, now BYOS in `docs/proprietär/` → `pdf_ingest.py --bsi`
> fails until the path is repointed. The **live** seed `seed_adr066`
> ([seed_both.py:609](../../scripts/seed_both.py#L609)) is **unaffected** — it hardcodes the
> BSI titles (MERGE, no PDF read). To be tracked in the BYOS setup strand
> (`docs/research/backend-source-download-byos.md`, not yet created).

---

## Local snapshots — not shipped in the public repository

The public repository ships **no binary source files** (PDF/XLSX/DOCX). The graph
seeds fully without them (`make seed-all` reads no PDFs — verified in the cleanroom
runs). Every source used for curation is listed below with its original URL, the
SHA-256 of the exact snapshot used, license and date. Fetch a file from its original
URL if you want a local copy (e.g. for optional `pdf_ingest.py` re-ingestion) and
verify it against the checksum — a mismatch means the publisher updated the document
since curation.

| Source | Original URL | SHA-256 of the snapshot used | License | Date |
|---|---|---|---|---|
| Richtlinie (EU) 2022/2555 (NIS2-Richtlinie) | https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32022L2555 | `b15fc30be2d1cd6dbc78aa927206d52ac2f44e685106339f942f4932ce82aea3` | Werk der EU (frei nutzbar) | 2022-12-14 |
| OWASP Top 10 for Large Language Model Applications v2025 | https://genai.owasp.org/llm-top-10/ | `d8596f2c6b3384081574d392619ee3e9065c4f86e5b1fed1bb56be78de2ce382` | CC-BY-SA-4.0 | 2024-11-17 |
| Verordnung (EU) 2016/679 (Datenschutz-Grundverordnung) | https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32016R0679 | `27b720c812be1bdf1462ff468ad6410fe94da80b48f6d10fa7e2269b9e5a1597` | Werk der EU (frei nutzbar) | 2016-04-27 |
| Verordnung (EU) 2024/1689 (KI-Verordnung / EU AI Act) | https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32024R1689 | `8137207e99f26b6fdebd94bd6741a7329ec8b26caaeea48d7bc26f676f44970a` | Werk der EU (frei nutzbar) | 2024-06-13 |
| OWASP API Security Top 10 | https://owasp.org/API-Security/ | `e59962aaca0833820a719c5e7b532ecd0dbef7dc17af4fab4c92adbef6b04239` | CC-BY-SA-4.0 | 2023 |
| OWASP Top 10 2025 (compiled by Miglen Evlogiev) | https://www.linkedin.com/in/miglenevlogiev/ | — | private compilation, compiler copyright unclear | 2025-12 |
| EU-U.S. Data Privacy Framework — Participant List | https://www.dataprivacyframework.gov/ | `53c2ceab01520cf79ffa825d5b3f269cde5509d8798a032b2e99d5dfaf5568f5` | Public domain (U.S. Government work, 17 U.S.C. § 105) — freely distributable | 2026-06-04 |
| DSGVO – BDSG – Texte und Erläuterungen | https://www.bfdi.bund.de/DE/Service/Publikationen/Broschueren/broschueren_node.html | `e10b5907246e4fedaee093646dbc549b24eea53d8d72e3315dd46a5838be926e` | dl-de/by-2.0 | 2026-03 |
| Muster Verarbeitungsverzeichnis (Auftragsverarbeiter) | https://www.datenschutz-berlin.de/themen/datenschutz-in-der-wirtschaft/verzeichnis-von-verarbeitungstaetigkeiten/ | `deab8f39abc34589203e593c8f4f81ef52e791f4fc494bb111048043df275d54` | amtliches Werk § 5 UrhG | 2018 |
| Muster Verarbeitungsverzeichnis (Verantwortlicher) | https://www.datenschutz-berlin.de/themen/datenschutz-in-der-wirtschaft/verzeichnis-von-verarbeitungstaetigkeiten/ | `841bbd3b4860dab880a8aaa1cb218bbb865fddb0f9227e03b3bd8c9023522f88` | amtliches Werk § 5 UrhG | 2018 |
| Hinweise zum Verzeichnis von Verarbeitungstätigkeiten, Art. 30 DSGVO | https://www.datenschutzkonferenz-online.de/orientierungshilfen.html | `5faa6f36dd2c9bea3bfd063f58e77dc0ceea70beb0f847d463faac69a3630b77` | dl-de/by-2.0 | 2018-02 |
| Liste der Verarbeitungsvorgänge gemäß Art. 35 Abs. 4 DS-GVO (Black List) | https://www.datenschutzkonferenz-online.de/dsfa.html | `c42fa3bed399ab837a3fad9fd8790009c754d4583245a8d7f37464d48ef8b027` | dl-de/by-2.0 | 2018-10-17 |
| Prüfschema DSFA | https://www.lda.bayern.de/de/datenschutz_eu.html | `d93109df227e68420b578d5cdeb341fe627e6c523733123640b39702ebeb3fa9` | amtliches Werk § 5 UrhG | 2021-02-11 |
| Datenübermittlungen in die USA (Bewertung Data Privacy Framework) | https://www.datenschutzkonferenz-online.de/positionspapiere.html | `bb8e15827400081d8b29cb0273663a61ee5b19077cd451600466a83787c21e36` | dl-de/by-2.0 | 2023 |
| Orientierungshilfe der Aufsichtsbehörden für Anbieter:innen von KI-Systemen | https://www.datenschutzkonferenz-online.de/orientierungshilfen.html | `07d3d6aff54abd95fe12b6cfcd847fe8928b18c27b02ec2f3dd5abff022cb132` | dl-de/by-2.0 | 2024-05-06 |
| Standard-Datenschutzmodell v3.1 | https://www.datenschutzkonferenz-online.de/standard-datenschutzmodell.html | `c690cd0cc865525745c7218a025bccda2cdd20e0eb33e2dda32e5f0fe9691072` | dl-de/by-2.0 | 2024-05-14 |
| Orientierungshilfe zu KI-Systemen für Verantwortliche | https://www.datenschutzkonferenz-online.de/orientierungshilfen.html | `766a3484e4347c06cb207e7ecee3928397a5bc2ae743fae0a6f5d4b5da66908d` | dl-de/by-2.0 | 2025-06-17 |
| Orientierungshilfe zu Retrieval Augmented Generation (RAG) | https://www.datenschutzkonferenz-online.de/orientierungshilfen.html | `c00136b8b3af62ab3ac449ddd12f24bec70a41f68ec0a05ccee28d06f1e189b7` | dl-de/by-2.0 | 2025-10-17 |
| Kurzpapier Nr. 5 — Datenschutz-Folgenabschätzung nach Art. 35 DS-GVO | https://www.datenschutzkonferenz-online.de/kurzpapiere.html | `d90d58221031c21302ba07611f776f7a531dc1e0cb5aff4d8bbecee39ed80c04` | dl-de/by-2.0 | 2018-12-17 |
| Die Datenschutz-Folgenabschätzung nach Art. 35 DSGVO — Ein Handbuch für die Praxis | https://publica.fraunhofer.de/handle/publica/586394 | `1058ee85b5329059b6c628485cbdb148d45fadda53bdc3d55c002277d9a44618` | CC-BY-4.0 | 2020 |
| Leitlinien 07/2020 zu den Begriffen „Verantwortlicher" und „Auftragsverarbeiter" in der DSGVO (Version 2.1, DE) | https://www.edpb.europa.eu/system/files/2023-10/edpb_guidelines_202007_controllerprocessor_final_de.pdf | `a10507170180a6fb5b534dc4664569e8bed07510ab6b8ca1524bb8061a7f0e87` | EU-Institutionendokument — frei nutzbar gemäß EU-Weiterverwendungspolitik | 2021-07-07 |
| Guidelines 07/2020 on the concepts of controller and processor in the GDPR (Version 2.1, EN) | https://www.edpb.europa.eu/system/files_en?file=2023-10%2FEDPB_guidelines_202007_controllerprocessor_final_en.pdf | `f47d0428ebfab4e4767495bd87e11cbd370439105f35baf710fe9fb31a043e22` | EU institutional document — freely reusable under the EU reuse policy | 2021-07-07 |
| Durchführungsbeschluss (EU) 2021/914 der Kommission über Standardvertragsklauseln für die Übermittlung personenbezogener Daten an Drittländer | https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32021D0914 | `51af5cfa334093a83c37d6051442f6926b6a3e075c31324fd8ab233b5d68ccdc` | Werk der EU-Kommission (frei nutzbar) | 2021-06-04 |
| Commission Implementing Decision (EU) 2021/914 on standard contractual clauses for the transfer of personal data to third countries | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32021D0914 | `e79903f89a984f0414b02a154e164bd6b0cbf24d7f3bfc9b2afa511c84ac8d11` | Work of the EU Commission (free to use) | 2021-06-04 |
| TOM-Checkliste technische-organisatorische Maßnahmen V3.3 (DSGVO) | https://www.bdsg-externer-datenschutzbeauftragter.de/ | `419afa71e8a3f6b15a7909f023c3a988ddf37bc414c6ff2d102e564bf568c09c` | private, restricted use (Nutzung erlaubt, Redistribution untersagt) | 2024-04-29 |
| Anwendungshinweise Muster Auftragsverarbeiter (DSGVO Art. 28) | https://www.lda.bayern.de/de/auftragsverarbeitung.html | `26d1778ce0c91f0150029e87b81db696fe016b3146e35b34d55c9abbb5251702` | amtliches Werk § 5 UrhG | 2018-02 |
| Anwendungshinweise Muster Verantwortliche (DSGVO Art. 28) | https://www.lda.bayern.de/de/auftragsverarbeitung.html | `55cbf5002751db3ee92fec44c383368a35ee38cbef93cbae2e9e60f9e91cd9e7` | amtliches Werk § 5 UrhG | 2018-02 |
| Anwendungshinweise Verzeichnis von Verarbeitungstätigkeiten (DSGVO Art. 30) | https://www.lda.bayern.de/de/dokumente/wp/vvt_hinweise.pdf | `03c79abcd658d95a18b8f08559ddbf81993d7d234d920e60a6adebf40e97a6b4` | amtliches Werk § 5 UrhG | 2018-02 |
| Checkliste Prüfung AVV v1.0 | https://www.datenschutz-berlin.de/themen/datenschutz-in-der-wirtschaft/auftragsverarbeitung/ | `476377d40860496559bc505945ff0910596f2d2cfb2c65062fc1c5d7eb38abf1` | amtliches Werk § 5 UrhG | 2022 |
| Kurze Checkliste für eine Datenschutzfolgenabschätzung für Digitale Archive | https://www.datenschutzkonferenz-online.de/ | `28aac0cc041da2ea5de63c73e875f246d09407dbde37a84135a3fb393d78cf47` | amtliches Werk § 5 UrhG | 2018 |
| Muster zur Auftragsverarbeitung (DSGVO Art. 28) | https://www.datenschutzkonferenz-online.de/orientierungshilfen.html | `66ec4a1458522158546e9c11bec6755177da49f6c2b9351d87aff95efc9c2fa3` | amtliches Werk § 5 UrhG | 2018 |

---

## Not in this registry (private working tree)

- **Shipped and read at seed time:** `bfdi/extracted/bfdi-anchorings.json` — the one
  source file that ships in the public repo (21 KB JSON extract, dl-de/by-2.0 with
  attribution); `make seed-all` reads it.
- **Read by `pdf_ingest.py` when present (optional re-ingestion):** `dsgvo.pdf`,
  `euaiact.pdf`, `CELEX_32022L2555_DE_TXT.pdf`, `OWASP-Top-10-for-LLMs-v2025.pdf`,
  `owasp-api-security-top-10.pdf` — not shipped in the public repo; fetch via the
  snapshot table above. The graph ships pre-seeded, so this is never required.
- **BSI-licensed (license unclear) — BYOS in `docs/proprietär/` (gitignored):**
  `AI-Cloud-Service-Compliance-Criteria-Catalogue_AIC4.pdf`, `IT_Grundschutz_Kompendium.pdf`.
  See the **BYOS** section above.
- **Builder/template provenance** (`dsk/`, `eur-lex/scc-2021-914/`, `edpb_*`, `templates/`,
  `bfdi/INFO1 (1).pdf`) — substantiate generated documents; not shipped, listed in the
  snapshot table above.
