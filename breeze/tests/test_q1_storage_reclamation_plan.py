from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "breeze" / "scripts" / "q1_storage_reclamation_plan.py"
SPEC = importlib.util.spec_from_file_location("q1_storage_reclamation_plan", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_checked_file_rejects_size_drift(tmp_path: Path) -> None:
    path = tmp_path / "asset.bin"
    path.write_bytes(b"abc")
    MODULE.checked_file(path, 3)
    with pytest.raises(ValueError, match="size drift"):
        MODULE.checked_file(path, 4)


def test_rendered_plan_does_not_select_blocked_assets() -> None:
    rows = [
        {
            "batch": "MUTCM_EXACT_SMALL_SUBSET_DUPLICATES",
            "bytes": 1,
            "retained_sha256": "a" * 64,
        },
        {
            "batch": "IMS_EXACT_NESTED_DUPLICATES",
            "bytes": 2,
            "retained_sha256": "b" * 64,
        },
    ]
    report = MODULE.render_report(rows, 10 * MODULE.GIB)
    assert "No deletion has been performed" in report
    assert "DIRG NPZs" in report and "retained" in report
    assert "XJTU archive" in report and "retained" in report


def test_mutcm_keeper_is_the_archive_not_an_assumed_extracted_file() -> None:
    assert MODULE.MUTCM_ARCHIVE.name == "full_dataset.7z"
    assert len(MODULE.MUTCM_ARCHIVE_SHA256) == 64
