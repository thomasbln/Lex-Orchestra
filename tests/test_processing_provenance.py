"""ADR-079 PR 2c-i — Ebene-0 provenance classification (N / X / Differenz).

DB-free: exercises the pure ``_classify_provenance`` logic with mocked
service-detection names + mocked graph rows. Mock rows use the Cypher
RETURN-alias keys (name / has_service_node / requires_avv / gdpr_adequate),
not node property names.

Fixture honesty (2026-07-28)
----------------------------
This file used to pin the bucket as ``tooling``. The name did not survive a check
against production: the bucket is not tooling. It is "no Service node in the catalog", which is a
statement about *our* knowledge, not about the third party. See the rationale in
``graph_client._classify_provenance``.

Correction (also 2026-07-28): an earlier version of this note claimed those three
names "cannot reach scan_signals today". **That was wrong** — a live check found
``dotenv``, ``ts-node`` and ``typescript`` in ``scan_signals`` on the working
system with a same-day timestamp. The reasoning error was to look only at the
static map: ``_add_canonical`` (``workflow/main.py``) falls through to
``canonical_with_fallback(raw, use_llm=True)`` when ``canonical()`` misses, and
Gemma4 happily returns the package name itself as the canonical name. It is then
added with no Service node behind it — straight into this bucket.

So there are three reachable paths, not two, and the third is the common one:

1. a canonical ``SIGNAL_MAP`` name with no catalog node (a catalog gap),
2. an unmapped compose image via ``canonical(raw) or raw.capitalize()`` in
   ``lex_orchestra_scout._scan_deployment_signals`` (arrives capitalised —
   a live document once read "1 Entwicklungswerkzeug … (Openai)"),
3. **Gemma4 echoing a package name** it could classify but the catalog does not
   know — how ``dotenv``/``ts-node``/``typescript`` got there.

The fixture keeps one synthetic member per path so the arithmetic stays legible.
"""
from src.graph.graph_client import _classify_provenance


# Shape taken from rand-industries (run ff70cd44): 14 detected, 11 processing.
_DETECTED = [
    "Braintree", "Elasticsearch", "MongoDB", "OpenAI", "Postmark",
    "Redis", "Resend", "Segment", "Sentry", "Stripe", "Supabase",
    # ── the three unclassified members, one per reachable production path ──
    # 1. unmapped docker-compose image → canonical() misses → .capitalize()
    "Worker",
    # 2. Gemma4 echoed the package name; no catalog node behind it. This is the
    #    common case in the field — dotenv/ts-node/typescript arrive this way.
    "ts-node",
    # 3. Gemma4 named it in the 0.60–0.75 confidence band: detected, but below
    #    the 0.75 threshold that would create a Service node
    #    (workflow/main.py, create_service_node_from_llm).
    "Acme Analytics",
]
# 11 processors (has node + requires_avv); 8 of them gdpr_adequate=false.
_THIRD_COUNTRY = {"Braintree", "MongoDB", "OpenAI", "Postmark", "Redis",
                  "Segment", "Stripe", "Supabase"}
_PROCESSORS = _THIRD_COUNTRY | {"Elasticsearch", "Resend", "Sentry"}
_UNCLASSIFIED = {"Worker", "ts-node", "Acme Analytics"}


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
