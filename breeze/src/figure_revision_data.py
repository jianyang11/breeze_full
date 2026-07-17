"""Deterministic source-data builders for the preview-only Fig. 3+ revision.

The module reads frozen/formal evidence, performs no model training or API
call, and never writes to the manuscript's formal figure directory.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.signal import filtfilt, firwin, hilbert, welch
from scipy.stats import kurtosis

from config import CLASSES, CONDITIONS, FS, MAIN_COND, fault_freqs
from data import load_file_split


REPO = Path(__file__).resolve().parents[2]
PREVIEW = REPO / "breeze" / "paper" / "figs" / "revision_preview"
ANALYSIS = REPO / "analysis"
PHASE = REPO / "breeze" / "results" / "phaseA_v2_frozen_2026-07-06" / "breeze"
CWRU = REPO / "breeze" / "results" / "cwru_patch_v2_2026-07-07_frozen"
BERKELEY = REPO / "breeze" / "results" / "milling_berkeley_v2_binary_formal_2026-07-08"
PHYSICS = REPO / "breeze" / "results" / "ablation_2026-07-14"
ADMISSION_FREEZE = (
    REPO / "breeze" / "results" / "admission_round_freeze_2026-07-17"
)
PU_LOCO_V1 = REPO / "breeze" / "results" / "pu_loco_2026-07-07_v1_frozen"
PU_LOCO_V2 = REPO / "breeze" / "results" / "pu_loco_v2_2026-07-08"
PU_LOCO_V3 = REPO / "breeze" / "results" / "pu_loco_v3_2026-07-08"
PU_LOCO_V4 = REPO / "breeze" / "results" / "pu_loco_v4_s2_morphology_2026-07-13"
PU_LOCO_V5 = REPO / "breeze" / "results" / "pu_loco_v5_s4_extrapolation_verifier_2026-07-13"
PU_LOCO_V6 = REPO / "breeze" / "results" / "pu_loco_v6_cscoh_2026-07-14"

POOL_FILES = {
    "llm": PHASE / "runs" / "phaseA_v2_balanced" / "phaseA_v2_llm_k3_B150.npz",
    "rule": PHASE / "runs" / "phaseA_v2_balanced" / "phaseA_v2_rule_B150.npz",
    "random_open_loop": PHASE / "runs" / "phaseA_v2_balanced" / "phaseA_v2_random_open_loop_B150.npz",
}
METHOD_LABELS = {
    "real": "Real",
    "llm": "LLM",
    "rule": "Rule",
    "random_open_loop": "Random",
    "noise_aug": "Noise",
}
CLASS_LABELS = {
    "healthy": "Healthy",
    "OR": "Outer race",
    "IR": "Inner race",
    "B": "Ball",
    "degraded": "Degraded",
}
BOOTSTRAP_SEED = 20260716
BOOTSTRAP_RESAMPLES = 20_000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
    ).strip()


def _relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO.resolve()))
    except ValueError:
        return str(resolved)


def assert_allowed_sources(paths: Iterable[Path]) -> None:
    forbidden = (
        "/private/",
        "mt_private",
        "trained_baselines",
        "/smoke/",
        "smoke_v",
        "/partial/",
    )
    for path in paths:
        text = "/" + _relative(path).lower().strip("/") + "/"
        hits = [token for token in forbidden if token in text]
        if hits:
            raise RuntimeError(f"forbidden figure source {path}: {hits}")
        if not path.exists():
            raise FileNotFoundError(path)


def write_source_manifest(
    figure_dir: Path,
    source_paths: Iterable[Path],
    filters: dict,
    sample_counts: dict,
    outputs: Iterable[Path],
    *,
    status: str = "complete",
    notes: list[str] | None = None,
) -> Path:
    sources = sorted({Path(path).resolve() for path in source_paths})
    assert_allowed_sources(sources)
    code_paths = [Path(__file__).resolve()]
    plotting_module = REPO / "breeze" / "src" / "figures_revision_preview.py"
    if plotting_module.exists():
        code_paths.append(plotting_module.resolve())
    manifest = {
        "figure_directory": _relative(figure_dir),
        "status": status,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": git_head(),
        "generator": _relative(Path(__file__)),
        "generator_sha256": sha256(Path(__file__)),
        "code": [
            {
                "path": _relative(path),
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
            }
            for path in code_paths
        ],
        "sources": [
            {
                "path": _relative(path),
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
            }
            for path in sources
        ],
        "filters": filters,
        "sample_counts": sample_counts,
        "outputs": [
            {
                "path": _relative(Path(path)),
                "sha256": sha256(Path(path)),
                "size_bytes": Path(path).stat().st_size,
            }
            for path in outputs
            if Path(path).exists()
        ],
        "notes": notes or [],
    }
    path = figure_dir / "source-manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    return path


def all_formal_source_paths() -> list[Path]:
    paths = [
        REPO / "breeze" / "paper" / "main_cas.tex",
        REPO / "breeze" / "paper" / "main_cas.pdf",
        REPO / "breeze" / "src" / "figures.py",
        REPO / "breeze" / "src" / "figure_style.py",
        PHASE / "results" / "phaseA_v2_downstream_cnn.csv",
        PHASE / "results" / "phaseA_v2_wilcoxon.csv",
        CWRU / "cwru_patch_v2_summary.csv",
        CWRU / "cwru_patch_v2_wilcoxon.csv",
        BERKELEY / "berkeley_v2_binary_formal_summary.csv",
        BERKELEY / "berkeley_v2_binary_formal_wilcoxon_holm.csv",
        PHASE / "results" / "phaseA_v2_failure_gate_summary.csv",
        PU_LOCO_V1 / "pu_loco_wilcoxon.csv",
        PU_LOCO_V2 / "pu_loco_wilcoxon.csv",
        PU_LOCO_V3 / "morphology_condition_map.md",
        PU_LOCO_V4 / "s2_s1_acceptance_failure.md",
        PU_LOCO_V5 / "pu_loco_v5_failure_analysis.md",
        PU_LOCO_V6 / "source_separability_summary.csv",
    ]
    paths.extend(POOL_FILES.values())
    for dataset in ("pu", "cwru", "berkeley"):
        root = PHYSICS / f"physics_frozen_full_v3_{dataset}"
        paths.extend(
            root / name
            for name in (
                "physics_metrics.csv",
                "physics_pool_availability.csv",
                "physics_pool_manifest.csv",
            )
        )
    for method in ("llm", "rule", "noise_aug"):
        paths.append(CWRU / "downstream" / f"within_load0_{method}_nsyn20.csv")
        paths.append(
            BERKELEY
            / "downstream_40seed_nsyn20"
            / f"berkeley_v2_binary_{method}_nsyn20.csv"
        )
    for name in (
        "rescreen_v2_full",
        "recipe_ablation_rule_v2_full",
        "recipe_ablation_random_v2_full",
    ):
        paths.append(PHASE / "runs" / name / "slot_summary.csv")
    paths.extend(sorted((REPO / "breeze" / "paper" / "figs").glob("*.*")))
    return sorted(set(paths))


def freeze_baseline_hashes() -> Path:
    paths = all_formal_source_paths()
    assert_allowed_sources(paths)
    rows = [
        {
            "path": _relative(path),
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
        }
        for path in paths
    ]
    out = ANALYSIS / "figure_revision_baseline_sha256.csv"
    pd.DataFrame(rows).to_csv(out, index=False, lineterminator="\n")
    return out


def _stable_rng(*parts: object) -> np.random.Generator:
    key = "|".join(map(str, (BOOTSTRAP_SEED, *parts))).encode()
    seed = int.from_bytes(hashlib.sha256(key).digest()[:8], "little")
    return np.random.default_rng(seed)


def paired_bootstrap_ci(deltas: np.ndarray, *key: object) -> tuple[float, float]:
    values = np.asarray(deltas, dtype=float)
    if values.ndim != 1 or len(values) < 2 or not np.all(np.isfinite(values)):
        raise ValueError("paired bootstrap requires at least two finite deltas")
    rng = _stable_rng(*key)
    indices = rng.integers(0, len(values), size=(BOOTSTRAP_RESAMPLES, len(values)))
    means = values[indices].mean(axis=1)
    low, high = np.quantile(means, [0.025, 0.975])
    return float(low), float(high)


def _pair_methods(
    rows: pd.DataFrame,
    method_col: str,
    llm_name: str,
    comparator: str,
    shot: int,
    metric: str,
) -> pd.DataFrame:
    subset = rows[rows["n_real"].eq(shot)]
    llm = subset[subset[method_col].eq(llm_name)][["seed", metric]].rename(
        columns={metric: "llm"}
    )
    other = subset[subset[method_col].eq(comparator)][["seed", metric]].rename(
        columns={metric: "comparator"}
    )
    paired = llm.merge(other, on="seed", how="outer", validate="one_to_one", indicator=True)
    if not paired["_merge"].eq("both").all():
        raise RuntimeError(f"unpaired rows for {shot}/{metric}/{comparator}")
    paired = paired.drop(columns="_merge").sort_values("seed").reset_index(drop=True)
    paired["delta"] = paired["llm"] - paired["comparator"]
    return paired


def build_fig3_data() -> tuple[pd.DataFrame, pd.DataFrame, list[Path]]:
    pu_seed = PHASE / "results" / "phaseA_v2_downstream_cnn.csv"
    pu_test = PHASE / "results" / "phaseA_v2_wilcoxon.csv"
    cwru_test = CWRU / "cwru_patch_v2_wilcoxon.csv"
    berk_test = BERKELEY / "berkeley_v2_binary_formal_wilcoxon_holm.csv"
    source_paths = [pu_seed, pu_test, cwru_test, berk_test]

    pu = pd.read_csv(pu_seed)
    cwru_frames = []
    berkeley_frames = []
    for method in ("llm", "rule", "noise_aug"):
        path = CWRU / "downstream" / f"within_load0_{method}_nsyn20.csv"
        frame = pd.read_csv(path)
        frame["method"] = method
        cwru_frames.append(frame)
        source_paths.append(path)
        path = (
            BERKELEY
            / "downstream_40seed_nsyn20"
            / f"berkeley_v2_binary_{method}_nsyn20.csv"
        )
        frame = pd.read_csv(path)
        frame["method"] = method
        berkeley_frames.append(frame)
        source_paths.append(path)
    cwru = pd.concat(cwru_frames, ignore_index=True)
    berkeley = pd.concat(berkeley_frames, ignore_index=True)
    pu_tests = pd.read_csv(pu_test)
    cwru_tests = pd.read_csv(cwru_test)
    berk_tests = pd.read_csv(berk_test)

    specs = (
        ("PU", pu, "baseline", "phaseA_v2_llm_k3", (5, 10, 25),
         (("rule", "phaseA_v2_rule"), ("random_open_loop", "phaseA_v2_random_open_loop")), 20),
        ("CWRU", cwru, "method", "llm", (5, 10, 25),
         (("rule", "rule"), ("noise_aug", "noise_aug")), 40),
        ("Berkeley", berkeley, "method", "llm", (2, 5, 10),
         (("rule", "rule"), ("noise_aug", "noise_aug")), 40),
    )
    summary_rows: list[dict] = []
    seed_rows: list[dict] = []
    for dataset, rows, method_col, llm_name, shots, comparisons, expected_n in specs:
        for comparison_label, comparator_name in comparisons:
            for shot in shots:
                for metric in ("acc", "macro_f1"):
                    paired = _pair_methods(
                        rows, method_col, llm_name, comparator_name, shot, metric
                    )
                    if len(paired) != expected_n:
                        raise RuntimeError(
                            f"{dataset}/{shot}/{metric}: {len(paired)} != {expected_n}"
                        )
                    deltas = paired["delta"].to_numpy()
                    low, high = paired_bootstrap_ci(
                        deltas, dataset, comparison_label, shot, metric
                    )
                    if dataset == "PU":
                        comp = f"phaseA_v2_llm_k3>{comparator_name}"
                        test = pu_tests[
                            pu_tests["n_real"].eq(shot)
                            & pu_tests["metric"].eq(metric)
                            & pu_tests["comparison"].eq(comp)
                        ]
                        q = float(test.iloc[0]["holm_q_in_family"])
                        passed = q <= 0.05
                        registered_delta = float(test.iloc[0]["mean_delta"])
                    elif dataset == "CWRU":
                        test = cwru_tests[
                            cwru_tests["split"].eq("within_load0")
                            & cwru_tests["n_real"].eq(shot)
                            & cwru_tests["metric"].eq(metric)
                            & cwru_tests["comparison"].eq(f"llm>{comparison_label}")
                        ]
                        q = float(test.iloc[0]["holm_q_in_family"])
                        passed = bool(test.iloc[0]["passed_holm"])
                        registered_delta = float(test.iloc[0]["mean_delta"])
                    else:
                        metric_name = "Acc" if metric == "acc" else "Macro-F1"
                        test = berk_tests[
                            berk_tests["n_real"].eq(shot)
                            & berk_tests["metric"].eq(metric_name)
                            & berk_tests["comparison"].eq(f"llm>{comparison_label}")
                        ]
                        q = float(test.iloc[0]["holm_q"])
                        passed = bool(test.iloc[0]["pass"])
                        registered_delta = float(test.iloc[0]["mean_delta"])
                    if len(test) != 1:
                        raise RuntimeError(
                            f"registered test missing/duplicate: {dataset}/{shot}/{metric}/{comparison_label}"
                        )
                    effect = float(deltas.mean())
                    if not np.isclose(effect, registered_delta, atol=2e-5, rtol=0):
                        raise RuntimeError(
                            f"effect mismatch {dataset}/{shot}/{metric}/{comparison_label}: "
                            f"{effect} != {registered_delta}"
                        )
                    summary_rows.append(
                        {
                            "dataset": dataset,
                            "comparison": comparison_label,
                            "shot": shot,
                            "metric": metric,
                            "effect_pp": effect * 100,
                            "ci_low_pp": low * 100,
                            "ci_high_pp": high * 100,
                            "n_pairs": len(paired),
                            "holm_q": q,
                            "passed_holm": passed,
                            "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
                            "bootstrap_seed": BOOTSTRAP_SEED,
                        }
                    )
                    for row in paired.itertuples(index=False):
                        seed_rows.append(
                            {
                                "dataset": dataset,
                                "comparison": comparison_label,
                                "shot": shot,
                                "metric": metric,
                                "seed": int(row.seed),
                                "llm": float(row.llm),
                                "comparator": float(row.comparator),
                                "delta_pp": float(row.delta) * 100,
                            }
                        )
    return (
        pd.DataFrame(summary_rows).sort_values(
            ["dataset", "comparison", "shot", "metric"]
        ).reset_index(drop=True),
        pd.DataFrame(seed_rows).sort_values(
            ["dataset", "comparison", "shot", "metric", "seed"]
        ).reset_index(drop=True),
        source_paths,
    )


def _load_pool(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with np.load(path, allow_pickle=True) as data:
        x = np.asarray(data["X"], dtype=np.float64)
        y = np.asarray(data["y"], dtype=int)
    if x.shape != (450, 3, 2048) or y.shape != (450,):
        raise RuntimeError(f"unexpected PU pool shape in {path}: {x.shape}/{y.shape}")
    if [int(np.sum(y == i)) for i in range(3)] != [150, 150, 150]:
        raise RuntimeError(f"unbalanced PU pool: {path}")
    return x, y


def load_pu_sources() -> dict[str, tuple[np.ndarray, np.ndarray]]:
    real_x, real_y, _ = load_file_split("train", MAIN_COND)
    sources = {"real": (real_x.astype(np.float64), real_y.astype(int))}
    sources.update({name: _load_pool(path) for name, path in POOL_FILES.items()})
    expected = [1200, 1202, 1444]
    if [int(np.sum(real_y == i)) for i in range(3)] != expected:
        raise RuntimeError("PU outer-training class counts changed")
    return sources


def physical_feature_matrix(windows: np.ndarray) -> np.ndarray:
    rows = []
    for window in np.asarray(windows, dtype=np.float64):
        pieces = []
        for channel in window:
            rms = float(np.sqrt(np.mean(channel**2)))
            if rms <= 0:
                raise RuntimeError("physical medoid feature is undefined at zero RMS")
            freq, power = welch(channel, fs=FS, nperseg=min(512, len(channel)))
            mass = np.maximum(power, 0.0) * np.gradient(freq)
            if mass.sum() <= 0:
                raise RuntimeError("physical medoid PSD is undefined")
            cdf = np.cumsum(mass / mass.sum())
            pieces.append(np.log(rms))
            pieces.extend(cdf.tolist())
        rows.append(pieces)
    matrix = np.asarray(rows, dtype=float)
    if not np.all(np.isfinite(matrix)):
        raise RuntimeError("non-finite physical medoid feature")
    return matrix


def select_pu_medoids(
    sources: dict[str, tuple[np.ndarray, np.ndarray]], classes: tuple[str, ...]
) -> tuple[pd.DataFrame, dict[tuple[str, str], np.ndarray]]:
    records = []
    selected: dict[tuple[str, str], np.ndarray] = {}
    for cls in classes:
        class_index = CLASSES.index(cls)
        real_windows = sources["real"][0][sources["real"][1] == class_index]
        real_features = physical_feature_matrix(real_windows)
        reference_center = np.median(real_features, axis=0)
        mad = np.median(np.abs(real_features - reference_center), axis=0)
        keep = mad > 0
        if int(np.sum(keep)) < 2:
            raise RuntimeError(f"too few non-degenerate physical coordinates for {cls}")
        scale = 1.4826 * mad[keep]
        for source, (x, y) in sources.items():
            indexes = np.flatnonzero(y == class_index)
            windows = x[indexes]
            features = physical_feature_matrix(windows)
            z = (features[:, keep] - reference_center[keep]) / scale
            source_center = np.median(z, axis=0)
            distances = np.linalg.norm(z - source_center, axis=1) / np.sqrt(z.shape[1])
            local_index = int(np.argmin(distances))
            source_index = int(indexes[local_index])
            selected[(source, cls)] = x[source_index]
            records.append(
                {
                    "class": cls,
                    "class_index": class_index,
                    "source": source,
                    "source_index": source_index,
                    "class_local_index": local_index,
                    "distance_to_source_robust_center": float(distances[local_index]),
                    "n_source_class": len(indexes),
                    "n_features_total": features.shape[1],
                    "n_features_retained": int(np.sum(keep)),
                    "reference_split": "PU outer-training only",
                    "tie_break": "lowest source index",
                }
            )
    return pd.DataFrame(records), selected


def _population_envelope(windows: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    taps = firwin(129, [500.0 / (FS / 2), 2000.0 / (FS / 2)], pass_zero=False)
    vibration = np.asarray(windows[:, 0, :], dtype=float)
    filtered = filtfilt(taps, [1.0], vibration, axis=-1)
    envelope = np.abs(hilbert(filtered, axis=-1)) ** 2
    envelope -= envelope.mean(axis=-1, keepdims=True)
    spectrum = np.abs(np.fft.rfft(envelope * np.hanning(envelope.shape[1]), axis=-1))
    spectrum /= envelope.shape[1]
    frequency = np.fft.rfftfreq(envelope.shape[1], 1.0 / FS)
    keep = frequency <= 220.0
    return (
        frequency[keep],
        np.quantile(spectrum[:, keep], 0.25, axis=0),
        np.median(spectrum[:, keep], axis=0),
        np.quantile(spectrum[:, keep], 0.75, axis=0),
    )


def build_fig4_data(
    classes: tuple[str, ...] = ("OR", "IR"),
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[Path]]:
    sources = load_pu_sources()
    medoids, selected = select_pu_medoids(sources, classes)
    waveform_rows = []
    envelope_rows = []
    n_time = int(0.05 * FS)
    for cls in classes:
        class_index = CLASSES.index(cls)
        for source in ("real", "llm", "rule", "random_open_loop"):
            index = int(
                medoids[
                    medoids["class"].eq(cls) & medoids["source"].eq(source)
                ].iloc[0]["source_index"]
            )
            waveform = selected[(source, cls)][0, :n_time]
            for sample, amplitude in enumerate(waveform):
                waveform_rows.append(
                    {
                        "class": cls,
                        "source": source,
                        "source_index": index,
                        "sample": sample,
                        "time_ms": sample / FS * 1000.0,
                        "amplitude": float(amplitude),
                    }
                )
            x, y = sources[source]
            class_windows = x[y == class_index]
            frequency, q25, median, q75 = _population_envelope(class_windows)
            for f, lo, mid, hi in zip(frequency, q25, median, q75):
                envelope_rows.append(
                    {
                        "class": cls,
                        "source": source,
                        "frequency_hz": float(f),
                        "q25": float(lo),
                        "median": float(mid),
                        "q75": float(hi),
                        "n_windows": len(class_windows),
                        "demodulation_hz": "500-2000",
                    }
                )
    source_paths = [*POOL_FILES.values(), REPO / "breeze" / "src" / "data.py"]
    source_paths.extend(sorted((REPO / "proc").glob(f"{MAIN_COND}_*.npz")))
    return (
        medoids.sort_values(["class_index", "source"]).reset_index(drop=True),
        pd.DataFrame(waveform_rows),
        pd.DataFrame(envelope_rows),
        source_paths,
    )


def build_s1_data() -> tuple[pd.DataFrame, list[Path]]:
    sources = load_pu_sources()
    rows = []
    for class_index, cls in enumerate(CLASSES):
        for source, (x, y) in sources.items():
            windows = x[y == class_index, 0]
            rms = np.sqrt(np.mean(windows**2, axis=1))
            kur = kurtosis(windows, axis=1, fisher=False, bias=False)
            for metric, values in (("RMS", rms), ("Kurtosis", kur)):
                order = np.argsort(values, kind="mergesort")
                sorted_values = values[order]
                ecdf = np.arange(1, len(values) + 1) / len(values)
                for rank, (value, probability) in enumerate(zip(sorted_values, ecdf), 1):
                    rows.append(
                        {
                            "class": cls,
                            "source": source,
                            "metric": metric,
                            "rank": rank,
                            "value": float(value),
                            "ecdf": float(probability),
                            "n_windows": len(values),
                            "reference_split": "PU outer-training only" if source == "real" else "frozen pool",
                        }
                    )
    source_paths = [*POOL_FILES.values(), REPO / "breeze" / "src" / "data.py"]
    source_paths.extend(sorted((REPO / "proc").glob(f"{MAIN_COND}_*.npz")))
    return pd.DataFrame(rows), source_paths


FIG5_METRICS = (
    ("rms_w1", "RMS-W1"),
    ("kurtosis_w1", "Kurtosis-W1"),
    ("psd_w1_mean", "PSD-W1"),
    ("band_energy_relative_error_mean", "Band error"),
    ("envelope_frequency_alignment_error_hz", "Fault align."),
)


def build_fig5_data() -> tuple[pd.DataFrame, pd.DataFrame, list[Path]]:
    ratio_rows = []
    diversity_rows = []
    sources: list[Path] = []
    for dataset in ("pu", "cwru", "berkeley"):
        root = PHYSICS / f"physics_frozen_full_v3_{dataset}"
        metric_path = root / "physics_metrics.csv"
        availability_path = root / "physics_pool_availability.csv"
        pool_manifest_path = root / "physics_pool_manifest.csv"
        sources.extend((metric_path, availability_path, pool_manifest_path))
        metrics = pd.read_csv(metric_path)
        availability = pd.read_csv(availability_path)
        available = availability[availability["status"].eq("available")]["pool"].tolist()
        classes = metrics["class"].drop_duplicates().tolist()
        for method in [name for name in ("llm", "noise_aug", "random_open_loop") if name in available]:
            for cls in classes:
                for metric, label in FIG5_METRICS:
                    numerator = metrics[
                        metrics["pool"].eq(method)
                        & metrics["class"].eq(cls)
                        & metrics["metric"].eq(metric)
                    ]
                    denominator = metrics[
                        metrics["pool"].eq("rule")
                        & metrics["class"].eq(cls)
                        & metrics["metric"].eq(metric)
                    ]
                    if numerator.empty or denominator.empty:
                        ratio_rows.append(
                            {
                                "dataset": dataset,
                                "method": method,
                                "class": cls,
                                "metric": metric,
                                "metric_label": label,
                                "method_distance": np.nan,
                                "rule_distance": np.nan,
                                "log2_ratio": np.nan,
                                "n_pool": int(
                                    metrics[
                                        metrics["pool"].eq(method)
                                        & metrics["class"].eq(cls)
                                    ]["n_pool"].iloc[0]
                                ),
                                "status": "NA: metric unavailable",
                            }
                        )
                        continue
                    if len(numerator) != 1 or len(denominator) != 1:
                        raise RuntimeError(f"duplicate physical cell {dataset}/{method}/{cls}/{metric}")
                    num = float(numerator.iloc[0]["value"])
                    den = float(denominator.iloc[0]["value"])
                    if num <= 0 or den <= 0:
                        raise RuntimeError(f"non-positive physical distance {dataset}/{method}/{cls}/{metric}")
                    ratio_rows.append(
                        {
                            "dataset": dataset,
                            "method": method,
                            "class": cls,
                            "metric": metric,
                            "metric_label": label,
                            "method_distance": num,
                            "rule_distance": den,
                            "log2_ratio": float(np.log2(num / den)),
                            "n_pool": int(numerator.iloc[0]["n_pool"]),
                            "status": "available",
                        }
                    )
        for cls in classes:
            reference = metrics[
                metrics["class"].eq(cls)
                & metrics["metric"].eq("real_nn_diversity")
            ]
            if reference.empty:
                raise RuntimeError(f"missing real NN diversity {dataset}/{cls}")
            if not np.allclose(reference["value"], reference.iloc[0]["value"]):
                raise RuntimeError(f"inconsistent real NN diversity {dataset}/{cls}")
            diversity_rows.append(
                {
                    "dataset": dataset,
                    "class": cls,
                    "method": "real_reference",
                    "nn_diversity": float(reference.iloc[0]["value"]),
                    "n_pool": int(reference.iloc[0]["n_reference"]),
                    "direction": "no universal optimum",
                }
            )
            for method in available:
                cell = metrics[
                    metrics["pool"].eq(method)
                    & metrics["class"].eq(cls)
                    & metrics["metric"].eq("nn_diversity")
                ]
                if len(cell) != 1:
                    raise RuntimeError(f"missing NN diversity {dataset}/{method}/{cls}")
                diversity_rows.append(
                    {
                        "dataset": dataset,
                        "class": cls,
                        "method": method,
                        "nn_diversity": float(cell.iloc[0]["value"]),
                        "n_pool": int(cell.iloc[0]["n_pool"]),
                        "direction": "no universal optimum",
                    }
                )
    return pd.DataFrame(ratio_rows), pd.DataFrame(diversity_rows), sources


def build_fig6_data() -> tuple[pd.DataFrame, pd.DataFrame, list[Path]]:
    cumulative_path = ADMISSION_FREEZE / "cumulative_admission_by_class.csv"
    slots_path = ADMISSION_FREEZE / "slot_first_pass_round.csv"
    manifest_path = ADMISSION_FREEZE / "round_records_manifest.csv"
    validation_path = ADMISSION_FREEZE / "validation_report.json"
    canonical_summary = PHASE / "runs" / "rescreen_v2_full" / "slot_summary.csv"
    sources = [
        cumulative_path,
        slots_path,
        manifest_path,
        validation_path,
        canonical_summary,
    ]
    assert_allowed_sources(sources)

    cumulative = pd.read_csv(cumulative_path)
    slots = pd.read_csv(slots_path)
    manifest = pd.read_csv(manifest_path)
    validation = json.loads(validation_path.read_text())
    summary = pd.read_csv(canonical_summary)

    if validation.get("status") != "passed":
        raise RuntimeError("round-level admission freeze did not pass validation")
    assertions = validation.get("assertions", {})
    if assertions.get("record_json_count") != 450:
        raise RuntimeError("round-record count changed")
    if assertions.get("final_admitted_slots") != 286:
        raise RuntimeError("round-record admitted total changed")
    if not assertions.get("selected_equals_first_feasible_candidate"):
        raise RuntimeError("selected/first-feasible validation is not true")
    if not assertions.get("slot_summary_rows_match_exactly"):
        raise RuntimeError("round records no longer match the frozen slot summary")

    if len(manifest) != 450 or manifest[["class", "slot"]].duplicated().any():
        raise RuntimeError("round-record manifest is incomplete or duplicated")
    if not manifest["sha256"].str.fullmatch(r"[0-9a-f]{64}").all():
        raise RuntimeError("round-record manifest contains an invalid SHA-256")
    if len(slots) != 450 or slots[["class", "slot"]].duplicated().any():
        raise RuntimeError("round-level slot aggregate is incomplete or duplicated")
    expected_classes = {"healthy", "OR", "IR"}
    if set(slots["class"]) != expected_classes:
        raise RuntimeError("round-level slot classes changed")
    if slots.groupby("class").size().to_dict() != {
        "IR": 150,
        "OR": 150,
        "healthy": 150,
    }:
        raise RuntimeError("round-level class slot counts changed")
    admitted = slots["first_pass_round"].notna()
    if int(admitted.sum()) != 286 or not slots["final_admitted"].eq(admitted).all():
        raise RuntimeError("round-level admitted flags do not match first-pass rounds")
    if not slots.loc[admitted, "first_pass_round"].isin([0, 1, 2, 3]).all():
        raise RuntimeError("first-pass round outside K=0..3")

    slot_join = slots.merge(
        summary,
        on=["class", "slot"],
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    if not slot_join["_merge"].eq("both").all():
        raise RuntimeError("round-level slots do not cover the frozen slot summary")
    if not slot_join["final_admitted"].eq(
        slot_join["accepted_before_diversity"]
    ).all():
        raise RuntimeError("round-level admission differs from frozen slot summary")
    if not slot_join["n_candidates_x"].eq(slot_join["n_candidates_y"]).all():
        raise RuntimeError("round-level candidate counts differ from frozen summary")
    if not slot_join["n_feasible_expansions_x"].eq(
        slot_join["n_feasible_expansions_y"]
    ).all():
        raise RuntimeError("round-level feasible expansions differ from frozen summary")

    expected_columns = {
        "feedback_round_k",
        "class",
        "newly_admitted",
        "cumulative_admitted",
        "total_slots",
        "cumulative_rate",
    }
    if set(cumulative.columns) != expected_columns or len(cumulative) != 16:
        raise RuntimeError("unexpected cumulative-admission table schema")
    for class_name, total in {
        "healthy": 150,
        "OR": 150,
        "IR": 150,
        "all": 450,
    }.items():
        rows = cumulative[cumulative["class"].eq(class_name)].sort_values(
            "feedback_round_k"
        )
        if rows["feedback_round_k"].tolist() != [0, 1, 2, 3]:
            raise RuntimeError(f"missing feedback round for {class_name}")
        if set(rows["total_slots"]) != {total}:
            raise RuntimeError(f"denominator changed for {class_name}")
        if not rows["cumulative_admitted"].is_monotonic_increasing:
            raise RuntimeError(f"non-monotone cumulative admission for {class_name}")
        expected_cumulative = rows["newly_admitted"].cumsum().to_numpy()
        np.testing.assert_array_equal(
            expected_cumulative, rows["cumulative_admitted"].to_numpy()
        )
        np.testing.assert_allclose(
            rows["cumulative_rate"].to_numpy(),
            rows["cumulative_admitted"].to_numpy() / total,
            atol=5e-13,
            rtol=0,
        )
    final_all = cumulative[
        cumulative["class"].eq("all") & cumulative["feedback_round_k"].eq(3)
    ].iloc[0]
    if int(final_all["cumulative_admitted"]) != 286:
        raise RuntimeError("K=3 cumulative admission changed")
    return cumulative, slots, sources


def build_fig7_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[Path]]:
    cwru_path = CWRU / "cwru_patch_v2_wilcoxon.csv"
    cwru = pd.read_csv(cwru_path)
    cwru = cwru[
        cwru["split"].isin(["lolo_load1", "lolo_load2", "lolo_load3"])
        & cwru["comparison"].eq("llm>rule")
    ].copy()
    if len(cwru) != 18:
        raise RuntimeError(f"expected 18 CWRU cross-load cells, found {len(cwru)}")
    cwru["heldout_load"] = cwru["split"].str.extract(r"load(\d+)").astype(int)
    cwru["effect_pp"] = cwru["mean_delta"] * 100
    cwru_out = cwru[
        [
            "split", "heldout_load", "n_real", "metric", "effect_pp",
            "holm_q_in_family", "passed_holm", "n_pairs",
        ]
    ].sort_values(["metric", "heldout_load", "n_real"])

    pu_rows = []
    for version, root in (("v1", PU_LOCO_V1), ("v2", PU_LOCO_V2)):
        data = pd.read_csv(root / "pu_loco_wilcoxon.csv")
        if len(data) != 96:
            raise RuntimeError(f"{version}: expected 96 PU LOCO rows")
        for (split, shot, metric), cell in data.groupby(
            ["split", "n_real", "metric"], sort=True
        ):
            if len(cell) != 4:
                raise RuntimeError(f"{version}/{split}/{shot}/{metric}: expected four comparisons")
            passed = cell["passed_holm"].astype(bool) & cell["mean_delta"].gt(0)
            pu_rows.append(
                {
                    "version": version,
                    "split": split,
                    "condition": split.removeprefix("loco_"),
                    "n_real": int(shot),
                    "metric": metric,
                    "passed_count": int(passed.sum()),
                    "registered_comparisons": 4,
                }
            )
    pu_out = pd.DataFrame(pu_rows).sort_values(
        ["version", "condition", "n_real", "metric"]
    )

    v1 = pd.read_csv(PU_LOCO_V1 / "pu_loco_wilcoxon.csv")
    v2 = pd.read_csv(PU_LOCO_V2 / "pu_loco_wilcoxon.csv")
    v6 = pd.read_csv(PU_LOCO_V6 / "source_separability_summary.csv")
    terminal = len(
        set(v6.loc[v6["target_terminal_cscoh_failure"].astype(bool), "target_condition"])
    )
    if terminal != 4:
        raise RuntimeError(f"expected four terminal PU v6 targets, found {terminal}")
    chain = pd.DataFrame(
        [
            {"stage": "v1", "scope": "formal held-out", "outcome": f"{int((~(v1['passed_holm'].astype(bool) & v1['mean_delta'].gt(0))).sum())}/96 fail", "formal": True},
            {"stage": "v2", "scope": "formal held-out", "outcome": f"{int((~(v2['passed_holm'].astype(bool) & v2['mean_delta'].gt(0))).sum())}/96 fail", "formal": True},
            {"stage": "v3", "scope": "train-only development", "outcome": "morphology map; no balanced pool", "formal": False},
            {"stage": "v4", "scope": "train-only admission", "outcome": "S1/S2 candidate pools fail", "formal": False},
            {"stage": "v5", "scope": "train-only sanity", "outcome": "wrong-label/noise controls admitted", "formal": False},
            {"stage": "v6", "scope": "source-only evidence", "outcome": f"CSCoh stop in {terminal}/4 targets", "formal": False},
        ]
    )
    source_paths = [
        cwru_path,
        PU_LOCO_V1 / "pu_loco_wilcoxon.csv",
        PU_LOCO_V2 / "pu_loco_wilcoxon.csv",
        PU_LOCO_V3 / "morphology_condition_map.md",
        PU_LOCO_V4 / "s2_s1_acceptance_failure.md",
        PU_LOCO_V5 / "pu_loco_v5_failure_analysis.md",
        PU_LOCO_V6 / "source_separability_summary.csv",
    ]
    return cwru_out.reset_index(drop=True), pu_out.reset_index(drop=True), chain, source_paths


if __name__ == "__main__":
    path = freeze_baseline_hashes()
    print(path)
