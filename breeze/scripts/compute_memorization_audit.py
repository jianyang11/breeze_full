"""Audit frozen synthetic pools against class-matched real training windows.

This is a zero-API, evaluation-only audit. It consumes the exact pool selections
recorded by the frozen physics-v3 manifests and never modifies a source pool or
training split. Per-sample rows are append-only and keyed for safe resume.

The audit deliberately separates three questions:

* exact equality: byte-identical float32 window and shape;
* nearest raw distance: class-reference-standardized waveform RMSE;
* maximum similarity: global-energy-normalized multichannel cross-correlation
  over every linear lag.

It also reports synthetic-to-real distance in the same real-scaled log-RMS and
PSD-CDF feature space used by the existing within-pool diversity metric. No
post-hoc threshold converts a high correlation or small distance into a binary
copy claim; only exact equality is binary.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.fft import irfft, next_fast_len, rfft


ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = ROOT / "breeze" / "results" / "ablation_2026-07-14"

from compute_physics_metrics import (  # noqa: E402
    frozen_pool_paths,
    load_npz,
    sha256,
    specs,
    standard_feature_matrix,
)


PHYSICS_DIRS = {
    "pu": RESULT_ROOT / "physics_frozen_full_v3_pu",
    "cwru": RESULT_ROOT / "physics_frozen_full_v3_cwru",
    "berkeley": RESULT_ROOT / "physics_frozen_full_v3_berkeley",
}
DETAIL_FIELDS = [
    "dataset",
    "protocol",
    "pool",
    "class",
    "class_id",
    "rank",
    "source_index",
    "pool_path",
    "pool_sha256",
    "n_reference",
    "nearest_raw_reference_index",
    "nearest_raw_nrmse",
    "nearest_feature_reference_index",
    "nearest_feature_distance",
    "max_xcorr_reference_index",
    "max_abs_normalized_xcorr",
    "max_xcorr_lag_samples",
    "exact_copy",
    "exact_copy_reference_index",
]


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp = Path(raw)
    try:
        tmp.write_text(content)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def window_digest(window: np.ndarray) -> str:
    value = np.ascontiguousarray(window, dtype=np.float32)
    digest = hashlib.sha256()
    digest.update(np.asarray(value.shape, dtype=np.int64).tobytes())
    digest.update(value.tobytes())
    return digest.hexdigest()


@dataclass(frozen=True)
class PoolItem:
    class_id: int
    rank: int
    source_index: int
    window: np.ndarray


class ReferenceIndex:
    """Read-only class reference prepared once for all synthetic windows."""

    def __init__(self, windows: np.ndarray, global_indices: np.ndarray, fs_hz: float):
        if windows.ndim != 3 or len(windows) == 0:
            raise ValueError(f"reference must be nonempty (n, channels, samples), got {windows.shape}")
        if len(global_indices) != len(windows):
            raise ValueError("reference/global-index length mismatch")
        self.windows = np.ascontiguousarray(windows, dtype=np.float32)
        self.global_indices = np.asarray(global_indices, dtype=np.int64)
        self.fs_hz = float(fs_hz)
        self.channels = int(windows.shape[1])
        self.length = int(windows.shape[2])

        channel_mean = self.windows.mean(axis=(0, 2), dtype=np.float64)
        channel_scale = self.windows.std(axis=(0, 2), dtype=np.float64)
        channel_scale = np.where(channel_scale > 1e-12, channel_scale, 1.0)
        standardized = (self.windows.astype(np.float64) - channel_mean[None, :, None]) / channel_scale[None, :, None]
        self.channel_mean = channel_mean
        self.channel_scale = channel_scale
        self.raw_flat = standardized.reshape(len(self.windows), -1)
        self.raw_norm2 = np.einsum("ij,ij->i", self.raw_flat, self.raw_flat)

        features = standard_feature_matrix(self.windows, self.fs_hz)
        self.feature_center = np.median(features, axis=0)
        feature_scale = np.std(features, axis=0)
        self.feature_scale = np.where(feature_scale > 1e-10, feature_scale, 1.0)
        self.feature_z = (features - self.feature_center) / self.feature_scale
        self.feature_norm2 = np.einsum("ij,ij->i", self.feature_z, self.feature_z)

        centered = self.windows.astype(np.float64) - self.windows.mean(axis=2, keepdims=True, dtype=np.float64)
        self.xcorr_norm = np.sqrt(np.einsum("nct,nct->n", centered, centered))
        if np.any(self.xcorr_norm <= 1e-15):
            raise RuntimeError("cross-correlation reference contains a constant multichannel window")
        self.nfft = int(next_fast_len(2 * self.length - 1))
        self.reference_fft = rfft(centered, n=self.nfft, axis=-1)
        self.valid_fft_positions = np.concatenate(
            [np.arange(0, self.length), np.arange(self.nfft - self.length + 1, self.nfft)]
        )
        self.valid_lags = np.concatenate(
            [np.arange(0, self.length), np.arange(-(self.length - 1), 0)]
        )

        hashes: dict[str, list[int]] = {}
        for local_index, window in enumerate(self.windows):
            hashes.setdefault(window_digest(window), []).append(local_index)
        self.hashes = hashes

    def raw_nearest(self, window: np.ndarray) -> tuple[int, float]:
        standardized = (window.astype(np.float64) - self.channel_mean[:, None]) / self.channel_scale[:, None]
        flat = standardized.reshape(-1)
        squared = self.raw_norm2 + float(flat @ flat) - 2.0 * (self.raw_flat @ flat)
        local = int(np.argmin(squared))
        nrmse = float(np.sqrt(max(float(squared[local]), 0.0) / flat.size))
        return int(self.global_indices[local]), nrmse

    def feature_nearest(self, window: np.ndarray) -> tuple[int, float]:
        feature = standard_feature_matrix(window[None], self.fs_hz)[0]
        z = (feature - self.feature_center) / self.feature_scale
        squared = self.feature_norm2 + float(z @ z) - 2.0 * (self.feature_z @ z)
        local = int(np.argmin(squared))
        return int(self.global_indices[local]), float(np.sqrt(max(float(squared[local]), 0.0)))

    def maximum_xcorr(self, window: np.ndarray) -> tuple[int, float, int]:
        centered = window.astype(np.float64) - window.mean(axis=1, keepdims=True, dtype=np.float64)
        norm = float(np.sqrt(np.einsum("ct,ct->", centered, centered)))
        if norm <= 1e-15:
            raise RuntimeError("cross-correlation candidate is constant across all channels")
        candidate_fft = rfft(centered, n=self.nfft, axis=-1)
        cross_spectrum = (self.reference_fft * np.conjugate(candidate_fft[None, :, :])).sum(axis=1)
        correlation = irfft(cross_spectrum, n=self.nfft, axis=-1)
        valid = correlation[:, self.valid_fft_positions] / (self.xcorr_norm[:, None] * norm)
        flat_index = int(np.argmax(np.abs(valid)))
        local_reference, lag_index = np.unravel_index(flat_index, valid.shape)
        return (
            int(self.global_indices[local_reference]),
            float(abs(valid[local_reference, lag_index])),
            int(self.valid_lags[lag_index]),
        )

    def exact_match(self, window: np.ndarray) -> tuple[bool, int | None]:
        for local in self.hashes.get(window_digest(window), []):
            if np.array_equal(np.asarray(window, dtype=np.float32), self.windows[local]):
                return True, int(self.global_indices[local])
        return False, None


def physics_manifest(dataset: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    root = PHYSICS_DIRS[dataset]
    manifest = read_csv(root / "physics_pool_manifest.csv")
    availability = read_csv(root / "physics_pool_availability.csv")
    if any(row["dataset"] != dataset for row in manifest + availability):
        raise RuntimeError(f"dataset mismatch in physics-v3 manifest for {dataset}")
    return manifest, availability


def selected_pool_items(dataset: str, pool: str, manifest: list[dict[str, str]]) -> tuple[list[PoolItem], Path, str]:
    rows = sorted(
        (row for row in manifest if row["pool"] == pool),
        key=lambda row: (int(row["class_id"]), int(row["rank"])),
    )
    if not rows:
        raise RuntimeError(f"no physics-v3 manifest rows for {dataset}/{pool}")
    pool_paths = {row["pool_path"] for row in rows}
    pool_hashes = {row["pool_sha256"] for row in rows}
    source_kinds = {row["source_kind"] for row in rows}
    if len(pool_paths) != 1 or len(pool_hashes) != 1 or len(source_kinds) != 1:
        raise RuntimeError(f"non-unique source provenance for {dataset}/{pool}")
    path = ROOT / next(iter(pool_paths))
    expected_hash = next(iter(pool_hashes))
    if not path.exists() or sha256(path) != expected_hash:
        raise RuntimeError(f"pool source/hash mismatch for {dataset}/{pool}: {path}")
    x_pool, y_pool, _ = load_npz(path)
    source_kind = next(iter(source_kinds))
    items: list[PoolItem] = []
    for row in rows:
        class_id = int(row["class_id"])
        rank = int(row["rank"])
        source_index = int(row["source_index"])
        if source_kind == "deterministic_noise_aug_outer_train":
            class_indexes = np.where(y_pool == class_id)[0]
            if rank >= len(class_indexes):
                raise RuntimeError(f"noise rank out of range for {dataset}/{pool}/{class_id}/{rank}")
            pool_index = int(class_indexes[rank])
        else:
            pool_index = source_index
        if int(y_pool[pool_index]) != class_id:
            raise RuntimeError(f"manifest class mismatch for {dataset}/{pool}/{source_index}")
        items.append(PoolItem(class_id=class_id, rank=rank, source_index=source_index, window=x_pool[pool_index]))
    return items, path, expected_hash


def completed_keys(path: Path) -> set[tuple[str, str, int, int]]:
    if not path.exists():
        return set()
    keys: set[tuple[str, str, int, int]] = set()
    for row in read_csv(path):
        key = (row["dataset"], row["pool"], int(row["class_id"]), int(row["rank"]))
        if key in keys:
            raise RuntimeError(f"duplicate memorization checkpoint row: {key}")
        keys.add(key)
    return keys


def audit_item(
    dataset: str,
    protocol: str,
    pool: str,
    class_name: str,
    class_id: int,
    item: PoolItem,
    pool_path: Path,
    pool_hash: str,
    reference: ReferenceIndex,
) -> dict[str, Any]:
    raw_reference, raw_nrmse = reference.raw_nearest(item.window)
    feature_reference, feature_distance = reference.feature_nearest(item.window)
    xcorr_reference, xcorr, lag = reference.maximum_xcorr(item.window)
    exact, exact_reference = reference.exact_match(item.window)
    return {
        "dataset": dataset,
        "protocol": protocol,
        "pool": pool,
        "class": class_name,
        "class_id": class_id,
        "rank": item.rank,
        "source_index": item.source_index,
        "pool_path": str(pool_path.relative_to(ROOT)),
        "pool_sha256": pool_hash,
        "n_reference": len(reference.windows),
        "nearest_raw_reference_index": raw_reference,
        "nearest_raw_nrmse": f"{raw_nrmse:.10g}",
        "nearest_feature_reference_index": feature_reference,
        "nearest_feature_distance": f"{feature_distance:.10g}",
        "max_xcorr_reference_index": xcorr_reference,
        "max_abs_normalized_xcorr": f"{xcorr:.10g}",
        "max_xcorr_lag_samples": lag,
        "exact_copy": str(bool(exact)),
        "exact_copy_reference_index": "" if exact_reference is None else exact_reference,
    }


def summarize(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault((row["dataset"], row["pool"], row["class"]), []).append(row)
    output: list[dict[str, Any]] = []
    for (dataset, pool, class_name), group in sorted(groups.items()):
        raw = np.asarray([float(row["nearest_raw_nrmse"]) for row in group])
        feature = np.asarray([float(row["nearest_feature_distance"]) for row in group])
        correlation = np.asarray([float(row["max_abs_normalized_xcorr"]) for row in group])
        output.append(
            {
                "dataset": dataset,
                "pool": pool,
                "class": class_name,
                "n_synthetic": len(group),
                "n_reference": int(group[0]["n_reference"]),
                "exact_copy_count": sum(row["exact_copy"] == "True" for row in group),
                "raw_nrmse_min": f"{raw.min():.10g}",
                "raw_nrmse_median": f"{np.median(raw):.10g}",
                "feature_distance_min": f"{feature.min():.10g}",
                "feature_distance_median": f"{np.median(feature):.10g}",
                "max_abs_xcorr": f"{correlation.max():.10g}",
                "median_max_abs_xcorr": f"{np.median(correlation):.10g}",
            }
        )
    return output


def write_summary(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "dataset",
        "pool",
        "class",
        "n_synthetic",
        "n_reference",
        "exact_copy_count",
        "raw_nrmse_min",
        "raw_nrmse_median",
        "feature_distance_min",
        "feature_distance_median",
        "max_abs_xcorr",
        "median_max_abs_xcorr",
    ]
    lines = [",".join(fields)]
    for row in rows:
        lines.append(",".join(str(row[field]) for field in fields))
    atomic_text(path, "\n".join(lines) + "\n")


def write_report(path: Path, summary: list[dict[str, Any]], availability: list[dict[str, str]], smoke: bool) -> None:
    lines = [
        "# Synthetic-to-real memorization audit",
        "",
        f"Status: {'smoke only; not manuscript evidence' if smoke else 'complete zero-API frozen-pool audit'}.",
        "",
        "The audit uses the exact synthetic selections in the physics-v3 manifests and class-matched outer-training windows. `raw_nrmse` is RMSE after class-reference per-channel standardization. `feature_distance` uses the same real-scaled log-RMS/PSD-CDF representation as the within-pool diversity metric, but measures synthetic-to-real distance. `max_abs_xcorr` is the largest absolute global-energy-normalized multichannel cross-correlation over all linear lags. Only byte-identical float32 equality is called an exact copy; no distance or correlation cutoff was selected after viewing results.",
        "",
        "## Availability",
        "",
        "| dataset | pool | status | reason |",
        "|---|---|---|---|",
    ]
    lines.extend(f"| {row['dataset']} | {row['pool']} | {row['status']} | {row['reason']} |" for row in availability)
    lines.extend(
        [
            "",
            "## Per-class summary",
            "",
            "| dataset | pool | class | n syn/ref | exact | min NRMSE | min feature distance | max |xcorr| |",
            "|---|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    lines.extend(
        f"| {row['dataset']} | {row['pool']} | {row['class']} | {row['n_synthetic']}/{row['n_reference']} | "
        f"{row['exact_copy_count']} | {float(row['raw_nrmse_min']):.4f} | {float(row['feature_distance_min']):.4f} | "
        f"{float(row['max_abs_xcorr']):.4f} |"
        for row in summary
    )
    lines.extend(["", "Machine-readable per-sample results are in `memorization_per_sample.csv`."])
    atomic_text(path, "\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--datasets", nargs="+", choices=sorted(PHYSICS_DIRS), default=sorted(PHYSICS_DIRS))
    parser.add_argument("--pools", nargs="+", default=["llm", "rule", "random_open_loop", "noise_aug"])
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--max-synthetic-per-class", type=int)
    parser.add_argument("--max-reference-per-class", type=int)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if args.workers <= 0:
        raise SystemExit("workers must be positive")
    if not args.smoke and (args.max_synthetic_per_class or args.max_reference_per_class):
        raise SystemExit("pool/reference caps are smoke-only")

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    detail_path = out_dir / "memorization_per_sample.csv"
    summary_path = out_dir / "memorization_summary.csv"
    availability_path = out_dir / "memorization_availability.csv"
    report_path = out_dir / "memorization_report.md"
    config_path = out_dir / "run_config.json"
    config = {
        "datasets": args.datasets,
        "pools": args.pools,
        "workers": args.workers,
        "max_synthetic_per_class": args.max_synthetic_per_class,
        "max_reference_per_class": args.max_reference_per_class,
        "smoke": args.smoke,
        "metric_selection": "physics_frozen_full_v3 manifests",
        "api_calls": 0,
    }
    if config_path.exists():
        if json.loads(config_path.read_text()) != config:
            raise SystemExit("run_config mismatch; use a new output directory")
    else:
        atomic_text(config_path, json.dumps(config, indent=2, sort_keys=True) + "\n")

    done = completed_keys(detail_path)
    if not detail_path.exists():
        with detail_path.open("w", newline="") as handle:
            csv.DictWriter(handle, fieldnames=DETAIL_FIELDS, lineterminator="\n").writeheader()

    all_availability: list[dict[str, str]] = []
    spec_map = specs()
    with detail_path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=DETAIL_FIELDS, lineterminator="\n")
        for dataset in args.datasets:
            spec = spec_map[dataset]
            x_ref, y_ref, class_names = spec.train_loader()
            manifest, availability = physics_manifest(dataset)
            availability_lookup = {row["pool"]: row for row in availability}
            for pool in args.pools:
                available = availability_lookup.get(pool)
                if available is None:
                    raise RuntimeError(f"missing availability row for {dataset}/{pool}")
                all_availability.append(dict(available))
                if available["status"] != "available":
                    continue
                items, pool_path, pool_hash = selected_pool_items(dataset, pool, manifest)
                for class_id, class_name in enumerate(class_names):
                    class_items = sorted(
                        (item for item in items if item.class_id == class_id),
                        key=lambda item: item.rank,
                    )
                    if args.max_synthetic_per_class:
                        class_items = class_items[: args.max_synthetic_per_class]
                    reference_global = np.where(y_ref == class_id)[0]
                    if args.max_reference_per_class:
                        reference_global = reference_global[: args.max_reference_per_class]
                    reference = ReferenceIndex(x_ref[reference_global], reference_global, spec.fs_hz)
                    pending = [
                        item
                        for item in class_items
                        if (dataset, pool, class_id, item.rank) not in done
                    ]
                    if not pending:
                        continue
                    def evaluate(item: PoolItem) -> dict[str, Any]:
                        return audit_item(
                            dataset,
                            spec.name,
                            pool,
                            class_name,
                            class_id,
                            item,
                            pool_path,
                            pool_hash,
                            reference,
                        )
                    with ThreadPoolExecutor(max_workers=args.workers) as executor:
                        for row in executor.map(evaluate, pending):
                            writer.writerow(row)
                            handle.flush()
                            done.add((dataset, pool, class_id, int(row["rank"])))
                    print(f"{dataset}/{pool}/{class_name}: {len(class_items)} complete", flush=True)

    rows = read_csv(detail_path)
    summary = summarize(rows)
    write_summary(summary_path, summary)
    availability_fields = ["dataset", "pool", "status", "reason"]
    availability_lines = [",".join(availability_fields)] + [
        ",".join(row[field] for field in availability_fields) for row in all_availability
    ]
    atomic_text(availability_path, "\n".join(availability_lines) + "\n")
    write_report(report_path, summary, all_availability, args.smoke)


if __name__ == "__main__":
    main()
