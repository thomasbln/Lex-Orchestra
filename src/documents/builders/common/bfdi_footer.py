"""ADR-106 PR C5 — BfDI Citation Footer Hook
==============================================

Centralized helper that collects BfDI anchorings (bfdi_guidance /
bfdi_commentary properties seeded by seed_pr_c4_bfdi) for any Requirement,
Law, or DocumentType nodes touched by a scan, and surfaces them as a
deduplicated `list[BfDICitation]` for template rendering.

Used by AVVBuilder / VVTBuilder / DSFABuilder to expose `bfdi_citations` on
their respective ContentModels. Template macro renders these as the
'Quellenverweise BfDI' block at the doc footer with mandatory dl-de/by-2-0
attribution per ADR-107.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Footer display cap. The full verbatim BfDI text stays on the node; only the
# rendered excerpt is bounded — at a sentence boundary, never mid-word.
_EXCERPT_LIMIT = 300


def _truncate_excerpt(text: str) -> str:
    """Display value: full text within the limit, else truncated at the last
    sentence end (punctuation + whitespace) within the limit, with an ellipsis.
    Falls back to a word boundary when no sentence end is found — never mid-word.
    """
    if len(text) <= _EXCERPT_LIMIT:
        return text
    window = text[:_EXCERPT_LIMIT]
    sentence_end = max(window.rfind(p) for p in (". ", "! ", "? ", ".\n", "!\n", "?\n"))
    if sentence_end > 0:
        return window[: sentence_end + 1] + "…"
    if " " in window:
        return window.rsplit(" ", 1)[0] + "…"
    return window + "…"


@dataclass(frozen=True)
class BfDICitation:
    """Single BfDI anchoring shown in a doc footer.

    `value` is the full verbatim text from the BfDI brochure (often 100–400
    chars). `excerpt` bounds it for display at a sentence boundary. It is a
    derived **field** (not a property) so that dataclasses.asdict() — used by
    document_architect to hand the model to Jinja — serializes it; a property
    would be dropped and the template would render an empty quote. Source
    attribution is constant per dl-de/by-2-0 license — rendered once at the
    bottom of the citations block, not per-citation.
    """
    source_section: str   # e.g. "3.1" or "3.2"
    source_pages: str     # e.g. "S. 44–45"
    value: str            # full BfDI text
    law_refs: list[str]   # e.g. ["DSGVO Art. 28 Abs. 3"]
    target_label: str     # e.g. "DSGVO Art. 28 Abs. 3" or "AVV (DocumentType)"
    excerpt: str = field(init=False, default="")  # derived from value in __post_init__

    def __post_init__(self) -> None:
        # frozen=True → assign via object.__setattr__.
        object.__setattr__(self, "excerpt", _truncate_excerpt(self.value))


def _collect_from_query(session, query: str, label_fn) -> list[BfDICitation]:
    """Helper: run a Cypher query that returns
    (section, pages, value, law_refs, <fields_for_label_fn>) and build
    BfDICitation entries.
    """
    out: list[BfDICitation] = []
    for row in session.run(query):
        section = row.get("section")
        if not section:
            continue
        out.append(BfDICitation(
            source_section=section,
            source_pages=row.get("pages") or "",
            value=row.get("value") or row.get("commentary") or "",
            law_refs=row.get("law_refs") or [],
            target_label=label_fn(row),
        ))
    return out


def collect_bfdi_citations(graph_client, doc_type: str) -> list[BfDICitation]:
    """Return BfDI citations relevant to a given doc type.

    Strategy: rather than over-engineer per-section filtering, we surface ALL
    BfDI-attached nodes that match the doc's topic area:
    - AVV → BfDI chapter 3.2 (Auftragsverarbeitung) Requirements + DocumentType AVV
    - DSFA → BfDI chapter 3.1 (DSB-Pflichten) + 3.2 Requirements
    - VVT → same as AVV (Art. 30 Abs. 2 covers VVT for processors)

    Deduplicates by source_section. Returns ordered by section ascending.
    """
    if not graph_client:
        return []
    try:
        from src.graph.graph_client import NEO4J_DB
        with graph_client._driver.session(database=NEO4J_DB) as sess:
            queries: list[str] = []
            if doc_type in ("AVV", "VVT"):
                queries.append("""
                    MATCH (n:Requirement)
                    WHERE n.bfdi_guidance IS NOT NULL
                      AND n.bfdi_source_section STARTS WITH '3.2'
                    RETURN n.bfdi_source_section AS section,
                           n.bfdi_source_pages   AS pages,
                           n.bfdi_guidance       AS value,
                           n.bfdi_law_refs       AS law_refs,
                           n.id                  AS req_id,
                           n.framework           AS fw,
                           n.title_de            AS title
                    ORDER BY n.bfdi_source_section, n.id
                """)
                queries.append("""
                    MATCH (n:DocumentType {type: 'AVV'})
                    WHERE n.bfdi_commentary IS NOT NULL
                    RETURN n.bfdi_source_section AS section,
                           n.bfdi_source_pages   AS pages,
                           n.bfdi_commentary     AS value,
                           n.bfdi_law_refs       AS law_refs,
                           'AVV (DocumentType)'  AS title
                """)
            elif doc_type == "DSFA":
                queries.append("""
                    MATCH (n:Requirement)
                    WHERE n.bfdi_guidance IS NOT NULL
                      AND (n.bfdi_source_section STARTS WITH '3.1'
                           OR n.bfdi_source_section STARTS WITH '3.2')
                    RETURN n.bfdi_source_section AS section,
                           n.bfdi_source_pages   AS pages,
                           n.bfdi_guidance       AS value,
                           n.bfdi_law_refs       AS law_refs,
                           n.id                  AS req_id,
                           n.framework           AS fw,
                           n.title_de            AS title
                    ORDER BY n.bfdi_source_section, n.id
                """)
            else:
                return []

            out: list[BfDICitation] = []
            seen_targets: set[str] = set()
            for q in queries:
                for row in sess.run(q):
                    section = row.get("section")
                    if not section:
                        continue
                    title = row.get("title") or row.get("req_id") or "—"
                    fw = row.get("fw")
                    label = f"{fw}: {title}" if fw else title
                    # Dedup by target (each Requirement/DocumentType cited once),
                    # not by section — multiple Requirements can share a section.
                    if label in seen_targets:
                        continue
                    seen_targets.add(label)
                    out.append(BfDICitation(
                        source_section=section,
                        source_pages=row.get("pages") or "",
                        value=row.get("value") or "",
                        law_refs=row.get("law_refs") or [],
                        target_label=label,
                    ))
            out.sort(key=lambda c: (c.source_section, c.target_label))
            return out
    except Exception as exc:
        logger.warning("BfDI citation collection failed for %s: %s", doc_type, exc)
        return []
