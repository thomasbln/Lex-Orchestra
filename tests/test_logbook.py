"""Tests for the ADR-111 provenance logbook schema + write side (PR 1).

PR 1 covers the schema (dataclasses/enums), the ADR-107 provenance extraction,
the ADR-001 guard, and the write-to-DRAFTS_DIR mechanism — without builder
section semantics (those arrive in PR 2, tested in test_logbook_builders.py).
"""

import json

import pytest

from src.documents.logbook import (
    LogbookEntry,
    ProvenanceBlock,
    SourceType,
    Status,
    extract_provenance,
    write_logbook,
)


# -- extract_provenance -------------------------------------------------------

def test_extract_provenance_stripe_service_seed_run_id_none():
    """A Stripe-shaped service dict yields source/license/last_verified;
    seed_run_id is None today (ADR-107 Rest 1, mechanism gap)."""
    node = {
        "name": "Stripe",
        "source": "ADR-075 Service-Region + SCC-Annotations (kuratiert)",
        "license": "Lex-Orchestra internal + EU SCC Decision 2021/914",
        "last_verified": "2026-05-28",
        # no seed_run_id on the node
    }
    prov = extract_provenance(node)
    assert prov.source == "ADR-075 Service-Region + SCC-Annotations (kuratiert)"
    assert prov.license == "Lex-Orchestra internal + EU SCC Decision 2021/914"
    assert prov.last_verified == "2026-05-28"
    assert prov.seed_run_id is None


def test_extract_provenance_law_without_license_records_null():
    """A Law dict without a license records license=None — the coverage gap
    (ADR-107 Rest 2) is recorded, never invented."""
    node = {"short": "Art. 28 DSGVO", "source": "EUR-Lex CELEX 32016R0679"}
    prov = extract_provenance(node)
    assert prov.source == "EUR-Lex CELEX 32016R0679"
    assert prov.license is None
    assert prov.last_verified is None
    assert prov.seed_run_id is None


def test_extract_provenance_empty_node():
    """An empty dict does not crash — every field is None."""
    prov = extract_provenance({})
    assert prov == ProvenanceBlock()


class _FakeNeo4jDate:
    """Stand-in for neo4j.time.Date — not a str, not JSON-serializable."""
    def __str__(self):
        return "2026-05-28"


def test_extract_provenance_coerces_neo4j_date_to_str():
    """Regression: Q_META returns last_verified as a Neo4j Date object, which
    is not a str and breaks json.dumps. extract_provenance must coerce it."""
    prov = extract_provenance({"last_verified": _FakeNeo4jDate(), "source": "seed"})
    assert prov.last_verified == "2026-05-28"
    assert isinstance(prov.last_verified, str)


def test_write_logbook_serializes_non_str_last_verified(tmp_path):
    """Regression for 'Object of type Date is not JSON serializable': even a raw
    non-str provenance value must not break the write (default=str safety net)."""
    from src.documents.logbook import LogbookEntry, ProvenanceBlock, SourceType, Status
    entry = LogbookEntry(
        section="AVV § 2(1) Datenkategorien",
        source_type=SourceType.GRAPH_NODE,
        source_key={"label": "Service", "name": "Stripe"},
        status=Status.SOURCED,
        provenance=ProvenanceBlock(last_verified=_FakeNeo4jDate()),
    )
    out = write_logbook("6a3e5e15-0000-4000-8000-000000000000", "AVV", [entry], tmp_path)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["entries"][0]["provenance"]["last_verified"] == "2026-05-28"


# -- write_logbook ------------------------------------------------------------

def test_write_logbook_places_file_next_to_drafts(tmp_path):
    run_id = "6a3e5e15-1234-4abc-9def-0123456789ab"
    entry = LogbookEntry(
        section="AVV § 2 Datenkategorien",
        source_type=SourceType.GRAPH_NODE,
        source_key={"label": "Service", "name": "Stripe"},
        status=Status.SOURCED,
        provenance=ProvenanceBlock(
            source="ADR-075 (kuratiert)",
            license="Lex-Orchestra internal",
            last_verified="2026-05-28",
        ),
    )
    out = write_logbook(run_id, "AVV", [entry], tmp_path)

    assert out.exists()
    assert out.name == "AVV_6a3e5e15.logbook.json"

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["run_id"] == run_id
    assert payload["doc_type"] == "AVV"
    assert payload["schema_version"] == 1     # format version, not an ADR reference
    assert "adr" not in payload                # metadata pollution removed
    assert "coverage_level" not in payload
    assert len(payload["entries"]) == 1

    e = payload["entries"][0]
    assert e["section"] == "AVV § 2 Datenkategorien"
    assert e["source_type"] == "graph_node"      # enum coerced to its string value
    assert e["status"] == "sourced"
    assert e["source_key"] == {"label": "Service", "name": "Stripe"}
    assert e["provenance"]["seed_run_id"] is None  # honest empty field
    assert "note" not in e                          # dropped when None


def test_write_logbook_empty_entries_still_writes_pipe(tmp_path):
    """PR 1: the pipe is wired even with no entries — an empty logbook is
    written to prove the mechanism."""
    run_id = "deadbeef-0000-4000-8000-000000000000"
    out = write_logbook(run_id, "VVT", [], tmp_path)
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["entries"] == []


def test_write_logbook_keeps_note_when_present(tmp_path):
    run_id = "6a3e5e15-1234-4abc-9def-0123456789ab"
    entry = LogbookEntry(
        section="AVV § 2 Datenkategorien",
        source_type=SourceType.GRAPH_NODE,
        source_key={"label": "Service", "name": "Stripe"},
        status=Status.SOURCED,
        note="integration_mode present but not applied",
    )
    out = write_logbook(run_id, "AVV", [entry], tmp_path)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["entries"][0]["note"] == "integration_mode present but not applied"


# -- ADR-001 guard ------------------------------------------------------------

@pytest.mark.parametrize("bad_value", [
    "src/payments.ts",                 # file path
    "dpo@example.com",                 # email / PII
    "@stripe/stripe-js",               # raw package specifier (@ + /)
    "C:\\Users\\thomas\\config.json",  # windows path
    "config.env",                      # config file
])
def test_write_logbook_rejects_pii_or_path_in_source_key(tmp_path, bad_value):
    run_id = "6a3e5e15-1234-4abc-9def-0123456789ab"
    entry = LogbookEntry(
        section="AVV § 2",
        source_type=SourceType.GRAPH_NODE,
        source_key={"label": "Service", "name": bad_value},
        status=Status.SOURCED,
    )
    with pytest.raises(ValueError, match="ADR-001"):
        write_logbook(run_id, "AVV", [entry], tmp_path)


@pytest.mark.parametrize("ok_value", [
    "Stripe",
    "MongoDB Atlas",
    "Art. 28 DSGVO",
    "C5-OPS-01",
])
def test_write_logbook_allows_canonical_source_keys(tmp_path, ok_value):
    run_id = "6a3e5e15-1234-4abc-9def-0123456789ab"
    entry = LogbookEntry(
        section="AVV § 2",
        source_type=SourceType.GRAPH_NODE,
        source_key={"name": ok_value},
        status=Status.SOURCED,
    )
    out = write_logbook(run_id, "AVV", [entry], tmp_path)
    assert out.exists()


def test_adr001_guard_does_not_check_provenance_license_slash(tmp_path):
    """A license string with a slash (EU SCC Decision 2021/914) is in the
    provenance block, not source_key — it must NOT trip the guard."""
    run_id = "6a3e5e15-1234-4abc-9def-0123456789ab"
    entry = LogbookEntry(
        section="SCC Annex I.B",
        source_type=SourceType.GRAPH_NODE,
        source_key={"label": "Service", "name": "Stripe"},
        status=Status.SOURCED,
        provenance=ProvenanceBlock(license="EU SCC Decision 2021/914"),
    )
    out = write_logbook(run_id, "SCC", [entry], tmp_path)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["entries"][0]["provenance"]["license"] == "EU SCC Decision 2021/914"
