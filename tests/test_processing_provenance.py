"""ADR-079 PR 2c-i — Ebene-0 provenance classification (N / X / Differenz).

DB-free: exercises the pure ``_classify_provenance`` logic with mocked
service-detection names + mocked graph rows. Mock rows use the Cypher
RETURN-alias keys (name / has_service_node / requires_avv / gdpr_adequate),
not node property names.

Fixture honesty (2026-07-28)
----------------------------
This file used to pin the bucket as ``tooling`` and fill it with ``dotenv``,
``ts-node`` and ``typescript``. Neither the name nor the members survived a
check against production:

* The bucket is not tooling. It is "no Service node in the catalog", which is a
  statement about *our* knowledge, not about the third party. See the rationale
  in ``graph_client._classify_provenance``.
* Those three names cannot reach ``scan_signals`` today. The manifest path drops
  a token whose ``canonical()`` is ``None`` (``workflow/main.py`` around the
  ``manifest_services`` build), and the compose path in
  ``lex_orchestra_scout._scan_deployment_signals`` emits
  ``canonical(raw) or raw.capitalize()`` — so an unmapped compose service
  arrives capitalised, never as lowercase ``ts-node``.

The fixture below therefore uses names each of the two reachable paths can
actually produce, and says which path produces them.
"""
from src.graph.graph_client import _classify_provenance


# Shape taken from rand-industries (run ff70cd44): 14 detected, 11 processing.
_DETECTED = [
    "Braintree", "Elasticsearch", "MongoDB", "OpenAI", "Postmark",
    "Redis", "Resend", "Segment", "Sentry", "Stripe", "Supabase",
    # ── the three unclassified members, one per reachable production path ──
    # 1. unmapped docker-compose image → canonical() misses → .capitalize()
    "Worker",
    "Nginx",
    # 2. Gemma4 named it in the 0.60–0.75 confidence band: detected, but
    #    below the 0.75 threshold that would create a Service node
    #    (workflow/main.py, create_service_node_from_llm).
    "Acme Analytics",
]
# 11 processors (has node + requires_avv); 8 of them gdpr_adequate=false.
_THIRD_COUNTRY = {"Braintree", "MongoDB", "OpenAI", "Postmark", "Redis",
                  "Segment", "Stripe", "Supabase"}
_PROCESSORS = _THIRD_COUNTRY | {"Elasticsearch", "Resend", "Sentry"}
_UNCLASSIFIED = {"Worker", "Nginx", "Acme Analytics"}


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
        else:  # unclassified: no service node in the catalog
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
    assert set(r["unclassified"]) == _UNCLASSIFIED
    assert r["other_services"] == []


def test_x_drittland_is_subset_of_x():
    r = _classify_provenance(_DETECTED, _graph_rows())
    assert r["x_drittland"] == 8
    assert set(r["third_country"]) == _THIRD_COUNTRY
    assert set(r["third_country"]).issubset(set(r["processors"]))


def test_nothing_silently_dropped():
    r = _classify_provenance(_DETECTED, _graph_rows())
    assert r["n"] == len(r["processors"]) + len(r["unclassified"]) + len(r["other_services"])
    # every detected name appears in exactly one bucket
    buckets = set(r["processors"]) | set(r["unclassified"]) | set(r["other_services"])
    assert buckets == set(_DETECTED)


def test_node_without_requires_avv_is_other_not_unclassified():
    detected = ["GitHub"]
    rows = [{"name": "GitHub", "has_service_node": True,
             "requires_avv": False, "gdpr_adequate": True}]
    r = _classify_provenance(detected, rows)
    assert r["x"] == 0
    assert r["differenz"] == 0           # unclassified = no node only
    assert r["other_services"] == ["GitHub"]
    assert r["n"] == 1


def test_empty_run():
    r = _classify_provenance([], [])
    assert r == {
        "n": 0, "detected": [], "x": 0, "processors": [],
        "x_drittland": 0, "third_country": [],
        "differenz": 0, "unclassified": [], "other_services": [],
    }


def test_missing_graph_row_treated_as_no_node():
    # a detected name with no matching graph row -> unclassified (no node)
    r = _classify_provenance(["Mystery"], [])
    assert r["unclassified"] == ["Mystery"]
    assert r["x"] == 0


def test_no_bucket_is_called_tooling():
    """The claim, not just the key, is what was wrong.

    A catalog miss says nothing about whether the component processes personal
    data. If someone re-introduces a ``tooling`` key, the wording follows it
    back into customer documents — so pin the absence.
    """
    r = _classify_provenance(["Mystery"], [])
    assert "tooling" not in r
