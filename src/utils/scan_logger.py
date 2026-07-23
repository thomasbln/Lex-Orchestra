"""
Structured JSON scan logger (ADR-030).
Writes one JSON line per event to /app/logs/lex-scan.log.

ADR-001: NEVER log raw PII values, code content, secrets, or system-prompt content.
         Log only: event types, entity types+scores, classification results, signal types.
"""
from __future__ import annotations

import gzip
import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

LOG_PATH = Path(os.getenv("SCAN_LOG_PATH", "/app/logs/lex-scan.log"))
MAX_LOG_SIZE_BYTES = int(os.getenv("SCAN_LOG_MAX_BYTES", str(10 * 1024 * 1024)))  # 10 MB
ARCHIVE_DIR = LOG_PATH.parent / "archive"


def _maybe_rotate() -> None:
    """Rotate lex-scan.log to archive/ when it exceeds MAX_LOG_SIZE_BYTES.

    Atomic rename first → fresh file starts immediately, then gzip the rotated
    file. If gzip fails, the uncompressed rotated file stays in archive/ so
    the audit trail is never lost.
    """
    if not LOG_PATH.exists():
        return
    try:
        if LOG_PATH.stat().st_size < MAX_LOG_SIZE_BYTES:
            return
    except OSError:
        return
    try:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        rotated = ARCHIVE_DIR / f"lex-scan-{ts}.log"
        LOG_PATH.rename(rotated)
        archive_path = ARCHIVE_DIR / f"lex-scan-{ts}.log.gz"
        with open(rotated, "rb") as src, gzip.open(archive_path, "wb") as dst:
            shutil.copyfileobj(src, dst)
        rotated.unlink()
    except Exception as e:
        logger.warning("scan_logger rotation failed (non-fatal): %s", e)


def _write(event: dict) -> None:
    """Write one JSON line to the scan log. Non-fatal on error."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _maybe_rotate()
        line = json.dumps(event, ensure_ascii=False) + "\n"
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        logger.warning("scan_logger write failed (non-fatal): %s", e)


def _base(run_id: str, event: str) -> dict:
    return {
        "ts":     datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": run_id[:8],
        "event":  event,
    }


# -- Layer 1 ------------------------------------------------------------------

def log_layer1_complete(run_id: str, signals: list[dict]) -> None:
    """Log Layer 1 completion -- signal types only, no evidence content."""
    _write({
        **_base(run_id, "layer1_complete"),
        "signals_count": len(signals),
        "signal_types":  [s["signal_type"] for s in signals],
        "sources":       list({s.get("source", "regex") for s in signals}),
    })


# -- Layer 2 ------------------------------------------------------------------

def log_layer2_entity(run_id: str, entity_type: str, score: float) -> None:
    """Log one Presidio entity detection -- type + score only, NEVER the raw value."""
    _write({
        **_base(run_id, "layer2_presidio"),
        "entity_type": entity_type,
        "score":       round(score, 2),
        "anonymised":  True,
    })


def log_layer2_summary(run_id: str, entities_found: int, entity_summary: str) -> None:
    """Log Presidio anonymisation summary for a snippet."""
    _write({
        **_base(run_id, "layer2_summary"),
        "entities_found":  entities_found,
        "entity_types":    entity_summary,
        "raw_value_logged": False,
    })


def log_layer2_content_scan(
    run_id: str,
    files_scanned: int,
    files_with_pii: int,
    entity_types_found: list[str],
) -> None:
    """Log Presidio content scan result (ADR-049).
    entity_types_found: deduplicated type names only — never raw PII values (ADR-001).
    """
    _write({
        **_base(run_id, "layer2_content_scan"),
        "files_scanned":      files_scanned,
        "files_with_pii":     files_with_pii,
        "entity_types_found": entity_types_found,
        "content_discarded":  True,
        "stays_local":        True,
    })


# -- Layer 3 ------------------------------------------------------------------

def log_layer3_classification(
    run_id: str, task: str, result: str, model: str
) -> None:
    """Log one Phi-4-mini classification result."""
    _write({
        **_base(run_id, "layer3_phi4"),
        "task":   task,
        "result": result,
        "model":  model,
    })


def log_layer3_dsfa(run_id: str, triggered: bool, reason: str) -> None:
    """Log DSFA trigger decision."""
    _write({
        **_base(run_id, "dsfa_trigger"),
        "triggered": triggered,
        "reason":    reason,
    })


# -- Scan lifecycle ------------------------------------------------------------

def log_scan_start(run_id: str, project: str, repo_url: str) -> None:
    _write({
        **_base(run_id, "scan_start"),
        "project":  project,
        "repo_url": repo_url,
    })


def log_scan_complete(
    run_id: str,
    signals_count: int,
    dsfa: bool,
    risk: str,
    doc_types: list[str],
) -> None:
    _write({
        **_base(run_id, "scan_complete"),
        "signals_count": signals_count,
        "dsfa":          dsfa,
        "risk":          risk,
        "doc_types":     doc_types,
    })


# -- Graph / Cypher -----------------------------------------------------------

def log_cypher(
    run_id: str,
    query_name: str,
    cypher_query: str,
    params_keys: list[str],
    result_count: int,
    cypher_queries: list[dict] | None = None,
) -> None:
    """Log a Neo4j Cypher query execution.

    cypher_query: primary/first query text (kept for backwards compatibility).
    cypher_queries: optional list of {label, cypher, result_count} for
                    multi-query functions like get_compliance_requirements.

    Logs the full query text so it can be verified that no PII is present.
    ADR-001: NEVER log query *parameter values* — only the parameter key names.
    The query string itself must only contain canonical service names,
    node labels, and relationship types — never customer data.
    """
    event = {
        **_base(run_id, "cypher_query"),
        "query_name":   query_name,
        "cypher":       cypher_query.strip(),
        "params_keys":  params_keys,
        "result_count": result_count,
    }
    if cypher_queries:
        event["cypher_queries"] = [
            {
                "label":        q.get("label", ""),
                "cypher":       (q.get("cypher") or "").strip(),
                "result_count": q.get("result_count", 0),
            }
            for q in cypher_queries
        ]
    _write(event)


# -- Graph response -----------------------------------------------------------

def log_cypher_result(
    run_id: str,
    query_name: str,
    doc_types: list[str],
    controls_count: int,
    risk_level: str,
    services_matched: list[str],
    active_risks: list[str],
) -> None:
    """Log what Neo4j returned — aggregated counts and type lists only.
    services_matched are canonical seed names (public knowledge), not customer data.
    Never logs raw node properties (ADR-001).
    """
    _write({
        **_base(run_id, "cypher_result"),
        "query_name":       query_name,
        "doc_types":        doc_types,
        "controls_count":   controls_count,
        "risk_level":       risk_level,
        "services_matched": services_matched,
        "active_risks":     active_risks,
    })


# -- LLM Reasoning ------------------------------------------------------------

def log_llm_reasoning(
    run_id: str,
    model: str,
    api_endpoint: str,
    input_contains_pii: bool,
    input_sources: list[str],
    service_categories: list[str],
    controls_count: int,
    output_priority_actions: int,
    output_tom_count: int,
    eu_ai_act_classification: str,
    leaves_network: bool,
) -> None:
    """Log Node 3 LLM reasoning call.

    This is the ONLY step where data leaves local infrastructure (to Anthropic API).
    Prompt contains ONLY: service categories (anonymised) + control texts (public).
    Never contains PII, file paths, customer code, or secrets (ADR-001).
    leaves_network=True is intentional and user-initiated via /scan.
    """
    _write({
        **_base(run_id, "llm_reasoning"),
        "model":                     model,
        "api_endpoint":              api_endpoint,
        "input_contains_pii":        input_contains_pii,
        "input_sources":             input_sources,
        "service_categories":        service_categories,
        "controls_count":            controls_count,
        "output_priority_actions":   output_priority_actions,
        "output_tom_count":          output_tom_count,
        "eu_ai_act_classification":  eu_ai_act_classification,
        "leaves_network":            leaves_network,
    })


# -- Document generation ------------------------------------------------------

def log_document_generation(
    run_id: str,
    doc_type: str,
    version: int,
    pii_fields_used: list[str],
    graph_source: str,
    llm_source: str,
    stays_local: bool,
    file_size_bytes: int,
) -> None:
    """Log Node 4 document generation — proves PII merge happens locally.

    pii_fields_used: field NAMES only from project_config (e.g. ["company_name", "address"])
    Never logs field VALUES (ADR-001).
    stays_local=True: document is never sent anywhere by this node.
    """
    _write({
        **_base(run_id, "document_generation"),
        "doc_type":        doc_type,
        "version":         version,
        "pii_fields_used": pii_fields_used,
        "graph_source":    graph_source,
        "llm_source":      llm_source,
        "stays_local":     stays_local,
        "file_size_bytes": file_size_bytes,
    })


# -- Telegram delivery --------------------------------------------------------

def log_telegram_delivery(
    run_id: str,
    doc_type: str,
    file_size_bytes: int,
    destination: str,
    leaves_network: bool,
    success: bool,
) -> None:
    """Log Telegram document delivery — the ONLY point where a finished
    document (with PII) leaves the local network.
    This is intentional and user-initiated (user ran /scan via Telegram).
    leaves_network=True is expected and documented.
    """
    _write({
        **_base(run_id, "telegram_delivery"),
        "doc_type":         doc_type,
        "file_size_bytes":  file_size_bytes,
        "destination":      destination,
        "leaves_network":   leaves_network,
        "success":          success,
    })


# -- Website / Impressum scan -------------------------------------------------

def log_impressum_scan(
    run_id: str,
    domain: str,
    url_tried: str,
    fields_found: list[str],
    fields_missing: list[str],
    law_signals: list[str],
    cached: bool,
) -> None:
    """Log website impressum scan result.
    domain and url are logged (public URLs, not PII).
    fields_found: field names only (e.g. ["company_name", "address"]) — not values.
    """
    _write({
        **_base(run_id, "impressum_scan"),
        "domain":         domain,
        "url_tried":      url_tried,
        "fields_found":   fields_found,
        "fields_missing": fields_missing,
        "law_signals":    law_signals,
        "cached":         cached,
    })


# -- Git clone / cleanup (ADR-032) --------------------------------------------

def log_git_clone(run_id: str, repo_url: str, clone_path: str) -> None:
    """Log successful git clone. repo_url is the public URL — tokens are never logged."""
    _write({
        **_base(run_id, "git_clone"),
        "repo_url":   repo_url,
        "clone_path": clone_path,
    })


def log_git_delete(run_id: str, clone_path: str) -> None:
    """Log clone deletion (ADR-001 — code never persists after scan)."""
    _write({
        **_base(run_id, "git_delete"),
        "clone_path": clone_path,
    })


# -- Errors -------------------------------------------------------------------

def log_error(run_id: str, error: str, layer: str | None = None) -> None:
    _write({
        **_base(run_id, "error"),
        "layer": layer,
        "error": error[:200],
    })
