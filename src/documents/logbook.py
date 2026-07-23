"""Provenance logbook — per-document source-tracking artifact (ADR-111).

Emits an additive `<doctype>_<id>.logbook.json` alongside each generated
document, recording for every contributing source (graph node, gap, config
field, static template clause) where a document section came from — or why it
is a gap. The document itself is never changed; the logbook is purely additive.

Coverage level "voll-minus-Versions-Anker" (ADR-111 option D): inherit the
ADR-107 per-node provenance that is live today (`source` / `license` /
`last_verified`) and record `seed_run_id` as an honest empty field until
ADR-107 Rest 1 delivers the version/snapshot anchor.

ADR-001 discipline: only canonical names/keys ever enter the logbook — never
PII, file paths, or customer data. Mirrors the `log_cypher` rule
(src/utils/scan_logger.py): the artifact carries public seed knowledge
(canonical service names, control ids, law shorts), not asset content.

PR 1 (this module) defines the schema + the write side. The three builders
(AVV/VVT/SCC) emit real entries in PR 2 (ADR-111 plan).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path


class SourceType(str, Enum):
    """Where a logbook entry's content originated (ADR-111 taxonomy)."""

    GRAPH_NODE = "graph_node"          # Service / Law / Control node — key {label, name|id|short}
    GAP_MARKER = "gap_marker"          # inline_gap_marker(id) fired — key {gap_id}
    CONFIG_FIELD = "config_field"      # project config field (company, DPO) — key {field}
    STATIC_TEMPLATE = "static_template"  # fixed legal clause, not graph-derived — key {anchor}


class Status(str, Enum):
    """Section status, aligned with the existing document gap logic."""

    SOURCED = "sourced"
    GAP = "gap"
    CONFIG_MISSING = "config_missing"


@dataclass
class ProvenanceBlock:
    """ADR-107 per-node provenance, inherited as-is from the source node.

    `license` may be ``None`` — ADR-107 Rest 2 (coverage gap on Law/Control
    nodes). A missing license is *recorded as null*, never invented.

    `seed_run_id` is the version/snapshot anchor. It is ``None`` today on
    100 % of nodes (ADR-107 Rest 1, mechanism gap). The field exists from day
    one so it auto-fills once ADR-107 delivers the anchor — no schema retrofit.
    """

    source: str | None = None
    license: str | None = None
    last_verified: str | None = None
    # TODO(ADR-107 Rest 1): fills in once the seed_run_id mechanism exists.
    seed_run_id: str | None = None


@dataclass
class LogbookEntry:
    """One contributing source for a document section.

    Granularity is *per source node*, not per section: a multi-service section
    (e.g. AVV § 2 fed by Stripe + Postmark + PostgreSQL) yields one entry per
    contributing service — that is where the debugging value lives.
    """

    section: str
    source_type: SourceType
    source_key: dict
    status: Status
    provenance: ProvenanceBlock = field(default_factory=ProvenanceBlock)
    # Free-form, ADR-001-clean note (e.g. "integration_mode present but not applied").
    note: str | None = None


# Heuristic markers of a non-canonical value: file paths, emails, raw package
# specifiers (@scope/pkg), Windows paths. Canonical seed keys never contain
# these — "Stripe", "MongoDB Atlas", "C5-01", "Art. 28 DSGVO" all pass.
_PII_PATH_PATTERN = re.compile(r"[/\\]|@|\.(?:ts|tsx|js|py|json|env)\b", re.IGNORECASE)


def _assert_adr001_clean(source_key: dict) -> None:
    """Raise if any source_key value looks like a path / PII / raw package name.

    ADR-001: only canonical names/keys enter the logbook. This guards the
    `source_key` values specifically — provenance.license may legitimately
    contain a slash (e.g. "EU SCC Decision 2021/914") and is not checked here.
    """
    for key, value in source_key.items():
        if isinstance(value, str) and _PII_PATH_PATTERN.search(value):
            raise ValueError(
                f"ADR-001 violation: source_key[{key!r}]={value!r} looks like a "
                f"path / email / raw package name — only canonical names/keys "
                f"are allowed in the logbook."
            )


def _coerce_str(value):
    """Stringify a value for the logbook, or pass ``None`` through.

    Neo4j returns temporal properties (e.g. ``last_verified``) as
    ``neo4j.time.Date`` objects, which are not JSON-serializable. The Q_META
    services query does not sanitize rows, so these leak into the service dict.
    Coerce to ``str`` ("2026-05-28") so the logbook serializes — and so the
    recorded value is a stable string regardless of the driver's return type.
    """
    if value is None or isinstance(value, str):
        return value
    return str(value)


def extract_provenance(node: dict) -> ProvenanceBlock:
    """Pull the ADR-107 provenance properties off a graph_result node dict.

    Works for Service / Law / Control dicts as they arrive in
    ``graph_result["services"][i]`` etc. A missing `license` yields
    ``license=None`` (coverage gap, recorded not invented); `seed_run_id` is
    always ``None`` today (ADR-107 Rest 1). Values are coerced to ``str`` so a
    Neo4j ``Date`` (``last_verified``) does not break JSON serialization.
    """
    return ProvenanceBlock(
        source=_coerce_str(node.get("source")),
        license=_coerce_str(node.get("license")),
        last_verified=_coerce_str(node.get("last_verified")),
        seed_run_id=_coerce_str(node.get("seed_run_id")),
    )


def write_logbook(
    run_id: str,
    doc_type: str,
    entries: list[LogbookEntry],
    drafts_dir: Path,
) -> Path:
    """Serialize the logbook to ``<doc_type>_<run_id[:8]>.logbook.json``.

    Lives next to the document's ``.md`` / ``.pdf`` in ``drafts_dir``, sharing
    the same ``run_id[:8]`` prefix as the generated documents. Runs the ADR-001
    guard on every entry's source_key before writing.
    """
    for entry in entries:
        _assert_adr001_clean(entry.source_key)

    payload = {
        # Format property, not a run property: a plain integer schema version,
        # NOT an ADR reference. The deciding ADR is the format's origin story
        # (documented in the ADR + this module), not content of a single run.
        "schema_version": 1,
        "run_id": run_id,
        "doc_type": doc_type,
        "entries": [_entry_to_dict(e) for e in entries],
    }

    drafts_dir.mkdir(parents=True, exist_ok=True)
    out_path = drafts_dir / f"{doc_type}_{run_id[:8]}.logbook.json"
    out_path.write_text(
        # default=str: belt-and-suspenders for any non-JSON-native value that
        # slips through (e.g. an un-coerced Neo4j temporal type) — the logbook
        # must never fail to write because of a driver return-type surprise.
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return out_path


def _entry_to_dict(entry: LogbookEntry) -> dict:
    """asdict with the enums coerced to their string values, note dropped if empty."""
    d = asdict(entry)
    d["source_type"] = entry.source_type.value
    d["status"] = entry.status.value
    if entry.note is None:
        d.pop("note", None)
    return d
