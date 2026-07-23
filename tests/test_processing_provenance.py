"""ADR-079 PR 2c-i — Ebene-0 provenance classification (N / X / Differenz).

DB-free: exercises the pure ``_classify_provenance`` logic with mocked
service-detection names + mocked graph rows. Mock rows use the Cypher
RETURN-alias keys (name / has_service_node / requires_avv / gdpr_adequate),
not node property names.
"""
from src.graph.graph_client import _classify_provenance


# rand-industries (run ff70cd44), the verified 14 / 11 / 3 split.
_DETECTED = [
    "Braintree", "dotenv", "Elasticsearch", "MongoDB", "OpenAI", "Postmark",
    "Redis", "Resend", "Segment", "Sentry", "Stripe", "Supabase",
    "ts-node", "typescript",
]
# 11 processors (has node + requires_avv); 8 of them gdpr_adequate=false.
_THIRD_COUNTRY = {"Braintree", "MongoDB", "OpenAI", "Postmark", "Redis",
                  "Segment", "Stripe", "Supabase"}
_PROCESSORS = _THIRD_COUNTRY | {"Elasticsearch", "Resend", "Sentry"}
_TOOLING = {"dotenv", "ts-node", "typescript"}


def _graph_rows():
    rows = []
    for nm in _DETECTED:
        if nm in _PROCESSORS:
            rows.append({
                "name": nm,
                "has_service_node": True,
                "requires_avv": True,
                "gdpr_adequate": nm not in _THIRD_COUNTRY,
            })
        else:  # tooling: no service node
            rows.append({
                "name": nm,
                "has_service_node": False,
                "requires_avv": False,
                "gdpr_adequate": None,
            })
    return rows


def test_rand_industries_14_11_3():
    r = _classify_provenance(_DETECTED, _graph_rows())
    assert r["n"] == 14
    assert r["x"] == 11
    assert set(r["processors"]) == _PROCESSORS
    assert r["differenz"] == 3
    assert set(r["tooling"]) == _TOOLING
    assert r["other_services"] == []


def test_x_drittland_is_subset_of_x():
    r = _classify_provenance(_DETECTED, _graph_rows())
    assert r["x_drittland"] == 8
    assert set(r["third_country"]) == _THIRD_COUNTRY
    assert set(r["third_country"]).issubset(set(r["processors"]))


def test_nothing_silently_dropped():
    r = _classify_provenance(_DETECTED, _graph_rows())
    assert r["n"] == len(r["processors"]) + len(r["tooling"]) + len(r["other_services"])
    # every detected name appears in exactly one bucket
    buckets = set(r["processors"]) | set(r["tooling"]) | set(r["other_services"])
    assert buckets == set(_DETECTED)


def test_node_without_requires_avv_is_other_not_tooling():
    detected = ["GitHub"]
    rows = [{"name": "GitHub", "has_service_node": True,
             "requires_avv": False, "gdpr_adequate": True}]
    r = _classify_provenance(detected, rows)
    assert r["x"] == 0
    assert r["differenz"] == 0           # tooling = no node only
    assert r["other_services"] == ["GitHub"]
    assert r["n"] == 1


def test_empty_run():
    r = _classify_provenance([], [])
    assert r == {
        "n": 0, "detected": [], "x": 0, "processors": [],
        "x_drittland": 0, "third_country": [],
        "differenz": 0, "tooling": [], "other_services": [],
    }


def test_missing_graph_row_treated_as_no_node():
    # a detected name with no matching graph row -> tooling (no node)
    r = _classify_provenance(["Mystery"], [])
    assert r["tooling"] == ["Mystery"]
    assert r["x"] == 0
