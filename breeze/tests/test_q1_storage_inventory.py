from __future__ import annotations

import csv
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "breeze" / "scripts" / "q1_storage_inventory.py"
SPEC = importlib.util.spec_from_file_location("q1_storage_inventory", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_storage_categories_are_non_overlapping() -> None:
    assert MODULE.classify(ROOT / "data" / "raw" / "source.7z") == "raw_archive"
    assert MODULE.classify(ROOT / "data" / "raw" / "source.mat") == "extracted_raw"
    assert MODULE.classify(ROOT / "proc" / "dataset.npz") == "processed_array"
    assert MODULE.classify(ROOT / "breeze" / "runs" / "pool.npz") == "generated_pool"
    assert MODULE.classify(ROOT / "breeze" / "runs" / "checkpoints" / "model.pt") == "checkpoint"


def test_atomic_csv_has_stable_schema(tmp_path: Path) -> None:
    output = tmp_path / "inventory.csv"
    rows = [
        {
            "path": "data/raw/source.7z",
            "bytes": 123,
            "gib": "0.000000",
            "mtime_utc": "2026-07-17T00:00:00+00:00",
            "category": "raw_archive",
            "git_visibility": "ignored",
        }
    ]
    MODULE.atomic_write_csv(output, rows)
    with output.open(newline="", encoding="utf-8") as handle:
        parsed = list(csv.DictReader(handle))
    assert parsed == [{key: str(value) for key, value in rows[0].items()}]
    assert not list(tmp_path.glob("*.tmp"))
