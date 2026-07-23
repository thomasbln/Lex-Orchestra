# Source Materials — Setup Guide

This document covers all source materials used by Lex-Orchestra to seed the knowledge graph. It follows a three-tier license model: Tier A ships in the repo, Tier B/C are fetched or licensed by the operator.

**Tier A:** Public, redistributable. Provenance (URL + SHA-256 + license per source) lives in [docs/sources/SOURCES.md](../sources/SOURCES.md). The repo ships **no binary source files** — the graph seeds fully without them; download from the URLs in SOURCES.md only if you want to re-run `pdf_ingest.py`.
**Tier B:** Publicly downloadable but not redistributable. You must download manually.
**Tier C:** Proprietary, purchase required (ISO, DIN, Beuth-Verlag). You must license and place locally.

After cloning the repo, the graph can be seeded fully from Tier-A sources alone — no PDF downloads needed. Tier-B/C materials are required only for specific post-release extensions.

---

## Quick Start

```bash
git clone https://github.com/thomasbln/Lex-Orchestra.git
cd Lex-Orchestra
cp docker/envs/.env.sovereign docker/envs/.env  # configure secrets
# full stack setup: see the README Quickstart (network create + profiles)

# Default target is `local` (bolt://localhost:7687, no prompts)
make seed-all                  # seed Tier-A sources only
make seed-validate             # graph invariants

# Optional: convenience target = seed-all + seed-validate
make seed-bootstrap
```

If you want to enable Tier-B/C extensions, check what's missing first:

```bash
make seed-extras    # walks every sidecar .meta.yaml, reports missing Tier-B/C PDFs
```

Then download/purchase per the Tier-B and Tier-C sections below, place the PDFs
at their `local_path_expected` location, and `make seed-extras` again to confirm.

---

## Tier A — Public, included in repo

These PDFs are committed to git under permissive licenses (dl-de/by-2.0, CC-BY-SA-4.0, EU works, German amtliche Werke § 5 UrhG, U.S. Government works). No user action required.

### DSK (Datenschutzkonferenz) — Goldstandard for Process-Knowledge

Location: `docs/sources/dsk/`
License: dl-de/by-2.0 (Datenlizenz Deutschland)
Attribution: "Konferenz der unabhängigen Datenschutzbehörden des Bundes und der Länder"

| File | Used by |
|---|---|
| `2024-DSK_SDM_V3-1.pdf` (Standard-Datenschutzmodell v3.1) | `seed_sdm_protection_goals`, `seed_sdm_requirements_b`, `seed_sdm_measures` |
| `N-586394-1.pdf` (Fraunhofer DSFA-Handbuch, CC-BY-4.0) | `seed_sdm_measures`, DSFA-Builder-Methodik |
| `DSK_KPNr_5_Datenschutz_Folgenabschaetzung.pdf` | DSFA-Builder Konsultations-Logik |
| `DSK_KPNr_1/3/4/6/20_*.pdf` | post-release extensions |
| `2018-DSK_Hinweise-zum-Verzeichnis-von-Verarbeitungstaetigkeiten.pdf` | `seed_processing_activities`, `seed_data_subjects`, VVT-Template |
| `2018_DSK_DSFA_Liste_Version_1.1.pdf` | DSFA-Trigger-Detection |
| `2024-DSK-OH_KI-und-Datenschutz.pdf` | KI-Policy-Builder, AI-Act-Builder |
| `20250617-DSK-OH_KI-Systeme.pdf` | KI-System-Builder, AI-Act-Builder |
| `20251017-DSK-OH_RAG.pdf` | RAG-UseCase-Classifier |
| `2023_DSK_Datenuebermittlung_USA.pdf` | SCC-Builder TIA-Block |
| `2022-DSK_OH-Werbung.pdf` | post-release marketing extension |
| `2018-BlnBDI_Muster_Verarbeitungsverzeichnis-*.pdf` | VVT-Template-Strukturbasis |
| `20210211_Pruefschema_DSFA_final.docx` | DSFA-Builder-Workflow |

### BfDI (Bundesbeauftragte für Datenschutz und Informationsfreiheit)

Location: `docs/sources/bfdi/`
License: dl-de/by-2.0

| File | Used by |
|---|---|
| `INFO1 (1).pdf` (DSGVO–BDSG Texte und Erläuterungen, 1. Auflage 2026) | `seed_bfdi_anchorings` (14 anchorings extracted into `extracted/bfdi-anchorings.json`) |

### Templates (BayLDA / BlnBDI / DSK Mustervorlagen)

Location: `docs/sources/templates/`
License: amtliches Werk § 5 UrhG (Tier A) — except `04-TOM-Checkliste*` which is Tier B (see below)

| File | Used by |
|---|---|
| `201802_ah_muster_auftragsverarbeiter.pdf` (BayLDA) | AVV-Template |
| `201802_ah_muster_verantwortliche.pdf` (BayLDA) | AVV-Template |
| `201802_ah_verzeichnis_verarbeitungstaetigkeiten.pdf` (BayLDA) | VVT-Template, `seed_processing_activities` |
| `20210211_Pruefschema_DSFA_final.pdf` (DSK/BayLDA) | DSFA-Builder |
| `2022-BlnBDI_Checkliste-Pruefung-AVV_v1.0.pdf` (BlnBDI) | AVV-Validation |
| `Kurze_Checkliste_fuer_eine_Datenschutzfolgeabschaetzung_fuer_Digitale_Archive.pdf` | DSFA-Builder |
| `Muster_zur_Auftragsverarbeitung.pdf` (DSK) | AVV-Template |

### EU Legal Texts (EUR-Lex) — Bilingual DE+EN

Location: `docs/sources/` and `docs/sources/eur-lex/`
License: Works of the EU institutions, free to use.

All major EU regulations are present in **both DE and EN** parallel versions, downloaded directly from EUR-Lex via stable CELEX URLs. This enables EN-output for SCC, AI-Act-Manifest, and VVT. Extending beyond the EU is on the roadmap.

| Regulation | CELEX | DE | EN | Used by |
|---|---|---|---|---|
| **GDPR / DSGVO** | 32016R0679 | `dsgvo.pdf` | `CELEX_32016R0679_EN_TXT.pdf` | DSGVO-Law-Nodes (`title_de` + `title_en`) |
| **EU AI Act** | 32024R1689 | `euaiact.pdf` | `CELEX_32024R1689_EN_TXT.pdf` | EU-AI-Act-Law-Nodes |
| **NIS2** | 32022L2555 | `CELEX_32022L2555_DE_TXT.pdf` | `CELEX_32022L2555_EN_TXT.pdf` | NIS2-Law-Nodes |
| **DORA** | 32022R2554 | `DORA.pdf` | `CELEX_32022R2554_EN_TXT.pdf` | DORA-Law-Nodes |
| **CRA** | 32024R2847 | `cyber-resilience-act-2024-2847.pdf` | `CELEX_32024R2847_EN_TXT.pdf` | `seed_adr066_cra_requirements` |
| **DSA** | 32022R2065 | (DE not included) | `CELEX_32022R2065_EN_TXT.pdf` | DSA-Law-Nodes |
| **SCC 2021/914** | 32021D0914 | `eur-lex/scc-2021-914/CELEX_32021D0914_DE_TXT.pdf` | `eur-lex/scc-2021-914/CELEX_32021D0914_EN_TXT.pdf` | SCC-Builder Modul-2-Anhänge |

### BSI (Bundesamt für Sicherheit in der Informationstechnik)

License: amtliches Werk § 5 UrhG

| File | Used by |
|---|---|
| `IT_Grundschutz_Kompendium.pdf` (Edition 2023) | `seed_adr066_bsi_bausteine` |
| `AI-Cloud-Service-Compliance-Criteria-Catalogue_AIC4.pdf` | `seed_aic4_controls` |
| `C5_2020.pdf` + Reference Tables xlsx | `seed_c5_controls` |

### BSI IT-Grundschutz Kompendium 2023 — full structured content

Location: `docs/sources/bsi it grundschutz/`
License: amtliches Werk § 5 UrhG

Full BSI IT-Grundschutz Kompendium Edition 2023 in machine-parseable form, including all 111 Bausteine. **Reserved for a post-release Measure-Layer extension.** The current `seed_adr066` seeds only 17 Requirements; this directory contains the full ~1500 requirements for a future post-release sprint.

| File | Type | Used by |
|---|---|---|
| `XML_Kompendium_2023.xml` (3 MB) | DocBook 5.0 XML, full Kompendium | `seed_bsi_compendium_xml_future` |
| `Zuordnung_ISO_und_IT_Grundschutz_Edit_6.pdf` | **Official BSI↔ISO 27001 mapping table** | `seed_adr063_maps_to_iso`, `seed_iso_bsi_crosswalk` — makes ISO 27001 (Tier C) usable via cross-walk even without the ISO full text |
| `krt2023_Excel.xlsx` | Cross-reference table 2023 (Excel) | `seed_bsi_compendium_xml_future` |
| `Checklisten/Checkliste_<Baustein>.xlsx` (111 files) | Per-Baustein requirements (MUSS/SOLL/SOLLTE) | `seed_bsi_compendium_xml_future` |

### NIST + OWASP

License: U.S. Government work (NIST) / CC-BY-SA-4.0 (OWASP)

| File | Used by |
|---|---|
| `nist-csf-2.0.pdf` (NIST Cybersecurity Framework 2.0) | `seed_nist_csf_controls` |
| `OWASP-Top-10-for-LLMs-v2025.pdf` | `seed_owasp_llm` |
| `owasp-api-security-top-10.pdf` | `seed_owasp_api` |

---

## Tier B — Publicly downloadable but not redistributable

You must download these manually. They are gitignored.

### a.s.k. TOM-Checkliste V3.3

**Expected path:** `docs/sources/templates/04-TOM-Checkliste-technische-organisatorische-Massnahmen-V3_3-DSGVO (1).pdf`

**Download:** https://www.bdsg-externer-datenschutzbeauftragter.de/

**License:** a.s.k. Datenschutz (Sascha Kuhrau) — "Diese Checkliste kann gerne in der Praxis von Unternehmen oder auch Behörden / kommunalen Einrichtungen genutzt und verändert werden. Ich möchte jedoch nicht, dass diese Checkliste ohne unsere Zustimmung auf anderen Internetseiten als Muster zum Download angeboten wird oder sich irgendwann in einem käuflich zu erwerbenden Vorlagenbuch wiederfindet."

**Consequence for Lex-Orchestra:** Used as structure inspiration only for the TOM template skeleton. **No verbatim content from this checklist is rendered into output documents.** If you don't have this PDF, Lex still works — the TOM-Builder will use SDM v3.1 D1.x measures as the primary content source.

### OWASP Top 10 2025 (Miglen Evlogiev compilation)

**Expected path:** `docs/sources/202512 - OWASP Top 10 2025 by Miglen Evlogiev.pdf`

**Status:** Private compilation, compiler copyright unclear. Not redistributed.

**Alternative (recommended):** Use the original OWASP materials already in Tier A:
- `OWASP-Top-10-for-LLMs-v2025.pdf` (CC-BY-SA-4.0)
- `owasp-api-security-top-10.pdf` (CC-BY-SA-4.0)

The aggregator PDF was for internal research only.

---

## Tier C — Proprietary (purchase required)

These are ISO/IEC standards. They cannot be redistributed under any license — you must purchase them from ISO or a national distributor (e.g. Beuth-Verlag in Germany).

If you don't have these PDFs, the corresponding seed scripts will skip with a clear warning, and the related Controls/Requirements will be marked with `source_status: "tier-C-missing"` in the graph. Lex-Orchestra core functionality continues to work without them.

### ISO/IEC 27001:2022

**Expected path:** `docs/sources/isoiec27001en.pdf`

**Purchase:** https://www.iso.org/standard/27001 (~124 EUR) or Beuth-Verlag

**Used by:** `seed_adr063_maps_to_iso`, `seed_iso27001_controls`

**Impact if missing:** OWASP→ISO 27001 mapping seeds skip; ISO 27001 Annex A controls are not seeded. BSI IT-Grundschutz (Tier A) remains the primary control source.

### ISO/IEC 42001:2023 (KI-Managementsystem)

**Expected path:** `docs/sources/ISO IEC 42001 2023 de.pdf`

**Purchase:** https://www.beuth.de/de/norm/iso-iec-42001/375036944 (~195 EUR)

**Used by:** A planned post-release framework extension. Not currently seeded.

### ISO/IEC 22989:2022 (KI-Konzepte)

**Expected path:** `docs/sources/ISO-22989.pdf`

**Purchase:** https://www.beuth.de/de/norm/iso-iec-22989/348421094 (~195 EUR)

**Used by:** A planned post-release framework extension. Not currently seeded.

---

## Sidecar `.meta.yaml` convention

Every source file in `docs/sources/` has a sibling `<filename>.meta.yaml` with the following fields:

```yaml
title: <Human-readable title>
publisher: <Publisher organization>
date: <Publication date>
tier: A | B | C
license: <License identifier>
license_url: <URL to license text>
license_attribution: <Required attribution string>
source_url: <Original download/info URL>
sha256: <Content hash of the local file, only for tier A>
in_repo: true | false
purchase_url: <Only for tier C>
estimated_cost_eur: <Only for tier C>
local_path_expected: <For tier B/C — where user must place the file>
seeds_used_by: [<list of seed function names>]
notes: <Optional context>
```

When adding new source materials, **always** create a matching sidecar. The provenance test (`tests/test_provenance_invariants.py`) will warn about missing sidecars.

---

## Migration notes (one-time, for existing setups)

If you already have a working Lex-Orchestra setup from before source provenance was introduced:

1. **ISO PDFs:** If you have them, they stay on your disk (now gitignored). Pull will not remove them.
2. **OWASP aggregator PDF:** Same. Stays locally, gitignored.
3. **Seed re-run:** After pulling, run `make seed-all` to populate source/license/last_verified properties on all existing nodes. MERGE-pattern is idempotent — no data loss.
4. **Validation:** `pytest tests/test_provenance_invariants.py` to confirm 100% provenance coverage.

---

## Adding a new source

1. Place the PDF in the appropriate subdirectory of `docs/sources/`.
2. Determine the tier:
   - License explicitly permits redistribution + free-to-share → **Tier A**, commit the PDF
   - Publicly downloadable but compiler/source has restriction → **Tier B**, gitignore + write sidecar
   - Proprietary, purchase required → **Tier C**, gitignore + write sidecar with purchase URL
3. Create the sidecar `.meta.yaml` with all required fields.
4. If Tier A: `git add docs/sources/path/to/file.pdf docs/sources/path/to/file.pdf.meta.yaml`
5. If Tier B/C: Add file pattern to `.gitignore`, commit only the sidecar `.meta.yaml`.
6. Update relevant seed script(s) to reference the new source and use its license/attribution properties.
7. Document the source in this file under the appropriate tier section.

---

## References

- [SOURCES.md](../sources/SOURCES.md) — per-source provenance, license tier and retrieval date
- [graph.md](../architecture/graph.md) — node types, seed layers, write rules
- `scripts/seed_both.py --validate-only` — the graph invariants enforced on every seed run

Design decisions behind these mechanisms are tracked internally.
