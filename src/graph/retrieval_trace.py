"""ADR-112: per-run graph retrieval trace (query-layer companion to ADR-111).

Records, per scan run and service-anchored, what each Cypher query returned from
the graph — full node content over all node types — with empties visible on two
axes: a query returning no nodes is a **graph gap**; a returned node with a null
property is a **content gap**. Together with the ADR-111 render logbook (builder
layer) this separates the three error types: graph gap vs. builder loss vs.
canonicalization miss (the last lands in PR 2).

Layer: graph-client, NOT the builders. Per-run artifact (queries run once per
run), written next to the documents in DRAFTS_DIR as `<run8>.retrieval-trace.json`.

No provenance / ADR block — the trace answers "what did the graph return", not
"is this claim sourced". Format identity is a plain `schema_version` integer
(same discipline as the ADR-111 logbook cleanup).

ADR-001: the trace dumps *all node properties*, a broader surface than the
render logbook's `source_key`-only guard. The property guard here therefore runs
on every property **value** — but, unlike the source_key guard, it must NOT trip
on a bare slash: graph property values legitimately contain slashes (legal text
"2021/914", licence "dl-de/by-2.0"). It catches real PII / code-path signals
only (emails, absolute/source paths, code file extensions). The trace carries
only graph-seed content (canonical names, control ids, law text) — never scanned
customer code or asset content, the same boundary as `log_cypher`.

PR 1 (this module + GraphClient.build_retrieval_trace) builds the query-layer
trace. PR 2 fills the `service.scanned_raw` / `mapping_status` canonicalization
front (today the `service` block carries only `name`).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TracedNode:
    """One graph node a query returned, with its full (sanitized) properties.

    ``assigned_to`` (controls only): which service — or ``category:<cat>`` label
    — the pipeline dedup attributed this control to in the document. The node is
    in this service's trace because the *graph* holds it (raw per-service query);
    ``assigned_to`` is the *dedup* truth placed beside it. ``assigned_to != the
    anchoring service`` means the control was deduped elsewhere (divergence
    named, not masked); ``None`` means it is in the graph but in no document.

    ``category`` (controls only, ADR-112 Nachtrag 2026-06-04): the concrete
    ``ServiceCategory`` this control was reached through
    (``Service-[:HAS_CATEGORY]->ServiceCategory-[:SUBJECT_TO_CONTROL]->Control``).
    Carried per-control (not as one via-string per service) so the trace stays
    robust if a service ever has n≥2 categories — a control reachable via two
    categories appears once per category. ``None`` if the service has no category.
    """

    label: str
    key: str
    properties: dict
    assigned_to: str | None = None
    category: str | None = None


@dataclass
class QueryResult:
    """What one Cypher query returned for a service (or run-level).

    An empty ``returned`` list is meaningful — it is the graph-gap axis and is
    preserved, never dropped.
    """

    query: str
    returned: list[TracedNode]
    via: str | None = None


@dataclass
class ServiceTrace:
    """All query results anchored to one detected service.

    ``service`` carries ``{"name": ...}`` in PR 1; PR 2 adds ``scanned_raw`` /
    ``canonical`` / ``mapping_status`` (the canonicalization front).
    """

    service: dict
    queries: list[QueryResult]


# ADR-112 widened ADR-001 guard for property *values*. Deliberately NOT the
# strict source_key guard (which bans any slash): property values legitimately
# carry slashes. Catch real PII / code-path signals only.
_PROPERTY_PII_PATTERN = re.compile(
    r"[\w.+-]+@[\w-]+\.[\w.-]+"          # email address
    r"|/(?:home|Users|app|src|var|etc)/"  # absolute / source path
    r"|[A-Za-z]:\\"                       # windows path
    r"|\b[\w./-]+\.(?:tsx?|jsx?|py|env)\b",  # code file path
    re.IGNORECASE,
)


def _assert_adr001_clean(label: str, key: str, properties: dict) -> None:
    """Raise if any property value looks like PII or a code/file path.

    Runs on values (ADR-112 widened surface), not just keys — but tolerant of
    slashes in legitimate graph content (legal text, licences).
    """
    for prop_key, value in properties.items():
        if isinstance(value, str) and _PROPERTY_PII_PATTERN.search(value):
            raise ValueError(
                f"ADR-001 violation: {label}{{{key}}}.{prop_key} value looks like "
                f"PII / code path: {value!r}"
            )


def write_retrieval_trace(
    run_id: str,
    service_traces: list[ServiceTrace],
    run_level_queries: list[QueryResult],
    drafts_dir: Path,
) -> Path:
    """Serialize the retrieval trace to ``<run8>.retrieval-trace.json``.

    One artifact per run, next to the documents in ``drafts_dir``. Runs the
    ADR-001 property guard on every traced node before writing.
    """
    for st in service_traces:
        for q in st.queries:
            for node in q.returned:
                _assert_adr001_clean(node.label, node.key, node.properties)
    for q in run_level_queries:
        for node in q.returned:
            _assert_adr001_clean(node.label, node.key, node.properties)

    payload = {
        "schema_version": 1,
        "run_id": run_id,
        "service_traces": [_service_trace_to_dict(st) for st in service_traces],
        "run_level_queries": [_query_result_to_dict(q) for q in run_level_queries],
    }

    drafts_dir.mkdir(parents=True, exist_ok=True)
    out_path = drafts_dir / f"{run_id[:8]}.retrieval-trace.json"
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return out_path


def _service_trace_to_dict(st: ServiceTrace) -> dict:
    return {
        "service": st.service,
        "queries": [_query_result_to_dict(q) for q in st.queries],
    }


def _query_result_to_dict(q: QueryResult) -> dict:
    d: dict = {
        "query": q.query,
        "returned": [_traced_node_to_dict(n) for n in q.returned],
    }
    if q.via is not None:
        d["via"] = q.via
    return d


def _traced_node_to_dict(n: TracedNode) -> dict:
    d: dict = {"label": n.label, "key": n.key, "properties": n.properties}
    if n.assigned_to is not None:
        d["assigned_to"] = n.assigned_to
    if n.category is not None:
        d["category"] = n.category
    return d
