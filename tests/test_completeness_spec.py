"""Completeness ratchet — required_sections spec ↔ rendered document coupling.

Finding 2026-07-28 (spec-drift sweep): the ADR-099/102 template rebuilds were
never mirrored into DocumentType.required_sections. The validator silently
scored 0.2–0.92 across four doc types in the DE standard path and nobody
noticed, because no test asserted 1.0. This module IS that missing coupling:

- ``test_spec_sections_all_present_in_de_render`` asserts an EXACT score of
  1.0 for every doc type carrying required_sections — not "green", not
  "above threshold". The miss list is in the failure message so the next
  drift costs no hand analysis. It parses the spec from the SEED FILE
  (``10_eu_primary.cypher``) — the repo source of truth — so it runs
  DB-free (CI-ready; the repo has no CI pipeline today, the pytest battery
  + pre-commit are the effective gates).
- ``test_live_graph_spec_matches_seed`` (skipped without a reachable graph)
  pins the live DB to the seed file, so a hotfixed property cannot drift
  away from the repo again.

Deliberate scope limit (named, not solved — see the 2026-07-28 order): this
ratchet checks spec → document only. The OPPOSITE direction — a template
section the spec does not know — is NOT caught: a future mandatory section
added to a template without a spec entry keeps scoring 1.0 while being
unchecked. Closing that needs a curated "which headings are duty-bearing"
list; a naive all-headings assertion would flag prose sections.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SEED = REPO / "src" / "graph" / "layers" / "10_jurisdiction" / "eu" / "10_eu_primary.cypher"


def _seed_specs() -> dict[str, list[str]]:
    """Parse {doc_type: required_sections} from the seed layer (repo truth)."""
    src = SEED.read_text(encoding="utf-8")
    specs: dict[str, list[str]] = {}
    for m in re.finditer(r'MERGE \(d:DocumentType \{type: "([^"]+)"\}\)', src):
        block = src[m.start():src.find(";", m.start())]
        rs = re.search(r"required_sections = \[(.*?)\]", block, re.S)
        if rs:
            specs[m.group(1)] = re.findall(r'"([^"]+)"', rs.group(1))
    return specs


_SEED_SPECS = _seed_specs()

# One render callable per doc type — the linter harness renders DB-free from
# the rand_industries fixtures (the reference project).
import sys  # noqa: E402
sys.path.insert(0, str(REPO / "tests"))
import test_doc_linter as harness  # noqa: E402

_RENDERERS = {
    "AVV":                     harness._render_avv,
    "TOM":                     harness._render_tom,
    "VVT":                     harness._render_vvt,
    "DSFA":                    harness._render_dsfa,
    "KI_Policy":               harness._render_ki_policy,
    "KI_System_Dokumentation": harness._render_ki_system,
    "AI_Act_Manifest":         harness._render_ai_act_manifest,
}


def test_seed_carries_specs_for_all_renderable_types():
    """The seed must spec every doc type we can render — a dropped block
    (or a renderer without a spec) is itself a finding."""
    assert set(_SEED_SPECS) == set(_RENDERERS), (
        f"seed specs {sorted(_SEED_SPECS)} != renderable types {sorted(_RENDERERS)}"
    )


@pytest.mark.parametrize("doc_type", sorted(_SEED_SPECS))
def test_spec_sections_all_present_in_de_render(doc_type):
    """EXACTLY 1.0 — every spec section present in the DE reference render."""
    from src.agents.document_validator import _check_section_present

    env = harness._make_jinja("de")
    content = _RENDERERS[doc_type](env, "de")
    sections = _SEED_SPECS[doc_type]
    misses = [s for s in sections if not _check_section_present(content, s)]
    score = round((len(sections) - len(misses)) / len(sections), 2)
    assert not misses, (
        f"{doc_type}: completeness_score {score} != 1.0 — "
        f"missing sections: {misses}\n"
        "Either the template dropped/renamed a duty-bearing heading (mirror it "
        "into the spec: live graph + seed block in 10_eu_primary.cypher), or "
        "the spec entry is a deliberate red sentinel — then justify it HERE "
        "as a commented exception, do not lower the bar."
    )


@pytest.mark.parametrize("doc_type", sorted(_SEED_SPECS))
def test_live_graph_spec_matches_seed(doc_type):
    """Live DB pinned to the seed file — a hotfix must not drift from the repo."""
    try:
        from src.graph.graph_client import GraphClient, NEO4J_DB
        with GraphClient() as gc:
            with gc._driver.session(database=NEO4J_DB) as sess:
                row = sess.run(
                    "MATCH (d:DocumentType {type: $t}) RETURN d.required_sections AS s",
                    t=doc_type,
                ).single()
    except Exception as exc:
        pytest.skip(f"graph unreachable: {exc}")
    assert row and row["s"] == _SEED_SPECS[doc_type], (
        f"{doc_type}: live required_sections != seed file — "
        f"live={row and row['s']}, seed={_SEED_SPECS[doc_type]}"
    )
