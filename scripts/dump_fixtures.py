#!/usr/bin/env python3
"""
Fixture capture for ADR-099 golden-file tests.

Monkey-patches DocumentArchitect.generate_all to capture all inputs during a
real scan so AVVBuilder (and later builders) have a baseline for golden-file tests.

NO changes to document_architect.py — the patch is only active while this script runs.

Usage:
    python scripts/dump_fixtures.py --project rand-industries --repo <repo-url-or-path>

Output (tests/fixtures/):
    rand_industries_graph.json        — graph_result as passed to generate_all
    rand_industries_reasoning.json    — reasoning_result
    rand_industries_config.json       — merged project_config + project_setup
    rand_industries_risk_signals.json — risk_signals list
    rand_industries_gaps.json         — gap_hints from self._gap_registry after generate_all
"""
import argparse
import json
import sys
import uuid
from dataclasses import asdict
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parents[1]))
from dotenv import load_dotenv
load_dotenv()

parser = argparse.ArgumentParser(description="Capture fixture JSONs from a live scan")
parser.add_argument("--project", default="rand-industries", help="Project name in Supabase")
parser.add_argument("--repo", required=True, help="Repo URL or local path to scan")
parser.add_argument("--depth", default="quick", choices=["quick", "full", "deep"])
args = parser.parse_args()

PROJECT = args.project
OUT = Path(__file__).parents[1] / "tests" / "fixtures"

# ---------------------------------------------------------------------------
# Monkey-patch — captures generate_all inputs + _gap_registry after original runs
# ---------------------------------------------------------------------------
from src.agents.document_architect import DocumentArchitect

_original_generate_all = DocumentArchitect.generate_all
captured: dict = {}


def _capture_and_forward(
    self,
    graph_result: dict,
    reasoning_result: dict,
    project_name: str,
    run_id: str,
    risk_signals=None,
    extraction_summary=None,
):
    # Capture inputs before original runs
    config = self._load_project_config(project_name) or {}
    setup = self._load_project_setup(project_name) or {}
    merged = {**config, **(setup or {})}

    captured["graph_result"] = graph_result
    captured["reasoning_result"] = reasoning_result or {}
    captured["config"] = merged
    captured["risk_signals"] = list(risk_signals or [])

    # Run original — this populates self._gap_registry
    result = _original_generate_all(
        self, graph_result, reasoning_result, project_name,
        run_id, risk_signals, extraction_summary,
    )

    # Read gap_hints from the registry the original populated — single source of truth
    captured["gaps"] = [asdict(g) for g in self._gap_registry.values()]

    svc_count = len(graph_result.get("services", []))
    print(f"  [capture] services={svc_count}  gaps={len(captured['gaps'])}  "
          f"risk_signals={len(risk_signals or [])}")

    return result


DocumentArchitect.generate_all = _capture_and_forward

# ---------------------------------------------------------------------------
# Trigger a real scan — initial state matches src/workflow/main.py exactly
# ---------------------------------------------------------------------------
print(f"Building workflow …")
from src.workflow.main import build_workflow

run_id = str(uuid.uuid4())
app = build_workflow(use_checkpointer=False)

initial_state = {
    "project_name":            PROJECT,
    "repo_url":                args.repo,
    "live_url":                None,
    "scan_depth":              args.depth,
    "dry_run":                 False,
    "scout_result":            None,
    "security_findings":       None,
    "deployment_signals":      None,
    "graph_result":            None,
    "reasoning_result":        None,
    "generated_docs":          [],
    "validation_result":       None,
    "config_requested":        False,
    "validator_retries":       0,
    "pending_telegram_message": None,
    "notification_sent":       False,
    "run_id":                  run_id,
    "errors":                  [],
}
config_dict = {"configurable": {"thread_id": run_id}}

print(f"Invoking scan for '{PROJECT}' (run_id={run_id[:8]}) …")
try:
    app.invoke(initial_state, config=config_dict)
finally:
    DocumentArchitect.generate_all = _original_generate_all

# ---------------------------------------------------------------------------
# Check capture succeeded
# ---------------------------------------------------------------------------
if not captured:
    print("\nERROR: generate_all was never called — scan did not reach document phase")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Write fixtures
# ---------------------------------------------------------------------------
OUT.mkdir(parents=True, exist_ok=True)

prefix = PROJECT.replace("-", "_")
FILES = {
    f"{prefix}_graph.json":         captured["graph_result"],
    f"{prefix}_reasoning.json":     captured["reasoning_result"],
    f"{prefix}_config.json":        captured["config"],
    f"{prefix}_risk_signals.json":  captured["risk_signals"],
    f"{prefix}_gaps.json":          captured["gaps"],
}

for filename, data in FILES.items():
    path = OUT / filename
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    print(f"  Written: tests/fixtures/{filename}")

# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------
services = captured["graph_result"].get("services", [])
gaps = captured["gaps"]
dpa_urls = [s.get("dpa_url") for s in services if s.get("dpa_url")]

print("\nSanity checks:")
print(f"  services count     : {len(services)} {'✅' if len(services) == 11 else '⚠️  expected 11'}")
print(f"  gaps count         : {len(gaps)} {'✅' if len(gaps) > 0 else '❌ expected > 0'}")
print(f"  services w/ dpa_url: {len(dpa_urls)} {'✅' if dpa_urls else '⚠️  none — Graph properties may be missing'}")

if len(gaps) == 0:
    print("\nERROR: 0 gaps — fixture is incomplete, do not commit")
    sys.exit(1)

print("\nDone. Review fixtures before committing.")
