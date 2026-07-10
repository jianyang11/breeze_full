from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(SCRIPTS))

from data_mt import (  # noqa: E402
    CLASS_ID_TO_DISPLAY_NAME,
    CLASS_ID_TO_NAME,
    MT_CHANNELS,
    MT_CLASSES,
    MT_DIR,
    RAW_CLASS_IDS,
    STRIDE_MT,
    TEST_FILES,
    TRAIN_FILES,
    WIN_MT,
    _windows,
    class_name_to_raw_id,
    normalize_mt_class,
    parse_mt_filename,
)
from mt_private_v1_preflight import (  # noqa: E402
    DECISION_SCHEMA_KEYS,
    exact_duplicate_pairs,
    window_hash,
)
from mt_verifier import MachineToolVerifier  # noqa: E402


def test_class_mapping_contract() -> None:
    assert RAW_CLASS_IDS == ["1", "2", "3"]
    assert MT_CLASSES == ["normal_machining", "lead_screw_anomaly", "base_imbalance"]
    assert CLASS_ID_TO_DISPLAY_NAME["1"] == "Normal machining"
    assert CLASS_ID_TO_NAME["2"] == "lead_screw_anomaly"


def test_filename_parsing() -> None:
    parsed = parse_mt_filename("2_10_pre.csv")
    assert parsed["parse_ok"] is True
    assert parsed["raw_class_id"] == "2"
    assert parsed["file_id"] == "10"
    assert parsed["class_name"] == "lead_screw_anomaly"
    parsed_no_pre = parse_mt_filename("3_7.csv")
    assert parsed_no_pre["parse_ok"] is True
    assert parsed_no_pre["file_id"] == "7"
    assert parse_mt_filename("bad.csv")["parse_ok"] is False


def test_train_test_file_id_isolation() -> None:
    assert TRAIN_FILES.isdisjoint(TEST_FILES)
    assert TRAIN_FILES == {"1", "2", "4", "5", "10"}
    assert TEST_FILES == {"7", "8"}


def test_four_channel_shape() -> None:
    path = next(iter(sorted(MT_DIR.glob("1_1_pre.csv"))))
    arr = np.genfromtxt(path, delimiter=",", skip_header=1, dtype=np.float32)
    assert arr.ndim == 2
    assert arr.shape[1] == len(MT_CHANNELS) == 4
    w = _windows(arr[: WIN_MT + STRIDE_MT])
    assert w.shape == (2, 4, WIN_MT)


def test_raw_class_id_name_consistency() -> None:
    for raw_id in RAW_CLASS_IDS:
        name = CLASS_ID_TO_NAME[raw_id]
        assert normalize_mt_class(raw_id) == name
        assert normalize_mt_class(name) == name
        assert class_name_to_raw_id(name) == raw_id
    assert normalize_mt_class("MT-3") == "base_imbalance"


def test_same_source_file_not_crossing_grouped_fold() -> None:
    files = []
    for path in sorted(MT_DIR.glob("*.csv")):
        parsed = parse_mt_filename(path)
        if parsed["parse_ok"] and parsed["file_id"] in TRAIN_FILES:
            files.append((path.name, parsed["file_id"]))
    for held in TRAIN_FILES:
        train_sources = {name for name, fid in files if fid != held}
        val_sources = {name for name, fid in files if fid == held}
        assert train_sources
        assert val_sources
        assert train_sources.isdisjoint(val_sources)


def test_exact_duplicate_detector() -> None:
    w = np.arange(4 * WIN_MT, dtype=np.float32).reshape(4, WIN_MT)
    h = window_hash(w)
    inv = pd.DataFrame(
        [
            {"split": "train", "sha256": "file_a", "class_name": "normal_machining", "file_name": "1_1_pre.csv"},
            {"split": "test", "sha256": "file_b", "class_name": "normal_machining", "file_name": "1_7.csv"},
        ]
    )
    records = [
        {
            "split": "train",
            "class_name": "normal_machining",
            "source_file": "1_1_pre.csv",
            "window_index": 0,
            "start": 0,
            "hash": h,
        },
        {
            "split": "test",
            "class_name": "normal_machining",
            "source_file": "1_7.csv",
            "window_index": 0,
            "start": 0,
            "hash": h,
        },
    ]
    rows = exact_duplicate_pairs(inv, records)
    assert any(r["duplicate_type"] == "window_train_test" for r in rows)


def test_output_schema_contract() -> None:
    expected = {
        "status",
        "class_mapping_confirmed",
        "exact_train_test_file_duplicates",
        "exact_train_test_window_duplicates",
        "metadata_confound_passed",
        "signal_learnability_passed",
        "cnn_learnability_passed",
        "allowed_next_stage",
        "reasons",
    }
    assert expected.issubset(set(DECISION_SCHEMA_KEYS))


def synthetic_train() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(123)
    xs, ys, files = [], [], []
    for ci, raw_id in enumerate(RAW_CLASS_IDS):
        for j in range(4):
            xs.append(rng.normal(loc=ci, scale=0.5, size=(4, WIN_MT)).astype(np.float32))
            ys.append(ci)
            files.append(f"{raw_id}_{j}")
    return np.stack(xs), np.asarray(ys, dtype=np.int64), np.asarray(files)


def test_verifier_load_save_consistency(tmp_path: Path) -> None:
    X, y, files = synthetic_train()
    verifier = MachineToolVerifier(coverage=0.90)
    verifier.calibrate(X, y, files)
    out = tmp_path / "mt_verifier.json"
    verifier.save(out)
    loaded = MachineToolVerifier.load(out)
    assert loaded.calib["schema"]["class_id_to_name"] == CLASS_ID_TO_NAME
    assert loaded.calib["schema"]["class_mapping_status"] == "confirmed_by_project_owner_2026-07-10"
    assert set(loaded.calib["classes"]) == set(MT_CLASSES)


def test_old_raw_id_input_compatible() -> None:
    X, y, files = synthetic_train()
    verifier = MachineToolVerifier(coverage=0.90)
    verifier.calibrate(X, y, files)
    report = verifier.verify(X[0], "1")
    assert report["class"] == "normal_machining"
    assert report["raw_class_id"] == "1"
    assert report["display_name"] == "Normal machining"
