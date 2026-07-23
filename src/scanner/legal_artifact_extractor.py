"""ADR-087: Repo-Content Extraction Layer.

Detects legal artifacts (privacy, imprint, DPA, ToS, cookies, security.txt)
in a scanned repository and extracts structured fields via Gemma 4.

Sovereignty: file contents sent to local Ollama only. No external LLM calls.
Audit: each extraction logged to audit_log with file path + extracted field list.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from src.llm import complete_ollama, resolve_ollama_endpoint

logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────

# ADR-127 Phase 1: endpoint lookup centralized in src/llm; resolves byte-identically
# to the prior os.environ.get("OLLAMA_BASE_URL", <default>) + "/api/generate" — this
# site reads OLLAMA_BASE_URL only (bare host:port, path appended).
OLLAMA_ENDPOINT = resolve_ollama_endpoint(
    base_env="OLLAMA_BASE_URL", base_default="http://ollama:11434", suffix="/api/generate"
)
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma4:e4b")
OLLAMA_TIMEOUT = 120.0

LEGAL_FILE_PATTERNS = [
    "**/privacy.html", "**/privacy.md", "**/privacy-policy.*",
    "**/datenschutz.html", "**/datenschutz.md", "**/datenschutzerklaerung.*",
    "**/impressum.html", "**/impressum.md",
    "**/imprint.html", "**/imprint.md", "**/legal-notice.*",
    "**/DPA.*", "**/dpa.md", "**/data-processing-agreement.*",
    "**/avv.md", "**/AVV.*",
    "**/terms.md", "**/tos.md", "**/ToS.*",
    "**/terms-of-service.*", "**/terms-of-use.*",
    "**/cookie-policy.*", "**/cookies.md",
    "**/security.txt", "**/.well-known/security.txt",
    "**/SECURITY.md", "**/security.md",
]

EXCLUDE_DIRS = {
    "node_modules", ".git", ".next", "dist", "build",
    "__pycache__", ".venv", "venv", "target", ".cache",
    "docs",
}

# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class LegalFile:
    path: Path
    relative_path: str
    artifact_type: str
    content: str
    size_bytes: int


@dataclass
class ExtractionResult:
    source_file: str
    artifact_type: str
    extracted_fields: dict[str, Any] = field(default_factory=dict)
    raw_llm_output: str = ""
    error: str | None = None
    extracted_at: str = ""


# ── Glob + classify ────────────────────────────────────────────────────────────

def _classify_artifact(path: Path) -> str:
    name = path.name.lower()
    if "privacy" in name or "datenschutz" in name:
        return "privacy"
    if "impressum" in name or "imprint" in name or "legal-notice" in name:
        return "imprint"
    if "dpa" in name or "avv" in name or "data-processing" in name:
        return "dpa"
    if "terms" in name or "tos" in name:
        return "tos"
    if "cookie" in name:
        return "cookies"
    if "security" in name:
        return "security"
    return "unknown"


def glob_legal_files(repo_path: Path) -> list[LegalFile]:
    """Find legal artifacts in repo. Reads contents up to 200 KB each."""
    seen: set[Path] = set()
    found: list[LegalFile] = []
    for pattern in LEGAL_FILE_PATTERNS:
        for match in repo_path.glob(pattern):
            if not match.is_file() or match in seen:
                continue
            seen.add(match)
            rel = match.relative_to(repo_path)
            if any(part in EXCLUDE_DIRS for part in rel.parts):
                continue
            try:
                size = match.stat().st_size
                if size > 200_000:
                    logger.warning("Skipping %s: %d bytes > 200 KB limit", rel, size)
                    continue
                content = match.read_text(encoding="utf-8", errors="replace")
                found.append(LegalFile(
                    path=match,
                    relative_path=str(rel),
                    artifact_type=_classify_artifact(match),
                    content=content,
                    size_bytes=size,
                ))
                logger.info("Found legal artifact: %s (%s)", rel, _classify_artifact(match))
            except OSError as e:
                logger.warning("Could not read %s: %s", rel, e)
    return found


# ── Gemma prompts ──────────────────────────────────────────────────────────────

PRIVACY_SCHEMA = {
    "company_name": "string or null",
    "address": "string or null — street and house number ONLY (e.g. 'Akazienstraße 3a'). Do NOT include ZIP code, city, or country here.",
    "contact_email": "string or null",
    "dpo_name": "string or null",
    "dpo_email": "string or null",
    "sub_processors": "list of strings (service/company names mentioned)",
    "data_categories": "list of strings (types of data processed)",
    "retention_clauses": "list of {category: string, duration: string}",
    "third_country_transfers": "list of {service: string, country: string}",
}

IMPRINT_SCHEMA = {
    "company_name": "string or null",
    "legal_form": "string or null (GmbH, UG, Inc., LLC, etc.)",
    "address": "string or null — street and house number ONLY (e.g. 'Hauptstraße 12'). Do NOT include ZIP code, city, or country here.",
    "city": "string or null",
    "zip_code": "string or null — digits only (e.g. '10823')",
    "country": "string or null",
    "contact_email": "string or null",
    "responsible_person": "string or null",
    "responsible_title": "string or null",
    "register_court": "string or null",
    "register_number": "string or null",
    "vat_id": "string or null",
}

DPA_SCHEMA = {
    "controller_name": "string or null",
    "processor_name": "string or null",
    "sub_processors": "list of strings",
    "data_categories": "list of strings",
    "retention_clauses": "list of {category: string, duration: string}",
    "dpo_name": "string or null",
    "dpo_email": "string or null",
}

SECURITY_SCHEMA = {
    "contact_email": "string or null",
    "contact_url": "string or null",
}

SCHEMAS: dict[str, dict] = {
    "privacy":  PRIVACY_SCHEMA,
    "imprint":  IMPRINT_SCHEMA,
    "dpa":      DPA_SCHEMA,
    "tos":      PRIVACY_SCHEMA,
    "cookies":  {"cookie_categories": "list of strings",
                 "retention_clauses": "list of {category: string, duration: string}"},
    "security": SECURITY_SCHEMA,
}


def _build_prompt(artifact_type: str, content: str) -> str:
    schema = SCHEMAS.get(artifact_type, PRIVACY_SCHEMA)
    schema_desc = json.dumps(schema, indent=2, ensure_ascii=False)
    excerpt = content[:30_000]
    truncated = "\n[... truncated ...]" if len(content) > 30_000 else ""
    return (
        f"You extract structured legal information from documents.\n\n"
        f"TASK: Read the following {artifact_type.upper()} document and extract the fields "
        f"defined in the schema. Return ONLY valid JSON matching the schema. "
        f"No prose, no markdown, no backticks. Use null for missing fields. Do not invent data.\n\n"
        f"SCHEMA:\n{schema_desc}\n\n"
        f"DOCUMENT:\n---\n{excerpt}{truncated}\n---\n\nJSON OUTPUT:"
    )


def _call_gemma(prompt: str) -> str:
    # ADR-127 Phase 1: transport via central client (httpx under the hood, so the
    # caller's `except httpx.HTTPError` path is preserved). raise_for_status fires
    # inside complete_ollama; JSON parsing of the result stays with the caller.
    data = complete_ollama(
        prompt,
        endpoint=OLLAMA_ENDPOINT,
        model=OLLAMA_MODEL,
        options={"temperature": 0.1, "num_predict": 2000},
        format="json",
        timeout=OLLAMA_TIMEOUT,
    )
    return data.get("response", "")


def _parse_json_output(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM output")
    return json.loads(match.group(0))


def extract_structured(file: LegalFile) -> ExtractionResult:
    """Extract structured fields from a legal file via Gemma."""
    result = ExtractionResult(
        source_file=file.relative_path,
        artifact_type=file.artifact_type,
        extracted_at=datetime.now(timezone.utc).isoformat(),
    )
    try:
        prompt = _build_prompt(file.artifact_type, file.content)
        raw = _call_gemma(prompt)
        result.raw_llm_output = raw
        result.extracted_fields = _parse_json_output(raw)
        logger.info(
            "Extracted %d fields from %s (type=%s)",
            len(result.extracted_fields), file.relative_path, file.artifact_type,
        )
    except httpx.HTTPError as e:
        result.error = f"Ollama call failed: {e}"
        logger.error("Gemma call failed for %s: %s", file.relative_path, e)
    except (ValueError, json.JSONDecodeError) as e:
        result.error = f"JSON parse failed: {e}"
        logger.error("JSON parse failed for %s: %s", file.relative_path, e)
    except Exception as e:
        result.error = f"Unexpected: {e}"
        logger.exception("Unexpected error extracting %s", file.relative_path)
    return result


# ── Merge into project ─────────────────────────────────────────────────────────

FIELD_MAPPING = {
    "company_name":       "company_name",
    "legal_form":         "legal_form",
    "address":            "address",
    "city":               "city",
    "zip_code":           "zip_code",
    "country":            "country",
    "contact_email":      "contact_email",
    "website":            "website_url",
    "responsible_person": "responsible_name",
    "responsible_title":  "responsible_title",
    "dpo_name":           "dpo_name",
    "dpo_email":          "dpo_email",
    "register_court":     "register_court",
    "register_number":    "register_number",
    "vat_id":             "vat_id",
}

ARTIFACT_PRIORITY = {"privacy": 1, "imprint": 2, "dpa": 3, "tos": 4, "cookies": 5, "security": 6}


def merge_into_project(
    extractions: list[ExtractionResult],
    project_name: str,
    db_conn,
) -> dict[str, Any]:
    """Merge extraction results into project_config (NULL-only, user wins).

    Returns summary dict for scan report.
    """
    successful = [e for e in extractions if not e.error]
    successful.sort(key=lambda e: ARTIFACT_PRIORITY.get(e.artifact_type, 99))

    # Highest-priority extraction wins per field
    consolidated: dict[str, tuple[Any, str]] = {}
    for ext in successful:
        for key, value in ext.extracted_fields.items():
            if value in (None, "", [], {}):
                continue
            project_field = FIELD_MAPPING.get(key)
            if not project_field or project_field in consolidated:
                continue
            consolidated[project_field] = (value, ext.source_file)

    # Load current config
    try:
        with db_conn.cursor() as cur:
            cur.execute("SELECT * FROM project_config WHERE project_name = %s", (project_name,))
            row = cur.fetchone()
            if not row:
                logger.warning("project_config missing for %s — cannot merge", project_name)
                return {"extractions_count": len(extractions), "extractions_successful": 0,
                        "fields_merged": 0, "fields_skipped": 0, "merged_fields": [],
                        "source_files": [], "errors": 1}
            col_names = [d[0] for d in cur.description]
            current = dict(zip(col_names, row))
    except Exception as e:
        logger.error("DB read failed in merge_into_project: %s", e)
        return {"extractions_count": len(extractions), "extractions_successful": 0,
                "fields_merged": 0, "fields_skipped": 0, "merged_fields": [],
                "source_files": [], "errors": 1}

    # Only update NULL/empty fields
    updates: dict[str, Any] = {}
    skipped: list[str] = []
    provenance: dict[str, dict] = {}
    for field_name, (value, source_file) in consolidated.items():
        if current.get(field_name):
            skipped.append(field_name)
            continue
        if field_name == "legal_form" and value:
            effective_company = updates.get("company_name") or current.get("company_name") or ""
            if str(value).strip("., ") in effective_company:
                skipped.append(field_name)
                continue
        updates[field_name] = value
        provenance[field_name] = {
            "source": source_file,
            "confidence": 0.85,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }

    if updates:
        set_clause = ", ".join(f"{k} = %s" for k in updates)
        set_clause += ", extraction_meta = extraction_meta || %s::jsonb"
        params = list(updates.values()) + [json.dumps(provenance), project_name]
        try:
            with db_conn.cursor() as cur:
                cur.execute(
                    f"UPDATE project_config SET {set_clause} WHERE project_name = %s",
                    params,
                )
            db_conn.commit()
            logger.info("Merged %d fields into project_config for %s: %s",
                        len(updates), project_name, list(updates.keys()))
        except Exception as e:
            logger.error("DB write failed in merge_into_project: %s", e)

    _log_audit(db_conn, project_name, extractions, updates)

    return {
        "extractions_count": len(extractions),
        "extractions_successful": len(successful),
        "fields_merged": len(updates),
        "fields_skipped": len(skipped),
        "merged_fields": list(updates.keys()),
        "source_files": [e.source_file for e in successful],
        "errors": len(extractions) - len(successful),
    }


def _log_audit(db_conn, project_name: str, extractions: list[ExtractionResult],
               updates: dict) -> None:
    try:
        with db_conn.cursor() as cur:
            for ext in extractions:
                cur.execute(
                    """INSERT INTO audit_log
                       (project_name, event_type, source_file, details, created_at)
                       VALUES (%s, 'repo_extraction', %s, %s, NOW())""",
                    (project_name, ext.source_file, json.dumps({
                        "artifact_type": ext.artifact_type,
                        "fields_extracted": list(ext.extracted_fields.keys()),
                        "error": ext.error,
                    })),
                )
        db_conn.commit()
    except Exception as e:
        logger.warning("Audit log write failed: %s", e)
