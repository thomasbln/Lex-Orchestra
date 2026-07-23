"""
Lex-Orchestra — LangGraph Workflow
====================================
5-Node pipeline: Scout → Graph → Reasoning → Documents → Notify

Trigger:
    python src/workflow/main.py --project "MeinProjekt" --repo https://github.com/...
    python src/workflow/main.py --project "Lex-Orchestra" --repo . --dry-run

State is persisted in PostgreSQL (Supabase on Pi) via LangGraph checkpointer.
ADR-001: No PII leaves local infrastructure (see asset_translator.py).
"""

import argparse
import functools
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Optional

import json as _json
import urllib.request as _urllib_request

import psycopg2
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── LangGraph ─────────────────────────────────────────────────────────────────
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from typing_extensions import TypedDict

# ── Local modules ─────────────────────────────────────────────────────────────
from src.graph.asset_translator import AssetTranslator
from src.graph.graph_client import GraphClient, resolve_control_title
from src.scanner.legal_artifact_extractor import extract_structured, glob_legal_files, merge_into_project

def _resolve_db_url() -> str:
    mcp_url = os.getenv("MCP_SUPABASE_URL", "")
    db_url  = os.getenv("DATABASE_URL", "")
    if mcp_url:
        return mcp_url
    if db_url and "supabase-db" not in db_url:
        return db_url
    return db_url

DB_URL = _resolve_db_url()


# ── Compliance whitelist ────────────────────────────────────────────────────────

COMPLIANCE_PACKAGES = {
    # AI / LLM
    "openai", "anthropic", "google-generativeai",
    "mistralai", "cohere", "huggingface-hub", "replicate",
    # Payment
    "stripe", "paypalrestsdk", "braintree", "mollie",
    # Email / SMS
    "sendgrid", "mailchimp3", "twilio", "postmarker", "resend",
    # Cloud / Storage / Hosting
    "boto3", "google-cloud-storage", "azure-storage-blob",
    "azure", "digitalocean", "render", "railway", "flyio", "coolify", "hashicorp",
    # Auth
    "auth0", "clerk",
    # Analytics / Monitoring
    "mixpanel", "amplitude", "posthog", "sentry-sdk", "datadog",
    # Database / BaaS
    "supabase", "firebase-admin", "pymongo",
    # Vector Databases
    "pgvector", "pinecone", "pinecone-client",
    "weaviate", "weaviate-client",
    "qdrant", "qdrant-client",
    "chromadb", "chroma",
    "llama-index", "llama_index",
    "langchain",
    # NoSQL / Additional DBs
    "motor", "mongoengine",
    "google-cloud-firestore",
    "mariadb",
}

EXCLUDED_DIRS = {
    "docs", "tests", ".claude", "node_modules", ".venv", "venv",
    "test", "fixtures", "mocks", "spec", ".git",
}

# ADR-078: manifest discovery via GitHub tree-API
MANIFEST_FILENAMES = {
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "Pipfile",
    "composer.json",
    "go.mod",
}
MANIFEST_SUFFIX_PATTERNS = ("requirements-",)   # must also end with .txt
MANIFEST_MAX_DEPTH = 3

# Internal container/service names that must not be treated as third-party services.
# These appear in docker-compose files but are project-internal infrastructure.
INTERNAL_CONTAINERS = {
    "lex-agent", "mcp-neo4j-lex", "supabase-db",
    "postgres", "redis", "nginx", "traefik", "db", "app",
}


def _is_compliance_package(name: str) -> bool:
    """True if package name matches compliance whitelist."""
    n = name.lower().replace("-", "").replace("_", "")
    for pkg in COMPLIANCE_PACKAGES:
        p = pkg.lower().replace("-", "").replace("_", "")
        if p in n or n in p:
            return True
    return False


def _stable_project_id(repo_url: str, project_name: str) -> str:
    """Deterministic UUID from repo URL — same repo = same project_id."""
    import uuid as _uuid
    seed = (repo_url or project_name or "unknown").lower().strip().rstrip("/")
    return str(_uuid.uuid5(_uuid.NAMESPACE_URL, seed))


# ── ADR-029: UseCase classification mapping ──────────────────────────────────

# Maps Phi-4-mini classification output → Neo4j UseCase node type (uc.type)
# Verified against graph: MATCH (uc:UseCase) RETURN uc.type
USECASE_TYPE_MAP: dict[str, str | None] = {
    "hr_recruitment":           "hr_recruitment_screening",
    "credit_scoring":           "credit_scoring",
    "education_assessment":     "education_assessment",
    "healthcare_decision":      "healthcare_decision",
    "biometric_identification": "biometric_categorization",
    "critical_infrastructure":  "critical_infrastructure_mgmt",
    "law_enforcement":          "law_enforcement_ai",
    "customer_service":         "customer_service_chatbot",
    "content_generation":       "ai_content_generator",
    "general_assistant":        "ai_assistant_general",
    "none":                     None,
}


# ── ADR-068: live scan-run step updates ───────────────────────────────────

# approve_api runs in the SAME container as this pipeline (lex-agent sidecar,
# uvicorn on :8001) — localhost is the architecturally correct default. The old
# default pointed at the lex-dashboard container (a Next.js server on :3000
# that never listens on 8001), so on hosts without an explicit env override
# every step PATCH silently failed and scan_results stayed 'running' forever
# (cleanroom run 3, finding F21).
APPROVE_API_URL     = os.getenv("APPROVE_API_URL", "http://localhost:8001")
SCAN_INTERNAL_SECRET = os.getenv("SCAN_INTERNAL_SECRET", "")


def _update_step(
    run_id: str | None,
    step: str | None = None,
    status: str | None = None,
    signals_found: int | None = None,
    docs_generated: int | None = None,
    error: str | None = None,
) -> None:
    """
    Best-effort PATCH /scan/{run_id}/step on approve_api — never raises.
    Pipeline continues if approve_api is unreachable (ADR-068).
    ADR-129 PR 4: `error` rides along so a failed status carries its cause.
    """
    if not run_id:
        return
    try:
        payload = {}
        if step is not None:           payload["step"]           = step
        if status is not None:         payload["status"]         = status
        if signals_found is not None:  payload["signals_found"]  = signals_found
        if docs_generated is not None: payload["docs_generated"] = docs_generated
        if error is not None:          payload["error"]          = error[:500]
        if not payload:
            return
        body = _json.dumps(payload).encode("utf-8")
        req = _urllib_request.Request(
            f"{APPROVE_API_URL}/scan/{run_id}/step",
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Scan-Secret": SCAN_INTERNAL_SECRET,
            },
            method="PATCH",
        )
        _urllib_request.urlopen(req, timeout=3.0).read()
    except Exception as e:
        logger.debug("ADR-068 _update_step failed (non-fatal) run_id=%s: %s", run_id, e)


# ── DB helpers ─────────────────────────────────────────────────────────────────

def _get_project_id(cur, project_name: str) -> str:
    """ADR-080: resolve project_name → project_config.id, creating a stub row
    if needed. Same semantics as approve_api._get_project_id_by_name but
    workflow-local so this module stays free of interface-layer imports.
    """
    cur.execute("SELECT id FROM project_config WHERE project_name = %s", (project_name,))
    row = cur.fetchone()
    if row:
        return str(row[0])
    cur.execute(
        "INSERT INTO project_config (project_name) VALUES (%s) "
        "ON CONFLICT (project_name) DO UPDATE SET project_name = EXCLUDED.project_name "
        "RETURNING id",
        (project_name,),
    )
    return str(cur.fetchone()[0])


def _write_scan_result(state: "LexState") -> None:
    """Write one row to scan_results. Safe to skip on error — workflow must not crash."""
    if not DB_URL:
        logger.warning("No DB URL — skipping scan_results write")
        return
    graph  = state.get("graph_result") or {}
    scout  = state.get("scout_result") or {}
    try:
        with psycopg2.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                # ADR-080: resolve project_id for denormalised FK. The row
                # typically exists already (via approve_api insert at /scan start
                # or via Settings save) but we ensure it to stay idempotent.
                project_id = _get_project_id(cur, state["project_name"])

                # ADR-068: row may already exist (inserted by approve_api at /scan start
                # with status='running'). DO UPDATE overwrites the stub with final values.
                cur.execute(
                    """
                    INSERT INTO scan_results
                        (run_id, project_id, project_name, repo_url, live_url, overall_risk,
                         services_found, services_known, doc_types, scan_depth, dry_run, errors,
                         started_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (run_id) DO UPDATE SET
                        started_at     = COALESCE(scan_results.started_at, EXCLUDED.started_at),
                        project_id     = EXCLUDED.project_id,
                        repo_url       = COALESCE(EXCLUDED.repo_url, scan_results.repo_url),
                        live_url       = COALESCE(EXCLUDED.live_url, scan_results.live_url),
                        overall_risk   = EXCLUDED.overall_risk,
                        services_found = EXCLUDED.services_found,
                        services_known = EXCLUDED.services_known,
                        doc_types      = EXCLUDED.doc_types,
                        scan_depth     = EXCLUDED.scan_depth,
                        dry_run        = EXCLUDED.dry_run,
                        errors         = EXCLUDED.errors
                    """,
                    (
                        state["run_id"],
                        project_id,
                        state["project_name"],
                        state.get("repo_url"),
                        state.get("live_url"),
                        graph.get("overall_risk", "unknown"),
                        scout.get("total_found", 0),
                        len(scout.get("service_names", [])),
                        graph.get("doc_types", []),
                        state.get("scan_depth", "quick"),
                        state.get("dry_run", False),
                        state.get("errors", []),
                    ),
                )
                conn.commit()
        logger.debug("scan_results written: run_id=%s", state["run_id"])
    except Exception as e:
        logger.error("Failed to write scan_results: %s", e)
        state.setdefault("errors", []).append(f"DB scan_results: {e}")

    # Update last_scan timestamp in project_config
    try:
        with psycopg2.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE project_config
                    SET last_scan = NOW()
                    WHERE project_name = %s
                    """,
                    (state["project_name"],),
                )
                conn.commit()
        logger.debug("project_config.last_scan updated for %s", state["project_name"])
    except Exception as e:
        logger.warning("Failed to update last_scan: %s", e)


def _write_measure_snapshot(state: "LexState") -> None:
    """ADR-127 P4.2 — freeze the reachable controls' graph defaults into
    owner_measures at scan time, before document generation.

    One row per (project_id, control_id, run_id, lang): the DE row always, the
    EN row only where the graph carries ``default_tom_measure_en`` (today 19 BSI).
    The snapshot (default_text/title/framework) makes an old scan reproducible
    even if the graph drifts later (ADR-127 Option B). Owner edits
    (``text``/``edited_flag``) and a row's ``source`` are preserved on conflict —
    only the snapshot columns refresh. Inheritance of a prior run's owner edits
    is handled below (P4.4) — a new run inherits the prior run's confirmed owner
    edits + deactivations (most recent prior run with a snapshot, NOT
    status='complete'), only for controls this scan also reaches.

    Best-effort: never raises — a Supabase hiccup must not fail the scan
    (same discipline as ``_update_step``).
    """
    if not DB_URL:
        return
    controls = (state.get("graph_result") or {}).get("controls") or []
    run_id = state.get("run_id")
    project_name = state.get("project_name")
    if not controls or not run_id or not project_name:
        return

    # Dedup by control_id — the controls list carries per-service duplicates.
    seen: set[str] = set()
    rows: list[tuple] = []  # (control_id, lang, default_text, title, framework)
    for c in controls:
        cid = c.get("control_id")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        framework = c.get("framework")
        # DE row always (default_text may be None — an honest gap for a reachable
        # control without a measure; the seed-validator [Wächter B] is what
        # forbids that upstream, not this writer).
        rows.append((cid, "de", c.get("default_tom_measure"),
                     resolve_control_title(c, "de"), framework))
        # EN row only where the graph carries an EN measure.
        if c.get("default_tom_measure_en"):
            rows.append((cid, "en", c.get("default_tom_measure_en"),
                         resolve_control_title(c, "en"), framework))
    if not rows:
        return

    try:
        with psycopg2.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                project_id = _get_project_id(cur, project_name)

                # ADR-127 P4.4 — inherit owner work from the most recent prior run
                # that HAS A SNAPSHOT (authoritative marker; NOT status='complete',
                # which is approve_api decoration — RoT#1). Nested best-effort: a
                # failure here leaves inheritance empty → pure graph-default snapshot.
                prior_edits: dict[tuple, tuple] = {}   # (control_id, lang) -> (text, source)
                prior_deleted: set[str] = set()
                prev_run = None
                try:
                    cur.execute(
                        """
                        SELECT om.run_id FROM owner_measures om
                        JOIN scan_results sr ON sr.run_id = om.run_id
                        WHERE om.project_id = %s AND om.run_id <> %s
                        ORDER BY sr.started_at DESC NULLS LAST
                        LIMIT 1
                        """,
                        (project_id, run_id),
                    )
                    prev = cur.fetchone()
                    if prev:
                        prev_run = prev[0]
                        cur.execute(
                            """
                            SELECT control_id, lang, text, source FROM owner_measures
                            WHERE project_id = %s AND run_id = %s
                              AND edited_flag IS TRUE AND text IS NOT NULL
                            """,
                            (project_id, prev_run),
                        )
                        prior_edits = {(r[0], r[1]): (r[2], r[3]) for r in cur.fetchall()}
                        cur.execute(
                            "SELECT control_id FROM deleted_controls WHERE project_id = %s AND run_id = %s",
                            (project_id, prev_run),
                        )
                        prior_deleted = {r[0] for r in cur.fetchall()}
                except Exception as e:
                    logger.warning("Measure inheritance lookup failed (non-fatal): %s", e)
                    # ADR-129 PR 2 (audit K1/K2): the TX is aborted — without a rollback
                    # every following INSERT raises InFailedSqlTransaction and the outer
                    # catch swallows the WHOLE snapshot. And inheritance is all-or-nothing:
                    # prev_run must not survive a partial lookup, or the custom-carry
                    # below would commit a half-inherited state.
                    conn.rollback()
                    prev_run = None
                    prior_edits, prior_deleted = {}, set()

                inherited = 0
                for cid, lang, default_text, title, framework in rows:
                    owned = prior_edits.get((cid, lang))
                    if owned:
                        text_val, source_val, edited_val = owned[0], owned[1], True
                        inherited += 1
                    else:
                        text_val, source_val, edited_val = None, "lex-llm-draft", False
                    cur.execute(
                        """
                        INSERT INTO owner_measures
                            (project_id, project_name, control_id, run_id, lang,
                             default_text, title, framework, text, edited_flag, source)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (project_id, control_id, run_id, lang) DO UPDATE SET
                            default_text = EXCLUDED.default_text,
                            title        = EXCLUDED.title,
                            framework    = EXCLUDED.framework,
                            updated_at   = now()
                        """,
                        (project_id, project_name, cid, run_id, lang,
                         default_text, title, framework, text_val, edited_val, source_val),
                    )

                # Inherit deactivations — ONLY for controls this scan also reaches
                # (`seen`). A control the prior run deactivated but this scan does not
                # reach is not written (it would not render anyway). Trade-off: if a
                # later scan reaches it again there is no inheritance — the edit/flag
                # were bound to the old run → owner re-edits on the new run. Accepted
                # (ADR-127).
                deleted_inherited = 0
                for cid in (prior_deleted & seen):
                    cur.execute(
                        """
                        INSERT INTO deleted_controls (project_id, project_name, run_id, control_id)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (project_id, project_name, run_id, cid),
                    )
                    deleted_inherited += 1

                # ADR-127 PR5e: custom measures inherit UNCONDITIONALLY (never
                # scan-reachable → not in `rows`/`seen`). Carry each prior custom row
                # into the new run with its active state. A custom row deleted in the
                # prior is simply absent there (DELETE was final) → not carried.
                custom_inherited = 0
                if prev_run:
                    cur.execute(
                        "SELECT control_id, lang, text, title, framework FROM owner_measures "
                        "WHERE project_id = %s AND run_id = %s AND control_id LIKE 'custom-%%'",
                        (project_id, prev_run),
                    )
                    for cid, c_lang, text, title, framework in cur.fetchall():
                        cur.execute(
                            """
                            INSERT INTO owner_measures
                                (project_id, project_name, control_id, run_id, lang,
                                 text, title, framework, edited_flag, source)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true, 'owner')
                            ON CONFLICT (project_id, control_id, run_id, lang) DO NOTHING
                            """,
                            (project_id, project_name, cid, run_id, c_lang, text, title, framework),
                        )
                        if cid in prior_deleted:   # inherit the active state (inactive stays inactive)
                            cur.execute(
                                "INSERT INTO deleted_controls (project_id, project_name, run_id, control_id) "
                                "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                                (project_id, project_name, run_id, cid),
                            )
                        custom_inherited += 1
                conn.commit()
        logger.info("Measure snapshot: %d rows / %d controls for run %s (inherited %d edits, %d deactivations, %d custom)",
                    len(rows), len(seen), run_id, inherited, deleted_inherited, custom_inherited)
    except Exception as e:
        logger.warning("Measure snapshot failed (non-fatal): %s", e)


def _persist_scan_signals(
    run_id: str,
    project_name: str,
    signals: list[dict],
) -> None:
    """
    Write scan_signals rows to Supabase.
    Called after signal extraction, before UUID mapping.
    evidence[] contains only relative file paths (ADR-001 compliant).
    Non-fatal: workflow continues on error.
    """
    if not signals or not DB_URL:
        return
    try:
        with psycopg2.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                # ADR-080: resolve once per batch
                project_id = _get_project_id(cur, project_name)
                for sig in signals:
                    cur.execute(
                        """
                        INSERT INTO scan_signals
                            (run_id, project_id, project_name, signal_type, value,
                             confidence, evidence, source)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            run_id,
                            project_id,
                            project_name,
                            sig["signal_type"],
                            sig.get("value"),
                            sig["confidence"],
                            sig.get("evidence", []),    # paths only — ADR-001
                            sig.get("source", "regex"),
                            # NOTE: evidence_snippets intentionally NOT persisted — RAM only (ADR-070)
                        ),
                    )
                conn.commit()
        logger.info(
            "Persisted %d scan signals for run %s", len(signals), run_id[:8]
        )
    except Exception as e:
        logger.warning("scan_signals persist failed (non-fatal): %s", e)


def _get_github_token(project_name: str, repo_url: str = "") -> str | None:
    """Resolve GitHub PAT via vault.decrypted_secrets. ADR-032/033/083.

    Precedence: repo-level override (project_repos) → project-level default
    (project_tokens) → env var GITHUB_TOKEN. RLS on vault.decrypted_secrets
    means only service_role can reach the ciphertext-at-rest — Lex-Orchestra
    runs as service_role, dashboard JWTs structurally cannot.
    """
    if not DB_URL:
        return os.getenv("GITHUB_TOKEN") or None
    try:
        with psycopg2.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                if repo_url:
                    cur.execute(
                        """
                        SELECT ds.decrypted_secret
                          FROM project_repos pr
                          JOIN vault.decrypted_secrets ds
                               ON ds.id = pr.github_token_secret_id
                         WHERE pr.project_name = %s
                           AND pr.repo_url     = %s
                           AND pr.is_active    = TRUE
                        """,
                        (project_name, repo_url),
                    )
                    row = cur.fetchone()
                    if row and row[0]:
                        return row[0]
                cur.execute(
                    """
                    SELECT ds.decrypted_secret
                      FROM project_tokens pt
                      JOIN vault.decrypted_secrets ds
                           ON ds.id = pt.github_token_secret_id
                     WHERE pt.project_name = %s
                    """,
                    (project_name,),
                )
                row = cur.fetchone()
                if row and row[0]:
                    return row[0]
    except Exception as e:
        logger.warning("Could not load github_token: %s", e)
    return os.getenv("GITHUB_TOKEN") or None


# ── State ──────────────────────────────────────────────────────────────────────

class LexState(TypedDict):
    # Input
    project_name:   str
    repo_url:       Optional[str]
    live_url:       Optional[str]
    scan_depth:     str             # "quick" | "full" | "deep"
    dry_run:        bool

    # Node 1 — Scout
    scout_result:            Optional[dict]       # anonymized: [{uuid, type, category, canonical_name}]
    security_findings:       Optional[list[dict]] # from Signal Category 2 — anonymised file paths
    deployment_signals:      Optional[list[dict]] # from Signal Category 3, verified=False
    risk_signals:            Optional[list[dict]] # ADR-027: raw signals from Schicht 1, pre-UUID mapping
    repo_extraction_summary: Optional[dict]       # ADR-087: legal artifact extraction results

    # Node 2 — Graph Enrichment
    graph_result:       Optional[dict]  # {docs_required, controls, risk_levels, overall_risk}
    graph_usecase_type: Optional[str]   # ADR-060: UseCase type for risk override

    # Node 3 — Legal Reasoning
    reasoning_result: Optional[dict]  # {summary, priority_actions, eu_ai_act_classification, tom_implementations}

    # Node 4 — Documents
    generated_docs: list[dict]      # [{id, doc_type, file_path, version, status}]

    # Node 4b — Validator
    validation_result:        Optional[list[dict]]  # one entry per generated doc
    config_requested:         bool                  # True after request_config fires (Phase 2)
    validator_retries:        int                   # loop guard — max 1 retry (Phase 2)
    pending_telegram_message: Optional[str]         # set by request_config (Phase 2)

    # Node 5 — Notify
    notification_sent: bool

    # Meta
    run_id:   str
    # LastValue by design — nodes mutate in place and return the full state;
    # partial-returning nodes MUST merge errors explicitly (see
    # node_document_validator). An operator.add reducer would duplicate the
    # list on every full-state return (ADR-129 PR 5).
    errors:   list[str]


# ── Node 1 — Scout ─────────────────────────────────────────────────────────────

def node_scout(state: LexState) -> LexState:
    """
    Scan repo/URL for services and third-party dependencies.
    Stores real asset data in PostgreSQL, returns only UUIDs to the pipeline.
    """
    # run_id may be absent when invoked via the LangGraph Server API
    if not state.get("run_id"):
        state["run_id"] = str(uuid.uuid4())
    state.setdefault("errors", [])

    # ADR-030: log scan start
    try:
        from src.utils.scan_logger import log_scan_start
        log_scan_start(state["run_id"], state["project_name"], state.get("repo_url", ""))
    except Exception:
        pass

    # ADR-068: clone is the first effective phase inside scout
    _update_step(state.get("run_id"), step="clone")

    repo_url = state.get("repo_url", "")
    project_token = None

    if repo_url and "github.com" in repo_url:
        # Resolve per-project token (ADR-033: project_repos → project_tokens → env)
        project_token = _get_github_token(state["project_name"], repo_url)
        # GitHub URL → fetch files via API (supports private repos via token)
        raw = _scout_fallback(repo_url, project_token)
    else:
        try:
            from src.scout.lex_orchestra_scout import run_scout
            raw = run_scout(
                repo_path=repo_url or None,
                live_url=state.get("live_url"),
                depth=state.get("scan_depth", "quick"),
            )
        except ImportError:
            logger.warning("Scout not yet implemented — using minimal fallback")
            raw = _scout_fallback(repo_url or ".")

    # Surface GitHub API errors (private repo, bad token) to pipeline errors
    if raw.get("error") == "private_no_token":
        dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:3000")
        setup_link = f"{dashboard_url}/setup?project={state['project_name']}"
        state["errors"].append(
            f"🔒 Private Repo — GitHub Token erforderlich.\n"
            f"Setup öffnen: {setup_link}"
        )
        logger.error("Private repo, no token: %s", repo_url)
        state["scout_result"] = {"anonymized": [], "service_names": []}
        return state
    elif raw.get("error") == "private_bad_token":
        state["errors"].append("🔒 GitHub Token ungültig oder kein Zugriff auf Repo.")
        logger.error("Private repo, bad token: %s", repo_url)
        state["scout_result"] = {"anonymized": [], "service_names": []}
        return state

    if not raw or (not raw.get("services") and not raw.get("service_names")):
        logger.warning("Scout returned no services")
        state["scout_result"] = {"anonymized": [], "service_names": []}
        return state

    # Deep pgvector detection for local repos (beyond package name)
    repo_local = state.get("repo_url", "")
    if repo_local and os.path.isdir(repo_local) and _detect_pgvector(repo_local):
        raw_services = raw["services"]
        pgvector_found = any(
            "pgvector" in s.get("name", "").lower()
            for s in raw_services
        )
        if not pgvector_found:
            raw_services.append({
                "name": "pgvector",
                "category": "vector_db",
                "type": "deep_scan",
                "source": "pgvector_extension_detected",
                "confidence": 0.9,
            })
            logger.info("Deep scan: pgvector extension detected")

    translator = AssetTranslator()
    translator.setup()

    project_id = _stable_project_id(state.get("repo_url", ""), state["project_name"])
    records = translator.store_assets(project_id, raw["services"])
    anonymized = translator.anonymize(records)

    # Canonical names that exist in Neo4j seed (for graph queries)
    known_names = {
        r["canonical_name"]
        for r in anonymized
        if r.get("canonical_name")
    }

    # Merge manifest-detected service names (already canonical from signal_map)
    manifest_names = raw.get("service_names", [])
    # Deduplicate case-insensitively, preferring manifest canonical casing
    by_lower: dict[str, str] = {}
    for name in manifest_names:
        by_lower[name.lower()] = name
    for name in known_names:
        by_lower.setdefault(name.lower(), name)
    all_service_names = sorted(by_lower.values())

    # ADR-072: ServiceCategories from LLM classification (pure-category sub-processors)
    manifest_categories = raw.get("service_categories", [])
    all_service_categories = sorted(set(manifest_categories))

    # ADR-110: derive payment integration-mode from the raw manifest names while
    # they still exist (the canonical set-collapse already discarded them inside
    # the scout). Carry it as an extensible per-service dict — {integration_mode}
    # today, but a dict on purpose so ADR-111's provenance field can dock onto the
    # same carrier without a transport change.
    service_modes: dict[str, dict] = {}
    stripe_mode = _derive_stripe_integration_mode(raw.get("services", []))
    if stripe_mode:
        from src.scout.signal_map import canonical as _canonical
        stripe_canonical = _canonical("stripe") or "Stripe"
        service_modes[stripe_canonical] = {"integration_mode": stripe_mode}
        logger.info("ADR-110: Stripe integration_mode=%s (canonical=%s)",
                    stripe_mode, stripe_canonical)

    logger.info(
        "Scout: %d services found, %d code-signal, %d manifest, %d total unique, %d llm categories",
        len(records), len(known_names), len(manifest_names),
        len(all_service_names), len(all_service_categories),
    )

    state["scout_result"] = {
        "anonymized":         anonymized,
        "service_names":      all_service_names,       # code signals + manifest services
        "service_categories": all_service_categories,  # ADR-072
        "service_modes":      service_modes,            # ADR-110 transient carrier (dict values)
        "total_found":        len(records),
    }

    state["security_findings"]  = raw.get("security_findings", [])
    state["deployment_signals"] = raw.get("deployment_signals", [])

    # ADR-062: auto-seed high-confidence Gemma4 classifications as Service nodes
    llm_classified = raw.get("llm_classified", [])
    if llm_classified:
        try:
            with GraphClient() as _gc:
                for svc in llm_classified:
                    confidence = svc.get("confidence", 0.0)
                    canonical_name = svc.get("canonical_name")
                    category = svc.get("category", "unknown")
                    if confidence >= 0.75 and canonical_name and category != "unknown":
                        if not _gc.get_service_info(canonical_name):
                            _gc.create_service_node_from_llm(
                                name=canonical_name,
                                category=category,
                                country=svc.get("country", "unknown"),
                                confidence=confidence,
                                source="gemma4_fallback",
                            )
        except Exception as e:
            logger.warning("ADR-062 auto-seed failed (non-fatal): %s", e)

    # ADR-032 — Git Clone for local Layer 1 scan (GitHub repos)
    clone_path = None
    repo_local = state.get("repo_url", "")
    if repo_url and "github.com" in repo_url:
        try:
            from src.scout.git_clone import clone_repo
            clone_path = clone_repo(repo_url, state["run_id"], project_token)
            if clone_path:
                repo_local = str(clone_path)
                logger.info("ADR-032: using local clone for Layer 1: %s", clone_path)
                _update_step(state.get("run_id"), step="infra")  # ADR-068: clone done → infra detection
            elif not project_token:
                dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:3000")
                setup_link = f"{dashboard_url}/setup?project={state['project_name']}"
                state["errors"].append(
                    f"🔒 Private Repo — GitHub Token erforderlich.\n"
                    f"Setup öffnen: {setup_link}"
                )
                logger.warning("ADR-032: clone failed (no token) — Layer 1 skipped")
                state["scout_result"] = {"anonymized": [], "service_names": []}
                return state
            else:
                logger.warning("ADR-032: clone failed — Layer 1 skipped for GitHub repo")
        except Exception as e:
            logger.warning("ADR-032: git clone failed (non-fatal): %s", e)

    # ADR-028 Layer 1 — regex scanner (ADR-049: now returns content_snippets too)
    if repo_local and os.path.isdir(repo_local):
        _update_step(state.get("run_id"), step="signals")  # ADR-068: infra done → signal extraction
        try:
            from src.scanner.regex_scanner import scan as regex_scan
            layer1_result = regex_scan(Path(repo_local), run_id=state["run_id"])

            # Handle both old (list) and new (tuple) return format
            if isinstance(layer1_result, tuple):
                layer1_signals, content_snippets = layer1_result
            else:
                layer1_signals, content_snippets = layer1_result, {}

            existing_types = {s["signal_type"] for s in raw.get("risk_signals", [])}
            for sig in layer1_signals:
                if sig["signal_type"] not in existing_types:
                    raw.setdefault("risk_signals", []).append(sig)
            logger.info("Layer 1: %d new signals added", len(layer1_signals))

            # ADR-049 Layer 2 content scan — Presidio on ALL file content (Option C)
            if content_snippets:
                try:
                    from src.scanner.pii_filter import anonymize_file_contents, is_available
                    if is_available():
                        anonymize_file_contents(content_snippets, run_id=state["run_id"])
                        logger.info(
                            "ADR-049: Presidio content scan complete — %d files, content discarded",
                            len(content_snippets),
                        )
                    else:
                        logger.warning("ADR-049: Presidio not available — content scan skipped")
                except Exception as e:
                    logger.warning("ADR-049: content scan failed (non-fatal): %s", e)

        except Exception as e:
            logger.warning("Layer 1 regex scan failed (non-fatal): %s", e)

    # ADR-028 Layer 2 — Presidio PII filter on signal evidence[]
    try:
        from src.scanner.pii_filter import anonymize_signals, is_available
        if is_available():
            raw["risk_signals"] = anonymize_signals(raw.get("risk_signals", []), run_id=state["run_id"])
            logger.info(
                "Layer 2: Presidio applied to %d risk_signals",
                len(raw.get("risk_signals", [])),
            )
        else:
            logger.warning("Layer 2: Presidio not available — skipping")
    except Exception as e:
        logger.warning("Layer 2 PII filter failed (non-fatal): %s", e)

    # ADR-028 + ADR-050 Layer 3 — local LLM classifier (model env-driven)
    # Only runs if AI/decision signals were surfaced by the Scout layer.
    has_ai = any(
        s["signal_type"] in ("ai_usage", "autonomy", "system_prompt", "decision_logic")
        for s in raw.get("risk_signals", [])
    )
    if has_ai:
        try:
            from src.scanner.llm_classifier import (
                classify_all,
                compute_dsfa_trigger,
                is_available as llm_available,
                MODEL as LAYER3_MODEL,
            )
            if llm_available():
                from src.scanner.pii_filter import anonymize

                # ADR-070: Layer 3 receives code snippets (±3 line context) instead of paths.
                # Priority signals first — they hold the most useful snippets for UseCase classification.
                LAYER3_PRIORITY_SIGNALS = {"ai_usage", "autonomy", "system_prompt", "decision_logic"}
                evidence_snippets: list[str] = []
                for sig in raw.get("risk_signals", []):
                    if sig.get("signal_type") in LAYER3_PRIORITY_SIGNALS:
                        evidence_snippets.extend(sig.get("evidence_snippets", []))
                if not evidence_snippets:
                    for sig in raw.get("risk_signals", []):
                        evidence_snippets.extend(sig.get("evidence_snippets", []))
                if not evidence_snippets:
                    logger.warning(
                        "Layer 3: no evidence_snippets — classifier will receive empty input"
                    )
                anon_snippet = anonymize("\n".join(evidence_snippets[:10]), run_id=state["run_id"])

                classifications = classify_all(anon_snippet, run_id=state["run_id"])
                dsfa = compute_dsfa_trigger(classifications)

                for task_key, value in classifications.items():
                    if value != "none":
                        raw.setdefault("risk_signals", []).append({
                            "signal_type": task_key,
                            "value":       value,
                            "confidence":  0.60,
                            "evidence":    [],
                            "source":      LAYER3_MODEL,
                        })
                if dsfa:
                    raw.setdefault("risk_signals", []).append({
                        "signal_type": "dsfa_trigger",
                        "value":       "true",
                        "confidence":  0.85,
                        "evidence":    [],
                        "source":      LAYER3_MODEL,
                    })
                logger.info("Layer 3: classifications=%s dsfa=%s", classifications, dsfa)

                # ADR-030: log DSFA trigger
                try:
                    from src.utils.scan_logger import log_layer3_dsfa
                    reason = "art9" if classifications.get("art9_category", "none") != "none" else (
                        "autonomous_decision" if dsfa else "no art9, no autonomous decision"
                    )
                    log_layer3_dsfa(state["run_id"], dsfa, reason)
                except Exception:
                    pass
            else:
                logger.warning("Layer 3: Ollama not available — skipping")
        except Exception as e:
            logger.warning("Layer 3 failed (non-fatal): %s", e)

    # ADR-029: system prompt extraction + UseCase classification
    if repo_local and os.path.isdir(repo_local):
        try:
            from src.scanner.regex_scanner import extract_system_prompt
            from src.scanner.pii_filter import anonymize_system_prompt
            from src.scanner.llm_classifier import classify_system_prompt_role, is_available as llm_available

            system_prompt_raw, prompt_source = extract_system_prompt(Path(repo_local))

            if system_prompt_raw and llm_available():
                # Anonymize before any further processing
                system_prompt_clean = anonymize_system_prompt(system_prompt_raw)

                # Classify role locally (Phi-4-mini on Pi)
                role, confidence = classify_system_prompt_role(system_prompt_clean)

                # Map Phi-4-mini label → graph UseCase node type
                graph_usecase_type = USECASE_TYPE_MAP.get(role)

                if graph_usecase_type:
                    # ADR-060: expose usecase_type to downstream graph enrichment
                    state["graph_usecase_type"] = graph_usecase_type
                    # Write mapped type to project_config (non-fatal)
                    try:
                        with psycopg2.connect(DB_URL) as conn:
                            with conn.cursor() as cur:
                                cur.execute(
                                    """
                                    UPDATE project_config
                                    SET ai_usecase_type = %s,
                                        ai_usecase_verified = false,
                                        ai_usecase_source = 'phi4_mini_classification',
                                        ai_usecase_confidence = %s
                                    WHERE project_name = %s
                                    """,
                                    (graph_usecase_type, confidence, state["project_name"]),
                                )
                                conn.commit()
                        logger.info(
                            "ai_usecase_type set: %s -> %s (confidence: %.2f, source: %s)",
                            role, graph_usecase_type, confidence, prompt_source,
                        )
                    except Exception as e:
                        logger.warning("ai_usecase_type update failed (non-fatal): %s", e)

                    # Add to signals for scan_signals table (ADR-027)
                    raw.setdefault("risk_signals", []).append({
                        "signal_type": "system_prompt_role",
                        "value":       graph_usecase_type,
                        "confidence":  confidence,
                        "evidence":    [f"system_prompt detected in {prompt_source}"],
                        "source":      "phi4_mini",
                    })

        except Exception as e:
            logger.warning("ADR-029 system prompt classification failed (non-fatal): %s", e)

    # ADR-027 — persist risk signals before UUID mapping
    risk_signals = raw.get("risk_signals", [])
    state["risk_signals"] = risk_signals

    # ADR-068: signal extraction done — report count (leave step to next node)
    _update_step(
        state.get("run_id"),
        signals_found=len(risk_signals),
    )

    # Write scan_results FIRST so scan_signals FK (run_id) is satisfied
    _write_scan_result(state)

    if risk_signals:
        _persist_scan_signals(
            run_id=state["run_id"],
            project_name=state["project_name"],
            signals=risk_signals,
        )

    # ADR-094: persist detected service names for assistant gap context
    _detected_service_names = (state.get("scout_result") or {}).get("service_names", [])
    if _detected_service_names:
        _service_signals = [
            {
                "signal_type": "service_detected",
                "value": name,
                "confidence": 0.8,
                "evidence": [],
                "source": "scout_catalog",
            }
            for name in _detected_service_names
        ]
        _persist_scan_signals(
            run_id=state["run_id"],
            project_name=state["project_name"],
            signals=_service_signals,
        )
        logger.info("Persisted %d service_detected signals", len(_service_signals))

    if state["security_findings"]:
        logger.info("Security: %d findings", len(state["security_findings"]))
    if state["deployment_signals"]:
        logger.info("Deployment signals: %d", len(state["deployment_signals"]))

    # ADR-087: Repo-content extraction — must run before cleanup deletes the clone
    repo_extraction_summary: dict = {}
    if clone_path is not None:
        try:
            project_name_for_extraction = state.get("project_name", "")
            legal_files = glob_legal_files(clone_path)
            logger.info("ADR-087: found %d legal artifacts in clone", len(legal_files))
            if legal_files:
                db_url = os.environ.get("DATABASE_URL", "")
                with psycopg2.connect(db_url) as db_conn:
                    extractions = [extract_structured(lf) for lf in legal_files]
                    repo_extraction_summary = merge_into_project(
                        extractions, project_name_for_extraction, db_conn
                    )
                    logger.info("ADR-087: extraction summary: %s", repo_extraction_summary)
        except Exception as e:
            logger.warning("ADR-087: repo extraction failed (non-fatal): %s", e)
    state["repo_extraction_summary"] = repo_extraction_summary

    # ADR-032 — Cleanup: always delete clone (ADR-001 — no code persists)
    if clone_path is not None:
        try:
            from src.scout.git_clone import cleanup_clone
            cleanup_clone(clone_path, state["run_id"])
        except Exception as e:
            logger.warning("ADR-032: clone cleanup failed: %s", e)

    return state


def _fetch_github_file(owner: str, repo: str, path: str, token: str) -> str | None:
    """
    Fetch a single file from the GitHub Contents API.
    Returns raw file content as a string, or None if not found / on error.
    """
    import requests
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {"Accept": "application/vnd.github.v3.raw"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.text
        if resp.status_code != 404:
            logger.warning("GitHub API %s → %s: %s", path, resp.status_code, resp.text[:120])
        return None
    except Exception as e:
        logger.warning("GitHub fetch failed (%s): %s", path, e)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# ADR-078: monorepo-aware manifest discovery via git/trees API
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_github_tree(owner: str, repo: str, token: str | None) -> list[dict]:
    """Single Tree-API call (recursive). Returns [] on error."""
    import requests
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            logger.warning("GitHub tree fetch failed: status=%d", resp.status_code)
            return []
        return resp.json().get("tree", []) or []
    except Exception as e:
        logger.warning("GitHub tree fetch failed: %s", e)
        return []


def _discover_github_manifests(tree: list[dict]) -> list[tuple[str, str]]:
    """
    Given the git/trees payload, return [(path, filename), ...] for all
    package-manifest files within MANIFEST_MAX_DEPTH and outside EXCLUDED_DIRS.

    No deduplication: a Next.js root package.json alongside a Node backend/
    package.json are both relevant. Workspace-redundant manifests (Lerna/Nx)
    are cheap because add_canonical is Set-based — duplicate package names
    fold automatically. Parity with the local _scan_manifests path (rglob).
    """
    def _is_manifest(name: str) -> bool:
        if name in MANIFEST_FILENAMES:
            return True
        if name.endswith(".txt") and any(
            name.startswith(p) for p in MANIFEST_SUFFIX_PATTERNS
        ):
            return True
        return False

    results: list[tuple[str, str]] = []
    for item in tree:
        if item.get("type") != "blob":
            continue
        path = item.get("path", "")
        if not path:
            continue
        parts = path.split("/")
        name = parts[-1]
        if not _is_manifest(name):
            continue
        if len(parts) - 1 > MANIFEST_MAX_DEPTH:
            continue
        if any(part in EXCLUDED_DIRS for part in parts):
            continue
        results.append((path, name))

    logger.info(
        "GitHub manifest discovery: %d manifests (%s)",
        len(results), [p for p, _ in results],
    )
    return results


def _discover_github_composes(tree: list[dict]) -> list[str]:
    """Return sub-directory docker-compose paths from the tree (root already handled separately)."""
    return [
        item["path"] for item in tree
        if item.get("type") == "blob"
        and item.get("path", "") != "docker-compose.yml"
        and item.get("path", "") != "docker-compose.yaml"
        and item.get("path", "").endswith(("docker-compose.yml", "docker-compose.yaml"))
        and not any(part in EXCLUDED_DIRS for part in item["path"].split("/"))
    ]


# ── Manifest parsers (ADR-078) ──────────────────────────────────────────────
# Uniform signature: (content, source, services_out, add_canonical) -> None.
# services_out is mutated for the compliance-whitelist entries; add_canonical
# handles the canonical/LLM-category path via signal_map.

def _parse_package_json(content: str, source: str, services: list, add_canonical) -> None:
    import json as _json
    try:
        pkg = _json.loads(content)
    except Exception as e:
        logger.warning("package.json parse error (%s): %s", source, e)
        return
    deps: dict = {}
    deps.update(pkg.get("dependencies", {}) or {})
    deps.update(pkg.get("devDependencies", {}) or {})
    added = 0
    for dep in deps:
        clean = dep.lstrip("@")
        if "/" in clean:
            scope, name = clean.split("/", 1)
            add_canonical(scope)
            add_canonical(name)
        else:
            add_canonical(clean)
        if _is_compliance_package(dep):
            services.append({
                "name": dep,
                "category": _guess_category(dep),
                "type": "dependency",
                "source": source,
                "confidence": 0.6,
            })
            added += 1
    logger.info("GitHub: parsed %s (%d compliance deps)", source, added)


def _parse_requirements_txt(content: str, source: str, services: list, add_canonical) -> None:
    added = 0
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name = line.split(">=")[0].split("==")[0].split("<=")[0].split("[")[0].strip()
        if name:
            add_canonical(name)
            if _is_compliance_package(name):
                services.append({
                    "name": name,
                    "category": _guess_category(name),
                    "type": "dependency",
                    "source": source,
                    "confidence": 0.5,
                })
                added += 1
    logger.info("GitHub: parsed %s (%d compliance deps)", source, added)


def _parse_pyproject_toml(content: str, source: str, services: list, add_canonical) -> None:
    import re as _re
    found = 0
    for pkg in _re.findall(r'["\']([a-zA-Z0-9_\-]+)(?:[>=<!\s]|["\'])', content):
        add_canonical(pkg)
        found += 1
    logger.info("GitHub: parsed %s (%d candidate tokens)", source, found)


def _parse_pipfile(content: str, source: str, services: list, add_canonical) -> None:
    in_packages = False
    added = 0
    for line in content.splitlines():
        stripped = line.strip()
        if stripped in ("[packages]", "[dev-packages]"):
            in_packages = True
            continue
        if stripped.startswith("[") and in_packages:
            in_packages = False
            continue
        if in_packages and "=" in stripped and not stripped.startswith("#"):
            pkg = stripped.split("=")[0].strip().strip('"\'')
            if pkg:
                add_canonical(pkg)
                added += 1
    logger.info("GitHub: parsed %s (%d packages)", source, added)


def _parse_composer_json(content: str, source: str, services: list, add_canonical) -> None:
    import json as _json
    try:
        data = _json.loads(content)
    except Exception as e:
        logger.warning("composer.json parse error (%s): %s", source, e)
        return
    added = 0
    for pkg_name in data.get("require", {}) or {}:
        if pkg_name == "php":
            continue
        short = pkg_name.split("/")[-1]
        for part in pkg_name.split("/"):
            add_canonical(part)
        if _is_compliance_package(short) or _is_compliance_package(pkg_name):
            services.append({
                "name": short,
                "category": _guess_category(pkg_name),
                "type": "dependency",
                "source": source,
                "confidence": 0.7,
            })
            added += 1
    logger.info("GitHub: parsed %s (%d compliance deps)", source, added)


def _parse_go_mod(content: str, source: str, services: list, add_canonical) -> None:
    import re as _re
    found = 0
    for module in _re.findall(r"^\s+([^\s]+)\s+v", content, _re.MULTILINE):
        for part in module.split("/"):
            add_canonical(part)
            found += 1
    logger.info("GitHub: parsed %s (%d module tokens)", source, found)


def _dispatch_manifest(name: str, content: str, path: str, services: list, add_canonical) -> None:
    if name == "package.json":
        _parse_package_json(content, path, services, add_canonical)
    elif name == "requirements.txt" or name.startswith("requirements-"):
        _parse_requirements_txt(content, path, services, add_canonical)
    elif name == "pyproject.toml":
        _parse_pyproject_toml(content, path, services, add_canonical)
    elif name == "Pipfile":
        _parse_pipfile(content, path, services, add_canonical)
    elif name == "composer.json":
        _parse_composer_json(content, path, services, add_canonical)
    elif name == "go.mod":
        _parse_go_mod(content, path, services, add_canonical)


def _scout_github(owner: str, repo: str, token: str) -> dict:
    """
    Fetch and parse key files from a GitHub repo via the GitHub APIs.

    ADR-078: manifest discovery uses a single git/trees call; package manifests
    (package.json, requirements*.txt, pyproject.toml, Pipfile, composer.json,
    go.mod) are discovered across subdirectories up to MANIFEST_MAX_DEPTH.
    Root-only probes are used as fallback when the tree call fails.

    Covers: docker-compose.yml (root + subdirs), package.json, requirements.txt,
    pyproject.toml, Pipfile, composer.json, go.mod, .env.example.
    """
    import requests as _requests
    import yaml

    services = []

    # ── Repo reachability check (detect private repo without token) ────────────
    check_url = f"https://api.github.com/repos/{owner}/{repo}"
    check_headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        check_headers["Authorization"] = f"Bearer {token}"
    try:
        check_resp = _requests.get(check_url, headers=check_headers, timeout=10)
        if check_resp.status_code in (403, 404) and not token:
            logger.error("GitHub repo %s/%s not accessible (private?) — no token provided", owner, repo)
            return {"services": [], "error": "private_no_token"}
        if check_resp.status_code in (403, 404) and token:
            logger.error("GitHub repo %s/%s not accessible — token invalid or no access", owner, repo)
            return {"services": [], "error": "private_bad_token"}
    except Exception as e:
        logger.warning("GitHub repo check failed: %s", e)

    # ── docker-compose.yml (root) ──────────────────────────────────────────────
    for dc_path in ["docker-compose.yml", "docker-compose.yaml"]:
        content = _fetch_github_file(owner, repo, dc_path, token)
        if content:
            try:
                data = yaml.safe_load(content)
                for svc_name, svc_cfg in (data.get("services") or {}).items():
                    if svc_name in INTERNAL_CONTAINERS:
                        continue
                    image = (svc_cfg or {}).get("image", "")
                    services.append({
                        "name": svc_name,
                        "category": _guess_category(svc_name + " " + image),
                        "type": "service",
                        "source": dc_path,
                        "confidence": 0.8,
                    })
                logger.info("GitHub: parsed %s", dc_path)
            except Exception as e:
                logger.warning("docker-compose parse error (%s): %s", dc_path, e)

    # ── ADR-078: single tree fetch, reused for compose-subdirs + manifests ───
    tree = _fetch_github_tree(owner, repo, token)

    # ── docker/*/docker-compose.yml — sub-directories from tree ──────────────
    for sub_path in _discover_github_composes(tree):
        content = _fetch_github_file(owner, repo, sub_path, token)
        if not content:
            continue
        try:
            data = yaml.safe_load(content)
            for svc_name, svc_cfg in (data.get("services") or {}).items():
                if svc_name in INTERNAL_CONTAINERS:
                    continue
                image = (svc_cfg or {}).get("image", "")
                services.append({
                    "name": svc_name,
                    "category": _guess_category(svc_name + " " + image),
                    "type": "service",
                    "source": sub_path,
                    "confidence": 0.8,
                })
            logger.info("GitHub: parsed %s", sub_path)
        except Exception as e:
            logger.warning("docker-compose parse error (%s): %s", sub_path, e)

    # ── Manifest discovery via tree API (ADR-078) ────────────────────────────
    from src.scout.signal_map import canonical, canonical_with_fallback
    manifest_services: set[str] = set()
    manifest_categories: set[str] = set()   # ADR-072
    github_llm_classified: list[dict] = []

    def _add_canonical(raw_name: str) -> None:
        c = canonical(raw_name)
        if c:
            manifest_services.add(c)
            return
        # ADR-062 + ADR-072: Gemma4 fallback — accept category even without canonical_name
        c_llm, cat_llm, llm_result = canonical_with_fallback(raw_name, use_llm=True)
        if c_llm:
            manifest_services.add(c_llm)
        if cat_llm:
            manifest_categories.add(cat_llm)
        if llm_result and (c_llm or cat_llm):
            github_llm_classified.append({**llm_result, "package_name": raw_name})

    manifest_paths = _discover_github_manifests(tree)

    # Fallback: tree unavailable or empty → probe known root-level paths so a
    # transient API error never silently drops manifest coverage to zero.
    if not manifest_paths:
        manifest_paths = [
            ("package.json",     "package.json"),
            ("requirements.txt", "requirements.txt"),
            ("pyproject.toml",   "pyproject.toml"),
            ("Pipfile",          "Pipfile"),
            ("composer.json",    "composer.json"),
            ("go.mod",           "go.mod"),
        ]
        logger.info(
            "GitHub manifest discovery: tree unavailable, root-only fallback (%d paths)",
            len(manifest_paths),
        )

    for path, name in manifest_paths:
        content = _fetch_github_file(owner, repo, path, token)
        if not content:
            continue
        _dispatch_manifest(name, content, path, services, _add_canonical)

    # ── .env.example — credential/service patterns ───────────────────────────
    content = _fetch_github_file(owner, repo, ".env.example", token)
    if content:
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key = line.split("=")[0].strip().lower()
            # known env var prefixes that signal a third-party service
            for marker, name, category in [
                ("openai",    "openai",    "ai_llm"),
                ("anthropic", "anthropic", "ai_llm"),
                ("stripe",    "stripe",    "payment"),
                ("sendgrid",  "sendgrid",  "email"),
                ("mailchimp", "mailchimp", "email"),
                ("s3",        "aws-s3",    "storage"),
                ("neo4j",     "neo4j",     "other"),
            ]:
                if marker in key:
                    services.append({
                        "name": name,
                        "category": category,
                        "type": "credential_hint",
                        "source": ".env.example",
                        "confidence": 0.4,
                    })
                    break
        logger.info("GitHub: parsed .env.example")

    logger.info(
        "GitHub scout: %d services, %d manifest paths (%d canonical, %d llm categories) in %s/%s",
        len(services), len(manifest_paths), len(manifest_services),
        len(manifest_categories), owner, repo,
    )
    return {
        "services": services,
        "service_names": sorted(manifest_services),
        "service_categories": sorted(manifest_categories),   # ADR-072
        "llm_classified": github_llm_classified,
    }


def _scout_fallback(path: str, token: str | None = None) -> dict:
    """
    Minimal scout for local paths and GitHub URLs.

    If path is a GitHub URL → fetch files via GitHub API (_scout_github).
    Otherwise → read from the local filesystem (original behavior).
    token: per-project token from _get_github_token() (ADR-033).
    """
    if path and "github.com" in path:
        if not token:
            logger.warning("No GitHub token for %s — API calls limited to public repos", path)
        # parse owner/repo, strip .git suffix and trailing slashes
        import re
        match = re.search(r"github\.com/([^/]+)/([^/\s]+?)(?:\.git)?/?$", path)
        if not match:
            logger.warning("Cannot parse GitHub URL: %s", path)
            return {"services": []}
        owner, repo = match.group(1), match.group(2)
        logger.info("GitHub URL detected: %s/%s", owner, repo)
        return _scout_github(owner, repo, token or "")

    # ── Local filesystem ──────────────────────────────────────────────────────
    import re
    import yaml

    services = []
    base = Path(path) if path and path != "." else Path.cwd()

    # docker-compose — root and one level deep, excluding irrelevant dirs
    dc_candidates = (
        list(base.glob("docker-compose.y*ml"))
        + list(base.glob("*/docker-compose.y*ml"))
        + list(base.glob("docker/*/docker-compose.y*ml"))
    )
    dc_candidates = [
        p for p in dc_candidates
        if not any(part in EXCLUDED_DIRS for part in p.parts)
    ]
    for dc_path in dc_candidates:
        try:
            data = yaml.safe_load(dc_path.read_text())
            for svc_name, svc_cfg in (data.get("services") or {}).items():
                if svc_name in INTERNAL_CONTAINERS:
                    continue
                image = (svc_cfg or {}).get("image", "")
                services.append({
                    "name": svc_name,
                    "category": _guess_category(svc_name + " " + image),
                    "type": "service",
                    "source": str(dc_path.relative_to(base)),
                    "confidence": 0.8,
                })
        except Exception as e:
            logger.warning("docker-compose parse error (%s): %s", dc_path.name, e)

    # package.json — production deps only, compliance whitelist
    pkg_path = base / "package.json"
    if pkg_path.exists():
        try:
            import json
            pkg = json.loads(pkg_path.read_text())
            deps = pkg.get("dependencies", {})
            for dep in deps:
                if _is_compliance_package(dep):
                    services.append({
                        "name": dep,
                        "category": _guess_category(dep),
                        "type": "dependency",
                        "source": "package.json",
                        "confidence": 0.6,
                    })
        except Exception as e:
            logger.warning("package.json parse error: %s", e)

    # composer.json — PHP compliance deps
    composer_path = base / "composer.json"
    if composer_path.exists():
        try:
            import json
            data = json.loads(composer_path.read_text())
            for pkg_name in data.get("require", {}):
                if pkg_name == "php":
                    continue
                short = pkg_name.split("/")[-1]
                if _is_compliance_package(short) or _is_compliance_package(pkg_name):
                    services.append({
                        "name": short,
                        "category": _guess_category(pkg_name),
                        "type": "dependency",
                        "source": "composer.json",
                        "confidence": 0.7,
                    })
        except Exception as e:
            logger.warning("composer.json parse error: %s", e)

    return {"services": services}


def _guess_category(text: str) -> str:
    text = text.lower()
    if any(k in text for k in ["stripe", "paypal", "braintree", "mollie"]):
        return "payment"
    if any(k in text for k in ["openai", "anthropic", "gemini", "mistral", "llm", "gpt",
                                "cohere", "huggingface", "replicate"]):
        return "ai_llm"
    if any(k in text for k in ["pgvector", "pinecone", "weaviate", "qdrant",
                                "chromadb", "chroma", "vector", "embedding",
                                "llama-index", "llamaindex", "langchain"]):
        return "vector_db"
    if any(k in text for k in ["mongo", "firestore", "firebase", "dynamo",
                                "cassandra", "couchdb", "redis"]):
        return "nosql_db"
    if any(k in text for k in ["analytics", "segment", "mixpanel", "amplitude",
                                "posthog"]):
        return "analytics"
    if any(k in text for k in ["sentry", "datadog", "newrelic", "monitoring",
                                "logging", "grafana"]):
        return "monitoring"
    if any(k in text for k in ["sendgrid", "mailchimp", "ses", "smtp", "resend",
                                "postmark", "twilio"]):
        return "email"
    if any(k in text for k in ["s3", "gcs", "blob", "storage"]):
        return "storage"
    if any(k in text for k in ["supabase", "neon", "planetscale", "turso"]):
        return "baas"
    if any(k in text for k in ["mysql", "postgres", "mariadb", "sqlite",
                                "rds", "aurora"]):
        return "database"
    return "other"


# ── ADR-110: Payment integration-mode (render-time signal) ──────────────────
# The three mode literals are single-sourced in the builder-common module so the
# scanner (producer, below) and the AVV/VVT/SCC builders (consumers) share one
# vocabulary — no drift across the three documents from one scan run.
from src.documents.builders.common.payment_mode import (  # noqa: E402
    PAYMENT_MODE_DELEGATED,
    PAYMENT_MODE_MERCHANT_SIDE,
    PAYMENT_MODE_UNKNOWN,
)

PAYMENT_INTEGRATION_MODES = frozenset(
    {PAYMENT_MODE_DELEGATED, PAYMENT_MODE_MERCHANT_SIDE, PAYMENT_MODE_UNKNOWN}
)


# ADR-110 ecosystem axis: Stripe server-SDK package names as the manifest
# parsers surface them (the service-entry `name`). npm/pip/ruby → "stripe";
# composer short name (stripe/stripe-php → split("/")[-1]) → "stripe-php".
# Extend as other ecosystems produce service entries — orthogonal to the
# ADR-113 per-PSP axis (which PSP), this is the per-ecosystem axis (which manifest).
_STRIPE_SERVER_SDK_NAMES = frozenset({"stripe", "stripe-php"})


def _derive_stripe_integration_mode(services: list[dict]) -> str | None:
    """
    ADR-110: derive *how* Stripe is integrated from raw manifest service entries,
    while the full package name still exists — i.e. before the canonical
    set-collapse in ``_add_canonical`` discards the raw name and only "Stripe"
    survives.

    Reads the raw scout ``services`` list (entries carry the full ``name``, e.g.
    ``@stripe/stripe-js`` / ``@stripe/react-stripe-js`` / ``stripe``, plus their
    ``source`` manifest path).

    Returns:
        ``"delegated"``              — a Stripe client-side JS package is present
                                       (``@stripe/stripe-js`` / ``@stripe/react-stripe-js``).
                                       Card data flows browser→Stripe; the shop is
                                       not in the PCI scope.
        ``"merchant_side_possible"`` — a server SDK package is present
                                       (``stripe`` npm/pip, ``stripe-php``
                                       composer — see ``_STRIPE_SERVER_SDK_NAMES``)
                                       with no ``*-js`` frontend package.
                                       Server-side raw-PAN processing cannot be
                                       ruled out from the manifest alone.
        ``"unknown"``                — Stripe is detected, but no manifest package
                                       gives a decisive integration signal (an
                                       indirect ``stripe-*`` package, or a server
                                       SDK from an ecosystem not yet in the
                                       allowlist). Honest gap, not asserted away.
        ``None``                     — no Stripe signal at all.

    Merge rule V2b (full-stack repo, frontend + backend manifests): if a
    client-side ``*-js`` package is present anywhere, ``"delegated"`` wins over a
    parallel server ``stripe`` — the frontend token is the unambiguous signal; a
    parallel server SDK is then typically webhook handling, not raw-PAN work.

    Scope: Stripe only (ADR-110). The server-SDK match is the per-ecosystem
    allowlist ``_STRIPE_SERVER_SDK_NAMES`` (npm/pip ``stripe``, composer
    ``stripe-php``); ecosystems not yet listed fall to ``"unknown"``. This is
    the ecosystem axis (which manifest), orthogonal to the ADR-113 per-PSP axis.
    """
    has_delegated = False
    has_server_sdk = False
    has_any_stripe = False

    for svc in services:
        name = (svc.get("name") or "").lower().replace("_", "-")
        if "stripe" not in name:
            continue
        has_any_stripe = True
        if "stripe-js" in name:        # @stripe/stripe-js, @stripe/react-stripe-js
            has_delegated = True
        elif name in _STRIPE_SERVER_SDK_NAMES:  # server SDK across ecosystems
            has_server_sdk = True

    if not has_any_stripe:
        return None
    if has_delegated:                  # V2b: client token wins over parallel server SDK
        return PAYMENT_MODE_DELEGATED
    if has_server_sdk:
        return PAYMENT_MODE_MERCHANT_SIDE
    return PAYMENT_MODE_UNKNOWN


def _detect_pgvector(repo_path: str) -> bool:
    """
    Detect pgvector usage beyond package name.
    pgvector is often used as a PostgreSQL extension, not a standalone Python package.
    Scans .py, .ts, .js, .sql, .yml, .yaml, .env.example for known signals.
    """
    signals = [
        "CREATE EXTENSION IF NOT EXISTS vector",
        "CREATE EXTENSION vector",
        "from pgvector",
        "pgvector.django",
        "VectorField(",
        "match_documents",
        "match_embeddings",
        "similarity_search",
        "ankane/pgvector",
        "pgvector/pgvector",
    ]
    scan_extensions = {".py", ".ts", ".js", ".sql", ".yml", ".yaml", ".env.example"}
    try:
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            for fname in files:
                if not any(fname.endswith(e) for e in scan_extensions):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    content = open(fpath, encoding="utf-8", errors="ignore").read()
                    if any(sig in content for sig in signals):
                        return True
                except Exception:
                    continue
    except Exception:
        pass
    return False


# ── Node 2 — Graph Enrichment ──────────────────────────────────────────────────

def node_graph_enrichment(state: LexState) -> LexState:
    """
    Query Neo4j for compliance requirements based on canonical service names.
    Only receives generic seed names — never customer-specific data (ADR-001).
    """
    _update_step(state.get("run_id"), step="graph")  # ADR-068

    scout = state.get("scout_result") or {}
    service_names = scout.get("service_names", [])
    service_categories = scout.get("service_categories", [])   # ADR-072
    service_modes = scout.get("service_modes", {}) or {}        # ADR-110 transient carrier
    logger.info(
        "Graph enrichment: service_names = %s, service_categories = %s",
        service_names, service_categories,
    )

    if not service_names and not service_categories:
        logger.warning("No known services or categories for graph enrichment")
        state["graph_result"] = {
            "services": [], "docs_required": [], "doc_types": [],
            "controls": [], "risk_levels": [], "overall_risk": "minimal",
        }
        return state

    # ADR-060: pass detected UseCase type for risk override
    usecase_types_for_graph: list[str] = []
    uc_type = state.get("graph_usecase_type")
    if uc_type:
        usecase_types_for_graph.append(uc_type)

    try:
        with GraphClient() as graph:
            result = graph.get_compliance_requirements(
                service_names,
                run_id=state.get("run_id", ""),
                usecase_types=usecase_types_for_graph,
                service_categories=service_categories,  # ADR-072
            )
        state["graph_result"] = result
    except Exception as e:
        logger.error("Graph enrichment failed: %s", e)
        state.setdefault("errors", []).append(f"Graph: {e}")
        state["graph_result"] = {
            "services": [], "docs_required": [], "doc_types": [],
            "controls": [], "risk_levels": [], "overall_risk": "unknown",
            # ADR-129 PR 6 (audit K4): downstream MUST NOT render empty compliance
            # docs as 'complete' — the architect checks this flag and fails the run.
            "_graph_failed": True,
        }

    # ADR-110: attach the transient integration_mode onto the matching graph
    # service(s) so all three doc builders read the same render-time signal.
    # The graph data model is untouched — this rides graph_result["services"][i]
    # only. Match is case-insensitive on the canonical service name.
    if service_modes:
        modes_by_lower = {k.lower(): v for k, v in service_modes.items()}
        for svc in state["graph_result"].get("services", []):
            carrier = modes_by_lower.get((svc.get("name") or "").lower())
            if carrier and carrier.get("integration_mode"):
                svc["integration_mode"] = carrier["integration_mode"]

    # ADR-112: write the per-run graph retrieval trace (query-layer companion to
    # the ADR-111 render logbook). Best-effort — a trace failure never blocks the
    # scan; it logs a visible warning (not a silent swallow, per the ADR-111
    # Date-bug lesson). Reads the finished graph_result + a separate read-only
    # full-node fetch; the production queries are untouched.
    try:
        from src.graph.retrieval_trace import write_retrieval_trace
        from src.graph.graph_client import GraphClient as _GC
        from pathlib import Path as _Path
        with _GC() as _gc_trace:
            _service_traces, _run_level = _gc_trace.build_retrieval_trace(
                state["graph_result"], service_names, usecase_types_for_graph,
            )
        _drafts = _Path(__file__).parents[2] / "legal" / "drafts"
        write_retrieval_trace(state.get("run_id", ""), _service_traces, _run_level, _drafts)
    except Exception as exc:
        logger.warning("ADR-112 retrieval trace failed (run %s): %s",
                       (state.get("run_id", "") or "")[:8], exc)

    return state


# ── Node 4 — Document Architect ────────────────────────────────────────────────

def node_document_architect(state: LexState) -> LexState:
    """
    Generate compliance documents locally.
    This is the only node that combines PII (from PostgreSQL) + graph knowledge.
    All output stays local — never leaves the network (ADR-001).
    """
    _update_step(state.get("run_id"), step="docgen")  # ADR-068

    if state.get("dry_run"):
        logger.info("[DRY-RUN] Skipping document generation")
        state["generated_docs"] = []
        _update_step(state.get("run_id"), status="complete", docs_generated=0)
        return state

    # ADR-129 PR 6 (audit K4): Neo4j down → failed + 0 docs. Empty compliance
    # documents delivered as 'complete' would be a USP breach — no docgen, no
    # snapshot, honest failed status instead.
    if (state.get("graph_result") or {}).get("_graph_failed"):
        logger.error("Graph unavailable — skipping document generation (run fails honestly)")
        state["generated_docs"] = []
        _update_step(
            state.get("run_id"),
            status="failed",
            error="graph_unavailable — no documents generated",
        )
        return state

    _write_scan_result(state)
    _write_measure_snapshot(state)  # ADR-127 P4.2: freeze reachable controls' defaults (before generate_all)

    try:
        from src.agents.document_architect import DocumentOrchestrator
        architect = DocumentOrchestrator()
        generated = architect.generate_all(
            graph_result=state.get("graph_result", {}),
            reasoning_result=state.get("reasoning_result", {}),
            project_name=state["project_name"],
            run_id=state["run_id"],
            risk_signals=state.get("risk_signals") or [],
        )
        # ADR scan_report: prepend plain-language summary as first document
        try:
            report_path = architect._write_scan_report(
                state=state,
                graph_result=state.get("graph_result", {}),
                reasoning_result=state.get("reasoning_result", {}),
                generated_doc_types=[d["doc_type"] for d in generated],
            )
            from src.documents.pdf_renderer import render_md_to_pdf
            report_pdf = render_md_to_pdf(report_path)
            scan_report = {
                "doc_type": "scan_report",
                "file_path": str(report_path),
                "pdf_path": str(report_pdf) if report_pdf else None,
                "version": 1,
                "status": "draft",
            }
            generated = [scan_report] + generated
            logger.info("Scan report generated — prepended to delivery queue")
        except Exception as e:
            logger.warning("Scan report generation failed (non-fatal): %s", e)

        state["generated_docs"] = generated
        logger.info("Generated %d documents", len(generated))
    except Exception as e:
        # Launch-Gate row 16 (audit K3): a docgen crash must NOT end the run
        # 'complete' with 0 docs — same honest-failed shape as the
        # graph-unavailable branch above. Short product text on the status
        # page (row 51 discipline); the raw error stays in the server log.
        logger.error("Document generation failed: %s", e)
        state.setdefault("errors", []).append(f"Documents: {e}")
        state["generated_docs"] = []
        _update_step(
            state.get("run_id"),
            status="failed",
            error="document generation failed — no documents produced (see logs)",
        )
        return state

    if not state.get("generated_docs"):
        # Silent-empty guard: a healthy non-dry run always renders documents;
        # zero without an exception is a broken pipeline, not a result.
        _update_step(
            state.get("run_id"),
            status="failed",
            error="document generation produced 0 documents (see logs)",
        )
        return state

    # ADR-068: scan is effectively done once docs are produced.
    # Notify-node runs afterwards but is log-only.
    _update_step(
        state.get("run_id"),
        status="complete",
        docs_generated=len(state.get("generated_docs") or []),
    )

    return state


# ── Node 4b — Document Validator ──────────────────────────────────────────────

def node_document_validator(state: LexState) -> dict:
    """
    Node 4b — Document Validator.
    Checks generated documents against graph specification (required_sections,
    required_project_config_fields). No LLM calls — purely deterministic.
    Returns partial dict (LangGraph best practice). ADR-018 Phase 1.
    """
    docs = state.get("generated_docs") or []
    if not docs or state.get("dry_run"):
        return {"validation_result": []}

    try:
        from src.agents.document_validator import DocumentValidator
        results = DocumentValidator().validate_all(docs, state["project_name"])
        scores  = [r["completeness_score"] for r in results]
        avg     = sum(scores) / len(scores) if scores else 0
        logger.info("Validation: %d docs, avg_score=%.2f", len(results), avg)
        return {"validation_result": results}
    except Exception as e:
        logger.error("Validation failed: %s", e)
        # ADR-129 PR 5 (audit K5): this is the only partial-returning node — a bare
        # ["Validator: …"] would OVERWRITE the errors accumulated by earlier nodes
        # (LastValue channel). Merge explicitly; no operator.add reducer (the other
        # nodes return the full mutated state — a reducer would duplicate the list).
        return {"validation_result": [], "errors": state.get("errors", []) + [f"Validator: {e}"]}


# ── Node 5 — Notify ────────────────────────────────────────────────────────────

def node_notify(state: LexState) -> LexState:
    """
    Notify node — intentionally minimal, log-only.
    Telegram delivery removed 2026-07-12 (retired chat-UI layer); documents
    are served by the /docs page. A CI/CD mode would notify via a webhook
    abstraction from approve_api (ADR-042), not from this node.
    """
    docs = state.get("generated_docs") or []
    logger.info(
        "Notify: %d document(s) ready for delivery | run_id=%s",
        len(docs), state.get("run_id", ""),
    )
    state["notification_sent"] = len(docs) > 0

    try:
        from src.utils.scan_logger import log_scan_complete
        graph = state.get("graph_result") or {}
        log_scan_complete(
            run_id=state.get("run_id", ""),
            signals_count=len(state.get("risk_signals") or []),
            dsfa=any(
                s.get("signal_type") == "dsfa_trigger"
                for s in (state.get("risk_signals") or [])
            ),
            risk=graph.get("overall_risk", "unknown"),
            doc_types=graph.get("doc_types", []),
        )
    except Exception:
        pass

    return state


def _format_summary(state: LexState) -> str:
    graph    = state.get("graph_result") or {}
    reasoning = state.get("reasoning_result") or {}
    docs     = state.get("generated_docs") or []
    errors   = state.get("errors") or []

    risk     = graph.get("overall_risk", "unknown").upper()
    doc_types = graph.get("doc_types", [])
    actions  = reasoning.get("priority_actions", [])
    summary  = reasoning.get("summary", "")

    lines = [
        f"⚖️  Lex-Orchestra — Scan: {state['project_name']}",
        f"Risk Level: {risk}",
        "",
    ]
    if summary:
        lines += [summary, ""]
    if doc_types:
        lines.append("📋 Erforderliche Dokumente: " + ", ".join(doc_types))
    if actions:
        lines.append("⚠️  Prioritäts-Maßnahmen:")
        lines += [f"  {i+1}. {a}" for i, a in enumerate(actions)]
    if docs:
        lines.append("📁 Generierte Entwürfe:")
        lines += [f"  • {d['doc_type'] if isinstance(d, dict) else d}" for d in docs]
    validation = state.get("validation_result") or []
    if validation:
        from src.agents.document_validator import DocumentValidator
        val_summary = DocumentValidator().format_telegram_summary(validation)
        if val_summary:
            lines += ["", "📊 Dokument-Qualität:", val_summary]

    # Security findings
    security = state.get("security_findings") or []
    if security:
        critical = [f for f in security if f["severity"] == "CRITICAL"]
        high     = [f for f in security if f["severity"] == "HIGH"]
        lines.append(f"\n🔐 Security Findings: {len(security)} total")
        if critical:
            lines.append("  🔴 CRITICAL (%d): %s" % (
                len(critical),
                " | ".join(f["description"] for f in critical[:2]),
            ))
        if high:
            lines.append("  🟠 HIGH (%d): %s" % (
                len(high),
                " | ".join(f["description"] for f in high[:2]),
            ))

    # ADR-027 — risk signals summary
    risk_signals = state.get("risk_signals") or []
    if risk_signals:
        top = sorted(risk_signals, key=lambda s: s["confidence"], reverse=True)[:3]
        lines.append("\n🔍 Erkannte Signale (Schicht 1):")
        for s in top:
            lines.append(f"  • {s['signal_type']} ({s['confidence']:.0%})")

    # Deployment signals
    deployment = state.get("deployment_signals") or []
    if deployment:
        hints = list({d["usecase_hint"] for d in deployment})
        lines.append(f"\n🤖 KI-Deployment erkannt: {', '.join(hints)}")
        lines.append("→ `/verify` um EU AI Act Klassifizierung zu bestätigen")

    # Hint: AI services detected but no ai_usecase_type configured
    services = (state.get("graph_result") or {}).get("services", [])
    has_ai = any(s.get("category") == "ai_llm" for s in services)
    if has_ai:
        try:
            from src.agents.document_architect import DocumentOrchestrator
            config = DocumentOrchestrator()._load_project_config(state["project_name"])
        except Exception:
            config = {}
        if not config.get("ai_usecase_type"):
            lines.append("\n💡 Tipp: KI-Dienste erkannt aber kein Use Case konfiguriert.")
            lines.append("→ /config ai_usecase_type ai_assistant_general")
            lines.append("  Optionen: ai_assistant_general | ai_content_generator | customer_service_chatbot")

    if errors:
        lines.append("❌ Fehler: " + "; ".join(errors))

    return "\n".join(lines)


# ── Workflow Assembly ──────────────────────────────────────────────────────────

def _node_guard(name: str, fn):
    """ADR-129 PR 4 (audit K3): make a node crash leave an honest scan status.

    Wraps a node: on exception, best-effort PATCH status='failed' with node name
    + cause, then RE-RAISES — LangGraph must still see the run as errored. The
    guard only keeps the scan_results row truthful; it never swallows errors.
    """
    @functools.wraps(fn)
    def wrapped(state):
        try:
            return fn(state)
        except Exception as e:
            _update_step(
                state.get("run_id") if isinstance(state, dict) else None,
                status="failed",
                error=f"{name}: {e}",
            )
            raise
    return wrapped


def build_workflow(use_checkpointer: bool = False):
    """Build and compile the LangGraph workflow.

    use_checkpointer=False by default: LangGraph Server (langgraph dev --inmem)
    manages its own state store. Pass True only for CLI runs where PostgreSQL
    checkpointing is needed.
    """
    workflow = StateGraph(LexState)

    workflow.add_node("scout",     _node_guard("scout", node_scout))
    workflow.add_node("graph",     _node_guard("graph", node_graph_enrichment))
    workflow.add_node("documents", _node_guard("documents", node_document_architect))
    workflow.add_node("validator", _node_guard("validator", node_document_validator))
    workflow.add_node("notify",    _node_guard("notify", node_notify))

    workflow.set_entry_point("scout")
    workflow.add_edge("scout",     "graph")
    workflow.add_edge("graph",     "documents")
    workflow.add_edge("documents", "validator")
    workflow.add_edge("validator", "notify")
    workflow.add_edge("notify",    END)

    return workflow.compile()


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lex-Orchestra Compliance Scan")
    parser.add_argument("--project",   required=True, help="Project name")
    parser.add_argument("--repo",      default=None,  help="Repo URL or local path")
    parser.add_argument("--url",       default=None,  help="Live URL to scan")
    parser.add_argument("--depth",     default="quick", choices=["quick", "full", "deep"])
    parser.add_argument("--dry-run",   action="store_true", help="No LLM calls, no DB writes")
    parser.add_argument("--no-checkpoint", action="store_true", help="Disable PostgreSQL checkpointer")
    args = parser.parse_args()

    # Add project root to Python path
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parents[2]))

    run_id = str(uuid.uuid4())
    logger.info("Starting scan | project=%s | run_id=%s", args.project, run_id)

    app = build_workflow(use_checkpointer=not args.no_checkpoint)

    initial_state: LexState = {
        "project_name":     args.project,
        "repo_url":         args.repo,
        "live_url":         args.url,
        "scan_depth":       args.depth,
        "dry_run":          args.dry_run,
        "scout_result":      None,
        "security_findings":  None,
        "deployment_signals": None,
        "graph_result":     None,
        "reasoning_result": None,
        "generated_docs":          [],
        "validation_result":       None,
        "config_requested":        False,
        "validator_retries":       0,
        "pending_telegram_message": None,
        "notification_sent":       False,
        "run_id":                  run_id,
        "errors":                  [],
    }

    config = {"configurable": {"thread_id": run_id}}

    try:
        final = app.invoke(initial_state, config=config)
        logger.info("Scan complete | errors=%d", len(final.get("errors", [])))
        if final.get("errors"):
            for err in final["errors"]:
                logger.error("  %s", err)
        sys.exit(0 if not final.get("errors") else 1)
    except Exception as e:
        logger.error("Workflow failed: %s", e)
        sys.exit(1)
