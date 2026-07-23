"""Logs run-select (row-58 follow-up, verdict a) — mutation guards.

Finding 2026-07-19 21:26: the /logs dropdown mislabeled every run as
"(Projekt gelöscht)" (UI matched on full UUIDs while log events carry 8-char
run ids) and structurally hid all runs outside the 100-line tail window.
Reverting either fix turns these red.
"""

import json
from pathlib import Path

import src.interface.approve_api as approve_api

LOGS_PAGE = (Path(__file__).parents[1]
             / "src" / "dashboard" / "app" / "logs" / "page.tsx")


def test_logs_select_matches_on_short_id():
    src = LOGS_PAGE.read_text(encoding="utf-8")
    assert "[r.run_id, r]" in src, (
        "logs run-select must key its metadata map on the 8-char r.run_id — "
        "a run_id_full map matches no log event and mislabels every run"
    )
    assert "metaByFull" not in src, "full-UUID map must not come back"


def _write_log(tmp_path, events):
    log = tmp_path / "lex-scan.log"
    log.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    return log


def test_filter_then_tail_reaches_runs_outside_window(tmp_path, monkeypatch):
    """A run older than the last `lines` log lines must still deliver events."""
    old = [{"event": "scan_start", "run_id": "aaaa1111", "n": i} for i in range(150)]
    new = [{"event": "scan_start", "run_id": "bbbb2222", "n": i} for i in range(120)]
    monkeypatch.setattr(approve_api, "SCAN_LOG_PATH", _write_log(tmp_path, old + new))

    d = approve_api.get_logs(lines=100, filter="all", run_id="aaaa1111")
    assert d["total"] > 0, "run outside the tail window must be reachable (filter then tail)"
    assert all(e["run_id"] == "aaaa1111" for e in d["events"])
    assert len(d["events"]) <= 100, "lines-cap must still apply after the filter"


def test_run_ids_cover_whole_log_not_window(tmp_path, monkeypatch):
    """Dropdown source: distinct runs over the whole log, newest first."""
    old = [{"event": "scan_start", "run_id": "aaaa1111", "n": i} for i in range(150)]
    new = [{"event": "scan_start", "run_id": "bbbb2222", "n": i} for i in range(120)]
    monkeypatch.setattr(approve_api, "SCAN_LOG_PATH", _write_log(tmp_path, old + new))

    d = approve_api.get_logs(lines=100, filter="all", run_id="")
    assert "aaaa1111" in d["run_ids"], (
        "run outside the 100-line window must still appear in the dropdown source"
    )
    assert d["run_ids"][0] == "bbbb2222", "newest run first"


def test_deep_link_full_uuid_selects_short_id_run(tmp_path, monkeypatch):
    """Scan-status deep link passes the full UUID; events carry 8-char ids."""
    events = [{"event": "scan_start", "run_id": "cccc3333", "n": i} for i in range(5)]
    monkeypatch.setattr(approve_api, "SCAN_LOG_PATH", _write_log(tmp_path, events))

    d = approve_api.get_logs(
        lines=100, filter="all",
        run_id="cccc3333-0000-0000-0000-000000000000",
    )
    assert d["total"] == 5
