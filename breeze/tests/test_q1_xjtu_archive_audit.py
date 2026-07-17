from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "breeze" / "scripts" / "q1_xjtu_archive_audit.py"
SPEC = importlib.util.spec_from_file_location("q1_xjtu_archive_audit", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_discover_parts_requires_contiguous_fixed_nonfinal_volumes(tmp_path: Path) -> None:
    for index, size in ((1, 10), (2, 10), (3, 7)):
        (tmp_path / f"dataset.part{index:02d}.rar").write_bytes(bytes(size))
    assert [path.name for path in MODULE.discover_parts(tmp_path)] == [
        "dataset.part01.rar",
        "dataset.part02.rar",
        "dataset.part03.rar",
    ]


def test_discover_parts_rejects_gap(tmp_path: Path) -> None:
    (tmp_path / "dataset.part01.rar").write_bytes(b"1")
    (tmp_path / "dataset.part03.rar").write_bytes(b"3")
    try:
        MODULE.discover_parts(tmp_path)
    except ValueError as exc:
        assert "non-contiguous" in str(exc)
    else:
        raise AssertionError("missing volume must fail")


def test_reference_scan_distinguishes_label_from_raw_binding(tmp_path: Path) -> None:
    (tmp_path / "config.json").write_text('{"dataset":"XJTU-SY"}', encoding="utf-8")
    (tmp_path / "manifest.json").write_text(
        '{"raw":"data/xjtu/XJTU-SY_Bearing_Datasets.part01.rar"}',
        encoding="utf-8",
    )
    rows = MODULE.scan_references((tmp_path,))
    assert {row["hit_type"] for row in rows} == {
        "dataset_label_only",
        "raw_path_binding",
    }


def test_member_path_safety() -> None:
    assert MODULE.safe_member_name("root/regime/bearing/1.csv")
    assert not MODULE.safe_member_name("../escape.csv")
    assert not MODULE.safe_member_name("/absolute.csv")
