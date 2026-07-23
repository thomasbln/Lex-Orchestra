"""ADR-127 P4.3 — owner-measure overlay loader (best-effort, shared by builders).

Reads the per-scan owner overlay from Supabase for a render:
- ``edits``: ``{control_id: text}`` where the owner confirmed a measure
  (``edited_flag`` true, ``text`` not null) for this ``(project, run, lang)``.
- ``deleted``: ``{control_id}`` controls the owner deactivated for this run —
  **language-agnostic** (gone in DE and EN).

Render precedence the builders apply on top of this overlay:
    owner edit (edits[cid]) > config["tom_implementations"] > graph default.
``deleted`` is a real skip (the control row is dropped entirely), never an empty
``concrete`` — so it hits both tom_builder (filters ``concrete==""``) and
ki_system_builder (ends ``or None``) consistently (K3 / seed-validator Wächter B).

``project_id`` is resolved via JOIN on ``project_config.project_name`` so callers
pass the ``project_name`` + ``run_id`` they already hold in ``BuildContext`` — no
schema change. DB URL resolution mirrors ``main._resolve_db_url`` (mcp first).

Best-effort: any failure (no DB_URL, Supabase down, tables missing) returns
``({}, set())`` so the builder falls back to graph defaults and never crashes.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def _db_url() -> str:
    return os.getenv("MCP_SUPABASE_URL", "") or os.getenv("DATABASE_URL", "")


def load_owner_measures(
    project_name: str | None,
    run_id: str | None,
    lang: str,
) -> tuple[dict[str, str], set[str]]:
    """Return (edits, deleted) overlay for one render; ({}, set()) on any failure."""
    db_url = _db_url()
    if not (db_url and project_name and run_id and lang):
        return {}, set()
    try:
        import psycopg2
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT om.control_id, om.text
                    FROM owner_measures om
                    JOIN project_config pc ON om.project_id = pc.id
                    WHERE pc.project_name = %s AND om.run_id = %s AND om.lang = %s
                      AND om.edited_flag IS TRUE AND om.text IS NOT NULL
                    """,
                    (project_name, run_id, lang),
                )
                edits = {row[0]: row[1] for row in cur.fetchall()}
                cur.execute(
                    """
                    SELECT dc.control_id
                    FROM deleted_controls dc
                    JOIN project_config pc ON dc.project_id = pc.id
                    WHERE pc.project_name = %s AND dc.run_id = %s
                    """,
                    (project_name, run_id),
                )
                deleted = {row[0] for row in cur.fetchall()}
        return edits, deleted
    except Exception as e:  # best-effort — never break a render on a DB hiccup
        logger.warning("owner_measures overlay load failed (non-fatal): %s", e)
        return {}, set()


def load_custom_measures(
    project_name: str | None,
    run_id: str | None,
    lang: str,
) -> list[dict]:
    """ADR-127 PR5e — owner-authored custom measures as synthetic control dicts.

    Returns rows with ``control_id LIKE 'custom-%'`` shaped like a graph control so the
    TOM builder renders them (TOM-only). ``service='—'`` so the "applicable to" column
    shows "—" (honest: custom measures are not service-bound). The deleted_controls skip
    and the owner overlay apply by control_id, so the active-toggle/edit work unchanged.
    title/text stay raw in the returned dicts; escaping happens at the render layer
    (cell_safe) — exactly one escape point, never here.

    Language-pure owner texts (ADR-129 re-audit B-1): custom rows are loaded across
    BOTH langs so a custom authored in one language still appears in the other
    language's document — with ``translation_pending=True`` and an empty text when
    the render lang has no owner text yet. The other-lang text is NEVER rendered as
    the measure (no silent language mixing); the builder turns the flag into a
    render-only gap marker. Title falls back to the other lang (the title names the
    measure; rule 4: the title appears, the measure cell carries the marker).
    Best-effort → [] on any failure.
    """
    db_url = _db_url()
    if not (db_url and project_name and run_id and lang):
        return []
    try:
        import psycopg2
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT om.control_id, om.lang, om.framework, om.title, om.text
                    FROM owner_measures om
                    JOIN project_config pc ON om.project_id = pc.id
                    WHERE pc.project_name = %s AND om.run_id = %s
                      AND om.control_id LIKE 'custom-%%'
                    ORDER BY om.control_id, om.lang
                    """,
                    (project_name, run_id),
                )
                rows = cur.fetchall()
        by_cid: dict[str, dict[str, tuple]] = {}
        for cid, row_lang, framework, title, text in rows:
            by_cid.setdefault(cid, {})[row_lang] = (framework, title, text)
        other = "en" if lang == "de" else "de"
        out: list[dict] = []
        for cid, langs in by_cid.items():
            active = langs.get(lang)
            fallback = langs.get(other)
            framework = (active or fallback)[0] or "Custom"
            # Active-lang text only; a non-empty other-lang text → translation pending.
            text = (active[2] if active else None) or ""
            pending = not text and bool(fallback and (fallback[2] or ""))
            title = (active[1] if active else None) or (fallback[1] if fallback else None) or ""
            out.append({
                "control_id": cid,
                "framework": framework,
                "title_de": title,
                "title_en": title,
                "text": text,
                "default_tom_measure": text,
                "translation_pending": pending,
                "service": "—",   # → "applicable to" renders "—" (not service-bound)
            })
        return out
    except Exception as e:  # best-effort
        logger.warning("load_custom_measures failed (non-fatal): %s", e)
        return []
