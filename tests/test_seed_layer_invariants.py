"""ADR-117 PR 4 guard — the seed layers must never write Control title_de/title_en.

Control i18n lives only via the ADR-117 pipeline (PR 1/2, applied to NucBox). The layers
write `c.title` (canonical, legacy) but NOT the i18n pair. This static invariant proves —
without a live re-seed — that `make seed-all` cannot alter Control title_de/title_en:
PR 1/2 work (tiers, RS gap, source) is re-seed-safe, and any future `c.title` removal
cannot accidentally touch the i18n fields.

(The title_de/title_en SETs that DO exist in the layers are Law `l.` / UseCase `uc5.`,
never Control `c.` — verified 2026-06-03.)
"""
import re
from pathlib import Path

_CONTROL_I18N = re.compile(r"\bc\.title_(?:de|en)\s*=")


def _layer_files() -> list[Path]:
    root = Path(__file__).resolve().parents[1]
    files = list(root.glob("src/graph/layers/**/*.cypher"))
    seed = root / "src/graph/neo4j_seed.cypher"
    if seed.exists():
        files.append(seed)
    return files


def test_layers_never_set_control_i18n():
    offenders: list[str] = []
    for f in _layer_files():
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip().startswith("//"):
                continue
            if _CONTROL_I18N.search(line):
                offenders.append(f"{f.name}:{i}: {line.strip()}")
    assert not offenders, (
        "Seed layers must not write Control title_de/title_en (ADR-117: Control i18n "
        "comes only from the PR1/PR2 pipeline). Offenders:\n" + "\n".join(offenders)
    )


def test_guard_actually_scans_layer_files():
    # Sanity: the glob finds the known layer files (so the guard isn't vacuously green).
    names = {f.name for f in _layer_files()}
    assert "neo4j_seed.cypher" in names
    # 20_bsi_c5.cypher is license-gated (BYOS, ADR-118) — absent from the
    # public tree by design. When it exists, the glob must see it.
    c5 = Path(__file__).resolve().parents[1] / "src/graph/layers/20_frameworks/20_bsi_c5.cypher"
    if c5.exists():
        assert "20_bsi_c5.cypher" in names

