"""Compute protocol-aligned physical-fidelity and diversity metrics.

This is an evaluation-only script.  It reads frozen outer-training data and
frozen/generated pools, writes a new dated result directory, and never calls
an LLM or modifies a source pool.  For each protocol it fixes the same
per-class synthetic budget used by the downstream experiment before computing
metrics, so pool-size differences cannot drive the comparison.

Metrics are reference-relative and class-conditional:

* bearing pools: envelope target-frequency alignment, RMS/kurtosis W1, PSD-CDF
  W1, band-energy relative error, and nearest-neighbour diversity;
* Berkeley milling: TPF-amplitude W1, RMS W1, PSD-CDF W1, band-energy relative
  error, and nearest-neighbour diversity.

The report explicitly records unavailable comparators instead of substituting
an unrelated pool.  Smoke-only trained-baseline pools are excluded.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from scipy.signal import firwin, filtfilt, hilbert, welch
from scipy.stats import kurtosis, wasserstein_distance


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "breeze" / "src"
sys.path.insert(0, str(SRC))

from config import FS, fault_freqs  # noqa: E402
from data import load_file_split  # noqa: E402


PU_POOL_ROOT = ROOT / "breeze" / "results" / "phaseA_v2_frozen_2026-07-06" / "breeze" / "runs" / "phaseA_v2_balanced"
CWRU_LLM_POOL = ROOT / "breeze" / "runs" / "phaseB_cwru_within_load0_llm_full_v1_combined" / "pool.npz"
CWRU_RULE_POOL = ROOT / "breeze" / "runs" / "phaseB_cwru_within_load0_rule_pilot_v1" / "pool.npz"
BERKELEY_LLM_POOL = ROOT / "breeze" / "runs" / "milling_berkeley_v2_binary_formal_2026-07-08_v11_repair_eq_coherent" / "berkeley" / "llm" / "pool.npz"
BERKELEY_RULE_POOL = ROOT / "breeze" / "runs" / "milling_berkeley_v2_binary_formal_2026-07-08_rule_random" / "berkeley" / "rule" / "pool.npz"
BERKELEY_RANDOM_POOL = ROOT / "breeze" / "runs" / "milling_berkeley_v2_binary_formal_2026-07-08_rule_random" / "berkeley" / "random_open_loop" / "pool.npz"


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    train_loader: Callable[[], tuple[np.ndarray, np.ndarray, list[str]]]
    fs_hz: float
    budget_per_class: int
    family: str
    band_edges: tuple[tuple[float, float], ...]
    bearing_targets: dict[int, float | None] | None = None
    tpf_hz: float | None = None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_path = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp_path = Path(raw_path)
    try:
        tmp_path.write_text(content)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def load_npz(path: Path) -> tuple[np.ndarray, np.ndarray, list[str]]:
    data = np.load(path, allow_pickle=True)
    key = "X" if "X" in data.files else "windows"
    x = data[key].astype(np.float32)
    y = data["y"].astype(np.int64)
    if "class_names" in data.files:
        names = [str(value) for value in data["class_names"]]
    elif "metadata" in data.files:
        mapping: dict[int, str] = {}
        for class_id, raw in zip(y, data["metadata"]):
            record = json.loads(str(raw))
            mapping.setdefault(int(class_id), str(record.get("label", record.get("class", ""))))
        names = [mapping[index] for index in sorted(mapping)]
    else:
        raise RuntimeError(f"missing class_names and metadata in {path}")
    return x, y, names


def load_pu() -> tuple[np.ndarray, np.ndarray, list[str]]:
    x, y, _ = load_file_split("train", "N09_M07_F10")
    return x.astype(np.float32), y.astype(np.int64), ["healthy", "OR", "IR"]


def load_cwru() -> tuple[np.ndarray, np.ndarray, list[str]]:
    return load_npz(ROOT / "proc" / "cwru_de12k_within_load0_train.npz")


def load_berkeley() -> tuple[np.ndarray, np.ndarray, list[str]]:
    return load_npz(ROOT / "proc" / "milling_berkeley_v2_binary_train.npz")


def psd_cdf(x: np.ndarray, fs_hz: float) -> tuple[np.ndarray, np.ndarray]:
    freq, power = welch(x, fs=fs_hz, nperseg=min(512, len(x)))
    power = np.maximum(power, 0.0)
    mass = power * np.gradient(freq)
    mass = mass / (mass.sum() + 1e-30)
    cdf = np.cumsum(mass)
    return freq, cdf / (cdf[-1] + 1e-30)


def psd_w1(x: np.ndarray, ref_cdf: np.ndarray, fs_hz: float) -> float:
    freq, cdf = psd_cdf(x, fs_hz)
    if len(cdf) != len(ref_cdf):
        raise RuntimeError("PSD grids differ; metric is undefined")
    return float(np.trapezoid(np.abs(cdf - ref_cdf), freq))


def band_fractions(x: np.ndarray, fs_hz: float, bands: tuple[tuple[float, float], ...]) -> np.ndarray:
    freq, power = welch(x, fs=fs_hz, nperseg=min(512, len(x)))
    total = np.trapezoid(power, freq) + 1e-30
    values = []
    for lo, hi in bands:
        mask = (freq >= lo) & (freq < hi)
        values.append(float(np.trapezoid(power[mask], freq[mask]) / total) if np.any(mask) else 0.0)
    return np.asarray(values, dtype=float)


def envelope_peak_error(x: np.ndarray, fs_hz: float, target_hz: float, band: tuple[float, float]) -> float:
    nyquist = fs_hz / 2.0
    if not 0 < band[0] < band[1] < nyquist:
        raise RuntimeError(f"invalid envelope band {band} for fs={fs_hz}")
    taps = firwin(129, [band[0] / nyquist, band[1] / nyquist], pass_zero=False)
    filtered = filtfilt(taps, [1.0], x)
    envelope = np.abs(hilbert(filtered)) ** 2
    spectrum = np.abs(np.fft.rfft((envelope - envelope.mean()) * np.hanning(len(envelope))))
    freq = np.fft.rfftfreq(len(envelope), d=1.0 / fs_hz)
    tolerance = max(2.0 * (freq[1] - freq[0]), 0.02 * target_hz)
    mask = (freq >= target_hz - tolerance) & (freq <= target_hz + tolerance)
    if not np.any(mask):
        raise RuntimeError(f"target frequency {target_hz} Hz is outside measurable envelope grid")
    return float(abs(freq[mask][np.argmax(spectrum[mask])] - target_hz))


def fft_ratio(x: np.ndarray, fs_hz: float, target_hz: float) -> float:
    if not 0 < target_hz < 0.48 * fs_hz:
        raise RuntimeError(f"TPF {target_hz} is unavailable at fs={fs_hz}")
    centered = x - np.mean(x)
    freq = np.fft.rfftfreq(len(centered), d=1.0 / fs_hz)
    amplitude = np.abs(np.fft.rfft(centered * np.hanning(len(centered)))) / len(centered)
    tolerance = max(2.0 * (freq[1] - freq[0]), 0.03 * target_hz)
    mask = (freq >= target_hz - tolerance) & (freq <= target_hz + tolerance)
    return float(amplitude[mask].max() / (np.sqrt(np.mean(centered**2)) + 1e-30))


def standard_feature_matrix(x: np.ndarray, fs_hz: float) -> np.ndarray:
    """Return the finite physical vector used for nearest-neighbour diversity.

    Kurtosis is deliberately not included here.  It is reported separately as
    a distributional fidelity metric, but is mathematically undefined for a
    constant (or numerically constant) window.  The diversity vector therefore
    consists only of quantities defined for every finite window: log RMS and
    the PSD CDF for every channel.
    """
    rows = []
    for window in x:
        pieces = []
        for channel in window:
            rms = np.sqrt(np.mean(channel**2))
            pieces.append(np.log(rms + 1e-30))
            _, cdf = psd_cdf(channel, fs_hz)
            pieces.extend(cdf.tolist())
        rows.append(pieces)
    return np.asarray(rows, dtype=float)


def mean_nearest_neighbor_distance(features: np.ndarray) -> float:
    if len(features) < 2:
        raise RuntimeError("nearest-neighbour diversity requires at least two samples")
    # This is the exact all-pairs Euclidean nearest-neighbour calculation.
    # The Gram formulation avoids allocating an n x n x feature_dim tensor for
    # high-dimensional PSD-CDF embeddings.
    norms = np.einsum("ij,ij->i", features, features)
    minima = np.empty(len(features), dtype=float)
    block_size = 64
    for start in range(0, len(features), block_size):
        stop = min(start + block_size, len(features))
        block = features[start:stop]
        squared = norms[start:stop, None] + norms[None, :] - 2.0 * (block @ features.T)
        squared[np.arange(stop - start), np.arange(start, stop)] = np.inf
        minima[start:stop] = np.minimum(squared.min(axis=1), np.inf)
    return float(np.sqrt(np.maximum(minima, 0.0)).mean())


def deterministic_sample(x: np.ndarray, y: np.ndarray, n_per_class: int, n_classes: int, seed: int) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    rng = np.random.default_rng(seed)
    chosen, manifest = [], []
    for class_id in range(n_classes):
        indexes = np.where(y == class_id)[0]
        if len(indexes) < n_per_class:
            raise RuntimeError(f"class {class_id}: need {n_per_class} pool samples, found {len(indexes)}")
        picks = np.sort(rng.choice(indexes, n_per_class, replace=False))
        chosen.extend(picks.tolist())
        manifest.extend({"class_id": class_id, "source_index": int(index), "rank": rank} for rank, index in enumerate(picks))
    selected = np.asarray(chosen, dtype=int)
    return x[selected], y[selected], manifest


def build_noise_pool(x_ref: np.ndarray, y_ref: np.ndarray, n_per_class: int, n_classes: int, seed: int) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    rng = np.random.default_rng(seed)
    channel_std = x_ref.std(axis=(0, 2), keepdims=True) + 1e-8
    pools, labels, manifest = [], [], []
    for class_id in range(n_classes):
        indexes = np.where(y_ref == class_id)[0]
        picks = rng.choice(indexes, n_per_class, replace=True)
        base = x_ref[picks]
        scale = rng.normal(1.0, 0.04, size=(n_per_class, 1, 1)).astype(np.float32)
        jitter = rng.normal(0.0, 0.03, size=base.shape).astype(np.float32) * channel_std
        pools.append((base * scale + jitter).astype(np.float32))
        labels.append(np.full(n_per_class, class_id, dtype=np.int64))
        manifest.extend({"class_id": class_id, "source_index": int(index), "rank": rank} for rank, index in enumerate(picks))
    return np.concatenate(pools), np.concatenate(labels), manifest


def save_noise_pool(path: Path, x: np.ndarray, y: np.ndarray, class_names: list[str]) -> None:
    if path.exists():
        old_x, old_y, old_names = load_npz(path)
        if np.array_equal(old_x, x) and np.array_equal(old_y, y) and old_names == class_names:
            return
        raise RuntimeError(f"refusing to overwrite a different deterministic noise pool: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, X=x, y=y, class_names=np.asarray(class_names))


def bearing_metrics(
    pool: np.ndarray,
    ref: np.ndarray,
    fs_hz: float,
    bands: tuple[tuple[float, float], ...],
    target_hz: float | None,
) -> dict[str, float]:
    reference_cdf = np.median(np.asarray([psd_cdf(window[0], fs_hz)[1] for window in ref]), axis=0)
    reference_rms = np.sqrt(np.mean(ref[:, 0, :] ** 2, axis=1))
    reference_kurt = np.asarray([kurtosis(window[0], fisher=False, bias=False) for window in ref])
    ref_bands = np.asarray([band_fractions(window[0], fs_hz, bands) for window in ref])
    pool_bands = np.asarray([band_fractions(window[0], fs_hz, bands) for window in pool])
    ref_features = standard_feature_matrix(ref, fs_hz)
    pool_features = standard_feature_matrix(pool, fs_hz)
    center = np.median(ref_features, axis=0)
    scale = np.std(ref_features, axis=0)
    scale = np.where(scale > 1e-10, scale, 1.0)
    out = {
        "rms_w1": float(wasserstein_distance(reference_rms, np.sqrt(np.mean(pool[:, 0, :] ** 2, axis=1)))),
        "kurtosis_w1": float(wasserstein_distance(reference_kurt, np.asarray([kurtosis(window[0], fisher=False, bias=False) for window in pool]))),
        "psd_w1_mean": float(np.mean([psd_w1(window[0], reference_cdf, fs_hz) for window in pool])),
        "band_energy_relative_error_mean": float(np.mean(np.abs(pool_bands.mean(axis=0) - ref_bands.mean(axis=0)) / (np.abs(ref_bands.mean(axis=0)) + 1e-12))),
        "nn_diversity": mean_nearest_neighbor_distance((pool_features - center) / scale),
        "real_nn_diversity": mean_nearest_neighbor_distance((ref_features - center) / scale),
    }
    if target_hz is not None:
        out["envelope_frequency_alignment_error_hz"] = float(
            np.mean([envelope_peak_error(window[0], fs_hz, target_hz, (500.0, min(3_800.0, fs_hz / 2.0 - 10.0))) for window in pool])
        )
    return out


def milling_metrics(
    pool: np.ndarray,
    ref: np.ndarray,
    fs_hz: float,
    bands: tuple[tuple[float, float], ...],
    tpf_hz: float,
) -> dict[str, float]:
    n_channels = ref.shape[1]
    ref_rms = np.sqrt(np.mean(ref**2, axis=2))
    pool_rms = np.sqrt(np.mean(pool**2, axis=2))
    rms_w1 = [wasserstein_distance(ref_rms[:, channel], pool_rms[:, channel]) for channel in range(n_channels)]
    tpf_w1 = []
    psd_values = []
    band_errors = []
    for channel in range(n_channels):
        ref_tpf = np.asarray([fft_ratio(window[channel], fs_hz, tpf_hz) for window in ref])
        pool_tpf = np.asarray([fft_ratio(window[channel], fs_hz, tpf_hz) for window in pool])
        tpf_w1.append(wasserstein_distance(ref_tpf, pool_tpf))
        ref_cdf = np.median(np.asarray([psd_cdf(window[channel], fs_hz)[1] for window in ref]), axis=0)
        psd_values.extend(psd_w1(window[channel], ref_cdf, fs_hz) for window in pool)
        ref_bands = np.asarray([band_fractions(window[channel], fs_hz, bands) for window in ref])
        pool_bands = np.asarray([band_fractions(window[channel], fs_hz, bands) for window in pool])
        band_errors.extend(np.abs(pool_bands.mean(axis=0) - ref_bands.mean(axis=0)) / (np.abs(ref_bands.mean(axis=0)) + 1e-12))
    ref_features = standard_feature_matrix(ref, fs_hz)
    pool_features = standard_feature_matrix(pool, fs_hz)
    center = np.median(ref_features, axis=0)
    scale = np.std(ref_features, axis=0)
    scale = np.where(scale > 1e-10, scale, 1.0)
    return {
        "tpf_amplitude_ratio_w1": float(np.mean(tpf_w1)),
        "rms_w1": float(np.mean(rms_w1)),
        "psd_w1_mean": float(np.mean(psd_values)),
        "band_energy_relative_error_mean": float(np.mean(band_errors)),
        "nn_diversity": mean_nearest_neighbor_distance((pool_features - center) / scale),
        "real_nn_diversity": mean_nearest_neighbor_distance((ref_features - center) / scale),
    }


def specs() -> dict[str, DatasetSpec]:
    pu_freqs = fault_freqs(900.0 / 60.0)
    cwru_rpm = 1796.0
    cwru_hz = cwru_rpm / 60.0
    return {
        "pu": DatasetSpec(
            name="PU Phase-A v2",
            train_loader=load_pu,
            fs_hz=float(FS),
            budget_per_class=150,
            family="bearing",
            band_edges=((0.0, 500.0), (500.0, 1500.0), (1500.0, 2500.0), (2500.0, 4000.0)),
            bearing_targets={0: None, 1: float(pu_freqs["BPFO"]), 2: float(pu_freqs["BPFI"])},
        ),
        "cwru": DatasetSpec(
            name="CWRU within-load0",
            train_loader=load_cwru,
            fs_hz=12_000.0,
            budget_per_class=20,
            family="bearing",
            band_edges=((0.0, 1000.0), (1000.0, 3000.0), (3000.0, 5000.0), (5000.0, 6000.0)),
            bearing_targets={0: None, 1: 5.4152 * cwru_hz, 2: 4.7135 * cwru_hz, 3: 3.5848 * cwru_hz},
        ),
        "berkeley": DatasetSpec(
            name="Berkeley v2 binary",
            train_loader=load_berkeley,
            fs_hz=250.0,
            budget_per_class=20,
            family="milling",
            band_edges=((0.0, 8.0), (8.0, 20.0), (20.0, 40.0), (40.0, 70.0), (70.0, 100.0), (100.0, 125.0)),
            tpf_hz=6.0 * 826.0 / 60.0,
        ),
    }


def frozen_pool_paths(dataset: str) -> dict[str, Path | None]:
    if dataset == "pu":
        return {
            "llm": PU_POOL_ROOT / "phaseA_v2_llm_k3_B150.npz",
            "rule": PU_POOL_ROOT / "phaseA_v2_rule_B150.npz",
            "random_open_loop": PU_POOL_ROOT / "phaseA_v2_random_open_loop_B150.npz",
        }
    if dataset == "cwru":
        return {"llm": CWRU_LLM_POOL, "rule": CWRU_RULE_POOL, "random_open_loop": None}
    if dataset == "berkeley":
        return {"llm": BERKELEY_LLM_POOL, "rule": BERKELEY_RULE_POOL, "random_open_loop": BERKELEY_RANDOM_POOL}
    raise ValueError(dataset)


def write_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite existing output: {path}")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--datasets", nargs="+", choices=["pu", "cwru", "berkeley"], default=["pu", "cwru", "berkeley"])
    parser.add_argument("--seed", type=int, default=20260714)
    parser.add_argument("--metric-n-per-class", type=int, help="optional diagnostic pool size; formal runs omit this flag")
    parser.add_argument("--trained-root")
    args = parser.parse_args()

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    metric_path = out_dir / "physics_metrics.csv"
    manifest_path = out_dir / "physics_pool_manifest.csv"
    availability_path = out_dir / "physics_pool_availability.csv"
    report_path = out_dir / "physics_metrics_report.md"
    if any(path.exists() for path in (metric_path, manifest_path, availability_path, report_path)):
        raise SystemExit("physics output already exists; use a new dated result directory")

    metrics: list[dict] = []
    manifests: list[dict] = []
    availability: list[dict] = []
    config = specs()
    for dataset in args.datasets:
        spec = config[dataset]
        metric_n = args.metric_n_per_class or spec.budget_per_class
        if metric_n <= 1:
            raise RuntimeError("metric-n-per-class must be at least two")
        x_ref, y_ref, class_names = spec.train_loader()
        n_classes = len(class_names)
        if set(np.unique(y_ref)) != set(range(n_classes)):
            raise RuntimeError(f"reference labels are incomplete for {dataset}")
        pool_map = frozen_pool_paths(dataset)
        noise_x, noise_y, noise_manifest = build_noise_pool(x_ref, y_ref, metric_n, n_classes, args.seed)
        noise_path = out_dir / "deterministic_noise_pools" / f"{dataset}_noise_aug_n{metric_n}.npz"
        save_noise_pool(noise_path, noise_x, noise_y, class_names)
        pool_map["noise_aug"] = noise_path
        for method, path in pool_map.items():
            if path is None:
                availability.append({"dataset": dataset, "pool": method, "status": "unavailable", "reason": "no matching frozen pool exists for this protocol"})
                continue
            if not path.exists():
                availability.append({"dataset": dataset, "pool": method, "status": "unavailable", "reason": f"missing source: {path.relative_to(ROOT)}"})
                continue
            x_pool, y_pool, names = load_npz(path)
            if names != class_names:
                raise RuntimeError(f"class names differ for {dataset}/{method}: {names} != {class_names}")
            if method == "noise_aug":
                selected_x, selected_y, selected_manifest = x_pool, y_pool, noise_manifest
                source_kind = "deterministic_noise_aug_outer_train"
            elif dataset == "pu" and metric_n == spec.budget_per_class:
                selected_x, selected_y = x_pool, y_pool
                selected_manifest = [
                    {"class_id": int(class_id), "source_index": int(index), "rank": int(rank)}
                    for class_id in range(n_classes)
                    for rank, index in enumerate(np.where(y_pool == class_id)[0].tolist())
                ]
                source_kind = "frozen_balanced_pool"
            else:
                selected_x, selected_y, selected_manifest = deterministic_sample(
                    x_pool, y_pool, metric_n, n_classes, args.seed
                )
                source_kind = "deterministic_metric_subsample_of_frozen_pool"
            availability.append({"dataset": dataset, "pool": method, "status": "available", "reason": source_kind})
            for record in selected_manifest:
                manifests.append(
                    {
                        "dataset": dataset,
                        "pool": method,
                        "pool_path": str(path.relative_to(ROOT)),
                        "pool_sha256": sha256(path),
                        "source_kind": source_kind,
                        **record,
                    }
                )
            for class_id, class_name in enumerate(class_names):
                class_pool = selected_x[selected_y == class_id]
                class_ref = x_ref[y_ref == class_id]
                if spec.family == "bearing":
                    assert spec.bearing_targets is not None
                    values = bearing_metrics(
                        class_pool,
                        class_ref,
                        spec.fs_hz,
                        spec.band_edges,
                        spec.bearing_targets[class_id],
                    )
                else:
                    assert spec.tpf_hz is not None
                    values = milling_metrics(class_pool, class_ref, spec.fs_hz, spec.band_edges, spec.tpf_hz)
                for metric, value in values.items():
                    metrics.append(
                        {
                            "dataset": dataset,
                            "protocol": spec.name,
                            "pool": method,
                            "class": class_name,
                            "n_pool": int(len(class_pool)),
                            "n_reference": int(len(class_ref)),
                            "metric": metric,
                            "value": f"{value:.10g}",
                        }
                    )

    if args.trained_root:
        trained_root = Path(args.trained_root).resolve()
        manifest = json.loads((trained_root / "run_manifest.json").read_text())
        if manifest.get("smoke"):
            raise RuntimeError("smoke-only trained-baseline pools are prohibited from physics metrics")
        raise RuntimeError("formal trained-baseline ingestion is enabled only after its protocol report is frozen")

    write_rows(metric_path, metrics, ["dataset", "protocol", "pool", "class", "n_pool", "n_reference", "metric", "value"])
    write_rows(manifest_path, manifests, ["dataset", "pool", "pool_path", "pool_sha256", "source_kind", "class_id", "source_index", "rank"])
    write_rows(availability_path, availability, ["dataset", "pool", "status", "reason"])
    report_lines = [
        "# Physics Metrics Report",
        "",
        "Status: preliminary zero-API report for frozen recipe pools. Trained-baseline pools are intentionally absent until their formal 40-seed run is complete; smoke pools are excluded.",
        "",
        "## Protocol",
        "",
        "Each metric compares a class-conditional synthetic pool against the matching outer-training reference. The pool size is fixed per run and recorded in the machine-readable manifest. Noise augmentation is regenerated deterministically from the same outer-training data and the registered scale/jitter transform; its manifest is saved alongside the metrics.",
        "",
        "## Availability",
        "",
        "| dataset | pool | status | reason |",
        "|---|---|---|---|",
    ]
    report_lines.extend(f"| {row['dataset']} | {row['pool']} | {row['status']} | {row['reason']} |" for row in availability)
    report_lines.extend(
        [
            "",
            "## Metric definitions",
            "",
            "- `envelope_frequency_alignment_error_hz`: mean nearest envelope-spectrum peak error at the class's registered bearing frequency; it is not applicable to healthy windows.",
            "- `rms_w1` and `kurtosis_w1`: Wasserstein-1 distance between synthetic and real window-level distributions.",
            "- `psd_w1_mean`: mean Wasserstein distance between a synthetic PSD CDF and the real class median PSD CDF.",
            "- `band_energy_relative_error_mean`: mean relative error of class-mean PSD-band energy fractions.",
            "- `nn_diversity`: mean nearest-neighbour distance among synthetic log-RMS and PSD-CDF feature vectors after real-reference scaling; `real_nn_diversity` is the corresponding real-reference value. Kurtosis is excluded from this vector because it is undefined for constant windows, while `kurtosis_w1` remains a separate fidelity metric.",
            "- Berkeley additionally uses `tpf_amplitude_ratio_w1`, evaluated at its documented 826 rpm and six-tooth TPF.",
            "",
            "Machine-readable values: `physics_metrics.csv`; exact source and sampling provenance: `physics_pool_manifest.csv`.",
        ]
    )
    atomic_text(report_path, "\n".join(report_lines) + "\n")
    print(json.dumps({"metrics": str(metric_path), "rows": len(metrics), "report": str(report_path)}, indent=2))


if __name__ == "__main__":
    main()
