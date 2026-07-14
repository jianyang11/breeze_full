"""One-shot formal evaluation for the preregistered private machine-tool v3 S-C pool.

This entry point is intentionally separate from the inner-only v3 workflow.
It refuses to load formal IDs 7/8 unless a committed, hash-locked
preregistration exists.  It never generates candidates or changes the S-C
pool; interrupted runs resume only missing seed/method rows.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

SCRIPT_DIR = Path(__file__).resolve().parent
BREEZE_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(BREEZE_DIR / "src"))

import mt_private_v3_conditional as v3  # noqa: E402
from data_mt import (  # noqa: E402
    CLASS_ID_TO_DISPLAY_NAME,
    MT_CLASSES,
    MT_DIR,
    RAW_CLASS_IDS,
    parse_mt_filename,
)
from mt_private_v2_llm_smoke import windowize  # noqa: E402


FORMAL_DATE = "2026-07-14"
OUT_DIR = BREEZE_DIR / "results" / f"mt_private_v3_formal_{FORMAL_DATE}"
FORMAL_TRAIN_FILE_IDS = ("1", "2", "4", "5", "10")
FORMAL_TEST_FILE_IDS = ("7", "8")
FORMAL_SEEDS = tuple(range(40))
CANDIDATE_METHOD = "s_c_llm"
N_REALS = v3.DOWNSTREAM_N_REALS
N_SYN_BY_N_REAL = v3.DOWNSTREAM_N_SYN_BY_N_REAL
PREREG_PATH = BREEZE_DIR / "results" / "mt_private_v3_design_2026-07-13" / "mt_private_v3_preregistration.md"
LOCK_PATH = BREEZE_DIR / "results" / "mt_private_v3_design_2026-07-13" / "mt_private_v3_formal_lock.json"
POOL_MANIFEST = v3.OUT_DIR / "mt_private_v3_s_c_llm_n20_pool_manifest.csv"
INNER_DECISION = v3.OUT_DIR / "mt_private_v3_s_c_llm_downstream_decision.json"

FORMAL_FIELDS = [
    "method", "n_real", "n_syn", "seed", "train_sample_count", "acc", "macro_f1",
    *[f"f1_{cls}" for cls in MT_CLASSES], "confusion",
]


def json_ready(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_ready(item) for item in value]
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_ready(value), indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows([{key: json_ready(value) for key, value in row.items()} for row in rows])


def append_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fresh = not path.exists()
    with path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FORMAL_FIELDS, lineterminator="\n", extrasaction="ignore")
        if fresh:
            writer.writeheader()
        writer.writerows([{key: json_ready(value) for key, value in row.items()} for row in rows])


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def holm_adjust(values: list[float]) -> list[float]:
    order = np.argsort(values)
    adjusted = np.zeros(len(values), dtype=float)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, (len(values) - rank) * values[index])
        adjusted[index] = min(running, 1.0)
    return adjusted.tolist()


def _find_csv(raw_class_id: str, file_id: str, permitted_ids: tuple[str, ...]) -> Path:
    if file_id not in permitted_ids:
        raise RuntimeError(f"file ID {file_id} is outside the preregistered split")
    matches = []
    for path in sorted(MT_DIR.glob(f"{raw_class_id}_{file_id}*.csv")):
        parsed = parse_mt_filename(path)
        if parsed.get("parse_ok") and str(parsed["raw_class_id"]) == raw_class_id and str(parsed["file_id"]) == file_id:
            matches.append(path)
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one CSV for class={raw_class_id}, file={file_id}; found {matches}")
    return matches[0]


def load_split(file_ids: tuple[str, ...], split: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, Any]], list[str]]:
    xs, ys, files, rows, files_read = [], [], [], [], []
    for ci, raw_id in enumerate(RAW_CLASS_IDS):
        for file_id in file_ids:
            path = _find_csv(raw_id, file_id, file_ids)
            raw = np.genfromtxt(path, delimiter=",", skip_header=1, dtype=np.float32)
            windows, _ = windowize(raw)
            if not len(windows):
                raise RuntimeError(f"{path.name} cannot produce a window")
            xs.append(windows)
            ys.append(np.full(len(windows), ci, dtype=np.int64))
            files.append(np.full(len(windows), path.name, dtype=object))
            files_read.append(path.name)
            rows.append({
                "split": split, "raw_class_id": raw_id, "class_name": MT_CLASSES[ci],
                "display_name": CLASS_ID_TO_DISPLAY_NAME[raw_id], "file_id": file_id,
                "source_file": path.name, "n_rows": int(len(raw)), "window_count": int(len(windows)),
            })
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(files), rows, files_read


def validate_preregistration() -> dict[str, Any]:
    if not PREREG_PATH.exists() or not LOCK_PATH.exists():
        raise RuntimeError("formal preregistration and machine-readable lock must exist before formal files are read")
    lock = json.loads(LOCK_PATH.read_text())
    required = {
        "candidate_method": CANDIDATE_METHOD,
        "formal_train_file_ids": list(FORMAL_TRAIN_FILE_IDS),
        "formal_test_file_ids": list(FORMAL_TEST_FILE_IDS),
        "formal_seeds": list(FORMAL_SEEDS),
        "n_reals": list(N_REALS),
        "n_syn_by_n_real": {str(key): value for key, value in N_SYN_BY_N_REAL.items()},
    }
    for key, expected in required.items():
        if lock.get(key) != expected:
            raise RuntimeError(f"formal lock mismatch for {key}")
    for relative_path, expected_hash in lock.get("source_sha256", {}).items():
        if sha256_file(BREEZE_DIR.parent / relative_path) != expected_hash:
            raise RuntimeError(f"source file differs from preregistration lock: {relative_path}")
    if lock.get("pool_manifest_sha256") != sha256_file(POOL_MANIFEST):
        raise RuntimeError("S-C pool manifest differs from preregistration lock")
    if lock.get("inner_decision_sha256") != sha256_file(INNER_DECISION):
        raise RuntimeError("inner decision differs from preregistration lock")
    decision = json.loads(INNER_DECISION.read_text())
    if decision.get("status") != "PASS" or decision.get("cells_at_least_noise_aug") != 6:
        raise RuntimeError("formal evaluation requires the frozen unique 6/6 S-C inner success")
    return lock


def sample_real_subset(X: np.ndarray, y: np.ndarray, n_real: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(v3.stable_seed("mt_private_v3_formal", "real_subset", n_real, seed))
    indices = []
    for ci, cls in enumerate(MT_CLASSES):
        available = np.flatnonzero(y == ci)
        if len(available) < n_real:
            raise RuntimeError(f"{cls} has {len(available)} train windows but requires {n_real}")
        indices.extend(rng.choice(available, n_real, replace=False).tolist())
    selected = np.asarray(indices, dtype=int)
    return X[selected], y[selected]


def noise_augment(X: np.ndarray, y: np.ndarray, n_syn: int, seed: int, class_std: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(v3.stable_seed("mt_private_v3_formal", "noise_aug", seed))
    xs, ys = [], []
    for ci, cls in enumerate(MT_CLASSES):
        carrier = X[y == ci][:n_syn]
        if len(carrier) < n_syn:
            raise RuntimeError("formal noise_aug requires distinct selected carriers without replacement")
        noise = rng.normal(size=carrier.shape).astype(np.float32) * (0.05 * class_std[cls])[None, :, None]
        xs.append(carrier + noise)
        ys.append(np.full(n_syn, ci, dtype=np.int64))
    return np.concatenate(xs).astype(np.float32), np.concatenate(ys)


def run_formal() -> dict[str, Any]:
    lock = validate_preregistration()
    X_train, y_train, _, train_rows, train_files = load_split(FORMAL_TRAIN_FILE_IDS, "formal_train")
    X_test, y_test, _, test_rows, test_files = load_split(FORMAL_TEST_FILE_IDS, "formal_test")
    if set(train_files) & set(test_files):
        raise RuntimeError("formal train/test source-file overlap")
    pool = v3.load_s_c_pool()
    class_std = {cls: X_train[y_train == ci].std(axis=(0, 2)) for ci, cls in enumerate(MT_CLASSES)}
    path = OUT_DIR / "mt_private_v3_formal_downstream.csv"
    done = {(row["method"], int(row["n_real"]), int(row["seed"])) for row in read_csv(path)}
    pending: list[dict[str, Any]] = []
    for n_real in N_REALS:
        n_syn = N_SYN_BY_N_REAL[n_real]
        static_x = np.concatenate([pool[cls][:n_syn] for cls in MT_CLASSES])
        static_y = np.concatenate([np.full(n_syn, ci, dtype=np.int64) for ci in range(len(MT_CLASSES))])
        for seed in FORMAL_SEEDS:
            X_real, y_real = sample_real_subset(X_train, y_train, n_real, seed)
            X_noise, y_noise = noise_augment(X_real, y_real, n_syn, seed, class_std)
            methods = {
                "real_only": (X_real, y_real),
                "noise_aug": (np.concatenate([X_real, X_noise]), np.concatenate([y_real, y_noise])),
                CANDIDATE_METHOD: (np.concatenate([X_real, static_x]), np.concatenate([y_real, static_y])),
            }
            for method, (X_fit, y_fit) in methods.items():
                if (method, n_real, seed) in done:
                    continue
                X_fit_norm, X_test_norm = v3.normalize_train_val(X_fit, X_test)
                model = v3.train_cnn(X_fit_norm.astype(np.float32), y_fit, v3.stable_seed("mt_private_v3_formal", "cnn", method, n_real, seed))
                predicted = v3.predict_cnn(model, X_test_norm.astype(np.float32))
                per_class = f1_score(y_test, predicted, labels=list(range(len(MT_CLASSES))), average=None, zero_division=0)
                pending.append({
                    "method": method, "n_real": n_real, "n_syn": n_syn if method != "real_only" else 0,
                    "seed": seed, "train_sample_count": len(y_fit),
                    "acc": float(accuracy_score(y_test, predicted)),
                    "macro_f1": float(f1_score(y_test, predicted, labels=list(range(len(MT_CLASSES))), average="macro", zero_division=0)),
                    **{f"f1_{cls}": float(per_class[ci]) for ci, cls in enumerate(MT_CLASSES)},
                    "confusion": json.dumps(confusion_matrix(y_test, predicted, labels=list(range(len(MT_CLASSES)))).tolist(), separators=(",", ":")),
                })
                if len(pending) >= 6:
                    append_csv(path, pending)
                    pending = []
    append_csv(path, pending)
    integrity = {
        "candidate_method": CANDIDATE_METHOD, "formal_train_files_read": train_files,
        "formal_test_files_read": test_files, "formal_train_rows": train_rows,
        "formal_test_rows": test_rows, "pool_manifest_sha256": lock["pool_manifest_sha256"],
        "inner_decision_sha256": lock["inner_decision_sha256"], "expected_rows": len(N_REALS) * len(FORMAL_SEEDS) * 3,
        "observed_rows": len(read_csv(path)),
    }
    write_json(OUT_DIR / "mt_private_v3_formal_integrity.json", integrity)
    return integrity


def summarize_formal() -> dict[str, Any]:
    path = OUT_DIR / "mt_private_v3_formal_downstream.csv"
    rows = read_csv(path)
    expected = len(N_REALS) * len(FORMAL_SEEDS) * 3
    if len(rows) != expected:
        raise RuntimeError(f"formal result is incomplete: {len(rows)}/{expected} rows")
    frame = pd.DataFrame(rows)
    for column in ["n_real", "n_syn", "seed", "train_sample_count", "acc", "macro_f1", *[f"f1_{cls}" for cls in MT_CLASSES]]:
        frame[column] = pd.to_numeric(frame[column])
    summary_rows = []
    for (method, n_real), group in frame.groupby(["method", "n_real"], sort=True):
        summary_rows.append({
            "method": method, "n_real": int(n_real), "seeds": len(group),
            **{f"mean_{metric}": float(group[metric].mean()) for metric in ("acc", "macro_f1")},
            **{f"std_{metric}": float(group[metric].std(ddof=1)) for metric in ("acc", "macro_f1")},
        })
    write_csv(OUT_DIR / "mt_private_v3_formal_downstream_summary.csv", summary_rows, sorted(summary_rows[0]))
    summary = pd.DataFrame(summary_rows).set_index(["method", "n_real"])
    cells, tests = [], []
    for n_real in N_REALS:
        for metric in ("acc", "macro_f1"):
            candidate = float(summary.loc[(CANDIDATE_METHOD, n_real), f"mean_{metric}"])
            noise = float(summary.loc[("noise_aug", n_real), f"mean_{metric}"])
            paired = frame[(frame.method == CANDIDATE_METHOD) & (frame.n_real == n_real)][["seed", metric]].merge(
                frame[(frame.method == "noise_aug") & (frame.n_real == n_real)][["seed", metric]],
                on="seed", suffixes=("_candidate", "_noise"),
            ).sort_values("seed")
            delta = paired[f"{metric}_candidate"].to_numpy() - paired[f"{metric}_noise"].to_numpy()
            p_raw = 1.0 if np.allclose(delta, 0) else float(wilcoxon(delta, alternative="greater", zero_method="zsplit").pvalue)
            cells.append({"n_real": n_real, "metric": metric, "candidate": candidate, "noise_aug": noise, "candidate_ge_noise": candidate >= noise})
            tests.append({"n_real": n_real, "metric": metric, "comparison": f"{CANDIDATE_METHOD}>noise_aug", "mean_delta": float(delta.mean()), "p_raw": p_raw})
    for row, q_value in zip(tests, holm_adjust([row["p_raw"] for row in tests]), strict=True):
        row["holm_q"] = q_value
    write_csv(OUT_DIR / "mt_private_v3_formal_wilcoxon_holm.csv", tests, ["n_real", "metric", "comparison", "mean_delta", "p_raw", "holm_q"])
    decision = {
        "candidate_method": CANDIDATE_METHOD, "formal_test_files_read": list(FORMAL_TEST_FILE_IDS),
        "formal_train_file_ids": list(FORMAL_TRAIN_FILE_IDS), "formal_seeds": list(FORMAL_SEEDS),
        "cells_at_least_noise_aug": int(sum(bool(row["candidate_ge_noise"]) for row in cells)),
        "total_cells": len(cells), "cells": cells, "wilcoxon_holm_family": tests,
    }
    write_json(OUT_DIR / "mt_private_v3_formal_decision.json", decision)
    return decision


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("formal", "summarize"), required=True)
    args = parser.parse_args()
    if args.stage == "formal":
        print(json.dumps(run_formal(), sort_keys=True))
    else:
        print(json.dumps(summarize_formal(), sort_keys=True))


if __name__ == "__main__":
    main()
