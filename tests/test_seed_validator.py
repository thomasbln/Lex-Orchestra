"""
Tests for ADR-100 graph validator (scripts/seed_both.py::validate_graph).
All tests use fake session objects — no live Neo4j required.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from scripts.seed_both import ALLOWED_DATA_SUBJECTS, ALLOWED_LEGAL_BASIS, validate_graph


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_session(services=None, relationships=None, usecase_rows=None, law_rows=None):
    """Return a mock session whose .run() returns canned rows per query keyword."""
    services = services or []
    relationships = relationships or []
    usecase_rows = usecase_rows or []
    law_rows = law_rows or []

    def run(query, **_kwargs):
        q = query.strip().lower()
        if "match (s:service)" in q:
            return services
        if "subject_to_control" in q:
            return relationships
        if "classified_by" in q:
            return usecase_rows
        if "match (l:law)" in q:
            return law_rows
        return []

    session = MagicMock()
    session.run.side_effect = run
    return session


def _svc(name, ds):
    return {"name": name, "ds": ds}


def _rel(rid, lb):
    return {"rid": rid, "lb": lb}


def _uc(uc_type, count):
    return {"type": uc_type, "classified_by_count": count}


def _law(name, article, article_title):
    return {"name": name, "article": article, "article_title": article_title}


# ── §4.1 data_subjects ────────────────────────────────────────────────────────

def test_valid_service_passes():
    session = _make_session(services=[_svc("Stripe", ["customers", "employees"])])
    assert validate_graph(session) == []


def test_null_data_subjects_is_error():
    session = _make_session(services=[_svc("MongoDB", None)])
    errors = validate_graph(session)
    assert any("data_subjects is null" in e for e in errors)


def test_string_data_subjects_is_error():
    session = _make_session(services=[_svc("Braintree", "customers")])
    errors = validate_graph(session)
    assert any("must be list" in e for e in errors)


def test_unknown_data_subject_value_is_error():
    session = _make_session(services=[_svc("Segment", ["customers", "aliens"])])
    errors = validate_graph(session)
    assert any("unknown data_subjects" in e and "aliens" in e for e in errors)


def test_empty_list_is_valid():
    session = _make_session(services=[_svc("Redis", [])])
    assert validate_graph(session) == []


def test_all_allowed_values_pass():
    session = _make_session(services=[_svc("AllSvc", sorted(ALLOWED_DATA_SUBJECTS))])
    assert validate_graph(session) == []


# ── §4.2 legal_basis on SUBJECT_TO_CONTROL ───────────────────────────────────

def test_missing_legal_basis_is_error():
    session = _make_session(relationships=[_rel(42, None)])
    errors = validate_graph(session)
    assert any("legal_basis missing" in e for e in errors)


def test_empty_string_legal_basis_is_error():
    session = _make_session(relationships=[_rel(43, "")])
    errors = validate_graph(session)
    assert any("legal_basis missing" in e for e in errors)


def test_unknown_legal_basis_is_error():
    session = _make_session(relationships=[_rel(44, "art_99_fantasy")])
    errors = validate_graph(session)
    assert any("unknown legal_basis" in e and "art_99_fantasy" in e for e in errors)


def test_valid_legal_basis_passes():
    session = _make_session(relationships=[_rel(45, "art_6_1_b_contract")])
    assert validate_graph(session) == []


def test_all_allowed_legal_basis_pass():
    rels = [_rel(i, lb) for i, lb in enumerate(sorted(ALLOWED_LEGAL_BASIS))]
    session = _make_session(relationships=rels)
    assert validate_graph(session) == []


# ── §4.3 CLASSIFIED_BY on UseCases ───────────────────────────────────────────

def test_usecase_with_zero_classified_by_is_error():
    session = _make_session(usecase_rows=[_uc("hr_recruitment_screening", 0)])
    errors = validate_graph(session)
    assert any("hr_recruitment_screening" in e and "count=0" in e for e in errors)


def test_usecase_with_two_classified_by_is_error():
    session = _make_session(usecase_rows=[_uc("social_scoring", 2)])
    errors = validate_graph(session)
    assert any("social_scoring" in e and "count=2" in e for e in errors)


def test_usecase_with_correct_edge_is_not_returned():
    # The query filters WHERE rels <> 1, so correctly classified usecases
    # are NOT in the result set — validate_graph sees an empty list.
    session = _make_session(usecase_rows=[])
    assert validate_graph(session) == []


# ── §4.4 Law node minimal metadata ───────────────────────────────────────────
# article_title is required. deadline_hours / retention_years are nullable by
# design — null removes the property in Neo4j, so absence is not an error.

def test_law_missing_article_title_is_error():
    session = _make_session(law_rows=[_law("DSGVO", "33", None)])
    errors = validate_graph(session)
    assert any("article_title missing" in e for e in errors)


def test_law_empty_article_title_is_error():
    session = _make_session(law_rows=[_law("DSGVO", "33", "")])
    errors = validate_graph(session)
    assert any("article_title missing" in e for e in errors)


def test_law_with_article_title_passes():
    session = _make_session(law_rows=[_law("DSGVO", "33", "Meldung von Verletzungen")])
    assert validate_graph(session) == []


def test_law_absent_deadline_hours_is_not_an_error():
    # null deadline_hours removes the property in Neo4j — absence is valid
    session = _make_session(law_rows=[_law("DSGVO", "30", "Verzeichnis von Verarbeitungstätigkeiten")])
    assert validate_graph(session) == []


def test_fully_valid_graph_returns_no_errors():
    session = _make_session(
        services=[_svc("Stripe", ["customers"])],
        relationships=[_rel(1, "art_6_1_b_contract")],
        usecase_rows=[],
        law_rows=[_law("DSGVO", "33", "Meldung von Verletzungen des Schutzes")],
    )
    assert validate_graph(session) == []


def test_multiple_errors_all_reported():
    session = _make_session(
        services=[_svc("A", None), _svc("B", "string")],
        relationships=[_rel(1, None), _rel(2, "bad_value")],
        usecase_rows=[_uc("uc1", 0)],
        law_rows=[_law("DSGVO", "33", None)],
    )
    errors = validate_graph(session)
    assert len(errors) >= 5
