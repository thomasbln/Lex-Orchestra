"""ADR-079 PR 2c-ii — Ebene-0 'Warum-Box' render (positive assertions).

DB-free: instantiates the orchestrator and patches `_provenance` so the box
render is exercised without Supabase/Neo4j. Positive (expected text present),
not only negative (jargon absent).
"""
from src.agents.document_architect import DocumentOrchestrator

# rand-industries (run ff70cd44) — the verified 14 / 11 / 3 provenance.
PROV = {
    "n": 14, "detected": [],
    "x": 11,
    "processors": ["Braintree", "Elasticsearch", "MongoDB", "OpenAI", "Postmark",
                   "Redis", "Resend", "Segment", "Sentry", "Stripe", "Supabase"],
    "x_drittland": 8,
    "third_country": ["Braintree", "MongoDB", "OpenAI", "Postmark", "Redis",
                      "Segment", "Stripe", "Supabase"],
    "differenz": 3, "tooling": ["dotenv", "ts-node", "typescript"],
    "other_services": [],
}


def _orch(prov=PROV):
    o = DocumentOrchestrator()
    o._provenance = lambda run_id: prov
    return o


def test_avv_box_shows_n_x_differenz_and_names():
    box = _orch()._render_ebene0_box("AVV", {"run_id": "x"})
    assert "14" in box and "11" in box and "3" in box
    # ADR-121 named: every detected processor is named, no "+K weitere" collapse
    for proc in PROV["processors"]:
        assert proc in box                       # all 11 processors named
    assert "weitere" not in box                  # no count collapse
    for tool in ("dotenv", "ts-node", "typescript"):
        assert tool in box                       # 3 tooling names all shown
    assert "Warum dieses Dokument" in box


def test_vvt_uses_service_box_like_avv():
    box = _orch()._render_ebene0_box("VVT", {"run_id": "x"})
    assert "14" in box and "11" in box


def test_scc_box_uses_x_drittland_not_x():
    box = _orch()._render_ebene0_box("SCC", {"run_id": "x"})
    assert "8" in box                            # x_drittland
    assert "Drittländer" in box and "Standardvertragsklauseln" in box
    assert "Stripe" in box                       # a third-country service (8 <= threshold)
    # the full X=11 framing must NOT appear in the SCC box
    assert "11" not in box


def test_ki_docs_use_usecase_trigger_not_service_box():
    for dt, needle in [
        ("KI_Policy", "Art. 4"),
        ("DSFA", "Art. 35"),
        ("AI_Act_Manifest", "2024/1689"),
        ("KI_System_Dokumentation", "Art. 11"),
    ]:
        box = _orch()._render_ebene0_box(dt, {"run_id": "x"})
        assert needle in box, f"{dt} missing legal trigger {needle}"
        # the service N/X box phrasing must NOT appear (use-case trigger only)
        assert "Komponenten erkannt" not in box, f"{dt} must not show the service N/X box"
        assert "Entwicklungswerkzeuge" not in box, f"{dt} must not show the service N/X box"


def test_other_services_surfaced_not_swallowed():
    prov = dict(PROV, other_services=["GitHub"], differenz=3)
    box = _orch(prov)._render_ebene0_box("AVV", {"run_id": "x"})
    assert "GitHub" in box and "bitte prüfen" in box


def test_no_cache_different_run_id_different_box():
    """C1 NO-CACHE: the box is recomputed per render, not a frozen constant."""
    o = DocumentOrchestrator()
    provs = {
        "run-a": dict(PROV, n=14, x=11),
        "run-b": dict(PROV, n=5, x=2, processors=["Stripe", "OpenAI"]),
    }
    o._provenance = lambda run_id: provs[run_id]
    box_a = o._render_ebene0_box("AVV", {"run_id": "run-a"})
    box_b = o._render_ebene0_box("AVV", {"run_id": "run-b"})
    assert "14" in box_a and "5" in box_b
    assert box_a != box_b


def test_box_empty_when_provenance_unavailable():
    o = DocumentOrchestrator()
    o._provenance = lambda run_id: None
    assert o._render_ebene0_box("AVV", {"run_id": "x"}) == ""


def test_unknown_doc_type_no_box():
    assert _orch()._render_ebene0_box("Sonstiges", {"run_id": "x"}) == ""
