"""
Neo4j Seeder — layer manifest + Python modules (ADR-130)
=========================================================

Usage:
    python scripts/seed_both.py                          # full seed, local Neo4j
    python scripts/seed_both.py --target nuc             # maintainer host (prompts; --yes to skip)
    python scripts/seed_both.py --module adr063          # single module, local
    python scripts/seed_both.py --validate-only          # ADR-100 checks, no writes
    python scripts/seed_both.py --validate-only --target aura   # aura is validate-only

Targets (ADR-130 D4/D5):
    local  (default) — bolt://localhost:7687, never prompts. Env overrides:
           NEO4J_LOCAL_URI / NEO4J_LOCAL_USERNAME / NEO4J_LOCAL_PASSWORD.
           Username/password fall back to the generic NEO4J_USERNAME /
           NEO4J_PASSWORD (docker/envs/.env). The URI deliberately does NOT
           fall back to NEO4J_URI — a generic URI can point at a remote
           instance, and a "local" run that silently writes remote is the
           incident class the target split exists to prevent.
    nuc    — maintainer host via NEO4J_NUC_* (SSH tunnel). Write runs prompt
           for confirmation; --yes skips (automation). Non-TTY without --yes
           aborts.
    aura   — validate-only (non-authoritative since 2026-05-27). Write runs
           are rejected. 'both' no longer exists.

All MERGE — idempotent (ADR-003). Safe to re-run.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

# ADR-053: docker/envs/.env is the single canonical env file. Load it by explicit
# path — a bare load_dotenv() searches upward from scripts/ and never reaches
# docker/envs/.env, so a fresh self-hoster keeps hitting the very error the
# script prints (F3). Missing file → no-op, shell env still applies.
load_dotenv(Path(__file__).resolve().parent.parent / "docker" / "envs" / ".env")

# ── ADR-107 Provenance (Source Discipline) ────────────────────────────────────
# Per-module provenance dicts. Each seed function uses the helper to splice
# source/source_url/license/license_attribution/last_verified into every node
# MERGE-SET and every relationship MERGE-SET — for both Nodes AND Edges.
# Bumped `_LAST_VERIFIED` per re-seed run; existing values get updated via MERGE.

_LAST_VERIFIED = "2026-05-28"

PROV_ADR061 = {
    "source": "ADR-061 Lex-Orchestra (kuratiert) — ServiceCategory layer",
    "license": "Lex-Orchestra internal",
    "license_attribution": "Lex-Orchestra",
    "last_verified": _LAST_VERIFIED,
}
PROV_ADR066 = {
    "source": "BSI IT-Grundschutz-Kompendium Edition 2023",
    "source_url": "https://www.bsi.bund.de/IT-Grundschutz/",
    "license": "amtliches Werk § 5 UrhG",
    "license_attribution": "Bundesamt für Sicherheit in der Informationstechnik",
    "last_verified": _LAST_VERIFIED,
}
PROV_ADR063 = {
    "source": "OWASP Top 10 + ISO/IEC 27001:2022 Annex A mapping (kuratiert)",
    "source_url": "https://owasp.org/Top10/",
    "license": "OWASP CC-BY-SA-4.0 + ISO Tier-C (Mapping kuratiert)",
    "license_attribution": "OWASP Foundation; mapping curated by Lex-Orchestra",
    "last_verified": _LAST_VERIFIED,
}
PROV_STUBS = {
    "source": "ADR-061 Service-Stubs (kuratiert)",
    "license": "Lex-Orchestra internal + Service-Provider-Trust-Pages",
    "license_attribution": "Lex-Orchestra",
    "last_verified": _LAST_VERIFIED,
}
PROV_ADR075 = {
    "source": "ADR-075 Service-Region + SCC-Annotations (kuratiert)",
    "license": "Lex-Orchestra internal + EU SCC Decision 2021/914",
    "license_attribution": "Lex-Orchestra; EU Commission SCC 2021/914",
    "last_verified": _LAST_VERIFIED,
}
PROV_ADR076 = {
    "source": "ADR-076 HostingProvider (kuratiert + Provider-Trust-Pages)",
    "license": "Lex-Orchestra internal + Provider Trust-Page-Statements",
    "license_attribution": "Lex-Orchestra",
    "last_verified": _LAST_VERIFIED,
}
PROV_ADR082 = {
    "source": "ADR-082 Integration Catalog (kuratiert)",
    "license": "Lex-Orchestra internal",
    "license_attribution": "Lex-Orchestra",
    "last_verified": _LAST_VERIFIED,
}
PROV_ADR093 = {
    "source": "DSGVO + NIS2 Volltext (EUR-Lex) + Lex-Orchestra Erläuterungen",
    "source_url": "https://eur-lex.europa.eu/",
    "license": "Werk der EU (frei nutzbar) + Lex-Orchestra-Erläuterungen",
    "license_attribution": "EUR-Lex; Erläuterungen by Lex-Orchestra",
    "last_verified": _LAST_VERIFIED,
}


def _prov_node_set(alias: str) -> str:
    """Cypher SET fragment for node `alias`, using $_p_* params. Returns leading ', '."""
    return (
        f", {alias}.source = $_p_source"
        f", {alias}.source_url = $_p_source_url"
        f", {alias}.license = $_p_license"
        f", {alias}.license_attribution = $_p_license_attribution"
        f", {alias}.last_verified = date($_p_last_verified)"
    )


def _prov_edge_set(alias: str) -> str:
    """Cypher SET fragment for relationship `alias` (e.g. 'r'). NO leading comma."""
    return (
        f"{alias}.source = $_p_source, "
        f"{alias}.source_url = $_p_source_url, "
        f"{alias}.license = $_p_license, "
        f"{alias}.license_attribution = $_p_license_attribution, "
        f"{alias}.last_verified = date($_p_last_verified)"
    )


def _prov_params(prov: dict) -> dict:
    """Turn a PROV_* dict into session.run kwargs (prefixed `_p_*` to avoid clash).

    Internal-curation dicts (ADR-061/075/076/082/106-B2/115 mappings) carry NO
    source_url — the deciding ADRs stay private, a link would point nowhere
    (verdict 2026-07-17, ADR-107 addendum). Defaulting the param to None keeps
    the shared SET fragments valid: `SET x.source_url = null` never creates the
    property and clears any legacy value on re-seed. The ADR identity stays in
    `source`.
    """
    params = {f"_p_{k}": v for k, v in prov.items()}
    params.setdefault("_p_source_url", None)
    return params


# ── ADR-106 PR B: 4 mini-seeds (provenance dicts) ─────────────────────────────

PROV_PR_B1_GPAI = {
    "source": "EU AI Act Art. 53 (Verordnung (EU) 2024/1689)",
    "source_url": "https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32024R1689",
    "license": "Werk der EU (frei nutzbar)",
    "license_attribution": "EUR-Lex",
    "last_verified": _LAST_VERIFIED,
}
PROV_PR_B2_DATACAT = {
    "source": "Service-Provider Trust-Pages + DPAs (kuratiert ADR-106 PR B2)",
    "license": "Lex-Orchestra internal + Provider Trust-Page-Statements",
    "license_attribution": "Lex-Orchestra (curated)",
    "last_verified": _LAST_VERIFIED,
}
PROV_PR_B3_RETENTION = {
    "source": "HGB § 257 + BAG-Rspr. + Art. 7 Abs. 3 DSGVO + § 24 BDSG (kuratiert)",
    "source_url": "https://www.gesetze-im-internet.de/hgb/__257.html",
    "license": "amtliches Werk § 5 UrhG (Gesetzestext)",
    "license_attribution": "Gesetzestext / Lex-Orchestra (Default-Mapping)",
    "last_verified": _LAST_VERIFIED,
}
PROV_PR_B4_SUPAUTH = {
    "source": "Bundesbeauftragte für den Datenschutz und die Informationsfreiheit (BfDI) — Aufsichtsbehörden-Liste",
    "source_url": "https://www.bfdi.bund.de/DE/Service/Anschriften/Laender/Laender-node.html",
    "license": "amtliches Werk § 5 UrhG",
    "license_attribution": "BfDI / Länderdatenschutzbehörden",
    "last_verified": _LAST_VERIFIED,
}

# ── ADR-106 PR C: SDM-Layer + BfDI-Anchorings ────────────────────────────────

PROV_PR_C_SDM = {
    "source": "Standard-Datenschutzmodell (SDM) v3.1, Datenschutzkonferenz 14.05.2024",
    "source_url": "https://www.datenschutzkonferenz-online.de/standard-datenschutzmodell.html",
    "license": "dl-de/by-2-0",
    "license_attribution": "Konferenz der unabhängigen Datenschutzbehörden des Bundes und der Länder (Datenschutzkonferenz)",
    "last_verified": _LAST_VERIFIED,
}
PROV_PR_C_LEGAL = {
    "source": "DSGVO Volltext (EUR-Lex CELEX 32016R0679) + BDSG (Bundesgesetzblatt)",
    "source_url": "https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32016R0679",
    "license": "Werk der EU + amtliches Werk § 5 UrhG",
    "license_attribution": "EUR-Lex / BMJV",
    "last_verified": _LAST_VERIFIED,
}
PROV_PR_C_BFDI = {
    "source": "BfDI-Broschüre 'DSGVO – BDSG – Texte und Erläuterungen', 1. Auflage März 2026",
    "source_url": "https://www.bfdi.bund.de/DE/Service/Publikationen/Broschueren/broschueren_node.html",
    "license": "dl-de/by-2-0",
    "license_attribution": "Die Bundesbeauftragte für den Datenschutz und die Informationsfreiheit",
    "last_verified": _LAST_VERIFIED,
}


# ── ADR-061: ServiceCategory nodes + category->control mappings ───────────────
CATEGORIES = [
    ("baas",           "Backend-as-a-Service",          True,  True),
    ("database",       "Relationale Datenbank",          True,  False),
    ("nosql_db",       "NoSQL-Datenbank",                True,  False),
    ("cache_db",       "In-Memory Cache",                True,  False),
    ("ai_llm",         "KI-Sprachmodell (LLM)",          True,  True),
    ("ai_platform",    "KI-Plattform",                   True,  True),
    ("payment",        "Zahlungsdienstleister",          True,  True),
    ("monitoring",     "Error/Log-Monitoring",           True,  True),
    ("email",          "E-Mail-Versand",                 True,  True),
    ("email_marketing","E-Mail-Marketing",               True,  True),
    ("auth",           "Authentifizierung / IAM",        True,  True),
    ("hosting",        "Server / PaaS-Hosting",          True,  False),
    ("cloud",          "Cloud-Infrastruktur",            True,  True),
    ("storage",        "Datei-Storage",                  True,  False),
    ("vector_db",      "Vektor-Datenbank",               True,  False),
    ("analytics",      "Analyse / Tracking",             True,  True),
    ("cdn_security",   "CDN / Web-Security",             True,  True),
    ("vcs",            "Versionskontrolle",              False, False),
    ("ci_cd",          "CI/CD-Pipeline",                 True,  False),
    ("crm",            "CRM / Kundendaten",              True,  True),
    ("crm_support",    "Support-CRM",                    True,  True),
    ("sms",            "SMS-Versand",                    True,  True),
    ("observability",  "LLM-Observability",              True,  False),
    ("media_storage",  "Medien-Storage",                 True,  False),
    ("search_db",      "Such-Index",                     True,  False),
    ("security",       "Security / SIEM",                True,  False),
    # collaboration: war Graph-Drift (source="ADR-061-extension-2026-05-26" im Graph,
    # aber nicht im Seed-Code) — PR 0.5 (ISO-Deseed) macht den Knoten reproduzierbar.
    ("collaboration",  "Kollaborations-Plattform",       True,  True),
]

# category -> control mappings (patched fallback IDs, ADR-066 upgrades them later)
CATEGORY_CONTROLS = [
    ("baas", "8.13", "ISO_27001"), ("baas", "8.20", "ISO_27001"), ("baas", "8.24", "ISO_27001"),
    ("baas", "APP.3.1", "BSI_Grundschutz"), ("baas", "CON.3", "BSI_Grundschutz"), ("baas", "OPS.1.1", "BSI_Grundschutz"),
    ("database", "8.13", "ISO_27001"), ("database", "8.24", "ISO_27001"), ("database", "8.3", "ISO_27001"),
    ("database", "APP.3.1", "BSI_Grundschutz"), ("database", "CON.3", "BSI_Grundschutz"), ("database", "OPS.1.1", "BSI_Grundschutz"),
    ("nosql_db", "8.13", "ISO_27001"), ("nosql_db", "8.24", "ISO_27001"), ("nosql_db", "8.3", "ISO_27001"),
    ("nosql_db", "APP.3.1", "BSI_Grundschutz"), ("nosql_db", "CON.3", "BSI_Grundschutz"),
    ("cache_db", "8.24", "ISO_27001"), ("cache_db", "8.3", "ISO_27001"),
    ("cache_db", "APP.3.1", "BSI_Grundschutz"), ("cache_db", "CON.1", "BSI_Grundschutz"),
    ("ai_llm", "8.20", "ISO_27001"), ("ai_llm", "8.24", "ISO_27001"), ("ai_llm", "5.23", "ISO_27001"),
    ("ai_llm", "OPS.1.1", "BSI_Grundschutz"), ("ai_llm", "CON.2", "BSI_Grundschutz"),
    # ai_platform — same as ai_llm: cloud AI API services
    ("ai_platform", "8.20", "ISO_27001"), ("ai_platform", "8.24", "ISO_27001"), ("ai_platform", "5.23", "ISO_27001"),
    ("ai_platform", "OPS.1.1", "BSI_Grundschutz"), ("ai_platform", "CON.2", "BSI_Grundschutz"),
    ("payment", "8.20", "ISO_27001"), ("payment", "8.24", "ISO_27001"), ("payment", "OPS.1.1", "BSI_Grundschutz"),
    ("monitoring", "8.15", "ISO_27001"), ("monitoring", "8.20", "ISO_27001"),
    ("monitoring", "DER.2.1", "BSI_Grundschutz"), ("monitoring", "OPS.1.1", "BSI_Grundschutz"),
    ("email", "8.20", "ISO_27001"), ("email", "5.14", "ISO_27001"), ("email", "OPS.1.2.5", "BSI_Grundschutz"),
    ("email_marketing", "8.20", "ISO_27001"), ("email_marketing", "5.14", "ISO_27001"), ("email_marketing", "OPS.1.2.5", "BSI_Grundschutz"),
    ("auth", "5.15", "ISO_27001"), ("auth", "8.2", "ISO_27001"),
    ("auth", "ORP.4", "BSI_Grundschutz"), ("auth", "SYS.1.1", "BSI_Grundschutz"),
    ("hosting", "8.14", "ISO_27001"), ("hosting", "8.20", "ISO_27001"),
    ("hosting", "CON.3", "BSI_Grundschutz"), ("hosting", "OPS.1.1", "BSI_Grundschutz"),
    ("cloud", "8.13", "ISO_27001"), ("cloud", "8.14", "ISO_27001"), ("cloud", "8.20", "ISO_27001"),
    ("cloud", "CON.3", "BSI_Grundschutz"),
    ("vector_db", "8.13", "ISO_27001"), ("vector_db", "8.24", "ISO_27001"),
    ("vector_db", "APP.3.1", "BSI_Grundschutz"), ("vector_db", "CON.3", "BSI_Grundschutz"),
    ("storage", "8.13", "ISO_27001"), ("storage", "8.24", "ISO_27001"), ("storage", "CON.3", "BSI_Grundschutz"),
    ("observability", "8.15", "ISO_27001"), ("observability", "8.16", "ISO_27001"), ("observability", "DER.2.1", "BSI_Grundschutz"),
    ("analytics", "8.15", "ISO_27001"), ("analytics", "5.33", "ISO_27001"),
    ("analytics", "OPS.1.1", "BSI_Grundschutz"), ("analytics", "CON.2", "BSI_Grundschutz"),
    ("crm", "5.34", "ISO_27001"), ("crm", "8.3", "ISO_27001"),
    ("crm", "ORP.1", "BSI_Grundschutz"), ("crm", "OPS.1.1", "BSI_Grundschutz"),
    ("vcs", "8.4", "ISO_27001"), ("vcs", "CON.1", "BSI_Grundschutz"),
    ("ci_cd", "8.25", "ISO_27001"), ("ci_cd", "8.29", "ISO_27001"), ("ci_cd", "CON.1", "BSI_Grundschutz"),
    # collaboration: Grundschutz-Pendants zu ISO 5.15/8.16/5.14/5.34 (PR 0.5, ISO-Deseed-Blocker).
    # War Graph-Drift (kein Seed-Code) + nach ISO-Deseed sonst NUR-ISO → Slack fiele auf 0 Controls.
    ("collaboration", "ORP.4",     "BSI_Grundschutz"),
    ("collaboration", "OPS.1.1.5", "BSI_Grundschutz"),
    ("collaboration", "CON.1",     "BSI_Grundschutz"),
    ("collaboration", "CON.2",     "BSI_Grundschutz"),
    # F23a (Graph-Diff 2026-07-15, checklist row 47): the PR-8-Fix-A edges were
    # live NucBox writes (2026-04-23) that never reached the seed tables — a
    # fresh install left these categories without BSI coverage and regressed
    # the vvt_legal_basis_missing gap. legal_basis comes from the Phase-3
    # layer 12_legal_basis_backfill.cypher (all four categories are in its
    # mapping; values verified against live NucBox edges).
    ("media_storage", "CON.3",     "BSI_Grundschutz"),
    ("search_db",     "CON.1",     "BSI_Grundschutz"),
    ("search_db",     "APP.3.1",   "BSI_Grundschutz"),
    ("security",      "CON.1",     "BSI_Grundschutz"),
]

# ── ADR-066: 6 precise BSI nodes + upgrade mappings ───────────────────────────
# title_en = official BSI IT-Grundschutz Compendium EN headings (Ed. 2022), Title Case —
# aligned with ADR-126 Phase 3b verify-seed so a standalone `--module adr066` does not
# write a divergent title_en (ORP.3 corrected from the old "Information security awareness…").
NEW_BSI = [
    ("APP.4.3",   "Relationale Datenbanksysteme",                              "Relational Database Systems"),
    ("OPS.1.1.3", "Patch- und Änderungsmanagement",                            "Patch and Change Management"),
    ("OPS.1.1.5", "Protokollierung",                                           "Logging"),
    ("OPS.1.2.4", "Telearbeit",                                                "Teleworking"),
    ("SYS.2.1",   "Allgemeiner Client",                                        "General Client"),
    ("ORP.3",     "Sensibilisierung und Schulung zur Informationssicherheit",  "Awareness and Training in Information Security"),
]

BSI_UPGRADES = [
    (["database", "nosql_db", "vector_db", "cache_db"],                                        "APP.4.3"),
    (["baas", "database", "nosql_db", "hosting", "cloud", "payment", "crm", "crm_support"],    "OPS.1.1.3"),
    # sms / cdn_security added per F23a (Graph-Diff 2026-07-15) — PR-8-Fix-A
    # live edges pulled into the seed tables (targets are NEW_BSI controls,
    # so they belong here rather than in CATEGORY_CONTROLS).
    (["monitoring", "observability", "cdn_security"],                                          "OPS.1.1.5"),
    (["email", "email_marketing", "sms"],                                                      "OPS.1.2.4"),
    (["auth", "hosting"],                                                                      "SYS.2.1"),
    (["crm", "crm_support", "analytics"],                                                      "ORP.3"),
    # ADR-127 Phase 2.0 — make 3 dead BSI controls scan-reachable (2026-06-20).
    # ISMS.1 + APP.6 deliberately excluded (not Lex target-group / too broad).
    # legal_basis is category-driven via 12_legal_basis_backfill.cypher (covers all
    # categories below) — NOT set here. Backfill is a separate, pre-existing manual
    # layer (not chained into seed-all) — tracked, not fixed here.
    (["cloud", "hosting", "baas", "storage", "media_storage"],                                 "OPS.2.2"),
    (["hosting", "cloud", "cdn_security"],                                                     "APP.3.2"),
    (["vcs", "ci_cd"],                                                                         "CON.10"),
]

# ── ADR-063: OWASP -> ISO MAPS_TO with tom_section ────────────────────────────
OWASP_MAPS = [
    ("API1",  "OWASP_API_Top10", "5.15", "1.3 Zugriffskontrolle"),
    ("API2",  "OWASP_API_Top10", "8.2",  "1.2 Zugangskontrolle"),
    ("API3",  "OWASP_API_Top10", "5.15", "1.3 Zugriffskontrolle"),
    ("API4",  "OWASP_API_Top10", "8.6",  "3.1 Verfügbarkeitskontrolle"),
    ("API5",  "OWASP_API_Top10", "5.15", "1.3 Zugriffskontrolle"),
    ("API6",  "OWASP_API_Top10", "8.3",  "1.3 Zugriffskontrolle"),
    ("API7",  "OWASP_API_Top10", "8.23", "2.1 Weitergabekontrolle"),
    ("API8",  "OWASP_API_Top10", "8.9",  "4.1 Datenschutz-Maßnahmen"),
    ("API9",  "OWASP_API_Top10", "5.9",  "4.1 Datenschutz-Maßnahmen"),
    ("API10", "OWASP_API_Top10", "8.28", "4.1 Datenschutz-Maßnahmen"),
    ("LLM01", "OWASP_LLM_Top10", "8.28", "4.1 Datenschutz-Maßnahmen"),
    ("LLM02", "OWASP_LLM_Top10", "5.34", "1.5 Pseudonymisierung"),
    ("LLM03", "OWASP_LLM_Top10", "5.19", "4.4 Auftragskontrolle"),
    ("LLM04", "OWASP_LLM_Top10", "8.24", "4.3 Privacy by Design"),
    ("LLM05", "OWASP_LLM_Top10", "8.28", "4.1 Datenschutz-Maßnahmen"),
    ("LLM06", "OWASP_LLM_Top10", "5.15", "1.3 Zugriffskontrolle"),
    ("LLM07", "OWASP_LLM_Top10", "5.34", "1.5 Pseudonymisierung"),
    ("LLM08", "OWASP_LLM_Top10", "8.24", "4.3 Privacy by Design"),
    ("LLM09", "OWASP_LLM_Top10", "5.36", "4.1 Datenschutz-Maßnahmen"),
    ("LLM10", "OWASP_LLM_Top10", "8.6",  "3.1 Verfügbarkeitskontrolle"),
]

# ── ADR-076: HostingProvider curated list ──────────────────────────────────
# Source: ADR-076 § Graph-Schema-Erweiterung.
# Tuple: (name, soc2, iso27001, default_regions, requires_scc_outside_eu)
ADR_076_HOSTING: list[tuple[str, bool, bool, list[str], bool]] = [
    ("AWS",            True,  True,  ["us-east-1", "eu-central-1", "eu-west-1"], True),
    ("GCP",            True,  True,  ["us-central1", "europe-west3"],             True),
    ("Azure",          True,  True,  ["eastus", "westeurope"],                    True),
    ("Hetzner",        False, True,  ["eu-central", "eu-west"],                   False),
    ("IONOS",          False, True,  ["eu-central"],                              False),
    ("OVH",            True,  True,  ["eu-west"],                                 False),
    ("Strato",         False, True,  ["eu-central"],                              False),
    ("Supabase Cloud", True,  False, ["eu-west-1", "us-east-1"],                  True),
    ("Vercel",         True,  False, ["global"],                                  True),
    ("Railway",        False, False, ["us-west1"],                                True),
    ("Fly.io",         True,  False, ["global"],                                  True),
    ("Cloudflare",     True,  True,  ["global"],                                  True),
]


# ── ADR-075: Service region + SCC mechanism ─────────────────────────────────
# Source: ADR-075 § 5 (Service DB table).
# Tuple: (service_name, default_region, requires_scc, scc_mechanism_or_null)
ADR_075_SCC: list[tuple[str, str, bool, str | None]] = [
    ("Stripe",        "us-east-1",  True,  "EU_SCCs_2021"),
    ("Postmark",      "us-east-1",  True,  "EU_SCCs_2021"),
    ("Twilio",        "us-west-2",  True,  "EU_SCCs_2021"),
    ("SendGrid",      "us-east-1",  True,  "EU_SCCs_2021"),
    ("AWS",           "unknown",    False, None),   # project-level question
    ("Google Cloud",  "unknown",    False, None),
    ("Azure",         "unknown",    False, None),
    ("Hetzner",       "eu-central", False, None),
    ("Mistral AI",    "eu-west-3",  False, None),
    ("Supabase",      "eu-central", False, None),   # self-hosted default
]


# ── ADR-082: Integration Catalog — Service nodes with category='integration' ─
# Source: ADR-082 § Graph Model. Each entry becomes a :Service node the
# dashboard renders as a Marketplace card. Keep the list curated and
# reviewed — ADR-082 § "Not in Scope" forbids silent/telemetry growth.
ADR_082_INTEGRATIONS: list[dict] = [
    {
        "name": "eRecht24",
        "subcategory": "legal_templates",
        "capabilities": ["imprint", "privacy_policy", "cookie_banner"],
        "required_credentials": ["api_key"],
        "config_schema_json": '{"domain":{"type":"string","required":true}}',
        "pricing_tier": "freemium",
        "documentation_url": "https://www.e-recht24.de/api",
        "region": "EU",
        "requires_scc": False,
        "country": "DEU",
        "country_source": "https://www.e-recht24.de/impressum.htm",
        "gdpr_adequate": True,
        "dpa_required": False,
    },
    {
        "name": "Firecrawl",
        "subcategory": "scraping",
        "capabilities": ["privacy_policy_extract", "imprint_extract"],
        "required_credentials": ["api_key"],
        "config_schema_json": "{}",
        "pricing_tier": "byok",
        "documentation_url": "https://firecrawl.dev",
        "region": "US",
        "requires_scc": True,
        "country": "USA",
        "country_source": "https://www.firecrawl.dev/privacy-policy",
        "gdpr_adequate": False,
        "dpa_required": True,
    },
    {
        "name": "Mistral AI EU",
        "subcategory": "llm",
        "capabilities": ["legal_reasoning", "translation"],
        "required_credentials": ["api_key"],
        "config_schema_json": "{}",
        "pricing_tier": "paid",
        "documentation_url": "https://docs.mistral.ai",
        "region": "EU",
        "requires_scc": False,
        "country": "FRA",
        "country_source": "https://legal.mistral.ai/legal-notice/",
        "gdpr_adequate": True,
        "dpa_required": False,
    },
    {
        "name": "Langfuse",
        "subcategory": "observability",
        "capabilities": ["llm_traces", "cost_tracking"],
        "required_credentials": ["public_key", "secret_key", "host"],
        "config_schema_json": "{}",
        "pricing_tier": "free",
        "documentation_url": "https://langfuse.com/docs",
        "region": "self-hosted",
        "requires_scc": False,
        "country": "DEU",
        "country_source": "https://langfuse.com/imprint",
        "gdpr_adequate": True,
        "dpa_required": False,
    },
    {
        "name": "GitHub",
        "subcategory": "repo_access",
        "capabilities": ["private_repo_clone"],
        "required_credentials": ["token"],
        "config_schema_json": "{}",
        "pricing_tier": "free",
        "documentation_url": "https://docs.github.com/en/rest",
        "region": "US",
        "requires_scc": True,
        "country": "USA",
        "country_source": "https://docs.github.com/en/site-policy/privacy-policies/github-privacy-statement",
        "gdpr_adequate": False,
        "dpa_required": True,
    },
    {
        "name": "Telegram",
        "subcategory": "notifications",
        "capabilities": ["scan_alerts", "doc_delivery"],
        "required_credentials": ["bot_token", "chat_id"],
        "config_schema_json": "{}",
        "pricing_tier": "free",
        "documentation_url": "https://core.telegram.org/bots/api",
        "region": "global",
        "requires_scc": True,
        "country": "BVI",
        "country_source": "https://telegram.org/privacy",
        "gdpr_adequate": False,
        "dpa_required": True,
    },
]


# ── Curated stub Service nodes — name + category + HAS_CATEGORY only ──────────
# ServiceCategory layer (ADR-061) provides Controls automatically.
STUB_SERVICES = [
    # (name, category, country, gdpr_adequate, dpa_required, ai_act_relevant)
    ("MongoDB",       "nosql_db",    "USA", False, True,  False),
    ("Braintree",     "payment",     "USA", False, True,  False),
    ("Segment",       "analytics",   "USA", False, True,  False),
    ("Amplitude",     "analytics",   "USA", False, True,  False),
    ("Mollie",        "payment",     "NLD", True,  True,  False),
    ("Replicate",     "ai_platform", "USA", False, True,  True),
    ("Chroma",        "vector_db",   "USA", False, True,  False),
    # ADR-072: Google OAuth / Expo intentionally NOT seeded as Service nodes —
    # Gemma4 classifies them by category (auth / baas) and controls flow via
    # ServiceCategory-[:SUBJECT_TO_CONTROL]->(Control). Prevents graph
    # pollution with LLM-derived company metadata.
]


ALLOWED_DATA_SUBJECTS: frozenset[str] = frozenset({
    "customers",
    "end_users",
    "employees",
    "website_visitors",
})

ALLOWED_LEGAL_BASIS: frozenset[str] = frozenset({
    "art_6_1_a_consent",
    "art_6_1_b_contract",
    "art_6_1_c_legal_obligation",
    "art_6_1_d_vital_interests",
    "art_6_1_e_public_task",
    "art_6_1_f_legitimate_interests",
    "art_9_2_special_category",
    "art_88_employment_context",
})


def _split_statements(cypher_text: str) -> list[str]:
    """Split a multi-statement Cypher file into individual statements.

    Splits on semicolons at end-of-line (own-line ';' or inline 'stmt;\\n'),
    so semicolons inside string literals (e.g. 'Anwendungsbereich; Grundsatz')
    are preserved correctly. Skips blank and comment-only blocks.
    """
    raw = re.split(r";\s*(?:\n|$)", cypher_text)
    stmts = []
    for block in raw:
        block = block.strip()
        non_comment_lines = [
            line for line in block.splitlines()
            if line.strip() and not line.strip().startswith("//")
        ]
        if non_comment_lines:
            stmts.append(block)
    return stmts


# ── ADR-130 D1/D3 — the layer manifest ────────────────────────────────────────
# EXPLICIT ordered lists, never a directory glob: resurrection safety is a
# LISTING property. The deseeded frameworks (ISO 27001 → ADR-120 BYOS, C5 →
# ADR-118, AIC4 → ADR-126 Phase 0.5) are unlistable by review — layers/byos/,
# the C5 and AIC4 layer files must NEVER appear here (guarded by
# tests/test_seed_layer_manifest.py). 14c_law_title_en_backfill stays out until
# Law.title_en gets a consumer (ADR-130 D1, KEPT-NOT-IN-MANIFEST).
#
# Phase 2 between these lists is the existing Python MODULES chain. The
# file-level dependency graph is cyclic (frameworks edges need eu_primary Laws;
# eu_primary CLASSIFIED_BY needs services_global RiskLevels; services_global
# REQUIRES edges need eu_primary DocumentTypes) — all files are idempotent, so
# a second pass of 00_services_global resolves the cycle deterministically.

LAYERS_DIR = Path(__file__).resolve().parents[1] / "src" / "graph" / "layers"

LAYERS_PHASE_0 = [
    "00_global/00_constraints.cypher",              # D6 — before any MERGE
]

LAYERS_PHASE_1 = [
    "00_global/00_services_global.cypher",          # Service/Country/RiskLevel/TransferMechanism
    "10_jurisdiction/eu/10_eu_primary.cypher",      # Law/DocumentType/UseCase/CLASSIFIED_BY
    "10_jurisdiction/eu/10_de.cypher",
    "00_global/00_frameworks.cypher",               # post-D2: OWASP+NIST+BSI only
    "00_global/00_services_global.cypher",          # 2nd pass — REQUIRES/VIOLATES edges land
]

LAYERS_PHASE_3 = [
    "00_global/00_tom_defaults.cypher",
    "00_global/01_bsi_basis_requirements_en.cypher",
    "10_jurisdiction/eu/11_data_subjects_normalize.cypher",
    "10_jurisdiction/eu/12_legal_basis_backfill.cypher",   # needs adr061 edges (Phase 2)
    "10_jurisdiction/eu/14a_law_dedup.cypher",             # before 14d (rename collision)
    "10_jurisdiction/eu/14b_law_minimal_metadata.cypher",
    "10_jurisdiction/eu/14d_law_cellar_sync.cypher",
]


def apply_layer(session, rel_path: str) -> str:
    """Execute one .cypher layer file statement-by-statement.

    A failed statement aborts the layer (and the run) — a half-applied
    foundation layer would make the Phase-2 modules MATCH nothing and
    no-op silently, which is exactly the failure class ADR-130 kills.
    """
    path = LAYERS_DIR / rel_path
    stmts = _split_statements(path.read_text(encoding="utf-8"))
    for i, stmt in enumerate(stmts, start=1):
        try:
            session.run(stmt).consume()
        except Exception as e:
            preview = " ".join(stmt.split())[:100]
            raise RuntimeError(
                f"layer {rel_path} failed at statement {i}/{len(stmts)}: {e} — '{preview}…'"
            ) from e
    return f"{len(stmts)} statements"


def validate_graph(session) -> list[str]:
    """Check graph consistency per ADR-100. Return list of error strings."""
    errors: list[str] = []

    # §4.1 — data_subjects on :Service nodes
    for row in session.run("MATCH (s:Service) RETURN s.name AS name, s.data_subjects AS ds"):
        ds = row["ds"]
        name = row["name"]
        if ds is None:
            errors.append(f"Service '{name}': data_subjects is null")
        elif not isinstance(ds, list):
            errors.append(f"Service '{name}': data_subjects must be list, got {type(ds).__name__}")
        else:
            unknown = set(ds) - ALLOWED_DATA_SUBJECTS
            if unknown:
                errors.append(f"Service '{name}': unknown data_subjects: {sorted(unknown)}")

    # §4.2 — legal_basis on SUBJECT_TO_CONTROL relationships
    for row in session.run(
        "MATCH ()-[r:SUBJECT_TO_CONTROL]->() RETURN r.legal_basis AS lb, elementId(r) AS rid"
    ):
        lb = row["lb"]
        rid = row["rid"]
        if not lb:
            errors.append(f"SUBJECT_TO_CONTROL rel elementId={rid}: legal_basis missing")
        elif lb not in ALLOWED_LEGAL_BASIS:
            errors.append(f"SUBJECT_TO_CONTROL rel elementId={rid}: unknown legal_basis '{lb}'")

    # §4.3 — every :UseCase must have exactly one [:CLASSIFIED_BY]->(:RiskLevel)
    for row in session.run("""
        MATCH (uc:UseCase)
        OPTIONAL MATCH (uc)-[r:CLASSIFIED_BY]->(:RiskLevel)
        WITH uc, count(r) AS rels
        WHERE rels <> 1
        RETURN uc.type AS type, rels AS classified_by_count
    """):
        errors.append(
            f"UseCase '{row['type']}': CLASSIFIED_BY count={row['classified_by_count']} (expected 1)"
        )

    # §4.4 — :Law node minimal metadata (ADR-100 Patch 14b)
    # article_title = short official heading (required, Patch 14b)
    # deadline_hours / retention_years = nullable by design (null removes property in Neo4j — not enforced)
    # note_de = rich explanation (optional, NOT enforced here — managed separately)
    for row in session.run(
        "MATCH (l:Law) RETURN l.name AS name, l.article AS article, "
        "l.article_title AS article_title"
    ):
        key = f"{row['name']}/{row['article']}"
        if not row["article_title"]:
            errors.append(f"Law {key}: article_title missing or empty")

    return errors


LOCAL_DEFAULT_URI = "bolt://localhost:7687"


def resolve_target_env(target: str) -> tuple[str, str, str, str]:
    """Resolve (uri, user, password, database) for a seed target.

    'local' (ADR-130 D4): NEO4J_LOCAL_URI or bolt://localhost:7687. The URI
    never falls back to the generic NEO4J_URI — that variable can point at a
    remote instance (it did: NucBox, ADR-119), and a 'local' run must not be
    silently redirectable. Username/password may fall back to the generic
    vars: a credential cannot redirect the write.

    'nuc' / 'aura': the historical NEO4J_{TARGET}_* convention, all required.
    """
    if target == "local":
        uri = os.getenv("NEO4J_LOCAL_URI") or LOCAL_DEFAULT_URI
        user = os.getenv("NEO4J_LOCAL_USERNAME") or os.getenv("NEO4J_USERNAME") or "neo4j"
        pwd = os.getenv("NEO4J_LOCAL_PASSWORD") or os.getenv("NEO4J_PASSWORD")
        if not pwd:
            raise ValueError(
                "No password for target 'local' — set NEO4J_LOCAL_PASSWORD or "
                "NEO4J_PASSWORD (docker/envs/.env, see .env.sovereign template)"
            )
        db = os.getenv("NEO4J_LOCAL_DATABASE", "neo4j")
        return uri, user, pwd, db
    prefix = f"NEO4J_{target.upper()}_"
    uri = os.getenv(f"{prefix}URI")
    user = os.getenv(f"{prefix}USERNAME")
    pwd = os.getenv(f"{prefix}PASSWORD")
    if not all([uri, user, pwd]):
        raise ValueError(f"Missing {prefix}* in .env for target '{target}'")
    return uri, user, pwd, os.getenv(f"{prefix}DATABASE", "neo4j")


def get_driver(target: str):
    """Return a Neo4j driver + database name for 'local', 'nuc' or 'aura'."""
    uri, user, pwd, db = resolve_target_env(target)
    return GraphDatabase.driver(uri, auth=(user, pwd)), db


def seed_adr061(session):
    """ServiceCategory nodes + HAS_CATEGORY + SUBJECT_TO_CONTROL + ai_llm TRIGGERS_FRAMEWORK.

    ADR-107: every node and every edge carries source/license/last_verified.
    """
    p = _prov_params(PROV_ADR061)

    for name, label, avv, drittland in CATEGORIES:
        session.run(
            "MERGE (sc:ServiceCategory {name:$n}) "
            "SET sc.label_de=$l, sc.requires_avv=$avv, sc.drittland_relevant=$dl"
            + _prov_node_set("sc"),
            n=name, l=label, avv=avv, dl=drittland, **p,
        )
    cats = session.run("MATCH (sc:ServiceCategory) RETURN count(sc) AS n").single()["n"]

    links = session.run(
        "MATCH (svc:Service), (sc:ServiceCategory {name: svc.category}) "
        "MERGE (svc)-[r:HAS_CATEGORY]->(sc) "
        "SET " + _prov_edge_set("r") + " "
        "RETURN count(*) AS n",
        **p,
    ).single()["n"]

    ok = 0
    for cat, cid, fw in CATEGORY_CONTROLS:
        r = session.run(
            "MATCH (sc:ServiceCategory {name: $cat}) "
            "MATCH (c:Control {id: $cid, framework: $fw}) "
            "MERGE (sc)-[r:SUBJECT_TO_CONTROL]->(c) "
            "SET " + _prov_edge_set("r") + " "
            "RETURN 1 AS ok",
            cat=cat, cid=cid, fw=fw, **p,
        ).single()
        if r:
            ok += 1

    triggers = 0
    for ai_cat in ["ai_llm", "ai_platform"]:
        r = session.run(
            "MATCH (sc:ServiceCategory {name: $cat}) "
            "MATCH (f:Control {framework:'OWASP_LLM_Top10'}) "
            "MERGE (sc)-[r:TRIGGERS_FRAMEWORK]->(f) "
            "SET " + _prov_edge_set("r") + " "
            "RETURN count(f) AS n",
            cat=ai_cat, **p,
        ).single()
        triggers += r["n"]

    return f"categories={cats}, has_category={links}, subject_to_control={ok}/{len(CATEGORY_CONTROLS)}, triggers_framework={triggers}"


def seed_adr066(session):
    """6 precise BSI nodes + upgrade mappings on ServiceCategory.

    ADR-107: source/license/last_verified on nodes + edges. PROV_ADR066 wins
    over the legacy `c.source = 'BSI IT-Grundschutz-Kompendium Edition 2023'`
    line (same value, normalized format).
    """
    p = _prov_params(PROV_ADR066)

    for cid, de, en in NEW_BSI:
        session.run(
            "MERGE (c:Control {id: $id, framework: 'BSI_Grundschutz'}) "
            "ON CREATE SET c.title_de=$de, c.title_en=$en, "
            "c.version='2023', c.confidence=1.0, c.copyright_cleared=false, "
            "c.copyright_note='BSI IT-Grundschutz — Titel frei, Volltext lizenzpflichtig'"
            + _prov_node_set("c") +
            " ON MATCH SET c.title_de=$de, c.title_en=$en"
            + _prov_node_set("c"),
            id=cid, de=de, en=en, **p,
        )
    total = session.run(
        "MATCH (c:Control {framework:'BSI_Grundschutz'}) RETURN count(c) AS n"
    ).single()["n"]

    up = 0
    for cats, cid in BSI_UPGRADES:
        r = session.run(
            "MATCH (sc:ServiceCategory) WHERE sc.name IN $cats "
            "MATCH (c:Control {id: $cid, framework: 'BSI_Grundschutz'}) "
            "MERGE (sc)-[r:SUBJECT_TO_CONTROL]->(c) "
            "SET " + _prov_edge_set("r") + " "
            "RETURN count(*) AS n",
            cats=cats, cid=cid, **p,
        ).single()
        up += r["n"]

    return f"bsi_total={total}, upgrade_edges={up}"


def seed_adr063(session):
    """OWASP -> ISO MAPS_TO with tom_section property. ADR-107: edge provenance."""
    p = _prov_params(PROV_ADR063)
    ok = 0
    for oid, fw, iid, tom in OWASP_MAPS:
        r = session.run(
            "MATCH (o:Control {id: $oid, framework: $fw}) "
            "MATCH (i:Control {id: $iid, framework: 'ISO_27001'}) "
            "MERGE (o)-[r:MAPS_TO]->(i) "
            "ON CREATE SET r.primary=true, r.tom_section=$tom, " + _prov_edge_set("r") + " "
            "ON MATCH  SET r.primary=true, r.tom_section=$tom, " + _prov_edge_set("r") + " "
            "RETURN 1 AS ok",
            oid=oid, fw=fw, iid=iid, tom=tom, **p,
        ).single()
        if r:
            ok += 1
    return f"maps_to={ok}/{len(OWASP_MAPS)}"


def seed_stubs(session):
    """Curated stub Service nodes — name + category + HAS_CATEGORY edge only.
    ServiceCategory layer provides Controls automatically (ADR-061).
    Return includes controls_via_category count for free verification.

    ADR-107: provenance on Service nodes + HAS_CATEGORY edges. Note: the legacy
    `s.source = 'curated_stub'` line is dropped in favor of standardized
    PROV_STUBS source string.
    """
    p = _prov_params(PROV_STUBS)
    ok = 0
    for name, category, country, gdpr_adequate, dpa_required, ai_act_relevant in STUB_SERVICES:
        session.run("""
            MERGE (s:Service {name: $name})
            ON CREATE SET
                s.category        = $category,
                s.country         = $country,
                s.gdpr_adequate   = $gdpr_adequate,
                s.dpa_required    = $dpa_required,
                s.ai_act_relevant = $ai_act_relevant"""
            + _prov_node_set("s") +
            """
            ON MATCH SET
                s.country         = $country,
                s.gdpr_adequate   = $gdpr_adequate,
                s.dpa_required    = $dpa_required,
                s.ai_act_relevant = $ai_act_relevant,
                s.last_seen       = datetime()"""
            + _prov_node_set("s") +
            """
            WITH s
            OPTIONAL MATCH (sc:ServiceCategory {name: $category})
            FOREACH (_ IN CASE WHEN sc IS NULL THEN [] ELSE [1] END |
                MERGE (s)-[r:HAS_CATEGORY]->(sc)
                ON CREATE SET """ + _prov_edge_set("r") + """
                ON MATCH SET """ + _prov_edge_set("r") + """
            )
        """, name=name, category=category, country=country,
             gdpr_adequate=gdpr_adequate, dpa_required=dpa_required,
             ai_act_relevant=ai_act_relevant, **p)
        ok += 1

    r = session.run("""
        MATCH (s:Service) WHERE s.source CONTAINS 'Service-Stubs' OR s.source = 'curated_stub'
        OPTIONAL MATCH (s)-[:HAS_CATEGORY]->()-[:SUBJECT_TO_CONTROL]->(c:Control)
        RETURN count(DISTINCT s) AS nodes, count(DISTINCT c) AS controls
    """).single()
    return f"stub_nodes={ok}/{len(STUB_SERVICES)} has_controls={r['controls']} across {r['nodes']} nodes"


def seed_adr075(session):
    """Service-Region + SCC-Mechanismus — ADR-075 § 5.

    Annotates existing Service nodes with default_region, requires_scc,
    scc_mechanism. MERGE is idempotent. Safe to re-run; no effect on
    other Service properties (category, country, dpa_required, etc).
    """
    p = _prov_params(PROV_ADR075)
    n = 0
    for name, region, requires_scc, mechanism in ADR_075_SCC:
        session.run(
            """
            MERGE (s:Service {name: $name})
            SET s.default_region = $region,
                s.requires_scc   = $requires_scc,
                s.scc_mechanism  = $mechanism"""
            + _prov_node_set("s"),
            name=name, region=region,
            requires_scc=requires_scc, mechanism=mechanism, **p,
        )
        n += 1
    return f"scc_annotated={n}/{len(ADR_075_SCC)}"


def seed_adr076(session):
    """HostingProvider curated list — ADR-076 § Graph-Schema-Erweiterung.

    MERGE on name, SET properties. Safe to re-run. HostingProvider is a new
    node type — no side effects on existing Service/Category/Control nodes.
    """
    p = _prov_params(PROV_ADR076)
    n = 0
    for name, soc2, iso, regions, scc in ADR_076_HOSTING:
        session.run(
            """
            MERGE (h:HostingProvider {name: $name})
            SET h.soc2                      = $soc2,
                h.iso27001                  = $iso,
                h.default_regions           = $regions,
                h.requires_scc_outside_eu   = $scc"""
            + _prov_node_set("h"),
            name=name, soc2=soc2, iso=iso, regions=regions, scc=scc, **p,
        )
        n += 1
    return f"hosting_providers={n}/{len(ADR_076_HOSTING)}"


def seed_adr082(session):
    """Integration Catalog — ADR-082 § Graph Model.

    Creates :Service nodes with category='integration'. The dashboard
    lists them as Marketplace cards; per-project wiring lives in the
    project_integrations Postgres table (ADR-082) with credentials in
    vault.secrets (ADR-083). Idempotent on name.

    Note: config_schema is stored as a JSON string. Neo4j cannot hold
    nested maps in properties; the backend parses it before serving.
    """
    p = _prov_params(PROV_ADR082)
    n = 0
    for itg in ADR_082_INTEGRATIONS:
        session.run(
            """
            MERGE (svc:Service {name: $name})
            SET svc.category             = 'integration',
                svc.subcategory          = $subcategory,
                svc.capabilities         = $capabilities,
                svc.required_credentials = $required_credentials,
                svc.config_schema        = $config_schema_json,
                svc.pricing_tier         = $pricing_tier,
                svc.documentation_url    = $documentation_url,
                svc.region               = $region,
                svc.requires_scc         = $requires_scc,
                svc.country              = $country,
                svc.country_source       = $country_source,
                svc.gdpr_adequate        = $gdpr_adequate,
                svc.dpa_required         = $dpa_required"""
            + _prov_node_set("svc"),
            **itg, **p,
        )
        n += 1
    return f"integrations={n}/{len(ADR_082_INTEGRATIONS)}"


# ── ADR-093 PR4 Minimal Content: DocumentType descriptions + Law nodes ─────────

ADR093_DOCTYPE_DESCRIPTIONS = [
    (
        "TOM",
        "Technisch-Organisatorische Maßnahmen (TOMs) sind konkrete Sicherheitsvorkehrungen, "
        "die ein Unternehmen laut Art. 32 DSGVO umsetzen muss, um personenbezogene Daten zu "
        "schützen. Typische Beispiele: Verschlüsselung, Zugriffskontrollen, Backups, "
        "Mitarbeiterschulungen, Sicherheitsrichtlinien. TOMs müssen dem Stand der Technik "
        "entsprechen und regelmäßig überprüft werden.",
    ),
    (
        "AVV",
        "Ein Auftragsverarbeitungsvertrag (AVV) ist ein Vertrag, den Unternehmen nach Art. 28 "
        "DSGVO mit jedem Dienstleister abschließen müssen, der im Auftrag personenbezogene Daten "
        "verarbeitet. Typische Beispiele: Cloud-Anbieter, E-Mail-Dienste, SaaS-Tools, "
        "Zahlungsdienstleister. Der AVV legt fest, was der Auftragsverarbeiter mit den Daten tun "
        "darf und welche Schutzmaßnahmen er einhalten muss.",
    ),
    (
        "VVT",
        "Das Verzeichnis von Verarbeitungstätigkeiten (VVT) ist eine interne Dokumentation, die "
        "Art. 30 DSGVO vorschreibt. Es erfasst alle Datenverarbeitungen im Unternehmen: welche "
        "Daten werden verarbeitet, zu welchem Zweck, wer hat Zugriff, wie lange werden sie "
        "gespeichert, welche Rechtsgrundlage gilt. Das VVT ist Pflicht für Unternehmen mit mehr "
        "als 250 Mitarbeitern oder bei risikoreicher Verarbeitung.",
    ),
    (
        "DSFA",
        "Eine Datenschutz-Folgenabschätzung (DSFA) ist eine Risikoanalyse nach Art. 35 DSGVO, "
        "die vor dem Start risikoreicher Datenverarbeitungen durchgeführt werden muss. Typische "
        "Auslöser: KI-Systeme zur Profilbildung, biometrische Daten, automatisierte "
        "Entscheidungen, Tracking auf großem Maßstab. Das Ergebnis ist eine Risikobeurteilung "
        "und ein Maßnahmenplan.",
    ),
    (
        "SCC",
        "Standardvertragsklauseln (SCCs) sind von der EU-Kommission genehmigte Vertragsvorlagen "
        "für Datentransfers in Drittländer außerhalb der EU/EWR (Art. 46 DSGVO). Sie sind "
        "notwendig, wenn kein Angemessenheitsbeschluss existiert — z.B. bei US-Diensten wie "
        "AWS, Google, Stripe oder Postmark. Die SCCs 2021 sind die aktuelle Version.",
    ),
    (
        "KI_Policy",
        "Eine KI-Nutzungsrichtlinie (KI-Policy) ist eine interne Regelung, wie Mitarbeitende "
        "KI-Systeme einsetzen dürfen. Sie schafft die nach EU-AI-Act Art. 4 geforderte "
        "KI-Kompetenz und regelt: welche KI-Tools erlaubt sind, welche Daten eingegeben werden "
        "dürfen, wer für KI-Ergebnisse verantwortlich ist, wie mit Fehlern umgegangen wird. "
        "Schützt vor unkontrolliertem KI-Einsatz und Datenschutzverstößen.",
    ),
    (
        "AI_Act_Manifest",
        "Das EU-AI-Act-Manifest dokumentiert, wie ein KI-System die Anforderungen der "
        "EU-KI-Verordnung (VO 2024/1689) erfüllt. Es ordnet das System einer Risikoklasse zu "
        "(minimal, begrenzt, hoch) und hält die daraus folgenden Pflichten fest. Typische "
        "Auslöser: KI zur Bewertung von Personen, automatisierte Entscheidungen, generative KI. "
        "Grundlage, um gegenüber Behörden und Kunden regelkonformen KI-Einsatz nachzuweisen.",
    ),
    (
        "KI_System_Dokumentation",
        "Die KI-System-Dokumentation beschreibt ein KI-System technisch und organisatorisch: "
        "Zweck, Funktionsweise, verwendete Daten, bekannte Grenzen und Risiken. Der EU-AI-Act "
        "verlangt sie insbesondere für Hochrisiko-Systeme (Art. 11). Typische Inhalte: welches "
        "Modell, womit trainiert, wie Ergebnisse überprüft werden, welche menschliche Aufsicht. "
        "Grundlage für Audits.",
    ),
]

ADR093_LAW_NODES = [
    {
        "name": "DSGVO",
        "article": "5",
        "title_de": "Grundsätze für die Verarbeitung personenbezogener Daten",
        "regulation": "DSGVO",
        "note_de": (
            "Art. 5 DSGVO nennt die sieben Grundsätze der Datenverarbeitung: "
            "(1) Rechtmäßigkeit, Verarbeitung nach Treu und Glauben, Transparenz — "
            "Daten dürfen nur mit klarer Rechtsgrundlage (Art. 6) verarbeitet werden. "
            "(2) Zweckbindung — Daten dürfen nur für den angegebenen Zweck genutzt werden. "
            "(3) Datenminsimierung — nur notwendige Daten erheben. "
            "(4) Richtigkeit — Daten müssen korrekt und aktuell sein. "
            "(5) Speicherbegrenzung — keine unbegrenzte Aufbewahrung. "
            "(6) Integrität und Vertraulichkeit — Schutz durch TOMs (Art. 32). "
            "(7) Rechenschaftspflicht — der Verantwortliche muss die Einhaltung nachweisen können."
        ),
    },
    {
        "name": "DSGVO",
        "article": "6",
        "title_de": "Rechtmäßigkeit der Verarbeitung",
        "regulation": "DSGVO",
        "note_de": (
            "Art. 6 DSGVO listet die sechs Rechtsgrundlagen für die Verarbeitung "
            "personenbezogener Daten: (a) Einwilligung der betroffenen Person, "
            "(b) Vertragserfüllung, (c) gesetzliche Verpflichtung, (d) lebenswichtige "
            "Interessen, (e) öffentliches Interesse / hoheitliche Gewalt, "
            "(f) berechtigte Interessen des Verantwortlichen. Ohne eine dieser Grundlagen "
            "ist die Verarbeitung rechtswidrig. Für Softwareunternehmen relevant: "
            "überwiegend (a) Einwilligung, (b) Vertrag und (f) berechtigte Interessen."
        ),
    },
    {
        "name": "DSGVO",
        "article": "7",
        "title_de": "Bedingungen für die Einwilligung",
        "regulation": "DSGVO",
        "note_de": (
            "Art. 7 DSGVO regelt, wann eine Einwilligung wirksam ist: Sie muss freiwillig, "
            "spezifisch, informiert und unmissverständlich sein. Der Verantwortliche muss die "
            "Einwilligung nachweisen können. Die betroffene Person kann jederzeit widerrufen. "
            "Cookie-Banner, Newsletter-Anmeldungen und Tracking-Einwilligungen müssen diese "
            "Anforderungen erfüllen. Vorausgefüllte Checkboxen oder 'weiter = einverstanden' "
            "sind nicht zulässig."
        ),
    },
    {
        "name": "DSGVO",
        "article": "35",
        "title_de": "Datenschutz-Folgenabschätzung",
        "regulation": "DSGVO",
        "note_de": (
            "Art. 35 DSGVO verpflichtet Unternehmen, vor risikoreichen Verarbeitungen eine "
            "Datenschutz-Folgenabschätzung (DSFA) durchzuführen. Pflicht besteht bei: "
            "systematischer Profilbildung (z.B. Scoring, Segmentierung), Verarbeitung "
            "besonderer Kategorien (Gesundheit, Biometrie, politische Meinungen) auf großem "
            "Maßstab, systematischer Überwachung, KI-gestützten Entscheidungen mit "
            "erheblichen Auswirkungen. Der Verantwortliche muss Risiken bewerten und "
            "Maßnahmen dokumentieren. Bei hohem Restrisiko: vorherige Konsultation der "
            "Aufsichtsbehörde (Art. 36)."
        ),
    },
    {
        "name": "NIS2",
        "article": "Überblick",
        "title_de": "NIS2-Richtlinie — Netz- und Informationssicherheit",
        # Official EN directive title (CELEX 32022L2555) — ADR-126 Addendum 1b, durable.
        "title_en": (
            "Directive (EU) 2022/2555 of the European Parliament and of the Council of "
            "14 December 2022 on measures for a high common level of cybersecurity across "
            "the Union, amending Regulation (EU) No 910/2014 and Directive (EU) 2018/1972, "
            "and repealing Directive (EU) 2016/1148 (NIS 2 Directive)"
        ),
        "regulation": "NIS2",
        "note_de": (
            "Die NIS2-Richtlinie (EU 2022/2555) ist die überarbeitete EU-Richtlinie zur "
            "Netz- und Informationssicherheit. Sie gilt ab Oktober 2024 für 'wesentliche' "
            "und 'wichtige' Einrichtungen in 18 Sektoren (u.a. Energie, Gesundheit, "
            "digitale Infrastruktur, Cloud-Dienste, Managed Services). "
            "Anforderungen: Risikomanagement, Meldepflichten bei Sicherheitsvorfällen "
            "(24h Frühwarnung, 72h vollständige Meldung), Lieferkettensicherheit, "
            "Verschlüsselung, Zugriffskontrolle. Bußgelder: bis zu 10 Mio. EUR oder "
            "2 % des weltweiten Umsatzes für wesentliche Einrichtungen."
        ),
    },
]


def seed_adr093(session):
    """PR4 Minimal Content: DocumentType.description_de + 4 DSGVO + 1 NIS2 Law nodes.

    ADR-107: provenance on DocumentType (SET description_de) + Law nodes.
    """
    p = _prov_params(PROV_ADR093)

    dt_ok = 0
    for dtype, desc in ADR093_DOCTYPE_DESCRIPTIONS:
        session.run(
            "MATCH (d:DocumentType {type: $type}) "
            "SET d.description_de = $desc"
            + _prov_node_set("d"),
            type=dtype, desc=desc, **p,
        )
        dt_ok += 1

    law_ok = 0
    for law in ADR093_LAW_NODES:
        # ON CREATE: full provenance for genuinely new nodes. ON MATCH: only note_de +
        # last_verified — the bare-number canonicals (ADR-126 Addendum 1b re-keyed these
        # from "Art. N" to "N") already carry richer provenance (CELEX source, title_en,
        # source_url_en); do not clobber it. note_de stays the Lex-authored Erläuterung.
        # title_en optional per entry (only NIS2 Überblick carries one — official CELEX
        # directive title). coalesce keeps the canonical's existing title_en for the
        # bare-number DSGVO entries (which have no title_en key -> None -> no clobber).
        session.run(
            """
            MERGE (l:Law {name: $name, article: $article})
            ON CREATE SET l.title_de   = $title_de,
                          l.regulation = $regulation,
                          l.note_de    = $note_de,
                          l.title_en   = coalesce($title_en, l.title_en)"""
            + _prov_node_set("l")
            + """
            ON MATCH SET l.note_de = $note_de,
                         l.title_en = coalesce($title_en, l.title_en),
                         l.last_verified = date($_p_last_verified)""",
            name=law["name"],
            article=law["article"],
            title_de=law["title_de"],
            regulation=law["regulation"],
            note_de=law["note_de"],
            title_en=law.get("title_en"),
            **p,
        )
        law_ok += 1

    total_laws = session.run("MATCH (l:Law) RETURN count(l) AS n").single()["n"]
    return f"doctype_descriptions={dt_ok}, law_nodes_merged={law_ok}, total_laws={total_laws}"


# ── ADR-106 PR B1: GPAI Flags + provider_obligations ─────────────────────────

# "Mistral AI EU" intentionally excluded: it is a catalog stub (ADR-082 Marketplace),
# NOT a compliance service. GPAI/provider_obligations belong on "Mistral AI" (ai_llm).
GPAI_SERVICES = ["OpenAI", "Anthropic", "Mistral AI"]
GPAI_OBLIGATIONS = [
    "Art. 53(1)(a) Technische Dokumentation",
    "Art. 53(1)(b) Trainings-Summary (Public)",
    "Art. 53(1)(c) Copyright-Compliance-Policy",
    "Art. 53(1)(d) EU-Vertreter benennen (für Anbieter aus Drittländern)",
]


def seed_pr_b1_gpai(session):
    """ADR-106 PR B1: tag 4 LLM services with is_gpai + provider_obligations."""
    p = _prov_params(PROV_PR_B1_GPAI)
    n = 0
    for name in GPAI_SERVICES:
        r = session.run(
            "MATCH (s:Service {name: $name}) "
            "SET s.is_gpai = true, s.provider_obligations = $oblig"
            + _prov_node_set("s") +
            " RETURN s.name AS name",
            name=name, oblig=GPAI_OBLIGATIONS, **p,
        ).single()
        if r:
            n += 1
    return f"gpai_tagged={n}/{len(GPAI_SERVICES)}"


# ── ADR-106 PR B2: data_categories backfill for 12 services ──────────────────
#
# Curated from each service's public DPA + service-type-typical data. Each
# entry: (service_name, [data_categories]).
SERVICE_DATA_CATEGORIES = [
    ("Amplitude", ["Event-Daten", "Nutzer-IDs", "Session-Daten", "Nutzungsverhalten", "Gerätedaten", "IP-Adressen"]),
    ("Chroma", ["Embedding-Vektoren", "Indizierte Dokumente", "ggf. personenbezogene Inhalte"]),
    ("Firecrawl", ["Crawled-Webinhalte", "URLs", "ggf. personenbezogene Inhalte aus Web-Quellen"]),
    ("Google Cloud Authentication", ["E-Mail-Adressen", "OAuth-Tokens", "Authentifizierungs-Metadaten", "IP-Adressen"]),
    ("HashiCorp Vault", ["Verschlüsselte Secrets", "Audit-Logs", "Zugriffs-Metadaten"]),
    # "Mistral AI EU" excluded — catalog stub (ADR-082), not a scanned compliance service.
    ("Mollie", ["Zahlungsdaten", "Kreditkartendaten (tokenisiert)", "Rechnungsadressen", "Transaktionsdaten"]),
    ("MongoDB", ["Anwendungsdaten", "Datenbankinhalt", "Logs"]),
    ("Replicate", ["API-Anfragen", "Modell-Inputs und -Outputs", "ggf. personenbezogene Inhalte in Prompts"]),
    ("Slack", ["Nachrichteninhalte", "Nutzer-IDs", "E-Mail-Adressen", "Dateianhänge", "Workspace-Metadaten"]),
    ("Telegram", ["Nachrichteninhalte", "Telefonnummern", "Nutzer-IDs", "Chat-Metadaten"]),
    ("eRecht24", ["API-Anfragen", "Unternehmensdaten", "Konfigurationsparameter"]),
]


def seed_pr_b2_data_categories(session):
    """ADR-106 PR B2: backfill data_categories for 12 services missing them."""
    p = _prov_params(PROV_PR_B2_DATACAT)
    n = 0
    for name, cats in SERVICE_DATA_CATEGORIES:
        r = session.run(
            "MATCH (s:Service {name: $name}) "
            "SET s.data_categories = $cats"
            + _prov_node_set("s") +
            " RETURN s.name AS name",
            name=name, cats=cats, **p,
        ).single()
        if r:
            n += 1
    return f"data_categories_backfilled={n}/{len(SERVICE_DATA_CATEGORIES)}"


# ── ADR-106 PR C.1 Cleanup: data_subjects backfill (3 services) ──────────────

# Values MUST come from the §4.1 allowlist (ALLOWED_DATA_SUBJECTS) — the German
# originals ("Endnutzer", "Verantwortliche", …) made every full seed re-write
# validator-red state (found 2026-07-14, Nachschlag B).
SERVICE_DATA_SUBJECTS = [
    ("Chroma",   ["end_users"]),  # vector DB for RAG over application data
    ("MongoDB",  ["end_users"]),  # general application DB
    ("eRecht24", ["employees"]),  # B2B compliance tool — users are the controller's staff
]


def seed_pr_c1_5_data_subjects(session):
    """ADR-106 PR C.1 Cleanup: backfill data_subjects for 3 services missing them.

    Uses PROV_PR_B2_DATACAT — same provenance bucket as data_categories backfill
    since both are curated from service-type-typical Betroffenenkategorien.
    """
    p = _prov_params(PROV_PR_B2_DATACAT)
    n = 0
    for name, subjects in SERVICE_DATA_SUBJECTS:
        r = session.run(
            "MATCH (s:Service {name: $name}) "
            "SET s.data_subjects = $subjects"
            + _prov_node_set("s") +
            " RETURN s.name AS name",
            name=name, subjects=subjects, **p,
        ).single()
        if r:
            n += 1
    return f"data_subjects_backfilled={n}/{len(SERVICE_DATA_SUBJECTS)}"


# ── ADR-106 PR D1: SDM Measure-Layer (~63 measures, SDM v3.1 D1.1–D1.7) ──────
#
# Tuple format: (mid, name_de, goal_ids[], req_b_ids[], tom_section)
# goal_ids: ProtectionGoal.id from PR C1 (dm/vf/ig/vt/nn/tp/iv)
# req_b_ids: Requirement_B.id from PR C2 (B1.x / B2 / B3)
# tom_section: maps to one of TOM_SECTION_ORDER strings used by tom_builder
SDM_MEASURES = [
    # D1.1 Verfügbarkeit (Vf)
    ("d1.1-backup-konzept",            "Sicherheitskopien gemäß getestetem Konzept (Daten, Prozesszustände, Konfigurationen, Datenstrukturen)",                                                                                    ["vf"],            ["B1.20"],                  "3.1 Verfügbarkeitskontrolle"),
    ("d1.1-schutz-aeussere-einfluesse","Schutz vor äußeren Einflüssen (Schadsoftware, Sabotage, höhere Gewalt)",                                                                                                                  ["vf"],            ["B1.18", "B1.19", "B1.22"], "3.1 Verfügbarkeitskontrolle"),
    ("d1.1-dokumentation-syntax",      "Dokumentation der Syntax der Daten",                                                                                                                                                      ["vf"],            ["B1.18", "B1.20"],         "3.1 Verfügbarkeitskontrolle"),
    ("d1.1-redundanz",                 "Redundanz von Hard- und Software sowie Infrastruktur",                                                                                                                                    ["vf"],            ["B1.20", "B1.19"],         "3.1 Verfügbarkeitskontrolle"),
    ("d1.1-reparatur-ausweich",        "Umsetzung von Reparaturstrategien und Ausweichprozessen",                                                                                                                                ["vf"],            ["B1.19", "B1.20", "B1.22"], "3.1 Verfügbarkeitskontrolle"),
    ("d1.1-notfallkonzept",            "Erstellung eines Notfallkonzepts zur Wiederherstellung einer Verarbeitungstätigkeit",                                                                                                    ["vf"],            ["B1.19", "B1.20"],         "4.2 Incident-Response-Management"),
    ("d1.1-vertretungsregeln",         "Vertretungsregelungen für abwesende Mitarbeitende",                                                                                                                                       ["vf"],            ["B1.18"],                  "3.1 Verfügbarkeitskontrolle"),
    # D1.2 Integrität (Ig)
    ("d1.2-schreib-aenderungsrechte",  "Einschränkung von Schreib- und Änderungsrechten",                                                                                                                                         ["ig"],            ["B1.6"],                   "1.3 Zugriffskontrolle"),
    ("d1.2-pruefsummen-signaturen",    "Einsatz von Prüfsummen, elektronischen Siegeln und Signaturen gemäß Kryptokonzept",                                                                                                      ["ig"],            ["B1.6", "B1.4", "B1.23", "B1.22"], "1.5 Pseudonymisierung"),
    ("d1.2-berechtigungen-rollen",     "Dokumentierte Zuweisung von Berechtigungen und Rollen",                                                                                                                                  ["ig", "vt"],     ["B1.6", "B1.7"],           "1.3 Zugriffskontrolle"),
    ("d1.2-loeschen-berichtigen",      "Löschen oder Berichtigen falscher Daten",                                                                                                                                                ["ig"],            ["B1.4"],                   "4.1 Datenschutz-Maßnahmen"),
    ("d1.2-haerten-systeme",           "Härten von IT-Systemen (Reduktion unnötiger Nebenfunktionalitäten)",                                                                                                                     ["ig"],            ["B1.6", "B1.19"],          "1.2 Zugangskontrolle"),
    ("d1.2-aktualitaet-prozesse",      "Prozesse zur Aufrechterhaltung der Aktualität von Daten",                                                                                                                                ["ig"],            ["B1.4"],                   "4.1 Datenschutz-Maßnahmen"),
    ("d1.2-id-auth-personen-geraete",  "Prozesse zur Identifizierung und Authentifizierung von Personen und Gerätschaften",                                                                                                      ["ig"],            ["B1.6", "B1.9"],           "1.2 Zugangskontrolle"),
    ("d1.2-sollverhalten-tests",       "Festlegung des Sollverhaltens von Prozessen und regelmäßige Funktionstests",                                                                                                             ["ig"],            ["B1.6", "B1.16", "B1.19"], "4.1 Datenschutz-Maßnahmen"),
    ("d1.2-sollverhalten-ablaeufe",    "Festlegung des Sollverhaltens von Abläufen und Tests zur Feststellung von Ist-Zuständen",                                                                                                ["ig"],            ["B1.6", "B1.16", "B1.23", "B1.19"], "4.1 Datenschutz-Maßnahmen"),
    ("d1.2-schutz-spionage-hacking",   "Schutz vor äußeren Einflüssen (Spionage, Hacking)",                                                                                                                                       ["ig"],            ["B1.6", "B1.19", "B1.22"], "2.1 Weitergabekontrolle"),
    # D1.3 Vertraulichkeit (Vt)
    ("d1.3-berechtigungs-rollenkonz",  "Festlegung eines Berechtigungs- und Rollenkonzeptes nach Erforderlichkeitsprinzip",                                                                                                      ["vt"],            ["B1.7"],                   "1.3 Zugriffskontrolle"),
    ("d1.3-auth-verfahren",            "Implementierung eines sicheren Authentifizierungsverfahrens",                                                                                                                             ["vt"],            ["B1.7", "B1.9"],           "1.2 Zugangskontrolle"),
    ("d1.3-personalkraft-eingrenzung", "Eingrenzung zulässiger Personalkräfte auf nachprüfbar zuständige und befähigte (ggf. sicherheitsüberprüft) ohne Interessenkonflikte",                                                    ["vt"],            ["B1.7"],                   "1.1 Zutrittskontrolle"),
    ("d1.3-kontrolle-kanaele",         "Festlegung und Kontrolle der Nutzung zugelassener Ressourcen, insbesondere Kommunikationskanäle",                                                                                        ["vt"],            ["B1.7", "B1.22"],          "2.1 Weitergabekontrolle"),
    ("d1.3-spezifizierte-umgebungen",  "Spezifizierte, für die Verarbeitungstätigkeit ausgestattete Umgebungen (Gebäude, Räume)",                                                                                                ["vt"],            ["B1.7"],                   "1.1 Zutrittskontrolle"),
    ("d1.3-org-ablaeufe-verpflicht",   "Festlegung organisatorischer Abläufe, Verpflichtung auf Datengeheimnis, Verschwiegenheitsvereinbarungen",                                                                                ["vt"],            ["B1.7", "B1.22"],          "4.4 Auftragskontrolle"),
    ("d1.3-verschluesselung-krypto",   "Verschlüsselung gespeicherter und transferierter Daten + Kryptokonzept",                                                                                                                  ["vt"],            ["B1.7"],                   "1.5 Pseudonymisierung"),
    # D1.4 Nichtverkettung (Nn)
    ("d1.4-rechte-einschraenkung",     "Einschränkung von Verarbeitungs-, Nutzungs- und Übermittlungsrechten",                                                                                                                   ["nn"],            ["B1.2"],                   "1.4 Trennungskontrolle"),
    ("d1.4-schnittstellen-schliessen", "Programmtechnische Unterlassung bzw. Schließung von Schnittstellen",                                                                                                                     ["nn"],            ["B1.2"],                   "1.4 Trennungskontrolle"),
    ("d1.4-backdoor-verbot",           "Regelnde Maßgaben zum Verbot von Backdoors und qualitätssichernde Revisionen bei Softwareentwicklung",                                                                                   ["nn"],            ["B1.2"],                   "1.4 Trennungskontrolle"),
    ("d1.4-trennung-org-grenzen",      "Trennung nach Organisations-/Abteilungsgrenzen",                                                                                                                                          ["nn"],            ["B1.2"],                   "1.4 Trennungskontrolle"),
    ("d1.4-rollen-zugriffs",           "Trennung mittels Rollenkonzepten mit abgestuften Zugriffsrechten (Identitätsmanagement + sichere Authentifizierung)",                                                                    ["nn"],            ["B1.2"],                   "1.4 Trennungskontrolle"),
    ("d1.4-nutzerkontrollierte-id",    "Zulassung von nutzerkontrolliertem Identitätsmanagement",                                                                                                                                 ["nn"],            ["B1.2"],                   "1.4 Trennungskontrolle"),
    ("d1.4-pseudonyme-anon",           "Einsatz zweckspezifischer Pseudonyme, Anonymisierungsdienste, anonymer Credentials",                                                                                                      ["nn", "dm"],     ["B1.2", "B1.3"],           "1.5 Pseudonymisierung"),
    ("d1.4-zweckaenderungsverfahren",  "Geregelte Zweckänderungsverfahren",                                                                                                                                                       ["nn"],            ["B1.2"],                   "1.4 Trennungskontrolle"),
    # D1.5 Transparenz (Tp)
    ("d1.5-dok-inventarisierung",      "Dokumentation/Inventarisierung aller Verarbeitungstätigkeiten gemäß Art. 30 DSGVO",                                                                                                      ["tp"],            ["B1.8"],                   "4.1 Datenschutz-Maßnahmen"),
    ("d1.5-dok-bestandteile",          "Dokumentation der Bestandteile (Geschäftsprozesse, Datenbestände, Datenflüsse, IT-Systeme, Betriebsabläufe)",                                                                            ["tp"],            ["B1.8"],                   "4.1 Datenschutz-Maßnahmen"),
    ("d1.5-dok-tests-freigabe",        "Dokumentation von Tests, der Freigabe und ggf. der DSFA",                                                                                                                                 ["tp"],            ["B1.8"],                   "4.1 Datenschutz-Maßnahmen"),
    ("d1.5-dok-profiling",             "Dokumentation der Faktoren für Profiling, Scoring oder teilautomatisierte Entscheidungen",                                                                                                ["tp"],            ["B1.8"],                   "4.1 Datenschutz-Maßnahmen"),
    ("d1.5-dok-vertraege-zustaend",    "Dokumentation der Verträge, Geschäftsverteilungspläne, Zuständigkeitsregelungen",                                                                                                          ["tp"],            ["B1.8"],                   "4.1 Datenschutz-Maßnahmen"),
    ("d1.5-dok-einwilligungen",        "Dokumentation von Einwilligungen, deren Widerruf sowie Widersprüche",                                                                                                                     ["tp"],            ["B2"],                     "4.1 Datenschutz-Maßnahmen"),
    ("d1.5-protokoll-zugriffe",        "Protokollierung von Zugriffen und Änderungen",                                                                                                                                            ["tp"],            ["B1.23", "B1.8"],          "2.2 Eingangskontrolle"),
    ("d1.5-versionierung",             "Versionierung",                                                                                                                                                                            ["tp"],            ["B1.23", "B1.8"],          "4.1 Datenschutz-Maßnahmen"),
    ("d1.5-protokoll-konzept",         "Dokumentation der Verarbeitungsprozesse mittels Protokollen auf Basis eines Protokollierungs- und Auswertungskonzepts",                                                                  ["tp"],            ["B1.23", "B1.8"],          "2.2 Eingangskontrolle"),
    ("d1.5-dok-quellen-pannen",        "Dokumentation der Datenquellen + Umsetzung der Informationspflichten gegenüber Betroffenen + Datenpannen-Umgang",                                                                         ["tp"],            ["B1.1", "B1.8"],           "4.1 Datenschutz-Maßnahmen"),
    ("d1.5-benachrichtigung-pannen",   "Benachrichtigung von Betroffenen bei Datenpannen oder bei Weiterverarbeitungen zu einem anderen Zweck",                                                                                  ["tp"],            ["B1.1"],                   "4.2 Incident-Response-Management"),
    ("d1.5-nachverfolgbarkeit-rechte", "Nachverfolgbarkeit der Aktivitäten zur Gewährung der Betroffenenrechte",                                                                                                                  ["tp"],            ["B1.1"],                   "4.1 Datenschutz-Maßnahmen"),
    ("d1.5-info-betroffene",           "Bereitstellung von Informationen über die Verarbeitung an Betroffene",                                                                                                                    ["tp"],            ["B1.1"],                   "4.1 Datenschutz-Maßnahmen"),
    # D1.6 Intervenierbarkeit (Iv)
    ("d1.6-einwilligung-widerruf",     "Maßnahmen für differenzierte Einwilligungs-, Rücknahme- sowie Widerspruchsmöglichkeiten",                                                                                                ["iv"],            ["B2"],                     "4.1 Datenschutz-Maßnahmen"),
    ("d1.6-sperrkennzeichen-felder",   "Schaffung notwendiger Datenfelder (Sperrkennzeichen, Benachrichtigungen, Einwilligungen, Widersprüche, Gegendarstellungen)",                                                              ["iv"],            ["B1.11", "B1.13", "B1.17", "B2", "B3"], "4.1 Datenschutz-Maßnahmen"),
    ("d1.6-dok-aenderungen",           "Dokumentierte Bearbeitung von Störungen, Problembearbeitungen und Änderungen an Verarbeitungstätigkeiten + TOMs",                                                                         ["iv"],            ["B1.22", "B1.13", "B3"],   "4.2 Incident-Response-Management"),
    ("d1.6-deaktivierung-funktion",    "Deaktivierungsmöglichkeit einzelner Funktionalitäten ohne Mitleidenschaft für das Gesamtsystem",                                                                                          ["iv"],            ["B1.22", "B1.13", "B3"],   "4.3 Privacy by Design"),
    ("d1.6-standard-abfrage-iface",   "Implementierung standardisierter Abfrage- und Dialogschnittstellen für Betroffenenrechte",                                                                                                ["iv"],            ["B1.10"],                  "4.1 Datenschutz-Maßnahmen"),
    ("d1.6-export-iface",              "Betreiben einer Schnittstelle für strukturierte, maschinenlesbare Daten zum Abruf durch Betroffene",                                                                                      ["iv"],            ["B1.10", "B1.14"],         "4.1 Datenschutz-Maßnahmen"),
    ("d1.6-id-auth-betroffene",        "Identifizierung und Authentifizierung der Personen, die Betroffenenrechte wahrnehmen möchten",                                                                                            ["iv"],            ["B1.9"],                   "1.2 Zugangskontrolle"),
    ("d1.6-spoc",                      "Einrichtung eines Single Point of Contact (SPoC) für Betroffene",                                                                                                                          ["iv"],            ["B1.10"],                  "4.1 Datenschutz-Maßnahmen"),
    ("d1.6-zusammenstellung-loesch",   "Operative Möglichkeit zur Zusammenstellung, konsistenten Berichtigung, Sperrung und Löschung aller Daten pro Person",                                                                     ["iv"],            ["B1.11", "B1.12", "B1.13", "B1.14", "B3"], "4.1 Datenschutz-Maßnahmen"),
    ("d1.6-optionen-betroffene",       "Bereitstellen von Optionen für Betroffene, um Programme datenschutzgerecht einstellen zu können",                                                                                         ["iv"],            ["B1.10", "B1.17"],         "4.3 Privacy by Design"),
    # D1.7 Datenminimierung (Dm)
    ("d1.7-attribute-reduktion",       "Reduzierung von erfassten Attributen der betroffenen Personen",                                                                                                                            ["dm"],            ["B1.3"],                   "4.3 Privacy by Design"),
    ("d1.7-verarbeitungsoptionen",     "Reduzierung der Verarbeitungsoptionen in Verarbeitungsprozessschritten",                                                                                                                  ["dm"],            ["B1.3"],                   "4.3 Privacy by Design"),
    ("d1.7-kenntnisnahme-reduktion",   "Reduzierung von Möglichkeiten der Kenntnisnahme vorhandener Daten",                                                                                                                       ["dm"],            ["B1.3"],                   "1.3 Zugriffskontrolle"),
    ("d1.7-voreinstellungen-personen", "Festlegung von Voreinstellungen für betroffene Personen (Beschränkung auf erforderliches Maß)",                                                                                          ["dm"],            ["B1.17"],                  "4.3 Privacy by Design"),
    ("d1.7-bevorzugung-automatisiert", "Bevorzugung automatisierter Verarbeitungsprozesse (Datenkenntnisnahme entbehrlich) gegenüber dialoggesteuerten",                                                                          ["dm"],            ["B1.3"],                   "4.3 Privacy by Design"),
    ("d1.7-datenmasken-pseudo",        "Implementierung von Datenmasken, automatischer Sperr-/Löschroutinen, Pseudonymisierungs-/Anonymisierungsverfahren",                                                                       ["dm"],            ["B1.3", "B1.5"],           "1.5 Pseudonymisierung"),
    ("d1.7-loeschkonzept",             "Festlegung und Umsetzung eines Löschkonzepts",                                                                                                                                             ["dm"],            ["B1.5"],                   "4.4 Auftragskontrolle"),
    ("d1.7-prozess-aenderungen-kontr", "Regelungen zur Kontrolle von Prozessen zur Änderung von Verarbeitungstätigkeiten",                                                                                                        ["dm"],            ["B1.3"],                   "4.1 Datenschutz-Maßnahmen"),
]


def seed_pr_d1_measures(session):
    """ADR-106 PR D1+D2: 63 Measure nodes from SDM v3.1 D1.1-D1.7 with multi-tag
    ADDRESSES→ProtectionGoal + IMPLEMENTS→Requirement_B edges + tom_section property.
    """
    p = _prov_params(PROV_PR_C_SDM)
    n_nodes = 0
    n_addr_edges = 0
    n_impl_edges = 0
    for mid, name, goal_ids, req_ids, tom_sec in SDM_MEASURES:
        session.run(
            "MERGE (m:Measure {id: $id}) "
            "SET m.name_de = $name, m.sdm_section = $sec, m.tom_section = $tom"
            + _prov_node_set("m"),
            id=mid, name=name, sec=mid.split("-")[0].upper(), tom=tom_sec, **p,
        )
        n_nodes += 1
        for goal_id in goal_ids:
            r = session.run(
                "MATCH (m:Measure {id: $mid}) "
                "MATCH (g:ProtectionGoal {id: $gid}) "
                "MERGE (m)-[e:ADDRESSES]->(g) "
                "SET " + _prov_edge_set("e") + " "
                "RETURN 1 AS ok",
                mid=mid, gid=goal_id, **p,
            ).single()
            if r:
                n_addr_edges += 1
        for req_id in req_ids:
            r = session.run(
                "MATCH (m:Measure {id: $mid}) "
                "MATCH (r:Requirement_B {id: $rid}) "
                "MERGE (m)-[e:IMPLEMENTS]->(r) "
                "SET " + _prov_edge_set("e") + " "
                "RETURN 1 AS ok",
                mid=mid, rid=req_id, **p,
            ).single()
            if r:
                n_impl_edges += 1
    return f"measures={n_nodes}/{len(SDM_MEASURES)}, ADDRESSES={n_addr_edges}, IMPLEMENTS={n_impl_edges}"


# ── ADR-106 PR D3: ProcessingActivity (~12, DSK VVT-Hinweise § 6.2) ──────────

PROCESSING_ACTIVITIES = [
    ("personalakte",           "Personalaktenführung / Stammdaten",                  "art_6_1_b_contract",     ["Beschäftigte"]),
    ("lohnabrechnung",         "Lohn-, Gehalts- und Bezügeabrechnung",                "art_6_1_c_legal_oblig",  ["Beschäftigte"]),
    ("arbeitszeit",            "Arbeitszeiterfassung",                                "art_6_1_b_contract",     ["Beschäftigte"]),
    ("bewerbung",              "Bewerbungsverfahren / Bewerberauswahl",               "art_6_1_b_contract",     ["Bewerber"]),
    ("newsletter",             "Newsletter- und E-Mail-Marketing",                    "art_6_1_a_consent",      ["Newsletter-Empfänger"]),
    ("kundenverwaltung",       "Kundenverwaltung / CRM",                              "art_6_1_b_contract",     ["Kunden"]),
    ("support_ticketing",      "Support-Ticketing / Kundenservice",                   "art_6_1_b_contract",     ["Kunden"]),
    ("payment_processing",     "Zahlungsabwicklung und Transaktionsverarbeitung",     "art_6_1_b_contract",     ["Kunden"]),
    ("error_monitoring",       "Error-Tracking, Performance-Monitoring",               "art_6_1_f_legit_int",    ["Endnutzer"]),
    ("tracking_analytics",     "Nutzungsanalyse, Tracking und Reichweitenmessung",     "art_6_1_a_consent",      ["Website-Besucher", "Endnutzer"]),
    ("ki_inferenz",            "KI-gestützte Textgenerierung und -verarbeitung",       "art_6_1_f_legit_int",    ["Endnutzer"]),
    ("rag_retrieval",          "Retrieval Augmented Generation über Unternehmensdaten","art_6_1_f_legit_int",    ["Endnutzer"]),
]

# (service_name, processing_activity_id) — high-confidence service ↔ activity mappings
SERVICE_ACTIVITY_MAPPINGS = [
    ("Stripe", "payment_processing"),
    ("Mollie", "payment_processing"),
    ("Braintree", "payment_processing"),
    ("Postmark", "newsletter"),
    ("Resend", "newsletter"),
    ("Sentry", "error_monitoring"),
    ("Segment", "tracking_analytics"),
    ("Amplitude", "tracking_analytics"),
    ("OpenAI", "ki_inferenz"),
    ("Anthropic", "ki_inferenz"),
    ("Chroma", "rag_retrieval"),
]


def seed_pr_d3_processing_activities(session):
    """ADR-106 PR D3: 12 ProcessingActivity-Nodes (DSK VVT-Hinweise § 6.2 + SaaS-Standard)
    + USED_FOR edges from Services to their activities.
    """
    p = _prov_params(PROV_PR_C_SDM)
    n_nodes = 0
    for paid, name, basis_id, subjects in PROCESSING_ACTIVITIES:
        session.run(
            "MERGE (pa:ProcessingActivity {id: $id}) "
            "SET pa.name_de = $name, pa.typical_legal_basis = $basis, "
            "    pa.typical_data_subjects = $subj"
            + _prov_node_set("pa"),
            id=paid, name=name, basis=basis_id, subj=subjects, **p,
        )
        n_nodes += 1
    n_edges = 0
    for svc_name, paid in SERVICE_ACTIVITY_MAPPINGS:
        r = session.run(
            "MATCH (s:Service {name: $svc}) "
            "MATCH (pa:ProcessingActivity {id: $id}) "
            "MERGE (s)-[e:USED_FOR]->(pa) "
            "SET " + _prov_edge_set("e") + " "
            "RETURN 1 AS ok",
            svc=svc_name, id=paid, **p,
        ).single()
        if r:
            n_edges += 1
    return f"processing_activities={n_nodes}/{len(PROCESSING_ACTIVITIES)}, used_for_edges={n_edges}/{len(SERVICE_ACTIVITY_MAPPINGS)}"


# ── ADR-106 PR D4: DataSubject (8, DSK § 6.3 + Art. 8 DSGVO) ─────────────────

DATA_SUBJECTS = [
    ("beschaeftigte",        "Beschäftigte",        "Mitarbeitende und Angestellte des Verantwortlichen"),
    ("bewerber",             "Bewerber",            "Personen mit Bewerbungsverhältnis (vor Beschäftigung)"),
    ("kunden",               "Kunden",              "Vertragspartner mit Bestell- oder Leistungsbezugsverhältnis"),
    ("endnutzer",            "Endnutzer",           "Nutzer der Anwendung / des Service ohne formales Vertragsverhältnis"),
    ("website_besucher",     "Website-Besucher",    "Personen, die die Webseite besuchen (typischerweise via Tracking erfasst)"),
    ("newsletter_empfaenger","Newsletter-Empfänger","Personen mit eingewilligtem Newsletter-Abonnement"),
    ("lieferanten",          "Lieferanten",         "Vertragspartner als Leistungserbringer (B2B)"),
    ("minderjaehrige",       "Minderjährige",       "Personen unter 16 Jahren (Art. 8 DSGVO — besondere Schutzpflicht)"),
]


def seed_pr_d4_data_subjects(session):
    """ADR-106 PR D4: 8 DataSubject-Nodes als kuratierte Standard-Kategorien."""
    p = _prov_params(PROV_PR_C_SDM)
    n = 0
    for sid, name, desc in DATA_SUBJECTS:
        session.run(
            "MERGE (ds:DataSubject {id: $id}) "
            "SET ds.name_de = $name, ds.description_de = $desc"
            + _prov_node_set("ds"),
            id=sid, name=name, desc=desc, **p,
        )
        n += 1
    return f"data_subjects_nodes={n}/{len(DATA_SUBJECTS)}"


# ── ADR-106 PR D5: LegalBasis (7, DSGVO Art. 6/9 + BDSG § 26) ────────────────

LEGAL_BASES = [
    ("art_6_1_a_consent",            "Einwilligung",                       "Art. 6 Abs. 1 lit. a",  "Einwilligung der betroffenen Person für einen oder mehrere bestimmte Zwecke"),
    ("art_6_1_b_contract",           "Vertragserfüllung / Vertragsanbahnung","Art. 6 Abs. 1 lit. b","Verarbeitung zur Erfüllung eines Vertrags oder zur Durchführung vorvertraglicher Maßnahmen"),
    ("art_6_1_c_legal_oblig",        "Rechtliche Verpflichtung",            "Art. 6 Abs. 1 lit. c", "Erfüllung einer rechtlichen Verpflichtung, der der Verantwortliche unterliegt"),
    ("art_6_1_d_vital_interests",    "Lebenswichtige Interessen",           "Art. 6 Abs. 1 lit. d", "Schutz lebenswichtiger Interessen der betroffenen Person oder einer anderen natürlichen Person"),
    ("art_6_1_e_public_interest",    "Öffentliches Interesse / Hoheitliche Gewalt","Art. 6 Abs. 1 lit. e","Wahrnehmung einer Aufgabe im öffentlichen Interesse oder in Ausübung öffentlicher Gewalt"),
    ("art_6_1_f_legit_int",          "Berechtigte Interessen",              "Art. 6 Abs. 1 lit. f", "Wahrung berechtigter Interessen des Verantwortlichen oder eines Dritten, sofern Interessen der Betroffenen nicht überwiegen"),
    ("art_9_special_categories",     "Besondere Kategorien personenbezogener Daten","Art. 9",       "Spezialregeln für sensible Daten (Gesundheit, Biometrie, politische Meinung, Religion, Sexualleben, etc.)"),
    ("bdsg_26_beschaeftigung",       "Beschäftigtenkontext",                "§ 26 BDSG",            "Datenverarbeitung im Beschäftigungsverhältnis (national, ergänzend zu Art. 88 DSGVO)"),
]


def seed_pr_d5_legal_basis(session):
    """ADR-106 PR D5: 8 LegalBasis-Nodes (DSGVO Art. 6/9 + BDSG § 26)."""
    p = _prov_params(PROV_PR_C_LEGAL)
    n = 0
    for bid, name, article, desc in LEGAL_BASES:
        session.run(
            "MERGE (lb:LegalBasis {id: $id}) "
            "SET lb.name_de = $name, lb.article_ref = $art, lb.description_de = $desc"
            + _prov_node_set("lb"),
            id=bid, name=name, art=article, desc=desc, **p,
        )
        n += 1
    return f"legal_basis_nodes={n}/{len(LEGAL_BASES)}"


# ── ADR-106 PR B3: RetentionPeriod nodes + HAS_RETENTION edges ───────────────
#
# 5 standard retention defaults from German law + commercial practice.
RETENTION_PERIODS = [
    {
        "id": "hgb_geschaeftsdokumente",
        "name_de": "HGB-Aufbewahrung Geschäftsdokumente",
        "duration_iso8601": "P10Y",
        "duration_de": "10 Jahre nach Ablauf des Kalenderjahres",
        "legal_basis": "HGB § 257; AO § 147",
        "applies_to_categories": ["Zahlungsdaten", "Rechnungsadressen", "Transaktionsdaten"],
    },
    {
        "id": "session_runtime",
        "name_de": "Session-Daten TTL",
        "duration_iso8601": "PT24H",
        "duration_de": "TTL-basiert (typisch 24h, konfigurierbar)",
        "legal_basis": "Erforderlichkeit gem. Art. 5 Abs. 1 lit. c DSGVO",
        "applies_to_categories": ["Session-Daten", "Cache-Daten"],
    },
    {
        "id": "log_standard",
        "name_de": "Application-Logs Standard-Retention",
        "duration_iso8601": "P90D",
        "duration_de": "90 Tage (konfigurierbar bis 365 Tage)",
        "legal_basis": "Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse Sicherheit)",
        "applies_to_categories": ["Error-Logs", "Stack-Traces", "IP-Adressen", "Delivery-Logs"],
    },
    {
        "id": "marketing_consent",
        "name_de": "Marketing/Tracking bis Widerruf",
        "duration_iso8601": "P0D",
        "duration_de": "Bis Widerruf der Einwilligung",
        "legal_basis": "Art. 7 Abs. 3 DSGVO",
        "applies_to_categories": ["Event-Daten", "Nutzungsverhalten", "Nutzer-IDs"],
    },
    {
        "id": "bewerbungsdaten",
        "name_de": "Bewerbungsdaten nach Absage",
        "duration_iso8601": "P6M",
        "duration_de": "6 Monate nach Absage (BAG-Rspr.)",
        "legal_basis": "BAG-Rspr. + § 24 Abs. 1 Nr. 2 BDSG",
        "applies_to_categories": ["Bewerbungsdaten", "Lebenslauf-Inhalte"],
    },
]

# (service_name, retention_id) — high-confidence default mappings.
SERVICE_RETENTION_MAPPINGS = [
    ("Stripe", "hgb_geschaeftsdokumente"),
    ("Mollie", "hgb_geschaeftsdokumente"),
    ("Braintree", "hgb_geschaeftsdokumente"),
    ("Redis", "session_runtime"),
    ("Sentry", "log_standard"),
    ("Postmark", "log_standard"),
    ("Resend", "log_standard"),
    ("Segment", "marketing_consent"),
    ("Amplitude", "marketing_consent"),
]


def seed_pr_b3_retention(session):
    """ADR-106 PR B3: 5 RetentionPeriod nodes + HAS_RETENTION edges."""
    p = _prov_params(PROV_PR_B3_RETENTION)
    nodes_n = 0
    for rp in RETENTION_PERIODS:
        session.run(
            "MERGE (r:RetentionPeriod {id: $id}) "
            "SET r.name_de = $name_de, "
            "    r.duration_iso8601 = $duration_iso8601, "
            "    r.duration_de = $duration_de, "
            "    r.legal_basis = $legal_basis, "
            "    r.applies_to_categories = $cats"
            + _prov_node_set("r"),
            id=rp["id"], name_de=rp["name_de"],
            duration_iso8601=rp["duration_iso8601"],
            duration_de=rp["duration_de"],
            legal_basis=rp["legal_basis"],
            cats=rp["applies_to_categories"], **p,
        )
        nodes_n += 1
    edges_n = 0
    for svc_name, rp_id in SERVICE_RETENTION_MAPPINGS:
        r = session.run(
            "MATCH (s:Service {name: $svc_name}) "
            "MATCH (r:RetentionPeriod {id: $rp_id}) "
            "MERGE (s)-[e:HAS_RETENTION]->(r) "
            "SET " + _prov_edge_set("e") + " "
            "RETURN 1 AS ok",
            svc_name=svc_name, rp_id=rp_id, **p,
        ).single()
        if r:
            edges_n += 1
    return f"retention_periods={nodes_n}/{len(RETENTION_PERIODS)}, has_retention_edges={edges_n}/{len(SERVICE_RETENTION_MAPPINGS)}"


# ── ADR-106 PR B4: 17 SupervisoryAuthority (BfDI + 16 Länder) ────────────────

SUPERVISORY_AUTHORITIES = [
    ("bfdi", "Die Bundesbeauftragte für den Datenschutz und die Informationsfreiheit", "BfDI", "Bund", "https://www.bfdi.bund.de/"),
    ("bw_lfdi", "Landesbeauftragter für den Datenschutz und die Informationsfreiheit Baden-Württemberg", "LfDI BW", "Baden-Württemberg", "https://www.baden-wuerttemberg.datenschutz.de/"),
    ("by_baylda", "Bayerisches Landesamt für Datenschutzaufsicht", "BayLDA", "Bayern", "https://www.lda.bayern.de/"),
    ("by_baydsb", "Bayerischer Landesbeauftragter für den Datenschutz", "BayLfD", "Bayern (öffentl.)", "https://www.datenschutz-bayern.de/"),
    ("be_blnbdi", "Berliner Beauftragte für Datenschutz und Informationsfreiheit", "BlnBDI", "Berlin", "https://www.datenschutz-berlin.de/"),
    ("bb_lda", "Landesbeauftragte für den Datenschutz und für das Recht auf Akteneinsicht Brandenburg", "LDA BB", "Brandenburg", "https://www.lda.brandenburg.de/"),
    ("hb_lfdi", "Die Landesbeauftragte für Datenschutz und Informationsfreiheit Bremen", "LfDI HB", "Bremen", "https://www.datenschutz.bremen.de/"),
    ("hh_hmbbfdi", "Der Hamburgische Beauftragte für Datenschutz und Informationsfreiheit", "HmbBfDI", "Hamburg", "https://datenschutz-hamburg.de/"),
    ("he_hbdi", "Der Hessische Beauftragte für Datenschutz und Informationsfreiheit", "HBDI", "Hessen", "https://datenschutz.hessen.de/"),
    ("mv_lfdi", "Der Landesbeauftragte für Datenschutz und Informationsfreiheit Mecklenburg-Vorpommern", "LfDI MV", "Mecklenburg-Vorpommern", "https://www.datenschutz-mv.de/"),
    ("ni_lfd", "Die Landesbeauftragte für den Datenschutz Niedersachsen", "LfD NI", "Niedersachsen", "https://lfd.niedersachsen.de/"),
    ("nw_ldi", "Landesbeauftragte für Datenschutz und Informationsfreiheit Nordrhein-Westfalen", "LDI NRW", "Nordrhein-Westfalen", "https://www.ldi.nrw.de/"),
    ("rp_lfdi", "Der Landesbeauftragte für den Datenschutz und die Informationsfreiheit Rheinland-Pfalz", "LfDI RLP", "Rheinland-Pfalz", "https://www.datenschutz.rlp.de/"),
    ("sl_uds", "Unabhängiges Datenschutzzentrum Saarland", "UDS", "Saarland", "https://www.datenschutz.saarland.de/"),
    ("sn_sdb", "Der Sächsische Datenschutzbeauftragte", "SDB", "Sachsen", "https://www.datenschutz.sachsen.de/"),
    ("st_lfd", "Landesbeauftragter für den Datenschutz Sachsen-Anhalt", "LfD ST", "Sachsen-Anhalt", "https://datenschutz.sachsen-anhalt.de/"),
    ("sh_uld", "Unabhängiges Landeszentrum für Datenschutz Schleswig-Holstein", "ULD", "Schleswig-Holstein", "https://www.datenschutzzentrum.de/"),
    ("th_tlfdi", "Thüringer Landesbeauftragter für den Datenschutz und die Informationsfreiheit", "TLfDI", "Thüringen", "https://www.tlfdi.de/"),
]


def seed_pr_b4_supervisory_authorities(session):
    """ADR-106 PR B4: 17 DE SupervisoryAuthority (BfDI + 16 Länder)."""
    p = _prov_params(PROV_PR_B4_SUPAUTH)
    n = 0
    for sid, full_name, short, bundesland, url in SUPERVISORY_AUTHORITIES:
        session.run(
            "MERGE (sa:SupervisoryAuthority {id: $id}) "
            "SET sa.full_name = $full, sa.short_name = $short, "
            "    sa.bundesland = $bl, sa.url = $url"
            + _prov_node_set("sa"),
            id=sid, full=full_name, short=short, bl=bundesland, url=url, **p,
        )
        n += 1
    return f"supervisory_authorities={n}/{len(SUPERVISORY_AUTHORITIES)}"


# ── ADR-106 PR C1: SDM Protection Goals (7) ──────────────────────────────────

PROTECTION_GOALS = [
    ("dm", "Datenminimierung", "Dm", "Beschränkung auf das für den Zweck erforderliche Maß (Art. 5 Abs. 1 lit. c DSGVO)"),
    ("vf", "Verfügbarkeit", "Vf", "Sicherstellung des zeitgerechten Zugriffs auf personenbezogene Daten (Art. 32 Abs. 1 lit. b DSGVO)"),
    ("ig", "Integrität", "Ig", "Schutz vor unbefugter Veränderung (Art. 32 Abs. 1 lit. b DSGVO)"),
    ("vt", "Vertraulichkeit", "Vt", "Schutz vor unbefugter Kenntnisnahme (Art. 32 Abs. 1 lit. b DSGVO)"),
    ("nn", "Nichtverkettung", "Nn", "Datenverarbeitung nur für den vorgesehenen Zweck, keine Zweckänderung ohne Rechtsgrundlage"),
    ("tp", "Transparenz", "Tp", "Nachvollziehbarkeit der Verarbeitung für Betroffene, Verantwortliche und Aufsicht (Art. 5 Abs. 1 lit. a DSGVO)"),
    ("iv", "Intervenierbarkeit", "Iv", "Möglichkeit der Wahrnehmung von Betroffenenrechten (Art. 12 ff. DSGVO)"),
]


def seed_pr_c1_protection_goals(session):
    """ADR-106 PR C1: 7 SDM-Gewährleistungsziele (SDM v3.1 Teil A4)."""
    p = _prov_params(PROV_PR_C_SDM)
    n = 0
    for gid, name, short, desc in PROTECTION_GOALS:
        session.run(
            "MERGE (g:ProtectionGoal {id: $id}) "
            "SET g.name_de = $name, g.short = $short, "
            "    g.description_de = $desc, g.sdm_section = 'A4'"
            + _prov_node_set("g"),
            id=gid, name=name, short=short, desc=desc, **p,
        )
        n += 1
    return f"protection_goals={n}/{len(PROTECTION_GOALS)}"


# ── ADR-106 PR C2: SDM B-Anforderungen (25 = B1.1–B1.23 + B2 + B3) ───────────

REQUIREMENTS_B = [
    ("B1.1",  "Transparenz für Betroffene",                 "B1.1",  ["Art. 5 Abs. 1 lit. a", "Art. 12", "Art. 13", "Art. 14"]),
    ("B1.2",  "Zweckbindung",                                "B1.2",  ["Art. 5 Abs. 1 lit. b", "Art. 6 Abs. 4"]),
    ("B1.3",  "Datenminimierung",                            "B1.3",  ["Art. 5 Abs. 1 lit. c", "Art. 25 Abs. 2"]),
    ("B1.4",  "Richtigkeit",                                 "B1.4",  ["Art. 5 Abs. 1 lit. d", "Art. 16"]),
    ("B1.5",  "Speicherbegrenzung",                          "B1.5",  ["Art. 5 Abs. 1 lit. e", "Art. 17"]),
    ("B1.6",  "Integrität",                                  "B1.6",  ["Art. 5 Abs. 1 lit. f", "Art. 32 Abs. 1 lit. b"]),
    ("B1.7",  "Vertraulichkeit",                             "B1.7",  ["Art. 5 Abs. 1 lit. f", "Art. 28 Abs. 3 lit. b", "Art. 32 Abs. 1 lit. b"]),
    ("B1.8",  "Rechenschafts- und Nachweisfähigkeit",        "B1.8",  ["Art. 5 Abs. 2", "Art. 24", "Art. 30"]),
    ("B1.9",  "Identifizierung und Authentifizierung",       "B1.9",  ["Art. 32 Abs. 1 lit. b"]),
    ("B1.10", "Unterstützung bei der Wahrnehmung von Betroffenenrechten", "B1.10", ["Art. 12", "Art. 15", "Art. 16", "Art. 17", "Art. 18", "Art. 20", "Art. 21"]),
    ("B1.11", "Berichtigungsmöglichkeit von Daten",          "B1.11", ["Art. 16"]),
    ("B1.12", "Löschbarkeit von Daten",                      "B1.12", ["Art. 17"]),
    ("B1.13", "Einschränkbarkeit der Verarbeitung von Daten","B1.13", ["Art. 18"]),
    ("B1.14", "Datenübertragbarkeit",                        "B1.14", ["Art. 20"]),
    ("B1.15", "Eingriffsmöglichkeit in Prozesse automatisierter Entscheidungen", "B1.15", ["Art. 22"]),
    ("B1.16", "Fehler- und Diskriminierungsfreiheit beim Profiling", "B1.16", ["Art. 5 Abs. 1 lit. a", "Art. 22"]),
    ("B1.17", "Datenschutz durch Voreinstellungen",          "B1.17", ["Art. 25 Abs. 2"]),
    ("B1.18", "Verfügbarkeit",                               "B1.18", ["Art. 32 Abs. 1 lit. b"]),
    ("B1.19", "Belastbarkeit",                               "B1.19", ["Art. 32 Abs. 1 lit. b"]),
    ("B1.20", "Wiederherstellbarkeit",                       "B1.20", ["Art. 32 Abs. 1 lit. c"]),
    ("B1.21", "Evaluierbarkeit",                             "B1.21", ["Art. 32 Abs. 1 lit. d"]),
    ("B1.22", "Behebung und Abmilderung von Datenschutzverletzungen", "B1.22", ["Art. 33", "Art. 34"]),
    ("B1.23", "Angemessene Überwachung der Verarbeitung",    "B1.23", ["Art. 32 Abs. 1 lit. d"]),
    ("B2",    "Einwilligungsmanagement",                     "B2",    ["Art. 7", "Art. 8", "Art. 9 Abs. 2 lit. a"]),
    ("B3",    "Umsetzung aufsichtsbehördlicher Anordnungen", "B3",    ["Art. 58"]),
]


def seed_pr_c2_requirements_b(session):
    """ADR-106 PR C2: 25 SDM B-Anforderungen (SDM v3.1 Teil B + B2 + B3).

    These are the SDM-abstracted requirements per Datenschutzkonferenz, not raw
    DSGVO article references. dsgvo_articles is the cross-table from SDM Teil C
    that links each B-requirement to the underlying DSGVO articles.
    """
    p = _prov_params(PROV_PR_C_SDM)
    n = 0
    for rid, name, sdm_sec, articles in REQUIREMENTS_B:
        session.run(
            "MERGE (r:Requirement_B {id: $id}) "
            "SET r.name_de = $name, r.sdm_section = $sec, "
            "    r.dsgvo_articles = $articles"
            + _prov_node_set("r"),
            id=rid, name=name, sec=sdm_sec, articles=articles, **p,
        )
        n += 1
    return f"requirements_b={n}/{len(REQUIREMENTS_B)}"


# ── ADR-106 PR C3: DSGVO + BDSG Legal Requirements (BfDI-Anchoring-Targets) ──
#
# Required prerequisite for seed_bfdi (C4): the BfDI brochure cites 13 distinct
# legal-requirement Nodes (DSGVO Art. 28/30/37/38/39 + BDSG § 38) that don't
# exist in our Requirement layer yet (only BSI/CRA Requirements were seeded).
# Composite key {id, framework} matches the BSI/CRA convention from ADR-066.
LEGAL_REQUIREMENTS = [
    ("DSGVO-28",     "DSGVO", "Auftragsverarbeitung — Grundlagen",                                            "Art. 28"),
    ("DSGVO-28-2",   "DSGVO", "Subunternehmer / Unterauftragsverarbeiter",                                    "Art. 28 Abs. 2"),
    ("DSGVO-28-3",   "DSGVO", "Voraussetzungen für die Auftragsverarbeitung (Vertrag, Weisungsbindung, TOM)", "Art. 28 Abs. 3"),
    ("DSGVO-28-3-a", "DSGVO", "Drittstaaten-Übermittlung im Auftragsverhältnis",                              "Art. 28 Abs. 3 lit. a"),
    ("DSGVO-28-10",  "DSGVO", "Statuswechsel bei Weisungsverstoß",                                            "Art. 28 Abs. 10"),
    ("DSGVO-30-2",   "DSGVO", "VVT-Pflicht des Auftragsverarbeiters",                                         "Art. 30 Abs. 2"),
    ("DSGVO-37-1-a", "DSGVO", "DSB-Bestellungspflicht öffentliche Stellen",                                   "Art. 37 Abs. 1 lit. a"),
    ("DSGVO-37-1-b", "DSGVO", "DSB-Bestellungspflicht bei Kerntätigkeit (Überwachung / Art. 9/10 Daten)",     "Art. 37 Abs. 1 lit. b"),
    ("DSGVO-37-5",   "DSGVO", "DSB-Qualifikation und Ressourcen",                                             "Art. 37 Abs. 5"),
    ("DSGVO-38",     "DSGVO", "DSB-Stellung (Weisungsfreiheit, Kündigungsschutz)",                            "Art. 38"),
    ("DSGVO-38-5",   "DSGVO", "DSB-Verschwiegenheitspflicht",                                                 "Art. 38 Abs. 5"),
    ("DSGVO-39",     "DSGVO", "DSB-Aufgabenkatalog",                                                          "Art. 39"),
    ("BDSG-38-1",    "BDSG",  "DSB-Bestellungspflicht nicht-öffentliche Stellen (20-Personen-Schwelle)",      "§ 38 Abs. 1"),
]


def seed_pr_c3_legal_requirements(session):
    """ADR-106 PR C3: 13 DSGVO/BDSG Requirement nodes — prereq for seed_bfdi.

    Uses the existing Requirement node type with composite key {id, framework}
    per ADR-066 (BSI) / ADR-082 (CRA) convention. ADR-107 provenance fully
    populated. These nodes are the targets that seed_bfdi attaches anchorings to.
    """
    p = _prov_params(PROV_PR_C_LEGAL)
    n = 0
    for rid, fw, title, article in LEGAL_REQUIREMENTS:
        session.run(
            "MERGE (r:Requirement {id: $id, framework: $fw}) "
            "SET r.title_de = $title, r.article_ref = $article, r.regulation = $fw"
            + _prov_node_set("r"),
            id=rid, fw=fw, title=title, article=article, **p,
        )
        n += 1
    return f"legal_requirements={n}/{len(LEGAL_REQUIREMENTS)}"


# ── ADR-106 PR C4: BfDI-Anchorings as properties ─────────────────────────────

def seed_pr_c4_bfdi(session):
    """ADR-106 PR C4: read bfdi-anchorings.json, attach bfdi_guidance /
    bfdi_commentary properties to Requirement / DocumentType nodes.

    Target nodes are seeded by seed_pr_c3_legal_requirements (Requirement) +
    pre-existing DocumentType ('AVV'). If a target is missing, raises with the
    target_node_match dump to surface seeding gaps (no silent creation).

    bfdi_law_refs is stored as a list[str]. Source attribution comes from
    PROV_PR_C_BFDI (dl-de/by-2-0).
    """
    import json
    from pathlib import Path

    anch_path = Path(__file__).resolve().parent.parent / "docs/sources/bfdi/extracted/bfdi-anchorings.json"
    if not anch_path.exists():
        return f"SKIP — bfdi-anchorings.json not found at {anch_path}"
    data = json.loads(anch_path.read_text(encoding="utf-8"))
    p = _prov_params(PROV_PR_C_BFDI)

    n = 0
    orphans: list[str] = []
    for a in data.get("anchorings", []):
        tnt = a.get("target_node_type")
        tnm = a.get("target_node_match", {})
        prop = a.get("property", "bfdi_guidance")
        if tnt == "Requirement":
            r = session.run(
                f"MATCH (n:Requirement {{id: $id, framework: $fw}}) "
                f"SET n.`{prop}` = $value, "
                f"    n.bfdi_source_section = $sect, "
                f"    n.bfdi_source_pages = $pages, "
                f"    n.bfdi_law_refs = $law_refs, "
                f"    n.bfdi_source = $_p_source, "
                f"    n.bfdi_license = $_p_license, "
                f"    n.bfdi_license_attribution = $_p_license_attribution, "
                f"    n.bfdi_last_verified = date($_p_last_verified) "
                f"RETURN elementId(n) AS nid",
                id=tnm.get("id"), fw=tnm.get("framework"),
                value=a.get("value"), sect=a.get("source_section"),
                pages=a.get("source_pages"), law_refs=a.get("law_refs", []),
                **p,
            ).single()
            if r:
                n += 1
            else:
                orphans.append(f"Requirement {tnm.get('framework')}:{tnm.get('id')}")
        elif tnt == "DocumentType":
            r = session.run(
                f"MATCH (n:DocumentType {{type: $type}}) "
                f"SET n.`{prop}` = $value, "
                f"    n.bfdi_source_section = $sect, "
                f"    n.bfdi_source_pages = $pages, "
                f"    n.bfdi_law_refs = $law_refs, "
                f"    n.bfdi_source = $_p_source, "
                f"    n.bfdi_license = $_p_license, "
                f"    n.bfdi_license_attribution = $_p_license_attribution, "
                f"    n.bfdi_last_verified = date($_p_last_verified) "
                f"RETURN elementId(n) AS nid",
                type=tnm.get("type"),
                value=a.get("value"), sect=a.get("source_section"),
                pages=a.get("source_pages"), law_refs=a.get("law_refs", []),
                **p,
            ).single()
            if r:
                n += 1
            else:
                orphans.append(f"DocumentType {tnm.get('type')}")
        else:
            orphans.append(f"unsupported target_node_type={tnt}")

    msg = f"bfdi_anchorings_attached={n}/{len(data.get('anchorings', []))}"
    if orphans:
        msg += f"; orphans={orphans}"
    return msg


# ── ADR-115 A1: PSP controller/processor role (ACTS_AS, launch slice) ─────────
#
# EDPB Guidelines 07/2020 (Rn. 26 + Rn. 82 + Bank-payments example under Rn. 40,
# p. 15), verified via legal-advisor gate 2026-06-03: a pure PSP is *controller*
# for payment_processing, INDEPENDENT of integration_mode — the merchant->PSP
# data flow is controller-to-controller because the PSP determines purpose/means
# on its own regulatory account (AML/GwG, PSD2/ZAG), which the merchant cannot
# remove by instruction. integration_mode governs PCI-DSS / AVV scope only, not
# the GDPR role. PayPal (e-money/bank) and Klarna (BNPL + Art. 22 scoring) are
# special_case — own activities beyond the pure-PSP rule.
# Decision record: ADR-115 (internal).

EDPB_ROLE_SOURCE = "EDPB 07/2020 Rn. 26 + Rn. 82 + Bank payments example (under Rn. 40, p. 15)"
# B-2/L9 (EN package): EN citation form ("Rn." is the German pinpoint marker).
EDPB_ROLE_SOURCE_EN = "EDPB 07/2020 para. 26 + para. 82 + bank payments example (under para. 40, p. 15)"

PROV_PSP_ROLE = {
    "source": "EDPB Guidelines 07/2020 on the concepts of controller and processor under the GDPR",
    "source_url": "https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-072020-concepts-controller-and-processor-gdpr_en",
    "license": "öffentliches EU-Dokument (frei nutzbar)",
    "license_attribution": "European Data Protection Board",
    "last_verified": "2026-06-03",
}
PROV_PSP_NODE = {
    "source": "ADR-115 A1 PSP launch role (kuratiert) + Provider-Trust-Pages",
    "license": "Lex-Orchestra internal",
    "license_attribution": "Lex-Orchestra",
    "last_verified": "2026-06-03",
}

# (name, role, legal_basis, role_source, role_source_en, role_note, create_node, country, ai_act_relevant)
PSP_ROLES = [
    ("Stripe",      "controller",   "Art. 6 Abs. 1 lit. b + lit. c DSGVO", EDPB_ROLE_SOURCE, EDPB_ROLE_SOURCE_EN,
        None, False, None, None),
    ("Mollie",      "controller",   "Art. 6 Abs. 1 lit. b + lit. c DSGVO", EDPB_ROLE_SOURCE, EDPB_ROLE_SOURCE_EN,
        None, False, None, None),
    ("Billwerk",    "controller",   "Art. 6 Abs. 1 lit. b + lit. c DSGVO", EDPB_ROLE_SOURCE, EDPB_ROLE_SOURCE_EN,
        "Subscription-billing-only deployments may act as processor at a separate ProcessingActivity; controller for payment_processing.",
        True, "Germany", False),
    ("Digistore24", "controller",   "Art. 6 Abs. 1 lit. b + lit. c DSGVO", EDPB_ROLE_SOURCE, EDPB_ROLE_SOURCE_EN,
        "Merchant-of-Record — own contractual party to the end customer.",
        True, "Germany", False),
    ("PayPal",      "special_case", "Art. 6 Abs. 1 lit. b + lit. c DSGVO",
        "PayPal: E-Geld-/Bankstatus — eigener Verantwortlicher auch merchant-side; gesonderte Prüfung nötig (EDPB 07/2020 Rn. 82).",
        "PayPal: e-money/banking status — a separate controller even merchant-side; separate assessment required (EDPB 07/2020 para. 82).",
        None, False, None, None),
    ("Klarna",      "special_case", "Art. 6 Abs. 1 lit. b/f DSGVO + Art. 22 DSGVO + § 31 BDSG",
        "Klarna: BNPL + Bonitäts-Scoring (Art. 22 DSGVO, AI-Act-relevant) — eigene Verarbeitungstätigkeit; gesonderte Prüfung nötig.",
        "Klarna: BNPL + credit scoring (Art. 22 GDPR, AI-Act-relevant) — its own processing activity; separate assessment required.",
        None, True, "Sweden", True),
]


def seed_psp_roles(session):
    """ADR-115 A1: graph-resident controller/processor role for pure PSPs.

    Creates (:Service)-[:ACTS_AS {role, role_source, legal_basis, role_note}]->
    (:ProcessingActivity {id:'payment_processing'}) for Stripe/Mollie/Billwerk/
    Digistore24 (role=controller) and PayPal/Klarna (role=special_case).

    Missing nodes are created (Billwerk/Digistore24/Klarna) with category=payment,
    data_subjects=['customers'] (§4.1 allowlist, ON CREATE — the pr_c1_5/pr_d4
    backfills run before this module and cannot reach these nodes; F5), and a
    HAS_CATEGORY->payment edge (edge authoritative, drift-free). Missing
    USED_FOR->payment_processing edges are added (PayPal + new nodes); existing
    USED_FOR provenance (Stripe/Mollie from pr_d3) is left untouched (ON CREATE).
    dpa_required=false on new nodes: the PSP renders controller / special_case,
    so no merchant Art. 28 AVV under the pure-PSP rule.

    role_source EDPB-verified (legal-advisor gate 2026-06-03). ADR-107 provenance
    on every node + edge. MERGE-only, idempotent.
    """
    p_role = _prov_params(PROV_PSP_ROLE)
    p_node = _prov_params(PROV_PSP_NODE)
    nodes_created = 0
    role_edges = 0

    for name, role, legal_basis, role_source, role_source_en, role_note, create_node, country, ai_act_relevant in PSP_ROLES:
        if create_node:
            session.run(
                """
                MERGE (s:Service {name: $name})
                ON CREATE SET s.category = 'payment', s.country = $country,
                    s.gdpr_adequate = true, s.dpa_required = false,
                    s.ai_act_relevant = $ai_act_relevant,
                    s.data_subjects = ['customers']"""
                + _prov_node_set("s") +
                """
                ON MATCH SET s.last_seen = datetime()"""
                + _prov_node_set("s") +
                """
                WITH s
                MATCH (sc:ServiceCategory {name: 'payment'})
                MERGE (s)-[r:HAS_CATEGORY]->(sc)
                ON CREATE SET """ + _prov_edge_set("r") + """
                ON MATCH SET """ + _prov_edge_set("r"),
                name=name, country=country, ai_act_relevant=ai_act_relevant, **p_node,
            )
            nodes_created += 1

        # USED_FOR — idempotent; ON CREATE only, so existing edge provenance stays
        session.run(
            "MATCH (s:Service {name: $name}) "
            "MATCH (pa:ProcessingActivity {id: 'payment_processing'}) "
            "MERGE (s)-[e:USED_FOR]->(pa) "
            "ON CREATE SET " + _prov_edge_set("e"),
            name=name, **p_node,
        )

        # ACTS_AS — the EDPB-backed role claim (always SET; idempotent re-seed)
        r = session.run(
            "MATCH (s:Service {name: $name}) "
            "MATCH (pa:ProcessingActivity {id: 'payment_processing'}) "
            "MERGE (s)-[a:ACTS_AS]->(pa) "
            "SET a.role = $role, a.role_source = $role_source, "
            "    a.role_source_en = $role_source_en, "
            "    a.legal_basis = $legal_basis, a.role_note = $role_note, "
            + _prov_edge_set("a") + " "
            "RETURN a.role AS role",
            name=name, role=role, role_source=role_source,
            role_source_en=role_source_en,
            legal_basis=legal_basis, role_note=role_note, **p_role,
        ).single()
        if r:
            role_edges += 1

    v = session.run(
        "MATCH (:Service)-[a:ACTS_AS]->(:ProcessingActivity {id:'payment_processing'}) "
        "RETURN a.role AS role, count(*) AS n ORDER BY role"
    ).data()
    summary = ", ".join(f"{row['role']}={row['n']}" for row in v) or "none"
    return f"psp_role_edges={role_edges}/{len(PSP_ROLES)} nodes_created={nodes_created} [{summary}]"


def seed_pr1_title_tiers(session):
    """ADR-117 PR 1: empty provable non-title garbage (LLM refusal text) to a gap and
    stamp Control.title_en_tier per the verified classification (classify_title_en.py).

    PURIST — NO auto-rehang: no in-graph source value is copied into title_en. title_de
    is left untouched (DE content = ADR-116). MERGE/SET idempotent: a re-run changes
    nothing (conditional WHERE). Scope: Control only (the verified classification);
    Law/Requirement/Risk title_en is a separate follow-up (different source logic).

    DELIBERATELY NOT in the `all` module list: this is a one-time ADR-117 migration
    (run explicitly via `--module pr1_title_tiers`), not a re-runnable baseline seed —
    even though it is idempotent, it does not belong in the standard seed-all baseline.

    Tiers:
      source_verified        title_en == source AND c.title + c.source_file present
      consistent_unverified  title_en == source, but no documented per-title source
      pending                divergent -> official correction via ADR-116 (DE) / 079 (EN)
      gap                    emptied refusal/meta garbage (not a title)
    """
    # 1) delete_to_gap — provable non-title garbage (LLM refusal text: >=3 markers)
    gapped = session.run(
        """
        MATCH (c:Control) WHERE c.title_en IS NOT NULL
          AND toLower(c.title_en) CONTAINS 'i need'
          AND toLower(c.title_en) CONTAINS 'translate'
          AND toLower(c.title_en) CONTAINS 'language'
        REMOVE c.title_en
        SET c.title_en_tier = 'gap'
        RETURN count(c) AS n
        """
    ).single()["n"]

    # 2) tier markers for the remaining title_en (idempotent: only set when different)
    tiered = session.run(
        """
        MATCH (c:Control) WHERE c.title_en IS NOT NULL
        WITH c,
             trim(toString(c.title_en)) AS en,
             trim(toString(coalesce(c.title, c.title_de, ''))) AS src
        WITH c, (en <> '' AND en = src) AS match,
             (c.title IS NOT NULL AND c.source_file IS NOT NULL) AS full_prov
        WITH c, CASE
            WHEN match AND full_prov THEN 'source_verified'
            WHEN match           THEN 'consistent_unverified'
            ELSE 'pending'
        END AS tier
        WHERE coalesce(c.title_en_tier, '') <> tier
        SET c.title_en_tier = tier
        RETURN count(c) AS n
        """
    ).single()["n"]

    dist = session.run(
        "MATCH (c:Control) WHERE c.title_en_tier IS NOT NULL "
        "RETURN c.title_en_tier AS tier, count(*) AS n ORDER BY n DESC"
    ).data()
    summary = ", ".join(f"{r['tier']}={r['n']}" for r in dist)
    return f"gapped={gapped} tiered_changed={tiered} [{summary}]"


def seed_pr2_title_provenance(session):
    """ADR-117 PR 2: per-language source provenance on title_en, matching the PR-1 tier.

    ONLY `source_verified` controls receive a per-title source (`c.source` +
    `c.source_file` — the documented provenance the tier is based on).
    `consistent_unverified` / `pending` / `gap` get NO source: the framework-level
    `c.source` string (e.g. "ISO-27001.pdf") must NOT be reinterpreted as a per-title
    source — that absence is precisely why their tier is not source_verified. Tier and
    source tell the SAME story. MERGE/SET idempotent. Control-scoped. title_de untouched.

    Deliberately NOT in `all` (one-time ADR-117 migration; run via --module pr2_title_provenance).
    """
    stamped = session.run(
        """
        MATCH (c:Control)
        WHERE c.title_en_tier = 'source_verified' AND c.title_en_source IS NULL
        SET c.title_en_source = c.source,
            c.title_en_source_file = c.source_file
        RETURN count(c) AS n
        """
    ).single()["n"]
    # honesty invariant: no per-title source may sit on a non-source_verified tier
    leaked = session.run(
        """
        MATCH (c:Control)
        WHERE c.title_en_source IS NOT NULL AND coalesce(c.title_en_tier,'') <> 'source_verified'
        RETURN count(c) AS n
        """
    ).single()["n"]
    dist = session.run(
        "MATCH (c:Control) WHERE c.title_en_tier IS NOT NULL "
        "RETURN c.title_en_tier AS tier, "
        "sum(CASE WHEN c.title_en_source IS NOT NULL THEN 1 ELSE 0 END) AS with_source, "
        "count(*) AS n ORDER BY tier"
    ).data()
    summary = ", ".join(f"{r['tier']}:src={r['with_source']}/{r['n']}" for r in dist)
    return f"stamped={stamped} leaked_source_wrong_tier={leaked} [{summary}]"


# ── ADR-126 Phase 1a: Law title_en backfill (9 EU-regulation articles, Class A) ──
#
# Additive IS-NULL backfill only — official EN article titles from the CELEX-EN texts
# (no free translation). The 4 DSGVO "Art. X" duplicates + 2 NIS2 overview duplicates
# are intentionally NOT here: they are a dedup, tracked as ADR-126 Addendum 1b.
# CRA Annex I additionally receives its missing `celex` (degree 24, actively consumed).
_CELEX_EN = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:"
ADR126_LAW_TITLE_EN = [
    # (name, article, title_en, celex)  — celex only set when the node's is null (CRA)
    ("DSGVO",     "25",      "Data protection by design and by default",                  None),
    ("DSGVO",     "36",      "Prior consultation",                                        None),
    ("DSGVO",     "40",      "Codes of conduct",                                          None),
    ("DSGVO",     "42",      "Certification",                                             None),
    ("DSGVO",     "82",      "Right to compensation and liability",                       None),
    ("EU AI Act", "3",       "Definitions",                                               None),
    ("EU AI Act", "10",      "Data and data governance",                                  None),
    ("EU AI Act", "13",      "Transparency and provision of information to deployers",    None),
    ("CRA",       "Annex I", "Essential cybersecurity requirements",                      "32024R2847"),
]
# CELEX per regulation, for the source_url_en stamp.
_ADR126_CELEX = {"DSGVO": "32016R0679", "EU AI Act": "32024R1689", "CRA": "32024R2847"}


def seed_adr126_law_title_en(session):
    """ADR-126 Phase 1a: backfill title_en on 9 EU-regulation Law nodes (Class A).

    Additive only (guarded on empty title_en — never overwrites). EN titles are the
    official CELEX-EN article headings; source_url_en = the EUR-Lex EN permalink.
    CRA Annex I also gets its missing `celex`. Idempotent: re-runs are no-ops once filled.
    """
    n = 0
    for name, article, title_en, celex in ADR126_LAW_TITLE_EN:
        r = session.run(
            """
            MATCH (l:Law {name: $name, article: $article})
            WHERE l.title_en IS NULL OR l.title_en = ''
            SET l.title_en      = $title_en,
                l.source_url_en  = $url,
                l.celex          = coalesce($celex, l.celex),
                l.last_verified  = date($today)
            RETURN l
            """,
            name=name, article=article, title_en=title_en,
            url=_CELEX_EN + _ADR126_CELEX[name],
            celex=celex, today="2026-06-16",
        )
        n += len(r.data())
    missing = session.run(
        "MATCH (l:Law) WHERE l.title_en IS NULL OR l.title_en='' RETURN count(*) AS n"
    ).single()["n"]
    filled = session.run(
        "MATCH (l:Law) WHERE l.title_en IS NOT NULL AND l.title_en<>'' RETURN count(*) AS n"
    ).single()["n"]
    return f"backfilled={n}, title_en_filled={filled}, still_missing={missing} (6 dups → Addendum 1b)"


# ── ADR-126 Phase 2: Measure name_en backfill (SDM EN V3.0a Kap. D1, Class A) ────
#
# 1:1 verbatim from the official EN edition, Chapter D1 "Generic Measures" (D1.1–D1.7).
# VERSION-SKEW (read-of-truth 2026-06-16): the DE Measure nodes are SDM v3.1 (DSK
# 14.05.2024), but the only official EN translation is V3.0a (engl. version V1.0c,
# DSK 24.11.2022). The D1 generic-measures set is stable across V3.0a↔V3.1 — all 63
# DE names map 1:1 to V3.0a-EN D1 bullets, 0 orphans → the V3.0a-EN text is valid for
# the V3.1-DE nodes. The provenance label therefore states V3.0a (the EN text's real
# edition), NOT v3.1. Trailing "(B1.x ...)" protection-goal cross-references are stripped
# (they are not part of the measure name; name_de carries none either).
# VERBATIM incl. two source typos preserved deliberately: "an contingency plan" (D1.1)
# and "controler" (D1.4) — they are in the official EN PDF; a later render-cosmetic pass
# (Phase 5) may [sic]-fix them, this is a data-fidelity field, not our error.
_SDM_EN_URL = "https://www.datenschutz-mv.de/static/DS/Dateien/Datenschutzmodell/SDM_V3_en.pdf"
_SDM_EN_SOURCE = "SDM EN V3.0a (engl. version V1.0c, DSK 24.11.2022), Kap. D1"
ADR126_MEASURE_NAME_EN = [
    # D1.1 Availability
    ("d1.1-backup-konzept", "Creation of backups of data, process states, configurations, data structures, transaction histories, etc. according to a tested concept"),
    ("d1.1-dokumentation-syntax", "Documentation of data syntax"),
    ("d1.1-notfallkonzept", "Preparation of an contingency plan for restoring processing activity"),
    ("d1.1-redundanz", "Redundancy of hardware, software and infrastructure"),
    ("d1.1-reparatur-ausweich", "Implementation of repair strategies and backup processes"),
    ("d1.1-schutz-aeussere-einfluesse", "Protection against external influences (malware, sabotage, force majeure)"),
    ("d1.1-vertretungsregeln", "Representation arrangements for absent employees"),
    # D1.2 Integrity
    ("d1.2-aktualitaet-prozesse", "Processes for maintaining the timeliness of data"),
    ("d1.2-berechtigungen-rollen", "documented assignment of authorisations and roles"),
    ("d1.2-haerten-systeme", "Hardening of IT systems so that they have no or as few secondary functionalities as possible"),
    ("d1.2-id-auth-personen-geraete", "Processes for identification and authentication of persons and equipment"),
    ("d1.2-loeschen-berichtigen", "erasure or rectifying of incorrect data"),
    ("d1.2-pruefsummen-signaturen", "Use of checksums, electronic seals and signatures in accordance with a cryptographic concept"),
    ("d1.2-schreib-aenderungsrechte", "Restriction of write and modification permissions"),
    ("d1.2-schutz-spionage-hacking", "Protection against external influences (espionage, hacking)"),
    ("d1.2-sollverhalten-ablaeufe", "Determination of the target behaviour of processes and procedures and regular performance of tests to ascertain or determine the current state of processes"),
    ("d1.2-sollverhalten-tests", "Definition of the intended behaviour of processes and regular tests to determine and document functionality, risks, security gaps and side effects of processes"),
    # D1.3 Confidentiality
    ("d1.3-auth-verfahren", "Implementation of a secure authentication procedure"),
    ("d1.3-berechtigungs-rollenkonz", "Definition of a concept for role-based access control according to the necessity principle on the basis of identity management by the controller"),
    ("d1.3-kontrolle-kanaele", "Specification and monitoring of the use of authorised resources, in particular communication channels"),
    ("d1.3-org-ablaeufe-verpflicht", "Definition and monitoring of organisational processes, internal regulations and contractual obligations (obligation to maintain data secrecy, confidentiality agreements, etc.)"),
    ("d1.3-personalkraft-eingrenzung", "Limitation of authorised personnel to those who are verifiably responsible (locally, professionally), qualified, reliable (if necessary with security clearance) and formally approved, and with whom no conflict of interests may arise in the exercise of their duties"),
    ("d1.3-spezifizierte-umgebungen", "specified environments (buildings, rooms) equipped for processing activities"),
    ("d1.3-verschluesselung-krypto", "Encryption of stored or transferred data and processes for managing and protecting cryptographic information (cryptographic concept)"),
    # D1.4 Unlinkability
    ("d1.4-backdoor-verbot", "regulatory measures to prohibit backdoors and quality assurance audits for compliance in software development"),
    ("d1.4-nutzerkontrollierte-id", "Approval of user-controlled identity management by the controller"),
    ("d1.4-pseudonyme-anon", "Use of purpose specific pseudonyms, anonymisation services, anonymous credentials, processing of pseudonymous or anonymised data"),
    ("d1.4-rechte-einschraenkung", "Restriction of processing, use and transfer permissions"),
    ("d1.4-rollen-zugriffs", "Separation by means of role concepts with graduated access rights on the basis of identity management by the controler and a secure authentication process"),
    ("d1.4-schnittstellen-schliessen", "program-wise omission or deactivation of interfaces in processing methods and components"),
    ("d1.4-trennung-org-grenzen", "Separation according to organisational/departmental boundaries"),
    ("d1.4-zweckaenderungsverfahren", "regulated processes for amending the purposes of the processing"),
    # D1.5 Transparency
    ("d1.5-benachrichtigung-pannen", "Notification of data subjects in the event of data breaches or further processing for another purpose"),
    ("d1.5-dok-bestandteile", "Documentation of the components of processing activities, in particular business processes, databases, data flows and network plans, IT systems used for this purpose, operating procedures, descriptions of processing activities, interaction with other processing activities"),
    ("d1.5-dok-einwilligungen", "Documentation of consents, their revocation and objections"),
    ("d1.5-dok-inventarisierung", "Documentation in the sense of an inventory of all processing activities in accordance with Art. 30 GDPR"),
    ("d1.5-dok-profiling", "Documentation of the factors used for profiling, scoring or semi-automated decisions"),
    ("d1.5-dok-quellen-pannen", "Documentation of the data sources, e. g. the implementation of information duties towards data subjects where their data were collected and the handling of data breaches"),
    ("d1.5-dok-tests-freigabe", "Documentation of tests, of the release and, where appropriate, the data protection impact assessment of new or modified processing activities"),
    ("d1.5-dok-vertraege-zustaend", "Documentation of contracts with internal employees, contracts with external service providers and third parties from whom data is collected or transmitted, business distribution plans, responsibility regulations"),
    ("d1.5-info-betroffene", "Provision of information on the processing of personal data to data subjects"),
    ("d1.5-nachverfolgbarkeit-rechte", "Traceability of the activities of the controller for granting data subjects' rights"),
    ("d1.5-protokoll-konzept", "Documentation of processing by means of protocols on the basis of a logging and evaluation concept"),
    ("d1.5-protokoll-zugriffe", "Logging of accesses and changes"),
    ("d1.5-versionierung", "Versioning"),
    # D1.6 Intervenability
    ("d1.6-deaktivierung-funktion", "Possibility of deactivating individual functionalities without affecting the overall system"),
    ("d1.6-dok-aenderungen", "documented processing of faults, problem handling and changes to processing activities as well as to technical and organisational measures"),
    ("d1.6-einwilligung-widerruf", "Measures for differentiated consent, revocation and objection options"),
    ("d1.6-export-iface", "Operation of an interface for structured, machine-readable data for the retrieval by data subjects"),
    ("d1.6-id-auth-betroffene", "Identification and authentication of persons who wish to exercise data subjects' rights"),
    ("d1.6-optionen-betroffene", "Provision of options for data subjects in order to be able to set up programs in line with data protection requirements"),
    ("d1.6-sperrkennzeichen-felder", "Creation of necessary data fields, e. g. for blocking indicators, notifications, consents, objections, counterstatements"),
    ("d1.6-spoc", "Establishment of a Single Point of Contact (SPoC) for data subjects"),
    ("d1.6-standard-abfrage-iface", "Implementation of standardised query and dialogue interfaces for data subjects to assert and/or enforce claims"),
    ("d1.6-zusammenstellung-loesch", "operational possibility of compiling, consistently rectifying, blocking and erasure of all data stored on a person"),
    # D1.7 Data Minimisation
    ("d1.7-attribute-reduktion", "Reduction of recorded attributes of data subjects"),
    ("d1.7-bevorzugung-automatisiert", "Preference for automated processes (not decision processes), which make it unnecessary to gain knowledge of processed data and limit influence in comparison to dialogue controlled processes"),
    ("d1.7-datenmasken-pseudo", "Implementation of data masks that suppress data fields, and automatic blocking and erasure routines, pseudonymisation and anonymisation processes"),
    ("d1.7-kenntnisnahme-reduktion", "Reduction of the possibility of gaining knowledge of existing data"),
    ("d1.7-loeschkonzept", "Definition and implementation of an erasure concept"),
    ("d1.7-prozess-aenderungen-kontr", "Rules for the monitoring of processes to change processing activities"),
    ("d1.7-verarbeitungsoptionen", "Reduction of processing options in each processing step"),
    ("d1.7-voreinstellungen-personen", "Establishing default settings for data subjects which limit the processing of their data to what is necessary for the purpose of the processing"),
]


def seed_adr126_measure_name_en(session):
    """ADR-126 Phase 2: backfill name_en on 63 Measure nodes (SDM EN V3.0a Kap. D1).

    Additive only (guarded on empty name_en — never overwrites). Text is 1:1 verbatim
    from the official EN edition's Chapter D1; source_en/source_url_en record the EN
    edition (V3.0a), distinct from the node's DE source (v3.1). Idempotent.
    """
    n = 0
    for mid, name_en in ADR126_MEASURE_NAME_EN:
        r = session.run(
            """
            MATCH (m:Measure {id: $id})
            WHERE m.name_en IS NULL OR m.name_en = ''
            SET m.name_en       = $name_en,
                m.source_en      = $source_en,
                m.source_url_en  = $url,
                m.last_verified  = date($today)
            RETURN m
            """,
            id=mid, name_en=name_en, source_en=_SDM_EN_SOURCE,
            url=_SDM_EN_URL, today="2026-06-16",
        )
        n += len(r.data())
    missing = session.run(
        "MATCH (m:Measure) WHERE m.name_en IS NULL OR m.name_en='' RETURN count(*) AS n"
    ).single()["n"]
    filled = session.run(
        "MATCH (m:Measure) WHERE m.name_en IS NOT NULL AND m.name_en<>'' RETURN count(*) AS n"
    ).single()["n"]
    return f"backfilled={n}, name_en_filled={filled}, still_missing={missing}"


# ── ADR-126 Phase 4: DocumentType + UseCase EN (Class B authored + Annex-III A) ──
#
# Class B = Lex-authored EN (source_en='lex-authored'). Only the 10 RENDERED
# DocumentTypes (description_de IS NOT NULL) are in scope; the 9 non-rendered catalog
# types are deliberately skipped. UseCase reason_en is split: 9 Annex-III headings are
# verbatim from CELEX 32024R1689 (field-level reason_en_source[_url]); the other 10 are
# authored. healthcare_decision.reason_en is HELD (null) — its annex_iii_nr="2" conflicts
# with the official Annex III No. 2 ("Critical infrastructure"); medical devices are
# Art. 6(1)/Annex I, not Annex III → data error, fix in Addendum 1b, no best-guess.
_CELEX_AIACT_EN = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689"
_ANNEX_III_SRC = "EU AI Act Annex III, CELEX 32024R1689 (EN)"

# (type, name_en, description_en) — 10 rendered DocumentTypes
ADR126_DOCTYPE_EN = [
    ("TOM", "Technical and Organisational Measures",
     "Technical and organisational measures (TOMs) are concrete security safeguards a company must implement under Art. 32 GDPR to protect personal data. Typical examples: encryption, access controls, backups, employee training, security policies. TOMs must reflect the state of the art and be reviewed regularly."),
    ("AVV", "Data Processing Agreement",
     "A Data Processing Agreement (DPA) is a contract that companies must conclude under Art. 28 GDPR with every service provider that processes personal data on their behalf. Typical examples: cloud providers, email services, SaaS tools, payment service providers. The DPA defines what the processor may do with the data and which protective measures it must observe."),
    ("VVT", "Records of Processing Activities",
     "The Records of Processing Activities (RoPA) is internal documentation required by Art. 30 GDPR. It captures all data processing in the company: which data is processed, for what purpose, who has access, how long it is stored, and which legal basis applies. The RoPA is mandatory for companies with more than 250 employees or where high-risk processing takes place."),
    ("DSFA", "Data Protection Impact Assessment",
     "A Data Protection Impact Assessment (DPIA) is a risk analysis under Art. 35 GDPR that must be carried out before starting high-risk data processing. Typical triggers: AI systems for profiling, biometric data, automated decisions, large-scale tracking. The result is a risk assessment and an action plan."),
    ("SCC", "Standard Contractual Clauses (EU-US)",
     "Standard Contractual Clauses (SCCs) are contract templates approved by the European Commission for data transfers to third countries outside the EU/EEA (Art. 46 GDPR). They are required where no adequacy decision exists — e.g. for US services such as AWS, Google, Stripe or Postmark. The SCCs adopted by the Commission in 2021 apply."),
    ("KI_Policy", "AI Usage Policy",
     "An AI usage policy is an internal rule on how employees may use AI systems. It establishes the AI literacy required by EU AI Act Art. 4 and governs: which AI tools are permitted, which data may be entered, who is responsible for AI results, and how errors are handled. It protects against uncontrolled AI use and data protection violations."),
    ("KI_System_Dokumentation", "AI System Documentation",
     "The AI system documentation describes an AI system technically and organisationally: purpose, mode of operation, data used, known limits and risks. The EU AI Act requires it in particular for high-risk systems (Art. 11). Typical contents: which model, what it was trained on, how results are verified, and what human oversight applies. It is the basis for audits."),
    ("AI_Act_Manifest", "EU AI Act Risk Manifest",
     "The EU AI Act Manifest documents how an AI system meets the requirements of the EU AI Regulation (Reg. 2024/1689). It assigns the system to a risk class (minimal, limited, high) and records the resulting obligations. Typical triggers: AI assessing individuals, automated decisions, generative AI. It is the basis for demonstrating compliant AI use to authorities and customers."),
    ("Datenschutzerklaerung", "Privacy Policy",
     "The privacy policy fulfils the duty to inform data subjects under GDPR Art. 13 and 14. It must be available on every website, app or digital application that processes personal data. Mandatory information includes: controller and contact details, the data protection officer where applicable, purposes and legal bases of each processing activity, categories of recipients, third-country transfers, storage period, data subject rights and the right to lodge a complaint with the supervisory authority. Violations can be penalised with fines of up to EUR 20 million or 4% of total worldwide annual turnover."),
    ("Impressum", "Legal Notice (Impressum) / Provider Identification",
     "The legal notice (Impressum) is the statutory provider identification under § 5 DDG (Digitale-Dienste-Gesetz) and § 18 MStV. It is mandatory for all commercially operated websites, apps and social media profiles. Mandatory information: name and address of the provider, contact details including email, commercial register and registration number (for legal entities), VAT ID, and the supervisory authority for activities requiring authorisation. The legal notice must be easily recognisable, directly accessible and permanently available."),
]

# (type, title_en, action_en, reason_en, reason_src)
#   reason_src: 'celex' = Annex-III verbatim heading; 'lex' = authored; None = held
ADR126_USECASE_EN = [
    ("ai_assistant_general", "General AI Assistant",
     "Inform users that they are interacting with AI",
     "Transparency obligation for AI interaction (Art. 50)", "lex"),
    ("ai_autonomous_agent", "Autonomous AI Agent",
     "Inform users that they are interacting with an autonomous AI agent. Ensure human oversight for critical actions.",
     "Transparency obligation: users must be informed that they are interacting with an autonomous AI system", "lex"),
    ("ai_content_generator", "AI-Generated Content (Text, Image, Audio, Video)",
     "Machine-readable marking + visible notice of AI generation",
     "Deepfake labelling obligation: synthetic content must be marked as AI-generated (Art. 50)", "lex"),
    ("biometric_categorization", "Biometric Categorisation and Identification",
     "Conformity assessment, strict data protection review, DPIA where applicable",
     "Annex III No. 1: Biometrics, in so far as their use is permitted under relevant Union or national law", "celex"),
    ("credit_scoring", "Creditworthiness Assessment and Credit Scoring",
     "Conformity assessment, registration in the EU database, explainability of the decision",
     "Annex III No. 5: Access to and enjoyment of essential private services and essential public services and benefits", "celex"),
    ("critical_infrastructure_mgmt", "AI in the Operation of Critical Infrastructure",
     "Conformity assessment, security analysis, contingency plan, registration in the EU database",
     "Annex III No. 2: Critical infrastructure", "celex"),
    ("customer_service_chatbot", "Customer Service Chatbot / FAQ Bot",
     "Display the notice \"You are speaking with an AI\" before or at the start of the conversation",
     "Transparency obligation: users must be informed that they are interacting with an AI system", "lex"),
    ("education_assessment", "AI-Supported Education and Examination Assessment",
     "Conformity assessment, human oversight, transparency towards data subjects",
     "Annex III No. 3: Education and vocational training", "celex"),
    ("emotion_recognition_system", "Emotion Recognition System",
     "Check deployment context: workplace/education = prohibited (Art. 5(1)(f)); otherwise high-risk deployer obligations (Art. 26) and inform affected persons per Art. 50(3)",
     "Annex III No. 1(c): emotion recognition — high risk; prohibited in workplace and education contexts (Art. 5(1)(f)); Art. 50(3) transparency applies in addition", "celex"),
    ("healthcare_decision", "AI-Supported Medical Diagnosis and Treatment Decision",
     "Conformity assessment, clinical evaluation, DPIA required, human oversight by medical professionals",
     None, None),  # reason_en HELD (F1 — annex_iii_nr=2 data error)
    ("hr_performance_evaluation", "AI-Supported Performance Evaluation and Employee Monitoring",
     "Conformity assessment, human oversight, fundamental rights impact assessment",
     "Annex III No. 4: Employment, workers management and access to self-employment", "celex"),
    ("hr_recruitment_screening", "AI-Supported Application Screening and Recruitment",
     "Conformity assessment, registration in the EU database, human oversight, technical documentation",
     "Annex III No. 4: Employment, workers management and access to self-employment", "celex"),
    ("justice_democratic_process", "AI in the Administration of Justice and Democratic Decision-Making",
     "Conformity assessment + EU database registration required",
     "Annex III No. 8: Administration of justice and democratic processes", "celex"),
    ("law_enforcement_ai", "AI for Law Enforcement Purposes",
     "Strict conformity assessment, fundamental rights impact assessment, approval by the supervisory authority required",
     "Annex III No. 6: Law enforcement, in so far as their use is permitted under relevant Union or national law", "celex"),
    ("migration_border_control", "AI-Supported Migration Control and Asylum Procedures",
     "Conformity assessment + EU database registration required",
     "Annex III No. 7: Migration, asylum and border control management, in so far as their use is permitted under relevant Union or national law", "celex"),
    ("realtime_remote_biometric_id", "Real-Time Remote Biometric Identification in Public Spaces",
     "PROHIBITED (exceptions only for law enforcement under Art. 5(2))",
     "Art. 5(1): real-time remote biometric identification in publicly accessible spaces — generally PROHIBITED (exceptions Art. 5(2))", "lex"),
    ("recommendation_engine", "Recommendation System (Products, Content)",
     "No obligations. Transparency towards users recommended.",
     "No regulatory use case, provided no high-risk criteria are met", "lex"),
    ("social_scoring_public", "Social Scoring by Public Authorities",
     "PROHIBITED — use not permitted",
     "Art. 5(1)(c): evaluation of natural persons by public authorities — PROHIBITED", "lex"),
    ("spam_filter", "Spam and Content Filter",
     "No obligations. Voluntary code of conduct recommended.",
     "No regulatory use case — minimal risk", "lex"),
    ("subliminal_manipulation", "Subliminal Manipulation of Persons",
     "PROHIBITED — use not permitted",
     "Art. 5(1)(a): manipulation beyond a person's awareness — PROHIBITED", "lex"),
]


def seed_adr126_doctype_en(session):
    """ADR-126 Phase 4: author name_en + description_en on the 10 rendered DocumentTypes.

    Class B (lex-authored). Guarded on description_de IS NOT NULL (rendered set only)
    AND additive on description_en. The 9 non-rendered catalog types are skipped.
    """
    n = 0
    for dtype, name_en, desc_en in ADR126_DOCTYPE_EN:
        r = session.run(
            """
            MATCH (d:DocumentType {type: $type})
            WHERE d.description_de IS NOT NULL
              AND (d.description_en IS NULL OR d.description_en = '')
            SET d.name_en        = $name_en,
                d.description_en  = $desc_en,
                d.source_en       = 'lex-authored',
                d.last_verified   = date($today)
            RETURN d
            """,
            type=dtype, name_en=name_en, desc_en=desc_en, today="2026-06-16",
        )
        n += len(r.data())
    filled = session.run(
        "MATCH (d:DocumentType) WHERE d.description_en IS NOT NULL AND d.description_en<>'' "
        "RETURN count(*) AS n"
    ).single()["n"]
    return f"doctype_authored={n}, description_en_filled={filled}/10 (9 non-rendered skipped)"


def seed_adr126_usecase_en(session):
    """ADR-126 Phase 4: author title_en + deployer_action_en (all 20) + reason_en.

    title/action = Class B (lex-authored). reason_en split: 9 Annex-III headings verbatim
    from CELEX 32024R1689 (field-level reason_en_source[_url]); 10 authored; 1 held
    (healthcare_decision — annex_iii_nr=2 data error). Additive guards throughout.
    """
    ta, re_a, re_b = 0, 0, 0
    for utype, title_en, action_en, reason_en, reason_src in ADR126_USECASE_EN:
        r = session.run(
            """
            MATCH (u:UseCase {type: $type})
            WHERE u.title_en IS NULL OR u.title_en = ''
            SET u.title_en           = $title_en,
                u.deployer_action_en = $action_en,
                u.source_en          = 'lex-authored',
                u.last_verified      = date($today)
            RETURN u
            """,
            type=utype, title_en=title_en, action_en=action_en, today="2026-06-16",
        )
        ta += len(r.data())
        if reason_src is None:          # held (healthcare_decision)
            continue
        if reason_src == "celex":
            r2 = session.run(
                """
                MATCH (u:UseCase {type: $type})
                WHERE u.reason_en IS NULL OR u.reason_en = ''
                SET u.reason_en            = $reason_en,
                    u.reason_en_source     = $src,
                    u.reason_en_source_url = $url
                RETURN u
                """,
                type=utype, reason_en=reason_en, src=_ANNEX_III_SRC, url=_CELEX_AIACT_EN,
            )
            re_a += len(r2.data())
        else:                            # 'lex'
            r2 = session.run(
                """
                MATCH (u:UseCase {type: $type})
                WHERE u.reason_en IS NULL OR u.reason_en = ''
                SET u.reason_en        = $reason_en,
                    u.reason_en_source = 'lex-authored'
                RETURN u
                """,
                type=utype, reason_en=reason_en,
            )
            re_b += len(r2.data())
    held = session.run(
        "MATCH (u:UseCase) WHERE u.title_en IS NOT NULL AND (u.reason_en IS NULL OR u.reason_en='') "
        "RETURN count(*) AS n"
    ).single()["n"]
    return f"usecase_title_action={ta}, reason_celex={re_a}, reason_authored={re_b}, reason_held={held}"


# ── ADR-126 Phase 3a: NIST CSF 2 control-title verification (ADR-117 mechanism) ──
#
# NIST CSF 2.0 is EN-native: title_en IS the source, verified verbatim against the
# official framework (CSWP 29). Promotes title_en_tier -> source_verified. Three titles
# were wrong and are corrected (overwrite): PR "Personal data protection" -> "Protect",
# DE "Detection" -> "Detect", RS null(gap) -> "Respond". The other 9 already match.
# Guard: only promotes rows not yet source_verified (idempotent re-run = 0).
_NIST_CSF_SRC = "NIST CSF 2.0, doi.org/10.6028/NIST.CSWP.29"
ADR126_NIST_TITLES = [
    # (id, official title_en)  — 6 Functions + 6 Categories, verbatim CSF 2.0
    ("GV", "Govern"),
    ("ID", "Identify"),
    ("PR", "Protect"),                  # was "Personal data protection" (wrong)
    ("DE", "Detect"),                   # was "Detection" (wrong)
    ("RS", "Respond"),                  # was null (gap)
    ("RC", "Recover"),
    ("ID.RA", "Risk Assessment"),
    ("PR.AA", "Identity Management, Authentication, and Access Control"),
    ("PR.DS", "Data Security"),
    ("PR.PS", "Platform Security"),
    ("DE.CM", "Continuous Monitoring"),
    ("RS.MA", "Incident Management"),
]


def seed_adr126_nist_title_verify(session):
    """ADR-126 Phase 3a: verify NIST CSF 2 control titles, promote to source_verified.

    EN-native framework — title_en checked verbatim against the official CSF 2.0 (CSWP 29).
    Sets the official title_en (corrects PR/DE, fills RS gap), promotes title_en_tier ->
    source_verified, stamps title_en_source. Guard: only rows not yet source_verified.
    """
    n = 0
    for cid, title_en in ADR126_NIST_TITLES:
        r = session.run(
            """
            MATCH (c:Control {framework: 'NIST_CSF_2', id: $id})
            WHERE coalesce(c.title_en_tier, '') <> 'source_verified'
            SET c.title_en        = $title_en,
                c.title_en_tier   = 'source_verified',
                c.title_en_source = $src,
                c.last_verified   = date($today)
            RETURN c
            """,
            id=cid, title_en=title_en, src=_NIST_CSF_SRC, today="2026-06-16",
        )
        n += len(r.data())
    dist = session.run(
        "MATCH (c:Control {framework:'NIST_CSF_2'}) RETURN c.title_en_tier AS tier, count(*) AS n "
        "ORDER BY tier"
    ).data()
    summary = ", ".join(f"{r['tier']}:{r['n']}" for r in dist)
    return f"promoted={n} [{summary}]"


# ── ADR-126 Phase 3c: OWASP control-title verification (Web/LLM/API, 30 controls) ──
#
# Verbatim against the official OWASP editions (verified 2026-06-16):
#   Web = Top 10:2025 (owasp.org/Top10/2025/); LLM = Top 10 for LLM Apps 2025
#   (genai.owasp.org/llm-top-10/); API = API Security Top 10 2023 (owasp.org/API-Security/2023).
# 12 corrections (overwrite of corrupt title_en, incl. LLM-hallucinations) + 18 promote-only.
# API node `source` was a bare filename → sanitised to a versioned string. The layer
# (00_frameworks.cypher) sets only `title` ON CREATE — title_en is owned here (durable in 'all').
# Guard: only rows not yet source_verified (idempotent re-run = 0).
_OWASP_SRC = {
    "OWASP_Top10":     "OWASP Top 10:2025, owasp.org/Top10/2025/",
    "OWASP_LLM_Top10": "OWASP Top 10 for LLM Applications 2025, genai.owasp.org/llm-top-10/",
    "OWASP_API_Top10": "OWASP API Security Top 10 2023, owasp.org/API-Security/editions/2023/",
}
ADR126_OWASP_TITLES = [
    # (framework, id, official title_en)
    ("OWASP_Top10", "A01", "Broken Access Control"),
    ("OWASP_Top10", "A02", "Security Misconfiguration"),
    ("OWASP_Top10", "A03", "Software Supply Chain Failures"),
    ("OWASP_Top10", "A04", "Cryptographic Failures"),
    ("OWASP_Top10", "A05", "Injection"),                              # was "Injection attack"
    ("OWASP_Top10", "A06", "Insecure Design"),
    ("OWASP_Top10", "A07", "Authentication Failures"),
    ("OWASP_Top10", "A08", "Software or Data Integrity Failures"),    # was "Integrity Failures"
    ("OWASP_Top10", "A09", "Security Logging and Alerting Failures"), # was "Logging and Alerting Failures"
    ("OWASP_Top10", "A10", "Mishandling of Exceptional Conditions"),  # was "Mishandling of Exceptions"
    ("OWASP_LLM_Top10", "LLM01", "Prompt Injection"),                 # was "Prompt Injection Attack"
    ("OWASP_LLM_Top10", "LLM02", "Sensitive Information Disclosure"), # was "Disclosure of Sensitive Personal Data"
    ("OWASP_LLM_Top10", "LLM03", "Supply Chain"),
    ("OWASP_LLM_Top10", "LLM04", "Data and Model Poisoning"),
    ("OWASP_LLM_Top10", "LLM05", "Improper Output Handling"),
    ("OWASP_LLM_Top10", "LLM06", "Excessive Agency"),                 # was "Agentschap overmatig" (NL halluc.)
    ("OWASP_LLM_Top10", "LLM07", "System Prompt Leakage"),            # was "Unauthorized Disclosure of System Instructions"
    ("OWASP_LLM_Top10", "LLM08", "Vector and Embedding Weaknesses"),
    ("OWASP_LLM_Top10", "LLM09", "Misinformation"),
    ("OWASP_LLM_Top10", "LLM10", "Unbounded Consumption"),            # was "Unrestricted consumption"
    ("OWASP_API_Top10", "API1", "Broken Object Level Authorization"),
    ("OWASP_API_Top10", "API2", "Broken Authentication"),
    ("OWASP_API_Top10", "API3", "Broken Object Property Level Authorization"),  # was "Broken Object Level Authorization" (= API1 dup)
    ("OWASP_API_Top10", "API4", "Unrestricted Resource Consumption"),
    ("OWASP_API_Top10", "API5", "Broken Function Level Authorization"),  # was "Broken Function Level Access Control"
    ("OWASP_API_Top10", "API6", "Unrestricted Access to Sensitive Business Flows"),
    ("OWASP_API_Top10", "API7", "Server Side Request Forgery"),
    ("OWASP_API_Top10", "API8", "Security Misconfiguration"),
    ("OWASP_API_Top10", "API9", "Improper Inventory Management"),
    ("OWASP_API_Top10", "API10", "Unsafe Consumption of APIs"),       # was "Unsafe Use of Active Pharmaceutical Ingredients" (halluc.)
]


def seed_adr126_owasp_title_verify(session):
    """ADR-126 Phase 3c: verify OWASP Web/LLM/API control titles, promote to source_verified.

    Sets the official title_en verbatim (corrects 12 corrupt titles incl. hallucinations,
    promotes 18), title_en_tier -> source_verified, title_en_source per edition. Also
    sanitises the OWASP_API_Top10 node `source` (was a bare filename). Guard: rows not
    yet source_verified. The layer owns `title` (ON CREATE); title_en is owned here.
    """
    n = 0
    for fw, cid, title_en in ADR126_OWASP_TITLES:
        r = session.run(
            """
            MATCH (c:Control {framework: $fw, id: $id})
            WHERE coalesce(c.title_en_tier, '') <> 'source_verified'
            SET c.title_en        = $title_en,
                c.title_en_tier   = 'source_verified',
                c.title_en_source = $src,
                c.last_verified   = date($today)
            RETURN c
            """,
            fw=fw, id=cid, title_en=title_en, src=_OWASP_SRC[fw], today="2026-06-16",
        )
        n += len(r.data())
    # Sanitise the OWASP API node `source` (was the bare filename "owasp-api-security-top-10.pdf")
    api_src = session.run(
        """
        MATCH (c:Control {framework: 'OWASP_API_Top10'})
        WHERE c.source = 'owasp-api-security-top-10.pdf'
        SET c.source = 'OWASP API Security Top 10 2023'
        RETURN count(c) AS n
        """
    ).single()["n"]
    dist = session.run(
        "MATCH (c:Control) WHERE c.framework IN ['OWASP_Top10','OWASP_LLM_Top10','OWASP_API_Top10'] "
        "RETURN c.framework AS fw, c.title_en_tier AS tier, count(*) AS n ORDER BY fw, tier"
    ).data()
    summary = "; ".join(f"{r['fw'].replace('OWASP_','').replace('_Top10','')}:{r['tier']}={r['n']}" for r in dist)
    return f"promoted={n}, api_source_sanitised={api_src} [{summary}]"


# ── ADR-126 Phase 3b: BSI Grundschutz control-title verification (22, Ed. 2022 EN) ──
#
# Verbatim against the official BSI IT-Grundschutz Compendium, Edition 2022 (EN), module
# index. EDITION SKEW: DE nodes are version="2023"; the EN compendium edition is 2022 —
# the Baustein set/titles are stable 2022<->2023 for these 22, so source_en honestly states
# Ed. 2022. The ID-reconcile OPS.1.1 -> OPS.1.1.2 (no standalone OPS.1.1 module exists) is a
# one-time live MCP migration done separately; the layer (00_frameworks.cypher) is fixed to
# MERGE OPS.1.1.2 directly so fresh seeds never recreate OPS.1.1. 3 substantive corrections:
# CON.3 "Data security concept" -> "Backup Concept" (Datensicherung=backup); ORP.3 wording;
# APP.3.2 singular->plural. 9 Title-Case normalisations. Guard: rows not yet source_verified.
_BSI_SRC = "BSI IT-Grundschutz Compendium, Edition 2022 (bsi.bund.de)"
ADR126_BSI_TITLES = [
    # (id [official Komp.-ID], official EN title — verbatim Ed. 2022)
    ("APP.3.1",   "Web Applications and Web Services"),
    ("APP.3.2",   "Web Servers"),                                  # was "Web server"
    ("APP.4.3",   "Relational Database Systems"),
    ("APP.6",     "General Software"),
    ("CON.1",     "Crypto Concept"),
    ("CON.2",     "Data Protection"),
    ("CON.3",     "Backup Concept"),                               # was "Data security concept" (mistranslation)
    ("CON.10",    "Development of Web Applications"),
    ("DER.2.1",   "Security Incident Handling"),
    ("ISMS.1",    "Security Management"),
    ("NET.1.1",   "Network Architecture and Design"),
    ("OPS.1.1.2", "Proper IT Administration"),                     # ID reconciled from OPS.1.1
    ("OPS.1.1.3", "Patch and Change Management"),
    ("OPS.1.1.5", "Logging"),
    ("OPS.1.2.4", "Teleworking"),
    ("OPS.1.2.5", "Remote Maintenance"),
    ("OPS.2.2",   "Cloud Usage"),
    ("ORP.1",     "Organisation"),
    ("ORP.3",     "Awareness and Training in Information Security"),  # was "Information security awareness and training"
    ("ORP.4",     "Identity and Access Management"),
    ("SYS.1.1",   "General Server"),
    ("SYS.2.1",   "General Client"),                               # was "General client"
]


def seed_adr126_bsi_title_verify(session):
    """ADR-126 Phase 3b: verify BSI Grundschutz control titles, promote to source_verified.

    Sets the official EN title_en (verbatim Ed. 2022 compendium), title_en_tier ->
    source_verified, title_en_source. Keyed on the reconciled official IDs (OPS.1.1.2).
    Guard: rows not yet source_verified. DE c.source/c.version untouched. Idempotent.
    """
    n = 0
    for cid, title_en in ADR126_BSI_TITLES:
        r = session.run(
            """
            MATCH (c:Control {framework: 'BSI_Grundschutz', id: $id})
            WHERE coalesce(c.title_en_tier, '') <> 'source_verified'
            SET c.title_en        = $title_en,
                c.title_en_tier   = 'source_verified',
                c.title_en_source = $src,
                c.last_verified   = date($today)
            RETURN c
            """,
            id=cid, title_en=title_en, src=_BSI_SRC, today="2026-06-16",
        )
        n += len(r.data())
    dist = session.run(
        "MATCH (c:Control {framework:'BSI_Grundschutz'}) RETURN c.title_en_tier AS tier, count(*) AS n "
        "ORDER BY tier"
    ).data()
    summary = ", ".join(f"{r['tier']}:{r['n']}" for r in dist)
    return f"promoted={n} [{summary}]"


# ── B-2/L8 (EN package, 2026-07-16): Service descriptor EN twins ─────────────
# processing_purpose / data_categories are German free text in the graph with
# no _en twin — they rendered verbatim into the EN AVV §2 / VVT / SCC /
# KI-System tables. lex-authored translations of the curated DE values
# (exported from the live graph 2026-07-16, cross-read). Services whose DE
# purpose is empty stay empty here — the render resolver falls back to the
# EN category default with the honest inferred marker (purpose_map).
# data_categories_en is always a comma-separated STRING (both renderers
# split strings; keeps one shape regardless of the DE value's str/list form).
# Provenance: descriptors_en_source on the node.

SERVICE_EN_DESCRIPTORS = [
    # (name, processing_purpose_en | None, data_categories_en)
    ("AWS", "Server hosting, cloud infrastructure, compute, storage", "Server logs, IP addresses, technical connection data, hosted application data"),
    ("AWS S3", "Object storage, file hosting, backup", "Files and objects of all kinds, potentially personal data in stored files"),
    ("Amplitude", None, "Event data, user IDs, session data, usage behaviour, device data, IP addresses"),
    ("Anthropic", "AI-assisted text generation and processing", "API requests, model inputs and outputs, potentially personal content in prompts"),
    ("Auth0", "Authentication, authorisation, identity management", "Authentication data, e-mail addresses, password hashes, login logs, MFA data"),
    ("Azure", "Server hosting, cloud infrastructure, compute, storage", "Server logs, IP addresses, technical connection data, hosted application data"),
    ("Chroma", None, "Embedding vectors, indexed documents, potentially personal content"),
    ("Clerk", "Authentication, authorisation, identity management", "Authentication data, e-mail addresses, password hashes, login logs, MFA data"),
    ("Cloudflare", "CDN, DDoS protection, DNS, WAF", "IP addresses, HTTP requests, DNS queries, security logs"),
    ("Cloudinary", "Media hosting, image optimisation, CDN delivery", "Image and video files, media data, potentially personal content in media"),
    ("Datadog", "Monitoring, observability, APM, log management", "Application logs, metrics, traces, performance data, potentially personal data in logs"),
    ("DigitalOcean", "Server hosting, cloud infrastructure, compute, storage", "Server logs, IP addresses, technical connection data, hosted application data"),
    ("Firebase", "Backend-as-a-Service, authentication, realtime database, storage", "Application data, user data, authentication data, realtime data, push tokens"),
    ("Firecrawl", None, "Crawled web content, URLs, potentially personal content from web sources"),
    ("Fly.io", "Server hosting, cloud infrastructure, compute, storage", "Server logs, IP addresses, technical connection data, hosted application data"),
    ("GitHub Actions", "CI/CD automation, build, test, deploy", "Source code, build logs, environment variables, CI/CD artifacts"),
    ("Google Analytics", "Web analytics, reach measurement, user behaviour", "IP addresses (anonymised), usage behaviour, page views, session data, device data"),
    ("Google Cloud", "Server hosting, cloud infrastructure, compute, storage", "Server logs, IP addresses, technical connection data, hosted application data"),
    ("Google Gemini", "AI-assisted text generation and processing", "API requests, model inputs and outputs, potentially personal content in prompts"),
    ("HashiCorp Vault", None, "Encrypted secrets, audit logs, access metadata"),
    ("Hetzner", "Server hosting, infrastructure provisioning", "Server logs, IP addresses, technical connection data"),
    ("HubSpot", "CRM, customer communication, support, marketing automation", "Contact data, e-mail addresses, communication history, CRM records, support tickets"),
    ("Hugging Face", "AI model hosting, inference, model hub", "Model inputs and outputs, API requests, potentially training data"),
    ("Intercom", "CRM, customer communication, support, marketing automation", "Contact data, e-mail addresses, communication history, CRM records, support tickets"),
    ("Langfuse", "LLM observability, audit trail, A/B testing", "LLM prompts, responses, traces, scores"),
    ("Mailchimp", "E-mail marketing, newsletters, marketing automation", "E-mail addresses, names, campaign interactions, open and click rates, segmentation data"),
    ("Mistral AI", "AI-assisted text generation and processing", "API requests, model inputs and outputs, potentially personal content in prompts"),
    ("Mixpanel", "Web analytics, user behaviour, product analytics", "IP addresses, usage behaviour, page views, session data, device data"),
    ("Mollie", None, "Payment data, card data (tokenised), billing addresses, transaction data"),
    ("MongoDB", None, "Application data, database content, logs"),
    ("Neon", "Database hosting, data storage", "Application data, database content, connection logs"),
    ("Netlify", "Server hosting, cloud infrastructure, compute, storage", "Server logs, IP addresses, technical connection data, hosted application data"),
    ("OpenAI", "AI-assisted text generation and processing", "API requests, model inputs and outputs, potentially personal content in prompts"),
    ("PayPal", "Payment processing, checkout, fraud prevention", "Payment data, PayPal account data, transaction history, billing addresses"),
    ("PlanetScale", "Database hosting, data storage", "Application data, database content, connection logs"),
    ("Plausible", "Web analytics, user behaviour, product analytics", "IP addresses, usage behaviour, page views, session data, device data"),
    ("PostHog", "Web analytics, user behaviour, product analytics", "IP addresses, usage behaviour, page views, session data, device data"),
    ("Postmark", "Transactional e-mail, e-mail delivery", "E-mail addresses, e-mail content, delivery metadata, delivery logs"),
    ("Railway", "Server hosting, cloud infrastructure, compute, storage", "Server logs, IP addresses, technical connection data, hosted application data"),
    ("Render", "Server hosting, cloud infrastructure, compute, storage", "Server logs, IP addresses, technical connection data, hosted application data"),
    ("Replicate", None, "API requests, model inputs and outputs, potentially personal content in prompts"),
    ("Resend", "Transactional e-mail, e-mail delivery", "E-mail addresses, e-mail content, delivery metadata, delivery logs"),
    ("SendGrid", "Transactional e-mail, marketing e-mail, e-mail delivery", "E-mail addresses, e-mail content, delivery metadata, open and click rates"),
    ("Sentry", "Error tracking, performance monitoring, debugging", "Error logs, stack traces, potentially personal data in error reports, IP addresses"),
    ("Stripe", "Payment processing, fraud prevention, invoicing", "Payment data, card data (tokenised), billing addresses, transaction data"),
    ("Supabase", "Database hosting, authentication, storage, realtime features", "Application data, user data, authentication data, logs, database content"),
    ("Telegram", None, "Message content, phone numbers, user IDs, chat metadata"),
    ("Twilio", "SMS delivery, voice communication, 2FA", "Phone numbers, SMS content, call metadata, communication data"),
    ("Vercel", "Server hosting, cloud infrastructure, compute, storage", "Server logs, IP addresses, technical connection data, hosted application data"),
    ("eRecht24", None, "API requests, company data, configuration parameters"),
]


def seed_service_en_descriptors(session):
    """B-2/L8: EN twins for service descriptors (MATCH-only, idempotent).

    SETs processing_purpose_en (where a curated EN purpose exists) and
    data_categories_en on existing Service nodes. Never creates nodes; a
    missing service is counted, not an error (fresh seeds may not carry
    every curated name yet)."""
    n = 0
    missing = []
    for name, purpose_en, cats_en in SERVICE_EN_DESCRIPTORS:
        r = session.run(
            "MATCH (s:Service {name: $name}) "
            "SET s.data_categories_en = $cats, "
            "    s.descriptors_en_source = 'lex-authored translation' "
            + (", s.processing_purpose_en = $purpose " if purpose_en else "")
            + "RETURN s.name AS name",
            name=name, cats=cats_en,
            **({"purpose": purpose_en} if purpose_en else {}),
        ).single()
        if r:
            n += 1
        else:
            missing.append(name)
    miss = f", missing={missing[:3]}" if missing else ""
    return f"service_en_descriptors={n}/{len(SERVICE_EN_DESCRIPTORS)}{miss}"


# ── F22 (Graph-Diff 2026-07-15, checklist row 46): Control.title_de backfill ──
# TITLE_FALLBACK["de"] = ["title_de"] — the German render path reads ONLY
# title_de (no EN fallback; language-pure cut per N1). The framework layer
# (00_frameworks.cypher) seeds only the legacy `title` prop, so a fresh install
# rendered EMPTY control titles in the German TOM (cleanroom runs 3/4:
# "| OPS.2.2 — |"). NucBox never showed it — title_de was backfilled there by
# curation and never reached the seed tables.
#
# BSI: the legacy `title` IS the official German compendium heading — copied.
# NIST/OWASP: values exported verbatim from the curated NucBox graph
# (2026-07-15, cross-read). They are the English technical terms (Prompt
# Injection, Broken Access Control, NIST function names in their all-caps
# convention) deliberately retained in German documents — domain terminology,
# not a translation gap. A08–A10 carry curated short forms. Provenance is
# recorded in title_de_source.

TITLE_DE_BACKFILL = [
    # NIST CSF 2.0 (12)
    ("NIST_CSF_2", "DE",    "DETECT"),
    ("NIST_CSF_2", "DE.CM", "Continuous Monitoring"),
    ("NIST_CSF_2", "GV",    "GOVERN"),
    ("NIST_CSF_2", "ID",    "IDENTIFY"),
    ("NIST_CSF_2", "ID.RA", "Risk Assessment"),
    ("NIST_CSF_2", "PR",    "PROTECT"),
    ("NIST_CSF_2", "PR.AA", "Identity Management, Authentication, and Access Control"),
    ("NIST_CSF_2", "PR.DS", "Data Security"),
    ("NIST_CSF_2", "PR.PS", "Platform Security"),
    ("NIST_CSF_2", "RC",    "RECOVER"),
    ("NIST_CSF_2", "RS",    "RESPOND"),
    ("NIST_CSF_2", "RS.MA", "Incident Management"),
    # OWASP API Security Top 10 2023 (10)
    ("OWASP_API_Top10", "API1",  "Broken Object Level Authorization"),
    ("OWASP_API_Top10", "API2",  "Broken Authentication"),
    ("OWASP_API_Top10", "API3",  "Broken Object Property Level Authorization"),
    ("OWASP_API_Top10", "API4",  "Unrestricted Resource Consumption"),
    ("OWASP_API_Top10", "API5",  "Broken Function Level Authorization"),
    ("OWASP_API_Top10", "API6",  "Unrestricted Access to Sensitive Business Flows"),
    ("OWASP_API_Top10", "API7",  "Server Side Request Forgery"),
    ("OWASP_API_Top10", "API8",  "Security Misconfiguration"),
    ("OWASP_API_Top10", "API9",  "Improper Inventory Management"),
    ("OWASP_API_Top10", "API10", "Unsafe Consumption of APIs"),
    # OWASP LLM Top 10 2025 (10)
    ("OWASP_LLM_Top10", "LLM01", "Prompt Injection"),
    ("OWASP_LLM_Top10", "LLM02", "Sensitive Information Disclosure"),
    ("OWASP_LLM_Top10", "LLM03", "Supply Chain"),
    ("OWASP_LLM_Top10", "LLM04", "Data and Model Poisoning"),
    ("OWASP_LLM_Top10", "LLM05", "Improper Output Handling"),
    ("OWASP_LLM_Top10", "LLM06", "Excessive Agency"),
    ("OWASP_LLM_Top10", "LLM07", "System Prompt Leakage"),
    ("OWASP_LLM_Top10", "LLM08", "Vector and Embedding Weaknesses"),
    ("OWASP_LLM_Top10", "LLM09", "Misinformation"),
    ("OWASP_LLM_Top10", "LLM10", "Unbounded Consumption"),
    # OWASP Top 10 2025 (Web) (10) — A08–A10 curated short forms
    ("OWASP_Top10", "A01", "Broken Access Control"),
    ("OWASP_Top10", "A02", "Security Misconfiguration"),
    ("OWASP_Top10", "A03", "Software Supply Chain Failures"),
    ("OWASP_Top10", "A04", "Cryptographic Failures"),
    ("OWASP_Top10", "A05", "Injection"),
    ("OWASP_Top10", "A06", "Insecure Design"),
    ("OWASP_Top10", "A07", "Authentication Failures"),
    ("OWASP_Top10", "A08", "Integrity Failures"),
    ("OWASP_Top10", "A09", "Logging and Alerting Failures"),
    ("OWASP_Top10", "A10", "Mishandling of Exceptions"),
]


def seed_title_de_backfill(session):
    """F22: ensure every Control carries title_de (German render path, N1).

    BSI copies the official German compendium heading from the legacy `title`
    prop (guarded — only where title_de is still null, so the adr066-owned six
    and any later curation stay untouched). NIST/OWASP SET the curated values
    unconditionally (idempotent; the seed table is the durable source, same
    doctrine as SERVICE_DATA_SUBJECTS). MERGE-free, MATCH-only.
    """
    bsi = session.run(
        "MATCH (c:Control {framework:'BSI_Grundschutz'}) "
        "WHERE c.title_de IS NULL AND c.title IS NOT NULL "
        "SET c.title_de = c.title, "
        "    c.title_de_source = 'BSI IT-Grundschutz-Kompendium Ed. 2022 (DE)' "
        "RETURN count(c) AS n"
    ).single()["n"]
    n = 0
    for fw, cid, title_de in TITLE_DE_BACKFILL:
        r = session.run(
            "MATCH (c:Control {id: $id, framework: $fw}) "
            "SET c.title_de = $t, "
            "    c.title_de_source = 'lex-authored (EN technical term retained)' "
            "RETURN 1 AS ok",
            id=cid, fw=fw, t=title_de,
        ).single()
        if r:
            n += 1
    missing = session.run(
        "MATCH (c:Control) WHERE c.title_de IS NULL RETURN count(c) AS n"
    ).single()["n"]
    return f"bsi_from_title={bsi}, nist_owasp={n}/{len(TITLE_DE_BACKFILL)}, title_de_missing={missing}"


MODULES = {
    "adr061": seed_adr061,
    "adr066": seed_adr066,
    "adr063": seed_adr063,
    "stubs":  seed_stubs,
    "adr075": seed_adr075,
    "adr076": seed_adr076,
    "adr082": seed_adr082,
    "adr093": seed_adr093,
    "pr_b1_gpai":          seed_pr_b1_gpai,
    "pr_b2_data_cat":      seed_pr_b2_data_categories,
    "pr_b3_retention":     seed_pr_b3_retention,
    "pr_b4_sup_auth":      seed_pr_b4_supervisory_authorities,
    "pr_c1_protection":    seed_pr_c1_protection_goals,
    "pr_c2_req_b":         seed_pr_c2_requirements_b,
    "pr_c3_legal_req":     seed_pr_c3_legal_requirements,
    "pr_c4_bfdi":          seed_pr_c4_bfdi,
    "pr_c1_5_subjects":    seed_pr_c1_5_data_subjects,
    "pr_d1_measures":      seed_pr_d1_measures,
    "pr_d3_proc_act":      seed_pr_d3_processing_activities,
    "pr_d4_data_subj":     seed_pr_d4_data_subjects,
    "pr_d5_legal_basis":   seed_pr_d5_legal_basis,
    "psp_roles":           seed_psp_roles,
    "pr1_title_tiers":     seed_pr1_title_tiers,
    "pr2_title_provenance": seed_pr2_title_provenance,
    "adr126_law_en":       seed_adr126_law_title_en,
    "adr126_measure_en":   seed_adr126_measure_name_en,
    "adr126_doctype_en":   seed_adr126_doctype_en,
    "adr126_usecase_en":   seed_adr126_usecase_en,
    "adr126_nist_verify":  seed_adr126_nist_title_verify,
    "adr126_owasp_verify": seed_adr126_owasp_title_verify,
    "adr126_bsi_verify":   seed_adr126_bsi_title_verify,
    "title_de_backfill":   seed_title_de_backfill,
    "service_en_descriptors": seed_service_en_descriptors,
}


def run(target: str, modules: list[str], with_layers: bool = False) -> None:
    """Seed one target.

    with_layers=False: the historical behaviour — Python modules only (single
    --module invocations). with_layers=True (--module all): the full ADR-130
    sequence Phase 0/1 (cypher foundations) → Phase 2 (modules) → Phase 3
    (cypher mutation layers) → validate_graph(). Validation errors raise, so
    `make seed-all` exits non-zero on a red graph.
    """
    driver, db = get_driver(target)
    try:
        with driver.session(database=db) as session:
            if with_layers:
                for rel_path in LAYERS_PHASE_0 + LAYERS_PHASE_1:
                    result = apply_layer(session, rel_path)
                    print(f"  [{target.upper():4}] layer {rel_path}: {result}")
            for mod_name in modules:
                try:
                    result = MODULES[mod_name](session)
                    print(f"  [{target.upper():4}] {mod_name}: {result}")
                except Exception as e:
                    print(f"  [{target.upper():4}] {mod_name}: FAILED — {e}")
            if with_layers:
                for rel_path in LAYERS_PHASE_3:
                    result = apply_layer(session, rel_path)
                    print(f"  [{target.upper():4}] layer {rel_path}: {result}")
                errors = validate_graph(session)
                if errors:
                    for e in errors:
                        print(f"  [{target.upper():4}] ✗ {e}", file=sys.stderr)
                    raise RuntimeError(f"graph validation failed: {len(errors)} error(s)")
                print(f"  [{target.upper():4}] ✓ validation passed (ADR-100 §4.1–§4.4)")
    finally:
        driver.close()


def confirm_remote_write(target: str, n_modules: int, with_layers: bool, assume_yes: bool) -> bool:
    """ADR-130 D5 — write runs against a REMOTE target require confirmation.

    'local' never prompts (self-hoster bootstrap UX; a wrong write hits a
    disposable local container). --yes skips the prompt for automation.
    Non-TTY without --yes refuses — a script must opt in explicitly.
    """
    if target == "local" or assume_yes:
        return True
    uri = resolve_target_env(target)[0]
    n_layers = len(LAYERS_PHASE_0 + LAYERS_PHASE_1 + LAYERS_PHASE_3) if with_layers else 0
    print(
        f"About to WRITE to remote target '{target}' ({uri}): "
        f"{n_modules} module(s), {n_layers} layer file(s)."
    )
    if not sys.stdin.isatty():
        print("Refusing: non-interactive session without --yes.", file=sys.stderr)
        return False
    return input("Proceed? [y/N] ").strip().lower() in ("y", "yes")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Neo4j seeder — ADR-130 layer manifest + Python modules"
    )
    parser.add_argument(
        "--target",
        choices=["local", "nuc", "aura"],
        default="local",
        help="local (default, never prompts) | nuc (maintainer host, prompts — "
             "--yes to skip) | aura (validate-only, non-authoritative)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="skip the remote-write confirmation prompt (automation/CI)",
    )
    parser.add_argument(
        "--module",
        # Derived from the registry — a hardcoded list silently lagged behind
        # MODULES (found 2026-07-16: title_de_backfill/service_en_descriptors
        # ran in `all` but were rejected as single modules).
        choices=[*MODULES, "all"],
        default="all",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Run graph consistency checks (ADR-100) and exit. No seed writes.",
    )
    args = parser.parse_args(argv)
    if args.target == "aura" and not args.validate_only:
        # ADR-130 D4: Aura left the write path (non-authoritative 2026-05-27).
        parser.error("target 'aura' is validate-only — write runs are not allowed")
    return args


def main() -> int:
    args = parse_args()
    targets = [args.target]

    if args.validate_only:
        total_errors = 0
        for t in targets:
            print(f"[{t.upper()}] validating graph (ADR-100)...")
            try:
                driver, db = get_driver(t)
                try:
                    with driver.session(database=db) as session:
                        errors = validate_graph(session)
                    if errors:
                        for e in errors:
                            print(f"  [{t.upper()}] ✗ {e}", file=sys.stderr)
                        print(f"  [{t.upper()}] {len(errors)} error(s) found", file=sys.stderr)
                        total_errors += len(errors)
                    else:
                        print(f"  [{t.upper()}] ✓ validation passed")
                finally:
                    driver.close()
            except Exception as e:
                print(f"[{t.upper()}] ABORTED — {e}", file=sys.stderr)
                return 1
        return 1 if total_errors > 0 else 0

    # Order: 061 (ServiceCategory) → 066 (BSI) → 063 (MAPS_TO) → stubs (Services)
    #      → 075 (Service-SCC-Annotations, needs Service nodes present)
    #      → 076 (HostingProvider — new node type, no dependencies)
    #      → 082 (Integration Catalog — Service{category:integration}, no dependencies)
    #      → 093 (PR4 content: DocumentType descriptions + Law nodes)
    #      → pr_b1_gpai (4 LLM services tagged is_gpai + provider_obligations)
    #      → pr_b2_data_cat (12 services backfilled with data_categories)
    #      → pr_b3_retention (5 RetentionPeriod nodes + 9 HAS_RETENTION edges)
    #      → pr_b4_sup_auth (17 DE SupervisoryAuthority nodes — BfDI + 16 Länder)
    if args.module == "all":
        modules = [
            "adr061", "adr066", "adr063", "stubs", "adr075", "adr076", "adr082", "adr093",
            "pr_b1_gpai", "pr_b2_data_cat", "pr_b3_retention", "pr_b4_sup_auth",
            "pr_c1_protection", "pr_c2_req_b",  # SDM-Layer first
            "pr_c3_legal_req",                  # DSGVO/BDSG Requirement nodes
            "pr_c4_bfdi",                       # depends on C3 targets existing
            "pr_c1_5_subjects",                 # PR C.1 Cleanup: data_subjects backfill
            # PR D: Measure-Layer + Process-Knowledge (depends on C1/C2/C5)
            "pr_d1_measures",                   # 63 Measures + ADDRESSES/IMPLEMENTS
            "pr_d3_proc_act",                   # 12 ProcessingActivity + USED_FOR
            "pr_d4_data_subj",                  # 8 DataSubject node-type
            "pr_d5_legal_basis",                # 8 LegalBasis (DSGVO + BDSG § 26)
            "psp_roles",                        # ADR-115 A1: PSP ACTS_AS role edges
            "adr126_law_en",                    # ADR-126 Phase 1a: 9 Law title_en backfill
            "adr126_measure_en",                # ADR-126 Phase 2: 63 Measure name_en backfill
            "adr126_doctype_en",                # ADR-126 Phase 4: 10 DocumentType EN
            "adr126_usecase_en",                # ADR-126 Phase 4: 20 UseCase EN
            "adr126_nist_verify",               # ADR-126 Phase 3a: NIST CSF 2 title verify
            "adr126_owasp_verify",              # ADR-126 Phase 3c: OWASP Web/LLM/API title verify
            "adr126_bsi_verify",                # ADR-126 Phase 3b: BSI Grundschutz title verify
            "title_de_backfill",                # F22: title_de on all 64 Controls (DE render path)
            "service_en_descriptors",           # B-2/L8: EN twins for service descriptors
        ]
    else:
        modules = [args.module]

    # ADR-130 D3: --module all runs the full layer manifest around the module
    # chain (Phase 0/1 → modules → Phase 3 → validator). Single-module
    # invocations stay module-only (historical behaviour).
    with_layers = args.module == "all"

    # ADR-130 D5: remote write runs need explicit confirmation.
    if not confirm_remote_write(args.target, len(modules), with_layers, args.yes):
        print("Aborted — no writes performed.")
        return 1

    for t in targets:
        print(f"[{t.upper()}] seeding {modules}...")
        try:
            run(t, modules, with_layers=with_layers)
        except Exception as e:
            print(f"[{t.upper()}] ABORTED — {e}")
            # F15: the "is Neo4j running?" hint only fits connection failures —
            # on validation errors Neo4j IS running and the hint misleads.
            if t == "local" and isinstance(e, ServiceUnavailable):
                print(
                    f"Hint: is Neo4j running on {os.getenv('NEO4J_LOCAL_URI') or LOCAL_DEFAULT_URI}? "
                    "Start it with: docker compose --profile with-neo4j up -d",
                    file=sys.stderr,
                )
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
