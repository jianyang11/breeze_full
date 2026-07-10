"""Training-free verifier for the private machine-tool dataset.

The machine-tool data use four channels (X/Y/Z acceleration + Current). The
raw class-prefix mapping was confirmed by the project owner on 2026-07-10, but
the workspace still does not include machine geometry, spindle speed, or feed
metadata. This verifier therefore calibrates only equipment-generic constraints
from the train split: time statistics, channel energy/correlation structure,
smooth spectral-band fractions, and normalized PSD-CDF W1 distances. No PU
bearing kinematics or unsupported machine-tool frequencies are used here.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.signal import welch

sys.path.insert(0, str(Path(__file__).parent))
from config import RESULTS_DIR, RUNS_DIR
from data_mt import (
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
    class_name_to_raw_id,
    normalize_mt_class,
    parse_mt_filename,
)
from verifier.features import time_stats


STAT_KEYS = ["rms", "peak", "std", "kurtosis", "skewness", "crest"]
NORM_SPEC_BANDS = 8


def _tolist(x: Any) -> Any:
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, np.generic):
        return x.item()
    if isinstance(x, dict):
        return {k: _tolist(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_tolist(v) for v in x]
    return x


def _windows(arr: np.ndarray) -> np.ndarray:
    n = (len(arr) - WIN_MT) // STRIDE_MT + 1
    if n < 1:
        return np.empty((0, len(MT_CHANNELS), WIN_MT), dtype=np.float32)
    return np.stack(
        [arr[i * STRIDE_MT:i * STRIDE_MT + WIN_MT].T for i in range(n)]
    ).astype(np.float32)


def load_mt_with_files(split: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load raw CSV windows and preserve class/file provenance."""
    Xs, ys, files = [], [], []
    wanted = TRAIN_FILES if split == "train" else TEST_FILES
    for f in sorted(glob.glob(str(MT_DIR / "*.csv"))):
        parsed = parse_mt_filename(f)
        if not parsed["parse_ok"]:
            raise ValueError(f"invalid private machine-tool filename: {f}")
        cls_id, fid = str(parsed["raw_class_id"]), str(parsed["file_id"])
        if fid not in wanted:
            continue
        d = np.genfromtxt(f, delimiter=",", skip_header=1)
        if d.ndim != 2 or d.shape[1] != len(MT_CHANNELS):
            raise ValueError(f"{f} has shape {d.shape}, expected four columns")
        w = _windows(d)
        ci = RAW_CLASS_IDS.index(cls_id)
        Xs.append(w)
        ys.append(np.full(len(w), ci, dtype=np.int64))
        files.extend([f"{cls_id}_{fid}"] * len(w))
    if not Xs:
        raise FileNotFoundError(f"no machine-tool CSV windows for split={split}")
    return np.concatenate(Xs), np.concatenate(ys), np.asarray(files)


def select_limit(
    X: np.ndarray,
    y: np.ndarray,
    files: np.ndarray,
    limit_per_class: int | None,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if limit_per_class is None:
        return X, y, files
    rng = np.random.default_rng(seed)
    keep = []
    for ci in range(len(MT_CLASSES)):
        idx = np.where(y == ci)[0]
        keep.extend(rng.choice(idx, min(limit_per_class, len(idx)), replace=False))
    keep = np.asarray(sorted(keep), dtype=int)
    return X[keep], y[keep], files[keep]


def _joint_alpha(values: np.ndarray, target: float) -> float:
    best_alpha, best_gap = 0.01, np.inf
    for alpha in np.linspace(0.001, 0.10, 50):
        lo = np.quantile(values, alpha / 2, axis=0)
        hi = np.quantile(values, 1 - alpha / 2, axis=0)
        rate = float(np.mean(np.all((values >= lo) & (values <= hi), axis=1)))
        gap = abs(rate - target)
        if gap < best_gap:
            best_alpha, best_gap = float(alpha), float(gap)
    return best_alpha


def _union_interval(values: np.ndarray, groups: np.ndarray, alpha: float) -> tuple[np.ndarray, np.ndarray]:
    lows, highs = [], []
    for group in np.unique(groups):
        vg = values[groups == group]
        lows.append(np.quantile(vg, alpha / 2, axis=0))
        highs.append(np.quantile(vg, 1 - alpha / 2, axis=0))
    return np.min(lows, axis=0), np.max(highs, axis=0)


def _per_group_quantile(values: np.ndarray, groups: np.ndarray, q: float, mode: str) -> np.ndarray:
    qs = np.asarray([np.quantile(values[groups == g], q, axis=0) for g in np.unique(groups)])
    if mode == "max":
        return np.max(qs, axis=0)
    if mode == "min":
        return np.min(qs, axis=0)
    raise ValueError(mode)


def soft_band_fracs_norm(x: np.ndarray, n_bands: int = NORM_SPEC_BANDS) -> np.ndarray:
    """Overlapping triangular PSD energy fractions on normalized frequency."""
    f, p = welch(x, fs=1.0, nperseg=min(512, len(x)))
    centers = (np.arange(n_bands, dtype=float) + 0.5) * (0.5 / n_bands)
    vals = []
    for i, center in enumerate(centers):
        left = 0.0 if i == 0 else centers[i - 1]
        right = 0.5 if i == n_bands - 1 else centers[i + 1]
        weights = np.zeros_like(f)
        ml = (f >= left) & (f <= center)
        mr = (f > center) & (f <= right)
        weights[ml] = (f[ml] - left) / max(center - left, 1e-12)
        weights[mr] = (right - f[mr]) / max(right - center, 1e-12)
        vals.append(np.trapezoid(p * np.clip(weights, 0.0, 1.0), f))
    vals = np.asarray(vals, dtype=float)
    return vals / (vals.sum() + 1e-30)


def psd_cdf_norm(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    f, p = welch(x, fs=1.0, nperseg=min(512, len(x)))
    p = np.maximum(p, 0.0)
    df = np.gradient(f)
    mass = p * df
    mass = mass / (mass.sum() + 1e-30)
    cdf = np.cumsum(mass)
    return f, cdf / (cdf[-1] + 1e-30)


def psd_w1_norm(x: np.ndarray, ref_cdf: np.ndarray) -> float:
    f, cdf = psd_cdf_norm(x)
    return float(np.trapezoid(np.abs(cdf - ref_cdf), f))


def stat_vector(w: np.ndarray) -> np.ndarray:
    return np.asarray(
        [time_stats(w[j])[key] for j in range(len(MT_CHANNELS)) for key in STAT_KEYS],
        dtype=float,
    )


def soft_spectrum_vector(w: np.ndarray) -> np.ndarray:
    return np.concatenate([soft_band_fracs_norm(w[j]) for j in range(len(MT_CHANNELS))])


def channel_energy_ratios(w: np.ndarray) -> np.ndarray:
    e = np.mean(w.astype(float) ** 2, axis=1)
    return e / (e.sum() + 1e-30)


def corr_upper(w: np.ndarray) -> np.ndarray:
    corr = np.corrcoef(w)
    corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0)
    return corr[np.triu_indices(len(MT_CHANNELS), k=1)]


def structure_vector(w: np.ndarray) -> np.ndarray:
    return np.concatenate([
        stat_vector(w),
        channel_energy_ratios(w),
        corr_upper(w),
        soft_spectrum_vector(w),
    ]).astype(float)


def feature_names() -> dict[str, list[str]]:
    stats = [f"{ch}_{key}" for ch in MT_CHANNELS for key in STAT_KEYS]
    soft = [f"{ch}_soft_band_{i}" for ch in MT_CHANNELS for i in range(NORM_SPEC_BANDS)]
    ratios = [f"{ch}_energy_ratio" for ch in MT_CHANNELS]
    corr = []
    for i in range(len(MT_CHANNELS)):
        for j in range(i + 1, len(MT_CHANNELS)):
            corr.append(f"corr_{MT_CHANNELS[i]}_{MT_CHANNELS[j]}")
    return {"stats": stats, "soft": soft, "ratios": ratios, "corr": corr}


@dataclass
class MachineToolVerifier:
    coverage: float = 0.90

    def __post_init__(self):
        self.calib: dict[str, Any] = {}

    def calibrate(self, X_train: np.ndarray, y_train: np.ndarray, files: np.ndarray) -> None:
        gate_coverage = self.coverage ** (1.0 / 3.0)
        names = feature_names()
        self.calib = {
            "coverage": self.coverage,
            "gate_coverage": gate_coverage,
            "schema": {
                "channels": MT_CHANNELS,
                "window": WIN_MT,
                "stride": STRIDE_MT,
                "sampling_rate_hz": MT_SAMPLING_RATE_HZ,
                "window_seconds": WIN_MT / MT_SAMPLING_RATE_HZ,
                "stride_seconds": STRIDE_MT / MT_SAMPLING_RATE_HZ,
                "frequency_axis": "normalized cycles/sample for verifier gates; acquisition sampling rate is 4000 Hz",
                "class_names": MT_CLASSES,
                "raw_class_ids": RAW_CLASS_IDS,
                "class_id_to_name": CLASS_ID_TO_NAME,
                "class_id_to_display_name": CLASS_ID_TO_DISPLAY_NAME,
                "documented_operating_states": [
                    "Normal machining",
                    "Lead-screw anomaly",
                    "Base imbalance",
                ],
                "class_mapping_status": CLASS_MAPPING_STATUS,
                "class_mapping_source": CLASS_MAPPING_SOURCE,
                "class_mapping_confirmed_date": CLASS_MAPPING_CONFIRMED_DATE,
                "class_mapping_note": (
                    "This mapping is confirmed by the project owner, not by the "
                    "published MechaForge PDF text and not inferred from waveforms."
                ),
            },
            "feature_names": names,
            "classes": {},
        }
        for ci, cls in enumerate(MT_CLASSES):
            idx = y_train == ci
            Wc, fc = X_train[idx], files[idx]
            stats = np.array([stat_vector(w) for w in Wc])
            soft = np.array([soft_spectrum_vector(w) for w in Wc])
            struct = np.array([structure_vector(w) for w in Wc])

            stats_alpha = _joint_alpha(stats, gate_coverage)
            stats_lo, stats_hi = _union_interval(stats, fc, stats_alpha)
            soft_alpha = _joint_alpha(soft, gate_coverage)
            soft_lo, soft_hi = _union_interval(soft, fc, soft_alpha)
            soft_med = np.median(soft, axis=0)
            soft_q25 = np.quantile(soft, 0.25, axis=0)
            soft_q75 = np.quantile(soft, 0.75, axis=0)
            soft_scale = (soft_q75 - soft_q25) / 1.349
            soft_scale = np.where(soft_scale > 1e-12, soft_scale, np.std(soft, axis=0) + 1e-9)
            soft_z = (soft - soft_med) / soft_scale
            soft_axis_dist = np.sqrt((soft_z ** 2).sum(axis=1))

            med = np.median(struct, axis=0)
            q25 = np.quantile(struct, 0.25, axis=0)
            q75 = np.quantile(struct, 0.75, axis=0)
            scale = (q75 - q25) / 1.349
            scale = np.where(scale > 1e-12, scale, np.std(struct, axis=0) + 1e-9)
            z = (struct - med) / scale
            axis_dist = np.sqrt((z ** 2).sum(axis=1))

            cdfs = []
            for ch in range(len(MT_CHANNELS)):
                cdfs.append(np.array([psd_cdf_norm(w[ch])[1] for w in Wc]))
            ref_cdfs = [np.median(c, axis=0) for c in cdfs]
            w1 = np.stack([
                np.array([psd_w1_norm(w[ch], ref_cdfs[ch]) for w in Wc])
                for ch in range(len(MT_CHANNELS))
            ], axis=1)

            embed = z
            dmat = np.sqrt(((embed[:, None, :] - embed[None, :, :]) ** 2).sum(axis=-1))
            np.fill_diagonal(dmat, np.inf)
            nn = dmat.min(axis=1)

            self.calib["classes"][cls] = {
                "raw_class_id": RAW_CLASS_IDS[ci],
                "class_name": cls,
                "display_name": CLASS_ID_TO_DISPLAY_NAME[RAW_CLASS_IDS[ci]],
                "n_train": int(len(Wc)),
                "train_files": sorted(np.unique(fc).tolist()),
                "stats_quantile": {
                    "alpha": stats_alpha,
                    "lo": stats_lo,
                    "hi": stats_hi,
                },
                "soft_spectrum": {
                    "alpha": soft_alpha,
                    "lo": soft_lo,
                    "hi": soft_hi,
                    "median": soft_med,
                    "scale": soft_scale,
                    "axis_threshold": float(_per_group_quantile(soft_axis_dist, fc, gate_coverage, "max")),
                    "hard_domains": ["coordinate_union", "axis_ellipsoid"],
                },
                "robust_ellipsoid": {
                    "median": med,
                    "scale": scale,
                    "axis_threshold": float(_per_group_quantile(axis_dist, fc, gate_coverage, "max")),
                },
                "psd_w1": {
                    "ref_cdf": ref_cdfs,
                    "threshold": _per_group_quantile(w1, fc, gate_coverage, "max"),
                },
                "diversity": {
                    "real_real_nn_q05": float(np.quantile(nn, 0.05)),
                    "real_real_nn_median": float(np.median(nn)),
                    "embedding_median": med,
                    "embedding_scale": scale,
                },
            }

    def verify(self, w: np.ndarray, cls: str) -> dict[str, Any]:
        class_name = normalize_mt_class(cls)
        raw_class_id = class_name_to_raw_id(class_name)
        class_key = class_name
        legacy_key = f"MT-{raw_class_id}"
        if class_key not in self.calib.get("classes", {}) and legacy_key in self.calib.get("classes", {}):
            class_key = legacy_key
        report: dict[str, Any] = {
            "class": class_name,
            "raw_class_id": raw_class_id,
            "display_name": CLASS_ID_TO_DISPLAY_NAME[raw_class_id],
            "schema": "machine_tool_4ch",
            "feasible": True,
            "gates": {},
            "scores": {},
        }

        def add_gate(name: str, passed: bool, messages: list[str]) -> None:
            report["gates"][name] = {"passed": bool(passed), "messages": messages}
            report["feasible"] = bool(report["feasible"] and passed)

        sanity_messages = []
        if w.shape != (len(MT_CHANNELS), WIN_MT):
            sanity_messages.append(f"shape {w.shape} != ({len(MT_CHANNELS)},{WIN_MT})")
        if not np.all(np.isfinite(w)):
            sanity_messages.append("non-finite values")
        if np.any(np.std(w, axis=1) < 1e-10):
            bad = [MT_CHANNELS[i] for i, s in enumerate(np.std(w, axis=1)) if s < 1e-10]
            sanity_messages.append(f"constant channels: {bad}")
        repeated = float(np.mean(np.all(np.diff(w, axis=1) == 0, axis=0)))
        if repeated > 0.2:
            sanity_messages.append(f"large repeated consecutive segments ratio={repeated:.3f}")
        add_gate("sanity", len(sanity_messages) == 0, sanity_messages)
        if sanity_messages:
            return _tolist(report)

        cal = self.calib["classes"][class_key]

        stats = stat_vector(w)
        stats_lo = np.asarray(cal["stats_quantile"]["lo"])
        stats_hi = np.asarray(cal["stats_quantile"]["hi"])
        stats_bad = np.where((stats < stats_lo) | (stats > stats_hi))[0]
        stats_messages = []
        for i in stats_bad[:8]:
            val = stats[i]
            stats_messages.append(
                f"{self.calib['feature_names']['stats'][i]}={val:.5g} outside "
                f"[{stats_lo[i]:.5g},{stats_hi[i]:.5g}]"
            )

        struct = structure_vector(w)
        med = np.asarray(cal["robust_ellipsoid"]["median"])
        scale = np.asarray(cal["robust_ellipsoid"]["scale"])
        z = (struct - med) / scale
        axis_dist = float(np.sqrt((z ** 2).sum()))
        axis_thr = float(cal["robust_ellipsoid"]["axis_threshold"])
        axis_passed = axis_dist <= axis_thr
        if not axis_passed:
            all_names = (
                self.calib["feature_names"]["stats"]
                + self.calib["feature_names"]["ratios"]
                + self.calib["feature_names"]["corr"]
                + self.calib["feature_names"]["soft"]
            )
            order = np.argsort(-np.abs(z))[:8]
            stats_messages.append(
                "largest robust deviations: "
                + ", ".join(f"{all_names[i]}={z[i]:.2f}" for i in order)
            )
        stats_passed = len(stats_bad) == 0 or axis_passed
        add_gate("stats_union", stats_passed, [] if stats_passed else stats_messages)
        report["scores"]["stats_union"] = {
            "quantile_passed": len(stats_bad) == 0,
            "axis_distance": axis_dist,
            "axis_threshold": axis_thr,
            "axis_passed": axis_passed,
        }

        soft = soft_spectrum_vector(w)
        soft_lo = np.asarray(cal["soft_spectrum"]["lo"])
        soft_hi = np.asarray(cal["soft_spectrum"]["hi"])
        soft_bad = np.where((soft < soft_lo) | (soft > soft_hi))[0]
        soft_med = np.asarray(cal["soft_spectrum"]["median"])
        soft_scale = np.asarray(cal["soft_spectrum"]["scale"])
        soft_z = (soft - soft_med) / soft_scale
        soft_axis_dist = float(np.sqrt((soft_z ** 2).sum()))
        soft_axis_thr = float(cal["soft_spectrum"]["axis_threshold"])
        soft_axis_passed = soft_axis_dist <= soft_axis_thr
        soft_coord_passed = len(soft_bad) == 0
        soft_passed = soft_coord_passed or soft_axis_passed
        soft_messages = []
        if not soft_passed:
            soft_messages.extend([
                f"{self.calib['feature_names']['soft'][i]}={soft[i]:.5f} outside "
                f"[{soft_lo[i]:.5f},{soft_hi[i]:.5f}]"
                for i in soft_bad[:8]
            ])
            order = np.argsort(-np.abs(soft_z))[:8]
            soft_messages.append(
                "largest spectral robust deviations: "
                + ", ".join(f"{self.calib['feature_names']['soft'][i]}={soft_z[i]:.2f}" for i in order)
            )
        add_gate("soft_spectrum", soft_passed, soft_messages)
        report["scores"]["soft_spectrum_max_violation"] = float(
            max(
                np.max(np.maximum(soft_lo - soft, 0.0)),
                np.max(np.maximum(soft - soft_hi, 0.0)),
            )
        )
        report["scores"]["soft_spectrum"] = {
            "coordinate_passed": soft_coord_passed,
            "axis_distance": soft_axis_dist,
            "axis_threshold": soft_axis_thr,
            "axis_passed": soft_axis_passed,
        }

        ref = [np.asarray(r) for r in cal["psd_w1"]["ref_cdf"]]
        w1 = np.asarray([psd_w1_norm(w[ch], ref[ch]) for ch in range(len(MT_CHANNELS))])
        w1_thr = np.asarray(cal["psd_w1"]["threshold"])
        w1_bad = np.where(w1 > w1_thr)[0]
        w1_messages = [
            f"{MT_CHANNELS[i]} PSD W1={w1[i]:.5f} exceeds train-supported threshold {w1_thr[i]:.5f}"
            for i in w1_bad
        ]
        add_gate("psd_w1", len(w1_bad) == 0, w1_messages)
        report["scores"]["psd_w1"] = {
            MT_CHANNELS[i]: {"value": float(w1[i]), "threshold": float(w1_thr[i])}
            for i in range(len(MT_CHANNELS))
        }

        div = cal["diversity"]
        div_z = (struct - np.asarray(div["embedding_median"])) / np.asarray(div["embedding_scale"])
        report["scores"]["diversity_embedding_norm"] = float(np.sqrt((div_z ** 2).sum()))
        report["scores"]["real_real_nn_reference"] = {
            "q05": float(div["real_real_nn_q05"]),
            "median": float(div["real_real_nn_median"]),
        }
        return _tolist(report)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(_tolist(self.calib), indent=2))

    @classmethod
    def load(cls, path: Path) -> "MachineToolVerifier":
        calib = json.loads(path.read_text())
        obj = cls(coverage=calib["coverage"])
        obj.calib = calib
        return obj


def summarize_reports(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for split in sorted({r["split"] for r in rows}):
        for ci, cls in enumerate(MT_CLASSES):
            sub = [r for r in rows if r["split"] == split and r["class"] == cls]
            if not sub:
                continue
            gate_names = sorted({g for r in sub for g in r["failed_gates"]})
            row = {
                "split": split,
                "class": cls,
                "raw_class_id": class_name_to_raw_id(cls),
                "display_name": CLASS_ID_TO_DISPLAY_NAME[class_name_to_raw_id(cls)],
                "n": len(sub),
                "pass_rate": sum(r["feasible"] for r in sub) / len(sub),
            }
            for gate in gate_names:
                row[f"fail_{gate}"] = sum(gate in r["failed_gates"] for r in sub)
            out.append(row)
    return out


def write_eval_outputs(
    verifier: MachineToolVerifier,
    summary_out: Path,
    details_out: Path,
    limit_eval_per_class: int | None,
) -> None:
    rows = []
    detail_rows = []
    for split in ("train", "test"):
        X, y, files = load_mt_with_files(split)
        X, y, files = select_limit(X, y, files, limit_eval_per_class, seed=1)
        for idx, (w, ci, fid) in enumerate(zip(X, y, files, strict=True)):
            cls = MT_CLASSES[int(ci)]
            report = verifier.verify(w, cls)
            failed = [name for name, gate in report["gates"].items() if not gate["passed"]]
            rows.append({
                "split": split,
                "class": cls,
                "raw_class_id": report["raw_class_id"],
                "display_name": report["display_name"],
                "feasible": bool(report["feasible"]),
                "failed_gates": failed,
            })
            detail_rows.append({
                "split": split,
                "class": cls,
                "raw_class_id": report["raw_class_id"],
                "display_name": report["display_name"],
                "index": idx,
                "file_id": fid,
                "feasible": bool(report["feasible"]),
                "failed_gates": "|".join(failed),
                "stats_axis_distance": report["scores"].get("stats_union", {}).get("axis_distance", np.nan),
                "stats_axis_threshold": report["scores"].get("stats_union", {}).get("axis_threshold", np.nan),
                "soft_spectrum_max_violation": report["scores"].get("soft_spectrum_max_violation", np.nan),
                "psd_w1_json": json.dumps(report["scores"].get("psd_w1", {}), separators=(",", ":")),
            })

    summary_out.parent.mkdir(parents=True, exist_ok=True)
    details_out.parent.mkdir(parents=True, exist_ok=True)
    summary = summarize_reports(rows)
    with summary_out.open("w", newline="") as fh:
        fieldnames = sorted({k for row in summary for k in row.keys()})
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary)
    with details_out.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(detail_rows[0].keys()))
        writer.writeheader()
        writer.writerows(detail_rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage", type=float, default=0.90)
    parser.add_argument("--calib-out", default=str(RUNS_DIR / "mt_verifier_c90.json"))
    parser.add_argument("--summary-out", default=str(RESULTS_DIR / "mt_verifier_real_pass.csv"))
    parser.add_argument("--details-out", default=str(RUNS_DIR / "mt_verifier_real_details.csv"))
    parser.add_argument("--limit-calib-per-class", type=int, default=None)
    parser.add_argument("--limit-eval-per-class", type=int, default=None)
    args = parser.parse_args()

    Xtr, ytr, files = load_mt_with_files("train")
    Xtr, ytr, files = select_limit(Xtr, ytr, files, args.limit_calib_per_class)
    verifier = MachineToolVerifier(coverage=args.coverage)
    verifier.calibrate(Xtr, ytr, files)
    calib_out = Path(args.calib_out)
    calib_out.parent.mkdir(parents=True, exist_ok=True)
    verifier.save(calib_out)
    write_eval_outputs(
        verifier,
        Path(args.summary_out),
        Path(args.details_out),
        args.limit_eval_per_class,
    )
    print(f"saved calibration: {calib_out}")
    print(f"saved summary: {args.summary_out}")
    print(f"saved details: {args.details_out}")


if __name__ == "__main__":
    main()
