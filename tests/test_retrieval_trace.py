"""Tests for the ADR-112 graph retrieval trace (PR 1).

Covers the schema + write side (pure, no DB), the widened ADR-001 property
guard, and build_retrieval_trace with a mocked Neo4j session.
"""

import json
import re

import pytest

from src.graph.graph_client import GraphClient
from src.graph.retrieval_trace import (
    QueryResult,
    ServiceTrace,
    TracedNode,
    write_retrieval_trace,
)


# -- write_retrieval_trace ----------------------------------------------------

def test_write_places_per_run_file(tmp_path):
    run_id = "5153dbcc-15db-45b0-a124-17b3e413395b"
    st = ServiceTrace(
        service={"name": "Stripe"},
        queries=[QueryResult("Q_META", [
            TracedNode("Service", "Stripe", {"category": "payment", "country": "USA"})
        ])],
    )
    out = write_retrieval_trace(run_id, [st], [], tmp_path)

    assert out.name == "5153dbcc.retrieval-trace.json"
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["run_id"] == run_id
    assert "adr" not in payload                 # no metadata pollution
    assert "provenance" not in json.dumps(payload)  # no provenance block anywhere
    assert payload["service_traces"][0]["service"] == {"name": "Stripe"}


def test_empty_query_preserved_as_graph_gap(tmp_path):
    """A query that returned nothing stays a visible row (returned: []) — the
    graph-gap axis."""
    st = ServiceTrace(
        service={"name": "Stripe"},
        queries=[QueryResult("Q_USECASE_RISK", [])],
    )
    out = write_retrieval_trace("run00001", [st], [], tmp_path)
    payload = json.loads(out.read_text(encoding="utf-8"))
    q = payload["service_traces"][0]["queries"][0]
    assert q["query"] == "Q_USECASE_RISK"
    assert q["returned"] == []                  # graph gap, not dropped


def test_null_property_visible_as_content_gap(tmp_path):
    """A returned node with a null property is preserved — the content-gap axis."""
    st = ServiceTrace(
        service={"name": "Elasticsearch"},
        queries=[QueryResult("Q_META", [
            TracedNode("Service", "Elasticsearch", {"category": "search", "data_categories": None})
        ])],
    )
    out = write_retrieval_trace("run00001", [st], [], tmp_path)
    payload = json.loads(out.read_text(encoding="utf-8"))
    props = payload["service_traces"][0]["queries"][0]["returned"][0]["properties"]
    assert props["data_categories"] is None     # content gap visible


def test_via_dropped_when_none_kept_when_set(tmp_path):
    st = ServiceTrace(service={"name": "S"}, queries=[
        QueryResult("Q_META", []),                                  # no via
        QueryResult("Q_CONTROLS", [], via="A->B->C"),               # via set
    ])
    out = write_retrieval_trace("run00001", [st], [], tmp_path)
    qs = json.loads(out.read_text(encoding="utf-8"))["service_traces"][0]["queries"]
    assert "via" not in qs[0]
    assert qs[1]["via"] == "A->B->C"


# -- ADR-001 property guard (widened to values, slash-tolerant) ---------------

@pytest.mark.parametrize("bad_value", [
    "dpo@rand-industries.example.com",   # email / PII
    "src/payments.ts",                   # code path
    "/Users/thomas/secret.env",          # absolute path
    "C:\\Users\\config.py",              # windows path
])
def test_guard_rejects_pii_or_code_path_in_property_value(tmp_path, bad_value):
    st = ServiceTrace(service={"name": "S"}, queries=[QueryResult("Q_META", [
        TracedNode("Service", "S", {"leak": bad_value})
    ])])
    with pytest.raises(ValueError, match="ADR-001"):
        write_retrieval_trace("run00001", [st], [], tmp_path)


@pytest.mark.parametrize("ok_value", [
    "EU SCC Decision 2021/914",          # legal reference with slash
    "dl-de/by-2.0",                      # licence id with slash
    "Art. 6 Abs. 1 lit. b DSGVO",        # legal text
    "Zahlungsdaten, Kreditkartendaten",  # data categories
])
def test_guard_tolerates_slashes_in_legitimate_graph_content(tmp_path, ok_value):
    """Unlike the source_key guard, property values may contain slashes — legal
    text and licences. These must NOT trip the guard."""
    st = ServiceTrace(service={"name": "S"}, queries=[QueryResult("Q_META", [
        TracedNode("Law", "Art. 6", {"text": ok_value})
    ])])
    out = write_retrieval_trace("run00001", [st], [], tmp_path)
    assert out.exists()


# -- build_retrieval_trace (mocked session) -----------------------------------

class _FakeDate:
    """Stand-in for a Neo4j temporal type — has iso_format(), not JSON-native."""
    def iso_format(self):
        return "2026-05-28"


class _FakeResult:
    """Iterable (for raw_controls) AND .single() (for full-node reads)."""
    def __init__(self, records):
        self._records = records  # list of dict-records keyed by RETURN alias "props"

    def single(self):
        return self._records[0] if self._records else None

    def __iter__(self):
        return iter(self._records)


class _FakeSession:
    def __init__(self, nodes, service_controls):
        self._nodes = nodes                      # {(label, key): props}  — full-node reads
        self._service_controls = service_controls  # {service_name: [control_props, ...]}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def run(self, cypher, v=None, name=None):
        # raw per-service controls query (ADR-112 PR1-fix)
        if "SUBJECT_TO_CONTROL" in cypher:
            ctrls = self._service_controls.get(name, [])
            # ADR-112 Nachtrag: mirror the RETURN alias `sc.name AS category`.
            # A service's category comes from its ServiceCategory; derive it from
            # the Service node when the test provides one, else None (str|None).
            cat = (self._nodes.get(("Service", name)) or {}).get("category")
            return _FakeResult([{"props": p, "category": cat} for p in ctrls])
        # full-node read: MATCH (n:LABEL {kp: $v}) RETURN n {.*} AS props
        label = re.search(r"MATCH \(n:(\w+)", cypher).group(1)
        props = self._nodes.get((label, v))
        return _FakeResult([{"props": props}] if props is not None else [])


class _FakeDriver:
    def __init__(self, nodes, service_controls):
        self._nodes = nodes
        self._service_controls = service_controls

    def session(self, database=None):
        return _FakeSession(self._nodes, self._service_controls)


def _client_with(nodes, service_controls=None):
    gc = object.__new__(GraphClient)   # bypass __init__ (no real Neo4j connection)
    gc._driver = _FakeDriver(nodes, service_controls or {})
    return gc


def test_build_trace_service_anchored_with_full_properties():
    nodes = {
        ("Service", "Stripe"): {"name": "Stripe", "category": "payment", "last_verified": _FakeDate()},
        ("DocumentType", "AVV"): {"type": "AVV", "name_de": "AVV"},
        ("Law", "Art. 28"): {"short": "Art. 28", "text": "Auftragsverarbeitung …"},
        # Control carries last_verified — a field Q_CONTROLS does NOT project,
        # so its presence proves the full-node read (not the projection).
        ("Control", "API1"): {"id": "API1", "framework": "OWASP_API_Top10", "last_verified": _FakeDate()},
    }
    result = {
        "services": [{"name": "Stripe"}],
        "docs_required": [{"service": "Stripe", "doc_type": "AVV", "law": "Art. 28"}],
        # dedup truth: API1 was kept by Stripe itself
        "controls": [{"service": "Stripe", "control_id": "API1", "framework": "OWASP_API_Top10"}],
        "risk_levels": [],          # → Q_RISK empty (graph gap)
        "usecase_risks": [],
    }
    # graph truth: Stripe's category holds API1 (raw per-service query)
    service_controls = {"Stripe": [
        {"id": "API1", "framework": "OWASP_API_Top10", "last_verified": _FakeDate()},
    ]}
    gc = _client_with(nodes, service_controls=service_controls)
    service_traces, run_level = gc.build_retrieval_trace(result, ["Stripe"], [])

    assert len(service_traces) == 1
    st = service_traces[0]
    assert st.service == {"name": "Stripe", "mapping_status": "matched"}
    by_query = {q.query: q for q in st.queries}

    # Q_META — full Service node, Neo4j date sanitized to a string at the source
    meta = by_query["Q_META"].returned[0]
    assert meta.label == "Service" and meta.key == "Stripe"
    assert meta.properties["last_verified"] == "2026-05-28"   # _sanitize_row applied

    # Q_DOCS — DocumentType + Law
    doc_keys = {(n.label, n.key) for n in by_query["Q_DOCS"].returned}
    assert doc_keys == {("DocumentType", "AVV"), ("Law", "Art. 28")}

    # Q_CONTROLS — raw per-service, full Control node incl. last_verified (proves
    # full-node read), assigned_to = self (Stripe kept its own control)
    ctrl = by_query["Q_CONTROLS"].returned[0]
    assert ctrl.key == "API1"
    assert ctrl.properties["last_verified"] == "2026-05-28"
    assert ctrl.assigned_to == "Stripe"
    assert ctrl.category == "payment"   # ADR-112 Nachtrag: concrete ServiceCategory per control
    assert by_query["Q_CONTROLS"].via and "SUBJECT_TO_CONTROL" in by_query["Q_CONTROLS"].via

    # Q_RISK — empty → graph gap, visible row
    assert by_query["Q_RISK"].returned == []

    # run-level queries always present (empties visible)
    rl = {q.query for q in run_level}
    assert rl == {"Q_CONTROLS_BY_CATEGORY", "Q_USECASE_RISK"}


def test_build_trace_controls_show_dedup_divergence_not_false_gap():
    """The PR1 fix: a service whose graph controls were deduped to ANOTHER
    service still shows them (graph truth), annotated assigned_to = that other
    service — not a false graph-gap (the Stripe-0-controls bug)."""
    result = {
        "services": [{"name": "Stripe"}],
        "docs_required": [], "risk_levels": [], "usecase_risks": [],
        # dedup truth: 8.20 + OPS.1.1 were claimed by Postmark/PostgreSQL first
        "controls": [
            {"service": "Postmark", "control_id": "8.20", "framework": "ISO_27001"},
            {"service": "PostgreSQL", "control_id": "OPS.1.1", "framework": "BSI_Grundschutz"},
        ],
    }
    # graph truth: Stripe's payment category holds both
    service_controls = {"Stripe": [
        {"id": "8.20", "framework": "ISO_27001", "title": "..."},
        {"id": "OPS.1.1", "framework": "BSI_Grundschutz", "title": "..."},
    ]}
    gc = _client_with({}, service_controls=service_controls)
    service_traces, _ = gc.build_retrieval_trace(result, ["Stripe"], [])

    q = {q.query: q for q in service_traces[0].queries}["Q_CONTROLS"]
    assert len(q.returned) == 2                 # graph truth shown, NOT 0 (no false gap)
    by_key = {n.key: n for n in q.returned}
    assert by_key["8.20"].assigned_to == "Postmark"        # deduped elsewhere — named
    assert by_key["OPS.1.1"].assigned_to == "PostgreSQL"


def test_build_trace_no_graph_node_axis_visible_row():
    """ADR-112 PR2: a scanned canonical with no graph match is a visible
    no_graph_node row with empty queries — not silently absent. Mirrors velstore
    (service_names=[Laravel, Stripe], only Stripe graph-matched)."""
    nodes = {("Service", "Stripe"): {"name": "Stripe", "category": "payment"}}
    result = {
        "services": [{"name": "Stripe"}],   # only Stripe graph-matched
        "docs_required": [], "controls": [], "risk_levels": [], "usecase_risks": [],
    }
    gc = _client_with(nodes, service_controls={"Stripe": []})
    # service_names = the full scout union: Laravel scanned but not matched
    service_traces, _ = gc.build_retrieval_trace(result, ["Laravel", "Stripe"], [])

    by_name = {st.service["name"]: st for st in service_traces}
    assert set(by_name) == {"Laravel", "Stripe"}

    laravel = by_name["Laravel"]
    assert laravel.service["mapping_status"] == "no_graph_node"
    assert laravel.queries == []                 # no node → no query ran

    stripe = by_name["Stripe"]
    assert stripe.service["mapping_status"] == "matched"
    assert {q.query for q in stripe.queries} == {"Q_META", "Q_DOCS", "Q_CONTROLS", "Q_RISK"}


def test_build_trace_all_matched_no_false_no_graph_node():
    """No scanned service is wrongly flagged no_graph_node when all match."""
    nodes = {("Service", "Stripe"): {"name": "Stripe"}}
    result = {"services": [{"name": "Stripe"}], "docs_required": [],
              "controls": [], "risk_levels": [], "usecase_risks": []}
    gc = _client_with(nodes, service_controls={"Stripe": []})
    service_traces, _ = gc.build_retrieval_trace(result, ["Stripe"], [])
    assert [st.service["mapping_status"] for st in service_traces] == ["matched"]


def test_build_trace_control_in_graph_but_no_doc_assigned_to_none():
    """A control the graph holds but that is absent from the deduped list →
    assigned_to None (in graph, in no document)."""
    result = {
        "services": [{"name": "Stripe"}],
        "docs_required": [], "controls": [], "risk_levels": [], "usecase_risks": [],
    }
    service_controls = {"Stripe": [{"id": "X.1", "framework": "ISO_27001"}]}
    gc = _client_with({}, service_controls=service_controls)
    service_traces, _ = gc.build_retrieval_trace(result, ["Stripe"], [])
    ctrl = {q.query: q for q in service_traces[0].queries}["Q_CONTROLS"].returned[0]
    assert ctrl.key == "X.1"
    assert ctrl.assigned_to is None


def test_build_trace_missing_graph_node_yields_empty_properties():
    """A node key with no matching graph node → empty properties, not a crash."""
    result = {
        "services": [{"name": "Ghost"}],
        "docs_required": [], "controls": [], "risk_levels": [], "usecase_risks": [],
    }
    gc = _client_with({})  # no nodes at all
    service_traces, _ = gc.build_retrieval_trace(result, ["Ghost"], [])
    meta = {q.query: q for q in service_traces[0].queries}["Q_META"].returned[0]
    assert meta.label == "Service" and meta.key == "Ghost"
    assert meta.properties == {}   # no node found → empty, recorded not crashed


def test_build_trace_end_to_end_through_write(tmp_path):
    nodes = {("Service", "Stripe"): {"name": "Stripe", "category": "payment"}}
    result = {
        "services": [{"name": "Stripe"}],
        "docs_required": [], "controls": [], "risk_levels": [], "usecase_risks": [],
    }
    gc = _client_with(nodes)
    service_traces, run_level = gc.build_retrieval_trace(result, ["Stripe"], [])
    out = write_retrieval_trace("5153dbcc-aaaa", service_traces, run_level, tmp_path)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["service_traces"][0]["queries"][0]["returned"][0]["properties"]["category"] == "payment"
