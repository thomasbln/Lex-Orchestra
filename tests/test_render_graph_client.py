"""Regression tests — the render GraphClient must never reach the LangGraph state.

ADR-106 PR C5 injected a live GraphClient into the caller's `graph_result` dict. In
the scan pipeline that dict IS `state["graph_result"]` (main.py passes it by
reference), so every run carried an unpicklable Bolt driver into the LangGraph
state and the end-of-run checkpoint serialization failed silently
(`Can't get local object 'BoltPool.open.<locals>.opener'`).

These tests pin the two properties that fix it:
  1. the caller's dict is never mutated (state stays serializable), and
  2. a client this layer created is closed on the success AND the failure path.
"""

import pytest

from src.agents.document_architect import DocumentOrchestrator, _render_graph_client


class FakeGraphClient:
    """Stand-in for GraphClient — records whether close() was called."""

    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


@pytest.fixture
def fake_client(monkeypatch):
    """Patch the GraphClient the helper imports, hand back the instance it builds."""
    created: list[FakeGraphClient] = []

    def _factory():
        client = FakeGraphClient()
        created.append(client)
        return client

    monkeypatch.setattr("src.graph.graph_client.GraphClient", _factory)
    return created


# ── _render_graph_client ──────────────────────────────────────────────────────

def test_caller_dict_is_not_mutated(fake_client):
    """The whole point: state["graph_result"] must not gain a Bolt driver."""
    caller = {"services": [{"name": "Stripe"}], "doc_types": ["AVV"]}

    local, owned = _render_graph_client(caller)

    assert "_graph_client" not in caller
    assert caller == {"services": [{"name": "Stripe"}], "doc_types": ["AVV"]}
    assert local is not caller
    assert owned is fake_client[0]


def test_copy_carries_the_client_for_the_builders(fake_client):
    """The builders read graph_result["_graph_client"] — the copy must supply it."""
    local, owned = _render_graph_client({"services": []})

    assert local["_graph_client"] is owned
    assert local["services"] == []


def test_caller_supplied_client_is_not_owned(fake_client):
    """A client passed in from outside belongs to the caller — we must not close it."""
    external = FakeGraphClient()

    local, owned = _render_graph_client({"_graph_client": external})

    assert owned is None, "an externally supplied client must not be adopted"
    assert local["_graph_client"] is external
    assert fake_client == [], "no second client may be created"


def test_unreachable_neo4j_yields_no_client(monkeypatch):
    """Best-effort: Neo4j down → no client, no exception (footer stays empty)."""
    def _boom():
        raise RuntimeError("neo4j unreachable")

    monkeypatch.setattr("src.graph.graph_client.GraphClient", _boom)

    local, owned = _render_graph_client({"services": []})

    assert owned is None
    assert "_graph_client" not in local


# ── generate_all() lifetime ───────────────────────────────────────────────────

def _generate_all_with(monkeypatch, body):
    """Run generate_all() with its render body replaced by `body`."""
    monkeypatch.setattr(DocumentOrchestrator, "_generate_all", body)
    caller = {"services": [], "doc_types": []}
    docs = DocumentOrchestrator().generate_all(
        graph_result=caller,
        reasoning_result={},
        project_name="rand-industries",
        run_id="00000000-0000-0000-0000-000000000000",
    )
    return caller, docs


def test_client_closed_on_success_path(monkeypatch, fake_client):
    seen: dict = {}

    def _body(self, *, graph_result, **kwargs):
        seen["graph_result"] = graph_result
        return [{"doc_type": "AVV"}]

    caller, docs = _generate_all_with(monkeypatch, _body)

    assert docs == [{"doc_type": "AVV"}]
    assert fake_client[0].closed is True
    # the body renders against the copy, the caller's dict stays clean
    assert seen["graph_result"]["_graph_client"] is fake_client[0]
    assert "_graph_client" not in caller


def test_client_closed_on_builder_error_path(monkeypatch, fake_client):
    """A builder blowing up must not leak the driver — try/finally, not a bare close."""
    def _body(self, **kwargs):
        raise RuntimeError("builder exploded")

    with pytest.raises(RuntimeError, match="builder exploded"):
        _generate_all_with(monkeypatch, _body)

    assert fake_client[0].closed is True


def test_close_failure_does_not_break_the_run(monkeypatch, fake_client):
    """A failing close() is logged, never raised — docs are already written."""
    def _body(self, **kwargs):
        return [{"doc_type": "TOM"}]

    monkeypatch.setattr(DocumentOrchestrator, "_generate_all", _body)

    class _AngryClient(FakeGraphClient):
        def close(self):
            raise RuntimeError("bolt already gone")

    monkeypatch.setattr("src.graph.graph_client.GraphClient", _AngryClient)

    docs = DocumentOrchestrator().generate_all(
        graph_result={"services": []},
        reasoning_result={},
        project_name="rand-industries",
        run_id="00000000-0000-0000-0000-000000000000",
    )

    assert docs == [{"doc_type": "TOM"}]
