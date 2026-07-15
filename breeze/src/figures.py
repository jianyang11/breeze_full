"""Evidence-constrained publication figures for the BREEZE manuscript.

Every empirical panel reads only sources named in ``analysis/evidence_ledger.md``.
The script performs no experiment, API call, pool repair, or result imputation.

Usage:
    python figures.py
    python figures.py --only waveforms downstream
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from scipy.signal import butter, hilbert, sosfiltfilt
from scipy.stats import kurtosis

sys.path.insert(0, str(Path(__file__).parent))
from config import CLASSES, CONDITIONS, FS, MAIN_COND, fault_freqs
from data import load_file_split
from figure_style import METHOD_COLORS, PALETTE, apply_style, panel_label, save_figure


REPO = Path(__file__).resolve().parents[2]
FIGS = REPO / "breeze" / "paper" / "figs"
PHASE = REPO / "breeze" / "results" / "phaseA_v2_frozen_2026-07-06" / "breeze"
CWRU = REPO / "breeze" / "results" / "cwru_patch_v2_2026-07-07_frozen"
BERKELEY = REPO / "breeze" / "results" / "milling_berkeley_v2_binary_formal_2026-07-08"
PHYSICS = REPO / "breeze" / "results" / "ablation_2026-07-14"
PU_LOCO_V1 = REPO / "breeze" / "results" / "pu_loco_2026-07-07_v1_frozen"
PU_LOCO_V2 = REPO / "breeze" / "results" / "pu_loco_v2_2026-07-08"
PU_LOCO_V3 = REPO / "breeze" / "results" / "pu_loco_v3_2026-07-08"
PU_LOCO_V4 = REPO / "breeze" / "results" / "pu_loco_v4_s2_morphology_2026-07-13"
PU_LOCO_V5 = REPO / "breeze" / "results" / "pu_loco_v5_s4_extrapolation_verifier_2026-07-13"
PU_LOCO_V6 = REPO / "breeze" / "results" / "pu_loco_v6_cscoh_2026-07-14"

CLASS_NAMES = {"healthy": "Healthy", "OR": "Outer race", "IR": "Inner race"}
SOURCE_NAMES = {"real": "Real train", "llm": "LLM", "rule": "Rule", "random_open_loop": "Random"}
POOL_FILES = {
    "llm": PHASE / "runs" / "phaseA_v2_balanced" / "phaseA_v2_llm_k3_B150.npz",
    "rule": PHASE / "runs" / "phaseA_v2_balanced" / "phaseA_v2_rule_B150.npz",
    "random_open_loop": PHASE / "runs" / "phaseA_v2_balanced" / "phaseA_v2_random_open_loop_B150.npz",
}


def _rows(path: Path, required: tuple[str, ...] = (), count: int | None = None) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"required frozen figure source is missing: {path}")
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if count is not None and len(rows) != count:
        raise ValueError(f"{path}: expected {count} rows, found {len(rows)}")
    fields = set(rows[0]) if rows else set()
    missing = set(required) - fields
    if missing:
        raise ValueError(f"{path}: missing columns {sorted(missing)}")
    return rows


def _pool(path: Path) -> tuple[np.ndarray, np.ndarray]:
    if not path.exists():
        raise FileNotFoundError(f"required frozen pool is missing: {path}")
    with np.load(path) as data:
        if set(data.files) < {"X", "y", "class_names"}:
            raise ValueError(f"{path}: incomplete pool archive")
        x = data["X"].astype(np.float64)
        y = data["y"].astype(int)
    if x.shape != (450, 3, 2048) or y.shape != (450,):
        raise ValueError(f"{path}: unexpected pool shape {x.shape}, {y.shape}")
    if any(np.count_nonzero(y == i) != 150 for i in range(3)):
        raise ValueError(f"{path}: pool is not 150/class")
    return x, y


def _normalize(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    return x / (np.max(np.abs(x)) + 1e-12)


def _envelope_spectrum(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Fixed 500--2000 Hz demodulation for like-for-like visualization."""
    sos = butter(4, (500.0, 2000.0), btype="bandpass", fs=FS, output="sos")
    band = sosfiltfilt(sos, np.asarray(x, dtype=float))
    env = np.abs(hilbert(band))
    env -= env.mean()
    spec = np.abs(np.fft.rfft(env * np.hanning(len(env))))
    freq = np.fft.rfftfreq(len(env), 1.0 / FS)
    return freq, spec


def _first_by_class(x: np.ndarray, y: np.ndarray, class_index: int) -> np.ndarray:
    indices = np.flatnonzero(y == class_index)
    if len(indices) == 0:
        raise ValueError(f"class index {class_index} has no samples")
    return x[indices[0]]


def fig_waveforms() -> None:
    """Deterministically selected PU time traces and envelope spectra."""
    apply_style(6.7)
    real_x, real_y, _ = load_file_split("train", MAIN_COND)
    sources: dict[str, tuple[np.ndarray, np.ndarray]] = {"real": (real_x, real_y)}
    sources.update({name: _pool(path) for name, path in POOL_FILES.items()})
    source_order = ("real", "llm", "rule", "random_open_loop")
    freqs = fault_freqs(CONDITIONS[MAIN_COND][0] / 60.0)

    fig, axes = plt.subplots(6, 4, figsize=(7.2, 7.0), sharex="row")
    time_n = int(0.05 * FS)
    t_ms = np.arange(time_n) / FS * 1000.0
    for class_index, class_name in enumerate(CLASSES):
        for col, source in enumerate(source_order):
            x, y = sources[source]
            sample = _first_by_class(x, y, class_index)[0]
            color = METHOD_COLORS[source]
            ax_t = axes[2 * class_index, col]
            ax_t.plot(t_ms, _normalize(sample[:time_n]), color=color, lw=0.65)
            ax_t.set_ylim(-1.08, 1.08)
            ax_t.set_yticks((-1, 0, 1))
            if class_index == 0:
                ax_t.set_title(SOURCE_NAMES[source], fontsize=7.5, color=color)
            if col == 0:
                ax_t.set_ylabel(f"{CLASS_NAMES[class_name]}\ntime")
            ax_t.tick_params(labelbottom=False)

            ax_e = axes[2 * class_index + 1, col]
            f_env, s_env = _envelope_spectrum(sample)
            keep = f_env <= 220.0
            ax_e.plot(f_env[keep], _normalize(s_env[keep]), color=color, lw=0.7)
            ax_e.set_xlim(0, 220)
            ax_e.set_ylim(0, 1.05)
            if class_name in ("OR", "IR"):
                key = "BPFO" if class_name == "OR" else "BPFI"
                ax_e.axvline(freqs[key], color=PALETTE["rose"], ls="--", lw=0.75)
                ax_e.text(freqs[key], 0.98, key, rotation=90, ha="right", va="top",
                          fontsize=5.4, color=PALETTE["rose"])
            if col == 0:
                ax_e.set_ylabel("Envelope")
            if class_index == len(CLASSES) - 1:
                ax_e.set_xlabel("Frequency [Hz]")
            else:
                ax_e.tick_params(labelbottom=False)
        panel_label(axes[2 * class_index, 0], chr(ord("a") + class_index), x=-0.36, y=1.06)
    fig.text(0.52, 0.994, "First ordered window per class; fixed 500--2000 Hz demodulation",
             ha="center", va="top", fontsize=6.2, color=PALETTE["neutral_mid"])
    fig.tight_layout(h_pad=0.28, w_pad=0.55, rect=(0, 0, 1, 0.985))
    save_figure(fig, FIGS / "waveforms.pdf")
    plt.close(fig)


def fig_boxplots() -> None:
    """PU RMS and kurtosis distributions with matched 150/class budgets."""
    apply_style(6.8)
    real_x, real_y, _ = load_file_split("train", MAIN_COND)
    sources: dict[str, tuple[np.ndarray, np.ndarray]] = {"real": (real_x, real_y)}
    sources.update({name: _pool(path) for name, path in POOL_FILES.items()})
    order = ("real", "llm", "rule", "random_open_loop")

    fig, axes = plt.subplots(2, 3, figsize=(7.2, 3.55), sharex=True)
    for col, class_name in enumerate(CLASSES):
        for row_index, metric in enumerate(("RMS", "Kurtosis")):
            values = []
            for source in order:
                x, y = sources[source]
                windows = x[y == col][:150, 0]
                if windows.shape[0] != 150:
                    raise ValueError(f"{source}/{class_name}: expected 150 windows")
                if metric == "RMS":
                    values.append(np.sqrt(np.mean(windows**2, axis=1)))
                else:
                    values.append(kurtosis(windows, axis=1, fisher=False, bias=False))
            ax = axes[row_index, col]
            bp = ax.boxplot(
                values,
                tick_labels=[SOURCE_NAMES[name] for name in order],
                widths=0.56,
                patch_artist=True,
                showfliers=True,
                flierprops={"markersize": 1.2, "markerfacecolor": "none", "markeredgewidth": 0.4},
                medianprops={"color": "black", "lw": 0.9},
                whiskerprops={"lw": 0.65},
                capprops={"lw": 0.65},
            )
            for patch, source in zip(bp["boxes"], order):
                patch.set_facecolor(METHOD_COLORS[source])
                patch.set_alpha(0.72 if source != "real" else 0.45)
                patch.set_linewidth(0.65)
            if row_index == 0:
                ax.set_title(CLASS_NAMES[class_name], fontsize=7.5)
            if col == 0:
                ax.set_ylabel(metric)
            ax.tick_params(axis="x", rotation=24, labelsize=5.5)
    panel_label(axes[0, 0], "a", x=-0.29)
    panel_label(axes[1, 0], "b", x=-0.29)
    fig.tight_layout(h_pad=0.65, w_pad=0.8)
    save_figure(fig, FIGS / "boxplots.pdf")
    plt.close(fig)


def _format_metric(value: float, metric: str) -> str:
    if metric == "psd_w1_mean":
        return f"{value:.0f}"
    if metric == "nn_diversity":
        return f"{value:.1f}"
    return f"{value:.3f}"


def fig_metric_distances() -> None:
    """Class-averaged physical diagnostics with explicit missing pools."""
    apply_style(6.6)
    datasets = ("pu", "cwru", "berkeley")
    pools = ("llm", "rule", "random_open_loop", "noise_aug")
    metrics = ("rms_w1", "psd_w1_mean", "band_energy_relative_error_mean", "nn_diversity")
    metric_labels = ("RMS W1", "PSD W1", "Band error", "NN diversity")
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.15))
    cmap = plt.get_cmap("Blues").copy()
    cmap.set_bad("#EEEEEE")

    for ax, dataset, label in zip(axes, datasets, "abc"):
        path = PHYSICS / f"physics_frozen_full_v3_{dataset}" / "physics_metrics.csv"
        rows = _rows(path, ("pool", "class", "metric", "value"))
        availability = _rows(
            PHYSICS / f"physics_frozen_full_v3_{dataset}" / "physics_pool_availability.csv",
            ("pool", "status"),
        )
        available = {row["pool"] for row in availability if row["status"] == "available"}
        raw = np.full((len(pools), len(metrics)), np.nan)
        for i, pool in enumerate(pools):
            if pool not in available:
                continue
            for j, metric in enumerate(metrics):
                values = [float(row["value"]) for row in rows if row["pool"] == pool and row["metric"] == metric]
                if not values:
                    raise ValueError(f"{dataset}/{pool}/{metric}: no values despite available status")
                raw[i, j] = float(np.mean(values))
        scaled = raw.copy()
        for j in range(len(metrics)):
            maximum = np.nanmax(raw[:, j])
            scaled[:, j] = raw[:, j] / maximum if maximum > 0 else raw[:, j]
        ax.imshow(np.ma.masked_invalid(scaled), cmap=cmap, norm=Normalize(0, 1), aspect="auto")
        ax.set_xticks(range(len(metrics)), metric_labels, rotation=34, ha="right")
        ax.set_yticks(range(len(pools)), [SOURCE_NAMES.get(pool, "Noise") for pool in pools])
        ax.set_title(dataset.upper() if dataset != "berkeley" else "Berkeley", fontsize=7.6)
        for i in range(len(pools)):
            for j, metric in enumerate(metrics):
                if np.isfinite(raw[i, j]):
                    color = "white" if scaled[i, j] > 0.63 else PALETTE["neutral_dark"]
                    ax.text(j, i, _format_metric(raw[i, j], metric), ha="center", va="center",
                            fontsize=5.7, color=color)
                else:
                    ax.text(j, i, "NA", ha="center", va="center", fontsize=5.7,
                            color=PALETTE["neutral_mid"])
        panel_label(ax, label, x=-0.2)
        ax.tick_params(length=0, labelsize=5.8)
    fig.text(0.5, 0.015, "Colour is max-scaled within dataset and metric; cells report raw class means.",
             ha="center", fontsize=6.1, color=PALETTE["neutral_mid"])
    fig.tight_layout(w_pad=0.8, rect=(0, 0.045, 1, 1))
    save_figure(fig, FIGS / "metric_distances.pdf")
    plt.close(fig)


def _read_method_file(path: Path, method: str) -> list[dict[str, str]]:
    rows = _rows(path, ("n_real", "seed", "acc", "macro_f1"))
    for row in rows:
        row["method"] = method
    return rows


def _paired_deltas(rows: list[dict[str, str]], shot: int, metric: str, comparator: str) -> np.ndarray:
    by = {(row["method"], int(row["n_real"]), int(row["seed"])): float(row[metric]) for row in rows}
    seeds = sorted(seed for method, n_real, seed in by if method == "llm" and n_real == shot)
    deltas = []
    for seed in seeds:
        llm_key = ("llm", shot, seed)
        other_key = (comparator, shot, seed)
        if other_key not in by:
            raise ValueError(f"missing paired row {other_key}")
        deltas.append(by[llm_key] - by[other_key])
    if not deltas:
        raise ValueError(f"no paired deltas for shot={shot}, metric={metric}, comparator={comparator}")
    return np.asarray(deltas)


def _delta_panel(ax, rows, shots, comparators, title, label) -> None:
    metric_order = ("acc", "macro_f1")
    y_labels = []
    y_base = []
    for shot in shots:
        for metric in metric_order:
            y_labels.append(f"{shot}  {'Acc.' if metric == 'acc' else 'F1'}")
            y_base.append(len(y_base))
    offsets = (-0.13, 0.13)
    comp_colors = (PALETTE["orange"], PALETTE["teal"])
    for comp_index, comparator in enumerate(comparators):
        for row_index, (shot, metric) in enumerate((s, m) for s in shots for m in metric_order):
            deltas = _paired_deltas(rows, shot, metric, comparator)
            pos = y_base[row_index] + offsets[comp_index]
            jitter = np.linspace(-0.055, 0.055, len(deltas))
            ax.scatter(deltas * 100, pos + jitter, s=5, color=comp_colors[comp_index], alpha=0.34,
                       linewidths=0, rasterized=False)
            q1, median, q3 = np.quantile(deltas * 100, (0.25, 0.5, 0.75))
            ax.plot((q1, q3), (pos, pos), color=comp_colors[comp_index], lw=1.8)
            ax.plot(median, pos, marker="D", ms=2.8, color=comp_colors[comp_index], mec="white", mew=0.35)
        ax.plot([], [], color=comp_colors[comp_index], lw=1.8, marker="D", ms=2.8,
                label=f"LLM - {comparator.replace('_', ' ')}")
    ax.axvline(0, color=PALETTE["neutral_dark"], lw=0.75, ls="--")
    ax.set_yticks(y_base, y_labels)
    ax.invert_yaxis()
    ax.set_xlabel("Paired delta [percentage points]")
    ax.set_title(title, fontsize=7.6)
    ax.legend(fontsize=5.4, loc="lower right")
    panel_label(ax, label, x=-0.2)


def fig_downstream() -> None:
    """Seed-level paired downstream deltas for the three formal protocols."""
    apply_style(6.5)
    pu = _rows(PHASE / "results" / "phaseA_v2_downstream_cnn.csv",
               ("baseline", "n_real", "seed", "acc", "macro_f1"), count=320)
    pu_map = {
        "phaseA_v2_llm_k3": "llm",
        "phaseA_v2_rule": "rule",
        "phaseA_v2_random_open_loop": "random_open_loop",
        "real_only": "real_only",
    }
    pu_rows = [{**row, "method": pu_map[row["baseline"]]} for row in pu]

    cwru_rows = []
    for method in ("llm", "rule", "noise_aug"):
        cwru_rows += _read_method_file(CWRU / "downstream" / f"within_load0_{method}_nsyn20.csv", method)
    if len(cwru_rows) != 360:
        raise ValueError(f"CWRU within-load figure source must contain 360 rows, found {len(cwru_rows)}")

    berkeley_rows = []
    for method in ("llm", "rule", "noise_aug"):
        berkeley_rows += _read_method_file(
            BERKELEY / "downstream_40seed_nsyn20" / f"berkeley_v2_binary_{method}_nsyn20.csv", method
        )
    if len(berkeley_rows) != 360:
        raise ValueError(f"Berkeley figure source must contain 360 rows, found {len(berkeley_rows)}")

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.7))
    _delta_panel(axes[0], pu_rows, (5, 10, 25), ("rule", "random_open_loop"), "PU file split", "a")
    _delta_panel(axes[1], cwru_rows, (5, 10, 25), ("rule", "noise_aug"), "CWRU within load 0", "b")
    _delta_panel(axes[2], berkeley_rows, (2, 5, 10), ("rule", "noise_aug"), "Berkeley binary", "c")
    fig.tight_layout(w_pad=0.9)
    save_figure(fig, FIGS / "downstream_bars.pdf")
    plt.close(fig)


def fig_acceptance() -> None:
    """Offline v2 rescreen: archived candidate depth and slot/window units."""
    apply_style(6.6)
    llm_slots = _rows(
        PHASE / "runs" / "rescreen_v2_full" / "slot_summary.csv",
        ("class", "accepted_before_diversity", "n_candidates"), count=450,
    )
    rule_slots = _rows(
        PHASE / "runs" / "recipe_ablation_rule_v2_full" / "slot_summary.csv",
        ("class", "accepted_slot", "n_candidates"), count=700,
    )
    random_slots = _rows(
        PHASE / "runs" / "recipe_ablation_random_v2_full" / "slot_summary.csv",
        ("class", "accepted_slot", "n_candidates"), count=450,
    )
    summary_path = PHASE / "runs" / "rescreen_v2_full" / "summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(summary_path)
    summary = json.loads(summary_path.read_text())
    if summary.get("slots") != 450 or summary.get("accepted_slots_before_diversity") != 286:
        raise ValueError("LLM rescreen summary does not match the frozen 450-slot/286-admitted record")

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.55))
    ax = axes[0]
    depths = np.arange(1, 5)
    totals = np.array([sum(int(row["n_candidates"]) == depth for row in llm_slots) for depth in depths])
    accepted = np.array([
        sum(int(row["n_candidates"]) == depth and row["accepted_before_diversity"] == "True" for row in llm_slots)
        for depth in depths
    ])
    ax.bar(depths, totals, color=PALETTE["neutral_soft"], edgecolor="black", lw=0.45, label="Archived slots")
    ax.bar(depths, accepted, color=PALETTE["blue"], edgecolor="black", lw=0.45, label="Admitted slots")
    ax.set_xticks(depths)
    ax.set_xlabel("Candidates archived for slot")
    ax.set_ylabel("Slot count")
    ax.legend(fontsize=5.4)
    panel_label(ax, "a")

    ax = axes[1]
    classes = tuple(CLASSES)
    slots = np.array([sum(row["class"] == cls for row in llm_slots) for cls in classes])
    admitted = np.array([
        sum(row["class"] == cls and row["accepted_before_diversity"] == "True" for row in llm_slots)
        for cls in classes
    ])
    windows = np.array([summary["kept_by_class"][cls] for cls in classes])
    x = np.arange(len(classes))
    width = 0.25
    for offset, values, name, color in (
        (-width, slots, "Proposal slots", PALETTE["neutral_soft"]),
        (0, admitted, "Admitted slots", PALETTE["blue_soft"]),
        (width, windows, "Kept windows", PALETTE["blue"]),
    ):
        ax.bar(x + offset, values, width, color=color, edgecolor="black", lw=0.4, label=name)
    ax.set_xticks(x, [CLASS_NAMES[c] for c in classes], rotation=20, ha="right")
    ax.set_ylabel("Count")
    ax.legend(fontsize=5.2)
    panel_label(ax, "b")

    ax = axes[2]
    source_rows = (("LLM", llm_slots, "accepted_before_diversity", PALETTE["blue"]),
                   ("Rule", rule_slots, "accepted_slot", PALETTE["orange"]),
                   ("Random", random_slots, "accepted_slot", PALETTE["neutral_mid"]))
    width = 0.24
    for i, (name, rows, field, color) in enumerate(source_rows):
        rates = []
        for cls in classes:
            class_rows = [row for row in rows if row["class"] == cls]
            rates.append(100 * sum(row[field] == "True" for row in class_rows) / len(class_rows))
        positions = x + (i - 1) * width
        ax.bar(positions, rates, width, color=color, edgecolor="black", lw=0.4, label=name)
        for position, rate in zip(positions, rates):
            if rate == 0:
                ax.text(position, 0.9, "0", ha="center", va="bottom", fontsize=5.3,
                        color=PALETTE["neutral_mid"])
    ax.set_xticks(x, [CLASS_NAMES[c] for c in classes], rotation=20, ha="right")
    ax.set_ylabel("Verifier slot admission [%]")
    ax.set_ylim(0, 80)
    ax.legend(fontsize=5.3)
    panel_label(ax, "c")
    fig.tight_layout(w_pad=0.9)
    save_figure(fig, FIGS / "acceptance_k.pdf")
    plt.close(fig)


def _cwru_delta_matrix(metric: str) -> tuple[np.ndarray, list[str]]:
    rows = _rows(CWRU / "cwru_patch_v2_summary.csv", ("split", "method", "n_real", "metric", "mean"), count=120)
    splits = [f"lolo_load{i}" for i in range(1, 4)]
    shots = (5, 10, 25)
    lookup = {(row["split"], row["method"], int(row["n_real"]), row["metric"]): float(row["mean"]) for row in rows}
    matrix = np.array([
        [lookup[(split, "llm", shot, metric)] - lookup[(split, "rule", shot, metric)] for shot in shots]
        for split in splits
    ])
    return matrix, [f"Held-out load {i}" for i in range(1, 4)]


def _pu_pass_matrix(path: Path) -> tuple[np.ndarray, list[str]]:
    rows = _rows(path, ("split", "n_real", "metric", "passed_holm"), count=96)
    splits = sorted({row["split"] for row in rows})
    columns = [(shot, metric) for shot in (5, 10, 25) for metric in ("acc", "macro_f1")]
    matrix = np.zeros((len(splits), len(columns)), dtype=int)
    for i, split in enumerate(splits):
        for j, (shot, metric) in enumerate(columns):
            cell = [row for row in rows if row["split"] == split and int(row["n_real"]) == shot and row["metric"] == metric]
            if len(cell) != 4:
                raise ValueError(f"PU LOCO cell {split}/{shot}/{metric} must contain four registered comparisons")
            matrix[i, j] = sum(row["passed_holm"] == "True" and float(row["mean_delta"]) > 0 for row in cell)
    return matrix, [split.removeprefix("loco_").replace("_", " ") for split in splits]


def fig_cross_condition() -> None:
    """CWRU positive load transfer beside complete PU LOCO failure cells."""
    apply_style(6.2)
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.0), gridspec_kw={"width_ratios": (0.82, 1.28)})
    for row_index, (metric, title, label) in enumerate((("acc", "CWRU: LLM - rule Accuracy", "a"),
                                                        ("macro_f1", "CWRU: LLM - rule Macro-F1", "c"))):
        matrix, row_labels = _cwru_delta_matrix(metric)
        ax = axes[row_index, 0]
        ax.imshow(matrix * 100, cmap="Blues", vmin=0, vmax=max(1.0, float(np.max(matrix * 100))), aspect="auto")
        ax.set_xticks(range(3), ("5", "10", "25"))
        ax.set_yticks(range(3), row_labels)
        ax.set_xlabel("Real windows/class")
        ax.set_title(title, fontsize=7.2)
        for i in range(3):
            for j in range(3):
                ax.text(j, i, f"{matrix[i, j] * 100:+.1f}", ha="center", va="center", fontsize=5.8,
                        color="white" if matrix[i, j] > np.max(matrix) * 0.58 else PALETTE["neutral_dark"])
        panel_label(ax, label, x=-0.3)

    for row_index, (directory, title, label) in enumerate(((PU_LOCO_V1, "PU LOCO v1: passed / 4 tests", "b"),
                                                            (PU_LOCO_V2, "PU LOCO v2: passed / 4 tests", "d"))):
        matrix, row_labels = _pu_pass_matrix(directory / "pu_loco_wilcoxon.csv")
        ax = axes[row_index, 1]
        ax.imshow(matrix, cmap="Blues", vmin=0, vmax=4, aspect="auto")
        ax.set_xticks(range(6), ("5 A", "5 F1", "10 A", "10 F1", "25 A", "25 F1"), rotation=25, ha="right")
        ax.set_yticks(range(4), row_labels)
        ax.set_title(title, fontsize=7.2)
        for i in range(4):
            for j in range(6):
                ax.text(j, i, f"{matrix[i, j]}/4", ha="center", va="center", fontsize=5.7,
                        color="white" if matrix[i, j] >= 3 else PALETTE["neutral_dark"])
        panel_label(ax, label, x=-0.2)
    fig.tight_layout(h_pad=0.9, w_pad=1.0)
    save_figure(fig, FIGS / "cross_condition_heatmap.pdf")
    plt.close(fig)


def fig_failure_reasons() -> None:
    """Non-exclusive gate-failure shares for LLM and random recipe sources."""
    apply_style(6.6)
    rows = _rows(
        PHASE / "results" / "phaseA_v2_failure_gate_summary.csv",
        ("source", "class", "gate", "share_of_all_slots"),
    )
    sources = (("llm_k3_rescreen_v2", "Cached LLM K=3 rescreen"),
               ("random_plus_verifier", "Random recipes + verifier"))
    gates = sorted({row["gate"] for row in rows})
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), sharey=True)
    class_colors = {"healthy": PALETTE["green"], "OR": PALETTE["orange"], "IR": PALETTE["blue"]}
    y = np.arange(len(gates))
    offsets = (-0.22, 0, 0.22)
    for ax, (source, title), label in zip(axes, sources, "ab"):
        for offset, cls in zip(offsets, CLASSES):
            values = []
            for gate in gates:
                cell = [row for row in rows if row["source"] == source and row["class"] == cls and row["gate"] == gate]
                values.append(100 * float(cell[0]["share_of_all_slots"]) if cell else 0.0)
            ax.barh(y + offset, values, height=0.2, color=class_colors[cls], edgecolor="black", lw=0.35,
                    label=CLASS_NAMES[cls])
        ax.set_yticks(y, [gate.replace("_", " ") for gate in gates])
        ax.invert_yaxis()
        ax.set_xlabel("Slots with gate failure [%]")
        ax.set_title(title, fontsize=7.4)
        ax.legend(fontsize=5.5)
        panel_label(ax, label, x=-0.2)
    fig.text(0.5, 0.01, "Gate reasons overlap; percentages are not additive.", ha="center",
             fontsize=6.1, color=PALETTE["neutral_mid"])
    fig.tight_layout(w_pad=0.9, rect=(0, 0.04, 1, 1))
    save_figure(fig, FIGS / "failure_reasons.pdf")
    plt.close(fig)


def fig_failure_case() -> None:
    """Complete PU LOCO v1--v6 evidence-stop chain."""
    apply_style(6.6)
    v1 = _rows(PU_LOCO_V1 / "pu_loco_wilcoxon.csv", ("passed_holm", "mean_delta"), count=96)
    v2 = _rows(PU_LOCO_V2 / "pu_loco_wilcoxon.csv", ("passed_holm", "mean_delta"), count=96)
    v1_fail = sum(not (row["passed_holm"] == "True" and float(row["mean_delta"]) > 0) for row in v1)
    v2_fail = sum(not (row["passed_holm"] == "True" and float(row["mean_delta"]) > 0) for row in v2)
    required_reports = (
        PU_LOCO_V3 / "morphology_condition_map.md",
        PU_LOCO_V4 / "s2_s1_acceptance_failure.md",
        PU_LOCO_V5 / "pu_loco_v5_failure_analysis.md",
    )
    for path in required_reports:
        if not path.exists():
            raise FileNotFoundError(path)
    v6_rows = _rows(
        PU_LOCO_V6 / "source_separability_summary.csv",
        ("target_condition", "target_terminal_cscoh_failure"), count=8,
    )
    terminal_targets = len({row["target_condition"] for row in v6_rows if row["target_terminal_cscoh_failure"] == "True"})
    if terminal_targets != 4:
        raise ValueError(f"PU LOCO v6 expected four terminal targets, found {terminal_targets}")

    stages = (
        ("v1", "Formal held-out", f"{v1_fail}/96 fail\nkinematic\nmismatch", True),
        ("v2", "Formal held-out", f"{v2_fail}/96 fail\nfrequency fix\ninsufficient", True),
        ("v3", "Train-only\ndevelopment", "morphology map\nno balanced pool", False),
        ("v4", "Train-only\nadmission", "S1/S2 candidate\npools fail", False),
        ("v5", "Train-only\nsanity", "wrong-label/noise\ncontrols admitted", False),
        ("v6", "Source-only\nevidence", f"CSCoh fails\n{terminal_targets}/4 targets stop", False),
    )
    fig, ax = plt.subplots(figsize=(7.2, 2.45))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4)
    ax.axis("off")
    for i, (version, scope, outcome, formal) in enumerate(stages):
        x = 0.25 + i * 1.95
        face = "#E8F0FA" if formal else "#F5F5F5"
        edge = PALETTE["blue"] if formal else PALETTE["neutral_mid"]
        box = FancyBboxPatch((x, 1.0), 1.55, 1.75, boxstyle="round,pad=0.03,rounding_size=0.04",
                             fc=face, ec=edge, lw=0.8)
        ax.add_patch(box)
        ax.text(x + 0.12, 2.58, version, fontsize=7.6, fontweight="bold", color=edge, va="top")
        ax.text(x + 0.12, 2.27, scope, fontsize=5.3, color=PALETTE["neutral_mid"], va="top")
        ax.text(x + 0.12, 1.63, outcome, fontsize=5.8, color=PALETTE["neutral_dark"], va="top")
        ax.text(x + 0.78, 0.72, "FORMAL" if formal else "NO HELD-OUT TEST", ha="center",
                fontsize=5.4, color=edge, fontweight="bold")
        if i < len(stages) - 1:
            ax.add_patch(FancyArrowPatch((x + 1.56, 1.88), (x + 1.91, 1.88), arrowstyle="-|>",
                                         mutation_scale=8, lw=0.7, color=PALETTE["neutral_mid"]))
    ax.text(0.25, 3.55, "PU leave-one-condition-out: the complete predeclared failure chain",
            fontsize=8.5, fontweight="bold", va="top")
    ax.text(0.25, 0.18, "v3--v6 are development/admission stops, not hidden formal downstream tests.",
            fontsize=6.2, color=PALETTE["rose"])
    save_figure(fig, FIGS / "failure_case.pdf")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="+", default=None)
    args = parser.parse_args()
    figures = {
        "waveforms": fig_waveforms,
        "boxplots": fig_boxplots,
        "metrics": fig_metric_distances,
        "downstream": fig_downstream,
        "acceptance": fig_acceptance,
        "cross_condition": fig_cross_condition,
        "failure": fig_failure_reasons,
        "failure_case": fig_failure_case,
    }
    for name, function in figures.items():
        if args.only and name not in args.only:
            continue
        function()
        print(f"{name}: ok", flush=True)


if __name__ == "__main__":
    main()
