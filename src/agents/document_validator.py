"""
Document Validator — Node 4b
Checks generated documents against the graph specification (required_sections,
required_project_config_fields on DocumentType nodes).

Returns a validation_result list — one gaps_report per document.
No LLM calls. Purely deterministic string-matching.

ADR-018: Document Validator Node
"""

import logging
import re
from pathlib import Path

from src.graph.graph_client import GraphClient

logger = logging.getLogger(__name__)

PLACEHOLDER_PATTERNS = [
    "(ausfüllen)",
    "(bitte ergänzen)",
    "(nicht angegeben)",
    "(eintragen)",
]


def _is_placeholder(value: str) -> bool:
    """True if value is an unfilled placeholder."""
    if not value:
        return True
    v = value.strip().lower()
    return any(p.lower() in v for p in PLACEHOLDER_PATTERNS)


def _load_required_spec(doc_type: str) -> dict:
    """
    Load required_sections and required_project_config_fields from graph.
    Returns {"sections": [...], "config_fields": [...]}.
    Falls back to empty lists if node not found.
    """
    try:
        with GraphClient() as gc:
            result = gc._driver.session().run(
                """
                MATCH (d:DocumentType {type: $doc_type})
                RETURN d.required_sections AS sections,
                       d.required_project_config_fields AS config_fields
                """,
                doc_type=doc_type,
            ).single()
            if result:
                return {
                    "sections": result["sections"] or [],
                    "config_fields": result["config_fields"] or [],
                }
    except Exception as e:
        logger.warning("Could not load spec for %s: %s", doc_type, e)
    return {"sections": [], "config_fields": []}


def _check_section_present(content: str, section: str) -> bool:
    """
    Check if a required section heading appears in the Markdown content.
    Strips leading symbols and whitespace for fuzzy match.
    Examples:
      "§9 Datenschutzkontrolle" → looks for "Datenschutzkontrolle"
      "1.1 Zutrittskontrolle"   → looks for "Zutrittskontrolle"
    """
    clean = re.sub(r"^[§\d\.\s]+", "", section).strip()
    if not clean:
        clean = section
    return clean.lower() in content.lower()


def _check_config_field(config: dict, field: str) -> bool:
    """True if config field is present and not a placeholder."""
    value = config.get(field, "")
    return bool(value) and not _is_placeholder(str(value))


class DocumentValidator:
    """Validates generated documents against graph specification."""

    # Field → section hint mapping for gaps appendix
    FIELD_HINTS = {
        "responsible_name":  "Weisungsbefugnis (§ 3 AVV / TOM Unterschrift)",
        "responsible_title": "Weisungsbefugnis (§ 3 AVV)",
        "dpo_name":          "Datenschutzkontrolle (§ 9 AVV / TOM § 4.1)",
        "dpo_email":         "Datenschutzkontrolle (§ 9 AVV)",
        "address":           "Verantwortlicher-Header (§ 1 AVV / VVT)",
        "zip_city":          "Verantwortlicher-Header",
        "register_court":    "Handelsregister (VVT Header)",
        "register_number":   "Handelsregister (VVT Header)",
        "contact_email":     "Kontaktangaben",
        "ai_usecase_type":   "AI Act Manifest § 3 / DSFA",
    }

    def validate_all(self, generated_docs: list[dict], project_name: str) -> list[dict]:
        """
        Validate all generated documents.
        Returns list of gaps_report dicts — one per document.
        """
        from src.graph.asset_translator import _resolve_db_url
        import psycopg2
        import psycopg2.extras

        config = {}
        db_url = _resolve_db_url()
        if db_url:
            try:
                with psycopg2.connect(db_url) as conn:
                    with conn.cursor(
                        cursor_factory=psycopg2.extras.RealDictCursor
                    ) as cur:
                        cur.execute(
                            "SELECT * FROM project_config WHERE project_name = %s",
                            (project_name,),
                        )
                        row = cur.fetchone()
                        config = dict(row) if row else {}
            except Exception as e:
                logger.warning("Could not load project_config: %s", e)

        results = []
        for doc in generated_docs:
            report = self._validate_document(doc, config)
            results.append(report)
            self._append_gaps_if_needed(report)
            logger.info(
                "Validated %s: score=%.2f usable=%s missing_sections=%d",
                report["doc_type"],
                report["completeness_score"],
                report["is_usable"],
                len(report["missing_sections"]),
            )
        return results

    def _validate_document(self, doc: dict, config: dict) -> dict:
        """Validate a single document. Returns gaps_report dict."""
        doc_type  = doc.get("doc_type", "")
        file_path = doc.get("file_path", "")

        spec = _load_required_spec(doc_type)
        required_sections      = spec["sections"]
        required_config_fields = spec["config_fields"]

        content = ""
        if file_path:
            try:
                content = Path(file_path).read_text(encoding="utf-8")
            except Exception as e:
                logger.warning("Could not read %s: %s", file_path, e)

        missing_sections   = [
            s for s in required_sections
            if not _check_section_present(content, s)
        ]
        missing_config     = [
            f for f in required_config_fields
            if not _check_config_field(config, f)
        ]
        placeholder_fields = [
            f for f in required_config_fields
            if config.get(f) and _is_placeholder(str(config.get(f, "")))
        ]

        total   = len(required_sections)
        present = total - len(missing_sections)
        score   = round(present / total, 2) if total > 0 else 1.0

        return {
            "doc_type":              doc_type,
            "file_path":             file_path,
            "missing_sections":      missing_sections,
            "missing_config_fields": missing_config,
            "placeholder_fields":    placeholder_fields,
            "completeness_score":    score,
            "is_usable":             len(missing_sections) == 0,
        }

    def _append_gaps_if_needed(self, report: dict) -> None:
        """
        Append action-oriented gaps section to document file.
        Only when config fields are missing. No legal disclaimers.
        """
        gaps = report["missing_config_fields"] + report["placeholder_fields"]
        if not gaps:
            return

        path = Path(report.get("file_path", ""))
        if not path.exists():
            return

        lines = [
            "",
            "---",
            "",
            "## Anhang: Noch ausstehende Angaben",
            "",
            "Diese Felder wurden noch nicht ausgefüllt:",
            "",
        ]
        for field in gaps:
            hint = self.FIELD_HINTS.get(field, "project_config")
            lines.append(f"- **{field}** — wird benötigt in: {hint}")

        lines += [
            "",
            "Ergänze diese Angaben in `/config` und starte neu mit `/scan`.",
            "",
        ]

        try:
            existing = path.read_text(encoding="utf-8")
            if "## Anhang: Noch ausstehende Angaben" not in existing:
                path.write_text(existing + "\n".join(lines), encoding="utf-8")
        except Exception as e:
            logger.warning("Could not append gaps to %s: %s", path, e)

    def format_telegram_summary(self, results: list[dict]) -> str:
        """
        Format validation results for Telegram.
        Tone: actionable, no disclaimers.

        ✅ AVV vollständig — einsatzbereit
        🔶 ToM (73%) — Felder ergänzen: responsible_name
        🔴 DSFA (40%) — fehlt: Schritt 1, Schritt 2
        """
        if not results:
            return ""

        lines = []
        for r in results:
            pct = int(r["completeness_score"] * 100)
            doc = r["doc_type"]

            if r["completeness_score"] >= 1.0 and not r["missing_config_fields"]:
                lines.append(f"✅ {doc} vollständig — einsatzbereit")
            elif r["is_usable"] and r["missing_config_fields"]:
                fields = ", ".join(r["missing_config_fields"][:3])
                lines.append(f"🔶 {doc} ({pct}%) — Felder ergänzen: {fields}")
            else:
                missing = r["missing_sections"][:2]
                lines.append(f"🔴 {doc} ({pct}%) — fehlt: {', '.join(missing)}")

        all_gaps = list(dict.fromkeys(
            f for r in results for f in r["missing_config_fields"]
        ))
        if all_gaps:
            lines.append(f"\n→ `/config` setzen: {', '.join(all_gaps[:3])}")

        return "\n".join(lines)
