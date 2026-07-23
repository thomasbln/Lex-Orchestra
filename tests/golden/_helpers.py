import dataclasses
import json
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent
FIXTURE_DIR = Path(__file__).parents[1] / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text())


def _load_golden(name: str) -> dict:
    return json.loads((GOLDEN_DIR / name).read_text())


def _save_golden(name: str, model: object) -> None:
    """Write a new golden baseline. Call once manually, not in tests."""
    (GOLDEN_DIR / name).write_text(
        json.dumps(dataclasses.asdict(model), indent=2, default=str)
    )
