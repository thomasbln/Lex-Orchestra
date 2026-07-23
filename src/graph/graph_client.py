"""
Graph Client — Neo4j Compliance Queries
========================================
All queries use canonical service names from the Neo4j seed (generic, public knowledge).
Never receives customer-specific data, file paths, or credentials (ADR-001).

Usage:
    graph = GraphClient()
    result = graph.get_compliance_requirements(["Stripe", "OpenAI"])
    controls = graph.get_controls_for_framework("ISO_27001")
"""

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

logger = logging.getLogger(__name__)

NEO4J_URI      = os.getenv("NEO4J_URI")
NEO4J_USER     = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DB       = os.getenv("NEO4J_DATABASE", "neo4j")

# ADR-117: title_de/title_en are the authoritative pair. The legacy `title` property
# (c.title) is NOT in the fallback chain — it is legacy (removed in PR 4). DE always
# resolves to title_de (present on every control); EN falls back to title_de when the
# EN field is a gap/empty (documented intermediate state until ADR-079 fills EN).
TITLE_FALLBACK = {
    "de": ["title_de"],
    "en": ["title_en", "title_de"],
    "fr": ["title_fr", "title_en", "title_de"],
    "es": ["title_es", "title_en", "title_de"],
    "nl": ["title_nl", "title_en", "title_de"],
    "it": ["title_it", "title_en", "title_de"],
    "pl": ["title_pl", "title_en", "title_de"],
}


def _title_coalesce(lang: str, alias: str = "n") -> str:
    """Return a Cypher coalesce expression for the title fallback chain (ADR-117).

    `alias` is the node variable used in the query (e.g. 'c' for `(c:Control)`).
    Always ends with '' so a fully-missing title yields '' (gap), never null.
    """
    fields = TITLE_FALLBACK.get(lang, ["title_de"])
    return "coalesce(" + ", ".join(f"{alias}.{f}" for f in fields) + ", '')"


def is_ai_service(service: dict) -> bool:
    """Single source of truth for "is this service an AI system?" (ADR-110 / EU AI Act).

    A service is AI-relevant when its graph node carries ``ai_act_relevant`` OR its
    category is ``ai_llm``. This is the SAME condition the document pipeline uses to
    gate the four KI documents (see ``document_architect`` KI-doc gating) — both the
    pipeline and the ``/api/ai-services`` endpoint import this helper so the two can
    never drift on what counts as an AI service. Operates on a Service dict as
    returned by ``get_compliance_requirements()['services']`` (Q_META).
    """
    return bool(service.get("ai_act_relevant")) or service.get("category") == "ai_llm"


def resolve_control_title(control: dict, lang: str = "de") -> str:
    """Render-time control-title resolution (ADR-079 PR 1).

    The scan stores BOTH ``title_de`` and ``title_en`` on each control dict
    (no longer a single scan-time-coalesced ``title``), so one scan can render
    either language. This picks the language-specific title following
    ``TITLE_FALLBACK`` on the render side — the render-time twin of the Cypher
    ``_title_coalesce``. Returns '' when no title is present (gap), never None.
    """
    for field in TITLE_FALLBACK.get(lang, ["title_de"]):
        value = control.get(field)
        if value:
            return value
    return ""


def _classify_provenance(detected: list[str], graph_rows: list[dict]) -> dict:
    """Pure N / X / Differenz classification for the Ebene-0 box (ADR-121).

    Splits the scanned ``detected`` service names against ``graph_rows`` (one row
    per name with keys ``name`` / ``has_service_node`` / ``requires_avv`` /
    ``gdpr_adequate``) into:

    - ``processors`` (X): has a Service node AND reaches a ServiceCategory with
      ``requires_avv=true`` — services that process personal data.
    - ``third_country`` (X_drittland): the subset of X with ``gdpr_adequate=false``
      — the SCC trigger (NOT the AVV X).
    - ``tooling`` (Differenz = N−X by the memo's definition): no Service node —
      development tooling without standalone data processing.
    - ``other_services``: has a node but ``requires_avv`` is not true — neither a
      processor nor tooling. Surfaced separately so nothing is silently dropped
      (``n == len(processors) + len(tooling) + len(other_services)``).

    Pure function: no DB access, so the classification logic is unit-testable
    without Supabase or Neo4j.
    """
    by_name = {r.get("name"): r for r in graph_rows}
    processors: list[str] = []
    third_country: list[str] = []
    tooling: list[str] = []
    other: list[str] = []
    for nm in detected:
        row = by_name.get(nm, {})
        if not row.get("has_service_node"):
            tooling.append(nm)
        elif row.get("requires_avv"):
            processors.append(nm)
            if row.get("gdpr_adequate") is False:
                third_country.append(nm)
        else:
            other.append(nm)
    return {
        "n": len(detected),
        "detected": list(detected),
        "x": len(processors),
        "processors": processors,
        "x_drittland": len(third_country),
        "third_country": third_country,
        "differenz": len(tooling),
        "tooling": tooling,
        "other_services": other,
    }


def _embed_names(query: str, names: list[str]) -> str:
    """Replace $names parameter with literal list for copy-to-browser logging.
    ADR-001: service_names are canonical seed names (public knowledge), not PII.
    """
    literal = "[" + ", ".join(f'"{n}"' for n in names) + "]"
    return query.replace("$names", literal)


class GraphClient:

    def __init__(self):
        if not all([NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD]):
            raise ValueError("NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD missing in .env")
        self._driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self):
        self._driver.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    # ── Ebene-0 provenance (ADR-079 PR 2c-i): two-source join ────────────────

    def _read_detected_services(self, run_id: str) -> list[str]:
        """Read the canonical service names scanned for ``run_id`` from Supabase.

        Source: scan_signals where signal_type='service_detected' (ADR-094).
        ADR-001: only canonical service names (public knowledge) leave Supabase —
        never PII. Returns [] when the DB is unavailable (graceful).
        """
        from src.graph.asset_translator import _resolve_db_url
        db_url = _resolve_db_url()
        if not db_url:
            return []
        import psycopg2
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT DISTINCT value FROM scan_signals "
                    "WHERE run_id = %s AND signal_type = 'service_detected' "
                    "AND value IS NOT NULL "
                    "ORDER BY value",
                    (run_id,),
                )
                return [r[0] for r in cur.fetchall()]

    def resolve_processing_provenance(self, run_id: str) -> dict:
        """Ebene-0 'Warum-Box' provenance — a join across TWO data sources.

        Joins the scanned service-detection signals in **Supabase** (scan_signals
        where signal_type='service_detected') against the compliance **graph**
        (Neo4j) and returns N / X / Differenz with names, so a document can show
        "N components detected, X process personal data, (N−X) are dev tooling".

        ADR-001: only canonical service names cross the Supabase↔Neo4j boundary;
        no PII is read or returned. ADR-121: this is the verified
        ``OPTIONAL MATCH (s:Service)-[:HAS_CATEGORY]->(:ServiceCategory)`` join.
        NO-CACHE (ADR-121 C1): computed per call, never persisted.

        Returns the dict shape of :func:`_classify_provenance`.
        """
        detected = self._read_detected_services(run_id)
        if not detected:
            return _classify_provenance([], [])
        q = """
UNWIND $names AS nm
OPTIONAL MATCH (s:Service {name: nm})
OPTIONAL MATCH (s)-[:HAS_CATEGORY]->(sc:ServiceCategory)
WITH nm, s, collect(sc.requires_avv) AS ra
RETURN nm                                AS name,
       (s IS NOT NULL)                   AS has_service_node,
       any(v IN ra WHERE v = true)       AS requires_avv,
       s.gdpr_adequate                   AS gdpr_adequate
""".strip()
        with self._driver.session(database=NEO4J_DB) as session:
            rows = [dict(r) for r in session.run(q, names=detected)]
        return _classify_provenance(detected, rows)

    # ── Generic query runner (used by Schema Explorer endpoints) ─────────────

    def run_query(self, cypher: str, params: dict | None = None) -> list[dict]:
        """Execute a read-only Cypher query and return rows as dicts."""
        with self._driver.session(database=NEO4J_DB) as session:
            result = session.run(cypher, **(params or {}))
            return [self._sanitize_row(dict(row)) for row in result]

    @staticmethod
    def _sanitize_row(row: dict) -> dict:
        """Convert Neo4j-specific types (Date, DateTime, Duration) to JSON-safe values."""
        for key, value in row.items():
            if isinstance(value, dict):
                row[key] = GraphClient._sanitize_row(value)
            elif hasattr(value, "iso_format"):
                row[key] = value.iso_format()
            elif isinstance(value, list):
                row[key] = [
                    GraphClient._sanitize_row(v) if isinstance(v, dict)
                    else v.iso_format() if hasattr(v, "iso_format")
                    else v
                    for v in value
                ]
        return row

    # ── Core workflow query ────────────────────────────────────────────────────

    def get_compliance_requirements(
        self,
        service_names: list[str],
        run_id: str = "",
        usecase_types: list[str] | None = None,
        service_categories: list[str] | None = None,
        lang: str = "de",
    ) -> dict:
        """
        Given a list of canonical service names (e.g. ["Stripe", "OpenAI"]),
        return all compliance requirements: required docs, laws, controls, risk levels.

        This is the main query for Node 2 (Graph Enrichment).
        service_names come from the Neo4j seed — generic, not customer-specific.
        usecase_types (ADR-060): optional list of UseCase.type values from classifier
        (e.g. ["hr_recruitment_screening"]) — overrides overall_risk when higher.
        service_categories (ADR-072): optional list of ServiceCategory names from
        Gemma4 classification (e.g. ["nosql_db", "baas"]) — resolves controls
        directly without requiring a Service node. Deduplication over
        (control_id, framework) is handled here, never in the caller.
        """
        _categories = service_categories or []
        _uc_types_early = usecase_types or []
        if not service_names and not _categories and not _uc_types_early:
            return {"services": [], "docs_required": [], "doc_types": [], "controls": [], "risk_levels": [], "overall_risk": "minimal", "active_risks": [], "usecase_risks": [], "missing_docs": []}

        # Query strings — defined as constants so the exact executed text
        # can be logged for the audit trail and copied into Neo4j Browser.
        Q_DOCS = """
UNWIND $names AS svc_name
MATCH (s:Service {name: svc_name})-[:REQUIRES]->(d:DocumentType)
OPTIONAL MATCH (d)-[:BASED_ON]->(l:Law)
OPTIONAL MATCH (s)-[:LOCATED_IN]->(c:Country)-[:REQUIRES_MECHANISM]->(t:TransferMechanism)
RETURN
    s.name          AS service,
    d.type          AS doc_type,
    d.name_de       AS doc_name_de,
    l.short         AS law,
    l.text          AS law_text,
    t.name          AS transfer_mechanism
""".strip()

        Q_CONTROLS = """
UNWIND $names AS svc_name
MATCH (s:Service {name: svc_name})
OPTIONAL MATCH (s)-[:REQUIRES_CONTROL]->(c1:Control)
OPTIONAL MATCH (s)-[:HAS_CATEGORY]->(sc)-[:SUBJECT_TO_CONTROL]->(c2:Control)
WITH s, collect(DISTINCT c1) + collect(DISTINCT c2) AS all_controls
UNWIND all_controls AS c
WITH s, c WHERE c IS NOT NULL
RETURN DISTINCT
    s.name                                       AS service,
    c.id                                         AS control_id,
    c.framework                                  AS framework,
    c.title_de                                   AS title_de,
    c.title_en                                   AS title_en,
    c.text                                       AS text,
    c.default_tom_measure                        AS default_tom_measure,
    c.default_tom_measure_en                     AS default_tom_measure_en
""".strip()

        Q_CONTROLS_BY_CATEGORY = """
UNWIND $categories AS cat_name
MATCH (sc:ServiceCategory {name: cat_name})-[:SUBJECT_TO_CONTROL]->(c:Control)
RETURN DISTINCT
    cat_name                                     AS service_category,
    c.id                                         AS control_id,
    c.framework                                  AS framework,
    c.title_de                                   AS title_de,
    c.title_en                                   AS title_en,
    c.text                                       AS text,
    c.default_tom_measure                        AS default_tom_measure,
    c.default_tom_measure_en                     AS default_tom_measure_en
""".strip()

        Q_RISK = """
UNWIND $names AS svc_name
MATCH (s:Service {name: svc_name})-[:TRIGGERS_RISK]->(r:RiskLevel)
RETURN
    s.name   AS service,
    r.level  AS level,
    r.action AS action
""".strip()

        Q_USECASE_RISK = """
UNWIND $usecase_types AS uc_type
MATCH (u:UseCase {type: uc_type})-[:CLASSIFIED_BY]->(rl:RiskLevel)
RETURN
    u.type               AS type,
    rl.level             AS risk_level,
    u.eu_ai_act_article  AS article,
    u.annex_iii_nr       AS annex_iii_nr,
    u.deployer_action    AS deployer_action,
    u.title_de           AS title_de,
    u.title_en           AS title_en
""".strip()

        Q_META = """
UNWIND $names AS svc_name
MATCH (s:Service {name: svc_name})
OPTIONAL MATCH (s)-[:LOCATED_IN]->(c:Country)
OPTIONAL MATCH (s)-[:HAS_CATEGORY]->(sc:ServiceCategory)-[stc:SUBJECT_TO_CONTROL]->()
OPTIONAL MATCH (s)-[role_edge:ACTS_AS]->(:ProcessingActivity {id: 'payment_processing'})
WITH s, c, head(collect(stc.legal_basis)) AS legal_basis, role_edge
RETURN
    s.name               AS name,
    s.category           AS category,
    s.dpa_required       AS dpa_required,
    s.ai_act_relevant    AS ai_act_relevant,
    s.gdpr_adequate      AS gdpr_adequate,
    s.dpa_url            AS dpa_url,
    s.data_categories    AS data_categories,
    s.data_categories_en AS data_categories_en,
    s.data_subjects      AS data_subjects,
    s.processing_purpose AS processing_purpose,
    s.processing_purpose_en AS processing_purpose_en,
    s.deletion_period    AS deletion_period,
    coalesce(c.name, s.country) AS country,
    legal_basis          AS legal_basis,
    s.source             AS source,
    s.license            AS license,
    s.last_verified      AS last_verified,
    role_edge.role        AS acts_as_role,
    role_edge.role_source AS acts_as_role_source,
    role_edge.role_source_en AS acts_as_role_source_en
""".strip()

        # ADR-079 PR 1: control titles are language-neutral at scan time.
        # Q_CONTROLS / Q_CONTROLS_BY_CATEGORY return BOTH c.title_de and
        # c.title_en; the render layer resolves the language per-document
        # (resolve_control_title). The scan no longer coalesces, so `lang`
        # no longer affects the stored control dict — one scan, either language.

        with self._driver.session(database=NEO4J_DB) as session:
            # Required documents + laws
            docs_result = session.run(Q_DOCS, names=service_names)

            docs = []
            doc_types_seen = set()
            for row in docs_result:
                dt = row["doc_type"]
                docs.append({
                    "service":            row["service"],
                    "doc_type":           dt,
                    "doc_name_de":        row["doc_name_de"],
                    "law":                row["law"],
                    "law_text":           row["law_text"],
                    "transfer_mechanism": row["transfer_mechanism"],
                })
                doc_types_seen.add(dt)

            # Security controls — Service-Node path (Q_CONTROLS) + ServiceCategory
            # path (Q_CONTROLS_BY_CATEGORY, ADR-072). Deduplication over
            # (control_id, framework) so TOM/AVV do not render duplicate sections.
            controls: list[dict] = []
            _seen_controls: set[tuple[str, str]] = set()

            def _add_control(service_label: str, row: dict) -> None:
                key = (row.get("control_id") or "", row.get("framework") or "")
                if not key[0] or key in _seen_controls:
                    return
                _seen_controls.add(key)
                controls.append({
                    "service":             service_label,
                    "control_id":          row["control_id"],
                    "framework":           row["framework"],
                    # ADR-079 PR 1: carry both languages; render resolves via
                    # resolve_control_title(c, lang). No scan-time 'title'.
                    "title_de":            row["title_de"],
                    "title_en":            row["title_en"],
                    "text":                row["text"],
                    "default_tom_measure": row["default_tom_measure"],
                    # ADR-127 P4.2: carry EN measure for the per-lang snapshot.
                    "default_tom_measure_en": row["default_tom_measure_en"],
                })

            if service_names:
                for row in session.run(Q_CONTROLS, names=service_names):
                    _add_control(row["service"], row)

            if _categories:
                for row in session.run(Q_CONTROLS_BY_CATEGORY, categories=_categories):
                    _add_control(f"category:{row['service_category']}", row)

            # Risk levels (EU AI Act)
            risk_result = session.run(Q_RISK, names=service_names)

            risk_levels = [
                {"service": row["service"], "level": row["level"], "action": row["action"]}
                for row in risk_result
            ]

            # Service metadata
            meta_result = session.run(Q_META, names=service_names)

            services_meta = [dict(row) for row in meta_result]

            # UseCase risk levels (ADR-060)
            _uc_types = usecase_types or []
            if _uc_types:
                uc_risk_result = session.run(Q_USECASE_RISK, usecase_types=_uc_types)
                usecase_risks = [dict(r) for r in uc_risk_result]
            else:
                usecase_risks = []

        # Highest risk level across all services.
        # gpai is intentionally excluded — it is a provider-side obligation
        # (OpenAI, Anthropic as model providers), not the deployer's.
        DEPLOYER_RISK_PRIORITY = {"unacceptable": 4, "high": 3, "limited": 2, "minimal": 1}
        overall_risk = "minimal"
        for r in risk_levels:
            lvl = (r["level"] or "").lower()
            if lvl == "gpai":
                continue
            if DEPLOYER_RISK_PRIORITY.get(lvl, 0) > DEPLOYER_RISK_PRIORITY.get(overall_risk, 0):
                overall_risk = lvl

        # ADR-100 §4.3: UseCase risk levels via CLASSIFIED_BY traversal feed overall_risk.
        # Source of truth is the graph edge, not u.risk_level property.
        for uc in usecase_risks:
            lvl = (uc.get("risk_level") or "").lower()
            if DEPLOYER_RISK_PRIORITY.get(lvl, 0) > DEPLOYER_RISK_PRIORITY.get(overall_risk, 0):
                overall_risk = lvl

        # Detect active risks from service category combinations.
        # ADR-072: include categories from LLM classification so pure-category
        # sub-processors (no Service node) still trigger risk heuristics.
        found_categories = {s.get("category") for s in services_meta}
        found_categories.update(_categories)
        active_risks = []

        has_llm        = "ai_llm" in found_categories
        has_vector     = "vector_db" in found_categories
        has_db         = bool(found_categories & {"baas", "database", "storage",
                                                  "nosql_db", "vector_db"})
        has_monitoring = bool(found_categories & {"monitoring", "logging"})

        if has_llm and has_vector:
            active_risks.append("RAG_OVER_PII")

        if has_llm and has_db and not has_vector:
            active_risks.append("PII_IN_LLM_CONTEXT")

        if has_llm and has_monitoring:
            active_risks.append("PII_IN_LOGS")

        # LLM Observability tools that satisfy EU AI Act Art. 12 audit trail.
        # Sentry/Datadog are error trackers — they do NOT satisfy Art. 12.
        LLM_OBSERVABILITY_TOOLS = {
            "langfuse",         # LLM Observability — DE, self-hostable
            "helicone",         # LLM Observability (USA)
            "phoenix-arize",    # LLM Observability
            "traceloop",        # LLM Observability
            "opentelemetry",    # only if LLM instrumentation configured
        }
        found_names = {(s.get("name") or "").lower() for s in services_meta}
        has_llm_observability = bool(found_names & LLM_OBSERVABILITY_TOOLS)

        if has_llm and not has_llm_observability:
            active_risks.append("NO_AI_AUDIT_TRAIL")

        logger.info(
            "Graph enrichment: %d services, %d docs, %d controls, risk=%s, active_risks=%s",
            len(services_meta), len(doc_types_seen), len(controls), overall_risk, active_risks
        )

        # Log Cypher event for audit trail (ADR-045)
        if run_id:
            try:
                from src.utils.scan_logger import log_cypher
                log_cypher(
                    run_id=run_id,
                    query_name="get_compliance_requirements",
                    cypher_query=_embed_names(Q_DOCS, service_names),
                    params_keys=["names"],
                    result_count=len(docs),
                    cypher_queries=[
                        {"label": "docs",     "cypher": _embed_names(Q_DOCS,     service_names), "result_count": len(docs)},
                        {"label": "controls", "cypher": _embed_names(Q_CONTROLS, service_names), "result_count": len(controls)},
                        {"label": "controls_by_category", "cypher": Q_CONTROLS_BY_CATEGORY.replace("$categories", str(_categories)), "result_count": sum(1 for c in controls if str(c.get("service", "")).startswith("category:"))},
                        {"label": "risk",     "cypher": _embed_names(Q_RISK,     service_names), "result_count": len(risk_levels)},
                        {"label": "meta",     "cypher": _embed_names(Q_META,     service_names), "result_count": len(services_meta)},
                        {"label": "usecase_risk", "cypher": Q_USECASE_RISK.replace("$usecase_types", str(_uc_types)), "result_count": len(usecase_risks)},
                    ],
                )
            except Exception:
                pass  # non-fatal

            # Log what Neo4j returned (ADR-045 trust chain)
            try:
                from src.utils.scan_logger import log_cypher_result
                log_cypher_result(
                    run_id=run_id,
                    query_name="get_compliance_requirements",
                    doc_types=list(doc_types_seen),
                    controls_count=len(controls),
                    risk_level=overall_risk,
                    services_matched=[s.get("name", "") for s in services_meta if s.get("name")],
                    active_risks=active_risks,
                )
            except Exception:
                pass

        return {
            "services":       services_meta,
            "docs_required":  docs,
            "doc_types":      list(doc_types_seen),
            "controls":       controls,
            "risk_levels":    risk_levels,
            "overall_risk":   overall_risk,
            "active_risks":   active_risks,
            "usecase_risks":  usecase_risks,
        }

    # ── ADR-112: per-run graph retrieval trace ──────────────────────────────────

    # Label → natural-key property for the full-node read. Fixed vocabulary
    # (not user input), so it is safe to interpolate the label into the MATCH.
    _TRACE_KEY_PROP = {
        "Service":      "name",
        "Control":      "id",
        "Law":          "short",
        "DocumentType": "type",
        "RiskLevel":    "level",
        "UseCase":      "type",
    }

    def build_retrieval_trace(
        self,
        result: dict,
        service_names: list[str],
        usecase_types: list[str] | None = None,
    ):
        """ADR-112: build the query-layer retrieval trace from a finished
        ``get_compliance_requirements`` result.

        Faithful by construction: the assembled lists in ``result`` (services,
        docs_required, controls, risk_levels, usecase_risks) *are* what the
        production queries returned — this method reads them, never re-runs the
        production queries, and adds full node properties via a separate
        read-only ``n {.*}`` fetch (ADR-112 Task 1.0; production RETURN clauses
        untouched). Empties are preserved as ``returned: []`` so a graph gap is a
        visible row. Returns ``(service_traces, run_level_queries)``.
        """
        from src.graph.retrieval_trace import QueryResult, ServiceTrace, TracedNode

        services_meta = result.get("services", [])
        docs = result.get("docs_required", [])
        controls = result.get("controls", [])
        risk_levels = result.get("risk_levels", [])
        usecase_risks = result.get("usecase_risks", [])

        with self._driver.session(database=NEO4J_DB) as session:

            def full(label: str, key: str) -> TracedNode:
                key_prop = self._TRACE_KEY_PROP[label]
                rec = session.run(
                    f"MATCH (n:{label} {{{key_prop}: $v}}) RETURN n {{.*}} AS props",
                    v=key,
                ).single()
                props = self._sanitize_row(dict(rec["props"])) if rec else {}
                return TracedNode(label=label, key=str(key), properties=props)

            # Q_CONTROLS dedup truth: which service the pipeline attributed each
            # control to in the document (_add_control dedups globally over
            # (control_id, framework); first claimer wins). Read it to annotate
            # the raw per-service graph controls — reading-of-truth, NOT
            # re-running the dedup logic.
            assigned_lookup = {
                (c.get("control_id"), c.get("framework")): c.get("service")
                for c in controls
            }

            def raw_controls(service_name: str) -> list[TracedNode]:
                """ADR-112 PR1-fix: controls the GRAPH holds for this service,
                queried raw (dedup-free), each annotated with assigned_to (the
                dedup truth). Avoids the false graph-gap from reading the
                post-dedup assembled list — Stripe's controls all overlap with
                services processed earlier, so reading the deduped list showed 0."""
                nodes: list[TracedNode] = []
                for rec in session.run(
                    "MATCH (s:Service {name: $name})-[:HAS_CATEGORY]->(sc:ServiceCategory)"
                    "-[:SUBJECT_TO_CONTROL]->(ctrl:Control) "
                    "RETURN DISTINCT ctrl {.*} AS props, sc.name AS category",
                    name=service_name,
                ):
                    props = self._sanitize_row(dict(rec["props"]))
                    nodes.append(TracedNode(
                        label="Control",
                        key=str(props.get("id")),
                        properties=props,
                        assigned_to=assigned_lookup.get((props.get("id"), props.get("framework"))),
                        category=rec.get("category"),
                    ))
                return nodes

            # ADR-112 PR2 — the canonicalization-miss axis: iterate ALL scanned
            # canonicals (service_names = the final scout union), not just the
            # graph-matched ones. A scanned service with no graph match is a
            # visible `no_graph_node` row, not silently absent. read-of-truth:
            # service_names vs. graph-matched (services_meta), both final at this
            # point. scanned_raw / `collapsed` is deferred to PR3 (the raw->canonical
            # map has no single-source-of-truth — see the plan).
            matched_by_name = {s.get("name") for s in services_meta if s.get("name")}
            all_names = list(dict.fromkeys(list(service_names) + list(matched_by_name)))

            service_traces: list[ServiceTrace] = []
            for name in all_names:
                if not name:
                    continue
                matched = name in matched_by_name
                service_block = {
                    "name": name,
                    "mapping_status": "matched" if matched else "no_graph_node",
                }
                if not matched:
                    # no graph node → no query ran; visible row with empty queries
                    service_traces.append(ServiceTrace(service=service_block, queries=[]))
                    continue

                queries: list[QueryResult] = []

                # Q_META — the Service node itself
                queries.append(QueryResult("Q_META", [full("Service", name)]))

                # Q_DOCS — DocumentType + Law nodes required by this service
                doc_nodes: list[TracedNode] = []
                seen: set[tuple[str, str]] = set()
                for d in docs:
                    if d.get("service") != name:
                        continue
                    dt = d.get("doc_type")
                    if dt and ("DocumentType", dt) not in seen:
                        seen.add(("DocumentType", dt))
                        doc_nodes.append(full("DocumentType", dt))
                    law = d.get("law")
                    if law and ("Law", law) not in seen:
                        seen.add(("Law", law))
                        doc_nodes.append(full("Law", law))
                queries.append(QueryResult("Q_DOCS", doc_nodes))

                # Q_CONTROLS — controls the graph holds for this service, queried
                # raw (dedup-free) + annotated with the dedup's assigned_to.
                queries.append(QueryResult(
                    "Q_CONTROLS", raw_controls(name),
                    via="Service-[:HAS_CATEGORY]->ServiceCategory-[:SUBJECT_TO_CONTROL]->Control",
                ))

                # Q_RISK — RiskLevel nodes for this service
                risk_nodes = [
                    full("RiskLevel", r["level"])
                    for r in risk_levels
                    if r.get("service") == name and r.get("level")
                ]
                queries.append(QueryResult("Q_RISK", risk_nodes))

                service_traces.append(ServiceTrace(service=service_block, queries=queries))

            # Run-level queries — not cleanly anchored to a single service.
            run_level: list[QueryResult] = []

            # Q_CONTROLS_BY_CATEGORY — ONLY ADR-072 orphan-category controls
            # (categories with no Service node; service label "category:<cat>").
            # A category that HAS a Service node resolves via the per-service
            # path above, NOT here — so this is empty for runs whose categories
            # all map to real Service nodes (e.g. velstore: payment→Stripe).
            # NOTE: still reads the assembled (post-dedup) `controls` list, unlike
            # the per-service raw read — the same single-source question folds into
            # ADR-114; unmanifested here because the orphan subset is empty.
            cat_nodes = [
                full("Control", c["control_id"])
                for c in controls
                if str(c.get("service", "")).startswith("category:") and c.get("control_id")
            ]
            run_level.append(QueryResult(
                "Q_CONTROLS_BY_CATEGORY", cat_nodes,
                # via names the orphan scope so it is NOT mistaken for the
                # per-service path (which prefixes Service-[:HAS_CATEGORY]->).
                via="ServiceCategory[ADR-072 orphan, no Service node]-[:SUBJECT_TO_CONTROL]->Control",
            ))

            # Q_USECASE_RISK — UseCase + RiskLevel nodes (deployer risk classification)
            uc_nodes: list[TracedNode] = []
            seen_uc: set[tuple[str, str]] = set()
            for uc in usecase_risks:
                uc_type = uc.get("type")
                if uc_type and ("UseCase", uc_type) not in seen_uc:
                    seen_uc.add(("UseCase", uc_type))
                    uc_nodes.append(full("UseCase", uc_type))
                lvl = uc.get("risk_level")
                if lvl and ("RiskLevel", lvl) not in seen_uc:
                    seen_uc.add(("RiskLevel", lvl))
                    uc_nodes.append(full("RiskLevel", lvl))
            run_level.append(QueryResult("Q_USECASE_RISK", uc_nodes))

        return service_traces, run_level

    def get_upcoming_deadlines(self, days: int = 90) -> list[dict]:
        """
        Return Law nodes whose applies_from falls within the next N days.
        Used by Legal News Scanner and Telegram /deadlines command.
        """
        import datetime
        with self._driver.session(database=NEO4J_DB) as session:
            result = session.run("""
                MATCH (l:Law)
                WHERE l.applies_from IS NOT NULL
                  AND toString(l.applies_from) >= toString(date())
                  AND toString(l.applies_from) <= toString(date() + duration({days: $days}))
                RETURN l.name         AS name,
                       l.article      AS article,
                       l.title        AS title,
                       l.applies_from AS applies_from,
                       l.jurisdictions AS jurisdictions,
                       l.confidence   AS confidence
                ORDER BY toString(l.applies_from)
            """, days=days)
            rows = list(result)

        today = datetime.date.today()
        return [
            {
                "name":         r["name"],
                "article":      r["article"],
                "title":        r["title"],
                "applies_from": str(r["applies_from"]),
                "jurisdictions": r["jurisdictions"] or [],
                "confidence":   r["confidence"],
                "days_until":   (
                    datetime.date.fromisoformat(str(r["applies_from"])) - today
                ).days,
            }
            for r in rows
        ]

    def get_compliance_requirements_for_jurisdiction(
        self,
        service_names: list[str],
        jurisdiction: str = "DE",
    ) -> dict:
        """
        Filter compliance requirements by jurisdiction.
        Stub — returns full requirements filtered by jurisdictions property.
        Full implementation in Phase 2 (multi-jurisdiction support).
        """
        full = self.get_compliance_requirements(service_names)

        # DE deployments accept DE + EU + global; others accept jurisdiction + global
        accepted = {"DE", "EU", "global"} if jurisdiction == "DE" else {jurisdiction, "global"}

        filtered_laws = [
            law for law in full.get("laws", [])
            if any(j in accepted for j in (law.get("jurisdictions") or []))
        ]
        full["laws"] = filtered_laws
        full["jurisdiction"] = jurisdiction
        return full

    # ── Full-text search (ADR-093) ─────────────────────────────────────────────

    def search_controls_by_keyword(self, term: str, limit: int = 8) -> list[dict]:
        """BM25 full-text search on Controls via 'control_text' index.
        Index must exist — created by _ensure_fulltext_indexes() in assistant.py.
        """
        with self._driver.session(database=NEO4J_DB) as session:
            result = session.run(
                """
                CALL db.index.fulltext.queryNodes('control_text', $term)
                YIELD node, score
                RETURN
                    node.id                                        AS id,
                    node.framework                                 AS framework,
                    coalesce(node.title_de, node.title_en, '')     AS title,
                    coalesce(node.text, node.description, '')      AS text,
                    score                                          AS score,
                    node.last_verified                             AS last_verified,
                    node.version                                   AS version
                ORDER BY score DESC
                LIMIT $limit
                """,
                term=term,
                limit=limit,
            )
            return [self._sanitize_row(dict(r)) for r in result]

    def search_laws_by_keyword(self, term: str, limit: int = 3) -> list[dict]:
        """BM25 full-text search on Laws via 'law_text' index.
        Index must exist — created by _ensure_fulltext_indexes() in assistant.py.
        """
        with self._driver.session(database=NEO4J_DB) as session:
            result = session.run(
                """
                CALL db.index.fulltext.queryNodes('law_text', $term)
                YIELD node, score
                RETURN
                    node.name                                      AS law,
                    node.article                                   AS article,
                    coalesce(node.title_de, node.title, '')        AS title,
                    node.short                                     AS short,
                    coalesce(node.note_de, node.text, '')          AS text,
                    score                                          AS score,
                    node.last_verified                             AS last_verified,
                    node.version                                   AS version
                ORDER BY score DESC
                LIMIT $limit
                """,
                term=term,
                limit=limit,
            )
            return [self._sanitize_row(dict(r)) for r in result]

    def search_doctypes_by_keyword(self, term: str, limit: int = 3) -> list[dict]:
        """BM25 full-text search on DocumentType nodes via 'doctype_text' index.
        Index must exist — created by _ensure_fulltext_indexes() in assistant.py.
        """
        with self._driver.session(database=NEO4J_DB) as session:
            result = session.run(
                """
                CALL db.index.fulltext.queryNodes('doctype_text', $term)
                YIELD node, score
                RETURN
                    node.type                                      AS type,
                    node.name_de                                   AS name_de,
                    coalesce(node.description_de, '')              AS description_de,
                    score                                          AS score
                ORDER BY score DESC
                LIMIT $limit
                """,
                term=term,
                limit=limit,
            )
            return [self._sanitize_row(dict(r)) for r in result]

    # ── Supporting queries ─────────────────────────────────────────────────────

    def get_service_info(self, service_name: str) -> Optional[dict]:
        """Return full service node data for a single canonical service."""
        with self._driver.session(database=NEO4J_DB) as session:
            result = session.run(
                "MATCH (s:Service {name: $name}) RETURN s",
                name=service_name
            )
            row = result.single()
            return dict(row["s"]) if row else None

    def create_service_node_from_llm(
        self,
        name: str,
        category: str,
        country: str,
        confidence: float,
        source: str = "gemma4_fallback",
    ) -> bool:
        """
        Auto-seed a Service node from Gemma4 classification (ADR-062).
        Only called when confidence >= 0.75 and no existing node found.
        Uses MERGE — idempotent (ADR-003).
        """
        try:
            with self._driver.session(database=NEO4J_DB) as session:
                session.run("""
                    MERGE (s:Service {name: $name})
                    ON CREATE SET
                        s.category        = $category,
                        s.country         = $country,
                        s.source          = $source,
                        s.confidence      = $confidence,
                        s.created_at      = datetime(),
                        s.dpa_required    = true,
                        s.gdpr_adequate   = CASE WHEN $country = 'USA' THEN false ELSE true END,
                        s.ai_act_relevant = CASE WHEN $category = 'ai_llm' THEN true ELSE false END
                    ON MATCH SET
                        s.last_seen       = datetime()
                    WITH s
                    OPTIONAL MATCH (sc:ServiceCategory {name: $category})
                    FOREACH (_ IN CASE WHEN sc IS NULL THEN [] ELSE [1] END |
                        MERGE (s)-[:HAS_CATEGORY]->(sc)
                    )
                """, name=name, category=category, country=country,
                     confidence=confidence, source=source)
            logger.info("Auto-seeded Service node: %s (category=%s, country=%s, conf=%.2f)",
                        name, category, country, confidence)
            return True
        except Exception as e:
            logger.warning("create_service_node_from_llm failed for '%s': %s", name, e)
            return False

    def get_controls_for_framework(self, framework: str, lang: str = "de") -> list[dict]:
        """Return all controls for a framework (e.g. 'ISO_27001', 'OWASP_LLM_Top10')."""
        with self._driver.session(database=NEO4J_DB) as session:
            result = session.run("""
                MATCH (c:Control {framework: $framework})
                RETURN c.id AS id, __TITLE_COALESCE__ AS title, c.text AS text
                ORDER BY c.id
            """.replace("__TITLE_COALESCE__", _title_coalesce(lang, "c")), framework=framework)
            return [dict(row) for row in result]

    def get_law_text(self, law_name: str, article: str, prop: str = "text") -> Optional[str]:
        """Fetch a property of a law article node.

        For the default ``prop="text"`` the legacy coalesce behaviour is kept
        (``note_de`` → ``text`` → ``short``) so existing text callers are unchanged.
        For any explicit ``prop`` (e.g. ``effective_date``) the requested property
        is read honestly — earlier this argument was silently ignored.
        """
        with self._driver.session(database=NEO4J_DB) as session:
            if prop == "text":
                result = session.run(
                    "MATCH (l:Law {name: $name, article: $article}) "
                    "RETURN coalesce(l.note_de, l.text, l.short, '') AS value",
                    name=law_name, article=article,
                )
            else:
                result = session.run(
                    "MATCH (l:Law {name: $name, article: $article}) "
                    "RETURN coalesce(l[$prop], '') AS value",
                    name=law_name, article=article, prop=prop,
                )
            row = result.single()
            v = row["value"] if row else None
            return v if v else None

    def get_doctype_description(self, doc_type: str, lang: str = "de") -> Optional[str]:
        """Fetch the plain-language "what is this?" intro for a DocumentType.

        Lang-aware with DE fallback: description_{lang} → description_de.
        Returns None when no description is seeded (intro box is then omitted).
        """
        with self._driver.session(database=NEO4J_DB) as session:
            result = session.run(
                "MATCH (d:DocumentType {type: $type}) "
                "RETURN coalesce(d['description_' + $lang], d.description_de, '') AS value",
                type=doc_type, lang=lang,
            )
            row = result.single()
            v = row["value"] if row else None
            return v if v else None

    def get_bsi_defaults_for_controls(self, control_ids: list[str], lang: str = "de") -> dict[str, dict]:
        """
        For a list of BSI control IDs, return their basis_requirements and description
        as default implementation hints for ToM generation.

        Returns: {control_id: {title, description, basis_requirements: [str]}}
        """
        if not control_ids:
            return {}
        with self._driver.session(database=NEO4J_DB) as session:
            result = session.run("""
                UNWIND $ids AS cid
                MATCH (c:Control {framework: "BSI_Grundschutz", id: cid})
                RETURN c.id AS id,
                       __TITLE_COALESCE__ AS title,
                       c.description AS description,
                       __BASIS_REQS__ AS basis_requirements
            """.replace("__TITLE_COALESCE__", _title_coalesce(lang, "c"))
               .replace("__BASIS_REQS__",
                        # ADR-129 PR 9/PR 11: EN pulls the official Ed.-2022-EN list
                        # when seeded, DE fallback otherwise.
                        "coalesce(c.basis_requirements_en, c.basis_requirements)"
                        if lang == "en" else "c.basis_requirements"), ids=control_ids)
            return {
                row["id"]: {
                    "title": row["title"],
                    "description": row["description"] or "",
                    "basis_requirements": row["basis_requirements"] or [],
                }
                for row in result
            }

    def get_usecases_for_risk_level(self, risk_level: str) -> list[dict]:
        """
        Return all UseCases for a given risk level.
        risk_level: "Minimal" | "Limited" | "High" | "Unacceptable"
        """
        with self._driver.session(database=NEO4J_DB) as session:
            result = session.run("""
                MATCH (u:UseCase {risk_level: $level})
                RETURN u.type AS type,
                       u.title_de AS title_de,
                       u.title_en AS title_en,
                       u.risk_level AS risk_level,
                       u.reason AS reason,
                       u.reason_en AS reason_en,
                       u.deployer_action AS deployer_action,
                       u.deployer_action_en AS deployer_action_en,
                       u.eu_ai_act_article AS article,
                       u.annex_iii_nr AS annex_iii_nr
                ORDER BY u.type
            """, level=risk_level)
            return [dict(row) for row in result]

    def get_all_usecases(self) -> list[dict]:
        """All UseCase nodes for the /ai purpose dropdown (ADR-124 Gate D).

        value = type (stable, portable), display = title_de; article from the
        authoritative eu_ai_act_article property (NOT the dead u.article duplicate).
        Includes Unacceptable (Art. 5) — the frontend surfaces them in a separate
        clearly-labelled prohibited group, never as a normal selectable purpose.
        """
        with self._driver.session(database=NEO4J_DB) as session:
            result = session.run("""
                MATCH (u:UseCase)
                RETURN u.type AS type,
                       u.title_de AS title_de,
                       u.risk_level AS risk_level,
                       u.eu_ai_act_article AS article
                ORDER BY u.risk_level, u.type
            """)
            return [dict(row) for row in result]

    def get_ai_provider_names(self) -> list[str]:
        """Curated AI provider names for the /ai 'add KI-service' picker (ADR-124 Gate F).

        Only real AI providers (ai_llm + ai_platform) — excludes payment services and
        the integration-catalog layer (category='integration', e.g. the Mistral-EU stub).
        """
        with self._driver.session(database=NEO4J_DB) as session:
            result = session.run("""
                MATCH (s:Service) WHERE s.category IN ['ai_llm', 'ai_platform']
                RETURN s.name AS name ORDER BY s.name
            """)
            return [row["name"] for row in result]

    def get_indicated_usecases(self, service_names: list[str]) -> list[dict]:
        """
        Return UseCases indicated by detected services.
        Used by Node 3 to flag potential high-risk deployment patterns.
        """
        if not service_names:
            return []
        with self._driver.session(database=NEO4J_DB) as session:
            result = session.run("""
                UNWIND $names AS svc_name
                MATCH (s:Service {name: svc_name})-[:CAN_INDICATE]->(u:UseCase)
                RETURN DISTINCT
                    u.type AS type,
                    u.title_de AS title_de,
                    u.title_en AS title_en,
                    u.risk_level AS risk_level,
                    u.reason AS reason,
                    u.reason_en AS reason_en,
                    u.deployer_action AS deployer_action,
                    u.deployer_action_en AS deployer_action_en
                ORDER BY u.risk_level, u.type
            """, names=service_names)
            return [dict(row) for row in result]

    def get_schema_summary(self) -> dict:
        """Return node/relationship counts — useful for health checks."""
        with self._driver.session(database=NEO4J_DB) as session:
            nodes = session.run(
                "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC"
            )
            rels = session.run(
                "MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count ORDER BY count DESC"
            )
            return {
                "nodes": [dict(r) for r in nodes],
                "relationships": [dict(r) for r in rels],
            }
