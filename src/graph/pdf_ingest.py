"""
Lex-Orchestra — PDF Ingest
Parses PDFs from docs/sources/ and populates text properties on existing
Law and Control nodes in Neo4j. Nodes must already exist (created by seed.py).

Usage:
    python src/graph/pdf_ingest.py
    python src/graph/pdf_ingest.py --dry-run
    python src/graph/pdf_ingest.py --pdf dsgvo
    python src/graph/pdf_ingest.py --pdf owasp_llm --force
"""

import os
import re
import sys
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DB = os.getenv("NEO4J_DATABASE")

SOURCES_DIR = Path(__file__).parent.parent.parent / "docs" / "sources"
MAX_TEXT_LEN = 2000


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------

def extract_pdf_text(pdf_path: Path) -> str:
    try:
        import pdfplumber
    except ImportError:
        log.error("pdfplumber not installed. Run: pip install pdfplumber")
        sys.exit(1)

    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n".join(pages)


def trim(text: str) -> str:
    """Normalize whitespace and cut to MAX_TEXT_LEN at a sentence boundary."""
    text = " ".join(text.split())
    if len(text) <= MAX_TEXT_LEN:
        return text
    cut = text[:MAX_TEXT_LEN]
    last_period = max(cut.rfind(". "), cut.rfind(".\n"))
    if last_period > MAX_TEXT_LEN * 0.7:
        return cut[: last_period + 1]
    return cut


def extract_section(full_text: str, start_pattern: str, end_pattern: str, min_length: int = 150) -> str:
    """Return text from start_pattern match until end_pattern (exclusive).

    If the matched section is shorter than min_length (e.g. a TOC entry),
    tries subsequent occurrences until a substantive section is found.
    """
    search_from = 0
    while search_from < len(full_text):
        m_start = re.search(start_pattern, full_text[search_from:], re.IGNORECASE)
        if not m_start:
            return ""
        abs_start = search_from + m_start.start()
        tail = full_text[abs_start:]
        m_end = re.search(end_pattern, tail[len(m_start.group()):], re.IGNORECASE)
        if m_end:
            section = tail[: len(m_start.group()) + m_end.start()].strip()
        else:
            section = tail[:4000].strip()
        if len(section) >= min_length:
            return section
        # Too short — skip past this match and try again
        search_from = abs_start + len(m_start.group())
    return ""


# ---------------------------------------------------------------------------
# Per-PDF parse functions → {identifier: text}
# ---------------------------------------------------------------------------

def parse_dsgvo(pdf_path: Path) -> dict:
    """Articles 13, 14, 28, 30, 32, 37, 46"""
    log.info("Parsing %s", pdf_path.name)
    full_text = extract_pdf_text(pdf_path)
    articles = [13, 14, 28, 30, 32, 37, 46]
    results = {}
    for i, art in enumerate(articles):
        next_art = articles[i + 1] if i + 1 < len(articles) else art + 1
        text = extract_section(
            full_text,
            rf"Artikel\s+{art}\b",
            rf"Artikel\s+{next_art}\b",
        )
        if text:
            results[str(art)] = trim(text)
            log.debug("  Art.%s: %d chars", art, len(results[str(art)]))
        else:
            log.warning("  DSGVO Art.%s: section not found in PDF", art)
    return results


def parse_euaiact(pdf_path: Path) -> dict:
    """Articles 6, 51, 52"""
    log.info("Parsing %s", pdf_path.name)
    full_text = extract_pdf_text(pdf_path)
    articles = [6, 51, 52]
    results = {}
    for i, art in enumerate(articles):
        next_art = articles[i + 1] if i + 1 < len(articles) else art + 1
        text = extract_section(
            full_text,
            rf"(?:Article|Artikel)\s+{art}\b",
            rf"(?:Article|Artikel)\s+{next_art}\b",
        )
        if text:
            results[str(art)] = trim(text)
            log.debug("  Art.%s: %d chars", art, len(results[str(art)]))
        else:
            log.warning("  EU AI Act Art.%s: section not found in PDF", art)
    return results


def parse_nis2(pdf_path: Path) -> dict:
    """Articles 21, 23, 24, 27, 32"""
    log.info("Parsing %s", pdf_path.name)
    full_text = extract_pdf_text(pdf_path)
    articles = [21, 23, 24, 27, 32]
    results = {}
    for i, art in enumerate(articles):
        next_art = articles[i + 1] if i + 1 < len(articles) else art + 1
        text = extract_section(
            full_text,
            rf"Artikel\s+{art}\b",
            rf"Artikel\s+{next_art}\b",
        )
        if text:
            results[str(art)] = trim(text)
            log.debug("  Art.%s: %d chars", art, len(results[str(art)]))
        else:
            log.warning("  NIS2 Art.%s: section not found in PDF", art)
    return results


# Legacy — ISO 27001:2013, superseded
def parse_iso27001_2013(pdf_path: Path) -> dict:
    """Annex A Controls: A.5.1.1 … A.18.2.1 (ISO 27001:2013 numbering)."""
    log.info("Parsing %s", pdf_path.name)
    full_text = extract_pdf_text(pdf_path)
    controls = [
        "A.5.1.1", "A.5.1.2", "A.8.1.1", "A.8.1.2", "A.8.2.1",
        "A.9.1.1", "A.9.2.1", "A.9.4.1", "A.12.1.1", "A.12.6.1",
        "A.18.1.1", "A.18.1.4", "A.18.2.1",
    ]
    results = {}
    for i, ctrl in enumerate(controls):
        next_ctrl = controls[i + 1] if i + 1 < len(controls) else None
        end_pat = re.escape(next_ctrl) + r"\s" if next_ctrl else r"(?:Annex B|Bibliography)"
        text = extract_section(full_text, re.escape(ctrl) + r"\s", end_pat)
        if text:
            results[ctrl] = trim(text)
            log.debug("  %s: %d chars", ctrl, len(results[ctrl]))
        else:
            log.warning("  ISO 27001:2013 %s: section not found in PDF", ctrl)
    return results


def parse_iso27001_2022(pdf_path: Path) -> dict:
    """ISO 27001:2022 Annex A controls 5.1–5.37, 6.1–6.8, 7.1–7.14, 8.1–8.34 (93 controls).

    The 2022 edition reorganises Annex A into four categories with x.x IDs.
    The PDF renders controls as a table; pdfplumber extracts the "Control" column
    header inline within each entry — cleaned up after extraction.
    Search is restricted to the Annex A section to avoid collisions with ISMS body
    clauses 5–8 which use the same numbering scheme.
    """
    log.info("Parsing %s", pdf_path.name)
    full_text = extract_pdf_text(pdf_path)

    # Restrict to Annex A only — ISMS body (chapters 5–8) uses the same x.x numbering
    annex_match = re.search(r"Table\s+A\.1\s*[—\-]\s*Information security controls", full_text)
    if annex_match:
        annex_text = full_text[annex_match.start():]
        log.debug("Annex A found at offset %d", annex_match.start())
    else:
        log.warning("Annex A marker not found — falling back to full text (false matches possible)")
        annex_text = full_text

    # 93 control IDs in document order
    controls = (
        [f"5.{i}" for i in range(1, 38)] +   # 5.1–5.37  (37 organisational controls)
        [f"6.{i}" for i in range(1, 9)]  +   # 6.1–6.8   (8 people controls)
        [f"7.{i}" for i in range(1, 15)] +   # 7.1–7.14  (14 physical controls)
        [f"8.{i}" for i in range(1, 35)]     # 8.1–8.34  (34 technological controls)
    )

    results = {}
    for i, ctrl in enumerate(controls):
        next_ctrl = controls[i + 1] if i + 1 < len(controls) else None
        end_pat = (r"\b" + re.escape(next_ctrl) + r"\b") if next_ctrl else r"Bibliography"

        raw = extract_section(
            annex_text,
            r"\b" + re.escape(ctrl) + r"\b",
            end_pat,
            min_length=40,
        )
        if raw:
            # Remove "Control" table-column artifact inserted by PDF text extraction
            cleaned = re.sub(r"\bControl\b\n?", " ", raw)
            # Rejoin hyphenated line-breaks ("secu-\nrity" → "security")
            cleaned = re.sub(r"-\n(\S)", r"\1", cleaned)
            results[ctrl] = trim(cleaned)
            log.debug("  %s: %d chars", ctrl, len(results[ctrl]))
        else:
            log.warning("  ISO 27001:2022 %s: section not found in PDF", ctrl)

    return results


def parse_bsi_grundschutz(pdf_path: Path) -> dict:
    """Bausteine: ORP.1, CON.2, OPS.1.1, SYS.1.1, NET.1.1"""
    log.info("Parsing %s", pdf_path.name)
    full_text = extract_pdf_text(pdf_path)
    controls = ["ORP.1", "CON.2", "OPS.1.1", "SYS.1.1", "NET.1.1"]
    results = {}
    for i, ctrl in enumerate(controls):
        next_ctrl = controls[i + 1] if i + 1 < len(controls) else None
        end_pat = rf"\b{re.escape(next_ctrl)}\b" if next_ctrl else r"(?:Anhang|Index)"
        text = extract_section(full_text, rf"\b{re.escape(ctrl)}\b", end_pat)
        if text:
            results[ctrl] = trim(text)
            log.debug("  %s: %d chars", ctrl, len(results[ctrl]))
        else:
            log.warning("  BSI %s: section not found in PDF", ctrl)
    return results


def parse_owasp_llm(pdf_path: Path) -> dict:
    """LLM01, LLM02, LLM06, LLM08, LLM09"""
    log.info("Parsing %s", pdf_path.name)
    full_text = extract_pdf_text(pdf_path)
    targets = ["LLM01", "LLM02", "LLM06", "LLM08", "LLM09"]
    # All possible LLM IDs as end-of-section anchors
    all_ids = [f"LLM{i:02d}" for i in range(1, 11)]
    results = {}
    for ctrl in targets:
        idx = all_ids.index(ctrl)
        subsequent = all_ids[idx + 1 :]
        end_pat = r"\b(" + "|".join(subsequent) + r")\b" if subsequent else r"(?:Appendix|References)"
        text = extract_section(full_text, rf"\b{ctrl}\b", end_pat)
        if text:
            results[ctrl] = trim(text)
            log.debug("  %s: %d chars", ctrl, len(results[ctrl]))
        else:
            log.warning("  OWASP LLM %s: section not found in PDF", ctrl)
    return results


def parse_owasp_api(pdf_path: Path) -> dict:
    """API1 … API10"""
    log.info("Parsing %s", pdf_path.name)
    full_text = extract_pdf_text(pdf_path)
    controls = [f"API{i}" for i in range(1, 11)]
    results = {}
    for i, ctrl in enumerate(controls):
        subsequent = controls[i + 1 :]
        end_pat = r"\b(" + "|".join(subsequent) + r")\b" if subsequent else r"(?:Appendix|References)"
        text = extract_section(full_text, rf"\b{ctrl}\b", end_pat)
        if text:
            results[ctrl] = trim(text)
            log.debug("  %s: %d chars", ctrl, len(results[ctrl]))
        else:
            log.warning("  OWASP API %s: section not found in PDF", ctrl)
    return results


# ---------------------------------------------------------------------------
# Neo4j write helpers
# ---------------------------------------------------------------------------

_LAW_CYPHER = """
MATCH (l:Law {name: $name, article: $article})
WHERE l.text = "" OR l.text IS NULL OR $force
SET l.text = $text, l.text_updated = datetime()
RETURN count(l) AS updated
"""

_CONTROL_CYPHER = """
MATCH (c:Control {framework: $framework, id: $id})
WHERE c.text = "" OR c.text IS NULL OR $force
SET c.text = $text, c.text_updated = datetime()
RETURN count(c) AS updated
"""

_CONTROL_CYPHER_VERSIONED = """
MATCH (c:Control {framework: $framework, id: $id, version: $version})
WHERE c.text = "" OR c.text IS NULL OR $force
SET c.text = $text, c.text_updated = datetime()
RETURN count(c) AS updated
"""


def write_law(session, name, article, text, force) -> bool:
    record = session.run(_LAW_CYPHER, name=name, article=article, text=text, force=force).single()
    updated = bool(record and record["updated"])
    if updated:
        log.info("  ✓ Law {name:%s, article:%s}", name, article)
    else:
        log.debug("  ~ Law {name:%s, article:%s} skipped (already set, use --force)", name, article)
    return updated


def write_control(session, framework, id, text, force, version=None) -> bool:
    if version:
        record = session.run(
            _CONTROL_CYPHER_VERSIONED,
            framework=framework, id=id, version=version, text=text, force=force,
        ).single()
    else:
        record = session.run(
            _CONTROL_CYPHER,
            framework=framework, id=id, text=text, force=force,
        ).single()
    updated = bool(record and record["updated"])
    if updated:
        log.info("  ✓ Control {framework:%s, id:%s}", framework, id)
    else:
        log.debug("  ~ Control {framework:%s, id:%s} skipped (already set, use --force)", framework, id)
    return updated


# ---------------------------------------------------------------------------
# PDF registry
# ---------------------------------------------------------------------------

PDF_REGISTRY = {
    "dsgvo": {
        "file": "dsgvo.pdf",
        "parse_fn": parse_dsgvo,
        "node_type": "law",
        "law_name": "DSGVO",
    },
    "euaiact": {
        "file": "euaiact.pdf",
        "parse_fn": parse_euaiact,
        "node_type": "law",
        "law_name": "EU AI Act",
    },
    "nis2": {
        "file": "CELEX_32022L2555_DE_TXT.pdf",
        "parse_fn": parse_nis2,
        "node_type": "law",
        "law_name": "NIS2",
    },
    "iso27001": {
        "file": "isoiec27001en.pdf",
        "parse_fn": parse_iso27001_2022,
        "node_type": "control",
        "framework": "ISO_27001",
        "version": "2022",
    },
    "bsi": {
        "file": "IT_Grundschutz_Kompendium.pdf",
        "parse_fn": parse_bsi_grundschutz,
        "node_type": "control",
        "framework": "BSI_Grundschutz",
    },
    "owasp_llm": {
        "file": "OWASP-Top-10-for-LLMs-v2025.pdf",
        "parse_fn": parse_owasp_llm,
        "node_type": "control",
        "framework": "OWASP_LLM_Top10",
    },
    "owasp_api": {
        "file": "owasp-api-security-top-10.pdf",
        "parse_fn": parse_owasp_api,
        "node_type": "control",
        "framework": "OWASP_API_Top10",
    },
}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_ingest(pdf_filter=None, dry_run=False, force=False):
    if not dry_run and not all([NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DB]):
        log.error("Missing Neo4j credentials. Check .env for NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE.")
        sys.exit(1)

    registry = PDF_REGISTRY
    if pdf_filter:
        if pdf_filter not in PDF_REGISTRY:
            log.error("Unknown PDF key '%s'. Valid keys: %s", pdf_filter, ", ".join(PDF_REGISTRY))
            sys.exit(1)
        registry = {pdf_filter: PDF_REGISTRY[pdf_filter]}

    driver = None
    if not dry_run:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        log.info("Connected to %s (db: %s)", NEO4J_URI, NEO4J_DB)

    total_updated = 0
    total_skipped = 0
    total_errors = 0

    for key, cfg in registry.items():
        pdf_path = SOURCES_DIR / cfg["file"]
        if not pdf_path.exists():
            log.error("[%s] PDF not found: %s", key, pdf_path)
            total_errors += 1
            continue

        try:
            parsed = cfg["parse_fn"](pdf_path)
        except Exception as e:
            log.error("[%s] Parse failed: %s", key, e)
            total_errors += 1
            continue

        log.info("[%s] %d sections parsed", key, len(parsed))

        if dry_run:
            for identifier, text in parsed.items():
                log.info("  [DRY-RUN] %s / %s → %d chars | %s…", key, identifier, len(text), text[:60])
            total_updated += len(parsed)
            continue

        with driver.session(database=NEO4J_DB) as session:
            for identifier, text in parsed.items():
                try:
                    if cfg["node_type"] == "law":
                        updated = write_law(session, cfg["law_name"], identifier, text, force)
                    else:
                        updated = write_control(session, cfg["framework"], identifier, text, force, version=cfg.get("version"))
                    if updated:
                        total_updated += 1
                    else:
                        total_skipped += 1
                except Exception as e:
                    log.error("  [%s / %s] Write error: %s", key, identifier, e)
                    total_errors += 1

    if driver:
        driver.close()

    print()
    print("=" * 50)
    print("PDF Ingest complete.")
    print(f"  Nodes updated:  {total_updated}")
    print(f"  Skipped:        {total_skipped}  (text already set — use --force to overwrite)")
    print(f"  Errors:         {total_errors}")
    print("=" * 50)

    if total_errors:
        log.warning("%d error(s) occurred. Check output above.", total_errors)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populate Neo4j Law/Control text from PDF sources")
    parser.add_argument("--dry-run", action="store_true", help="Parse PDFs and preview output, no DB write")
    parser.add_argument(
        "--pdf",
        metavar="KEY",
        help="Process one PDF only: dsgvo | euaiact | nis2 | iso27001 | bsi | owasp_llm | owasp_api",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite text even if already set")
    args = parser.parse_args()
    run_ingest(pdf_filter=args.pdf, dry_run=args.dry_run, force=args.force)
