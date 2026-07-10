"""Private machine-tool v1 preflight audit.

This is a zero-API, pre-preregistration audit for the private machine-tool
dataset. It does not generate synthetic data, does not tune on test files, and
does not use class prefixes, filenames, paths, labels, or result fields as
classifier inputs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "breeze" / "src"
sys.path.insert(0, str(SRC_DIR))

from config import RESULTS_DIR, RUNS_DIR  # noqa: E402
from data_mt import (  # noqa: E402
    CLASS_ID_TO_DISPLAY_NAME,
    CLASS_ID_TO_NAME,
    CLASS_MAPPING_CONFIRMED_DATE,
    CLASS_MAPPING_SOURCE,
    CLASS_MAPPING_STATUS,
    MT_CHANNELS,
    MT_CLASSES,
    MT_DIR,
    MT_SAMPLING_RATE_HZ,
    RAW_CLASS_IDS,
    STRIDE_MT,
    TEST_FILES,
    TRAIN_FILES,
    WIN_MT,
    parse_mt_filename,
)
from models import SimpleCNN  # noqa: E402


DATE_TAG = "2026-07-10"
RUN_NAME = f"mt_private_v1_preflight_{DATE_TAG}"
OUT_DIR = RESULTS_DIR / RUN_NAME
RUN_DIR = RUNS_DIR / RUN_NAME
TRAIN_FILE_IDS = sorted(TRAIN_FILES, key=lambda x: int(x))
TEST_FILE_IDS = sorted(TEST_FILES, key=lambda x: int(x))
N_REAL_VALUES = ["full", "10", "25", "50"]
N_REAL_NUMERIC = [10, 25, 50]
SEEDS = list(range(10))
CNN_EPOCHS = 20
DECISION_SCHEMA_KEYS = [
    "status",
    "class_mapping_confirmed",
    "exact_train_test_file_duplicates",
    "exact_train_test_window_duplicates",
    "metadata_confound_passed",
    "signal_learnability_passed",
    "cnn_learnability_passed",
    "allowed_next_stage",
    "reasons",
]


def ensure_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def append_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with path.open("a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        if new_file:
            writer.writeheader()
        writer.writerows(rows)


def done_keys(path: Path, keys: list[str]) -> set[tuple[str, ...]]:
    if not path.exists():
        return set()
    with path.open() as fh:
        return {tuple(str(row[k]) for k in keys) for row in csv.DictReader(fh)}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_signal_csv(path: Path) -> np.ndarray:
    arr = np.genfromtxt(path, delimiter=",", skip_header=1, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    return np.asarray(arr, dtype=np.float32)


def repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def resolve_record_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def split_for_file_id(file_id: str) -> str:
    if file_id in TRAIN_FILES:
        return "train"
    if file_id in TEST_FILES:
        return "test"
    return "unused"


def window_count(n_rows: int) -> int:
    n = (n_rows - WIN_MT) // STRIDE_MT + 1
    return max(int(n), 0)


def iter_windows(arr: np.ndarray) -> Iterable[tuple[int, int, int, np.ndarray]]:
    n = window_count(len(arr))
    for wi in range(n):
        start = wi * STRIDE_MT
        end = start + WIN_MT
        yield wi, start, end, arr[start:end].T.astype(np.float32, copy=False)


def inventory_rows() -> list[dict[str, Any]]:
    rows = []
    for path in sorted(MT_DIR.glob("*.csv")):
        parsed = parse_mt_filename(path)
        parse_ok = bool(parsed.get("parse_ok", False))
        arr = read_signal_csv(path)
        raw_id = str(parsed.get("raw_class_id", ""))
        file_id = str(parsed.get("file_id", ""))
        finite = bool(np.all(np.isfinite(arr)))
        row: dict[str, Any] = {
            "file_name": path.name,
            "path": repo_relative(path),
            "parse_ok": parse_ok,
            "raw_class_id": raw_id,
            "class_name": parsed.get("class_name", ""),
            "display_name": parsed.get("display_name", ""),
            "file_id": file_id,
            "split": split_for_file_id(file_id) if parse_ok else "invalid",
            "n_rows": int(arr.shape[0]),
            "n_cols": int(arr.shape[1]) if arr.ndim == 2 else 0,
            "window_count": window_count(int(arr.shape[0])),
            "sha256": sha256_file(path),
            "finite": finite,
            "nan_count": int(np.isnan(arr).sum()),
            "inf_count": int(np.isinf(arr).sum()),
            "size_bytes": int(path.stat().st_size),
        }
        if arr.ndim == 2 and arr.shape[1] == len(MT_CHANNELS):
            for ci, ch in enumerate(MT_CHANNELS):
                x = arr[:, ci]
                row[f"{ch}_mean"] = float(np.nanmean(x))
                row[f"{ch}_std"] = float(np.nanstd(x))
                row[f"{ch}_min"] = float(np.nanmin(x))
                row[f"{ch}_max"] = float(np.nanmax(x))
        rows.append(row)
    return rows


def write_class_mapping_doc() -> None:
    lines = [
        "# Private Machine-Tool Class Mapping",
        "",
        f"- Confirmed date: {CLASS_MAPPING_CONFIRMED_DATE}",
        f"- Mapping status: `{CLASS_MAPPING_STATUS}`",
        f"- Mapping source: {CLASS_MAPPING_SOURCE}",
        "- Evidence boundary: this mapping is confirmed by the project owner on 2026-07-10.",
        "- Evidence boundary: this mapping is not present in the published MechaForge PDF text.",
        "- Evidence boundary: labels are not inferred from waveforms.",
        "",
        "| Raw class ID | Canonical class name | Display name |",
        "|---|---|---|",
    ]
    for raw_id in RAW_CLASS_IDS:
        lines.append(
            f"| {raw_id} | `{CLASS_ID_TO_NAME[raw_id]}` | {CLASS_ID_TO_DISPLAY_NAME[raw_id]} |"
        )
    (OUT_DIR / "mt_private_class_mapping.md").write_text("\n".join(lines) + "\n")


def stage_inventory() -> None:
    ensure_dirs()
    write_class_mapping_doc()
    rows = inventory_rows()
    fields = [
        "file_name",
        "path",
        "parse_ok",
        "raw_class_id",
        "class_name",
        "display_name",
        "file_id",
        "split",
        "n_rows",
        "n_cols",
        "window_count",
        "sha256",
        "finite",
        "nan_count",
        "inf_count",
        "size_bytes",
    ]
    for ch in MT_CHANNELS:
        fields.extend([f"{ch}_mean", f"{ch}_std", f"{ch}_min", f"{ch}_max"])
    write_csv(OUT_DIR / "mt_private_file_inventory.csv", rows, fields)

    by_split = Counter(r["split"] for r in rows)
    by_class_split = Counter((r["split"], r["class_name"]) for r in rows)
    total_windows = sum(int(r["window_count"]) for r in rows)
    train_windows = sum(int(r["window_count"]) for r in rows if r["split"] == "train")
    test_windows = sum(int(r["window_count"]) for r in rows if r["split"] == "test")
    bad_shape = [r for r in rows if r["n_cols"] != len(MT_CHANNELS)]
    bad_finite = [r for r in rows if not r["finite"]]
    lines = [
        "# Private Machine-Tool File Inventory",
        "",
        "This inventory is a zero-API preflight audit. Test files are only listed for",
        "integrity and leakage checks, not for parameter or feature selection.",
        "",
        f"- CSV files scanned: {len(rows)}",
        f"- Channels expected: {MT_CHANNELS}",
        f"- Sampling rate: {MT_SAMPLING_RATE_HZ:g} Hz",
        f"- Window/stride: {WIN_MT}/{STRIDE_MT}",
        f"- Train file IDs: {TRAIN_FILE_IDS}",
        f"- Test file IDs: {TEST_FILE_IDS}",
        f"- Files by split: {dict(by_split)}",
        f"- Total windows: {total_windows}",
        f"- Train windows: {train_windows}",
        f"- Test windows: {test_windows}",
        f"- Bad-shape files: {len(bad_shape)}",
        f"- Non-finite files: {len(bad_finite)}",
        "",
        "## Files By Split And Class",
        "",
        "| Split | Class | Files |",
        "|---|---|---:|",
    ]
    for key, count in sorted(by_class_split.items()):
        lines.append(f"| {key[0]} | {key[1]} | {count} |")
    (OUT_DIR / "mt_private_file_inventory_report.md").write_text("\n".join(lines) + "\n")


def load_inventory() -> pd.DataFrame:
    path = OUT_DIR / "mt_private_file_inventory.csv"
    if not path.exists():
        stage_inventory()
    return pd.read_csv(path)


def stage_split_audit() -> None:
    ensure_dirs()
    inv = load_inventory()
    rows: list[dict[str, Any]] = []
    for rec in inv.to_dict("records"):
        if rec["split"] not in {"train", "test"}:
            continue
        arr = read_signal_csv(resolve_record_path(str(rec["path"])))
        for wi, start, end, _ in iter_windows(arr):
            rows.append(
                {
                    "sample_id": f"{rec['raw_class_id']}_{rec['file_id']}_w{wi:04d}",
                    "split": rec["split"],
                    "raw_class_id": rec["raw_class_id"],
                    "class_name": rec["class_name"],
                    "display_name": rec["display_name"],
                    "source_file": rec["file_name"],
                    "file_id": rec["file_id"],
                    "window_index": wi,
                    "start": start,
                    "end": end,
                    "n_rows": int(rec["n_rows"]),
                    "window_count_in_file": int(rec["window_count"]),
                }
            )
    write_csv(
        OUT_DIR / "mt_private_split_manifest.csv",
        rows,
        [
            "sample_id",
            "split",
            "raw_class_id",
            "class_name",
            "display_name",
            "source_file",
            "file_id",
            "window_index",
            "start",
            "end",
            "n_rows",
            "window_count_in_file",
        ],
    )


def load_split_manifest() -> pd.DataFrame:
    path = OUT_DIR / "mt_private_split_manifest.csv"
    if not path.exists():
        stage_split_audit()
    return pd.read_csv(path)


def window_hash(w: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(w).tobytes()).hexdigest()


def window_embedding(w: np.ndarray) -> np.ndarray:
    x = w.astype(np.float32, copy=False)
    x = x - x.mean(axis=1, keepdims=True)
    x = x / (x.std(axis=1, keepdims=True) + 1e-8)
    emb = x[:, ::32].reshape(-1)
    norm = float(np.linalg.norm(emb))
    if norm <= 1e-12:
        return np.zeros_like(emb, dtype=np.float32)
    return (emb / norm).astype(np.float32)


def build_window_records(inv: pd.DataFrame) -> tuple[list[dict[str, Any]], np.ndarray]:
    records: list[dict[str, Any]] = []
    embeds = []
    for rec in inv.to_dict("records"):
        if rec["split"] not in {"train", "test"}:
            continue
        arr = read_signal_csv(resolve_record_path(str(rec["path"])))
        for wi, start, end, w in iter_windows(arr):
            records.append(
                {
                    "split": rec["split"],
                    "raw_class_id": str(rec["raw_class_id"]),
                    "class_name": rec["class_name"],
                    "display_name": rec["display_name"],
                    "source_file": rec["file_name"],
                    "file_id": str(rec["file_id"]),
                    "window_index": wi,
                    "start": start,
                    "end": end,
                    "hash": window_hash(w),
                }
            )
            embeds.append(window_embedding(w))
    return records, np.vstack(embeds).astype(np.float32)


def exact_duplicate_pairs(inv: pd.DataFrame, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    train_files = inv[inv["split"] == "train"].to_dict("records")
    test_files = inv[inv["split"] == "test"].to_dict("records")
    for tr in train_files:
        for te in test_files:
            if tr["sha256"] == te["sha256"]:
                rows.append(
                    {
                        "duplicate_type": "raw_file_train_test",
                        "left_split": "train",
                        "left_class": tr["class_name"],
                        "left_file": tr["file_name"],
                        "left_window_index": "",
                        "left_start": "",
                        "right_split": "test",
                        "right_class": te["class_name"],
                        "right_file": te["file_name"],
                        "right_window_index": "",
                        "right_start": "",
                        "sha256": tr["sha256"],
                    }
                )
    by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        by_hash[str(rec["hash"])].append(rec)
    for h, group in by_hash.items():
        trains = [r for r in group if r["split"] == "train"]
        tests = [r for r in group if r["split"] == "test"]
        for tr in trains:
            for te in tests:
                rows.append(
                    {
                        "duplicate_type": "window_train_test",
                        "left_split": "train",
                        "left_class": tr["class_name"],
                        "left_file": tr["source_file"],
                        "left_window_index": tr["window_index"],
                        "left_start": tr["start"],
                        "right_split": "test",
                        "right_class": te["class_name"],
                        "right_file": te["source_file"],
                        "right_window_index": te["window_index"],
                        "right_start": te["start"],
                        "sha256": h,
                    }
                )
    return rows


def quantiles(values: np.ndarray) -> dict[str, float]:
    if len(values) == 0:
        return {"min": math.nan, "q05": math.nan, "median": math.nan, "q95": math.nan, "max": math.nan}
    return {
        "min": float(np.min(values)),
        "q05": float(np.quantile(values, 0.05)),
        "median": float(np.quantile(values, 0.50)),
        "q95": float(np.quantile(values, 0.95)),
        "max": float(np.max(values)),
    }


def nearest_pairs(records: list[dict[str, Any]], embeds: np.ndarray) -> tuple[list[dict[str, Any]], dict[str, dict[str, float]]]:
    split = np.asarray([r["split"] for r in records])
    cls = np.asarray([r["class_name"] for r in records])
    src = np.asarray([r["source_file"] for r in records])
    train_idx = np.where(split == "train")[0]
    test_idx = np.where(split == "test")[0]
    sim = embeds @ embeds.T
    nearest_train_test_rows = []
    for ti in test_idx:
        sims = sim[ti, train_idx]
        best_pos = int(np.argmax(sims))
        bi = int(train_idx[best_pos])
        left = records[bi]
        right = records[int(ti)]
        corr = float(sims[best_pos])
        nearest_train_test_rows.append(
            {
                "pair_type": "nearest_train_to_test_window",
                "train_split": left["split"],
                "train_class": left["class_name"],
                "train_file": left["source_file"],
                "train_window_index": left["window_index"],
                "train_start": left["start"],
                "test_split": right["split"],
                "test_class": right["class_name"],
                "test_file": right["source_file"],
                "test_window_index": right["window_index"],
                "test_start": right["start"],
                "cosine_similarity": corr,
                "cosine_distance": 1.0 - corr,
            }
        )

    same_vals = []
    diff_vals = []
    for i in range(len(records)):
        cross_file = src != src[i]
        same_class = cls == cls[i]
        diff_class = cls != cls[i]
        mask_same = cross_file & same_class
        mask_diff = cross_file & diff_class
        if np.any(mask_same):
            same_vals.append(float(np.max(sim[i, mask_same])))
        if np.any(mask_diff):
            diff_vals.append(float(np.max(sim[i, mask_diff])))
    stats = {
        "nearest_train_test_cosine": quantiles(np.asarray([r["cosine_similarity"] for r in nearest_train_test_rows])),
        "same_class_cross_file_cosine": quantiles(np.asarray(same_vals, dtype=float)),
        "different_class_cross_file_cosine": quantiles(np.asarray(diff_vals, dtype=float)),
    }
    return nearest_train_test_rows, stats


def stage_duplicate_audit() -> None:
    ensure_dirs()
    inv = load_inventory()
    records, embeds = build_window_records(inv)
    exact_rows = exact_duplicate_pairs(inv, records)
    exact_fields = [
        "duplicate_type",
        "left_split",
        "left_class",
        "left_file",
        "left_window_index",
        "left_start",
        "right_split",
        "right_class",
        "right_file",
        "right_window_index",
        "right_start",
        "sha256",
    ]
    write_csv(OUT_DIR / "mt_private_exact_duplicate_pairs.csv", exact_rows, exact_fields)
    nearest_rows, near_stats = nearest_pairs(records, embeds)
    nearest_fields = [
        "pair_type",
        "train_split",
        "train_class",
        "train_file",
        "train_window_index",
        "train_start",
        "test_split",
        "test_class",
        "test_file",
        "test_window_index",
        "test_start",
        "cosine_similarity",
        "cosine_distance",
    ]
    write_csv(OUT_DIR / "mt_private_nearest_train_test_pairs.csv", nearest_rows, nearest_fields)

    exact_raw = sum(1 for r in exact_rows if r["duplicate_type"] == "raw_file_train_test")
    exact_win = sum(1 for r in exact_rows if r["duplicate_type"] == "window_train_test")
    lines = [
        "# Private Machine-Tool Duplicate Audit",
        "",
        "Exact train/test duplicates are treated as integrity blockers. High nearest-neighbor",
        "cosine similarity is reported as a diagnostic and is not equated with leakage.",
        "",
        f"- Exact raw train/test duplicate files: {exact_raw}",
        f"- Exact train/test duplicate windows: {exact_win}",
        f"- Windows embedded for near-duplicate diagnostics: {len(records)}",
        "",
        "## Near-Duplicate Distribution",
        "",
        "| Diagnostic | min | q05 | median | q95 | max |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, qs in near_stats.items():
        lines.append(
            f"| {name} | {qs['min']:.6f} | {qs['q05']:.6f} | {qs['median']:.6f} | "
            f"{qs['q95']:.6f} | {qs['max']:.6f} |"
        )
    (OUT_DIR / "mt_private_duplicate_audit.md").write_text("\n".join(lines) + "\n")


def mt_label_index(class_name: str) -> int:
    return MT_CLASSES.index(class_name)


def robust_channel_stats(x: np.ndarray) -> list[float]:
    x = np.asarray(x, dtype=np.float64)
    mean = float(np.mean(x))
    std = float(np.std(x) + 1e-12)
    centered = x - mean
    rms = float(np.sqrt(np.mean(x * x)))
    peak = float(np.max(np.abs(x)))
    ptp = float(np.ptp(x))
    skew = float(np.mean((centered / std) ** 3))
    kurt = float(np.mean((centered / std) ** 4))
    crest = float(peak / (rms + 1e-12))
    q25, q50, q75 = np.quantile(x, [0.25, 0.50, 0.75])
    return [mean, std, rms, peak, ptp, skew, kurt, crest, float(q25), float(q50), float(q75)]


def psd_band_features(x: np.ndarray, n_bands: int = 8) -> list[float]:
    x = np.asarray(x, dtype=np.float64)
    x = x - np.mean(x)
    p = np.abs(np.fft.rfft(x)) ** 2
    p[0] = 0.0
    total = float(p.sum() + 1e-30)
    bands = np.array_split(p, n_bands)
    vals = [float(b.sum() / total) for b in bands]
    freqs = np.linspace(0.0, 0.5, len(p))
    prob = p / total
    centroid = float(np.sum(freqs * prob))
    spread = float(np.sqrt(np.sum(((freqs - centroid) ** 2) * prob)))
    entropy = float(-np.sum(prob * np.log(prob + 1e-30)) / math.log(max(len(prob), 2)))
    return vals + [centroid, spread, entropy]


def signal_feature_names() -> list[str]:
    names = []
    stat_names = ["mean", "std", "rms", "peak", "ptp", "skew", "kurt", "crest", "q25", "q50", "q75"]
    for ch in MT_CHANNELS:
        names.extend([f"{ch}_{name}" for name in stat_names])
        names.extend([f"{ch}_psd_band_{i}" for i in range(8)])
        names.extend([f"{ch}_psd_centroid", f"{ch}_psd_spread", f"{ch}_psd_entropy"])
    for i, ch_i in enumerate(MT_CHANNELS):
        for j, ch_j in enumerate(MT_CHANNELS):
            if j > i:
                names.append(f"corr_{ch_i}_{ch_j}")
    return names


def signal_feature_vector(w: np.ndarray) -> np.ndarray:
    feats: list[float] = []
    for ch in range(len(MT_CHANNELS)):
        feats.extend(robust_channel_stats(w[ch]))
        feats.extend(psd_band_features(w[ch]))
    corr = np.corrcoef(w)
    corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0)
    for i in range(len(MT_CHANNELS)):
        for j in range(i + 1, len(MT_CHANNELS)):
            feats.append(float(corr[i, j]))
    return np.nan_to_num(np.asarray(feats, dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0)


def build_train_file_table(inv: pd.DataFrame) -> pd.DataFrame:
    return inv[inv["split"] == "train"].copy().reset_index(drop=True)


def file_signal_features(path: Path) -> np.ndarray:
    arr = read_signal_csv(path)
    return signal_feature_vector(arr.T.astype(np.float32, copy=False))


def train_windows_with_metadata(inv: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    rows = []
    wins = []
    ys = []
    for rec in inv[inv["split"] == "train"].to_dict("records"):
        arr = read_signal_csv(resolve_record_path(str(rec["path"])))
        for wi, start, end, w in iter_windows(arr):
            wins.append(w)
            ys.append(mt_label_index(str(rec["class_name"])))
            rows.append(
                {
                    "class_name": rec["class_name"],
                    "raw_class_id": rec["raw_class_id"],
                    "display_name": rec["display_name"],
                    "source_file": rec["file_name"],
                    "file_id": str(rec["file_id"]),
                    "window_index": wi,
                    "start": start,
                    "end": end,
                    "n_rows": int(rec["n_rows"]),
                    "window_count_in_file": int(rec["window_count"]),
                    "norm_start": start / max(int(rec["n_rows"]) - WIN_MT, 1),
                    "norm_end": end / max(int(rec["n_rows"]), 1),
                }
            )
    return np.stack(wins).astype(np.float32), np.asarray(ys, dtype=np.int64), pd.DataFrame(rows)


def metrics_row(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    labels = list(range(len(MT_CLASSES)))
    per = f1_score(y_true, y_pred, average=None, labels=labels, zero_division=0)
    return {
        "acc": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", labels=labels, zero_division=0)),
        **{f"f1_{MT_CLASSES[i]}": float(per[i]) for i in range(len(MT_CLASSES))},
        "confusion": json.dumps(confusion_matrix(y_true, y_pred, labels=labels).tolist(), separators=(",", ":")),
    }


def majority_predict(y_train: np.ndarray, n: int) -> np.ndarray:
    counts = np.bincount(y_train, minlength=len(MT_CLASSES))
    return np.full(n, int(np.argmax(counts)), dtype=np.int64)


def fit_predict_features(model_name: str, X_train: np.ndarray, y_train: np.ndarray, X_val: np.ndarray) -> np.ndarray:
    if model_name == "majority":
        return majority_predict(y_train, len(X_val))
    if model_name == "logistic_regression":
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=2000, class_weight="balanced", random_state=0),
        )
    elif model_name == "extra_trees":
        model = ExtraTreesClassifier(
            n_estimators=300,
            max_features="sqrt",
            class_weight="balanced",
            random_state=0,
            n_jobs=-1,
        )
    else:
        raise ValueError(model_name)
    model.fit(X_train, y_train)
    return model.predict(X_val)


def lofo_file_level_rows(X: np.ndarray, y: np.ndarray, file_ids: np.ndarray, baseline: str, model_name: str) -> list[dict[str, Any]]:
    rows = []
    for held in TRAIN_FILE_IDS:
        train_mask = file_ids != held
        val_mask = file_ids == held
        pred = fit_predict_features(model_name, X[train_mask], y[train_mask], X[val_mask])
        row = {
            "baseline": baseline,
            "model": model_name,
            "fold": f"file_id_{held}",
            "heldout_file_id": held,
            "n_train": int(train_mask.sum()),
            "n_val": int(val_mask.sum()),
        }
        row.update(metrics_row(y[val_mask], pred))
        rows.append(row)
    return rows


def summarize_metric_rows(rows: list[dict[str, Any]], group_cols: list[str]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    out = []
    if df.empty:
        return out
    metrics = ["acc", "macro_f1"] + [f"f1_{c}" for c in MT_CLASSES]
    for keys, sub in df.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = {col: key for col, key in zip(group_cols, keys, strict=True)}
        row["folds"] = int(sub["fold"].nunique()) if "fold" in sub else int(len(sub))
        for metric in metrics:
            vals = pd.to_numeric(sub[metric], errors="coerce")
            row[f"mean_{metric}"] = float(vals.mean())
            row[f"worst_{metric}"] = float(vals.min())
        out.append(row)
    return out


def stage_confound_audit() -> None:
    ensure_dirs()
    inv = load_inventory()
    train_files = build_train_file_table(inv)
    y_file = np.asarray([mt_label_index(c) for c in train_files["class_name"]], dtype=np.int64)
    file_ids = train_files["file_id"].astype(str).to_numpy()

    safe_X = train_files[["file_id", "n_rows", "window_count", "size_bytes"]].astype(float).to_numpy()
    acq_X = train_files[["file_id"]].astype(float).to_numpy()
    file_signal_X = np.vstack([file_signal_features(resolve_record_path(p)) for p in train_files["path"]])

    metadata_rows = []
    metadata_rows.extend(lofo_file_level_rows(safe_X, y_file, file_ids, "metadata_safe", "logistic_regression"))
    metadata_rows.extend(lofo_file_level_rows(safe_X, y_file, file_ids, "metadata_safe", "extra_trees"))
    metadata_rows.extend(lofo_file_level_rows(acq_X, y_file, file_ids, "acquisition_index", "logistic_regression"))
    metadata_rows.extend(lofo_file_level_rows(acq_X, y_file, file_ids, "acquisition_index", "extra_trees"))
    write_csv(
        OUT_DIR / "mt_private_metadata_audit.csv",
        metadata_rows,
        [
            "baseline",
            "model",
            "fold",
            "heldout_file_id",
            "n_train",
            "n_val",
            "acc",
            "macro_f1",
            *[f"f1_{c}" for c in MT_CLASSES],
            "confusion",
        ],
    )

    file_rows = lofo_file_level_rows(file_signal_X, y_file, file_ids, "file_level_signal_features", "extra_trees")
    write_csv(
        OUT_DIR / "mt_private_file_level_feature_audit.csv",
        file_rows,
        [
            "baseline",
            "model",
            "fold",
            "heldout_file_id",
            "n_train",
            "n_val",
            "acc",
            "macro_f1",
            *[f"f1_{c}" for c in MT_CLASSES],
            "confusion",
        ],
    )

    _, y_win, meta = train_windows_with_metadata(inv)
    pos_X = meta[["norm_start", "norm_end", "n_rows", "window_count_in_file"]].astype(float).to_numpy()
    win_file_ids = meta["file_id"].astype(str).to_numpy()
    pos_rows = lofo_file_level_rows(pos_X, y_win, win_file_ids, "window_position_only", "extra_trees")
    write_csv(
        OUT_DIR / "mt_private_window_position_audit.csv",
        pos_rows,
        [
            "baseline",
            "model",
            "fold",
            "heldout_file_id",
            "n_train",
            "n_val",
            "acc",
            "macro_f1",
            *[f"f1_{c}" for c in MT_CLASSES],
            "confusion",
        ],
    )

    meta_summary = summarize_metric_rows(metadata_rows, ["baseline", "model"])
    file_summary = summarize_metric_rows(file_rows, ["baseline", "model"])
    pos_summary = summarize_metric_rows(pos_rows, ["baseline", "model"])
    lines = [
        "# Private Machine-Tool Confound Audit",
        "",
        "All diagnostics in this file use train-only leave-one-file-ID-out folds.",
        "Class prefixes, filenames, source paths, labels, and test files are not classifier inputs.",
        "",
        "## Metadata Diagnostics",
        "",
        "| Baseline | Model | Mean Macro-F1 | Worst Macro-F1 |",
        "|---|---|---:|---:|",
    ]
    for row in meta_summary:
        lines.append(
            f"| {row['baseline']} | {row['model']} | {row['mean_macro_f1']:.4f} | "
            f"{row['worst_macro_f1']:.4f} |"
        )
    lines.extend(["", "## Window Position Diagnostic", "", "| Baseline | Model | Mean Macro-F1 | Worst Macro-F1 |", "|---|---|---:|---:|"])
    for row in pos_summary:
        lines.append(
            f"| {row['baseline']} | {row['model']} | {row['mean_macro_f1']:.4f} | "
            f"{row['worst_macro_f1']:.4f} |"
        )
    lines.extend(["", "## File-Level Signal Diagnostic", "", "| Baseline | Model | Mean Macro-F1 | Worst Macro-F1 |", "|---|---|---:|---:|"])
    for row in file_summary:
        lines.append(
            f"| {row['baseline']} | {row['model']} | {row['mean_macro_f1']:.4f} | "
            f"{row['worst_macro_f1']:.4f} |"
        )
    (OUT_DIR / "mt_private_confound_audit.md").write_text("\n".join(lines) + "\n")


def sample_n_per_class(
    y: np.ndarray,
    train_indices: np.ndarray,
    n_per_class: int | None,
    seed: int,
) -> np.ndarray:
    if n_per_class is None:
        return train_indices
    rng = np.random.default_rng(seed)
    keep = []
    for ci in range(len(MT_CLASSES)):
        idx = train_indices[y[train_indices] == ci]
        if len(idx) == 0:
            continue
        choose = min(n_per_class, len(idx))
        keep.extend(rng.choice(idx, choose, replace=False).tolist())
    return np.asarray(sorted(keep), dtype=int)


def train_feature_matrix(X_win: np.ndarray) -> np.ndarray:
    return np.vstack([signal_feature_vector(w) for w in X_win]).astype(np.float32)


def confusion_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        cm = json.loads(row["confusion"])
        for i, true_cls in enumerate(MT_CLASSES):
            for j, pred_cls in enumerate(MT_CLASSES):
                out.append(
                    {
                        "source_csv": row.get("source_csv", ""),
                        "baseline": row["baseline"],
                        "model": row["model"],
                        "n_real": row["n_real"],
                        "seed": row["seed"],
                        "fold": row["fold"],
                        "heldout_file_id": row["heldout_file_id"],
                        "true_class": true_cls,
                        "pred_class": pred_cls,
                        "count": int(cm[i][j]),
                    }
                )
    return out


def stage_learnability_features() -> None:
    ensure_dirs()
    out = OUT_DIR / "mt_private_trainonly_lofo_features.csv"
    fields = [
        "baseline",
        "model",
        "n_real",
        "seed",
        "fold",
        "heldout_file_id",
        "n_train",
        "n_val",
        "acc",
        "macro_f1",
        *[f"f1_{c}" for c in MT_CLASSES],
        "confusion",
    ]
    done = done_keys(out, ["baseline", "model", "n_real", "seed", "fold"])

    inv = load_inventory()
    X_win, y, meta = train_windows_with_metadata(inv)
    X_feat = train_feature_matrix(X_win)
    file_ids = meta["file_id"].astype(str).to_numpy()
    pos_X = meta[["norm_start", "norm_end", "n_rows", "window_count_in_file"]].astype(float).to_numpy()
    rows_to_append: list[dict[str, Any]] = []

    for held in TRAIN_FILE_IDS:
        train_idx = np.where(file_ids != held)[0]
        val_idx = np.where(file_ids == held)[0]
        for baseline, model_name, Xmat in [
            ("majority", "majority", X_feat),
            ("window_position_only", "extra_trees", pos_X),
        ]:
            key = (baseline, model_name, "full", "0", f"file_id_{held}")
            if key not in done:
                pred = fit_predict_features(model_name, Xmat[train_idx], y[train_idx], Xmat[val_idx])
                row = {
                    "baseline": baseline,
                    "model": model_name,
                    "n_real": "full",
                    "seed": 0,
                    "fold": f"file_id_{held}",
                    "heldout_file_id": held,
                    "n_train": int(len(train_idx)),
                    "n_val": int(len(val_idx)),
                }
                row.update(metrics_row(y[val_idx], pred))
                rows_to_append.append(row)

        for n_real in [None, *N_REAL_NUMERIC]:
            n_label = "full" if n_real is None else str(n_real)
            seeds = [0] if n_real is None else SEEDS
            for seed in seeds:
                key = ("signal_feature_only", "extra_trees", n_label, str(seed), f"file_id_{held}")
                if key in done:
                    continue
                chosen = sample_n_per_class(y, train_idx, n_real, seed=10000 + int(held) * 100 + seed)
                pred = fit_predict_features("extra_trees", X_feat[chosen], y[chosen], X_feat[val_idx])
                row = {
                    "baseline": "signal_feature_only",
                    "model": "extra_trees",
                    "n_real": n_label,
                    "seed": seed,
                    "fold": f"file_id_{held}",
                    "heldout_file_id": held,
                    "n_train": int(len(chosen)),
                    "n_val": int(len(val_idx)),
                }
                row.update(metrics_row(y[val_idx], pred))
                rows_to_append.append(row)
                if len(rows_to_append) >= 20:
                    append_csv(out, rows_to_append, fields)
                    rows_to_append = []
    if rows_to_append:
        append_csv(out, rows_to_append, fields)


def normalize_windows(train: np.ndarray, val: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = train.mean(axis=(0, 2), keepdims=True)
    std = train.std(axis=(0, 2), keepdims=True) + 1e-8
    return (train - mean) / std, (val - mean) / std


def fit_cnn(X_train: np.ndarray, y_train: np.ndarray, seed: int, epochs: int) -> SimpleCNN:
    torch.manual_seed(seed)
    model = SimpleCNN(in_ch=len(MT_CHANNELS), num_classes=len(MT_CLASSES))
    opt = torch.optim.Adam(model.parameters(), lr=3e-4, weight_decay=1e-4)
    crit = nn.CrossEntropyLoss()
    Xt = torch.tensor(X_train, dtype=torch.float32)
    yt = torch.tensor(y_train, dtype=torch.long)
    generator = torch.Generator().manual_seed(seed)
    model.train()
    for _ in range(epochs):
        perm = torch.randperm(len(Xt), generator=generator)
        for start in range(0, len(Xt), 32):
            idx = perm[start:start + 32]
            opt.zero_grad()
            loss = crit(model(Xt[idx]), yt[idx])
            loss.backward()
            opt.step()
    return model


def predict_cnn(model: SimpleCNN, X_val: np.ndarray) -> np.ndarray:
    model.eval()
    preds = []
    with torch.no_grad():
        Xt = torch.tensor(X_val, dtype=torch.float32)
        for start in range(0, len(Xt), 256):
            preds.append(model(Xt[start:start + 256]).argmax(1).cpu().numpy())
    return np.concatenate(preds)


def stage_learnability_cnn() -> None:
    ensure_dirs()
    out = OUT_DIR / "mt_private_trainonly_lofo_cnn.csv"
    fields = [
        "baseline",
        "model",
        "n_real",
        "seed",
        "epochs",
        "fold",
        "heldout_file_id",
        "n_train",
        "n_val",
        "acc",
        "macro_f1",
        *[f"f1_{c}" for c in MT_CLASSES],
        "confusion",
    ]
    done = done_keys(out, ["baseline", "model", "n_real", "seed", "fold", "epochs"])

    inv = load_inventory()
    X_win, y, meta = train_windows_with_metadata(inv)
    file_ids = meta["file_id"].astype(str).to_numpy()
    rows_to_append: list[dict[str, Any]] = []
    for held in TRAIN_FILE_IDS:
        base_train_idx = np.where(file_ids != held)[0]
        val_idx = np.where(file_ids == held)[0]
        for n_real in [None, *N_REAL_NUMERIC]:
            n_label = "full" if n_real is None else str(n_real)
            seeds = [0] if n_real is None else SEEDS
            for seed in seeds:
                key = ("real_only", "simple_cnn", n_label, str(seed), f"file_id_{held}", str(CNN_EPOCHS))
                if key in done:
                    continue
                train_idx = sample_n_per_class(y, base_train_idx, n_real, seed=20000 + int(held) * 100 + seed)
                Xtr, Xva = normalize_windows(X_win[train_idx], X_win[val_idx])
                model = fit_cnn(Xtr, y[train_idx], seed=seed, epochs=CNN_EPOCHS)
                pred = predict_cnn(model, Xva)
                row = {
                    "baseline": "real_only",
                    "model": "simple_cnn",
                    "n_real": n_label,
                    "seed": seed,
                    "epochs": CNN_EPOCHS,
                    "fold": f"file_id_{held}",
                    "heldout_file_id": held,
                    "n_train": int(len(train_idx)),
                    "n_val": int(len(val_idx)),
                }
                row.update(metrics_row(y[val_idx], pred))
                rows_to_append.append(row)
                if len(rows_to_append) >= 10:
                    append_csv(out, rows_to_append, fields)
                    rows_to_append = []
    if rows_to_append:
        append_csv(out, rows_to_append, fields)


def stage_learnability() -> None:
    stage_learnability_features()
    stage_learnability_cnn()
    summarize_learnability()


def summarize_learnability() -> None:
    feature_path = OUT_DIR / "mt_private_trainonly_lofo_features.csv"
    cnn_path = OUT_DIR / "mt_private_trainonly_lofo_cnn.csv"
    rows: list[dict[str, Any]] = []
    conf_rows: list[dict[str, Any]] = []
    if feature_path.exists():
        fdf = pd.read_csv(feature_path)
        rows.extend(fdf.to_dict("records"))
        feature_records = fdf.to_dict("records")
        for r in feature_records:
            r["source_csv"] = feature_path.name
        conf_rows.extend(confusion_rows(feature_records))
    if cnn_path.exists():
        cdf = pd.read_csv(cnn_path)
        rows.extend(cdf.to_dict("records"))
        cnn_records = cdf.to_dict("records")
        for r in cnn_records:
            r["source_csv"] = cnn_path.name
        conf_rows.extend(confusion_rows(cnn_records))
    summary = summarize_metric_rows(rows, ["baseline", "model", "n_real"])
    write_csv(
        OUT_DIR / "mt_private_trainonly_lofo_summary.csv",
        summary,
        [
            "baseline",
            "model",
            "n_real",
            "folds",
            "mean_acc",
            "worst_acc",
            "mean_macro_f1",
            "worst_macro_f1",
            *[f"mean_f1_{c}" for c in MT_CLASSES],
            *[f"worst_f1_{c}" for c in MT_CLASSES],
        ],
    )
    write_csv(
        OUT_DIR / "mt_private_trainonly_lofo_confusions.csv",
        conf_rows,
        [
            "source_csv",
            "baseline",
            "model",
            "n_real",
            "seed",
            "fold",
            "heldout_file_id",
            "true_class",
            "pred_class",
            "count",
        ],
    )

    lines = [
        "# Private Machine-Tool Train-Only LOFO Learnability",
        "",
        "All rows use train files only and leave one file ID out at a time. File IDs 7/8",
        "are not used for model selection, thresholding, feature selection, or parameter",
        "selection in this audit.",
        "",
        "| Baseline | Model | n_real | Mean Acc | Mean Macro-F1 | Worst Macro-F1 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['baseline']} | {row['model']} | {row['n_real']} | "
            f"{row['mean_acc']:.4f} | {row['mean_macro_f1']:.4f} | {row['worst_macro_f1']:.4f} |"
        )
    (OUT_DIR / "mt_private_learnability_report.md").write_text("\n".join(lines) + "\n")


def read_summary_row(baseline: str, model: str, n_real: str) -> dict[str, Any] | None:
    path = OUT_DIR / "mt_private_trainonly_lofo_summary.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    sub = df[
        (df["baseline"].astype(str) == baseline)
        & (df["model"].astype(str) == model)
        & (df["n_real"].astype(str) == n_real)
    ]
    if sub.empty:
        return None
    return sub.iloc[0].to_dict()


def preflight_decision() -> dict[str, Any]:
    inv = load_inventory()
    exact_path = OUT_DIR / "mt_private_exact_duplicate_pairs.csv"
    exact = pd.read_csv(exact_path) if exact_path.exists() else pd.DataFrame()
    exact_raw = int((exact.get("duplicate_type", pd.Series(dtype=str)) == "raw_file_train_test").sum())
    exact_win = int((exact.get("duplicate_type", pd.Series(dtype=str)) == "window_train_test").sum())
    bad_shape = int((inv["n_cols"] != len(MT_CHANNELS)).sum())
    bad_finite = int((inv["finite"].astype(str) != "True").sum())

    meta = pd.read_csv(OUT_DIR / "mt_private_metadata_audit.csv") if (OUT_DIR / "mt_private_metadata_audit.csv").exists() else pd.DataFrame()
    pos = pd.read_csv(OUT_DIR / "mt_private_window_position_audit.csv") if (OUT_DIR / "mt_private_window_position_audit.csv").exists() else pd.DataFrame()
    safe_mean = float(
        meta[
            (meta["baseline"] == "metadata_safe") & (meta["model"] == "extra_trees")
        ]["macro_f1"].mean()
    ) if not meta.empty else math.nan
    pos_mean = float(pos["macro_f1"].mean()) if not pos.empty else math.nan

    signal = read_summary_row("signal_feature_only", "extra_trees", "full")
    cnn = read_summary_row("real_only", "simple_cnn", "full")
    signal_mean = float(signal["mean_macro_f1"]) if signal else math.nan
    signal_worst = float(signal["worst_macro_f1"]) if signal else math.nan
    signal_per_class = [
        float(signal[f"mean_f1_{c}"]) for c in MT_CLASSES
    ] if signal else []
    cnn_mean = float(cnn["mean_macro_f1"]) if cnn else math.nan

    class_support_ok = True
    reasons: list[str] = []
    for split in ["train", "test"]:
        sub = inv[inv["split"] == split]
        counts = sub.groupby("class_name")["file_name"].count().to_dict()
        for cls in MT_CLASSES:
            if counts.get(cls, 0) == 0:
                class_support_ok = False
                reasons.append(f"{split} has no files for {cls}")
    for held in TRAIN_FILE_IDS:
        train_counts = inv[(inv["split"] == "train") & (inv["file_id"].astype(str) != held)].groupby("class_name")["file_name"].count().to_dict()
        val_counts = inv[(inv["split"] == "train") & (inv["file_id"].astype(str) == held)].groupby("class_name")["file_name"].count().to_dict()
        for cls in MT_CLASSES:
            if train_counts.get(cls, 0) == 0 or val_counts.get(cls, 0) == 0:
                class_support_ok = False
                reasons.append(f"LOFO file_id={held} lacks train/val support for {cls}")

    integrity_ok = bad_shape == 0 and bad_finite == 0 and exact_raw == 0 and exact_win == 0
    if bad_shape:
        reasons.append(f"{bad_shape} files do not match the four-channel schema")
    if bad_finite:
        reasons.append(f"{bad_finite} files contain NaN/Inf")
    if exact_raw:
        reasons.append(f"{exact_raw} exact train/test raw-file duplicates")
    if exact_win:
        reasons.append(f"{exact_win} exact train/test window duplicates")

    metadata_ok = safe_mean < 0.80 and pos_mean < 0.80
    if not math.isnan(safe_mean) and safe_mean >= 0.80:
        reasons.append(f"metadata_safe macro-F1 is high-risk: {safe_mean:.4f}")
    if not math.isnan(pos_mean) and pos_mean >= 0.80:
        reasons.append(f"window_position_only macro-F1 is high-risk: {pos_mean:.4f}")

    signal_ok = (
        signal is not None
        and signal_mean >= 0.60
        and signal_worst >= 0.45
        and all(v >= 0.45 for v in signal_per_class)
    )
    cnn_ok = cnn is not None and cnn_mean >= 0.60
    if signal is None:
        reasons.append("missing signal-feature train-only LOFO summary")
    elif not signal_ok:
        reasons.append(
            f"signal-feature gate failed: mean={signal_mean:.4f}, worst={signal_worst:.4f}, "
            f"per_class={signal_per_class}"
        )
    if cnn is None:
        reasons.append("missing SimpleCNN train-only LOFO summary")
    elif not cnn_ok:
        reasons.append(f"SimpleCNN gate failed: mean macro-F1={cnn_mean:.4f}")

    if integrity_ok and class_support_ok and metadata_ok and signal_ok and cnn_ok:
        status = "PASS"
        allowed = "llm_smoke"
    elif integrity_ok and class_support_ok and metadata_ok and (signal_ok or cnn_ok):
        status = "CONDITIONAL_PASS"
        allowed = "remediation_only"
    else:
        status = "BLOCKED"
        allowed = "stop"

    return {
        "status": status,
        "class_mapping_confirmed": True,
        "exact_train_test_file_duplicates": exact_raw,
        "exact_train_test_window_duplicates": exact_win,
        "metadata_confound_passed": bool(metadata_ok),
        "signal_learnability_passed": bool(signal_ok),
        "cnn_learnability_passed": bool(cnn_ok),
        "allowed_next_stage": allowed,
        "reasons": reasons,
        "metrics": {
            "metadata_safe_extra_trees_mean_macro_f1": safe_mean,
            "window_position_extra_trees_mean_macro_f1": pos_mean,
            "signal_feature_full_mean_macro_f1": signal_mean,
            "signal_feature_full_worst_macro_f1": signal_worst,
            "signal_feature_full_per_class_mean_f1": {
                cls: signal_per_class[i] for i, cls in enumerate(MT_CLASSES)
            } if signal_per_class else {},
            "simple_cnn_full_mean_macro_f1": cnn_mean,
        },
    }


def stage_summarize() -> None:
    ensure_dirs()
    decision = preflight_decision()
    (OUT_DIR / "mt_private_preflight_decision.json").write_text(json.dumps(decision, indent=2, sort_keys=True))
    metrics = decision["metrics"]
    lines = [
        "# Private Machine-Tool Preflight Gate Report",
        "",
        f"- Status: {decision['status']}",
        f"- Allowed next stage: {decision['allowed_next_stage']}",
        f"- Class mapping confirmed: {decision['class_mapping_confirmed']}",
        f"- Exact train/test raw-file duplicates: {decision['exact_train_test_file_duplicates']}",
        f"- Exact train/test window duplicates: {decision['exact_train_test_window_duplicates']}",
        f"- Metadata confound passed: {decision['metadata_confound_passed']}",
        f"- Signal learnability passed: {decision['signal_learnability_passed']}",
        f"- CNN learnability passed: {decision['cnn_learnability_passed']}",
        "",
        "## Gate Metrics",
        "",
        f"- metadata_safe ExtraTrees mean Macro-F1: {metrics['metadata_safe_extra_trees_mean_macro_f1']:.4f}",
        f"- window_position_only ExtraTrees mean Macro-F1: {metrics['window_position_extra_trees_mean_macro_f1']:.4f}",
        f"- signal_feature_only full mean Macro-F1: {metrics['signal_feature_full_mean_macro_f1']:.4f}",
        f"- signal_feature_only full worst-fold Macro-F1: {metrics['signal_feature_full_worst_macro_f1']:.4f}",
        f"- SimpleCNN full mean Macro-F1: {metrics['simple_cnn_full_mean_macro_f1']:.4f}",
        "",
        "## Reasons",
        "",
    ]
    if decision["reasons"]:
        lines.extend([f"- {r}" for r in decision["reasons"]])
    else:
        lines.append("- All preflight gates passed.")
    lines.extend(
        [
            "",
            "## Evidence Boundary",
            "",
            "- The 1/2/3 class mapping is confirmed by the project owner on 2026-07-10.",
            "- The mapping is not treated as published MechaForge PDF content.",
            "- Test file IDs 7/8 were used only for inventory and leakage integrity checks in this preflight.",
            "- No LLM/API call, synthetic waveform, synthetic recipe, or formal held-out test was run.",
        ]
    )
    (OUT_DIR / "mt_private_preflight_gate_report.md").write_text("\n".join(lines) + "\n")


def stage_all() -> None:
    stage_inventory()
    stage_split_audit()
    stage_duplicate_audit()
    stage_confound_audit()
    stage_learnability()
    stage_summarize()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        choices=[
            "inventory",
            "split-audit",
            "duplicate-audit",
            "confound-audit",
            "learnability",
            "summarize",
            "all",
        ],
        default="all",
    )
    args = parser.parse_args()
    if args.stage == "inventory":
        stage_inventory()
    elif args.stage == "split-audit":
        stage_split_audit()
    elif args.stage == "duplicate-audit":
        stage_duplicate_audit()
    elif args.stage == "confound-audit":
        stage_confound_audit()
    elif args.stage == "learnability":
        stage_learnability()
    elif args.stage == "summarize":
        stage_summarize()
    else:
        stage_all()


if __name__ == "__main__":
    main()
