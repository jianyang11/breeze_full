"""Private machine-tool LLM closed-loop inner-validation smoke.

This is deliberately isolated from the frozen formal test files (file IDs 7
and 8).  It implements the protocol frozen in the v2 smoke request: a single
development split (1/2/4/5 -> inner train, 10 -> inner validation), a compact
recipe-only LLM interface, deterministic class-conditional rendering, and
train-only verifier/admission calibration.  It is not a formal test runner.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
import torch
import torch.nn as nn
from scipy.stats import wilcoxon
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

SCRIPT_DIR = Path(__file__).resolve().parent
BREEZE_DIR = SCRIPT_DIR.parent
ROOT = BREEZE_DIR.parent
sys.path.insert(0, str(BREEZE_DIR / "src"))

from config import LLM_BASE_URL, LLM_MIN_INTERVAL, LLM_MODEL  # noqa: E402
from data_mt import (  # noqa: E402
    CLASS_ID_TO_DISPLAY_NAME,
    MT_CHANNELS,
    MT_CLASSES,
    MT_DIR,
    RAW_CLASS_IDS,
    WIN_MT,
    class_name_to_raw_id,
    parse_mt_filename,
)
from models import SimpleCNN  # noqa: E402
from mt_verifier import (  # noqa: E402
    MachineToolVerifier,
    feature_names,
    psd_w1_norm,
    soft_spectrum_vector,
    stat_vector,
    structure_vector,
)


STAGE_DATE = "2026-07-10"
OUT_DIR = BREEZE_DIR / "results" / f"mt_private_v2_llm_smoke_{STAGE_DATE}"
RUN_DIR = BREEZE_DIR / "runs" / f"mt_private_v2_llm_smoke_{STAGE_DATE}"
INNER_TRAIN_FILE_IDS = ("1", "2", "4", "5")
INNER_VAL_FILE_ID = "10"
FORBIDDEN_FILE_IDS = {"7", "8"}
API_START_CUMULATIVE = 1071
API_STAGE_BUDGET = 60
N_BANDS = 8
RECIPE_KEYS = {
    "class_name",
    "template_rank",
    "channel_std_mult",
    "channel_mean_shift_std",
    "soft_band_gain",
    "spectral_mix",
    "noise_gain",
    "shared_component_gain",
    "trend_strength",
    "phase_randomization_strength",
    "rationale",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def stable_seed(*parts: object) -> int:
    payload = "|".join(map(str, parts)).encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest()[:16], 16) % (2**32)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def json_ready(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(v) for v in value]
    return value


def ensure_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name in ("recipes", "attempts", "accepted", "rejected", "pools", "checkpoints"):
        (RUN_DIR / name).mkdir(parents=True, exist_ok=True)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_ready(value), indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows([{key: json_ready(value) for key, value in row.items()} for row in rows])


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def windowize(array: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if array.ndim != 2 or array.shape[1] != len(MT_CHANNELS):
        raise ValueError(f"expected raw CSV shape (n,{len(MT_CHANNELS)}), got {array.shape}")
    stride = 1024
    count = (len(array) - WIN_MT) // stride + 1
    if count < 1:
        return np.empty((0, len(MT_CHANNELS), WIN_MT), dtype=np.float32), np.empty(0, dtype=int)
    starts = np.arange(count, dtype=int) * stride
    windows = np.stack([array[start:start + WIN_MT].T for start in starts]).astype(np.float32)
    return windows, starts


@dataclass
class DevData:
    X_train: np.ndarray
    y_train: np.ndarray
    train_files: np.ndarray
    train_starts: np.ndarray
    file_rows: list[dict[str, Any]]
    files_read: list[str]


def _find_single_csv(raw_class_id: str, file_id: str) -> Path:
    if file_id in FORBIDDEN_FILE_IDS:
        raise RuntimeError(f"formal test file ID {file_id} is forbidden in private-MT v2 smoke")
    matches = []
    for path in sorted(MT_DIR.glob(f"{raw_class_id}_{file_id}*.csv")):
        parsed = parse_mt_filename(path)
        if parsed.get("parse_ok") and str(parsed["raw_class_id"]) == raw_class_id and str(parsed["file_id"]) == file_id:
            matches.append(path)
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one allowed CSV for class={raw_class_id}, file={file_id}; found {matches}")
    return matches[0]


def load_development_train() -> DevData:
    xs, ys, files, starts_all, rows, files_read = [], [], [], [], [], []
    for ci, raw_id in enumerate(RAW_CLASS_IDS):
        for file_id in INNER_TRAIN_FILE_IDS:
            path = _find_single_csv(raw_id, file_id)
            raw = np.genfromtxt(path, delimiter=",", skip_header=1, dtype=np.float32)
            windows, starts = windowize(raw)
            if not len(windows):
                raise RuntimeError(f"{path.name} cannot produce a {WIN_MT}-sample window")
            files_read.append(path.name)
            xs.append(windows)
            ys.append(np.full(len(windows), ci, dtype=np.int64))
            source = f"{raw_id}_{file_id}"
            files.append(np.full(len(windows), source, dtype=object))
            starts_all.append(starts)
            rows.append({
                "split": "inner_train",
                "raw_class_id": raw_id,
                "class_name": MT_CLASSES[ci],
                "display_name": CLASS_ID_TO_DISPLAY_NAME[raw_id],
                "file_id": file_id,
                "source_file": path.name,
                "n_rows": int(len(raw)),
                "window_count": int(len(windows)),
            })
    return DevData(
        X_train=np.concatenate(xs),
        y_train=np.concatenate(ys),
        train_files=np.concatenate(files),
        train_starts=np.concatenate(starts_all),
        file_rows=rows,
        files_read=files_read,
    )


def load_inner_validation() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[dict[str, Any]], list[str]]:
    xs, ys, files, starts_all, rows, files_read = [], [], [], [], [], []
    for ci, raw_id in enumerate(RAW_CLASS_IDS):
        path = _find_single_csv(raw_id, INNER_VAL_FILE_ID)
        raw = np.genfromtxt(path, delimiter=",", skip_header=1, dtype=np.float32)
        windows, starts = windowize(raw)
        if not len(windows):
            raise RuntimeError(f"{path.name} cannot produce a {WIN_MT}-sample window")
        files_read.append(path.name)
        xs.append(windows)
        ys.append(np.full(len(windows), ci, dtype=np.int64))
        files.append(np.full(len(windows), f"{raw_id}_{INNER_VAL_FILE_ID}", dtype=object))
        starts_all.append(starts)
        rows.append({
            "split": "inner_val",
            "raw_class_id": raw_id,
            "class_name": MT_CLASSES[ci],
            "display_name": CLASS_ID_TO_DISPLAY_NAME[raw_id],
            "file_id": INNER_VAL_FILE_ID,
            "source_file": path.name,
            "n_rows": int(len(raw)),
            "window_count": int(len(windows)),
        })
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(files), np.concatenate(starts_all), rows, files_read


def robust_scale(values: np.ndarray, axis: int = 0) -> np.ndarray:
    q25 = np.quantile(values, 0.25, axis=axis)
    q75 = np.quantile(values, 0.75, axis=axis)
    scale = (q75 - q25) / 1.349
    fallback = np.std(values, axis=axis) + 1e-9
    return np.where(scale > 1e-10, scale, fallback)


def feature_matrix(windows: np.ndarray) -> np.ndarray:
    return np.asarray([structure_vector(window) for window in windows], dtype=np.float64)


def channel_stats(windows: np.ndarray) -> dict[str, Any]:
    output: dict[str, Any] = {}
    stats_by_window = np.asarray([[list(stat_vector(w)[ch * 6:(ch + 1) * 6]) for ch in range(len(MT_CHANNELS))] for w in windows])
    soft = np.asarray([soft_spectrum_vector(w).reshape(len(MT_CHANNELS), N_BANDS) for w in windows])
    for ch, name in enumerate(MT_CHANNELS):
        output[name] = {
            key: float(np.median(stats_by_window[:, ch, ki]))
            for ki, key in enumerate(("rms", "peak", "std", "kurtosis", "skewness", "crest"))
        }
        output[name]["soft_band_median"] = [float(v) for v in np.median(soft[:, ch], axis=0)]
    return output


def class_exemplar_statistics(dev: DevData, verifier: MachineToolVerifier) -> tuple[dict[str, Any], dict[str, Any]]:
    matrices = feature_matrix(dev.X_train)
    names = feature_names()
    ordered_names = names["stats"] + names["ratios"] + names["corr"] + names["soft"]
    result: dict[str, Any] = {
        "provenance": {
            "split": "inner_train only",
            "file_ids": list(INNER_TRAIN_FILE_IDS),
            "sampling_rate_hz": 4000,
            "window": WIN_MT,
            "normalised_frequency_only": True,
            "formal_test_files_excluded": sorted(FORBIDDEN_FILE_IDS),
        },
        "classes": {},
    }
    medians: dict[str, np.ndarray] = {}
    scales: dict[str, np.ndarray] = {}
    for ci, cls in enumerate(MT_CLASSES):
        idx = dev.y_train == ci
        windows = dev.X_train[idx]
        struct = matrices[idx]
        median = np.median(struct, axis=0)
        scale = robust_scale(struct)
        z = (struct - median) / scale
        dmat = np.sqrt(np.sum((z[:, None] - z[None, :]) ** 2, axis=-1))
        np.fill_diagonal(dmat, np.inf)
        nn = dmat.min(axis=1)
        cal = verifier.calib["classes"][cls]
        w1 = []
        for ch in range(len(MT_CHANNELS)):
            ref = np.asarray(cal["psd_w1"]["ref_cdf"][ch])
            w1.append([psd_w1_norm(window[ch], ref) for window in windows])
        raw_id = class_name_to_raw_id(cls)
        result["classes"][cls] = {
            "raw_class_id": raw_id,
            "display_name": CLASS_ID_TO_DISPLAY_NAME[raw_id],
            "n_windows": int(len(windows)),
            "channel_median_statistics": channel_stats(windows),
            "channel_energy_ratio_median": [float(v) for v in np.median(struct[:, 24:28], axis=0)],
            "channel_correlation_median": [float(v) for v in np.median(struct[:, 28:34], axis=0)],
            "robust_class_centroid": [float(v) for v in median],
            "robust_class_scale": [float(v) for v in scale],
            "real_real_nearest_neighbor": {
                "q05": float(np.quantile(nn, 0.05)),
                "median": float(np.median(nn)),
                "q95": float(np.quantile(nn, 0.95)),
            },
            "psd_w1_train_distribution": {
                channel: {
                    "q05": float(np.quantile(w1[ch], 0.05)),
                    "median": float(np.median(w1[ch])),
                    "q95": float(np.quantile(w1[ch], 0.95)),
                }
                for ch, channel in enumerate(MT_CHANNELS)
            },
        }
        medians[cls], scales[cls] = median, scale

    differences: dict[str, Any] = {
        "provenance": "inner_train only; robust effect sizes use pairwise median difference divided by pooled robust scale",
        "pairwise": {},
    }
    for left_i, left in enumerate(MT_CLASSES):
        for right in MT_CLASSES[left_i + 1:]:
            denom = np.sqrt((scales[left] ** 2 + scales[right] ** 2) / 2.0)
            effect = (medians[left] - medians[right]) / (denom + 1e-12)
            top = np.argsort(-np.abs(effect))[:12]
            differences["pairwise"][f"{left}__vs__{right}"] = [
                {
                    "feature": ordered_names[int(i)],
                    "effect_size": float(effect[i]),
                    "left_median": float(medians[left][i]),
                    "right_median": float(medians[right][i]),
                }
                for i in top
            ]
    return result, differences


def recipe_schema(n_templates: int) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(RECIPE_KEYS),
        "properties": {
            "class_name": {"enum": MT_CLASSES},
            "template_rank": {"type": "integer", "minimum": 0, "maximum": max(n_templates - 1, 0)},
            "channel_std_mult": {"channels": MT_CHANNELS, "range": [0.80, 1.20]},
            "channel_mean_shift_std": {"channels": MT_CHANNELS, "range": [-0.10, 0.10]},
            "soft_band_gain": {"channels": MT_CHANNELS, "bands": N_BANDS, "range": [0.70, 1.30]},
            "spectral_mix": {"range": [0.00, 0.50]},
            "noise_gain": {"range": [0.00, 0.06]},
            "shared_component_gain": {"range": [0.00, 0.15]},
            "trend_strength": {"range": [-0.05, 0.05]},
            "phase_randomization_strength": {"range": [0.50, 1.00]},
            "rationale": {"type": "string", "max_length": 300},
        },
        "normalization": "Valid numeric recipe values are clipped only to these frozen recipe-domain bounds before rendering. Generated waveforms are never post-processed after verifier rejection.",
    }


def prompt_messages(target_class: str, exemplar: dict[str, Any], differences: dict[str, Any], schema: dict[str, Any], round_id: int, feedback: dict[str, Any] | None) -> list[dict[str, str]]:
    system = (
        "You are an expert in multichannel CNC machine-condition signal synthesis. "
        "You design compact train-supported recipes for a deterministic renderer. "
        "Return one valid JSON object only. Do not output waveform samples, code, markdown, "
        "file names, file IDs, unsupported physical frequencies, or test information."
    )
    target_stats = {
        key: value for key, value in exemplar["classes"][target_class].items()
        if key not in {"raw_class_id", "display_name"}
    }
    target_differences = {
        key: value for key, value in differences["pairwise"].items() if target_class in key
    }
    content = {
        "target_class": target_class,
        "channel_schema": {"channels": MT_CHANNELS, "sampling_rate_hz": 4000, "window_samples": WIN_MT},
        "inner_train_only_statistics": target_stats,
        "inner_train_only_class_differences": target_differences,
        "recipe_schema": schema,
        "frozen_rules": [
            "Use only train-supported differences supplied here.",
            "Do not directly copy a template.",
            "Do not use a file name, file ID, raw class ID, formal test information, speed, TPF, shaft order, BPFO, BPFI, or any unknown absolute frequency.",
            "Do not emit code or waveform samples.",
        ],
        "feedback_round": round_id,
        "previous_failure_report": feedback,
    }
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(json_ready(content), ensure_ascii=False, separators=(",", ":"))}]


def normalize_recipe(raw: dict[str, Any], target_class: str, n_templates: int) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != RECIPE_KEYS:
        missing, extra = sorted(RECIPE_KEYS - set(raw or {})), sorted(set(raw or {}) - RECIPE_KEYS)
        raise ValueError(f"recipe schema mismatch; missing={missing}, extra={extra}")
    if raw["class_name"] != target_class:
        raise ValueError(f"recipe target mismatch: expected {target_class}, got {raw['class_name']!r}")
    if n_templates < 1:
        raise ValueError("no class templates are available")

    def clip_number(value: Any, lower: float, upper: float) -> float:
        value = float(value)
        if not np.isfinite(value):
            raise ValueError("recipe contains a non-finite number")
        return float(np.clip(value, lower, upper))

    out = {"class_name": target_class}
    rank = int(round(float(raw["template_rank"])))
    out["template_rank"] = int(np.clip(rank, 0, n_templates - 1))
    for name, limits in (("channel_std_mult", (0.80, 1.20)), ("channel_mean_shift_std", (-0.10, 0.10))):
        value = raw[name]
        if not isinstance(value, dict) or set(value) != set(MT_CHANNELS):
            raise ValueError(f"{name} must specify exactly {MT_CHANNELS}")
        out[name] = {channel: clip_number(value[channel], *limits) for channel in MT_CHANNELS}
    bands = raw["soft_band_gain"]
    if not isinstance(bands, dict) or set(bands) != set(MT_CHANNELS):
        raise ValueError("soft_band_gain must specify exactly the four channels")
    out["soft_band_gain"] = {}
    for channel in MT_CHANNELS:
        values = bands[channel]
        if not isinstance(values, list) or len(values) != N_BANDS:
            raise ValueError(f"soft_band_gain[{channel}] must contain {N_BANDS} values")
        out["soft_band_gain"][channel] = [clip_number(value, 0.70, 1.30) for value in values]
    for name, lower, upper in (
        ("spectral_mix", 0.00, 0.50),
        ("noise_gain", 0.00, 0.06),
        ("shared_component_gain", 0.00, 0.15),
        ("trend_strength", -0.05, 0.05),
        ("phase_randomization_strength", 0.50, 1.00),
    ):
        out[name] = clip_number(raw[name], lower, upper)
    if not isinstance(raw["rationale"], str):
        raise ValueError("rationale must be a string")
    out["rationale"] = raw["rationale"].strip()[:300]
    return out


def rule_recipe(target_class: str, template_rank: int) -> dict[str, Any]:
    return {
        "class_name": target_class,
        "template_rank": template_rank,
        "channel_std_mult": {channel: 1.0 for channel in MT_CHANNELS},
        "channel_mean_shift_std": {channel: 0.0 for channel in MT_CHANNELS},
        "soft_band_gain": {channel: [1.0] * N_BANDS for channel in MT_CHANNELS},
        "spectral_mix": 0.20,
        "noise_gain": 0.01,
        "shared_component_gain": 0.02,
        "trend_strength": 0.0,
        "phase_randomization_strength": 1.0,
        "rationale": "Frozen rule-verified baseline recipe.",
    }


def random_recipe(target_class: str, template_rank: int, rng: np.random.Generator) -> dict[str, Any]:
    return {
        "class_name": target_class,
        "template_rank": template_rank,
        "channel_std_mult": {channel: float(rng.uniform(0.80, 1.20)) for channel in MT_CHANNELS},
        "channel_mean_shift_std": {channel: float(rng.uniform(-0.10, 0.10)) for channel in MT_CHANNELS},
        "soft_band_gain": {channel: rng.uniform(0.70, 1.30, N_BANDS).tolist() for channel in MT_CHANNELS},
        "spectral_mix": float(rng.uniform(0.00, 0.50)),
        "noise_gain": float(rng.uniform(0.00, 0.06)),
        "shared_component_gain": float(rng.uniform(0.00, 0.15)),
        "trend_strength": float(rng.uniform(-0.05, 0.05)),
        "phase_randomization_strength": float(rng.uniform(0.50, 1.00)),
        "rationale": "Uniform open-loop sample from the frozen recipe domain.",
    }


def iaaft_surrogate(x: np.ndarray, rng: np.random.Generator, phase_strength: float) -> np.ndarray:
    """IAAFT-style surrogate retaining a template's amplitude distribution and PSD."""
    centered = np.asarray(x, dtype=float) - float(np.mean(x))
    ordered = np.sort(centered)
    target_amplitude = np.abs(np.fft.rfft(centered))
    base_phase = np.angle(np.fft.rfft(centered))
    random_phase = rng.uniform(-np.pi, np.pi, len(target_amplitude))
    phase = base_phase + phase_strength * np.angle(np.exp(1j * (random_phase - base_phase)))
    phase[0] = 0.0
    if len(phase) > 1:
        phase[-1] = 0.0
    y = np.fft.irfft(target_amplitude * np.exp(1j * phase), len(centered))
    for _ in range(10):
        ranks = np.argsort(np.argsort(y, kind="mergesort"), kind="mergesort")
        y = ordered[ranks]
        phase = np.angle(np.fft.rfft(y))
        y = np.fft.irfft(target_amplitude * np.exp(1j * phase), len(centered))
    ranks = np.argsort(np.argsort(y, kind="mergesort"), kind="mergesort")
    return ordered[ranks] + float(np.mean(x))


def apply_soft_band_gain(x: np.ndarray, gains: list[float]) -> np.ndarray:
    spectrum = np.fft.rfft(x)
    freq = np.fft.rfftfreq(len(x), d=1.0)
    centers = (np.arange(N_BANDS, dtype=float) + 0.5) * (0.5 / N_BANDS)
    interpolated = np.interp(freq, np.r_[0.0, centers, 0.5], np.r_[gains[0], gains, gains[-1]])
    return np.fft.irfft(spectrum * interpolated, len(x))


def render_mt_recipe(recipe: dict[str, Any], templates: dict[str, np.ndarray], class_channel_std: dict[str, np.ndarray], seed: int) -> np.ndarray:
    """Render a fresh four-channel candidate without returning a real template."""
    cls = recipe["class_name"]
    source = templates[cls]
    rng = np.random.default_rng(seed)
    rank = int(recipe["template_rank"])
    first = source[rank % len(source)]
    second = source[(rank + 1 + int(rng.integers(0, max(len(source) - 1, 1)))) % len(source)]
    phase_strength = float(recipe["phase_randomization_strength"])
    mixed = np.empty_like(first, dtype=np.float64)
    for ch, name in enumerate(MT_CHANNELS):
        a = iaaft_surrogate(first[ch], rng, phase_strength)
        b = iaaft_surrogate(second[ch], rng, phase_strength)
        x = (1.0 - recipe["spectral_mix"]) * a + recipe["spectral_mix"] * b
        mixed[ch] = apply_soft_band_gain(x, recipe["soft_band_gain"][name])
    # The class-template common component is a data-derived, normalized signal.
    normalized = (mixed - mixed.mean(axis=1, keepdims=True)) / (mixed.std(axis=1, keepdims=True) + 1e-12)
    shared = normalized.mean(axis=0)
    trend = np.linspace(-1.0, 1.0, WIN_MT)
    output = np.empty_like(mixed, dtype=np.float64)
    for ch, name in enumerate(MT_CHANNELS):
        target_std = float(np.std(first[ch])) * recipe["channel_std_mult"][name]
        target_mean = float(np.mean(first[ch])) + recipe["channel_mean_shift_std"][name] * float(class_channel_std[cls][ch])
        x = mixed[ch] - np.mean(mixed[ch])
        x = x / (np.std(x) + 1e-12) * target_std
        x += target_mean
        x += recipe["shared_component_gain"] * target_std * shared
        x += recipe["noise_gain"] * float(class_channel_std[cls][ch]) * rng.normal(size=WIN_MT)
        x += recipe["trend_strength"] * float(class_channel_std[cls][ch]) * trend
        output[ch] = x
    if not np.all(np.isfinite(output)):
        raise ValueError("renderer created non-finite values")
    if any(np.array_equal(output.astype(np.float32), template) for template in source):
        raise RuntimeError("renderer unexpectedly returned an exact real template")
    return output.astype(np.float32)


def candidate_feedback(report: dict[str, Any]) -> dict[str, Any]:
    violations = []
    scores = report["verifier"]["scores"]
    gates = report["verifier"]["gates"]
    if not gates["stats_union"]["passed"]:
        stat = scores.get("stats_union", {})
        violations.append({
            "feature": "robust_structure_distance",
            "value": stat.get("axis_distance"),
            "threshold": stat.get("axis_threshold"),
            "direction": "move the class-conditional statistic vector closer to the inner-train robust centroid",
        })
    if not gates["soft_spectrum"]["passed"]:
        soft = scores.get("soft_spectrum", {})
        violations.append({
            "feature": "soft_spectral_axis_distance",
            "value": soft.get("axis_distance"),
            "threshold": soft.get("axis_threshold"),
            "coordinate_max_violation": scores.get("soft_spectrum_max_violation"),
            "direction": "reduce normalized soft-band deviations from the inner-train class profile",
        })
    if not gates["psd_w1"]["passed"]:
        for channel, value in scores.get("psd_w1", {}).items():
            if value["value"] > value["threshold"]:
                violations.append({
                    "feature": f"{channel}_psd_w1",
                    "value": value["value"],
                    "threshold": value["threshold"],
                    "direction": "move the normalized spectrum closer to the class reference",
                })
    if not report["diversity_passed"]:
        violations.append({
            "feature": "nearest_train_distance",
            "value": report["nearest_train_distance"],
            "minimum": report["diversity_minimum"],
            "direction": "increase variation without leaving class support",
        })
    if not report["class_identity_passed"]:
        violations.append({
            "feature": "class_identity",
            "target": report["class_name"],
            "predicted": report["class_identity_prediction"],
            "probability": report["class_identity_probability"],
            "direction": "express the supplied train-supported class differences more clearly",
        })
    return {
        "failed_gates": report["failure_reasons"],
        "violations": violations,
        "class_identity": {
            "target": report["class_name"],
            "predicted": report["class_identity_prediction"],
        },
        "diversity": {
            "nearest_train_distance": report["nearest_train_distance"],
            "minimum": report["diversity_minimum"],
        },
    }


@dataclass
class Admission:
    verifier: MachineToolVerifier
    identity: ExtraTreesClassifier
    train_features: dict[str, np.ndarray]
    train_windows: dict[str, np.ndarray]
    train_sources: dict[str, np.ndarray]


def build_admission(dev: DevData, verifier: MachineToolVerifier) -> Admission:
    features = feature_matrix(dev.X_train)
    identity = ExtraTreesClassifier(
        n_estimators=400,
        random_state=stable_seed("mt_private_v2", "class_identity"),
        class_weight="balanced",
        max_features="sqrt",
        n_jobs=1,
    )
    identity.fit(features, dev.y_train)
    by_features, by_windows, by_sources = {}, {}, {}
    for ci, cls in enumerate(MT_CLASSES):
        idx = dev.y_train == ci
        by_features[cls] = features[idx]
        by_windows[cls] = dev.X_train[idx]
        by_sources[cls] = dev.train_files[idx]
    return Admission(verifier, identity, by_features, by_windows, by_sources)


def admit_candidate(window: np.ndarray, cls: str, admission: Admission, existing_hashes: set[str]) -> dict[str, Any]:
    verifier_report = admission.verifier.verify(window, cls)
    raw_id = class_name_to_raw_id(cls)
    feature = structure_vector(window)
    cal = admission.verifier.calib["classes"][cls]
    med = np.asarray(cal["diversity"]["embedding_median"], dtype=float)
    scale = np.asarray(cal["diversity"]["embedding_scale"], dtype=float)
    real_features = admission.train_features[cls]
    dists = np.sqrt(np.sum((((real_features - feature) / scale) ** 2), axis=1))
    closest = int(np.argmin(dists))
    nearest_distance = float(dists[closest])
    diversity_minimum = float(cal["diversity"]["real_real_nn_q05"])
    diversity_passed = nearest_distance >= diversity_minimum
    ci = int(MT_CLASSES.index(cls))
    probabilities = admission.identity.predict_proba(feature.reshape(1, -1))[0]
    identity_index = int(np.argmax(probabilities))
    identity_prediction = MT_CLASSES[identity_index]
    identity_probability = float(probabilities[ci])
    identity_passed = identity_prediction == cls
    digest = sha256_bytes(np.ascontiguousarray(window).tobytes())
    exact_train = any(np.array_equal(window, real) for real in admission.train_windows[cls])
    exact_synthetic = digest in existing_hashes
    hard_passed = bool(verifier_report["feasible"])
    accepted = bool(
        hard_passed
        and diversity_passed
        and identity_passed
        and not exact_train
        and not exact_synthetic
        and window.shape == (len(MT_CHANNELS), WIN_MT)
        and np.all(np.isfinite(window))
    )
    failures = [name for name, gate in verifier_report["gates"].items() if not gate["passed"]]
    if not diversity_passed:
        failures.append("diversity")
    if not identity_passed:
        failures.append("class_identity")
    if exact_train:
        failures.append("exact_train_duplicate")
    if exact_synthetic:
        failures.append("exact_synthetic_duplicate")
    return {
        "class_name": cls,
        "raw_class_id": raw_id,
        "display_name": CLASS_ID_TO_DISPLAY_NAME[raw_id],
        "accepted": accepted,
        "verifier": verifier_report,
        "hard_gates_passed": hard_passed,
        "diversity_passed": diversity_passed,
        "diversity_minimum": diversity_minimum,
        "nearest_train_distance": nearest_distance,
        "nearest_train_file": str(admission.train_sources[cls][closest]),
        "class_identity_passed": identity_passed,
        "class_identity_prediction": identity_prediction,
        "class_identity_probability": identity_probability,
        "exact_train_duplicate": exact_train,
        "exact_synthetic_duplicate": exact_synthetic,
        "candidate_sha256": digest,
        "failure_reasons": failures,
    }


def state_path(cls: str, slot: int) -> Path:
    return RUN_DIR / "checkpoints" / f"{cls}_slot_{slot:02d}.json"


def default_slot_state(cls: str, slot: int) -> dict[str, Any]:
    return {"class_name": cls, "slot": slot, "status": "pending", "history": []}


def load_slot_state(cls: str, slot: int) -> dict[str, Any]:
    path = state_path(cls, slot)
    return json.loads(path.read_text()) if path.exists() else default_slot_state(cls, slot)


def save_slot_state(state: dict[str, Any]) -> None:
    write_json(state_path(state["class_name"], int(state["slot"])), state)


def load_all_states(target_per_class: int) -> list[dict[str, Any]]:
    return [load_slot_state(cls, slot) for slot in range(target_per_class) for cls in MT_CLASSES]


def api_log_path() -> Path:
    return OUT_DIR / "mt_private_v2_api_log.csv"


API_LOG_FIELDS = [
    "request_index", "slot", "target_class", "round_id", "attempt", "model", "prompt_hash", "response_hash",
    "http_status", "parse_status", "timestamp", "accepted", "rejection_reasons",
]


def append_api_log(row: dict[str, Any]) -> None:
    path = api_log_path()
    fresh = not path.exists()
    with path.open("a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=API_LOG_FIELDS, lineterminator="\n", extrasaction="ignore")
        if fresh:
            writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in API_LOG_FIELDS})


def api_attempt_count() -> int:
    return len(read_csv_rows(api_log_path()))


def call_recipe_api(messages: list[dict[str, str]], request_index: int, slot: int, cls: str, round_id: int, last_call: list[float]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("MIMO_API_KEY")
    if not key:
        raise RuntimeError("Set DASHSCOPE_API_KEY or MIMO_API_KEY in the process environment; keys are never read from files.")
    elapsed = time.monotonic() - last_call[0]
    if elapsed < LLM_MIN_INTERVAL:
        time.sleep(LLM_MIN_INTERVAL - elapsed)
    prompt_bytes = json.dumps(messages, sort_keys=True, separators=(",", ":")).encode("utf-8")
    prompt_hash = sha256_bytes(prompt_bytes)
    status, text, parsed, parse_status = 0, "", None, "not_attempted"
    try:
        response = requests.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": LLM_MODEL,
                "messages": messages,
                "temperature": 0.65,
                "max_tokens": 1200,
                "enable_thinking": False,
                "chat_template_kwargs": {"enable_thinking": False},
            },
            timeout=300,
        )
        last_call[0] = time.monotonic()
        status = int(response.status_code)
        text = response.text
        if status == 200:
            content = response.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content.strip())
            parse_status = "json_ok"
        else:
            parse_status = "http_error"
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        last_call[0] = time.monotonic()
        parse_status = f"error:{type(exc).__name__}"
    log = {
        "request_index": request_index,
        "slot": slot,
        "target_class": cls,
        "round_id": round_id,
        "attempt": request_index,
        "model": LLM_MODEL,
        "prompt_hash": prompt_hash,
        "response_hash": sha256_bytes(text.encode("utf-8")) if text else "",
        "http_status": status,
        "parse_status": parse_status,
        "timestamp": utc_now(),
        "accepted": False,
        "rejection_reasons": "",
    }
    return parsed, log


def generate_llm_pool(dev: DevData, templates: dict[str, np.ndarray], class_std: dict[str, np.ndarray], exemplar: dict[str, Any], differences: dict[str, Any], schema: dict[str, Any], admission: Admission, target_per_class: int, max_api_requests: int, max_feedback_rounds: int, expansions: int, prepare_only: bool, readmit_existing: bool) -> dict[str, Any]:
    ensure_dirs()
    if prepare_only:
        return {"api_requests": api_attempt_count(), "prepare_only": True}
    if max_api_requests > API_STAGE_BUDGET:
        raise ValueError(f"max_api_requests cannot exceed frozen budget {API_STAGE_BUDGET}")
    if readmit_existing:
        for state in load_all_states(target_per_class):
            if state.get("status") == "accepted" and state.get("accepted_path"):
                path = RUN_DIR / state["accepted_path"]
                if path.exists():
                    state["readmission"] = admit_candidate(np.load(path), state["class_name"], admission, set())
                    save_slot_state(state)
    states = load_all_states(target_per_class)
    accepted_hashes: set[str] = set()
    for state in states:
        if state.get("status") == "accepted" and state.get("accepted_path"):
            path = RUN_DIR / state["accepted_path"]
            if path.exists():
                accepted_hashes.add(sha256_bytes(np.ascontiguousarray(np.load(path)).tobytes()))
    last_call = [0.0]
    while api_attempt_count() < max_api_requests:
        states = load_all_states(target_per_class)
        accepted_counts = Counter(state["class_name"] for state in states if state["status"] == "accepted")
        eligible = [
            state for state in states
            if state["status"] == "pending" and len(state["history"]) <= max_feedback_rounds
        ]
        if not eligible:
            break
        eligible.sort(key=lambda state: (accepted_counts[state["class_name"]], int(state["slot"]), state["class_name"]))
        state = eligible[0]
        cls, slot = state["class_name"], int(state["slot"])
        round_id = len(state["history"])
        previous_feedback = state["history"][-1].get("feedback") if state["history"] else None
        messages = prompt_messages(cls, exemplar, differences, schema, round_id, previous_feedback)
        raw_recipe, api_row = call_recipe_api(messages, api_attempt_count() + 1, slot, cls, round_id, last_call)
        record: dict[str, Any] = {"round_id": round_id, "api_request_index": api_row["request_index"], "attempts": []}
        recipe = None
        if raw_recipe is None:
            record["recipe_error"] = api_row["parse_status"]
            record["feedback"] = {"failed_gates": ["api_or_json"], "violations": [{"feature": "response", "direction": "return exactly one valid JSON object matching the schema"}]}
            api_row["rejection_reasons"] = "api_or_json"
        else:
            try:
                recipe = normalize_recipe(raw_recipe, cls, len(templates[cls]))
                record["recipe"] = recipe
                write_json(RUN_DIR / "recipes" / f"{cls}_slot_{slot:02d}_round_{round_id}.json", recipe)
            except (TypeError, ValueError) as exc:
                record["recipe_error"] = str(exc)
                record["feedback"] = {"failed_gates": ["recipe_schema"], "violations": [{"feature": "recipe_schema", "direction": str(exc)}]}
                api_row["rejection_reasons"] = "recipe_schema"
        first_accepted: dict[str, Any] | None = None
        if recipe is not None:
            for expansion_id in range(expansions):
                seed = stable_seed("mt_private_v2", cls, slot, round_id, expansion_id)
                try:
                    window = render_mt_recipe(recipe, templates, class_std, seed)
                    report = admit_candidate(window, cls, admission, accepted_hashes)
                    report.update({"slot": slot, "round_id": round_id, "expansion_id": expansion_id, "seed": seed})
                    if report["accepted"] and first_accepted is None:
                        first_accepted = report
                        path = RUN_DIR / "accepted" / f"{cls}_slot_{slot:02d}.npy"
                        np.save(path, window)
                        state["accepted_path"] = str(path.relative_to(RUN_DIR))
                        state["accepted_report"] = report
                        accepted_hashes.add(report["candidate_sha256"])
                    elif report["accepted"]:
                        report["accepted"] = False
                        report["retained"] = False
                        report["failure_reasons"] = ["slot_already_retained"]
                    else:
                        np.save(RUN_DIR / "rejected" / f"{cls}_slot_{slot:02d}_round_{round_id}_exp_{expansion_id}.npy", window)
                    record["attempts"].append(report)
                    write_json(RUN_DIR / "attempts" / f"{cls}_slot_{slot:02d}_round_{round_id}_exp_{expansion_id}.json", report)
                except (RuntimeError, ValueError) as exc:
                    record["attempts"].append({"slot": slot, "round_id": round_id, "expansion_id": expansion_id, "accepted": False, "failure_reasons": [f"render:{type(exc).__name__}"]})
            if first_accepted is None:
                last_report = record["attempts"][-1] if record["attempts"] else {"failure_reasons": ["no_expansion"]}
                record["feedback"] = candidate_feedback(last_report) if "verifier" in last_report else {"failed_gates": last_report["failure_reasons"], "violations": []}
                api_row["rejection_reasons"] = "|".join(record["feedback"]["failed_gates"])
        if first_accepted is not None:
            state["status"] = "accepted"
            api_row["accepted"] = True
        elif round_id >= max_feedback_rounds:
            state["status"] = "exhausted"
        state["history"].append(record)
        save_slot_state(state)
        append_api_log(api_row)
    states = load_all_states(target_per_class)
    return {"api_requests": api_attempt_count(), "states": states, "prepare_only": False}


def flatten_attempts(states: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for state in states:
        for history in state.get("history", []):
            for attempt in history.get("attempts", []):
                verifier = attempt.get("verifier", {})
                rows.append({
                    "class_name": state["class_name"], "slot": state["slot"], "round_id": history["round_id"],
                    "expansion_id": attempt.get("expansion_id", ""), "accepted": bool(attempt.get("accepted", False)),
                    "hard_gates_passed": attempt.get("hard_gates_passed", ""), "diversity_passed": attempt.get("diversity_passed", ""),
                    "class_identity_passed": attempt.get("class_identity_passed", ""),
                    "nearest_train_distance": attempt.get("nearest_train_distance", ""), "diversity_minimum": attempt.get("diversity_minimum", ""),
                    "class_identity_prediction": attempt.get("class_identity_prediction", ""), "class_identity_probability": attempt.get("class_identity_probability", ""),
                    "candidate_sha256": attempt.get("candidate_sha256", ""), "failure_reasons": "|".join(attempt.get("failure_reasons", [])),
                    "verifier_feasible": verifier.get("feasible", ""),
                })
    return rows


def write_generation_outputs(target_per_class: int) -> dict[str, Any]:
    states = load_all_states(target_per_class)
    slot_rows = []
    pool_rows, diversity_rows, identity_rows = [], [], []
    for state in states:
        report = state.get("accepted_report", {})
        slot_rows.append({
            "class_name": state["class_name"], "raw_class_id": class_name_to_raw_id(state["class_name"]), "slot": state["slot"],
            "status": state["status"], "rounds_attempted": len(state.get("history", [])), "accepted": state["status"] == "accepted",
            "accepted_round": report.get("round_id", ""), "accepted_expansion": report.get("expansion_id", ""),
        })
        if state["status"] == "accepted":
            pool_rows.append({
                "class_name": state["class_name"], "raw_class_id": class_name_to_raw_id(state["class_name"]), "slot": state["slot"],
                "round_id": report["round_id"], "expansion_id": report["expansion_id"], "path": state.get("accepted_path", ""),
                "sha256": report["candidate_sha256"], "nearest_train_file": report["nearest_train_file"],
            })
            diversity_rows.append({key: report.get(key, "") for key in ("class_name", "slot", "round_id", "expansion_id", "nearest_train_distance", "diversity_minimum", "diversity_passed", "exact_train_duplicate", "exact_synthetic_duplicate")})
            identity_rows.append({key: report.get(key, "") for key in ("class_name", "slot", "round_id", "expansion_id", "class_identity_prediction", "class_identity_probability", "class_identity_passed")})
    attempts = flatten_attempts(states)
    write_csv(OUT_DIR / "mt_private_v2_slot_summary.csv", slot_rows)
    write_csv(OUT_DIR / "mt_private_v2_attempt_summary.csv", attempts)
    write_csv(OUT_DIR / "mt_private_v2_pool_manifest.csv", pool_rows)
    write_csv(OUT_DIR / "mt_private_v2_diversity_audit.csv", diversity_rows)
    write_csv(OUT_DIR / "mt_private_v2_class_identity_audit.csv", identity_rows)
    accepted_counts = Counter(row["class_name"] for row in pool_rows)
    round_rows = []
    cumulative = 0
    for round_id in range(4):
        api_slots = sum(1 for state in states if len(state.get("history", [])) > round_id)
        accepted_here = sum(1 for row in pool_rows if row["round_id"] == round_id)
        cumulative += accepted_here
        round_rows.append({"round_id": round_id, "api_slots": api_slots, "accepted_at_round": accepted_here, "cumulative_accepted": cumulative, "acceptance_rate": accepted_here / api_slots if api_slots else np.nan})
    write_csv(OUT_DIR / "mt_private_v2_acceptance_by_round.csv", round_rows)
    rescues = []
    for state in states:
        initial_failed = bool(state.get("history")) and not any(item.get("accepted", False) for item in state["history"][0].get("attempts", []))
        accepted_after_feedback = state["status"] == "accepted" and int(state.get("accepted_report", {}).get("round_id", 0)) > 0
        rescues.append({"class_name": state["class_name"], "slot": state["slot"], "initial_failed": initial_failed, "accepted_after_feedback": accepted_after_feedback, "rescue": bool(initial_failed and accepted_after_feedback)})
    write_csv(OUT_DIR / "mt_private_v2_feedback_rescue.csv", rescues)
    failure_counts = Counter(reason for row in attempts for reason in row["failure_reasons"].split("|") if reason)
    write_csv(OUT_DIR / "mt_private_v2_gate_failures.csv", [{"failure_reason": key, "count": value} for key, value in sorted(failure_counts.items())])
    pool_summary = [{"class_name": cls, "target_slots": target_per_class, "accepted": accepted_counts[cls], "slot_acceptance_rate": accepted_counts[cls] / target_per_class} for cls in MT_CLASSES]
    write_csv(OUT_DIR / "mt_private_v2_pool_summary.csv", pool_summary)
    return {"states": states, "pool_rows": pool_rows, "attempts": attempts, "accepted_counts": dict(accepted_counts), "round_rows": round_rows, "rescues": rescues}


def load_selected_llm_pool(pool_rows: list[dict[str, Any]], balanced_n_syn: int) -> tuple[dict[str, np.ndarray], dict[str, list[dict[str, Any]]]]:
    pools, manifests = {}, {}
    for cls in MT_CLASSES:
        rows = sorted((row for row in pool_rows if row["class_name"] == cls), key=lambda row: int(row["slot"]))[:balanced_n_syn]
        pools[cls] = np.stack([np.load(RUN_DIR / row["path"]) for row in rows]) if rows else np.empty((0, len(MT_CHANNELS), WIN_MT), dtype=np.float32)
        manifests[cls] = rows
    return pools, manifests


def build_baseline_pools(templates: dict[str, np.ndarray], class_std: dict[str, np.ndarray], admission: Admission, balanced_n_syn: int) -> tuple[dict[str, dict[str, np.ndarray]], list[dict[str, Any]]]:
    pools: dict[str, dict[str, np.ndarray]] = {"rule_verified": {}, "random_open_loop": {}}
    rows: list[dict[str, Any]] = []
    for method in pools:
        for cls in MT_CLASSES:
            accepted, hashes, attempts = [], set(), 0
            while len(accepted) < balanced_n_syn and attempts < 200:
                seed = stable_seed("mt_private_v2", method, cls, attempts)
                rank = attempts % len(templates[cls])
                recipe = rule_recipe(cls, rank) if method == "rule_verified" else random_recipe(cls, rank, np.random.default_rng(seed))
                window = render_mt_recipe(recipe, templates, class_std, seed)
                if method == "rule_verified":
                    report = admit_candidate(window, cls, admission, hashes)
                    if report["accepted"]:
                        hashes.add(report["candidate_sha256"])
                        accepted.append(window)
                elif np.all(np.isfinite(window)) and window.shape == (len(MT_CHANNELS), WIN_MT):
                    digest = sha256_bytes(np.ascontiguousarray(window).tobytes())
                    if digest not in hashes:
                        hashes.add(digest)
                        accepted.append(window)
                attempts += 1
            pools[method][cls] = np.asarray(accepted, dtype=np.float32)
            rows.append({"method": method, "class_name": cls, "target": balanced_n_syn, "accepted": len(accepted), "offline_attempts": attempts, "verifier_used": method == "rule_verified"})
        np.savez_compressed(RUN_DIR / "pools" / f"{method}.npz", **pools[method])
    for cls in MT_CLASSES:
        rows.append({"method": "noise_aug", "class_name": cls, "target": balanced_n_syn, "accepted": balanced_n_syn, "offline_attempts": 0, "verifier_used": False})
        rows.append({"method": "llm_closed_loop", "class_name": cls, "target": balanced_n_syn, "accepted": balanced_n_syn, "offline_attempts": "api", "verifier_used": True})
    write_csv(OUT_DIR / "mt_private_v2_baseline_pool_summary.csv", rows)
    return pools, rows


def sample_real_subset(X: np.ndarray, y: np.ndarray, n_real: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(stable_seed("mt_private_v2", "real_subset", n_real, seed))
    keep = []
    for ci in range(len(MT_CLASSES)):
        indices = np.flatnonzero(y == ci)
        if len(indices) < n_real:
            raise RuntimeError(f"class {MT_CLASSES[ci]} has only {len(indices)} inner-train windows, needs {n_real}")
        keep.extend(rng.choice(indices, n_real, replace=False).tolist())
    keep = np.asarray(keep, dtype=int)
    return X[keep], y[keep]


def noise_augment(X: np.ndarray, y: np.ndarray, balanced_n_syn: int, seed: int, class_std: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(stable_seed("mt_private_v2", "noise_aug", seed))
    xs, ys = [], []
    for ci, cls in enumerate(MT_CLASSES):
        base = X[y == ci][:balanced_n_syn]
        if len(base) < balanced_n_syn:
            raise RuntimeError("noise augmentation needs at least balanced_n_syn real windows per class")
        noise = rng.normal(size=base.shape).astype(np.float32) * (0.05 * class_std[cls])[None, :, None]
        xs.append(base + noise)
        ys.append(np.full(balanced_n_syn, ci, dtype=np.int64))
    return np.concatenate(xs).astype(np.float32), np.concatenate(ys)


def normalize_train_val(X_train: np.ndarray, X_val: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = X_train.mean(axis=(0, 2), keepdims=True)
    std = X_train.std(axis=(0, 2), keepdims=True) + 1e-8
    return (X_train - mean) / std, (X_val - mean) / std


def train_cnn(X_train: np.ndarray, y_train: np.ndarray, seed: int, epochs: int = 60) -> SimpleCNN:
    torch.manual_seed(seed)
    model = SimpleCNN(in_ch=len(MT_CHANNELS), num_classes=len(MT_CLASSES))
    opt = torch.optim.Adam(model.parameters(), lr=3e-4, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss()
    X_tensor = torch.tensor(X_train, dtype=torch.float32)
    y_tensor = torch.tensor(y_train, dtype=torch.long)
    generator = torch.Generator().manual_seed(seed)
    model.train()
    for _ in range(epochs):
        order = torch.randperm(len(X_tensor), generator=generator)
        for start in range(0, len(order), 32):
            batch = order[start:start + 32]
            opt.zero_grad()
            loss = criterion(model(X_tensor[batch]), y_tensor[batch])
            loss.backward()
            opt.step()
    return model


def predict_cnn(model: SimpleCNN, X_val: np.ndarray) -> np.ndarray:
    model.eval()
    chunks = []
    with torch.no_grad():
        tensor = torch.tensor(X_val, dtype=torch.float32)
        for start in range(0, len(tensor), 256):
            chunks.append(model(tensor[start:start + 256]).argmax(1).cpu().numpy())
    return np.concatenate(chunks)


DOWNSTREAM_FIELDS = ["method", "n_real", "n_syn", "seed", "train_sample_count", "acc", "macro_f1", *[f"f1_{cls}" for cls in MT_CLASSES], "confusion"]


def existing_downstream_keys() -> set[tuple[str, int, int]]:
    return {(row["method"], int(row["n_real"]), int(row["seed"])) for row in read_csv_rows(OUT_DIR / "mt_private_v2_downstream.csv")}


def run_downstream(dev: DevData, balanced_n_syn: int, llm_pools: dict[str, np.ndarray], baseline_pools: dict[str, dict[str, np.ndarray]], class_std: dict[str, np.ndarray], n_reals: list[int], seeds: int) -> list[dict[str, Any]]:
    X_val, y_val, _, _, _, val_files_read = load_inner_validation()
    if any(parse_mt_filename(name).get("file_id") in FORBIDDEN_FILE_IDS for name in val_files_read):
        raise RuntimeError("formal test data were loaded")
    static = {
        "llm_closed_loop": (np.concatenate([llm_pools[cls] for cls in MT_CLASSES]), np.concatenate([np.full(balanced_n_syn, ci, dtype=np.int64) for ci in range(len(MT_CLASSES))])),
        "rule_verified": (np.concatenate([baseline_pools["rule_verified"][cls] for cls in MT_CLASSES]), np.concatenate([np.full(balanced_n_syn, ci, dtype=np.int64) for ci in range(len(MT_CLASSES))])),
        "random_open_loop": (np.concatenate([baseline_pools["random_open_loop"][cls] for cls in MT_CLASSES]), np.concatenate([np.full(balanced_n_syn, ci, dtype=np.int64) for ci in range(len(MT_CLASSES))])),
    }
    if any(len(X) != balanced_n_syn * len(MT_CLASSES) for X, _ in static.values()):
        raise RuntimeError("a static synthetic baseline pool is not class-balanced at B")
    path = OUT_DIR / "mt_private_v2_downstream.csv"
    done = existing_downstream_keys()
    new_rows = []
    for n_real in n_reals:
        for seed in range(seeds):
            X_real, y_real = sample_real_subset(dev.X_train, dev.y_train, n_real, seed)
            X_noise, y_noise = noise_augment(X_real, y_real, balanced_n_syn, seed, class_std)
            methods: dict[str, tuple[np.ndarray, np.ndarray]] = {
                "real_only": (X_real, y_real),
                "noise_aug": (np.concatenate([X_real, X_noise]), np.concatenate([y_real, y_noise])),
            }
            methods.update({name: (np.concatenate([X_real, X_syn]), np.concatenate([y_real, y_syn])) for name, (X_syn, y_syn) in static.items()})
            for method, (X_train, y_train) in methods.items():
                if (method, n_real, seed) in done:
                    continue
                X_train_norm, X_val_norm = normalize_train_val(X_train, X_val)
                model = train_cnn(X_train_norm.astype(np.float32), y_train, stable_seed("mt_private_v2", "cnn", method, n_real, seed))
                pred = predict_cnn(model, X_val_norm.astype(np.float32))
                per_class = f1_score(y_val, pred, labels=list(range(len(MT_CLASSES))), average=None, zero_division=0)
                row = {
                    "method": method, "n_real": n_real, "n_syn": balanced_n_syn, "seed": seed, "train_sample_count": len(y_train),
                    "acc": float(accuracy_score(y_val, pred)), "macro_f1": float(f1_score(y_val, pred, labels=list(range(len(MT_CLASSES))), average="macro", zero_division=0)),
                    **{f"f1_{cls}": float(per_class[ci]) for ci, cls in enumerate(MT_CLASSES)},
                    "confusion": json.dumps(
                        confusion_matrix(y_val, pred, labels=list(range(len(MT_CLASSES)))).tolist(),
                        separators=(",", ":"),
                    ),
                }
                new_rows.append(row)
                if len(new_rows) >= 10:
                    write_or_append_downstream(path, new_rows)
                    new_rows = []
    if new_rows:
        write_or_append_downstream(path, new_rows)
    rows = [{key: parse_number(value) for key, value in row.items()} for row in read_csv_rows(path)]
    return rows


def parse_number(value: str) -> Any:
    if value == "":
        return value
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def write_or_append_downstream(path: Path, rows: list[dict[str, Any]]) -> None:
    fresh = not path.exists()
    with path.open("a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=DOWNSTREAM_FIELDS, lineterminator="\n", extrasaction="ignore")
        if fresh:
            writer.writeheader()
        writer.writerows(rows)


def holm_adjust(values: list[float]) -> list[float]:
    order = np.argsort(values)
    adjusted = np.zeros(len(values), dtype=float)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, (len(values) - rank) * values[index])
        adjusted[index] = min(running, 1.0)
    return adjusted.tolist()


def summarize_downstream(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    frame = pd.DataFrame(rows)
    numeric = ["acc", "macro_f1", *[f"f1_{cls}" for cls in MT_CLASSES]]
    summary_rows = []
    per_rows = []
    for (method, n_real), group in frame.groupby(["method", "n_real"], sort=True):
        summary_rows.append({"method": method, "n_real": int(n_real), "n_syn": int(group["n_syn"].iloc[0]), "seeds": len(group), **{f"mean_{metric}": float(group[metric].mean()) for metric in numeric}, **{f"std_{metric}": float(group[metric].std(ddof=1)) for metric in numeric}})
        for cls in MT_CLASSES:
            per_rows.append({"method": method, "n_real": int(n_real), "n_syn": int(group["n_syn"].iloc[0]), "class_name": cls, "mean_f1": float(group[f"f1_{cls}"].mean()), "std_f1": float(group[f"f1_{cls}"].std(ddof=1))})
    confusion_rows = []
    for row in rows:
        matrix = json.loads(row["confusion"])
        for ci, true_cls in enumerate(MT_CLASSES):
            for pi, pred_cls in enumerate(MT_CLASSES):
                confusion_rows.append({"method": row["method"], "n_real": row["n_real"], "seed": row["seed"], "true_class": true_cls, "pred_class": pred_cls, "count": int(matrix[ci][pi])})
    wilcoxon_rows = []
    baselines = ["real_only", "noise_aug", "random_open_loop", "rule_verified"]
    for n_real in sorted(frame["n_real"].unique()):
        for metric in numeric:
            llm = frame[(frame.method == "llm_closed_loop") & (frame.n_real == n_real)][["seed", metric]].sort_values("seed")
            family = []
            for baseline in baselines:
                base = frame[(frame.method == baseline) & (frame.n_real == n_real)][["seed", metric]].sort_values("seed")
                paired = llm.merge(base, on="seed", suffixes=("_llm", "_base"))
                delta = paired[f"{metric}_llm"].to_numpy() - paired[f"{metric}_base"].to_numpy()
                if len(delta) == 0 or np.allclose(delta, 0):
                    p = 1.0
                else:
                    try:
                        p = float(wilcoxon(delta, alternative="greater", zero_method="zsplit").pvalue)
                    except ValueError:
                        p = 1.0
                family.append({"n_real": int(n_real), "metric": metric, "comparison": f"llm_closed_loop>{baseline}", "p_raw": p, "mean_delta": float(np.mean(delta)), "median_delta": float(np.median(delta)), "wins": int(np.sum(delta > 0)), "losses": int(np.sum(delta < 0)), "ties": int(np.sum(delta == 0))})
            q_values = holm_adjust([row["p_raw"] for row in family])
            for row, q_value in zip(family, q_values, strict=True):
                row["holm_q"] = q_value
            wilcoxon_rows.extend(family)
    return summary_rows, per_rows, confusion_rows, wilcoxon_rows


def prepare_outputs(dev: DevData, verifier: MachineToolVerifier, exemplar: dict[str, Any], differences: dict[str, Any], schema: dict[str, Any]) -> dict[str, np.ndarray]:
    ensure_dirs()
    split_rows = dev.file_rows + [{
        "split": "inner_val", "raw_class_id": raw_id, "class_name": cls, "display_name": CLASS_ID_TO_DISPLAY_NAME[raw_id],
        "file_id": INNER_VAL_FILE_ID, "source_file": "not_loaded_in_prepare", "n_rows": "not_loaded", "window_count": "not_loaded",
    } for raw_id, cls in zip(RAW_CLASS_IDS, MT_CLASSES, strict=True)]
    write_csv(OUT_DIR / "mt_private_v2_split_index.csv", split_rows)
    (OUT_DIR / "mt_private_v2_split_report.md").write_text("\n".join([
        "# Private Machine-Tool v2 Frozen Development Split", "",
        "- Inner-train file IDs: `1, 2, 4, 5` for each formal class.",
        "- Inner-validation file ID: `10` for each formal class.",
        "- Formal test file IDs `7, 8` are rejected by the data loader and are not read.",
        "- The split rule was frozen before any v2 LLM request or inner-validation result.",
    ]) + "\n")
    write_json(OUT_DIR / "mt_private_v2_inner_train_exemplar_stats.json", exemplar)
    (OUT_DIR / "mt_private_v2_class_difference_report.md").write_text("# Private Machine-Tool v2 Inner-Train Class Differences\n\n```json\n" + json.dumps(differences, indent=2) + "\n```\n")
    write_json(OUT_DIR / "mt_private_v2_recipe_schema.json", schema)
    previews = []
    for cls in MT_CLASSES:
        messages = prompt_messages(cls, exemplar, differences, schema, 0, None)
        previews.extend([f"## {cls}", "", "```json", messages[1]["content"], "```", ""])
    (OUT_DIR / "mt_private_v2_prompt_preview.md").write_text("# Prompt Preview\n\nSystem prompt returns JSON only; previews contain inner-train statistics only.\n\n" + "\n".join(previews))
    (OUT_DIR / "mt_private_v2_api_budget_plan.md").write_text("\n".join([
        "# Private Machine-Tool v2 API Budget", "",
        f"- Start cumulative count: `{API_START_CUMULATIVE}/3000`.",
        f"- Frozen stage ceiling: `{API_STAGE_BUDGET}` request attempts.",
        f"- Maximum end cumulative count: `{API_START_CUMULATIVE + API_STAGE_BUDGET}/3000`.",
        f"- Minimum serial interval: `{LLM_MIN_INTERVAL:.1f}` seconds.",
        "- HTTP failures and parse failures count against the ceiling.",
    ]) + "\n")
    calibration_path = RUN_DIR / "mt_private_v2_inner_train_verifier_c90.json"
    verifier.save(calibration_path)
    templates = {cls: dev.X_train[dev.y_train == ci] for ci, cls in enumerate(MT_CLASSES)}
    class_std = {cls: templates[cls].std(axis=(0, 2)) for cls in MT_CLASSES}
    smoke = render_mt_recipe(rule_recipe(MT_CLASSES[0], 0), templates, class_std, stable_seed("mt_private_v2", "prepare_renderer"))
    if smoke.shape != (len(MT_CHANNELS), WIN_MT) or not np.all(np.isfinite(smoke)):
        raise RuntimeError("no-API renderer smoke failed")
    (OUT_DIR / "mt_private_v2_prepare_report.md").write_text("\n".join([
        "# Private Machine-Tool v2 Prepare Report", "",
        "- Status: passed prepare-only checks.",
        "- API requests: `0`.",
        f"- Loaded inner-train files: `{', '.join(dev.files_read)}`.",
        "- Formal test files loaded: `0`.",
        "- Inner-val waveform files were not loaded in prepare.",
        "- Verifier calibration uses only inner-train files 1/2/4/5.",
        "- Prompt preview contains no raw file path, file ID, raw class prefix, inner-val statistics, or formal test information.",
        f"- No-API renderer smoke shape: `{tuple(smoke.shape)}`; finite: `{bool(np.all(np.isfinite(smoke)))}`.",
    ]) + "\n")
    return templates, class_std


def write_failure_and_decision(target_per_class: int, balanced_n_syn: int, generation: dict[str, Any], downstream_rows: list[dict[str, Any]] | None) -> dict[str, Any]:
    states = generation["states"]
    counts = {cls: int(generation["accepted_counts"].get(cls, 0)) for cls in MT_CLASSES}
    attempt_rows = generation["attempts"]
    all_valid = all(
        state["status"] in {"accepted", "exhausted", "pending"} for state in states
    ) and len(states) == target_per_class * len(MT_CLASSES)
    pool_full = all(counts[cls] >= target_per_class for cls in MT_CLASSES)
    pool_conditional = all(counts[cls] >= 5 for cls in MT_CLASSES)
    diversity_audit = read_csv_rows(OUT_DIR / "mt_private_v2_diversity_audit.csv")
    identity_audit = read_csv_rows(OUT_DIR / "mt_private_v2_class_identity_audit.csv")
    pool_quality = bool(diversity_audit) and len(diversity_audit) == sum(counts.values()) and all(
        not parse_bool(row["exact_train_duplicate"])
        and not parse_bool(row["exact_synthetic_duplicate"])
        and parse_bool(row["diversity_passed"])
        for row in diversity_audit
    ) and bool(identity_audit) and all(parse_bool(row["class_identity_passed"]) for row in identity_audit)
    initial_failed = [row for row in generation["rescues"] if row["initial_failed"]]
    rescue_count = sum(bool(row["rescue"]) for row in generation["rescues"])
    rescue_rate = rescue_count / len(initial_failed) if initial_failed else 0.0
    round_rows = generation["round_rows"]
    round0 = next(row for row in round_rows if row["round_id"] == 0)
    round1 = next(row for row in round_rows if row["round_id"] == 1)
    feedback_gate = bool(round1["cumulative_accepted"] > round0["cumulative_accepted"] or rescue_rate >= 0.20)
    core_real_noise = core_rule = core_random = 0
    lead_gate = all_class_gate = False
    downstream_gate = False
    summaries: list[dict[str, Any]] = []
    if downstream_rows:
        summaries, per_rows, confusion_rows, wilcoxon_rows = summarize_downstream(downstream_rows)
        write_csv(OUT_DIR / "mt_private_v2_downstream_summary.csv", summaries)
        write_csv(OUT_DIR / "mt_private_v2_downstream_per_class.csv", per_rows)
        write_csv(OUT_DIR / "mt_private_v2_downstream_confusions.csv", confusion_rows)
        write_csv(OUT_DIR / "mt_private_v2_wilcoxon_holm.csv", wilcoxon_rows)
        summary_frame = pd.DataFrame(summaries).set_index(["method", "n_real"])
        cells = []
        for n_real in (10, 25, 50):
            for metric in ("acc", "macro_f1"):
                llm = float(summary_frame.loc[("llm_closed_loop", n_real), f"mean_{metric}"])
                real = float(summary_frame.loc[("real_only", n_real), f"mean_{metric}"])
                noise = float(summary_frame.loc[("noise_aug", n_real), f"mean_{metric}"])
                rule = float(summary_frame.loc[("rule_verified", n_real), f"mean_{metric}"])
                random = float(summary_frame.loc[("random_open_loop", n_real), f"mean_{metric}"])
                cells.append({"n_real": n_real, "metric": metric, "llm": llm, "real_only": real, "noise_aug": noise, "rule_verified": rule, "random_open_loop": random})
        core_real_noise = sum(row["llm"] > row["real_only"] and row["llm"] > row["noise_aug"] for row in cells)
        core_rule = sum(row["llm"] >= row["rule_verified"] for row in cells)
        core_random = sum(row["llm"] > row["random_open_loop"] for row in cells)
        lead_deltas = []
        class_f1_means = []
        for cls in MT_CLASSES:
            values = [float(summary_frame.loc[("llm_closed_loop", n_real), f"mean_f1_{cls}"]) for n_real in (10, 25, 50)]
            class_f1_means.append(np.mean(values))
            if cls == "lead_screw_anomaly":
                real_values = [float(summary_frame.loc[("real_only", n_real), f"mean_f1_{cls}"]) for n_real in (10, 25, 50)]
                lead_deltas = [value - base for value, base in zip(values, real_values, strict=True)]
        lead_gate = bool(sum(delta >= 0 for delta in lead_deltas) >= 2 and np.mean(lead_deltas) >= -0.02 and min(float(summary_frame.loc[("llm_closed_loop", n), "mean_f1_lead_screw_anomaly"]) for n in (10, 25, 50)) > 0.05)
        all_class_gate = bool(all(value >= 0.40 for value in class_f1_means))
        downstream_gate = bool(core_real_noise >= 5 and core_rule >= 4 and min(row["llm"] - row["rule_verified"] for row in cells) >= -0.02 and core_random >= 5 and lead_gate and all_class_gate)
    else:
        write_csv(OUT_DIR / "mt_private_v2_downstream_summary.csv", [])
        write_csv(OUT_DIR / "mt_private_v2_downstream_per_class.csv", [])
        write_csv(OUT_DIR / "mt_private_v2_downstream_confusions.csv", [])
        write_csv(OUT_DIR / "mt_private_v2_wilcoxon_holm.csv", [])
    api_requests = api_attempt_count()
    gate_a = bool(all_valid and api_requests <= API_STAGE_BUDGET)
    reasons = []
    if not gate_a:
        reasons.append("run integrity or API budget gate failed")
    if not pool_conditional:
        reasons.append("at least one class has fewer than five accepted LLM slots")
    if pool_conditional and not pool_quality:
        reasons.append("an accepted candidate failed a required admission quality check")
    if not feedback_gate:
        reasons.append("structured feedback did not demonstrate a rescue")
    if pool_conditional and not downstream_gate:
        reasons.append("downstream core gate failed")
    if gate_a and pool_full and pool_quality and feedback_gate and downstream_gate:
        status, next_stage = "PASS", "write_formal_preregistration"
    elif gate_a and pool_conditional and pool_quality and feedback_gate and downstream_gate:
        status, next_stage = "CONDITIONAL_PASS", "one_controlled_pool_extension"
    else:
        status, next_stage = "BLOCKED", "failure_analysis_only"
    decision = {
        "status": status,
        "allowed_next_stage": next_stage,
        "api_start_cumulative": API_START_CUMULATIVE,
        "api_requests_this_stage": api_requests,
        "api_end_cumulative": API_START_CUMULATIVE + api_requests,
        "api_budget": API_STAGE_BUDGET,
        "formal_test_files_read": 0,
        "target_per_class": target_per_class,
        "accepted_counts": counts,
        "slot_acceptance_by_class": {cls: counts[cls] / target_per_class for cls in MT_CLASSES},
        "feedback_rescue_rate": rescue_rate,
        "balanced_n_syn": balanced_n_syn,
        "pool_gate_passed": bool(pool_full and pool_quality),
        "feedback_gate_passed": feedback_gate,
        "downstream_gate_passed": downstream_gate,
        "core_cells_passed_vs_real_noise": core_real_noise,
        "core_cells_passed_vs_rule": core_rule,
        "core_cells_passed_vs_random": core_random,
        "lead_screw_gate_passed": lead_gate,
        "reasons": reasons,
    }
    write_json(OUT_DIR / "mt_private_v2_smoke_decision.json", decision)
    failure_lines = ["# Private Machine-Tool v2 Smoke Failure Analysis", "", f"- Current status: `{status}`", f"- Balanced n_syn: `{balanced_n_syn}`", "", "## Reasons", ""]
    failure_lines.extend([f"- {reason}" for reason in reasons] or ["- No failure reason."])
    failure_lines.extend(["", "## Gate Failure Counts", ""])
    failures = Counter(reason for row in attempt_rows for reason in str(row["failure_reasons"]).split("|") if reason)
    failure_lines.extend([f"- {reason}: `{count}`" for reason, count in sorted(failures.items())] or ["- No renderer/verifier rejection records."])
    (OUT_DIR / "mt_private_v2_failure_analysis.md").write_text("\n".join(failure_lines) + "\n")
    report = ["# Private Machine-Tool v2 LLM Closed-Loop Smoke", "", "Status: inner-validation smoke only; no formal test file was read.", "", "## Gate Summary", "", f"- Decision: `{status}`", f"- Next allowed stage: `{next_stage}`", f"- API requests: `{api_requests}/{API_STAGE_BUDGET}`; cumulative `{API_START_CUMULATIVE + api_requests}/3000`.", f"- Formal test files read: `0`.", f"- Accepted counts: `{counts}`; balanced n_syn `{balanced_n_syn}`.", f"- Feedback rescue rate: `{rescue_rate:.3f}`; feedback gate `{feedback_gate}`.", f"- Downstream gate: `{downstream_gate}`; real/noise cells `{core_real_noise}/6`, rule `{core_rule}/6`, random `{core_random}/6`.", "", "## Frozen Boundaries", "", "- Development uses file IDs 1/2/4/5 for inner train and file 10 only for inner validation.", "- No TPF, rotational-order, bearing-frequency, spindle speed, or invented machine geometry was used.", "- Waveforms rejected by the verifier were not repaired; later rounds used new recipes and fresh renders."]
    (OUT_DIR / "mt_private_v2_smoke_report.md").write_text("\n".join(report) + "\n")
    return decision


def run_prepare() -> tuple[DevData, dict[str, np.ndarray], dict[str, np.ndarray], dict[str, Any], dict[str, Any], dict[str, Any], Admission]:
    dev = load_development_train()
    verifier = MachineToolVerifier(coverage=0.90)
    verifier.calibrate(dev.X_train, dev.y_train, dev.train_files)
    exemplar, differences = class_exemplar_statistics(dev, verifier)
    schema = recipe_schema(max(sum(dev.y_train == ci) for ci in range(len(MT_CLASSES))))
    templates, class_std = prepare_outputs(dev, verifier, exemplar, differences, schema)
    return dev, templates, class_std, exemplar, differences, schema, build_admission(dev, verifier)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["prepare", "generate", "baselines", "downstream", "summarize", "all"], default="all")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--max-api-requests", type=int, default=API_STAGE_BUDGET)
    parser.add_argument("--target-per-class", type=int, default=10)
    parser.add_argument("--max-feedback-rounds", type=int, default=3)
    parser.add_argument("--expansions-per-recipe", type=int, default=3)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--readmit-existing", action="store_true")
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--n-real", type=int, nargs="+", default=[10, 25, 50])
    parser.add_argument("--n-syn", type=int, default=None)
    args = parser.parse_args()
    if args.target_per_class != 10:
        raise ValueError("target_per_class is frozen at 10 for this smoke")
    if args.max_feedback_rounds != 3 or args.expansions_per_recipe != 3:
        raise ValueError("feedback rounds and expansions are frozen at 3")
    if args.max_api_requests < 0 or args.max_api_requests > API_STAGE_BUDGET:
        raise ValueError(f"max_api_requests must be in [0,{API_STAGE_BUDGET}]")
    ensure_dirs()
    dev, templates, class_std, exemplar, differences, schema, admission = run_prepare()
    if args.stage == "prepare" or args.prepare_only:
        print(json.dumps({"stage": "prepare", "api_requests": 0, "formal_test_files_read": 0, "status": "passed"}, sort_keys=True))
        return
    if args.stage in {"generate", "all"}:
        generate_llm_pool(dev, templates, class_std, exemplar, differences, schema, admission, args.target_per_class, args.max_api_requests, args.max_feedback_rounds, args.expansions_per_recipe, False, args.readmit_existing)
    generation = write_generation_outputs(args.target_per_class)
    counts = generation["accepted_counts"]
    balanced_n_syn = min([counts.get(cls, 0) for cls in MT_CLASSES] + [args.target_per_class])
    if args.n_syn is not None and args.n_syn != balanced_n_syn:
        raise ValueError("n_syn is derived from the accepted balanced LLM pool and cannot be manually selected")
    baseline_pools: dict[str, dict[str, np.ndarray]] = {}
    llm_pools: dict[str, np.ndarray] = {}
    if args.stage in {"baselines", "downstream", "all", "summarize"} and balanced_n_syn:
        llm_pools, _ = load_selected_llm_pool(generation["pool_rows"], balanced_n_syn)
        baseline_pools, _ = build_baseline_pools(templates, class_std, admission, balanced_n_syn)
    else:
        write_csv(OUT_DIR / "mt_private_v2_baseline_pool_summary.csv", [])
    downstream_rows: list[dict[str, Any]] | None = None
    can_run_downstream = balanced_n_syn >= 5 and baseline_pools and all(len(baseline_pools[m][cls]) >= balanced_n_syn for m in baseline_pools for cls in MT_CLASSES)
    if args.stage in {"downstream", "all"} and can_run_downstream:
        downstream_rows = run_downstream(dev, balanced_n_syn, llm_pools, baseline_pools, class_std, args.n_real, args.seeds)
    elif (OUT_DIR / "mt_private_v2_downstream.csv").exists():
        downstream_rows = [{key: parse_number(value) for key, value in row.items()} for row in read_csv_rows(OUT_DIR / "mt_private_v2_downstream.csv")]
    if args.stage in {"summarize", "all", "downstream"}:
        decision = write_failure_and_decision(args.target_per_class, balanced_n_syn, generation, downstream_rows)
        print(json.dumps(decision, sort_keys=True))


if __name__ == "__main__":
    main()
