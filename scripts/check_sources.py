"""
Source Inventory Check — Lex-Orchestra

Checks docs/sources/ against Neo4j graph.
Reports which PDFs are imported, which are missing, and what to do next.

Usage:
    python scripts/check_sources.py
    python scripts/check_sources.py --json      # machine-readable output
    python scripts/check_sources.py --missing   # only show missing
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
logger = logging.getLogger(__name__)

SOURCES_DIR = Path(__file__).parents[1] / "docs" / "sources"

# Mapping: filename → what to look for in Neo4j + metadata
SOURCE_MAP = {
    "euaiact.pdf": {
        "description": "EU AI Act (Regulation EU 2024/1689)",
        "check": {"label": "Law", "property": "name", "value": "EU AI Act"},
        "layer": "10_jurisdiction/eu/10_eu_primary.cypher",
        "jurisdiction": "EU",
        "applies_from": "2026-08-02",
        "note": None,
    },
    "dsgvo.pdf": {
        "description": "GDPR / DSGVO (Regulation EU 2016/679)",
        "check": {"label": "Law", "property": "name", "value": "DSGVO"},
        "layer": "10_jurisdiction/eu/10_eu_primary.cypher",
        "jurisdiction": "EU",
        "applies_from": "2018-05-25",
        "note": None,
    },
    "CELEX_32022L2555_DE_TXT.pdf": {
        "description": "NIS2 Directive (EU 2022/2555)",
        "check": {"label": "Law", "property": "name", "value": "NIS2"},
        "layer": "10_jurisdiction/eu/10_eu_primary.cypher",
        "jurisdiction": "EU",
        "applies_from": "2024-10-18",
        "note": None,
    },
    "cyber-resilience-act-2024-2847.pdf": {
        "description": "CRA — Cyber Resilience Act (EU 2024/2847)",
        "check": {"label": "Law", "property": "name", "value": "CRA"},
        "layer": "10_jurisdiction/eu/10_eu_primary.cypher",
        "jurisdiction": "EU",
        "applies_from": "2027-12-11",
        "note": None,
    },
    "ISO-27001.pdf": {
        "description": "ISO 27001:2013 Information Security",
        "check": {"label": "Control", "property": "framework", "value": "ISO_27001"},
        "layer": "00_global/00_frameworks.cypher",
        "jurisdiction": "global",
        "applies_from": None,
        "note": "ISO 27001:2022 revision not yet in graph — consider upgrading",
    },
    "IT_Grundschutz_Kompendium.pdf": {
        "description": "BSI IT-Grundschutz Kompendium Edition 2023",
        "check": {"label": "Control", "property": "framework", "value": "BSI_Grundschutz"},
        "layer": "00_global/00_frameworks.cypher",
        "jurisdiction": "global",
        "applies_from": None,
        "note": None,
    },
    "nist-csf-2.0.pdf": {
        "description": "NIST Cybersecurity Framework 2.0 (CSWP 29)",
        "check": {"label": "Control", "property": "framework", "value": "NIST_CSF_2"},
        "layer": "00_global/00_frameworks.cypher",
        "jurisdiction": "global",
        "applies_from": None,
        "note": None,
    },
    "owasp-api-security-top-10.pdf": {
        "description": "OWASP API Security Top 10",
        "check": {"label": "Control", "property": "framework", "value": "OWASP_API_Top10"},
        "layer": "00_global/00_frameworks.cypher",
        "jurisdiction": "global",
        "applies_from": None,
        "note": None,
    },
    "OWASP-Top-10-for-LLMs-v2025.pdf": {
        "description": "OWASP Top 10 for LLM Applications v2025",
        "check": {"label": "Control", "property": "framework", "value": "OWASP_LLM_Top10"},
        "layer": "00_global/00_frameworks.cypher",
        "jurisdiction": "global",
        "applies_from": None,
        "note": None,
    },
    "202512 - OWASP Top 10 2025 by Miglen Evlogiev.pdf": {
        "description": "OWASP Top 10 Web Application Security Risks 2025",
        "check": {"label": "Control", "property": "framework", "value": "OWASP_Top10"},
        "layer": "00_global/00_frameworks.cypher",
        "jurisdiction": "global",
        "applies_from": None,
        "note": None,
    },
    "DORA.pdf": {
        "description": "DORA — Digital Operational Resilience Act (EU 2022/2554)",
        "check": {"label": "Law", "property": "name", "value": "DORA"},
        "layer": "10_jurisdiction/eu/10_eu_primary.cypher",
        "jurisdiction": "EU",
        "applies_from": "2025-01-17",
        "note": "Financial sector regulation — affects banks, insurance, fintech",
    },
    "CELEX_32022R2065_EN_TXT.pdf": {
        "description": "DSA — Digital Services Act (EU 2022/2065)",
        "check": {"label": "Law", "property": "name", "value": "DSA"},
        "layer": "10_jurisdiction/eu/10_eu_primary.cypher",
        "jurisdiction": "EU",
        "applies_from": "2024-02-17",
        "note": "Download: https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32022R2065 | OJ L 277, 27.10.2022 | 3 nodes in graph: Art. 5 (Impressum), Art. 14 (Notice-and-Action), Art. 26 (Werbetransparenz)",
    },
}

# PDFs in sources/ that are not regulatory frameworks (skip silently)
SKIP_FILES = {
    "eur-lex.europa.eu.html",  # HTML archive, not a framework
}


def check_node_exists(driver, label: str, property_name: str, value: str) -> int:
    """Return count of matching nodes in Neo4j."""
    with driver.session() as session:
        result = session.run(
            f"MATCH (n:{label}) WHERE n.{property_name} = $value RETURN count(n) AS cnt",
            value=value,
        )
        return result.single()["cnt"]


def run_check(args) -> list[dict]:
    """Run source inventory check. Returns list of result dicts."""
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")

    if not all([neo4j_uri, neo4j_user, neo4j_password]):
        print("ERROR: NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD missing in .env")
        sys.exit(1)

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    results = []

    # Find all files in sources/
    source_files = {f.name for f in SOURCES_DIR.iterdir() if f.is_file()}

    # Check each known source
    for filename, meta in SOURCE_MAP.items():
        if filename in SKIP_FILES:
            continue

        present_on_disk = filename in source_files
        node_count = 0

        if present_on_disk:
            c = meta["check"]
            node_count = check_node_exists(driver, c["label"], c["property"], c["value"])

        status = "missing" if node_count == 0 else "imported"
        if not present_on_disk:
            status = "pdf_missing"

        results.append({
            "filename": filename,
            "description": meta["description"],
            "status": status,
            "node_count": node_count,
            "node_label": meta["check"]["label"],
            "jurisdiction": meta["jurisdiction"],
            "layer": meta["layer"],
            "applies_from": meta["applies_from"],
            "note": meta["note"],
            "on_disk": present_on_disk,
        })

    # Check for unknown files in sources/ (not in SOURCE_MAP)
    known_files = set(SOURCE_MAP.keys()) | SKIP_FILES
    unknown = source_files - known_files
    for filename in sorted(unknown):
        if not filename.startswith("."):
            results.append({
                "filename": filename,
                "description": "Unknown — not in SOURCE_MAP",
                "status": "unknown",
                "node_count": 0,
                "node_label": None,
                "jurisdiction": None,
                "layer": None,
                "applies_from": None,
                "note": "Add to SOURCE_MAP in scripts/check_sources.py",
                "on_disk": True,
            })

    driver.close()
    return results


def print_report(results: list[dict], missing_only: bool = False) -> None:
    """Print human-readable report."""
    print()
    print("Lex-Orchestra — Source Inventory")
    print("=" * 60)
    print()

    imported = [r for r in results if r["status"] == "imported"]
    missing  = [r for r in results if r["status"] == "missing"]
    unknown  = [r for r in results if r["status"] == "unknown"]
    pdf_miss = [r for r in results if r["status"] == "pdf_missing"]

    if not missing_only:
        print("IMPORTED:")
        for r in imported:
            note = f"  NOTE: {r['note']}" if r["note"] else ""
            print(f"  OK  {r['filename']:<45} -> {r['node_count']} {r['node_label']} nodes{note}")

        if unknown:
            print()
            print("UNKNOWN (in sources/ but not in SOURCE_MAP):")
            for r in unknown:
                print(f"  ?   {r['filename']}")
                print(f"      Add to SOURCE_MAP in scripts/check_sources.py")

    if missing:
        print()
        print("NOT IMPORTED:")
        for r in missing:
            print(f"  MISSING  {r['filename']}")
            print(f"           {r['description']}")
            print(f"           Jurisdiction:  {r['jurisdiction']}")
            if r["applies_from"]:
                print(f"           applies_from:  {r['applies_from']}")
            print(f"           Target layer:  src/graph/layers/{r['layer']}")
            if r["note"]:
                print(f"           Note:          {r['note']}")
            print(f"           Action:        Read PDF -> add Law/Control nodes to layer file")
            print(f"                          -> run: make seed-all")
            print()
    else:
        if not missing_only:
            print()
            print("  All known sources are imported.")

    if pdf_miss and not missing_only:
        print()
        print("PDF MISSING FROM docs/sources/:")
        for r in pdf_miss:
            print(f"  PDF  {r['filename']} -- {r['description']}")
            print(f"       Download and place in docs/sources/ to enable import")

    print()
    print(f"SUMMARY: {len(imported)} imported / {len(missing)} missing"
          f" / {len(unknown)} unknown / {len(pdf_miss)} pdf missing")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check docs/sources/ against Neo4j graph")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--missing", action="store_true", help="Show only missing sources")
    args = parser.parse_args()

    results = run_check(args)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print_report(results, missing_only=args.missing)

    # Exit code 1 if any sources are missing (useful for CI)
    missing_count = sum(1 for r in results if r["status"] == "missing")
    sys.exit(1 if missing_count > 0 else 0)
