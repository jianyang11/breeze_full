"""Preview-only Nature-style rebuild of BREEZE Fig. 3 and later figures."""
from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap, ListedColormap, TwoSlopeNorm

import figure_revision_data as data


WIDTH_IN = 183.0 / 25.4
BLUE = "#0F4D92"
ORANGE = "#D67A2C"
TEAL = "#2A8C82"
GRAY = "#777777"
DARK = "#2F2F2F"
LIGHT = "#D9D9D9"
ROSE = "#A33A3A"
METHOD_COLORS = {
    "real": DARK,
    "real_reference": DARK,
    "llm": BLUE,
    "rule": ORANGE,
    "random_open_loop": GRAY,
    "noise_aug": TEAL,
}
METHOD_MARKERS = {
    "real_reference": "D",
    "llm": "o",
    "rule": "s",
    "random_open_loop": "^",
    "noise_aug": "v",
}
METHOD_LINESTYLES = {
    "real": "-",
    "llm": (0, (5, 1.8)),
    "rule": (0, (2.2, 1.5)),
    "random_open_loop": (0, (1, 1.4)),
}
SOURCE_ORDER = ("real", "llm", "rule", "random_open_loop")


def apply_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 6.2,
            "axes.titlesize": 7.0,
            "axes.labelsize": 6.3,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.labelsize": 5.7,
            "ytick.labelsize": 5.7,
            "xtick.major.width": 0.7,
            "ytick.major.width": 0.7,
            "xtick.major.size": 2.5,
            "ytick.major.size": 2.5,
            "legend.fontsize": 5.7,
            "legend.frameon": False,
            "lines.linewidth": 1.0,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": "breeze-figure-revision-v1",
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def panel_label(ax: plt.Axes, label: str, x: float = -0.14, y: float = 1.04) -> None:
    ax.text(
        x,
        y,
        label,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=8.5,
        fontweight="bold",
        clip_on=False,
    )


def save_preview(fig: plt.Figure, directory: Path, stem: str) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths = [directory / f"{stem}.{suffix}" for suffix in ("pdf", "svg", "png", "tiff")]
    fig.savefig(
        paths[0],
        metadata={
            "Creator": "BREEZE figure revision",
            "CreationDate": None,
            "ModDate": None,
        },
    )
    fig.savefig(paths[1], metadata={"Date": None})
    svg_lines = paths[1].read_text().splitlines()
    paths[1].write_text("\n".join(line.rstrip() for line in svg_lines) + "\n")
    fig.savefig(paths[2], dpi=300)
    fig.savefig(paths[3], dpi=600, pil_kwargs={"compression": "tiff_lzw"})
    plt.close(fig)
    return paths


def _nice_symmetric_limit(values: np.ndarray, minimum: float = 1.0) -> float:
    maximum = max(minimum, float(np.nanmax(np.abs(values))) * 1.12)
    step = 0.5 if maximum < 5 else 1.0 if maximum < 20 else 5.0
    return math.ceil(maximum / step) * step


def figure3() -> tuple[Path, list[Path]]:
    summary, seeds, sources = data.build_fig3_data()
    out = data.PREVIEW / "fig3_downstream_effects"
    out.mkdir(parents=True, exist_ok=True)
    summary_path = out / "source_data.csv"
    seeds_path = out / "paired_seed_deltas.csv"
    summary.to_csv(summary_path, index=False, lineterminator="\n")
    seeds.to_csv(seeds_path, index=False, lineterminator="\n")

    apply_style()
    fig, axes = plt.subplots(
        2,
        3,
        figsize=(WIDTH_IN, 112 / 25.4),
        sharey=False,
        constrained_layout=True,
    )
    datasets = ("PU", "CWRU", "Berkeley")
    nonstructured = {"PU": "random_open_loop", "CWRU": "noise_aug", "Berkeley": "noise_aug"}
    rule_values = summary[summary["comparison"].eq("rule")][["ci_low_pp", "ci_high_pp"]].to_numpy()
    rule_limit = _nice_symmetric_limit(rule_values)
    axis_rows = []
    for row_index in range(2):
        for column, dataset_name in enumerate(datasets):
            comparator = "rule" if row_index == 0 else nonstructured[dataset_name]
            subset = summary[
                summary["dataset"].eq(dataset_name)
                & summary["comparison"].eq(comparator)
            ].copy()
            shots = sorted(subset["shot"].unique())
            order = [(shot, metric) for shot in shots for metric in ("acc", "macro_f1")]
            subset["order"] = [order.index((row.shot, row.metric)) for row in subset.itertuples()]
            subset = subset.sort_values("order")
            ax = axes[row_index, column]
            ax.axvline(0, color=DARK, lw=1.05, zorder=0)
            for y, row in enumerate(subset.itertuples(index=False)):
                marker = "o" if row.metric == "acc" else "s"
                face = BLUE if row.passed_holm else "white"
                ax.plot(
                    [row.ci_low_pp, row.ci_high_pp],
                    [y, y],
                    color=BLUE,
                    lw=1.1,
                    solid_capstyle="round",
                    zorder=2,
                )
                ax.scatter(
                    row.effect_pp,
                    y,
                    s=21,
                    marker=marker,
                    facecolor=face,
                    edgecolor=BLUE,
                    linewidth=0.85,
                    zorder=3,
                )
            labels = [f"{shot}  {'Acc' if metric == 'acc' else 'F1'}" for shot, metric in order]
            ax.set_yticks(range(len(order)), labels if column == 0 else [])
            ax.invert_yaxis()
            if row_index == 0:
                limit = rule_limit
                descriptor = "LLM - rule"
            else:
                values = subset[["ci_low_pp", "ci_high_pp"]].to_numpy()
                limit = _nice_symmetric_limit(values)
                descriptor = f"LLM - {'random open-loop' if comparator == 'random_open_loop' else 'noise'}"
            ax.set_xlim(-limit, limit)
            ax.grid(axis="x", color="#E6E6E6", lw=0.55, zorder=-1)
            ax.set_title(dataset_name, pad=10 if row_index == 0 else 7, fontweight="bold")
            ax.text(0.5, 1.015, descriptor, transform=ax.transAxes, ha="center", va="bottom", fontsize=5.8)
            ax.text(
                0.02,
                0.04,
                f"n={int(subset['n_pairs'].iloc[0])} paired seeds\nx range: +/-{limit:g} pp",
                transform=ax.transAxes,
                ha="left",
                va="bottom",
                fontsize=5.2,
                color=GRAY,
            )
            if row_index == 1:
                ax.set_xlabel("Paired effect (percentage points)")
            if column == 0:
                ax.set_ylabel("Few-shot setting / metric")
            panel_label(ax, chr(ord("a") + row_index * 3 + column))
            axis_rows.append(
                {"row": row_index + 1, "dataset": dataset_name, "comparison": comparator, "x_min_pp": -limit, "x_max_pp": limit}
            )
    axis_path = out / "axis_limits.csv"
    pd.DataFrame(axis_rows).to_csv(axis_path, index=False, lineterminator="\n")
    figure_paths = save_preview(fig, out, "fig3_downstream_effects")
    outputs = [summary_path, seeds_path, axis_path, *figure_paths]
    manifest = data.write_source_manifest(
        out,
        sources,
        {
            "protocols": "PU file split; CWRU within load0; Berkeley preregistered held-out case split",
            "shots": {"PU": [5, 10, 25], "CWRU": [5, 10, 25], "Berkeley": [2, 5, 10]},
            "comparisons": "row 1 LLM-rule; row 2 PU LLM-random, CWRU/Berkeley LLM-noise",
            "bootstrap": f"paired percentile, {data.BOOTSTRAP_RESAMPLES} resamples, seed {data.BOOTSTRAP_SEED}",
        },
        {"summary_cells": len(summary), "paired_seed_rows": len(seeds)},
        outputs,
        notes=["Seeds repeat few-shot subset selection/CNN initialization around a fixed synthetic pool."],
    )
    return manifest, outputs


def _plot_waveform_envelope(
    classes: tuple[str, ...],
    directory_name: str,
    stem: str,
    figure_height_mm: float,
) -> tuple[Path, list[Path]]:
    medoids, waveforms, envelope, sources = data.build_fig4_data(classes)
    out = data.PREVIEW / directory_name
    out.mkdir(parents=True, exist_ok=True)
    medoid_path = out / "medoids.csv"
    waveform_path = out / "waveform_source_data.csv"
    envelope_path = out / "envelope_source_data.csv"
    medoids.to_csv(medoid_path, index=False, lineterminator="\n")
    waveforms.to_csv(waveform_path, index=False, lineterminator="\n")
    envelope.to_csv(envelope_path, index=False, lineterminator="\n")

    apply_style()
    fig, axes = plt.subplots(
        2 * len(classes),
        4,
        figsize=(WIDTH_IN, figure_height_mm / 25.4),
        constrained_layout=True,
        squeeze=False,
    )
    frequencies = data.fault_freqs(data.CONDITIONS[data.MAIN_COND][0] / 60.0)
    for class_row, cls in enumerate(classes):
        class_wave = waveforms[waveforms["class"].eq(cls)]
        peak = class_wave["amplitude"].abs().max() * 1.08
        class_env = envelope[envelope["class"].eq(cls)]
        env_max = class_env["q75"].max() * 1.08
        target_key = "BPFO" if cls == "OR" else "BPFI" if cls == "IR" else None
        for column, source in enumerate(SOURCE_ORDER):
            color = METHOD_COLORS[source]
            ax_wave = axes[2 * class_row, column]
            trace = class_wave[class_wave["source"].eq(source)].sort_values("sample")
            ax_wave.plot(trace["time_ms"], trace["amplitude"], color=color, lw=0.75)
            ax_wave.set_xlim(0, 50)
            ax_wave.set_ylim(-peak, peak)
            ax_wave.axhline(0, color="#D0D0D0", lw=0.45, zorder=0)
            if class_row == 0:
                ax_wave.set_title(data.METHOD_LABELS[source], color=color, fontweight="bold")
            if column == 0:
                ax_wave.set_ylabel(f"{data.CLASS_LABELS[cls]}\nAmplitude")
            else:
                ax_wave.set_yticklabels([])
            ax_wave.set_xlabel("Time (ms)")

            ax_env = axes[2 * class_row + 1, column]
            spectrum = class_env[class_env["source"].eq(source)].sort_values("frequency_hz")
            ax_env.fill_between(
                spectrum["frequency_hz"],
                spectrum["q25"],
                spectrum["q75"],
                color=color,
                alpha=0.20,
                linewidth=0,
            )
            ax_env.plot(spectrum["frequency_hz"], spectrum["median"], color=color, lw=0.9)
            ax_env.set_xlim(0, 220)
            ax_env.set_ylim(0, env_max)
            if target_key:
                target = frequencies[target_key]
                ax_env.axvline(target, color=ROSE, ls=(0, (3, 2)), lw=0.8)
                if column == 0:
                    ax_env.text(
                        target,
                        env_max * 0.96,
                        f"{target_key} {target:.1f} Hz",
                        rotation=90,
                        ha="right",
                        va="top",
                        color=ROSE,
                        fontsize=5.2,
                    )
            if column == 0:
                ax_env.set_ylabel("Envelope\nspectrum")
            else:
                ax_env.set_yticklabels([])
            ax_env.set_xlabel("Frequency (Hz)")
        panel_label(axes[2 * class_row, 0], chr(ord("a") + class_row), x=-0.25)
    figure_paths = save_preview(fig, out, stem)
    outputs = [medoid_path, waveform_path, envelope_path, *figure_paths]
    manifest = data.write_source_manifest(
        out,
        sources,
        {
            "classes": list(classes),
            "real_reference": "PU N09_M07_F10 outer-training windows only",
            "medoid": "actual window nearest within-source/class coordinate-wise median after class-real median/MAD scaling",
            "waveform": "raw vibration amplitude; first 50 ms of fixed medoid; shared y range within class",
            "envelope": "all source/class windows; FIR 500-2000 Hz; squared envelope; Hann FFT; median and IQR; no per-source normalization",
        },
        {
            "medoids": len(medoids),
            "waveform_rows": len(waveforms),
            "envelope_rows": len(envelope),
        },
        outputs,
        notes=["The medoid is an interpretable representative; population spectra and Fig. 5 carry fidelity evidence."],
    )
    return manifest, outputs


def figure4() -> tuple[Path, list[Path]]:
    return _plot_waveform_envelope(
        ("OR", "IR"), "fig4_waveform_envelope", "fig4_waveform_envelope", 138
    )


def supplementary_s2() -> tuple[Path, list[Path]]:
    return _plot_waveform_envelope(
        ("healthy",), "figS2_healthy_waveform_envelope", "figS2_healthy_waveform_envelope", 78
    )


def supplementary_s1() -> tuple[Path, list[Path]]:
    snapshot, sources = data.build_s1_data()
    out = data.PREVIEW / "figS1_pu_distributions"
    out.mkdir(parents=True, exist_ok=True)
    source_path = out / "source_data.csv"
    snapshot.to_csv(source_path, index=False, lineterminator="\n")
    apply_style()
    fig, axes = plt.subplots(2, 3, figsize=(WIDTH_IN, 91 / 25.4), constrained_layout=True)
    for row, metric in enumerate(("RMS", "Kurtosis")):
        for column, cls in enumerate(data.CLASSES):
            ax = axes[row, column]
            subset = snapshot[snapshot["metric"].eq(metric) & snapshot["class"].eq(cls)]
            counts = []
            for source in SOURCE_ORDER:
                curve = subset[subset["source"].eq(source)].sort_values("rank")
                ax.plot(
                    curve["value"],
                    curve["ecdf"],
                    color=METHOD_COLORS[source],
                    linestyle=METHOD_LINESTYLES[source],
                    lw=1.05,
                    label=data.METHOD_LABELS[source],
                )
                counts.append(f"{data.METHOD_LABELS[source]} {int(curve['n_windows'].iloc[0])}")
            ax.set_ylim(0, 1)
            ax.grid(color="#E8E8E8", lw=0.5)
            if row == 0:
                ax.set_title(data.CLASS_LABELS[cls], fontweight="bold")
            if column == 0:
                ax.set_ylabel(f"{metric}\nECDF")
            else:
                ax.set_yticklabels([])
            ax.set_xlabel(metric)
            ax.text(0.98, 0.04, "n: " + ", ".join(counts), transform=ax.transAxes, ha="right", va="bottom", fontsize=4.8, color=GRAY)
            panel_label(ax, chr(ord("a") + row * 3 + column))
    axes[0, 0].legend(ncol=2, loc="upper left")
    figure_paths = save_preview(fig, out, "figS1_pu_distributions")
    outputs = [source_path, *figure_paths]
    manifest = data.write_source_manifest(
        out,
        sources,
        {"split": "PU outer-training only", "statistics": "empirical CDF; no inferential test"},
        {"source_rows": len(snapshot)},
        outputs,
    )
    return manifest, outputs


def _matrix_rows(frame: pd.DataFrame) -> tuple[list[str], list[str], np.ndarray]:
    method_order = [method for method in ("llm", "noise_aug", "random_open_loop") if method in set(frame["method"])]
    class_order = frame["class"].drop_duplicates().tolist()
    metric_order = [label for _, label in data.FIG5_METRICS]
    rows = [(method, cls) for method in method_order for cls in class_order]
    matrix = np.full((len(rows), len(metric_order)), np.nan)
    for i, (method, cls) in enumerate(rows):
        for j, label in enumerate(metric_order):
            cell = frame[
                frame["method"].eq(method)
                & frame["class"].eq(cls)
                & frame["metric_label"].eq(label)
            ]
            if len(cell) != 1:
                raise RuntimeError(f"physical matrix cell count {method}/{cls}/{label}: {len(cell)}")
            matrix[i, j] = float(cell.iloc[0]["log2_ratio"])
    short_class = {"healthy": "H", "OR": "OR", "IR": "IR", "B": "B", "degraded": "D"}
    short_method = {"llm": "LLM", "noise_aug": "Noise", "random_open_loop": "Random"}
    labels = [f"{short_method[method]}/{short_class[cls]}" for method, cls in rows]
    return labels, metric_order, matrix


def figure5() -> tuple[Path, list[Path]]:
    ratios, diversity, sources = data.build_fig5_data()
    out = data.PREVIEW / "fig5_physical_error"
    out.mkdir(parents=True, exist_ok=True)
    ratios_path = out / "physical_error_ratios.csv"
    diversity_path = out / "nn_diversity.csv"
    ratios.to_csv(ratios_path, index=False, lineterminator="\n")
    diversity.to_csv(diversity_path, index=False, lineterminator="\n")
    finite = ratios["log2_ratio"].dropna().to_numpy()
    limit = math.ceil(float(np.max(np.abs(finite))) * 10) / 10
    cmap = LinearSegmentedColormap.from_list("physical_ratio", ["#2166AC", "#F7F7F7", "#B2182B"])
    cmap.set_bad("#E3E3E3")
    norm = TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit)
    apply_style()
    fig, axes = plt.subplots(2, 2, figsize=(WIDTH_IN, 148 / 25.4), constrained_layout=True)
    images = []
    for ax, dataset_name, title, label in zip(
        (axes[0, 0], axes[0, 1], axes[1, 0]),
        ("pu", "cwru", "berkeley"),
        ("PU", "CWRU", "Berkeley"),
        ("a", "b", "c"),
    ):
        frame = ratios[ratios["dataset"].eq(dataset_name)]
        row_labels, metric_labels, matrix = _matrix_rows(frame)
        image = ax.imshow(np.ma.masked_invalid(matrix), cmap=cmap, norm=norm, aspect="auto")
        images.append(image)
        ax.set_xticks(range(len(metric_labels)), metric_labels, rotation=34, ha="right")
        ax.set_yticks(range(len(row_labels)), row_labels)
        ax.set_title(title, fontweight="bold")
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                value = matrix[i, j]
                text = "NA" if np.isnan(value) else f"{value:+.1f}"
                color = DARK if np.isnan(value) or abs(value) < limit * 0.52 else "white"
                ax.text(j, i, text, ha="center", va="center", fontsize=5.0, color=color)
        panel_label(ax, label, x=-0.22)

    ax = axes[1, 1]
    dataset_order = ("pu", "cwru", "berkeley")
    class_order = {"pu": ["healthy", "OR", "IR"], "cwru": ["healthy", "IR", "B", "OR"], "berkeley": ["healthy", "degraded"]}
    row_keys = [(dataset_name, cls) for dataset_name in dataset_order for cls in class_order[dataset_name]]
    y = np.arange(len(row_keys))
    methods = ("real_reference", "llm", "rule", "noise_aug", "random_open_loop")
    offsets = dict(zip(methods, np.linspace(-0.28, 0.28, len(methods))))
    for method in methods:
        xs, ys = [], []
        for index, (dataset_name, cls) in enumerate(row_keys):
            cell = diversity[
                diversity["dataset"].eq(dataset_name)
                & diversity["class"].eq(cls)
                & diversity["method"].eq(method)
            ]
            if cell.empty:
                continue
            xs.append(float(cell.iloc[0]["nn_diversity"]))
            ys.append(index + offsets[method])
        if xs:
            ax.scatter(
                xs,
                ys,
                s=15,
                marker=METHOD_MARKERS[method],
                facecolor=METHOD_COLORS[method],
                edgecolor="white" if method != "real_reference" else DARK,
                linewidth=0.4,
                label="Real ref." if method == "real_reference" else data.METHOD_LABELS[method],
            )
    ax.set_xscale("log")
    ax.set_yticks(y, [f"{dataset_name.upper()}/{data.CLASS_LABELS[cls]}" for dataset_name, cls in row_keys])
    ax.invert_yaxis()
    ax.set_xlabel("Raw NN diversity (log axis)")
    ax.set_title("Within-pool diversity; no universal optimum", fontweight="bold")
    ax.grid(axis="x", color="#E5E5E5", lw=0.5)
    ax.legend(ncol=2, loc="lower right")
    panel_label(ax, "d", x=-0.28)
    colorbar = fig.colorbar(images[0], ax=[axes[0, 0], axes[0, 1], axes[1, 0]], orientation="horizontal", fraction=0.05, pad=0.08)
    colorbar.set_label("log2(method distance / rule distance): <0 closer to real")
    figure_paths = save_preview(fig, out, "fig5_physical_error")
    outputs = [ratios_path, diversity_path, *figure_paths]
    manifest = data.write_source_manifest(
        out,
        sources,
        {
            "matrix": "class-conditional log2(method distance / rule distance); all finite cells retained",
            "NA": "undefined or unavailable frozen metric only; no interpolation",
            "diversity": "raw NN diversity on log x axis; displayed separately from fidelity errors",
        },
        {"ratio_rows": len(ratios), "available_ratio_cells": int(ratios["log2_ratio"].notna().sum()), "diversity_points": len(diversity)},
        outputs,
        notes=["Berkeley TPF-amplitude W1 is not relabelled as bearing fault-frequency alignment."],
    )
    return manifest, outputs


def figure6() -> tuple[Path, list[Path]]:
    cumulative, slots, sources = data.build_fig6_data()
    out = data.PREVIEW / "fig6_admission_mechanism"
    out.mkdir(parents=True, exist_ok=True)
    source_path = out / "source_data.csv"
    cumulative.to_csv(source_path, index=False, lineterminator="\n")

    apply_style()
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(WIDTH_IN, 76 / 25.4),
        gridspec_kw={"width_ratios": [1.55, 1.0]},
        constrained_layout=True,
    )
    class_styles = {
        "healthy": (TEAL, "o", "-", "Healthy"),
        "OR": (ORANGE, "s", (0, (4, 1.6)), "Outer race"),
        "IR": (BLUE, "^", (0, (1.6, 1.2)), "Inner race"),
        "all": (DARK, "D", "-", "All slots"),
    }

    ax = axes[0]
    for class_name in ("healthy", "OR", "IR", "all"):
        color, marker, linestyle, label = class_styles[class_name]
        rows = cumulative[cumulative["class"].eq(class_name)].sort_values(
            "feedback_round_k"
        )
        line_width = 1.7 if class_name == "all" else 1.05
        marker_size = 4.5 if class_name == "all" else 4.0
        ax.plot(
            rows["feedback_round_k"],
            rows["cumulative_rate"] * 100,
            color=color,
            marker=marker,
            markersize=marker_size,
            markerfacecolor="white" if class_name == "all" else color,
            markeredgecolor=color,
            markeredgewidth=0.8,
            linestyle=linestyle,
            linewidth=line_width,
            label=label,
            zorder=3 if class_name == "all" else 2,
        )
    all_rows = cumulative[cumulative["class"].eq("all")].sort_values(
        "feedback_round_k"
    )
    label_offsets = {
        0: (0, -17, "center", "top"),
        1: (-18, -2, "right", "center"),
        2: (0, 8, "center", "bottom"),
        3: (0, 8, "center", "bottom"),
    }
    for row in all_rows.itertuples(index=False):
        offset_x, offset_y, horizontal, vertical = label_offsets[
            int(row.feedback_round_k)
        ]
        ax.annotate(
            f"{int(row.cumulative_admitted)}/{int(row.total_slots)}",
            (row.feedback_round_k, row.cumulative_rate * 100),
            xytext=(offset_x, offset_y),
            textcoords="offset points",
            ha=horizontal,
            va=vertical,
            fontsize=5.2,
            color=DARK,
        )
    ax.set_xticks(range(4), ["$K=0$", "$K=1$", "$K=2$", "$K=3$"])
    ax.set_xlim(-0.12, 3.12)
    ax.set_ylim(32, 76)
    ax.set_ylabel("Cumulative admitted slots (%)")
    ax.set_xlabel("Maximum feedback round")
    ax.set_title("Feedback accumulates feasible proposal slots", fontweight="bold")
    ax.grid(axis="y", color="#E5E5E5", lw=0.55)
    ax.legend(ncol=2, loc="lower right", handlelength=2.4, columnspacing=1.2)
    panel_label(ax, "a", x=-0.15)

    ax = axes[1]
    rounds = np.arange(4)
    bottom = np.zeros(4, dtype=float)
    for class_name in ("healthy", "OR", "IR"):
        color, _, _, label = class_styles[class_name]
        rows = cumulative[cumulative["class"].eq(class_name)].sort_values(
            "feedback_round_k"
        )
        values = rows["newly_admitted"].to_numpy(dtype=float)
        ax.bar(
            rounds,
            values,
            bottom=bottom,
            width=0.62,
            color=color,
            edgecolor="white",
            linewidth=0.65,
            label=label,
        )
        bottom += values
    totals = all_rows["newly_admitted"].to_numpy(dtype=int)
    for x, total in zip(rounds, totals):
        ax.text(x, total + 5, f"+{total}", ha="center", va="bottom", fontsize=5.7, fontweight="bold")
    ax.axhline(0, color=DARK, lw=0.8)
    ax.set_xticks(rounds, ["$K=0$", "$K=1$", "$K=2$", "$K=3$"])
    ax.set_ylim(0, 235)
    ax.set_ylabel("Newly admitted slots")
    ax.set_xlabel("First passing round")
    ax.set_title("Most admissions occur before feedback", fontweight="bold")
    ax.grid(axis="y", color="#E5E5E5", lw=0.55, zorder=-1)
    final_admitted = int(slots["final_admitted"].sum())
    total_slots = len(slots)
    ax.text(
        0.98,
        0.94,
        f"{total_slots - final_admitted}/{total_slots} remain unadmitted at $K=3$",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=5.6,
        color=GRAY,
    )
    panel_label(ax, "b", x=-0.19)

    figure_paths = save_preview(fig, out, "fig6_admission_mechanism")
    outputs = [source_path, *figure_paths]
    manifest = data.write_source_manifest(
        out,
        sources,
        {
            "unit": "proposal slot",
            "first_pass_round": "minimum archived round with feasible=true",
            "curve": "cumulative first-pass count divided by all class or pooled slots",
            "uncertainty": "none; complete accounting of one frozen 450-slot run",
        },
        {
            "slots": len(slots),
            "final_admitted": int(slots["final_admitted"].sum()),
            "classes": int(slots["class"].nunique()),
            "feedback_rounds": 4,
        },
        outputs,
        notes=[
            "The plotted round is reconstructed from the first feasible candidate, not from archive depth.",
            "Counts do not quantify uncertainty over independent LLM pool generations.",
        ],
    )
    return manifest, outputs


def _cwru_matrix(frame: pd.DataFrame, metric: str) -> np.ndarray:
    matrix = np.empty((3, 3), dtype=float)
    for i, load in enumerate((1, 2, 3)):
        for j, shot in enumerate((5, 10, 25)):
            cell = frame[
                frame["heldout_load"].eq(load)
                & frame["n_real"].eq(shot)
                & frame["metric"].eq(metric)
            ]
            if len(cell) != 1:
                raise RuntimeError(f"CWRU cell {load}/{shot}/{metric}: {len(cell)}")
            matrix[i, j] = float(cell.iloc[0]["effect_pp"])
    return matrix


def _pu_matrix(frame: pd.DataFrame, version: str) -> tuple[np.ndarray, list[str]]:
    subset = frame[frame["version"].eq(version)]
    conditions = sorted(subset["condition"].unique())
    columns = [(shot, metric) for shot in (5, 10, 25) for metric in ("acc", "macro_f1")]
    matrix = np.empty((len(conditions), len(columns)), dtype=int)
    for i, condition in enumerate(conditions):
        for j, (shot, metric) in enumerate(columns):
            cell = subset[
                subset["condition"].eq(condition)
                & subset["n_real"].eq(shot)
                & subset["metric"].eq(metric)
            ]
            if len(cell) != 1:
                raise RuntimeError(f"PU cell {version}/{condition}/{shot}/{metric}: {len(cell)}")
            matrix[i, j] = int(cell.iloc[0]["passed_count"])
    return matrix, conditions


def figure7() -> tuple[Path, list[Path], pd.DataFrame]:
    cwru, pu, chain, sources = data.build_fig7_data()
    out = data.PREVIEW / "fig7_cross_condition"
    out.mkdir(parents=True, exist_ok=True)
    cwru_path = out / "cwru_source_data.csv"
    pu_path = out / "pu_source_data.csv"
    cwru.to_csv(cwru_path, index=False, lineterminator="\n")
    pu.to_csv(pu_path, index=False, lineterminator="\n")
    cwru_limit = _nice_symmetric_limit(cwru["effect_pp"].to_numpy())
    continuous_cmap = LinearSegmentedColormap.from_list("cross_effect", ["#B2182B", "#F7F7F7", "#2166AC"])
    continuous_norm = TwoSlopeNorm(vmin=-cwru_limit, vcenter=0, vmax=cwru_limit)
    discrete_cmap = ListedColormap(["#ECECEC", "#F2D49B", "#93C7BD", "#5E8FC1", "#174A7E"])
    discrete_norm = BoundaryNorm(np.arange(-0.5, 5.5, 1), discrete_cmap.N)
    apply_style()
    fig, axes = plt.subplots(2, 2, figsize=(WIDTH_IN, 124 / 25.4), constrained_layout=True, gridspec_kw={"width_ratios": (0.86, 1.35)})
    continuous_images = []
    discrete_images = []
    for row, (metric, title, label) in enumerate(
        (("acc", "Accuracy", "a"), ("macro_f1", "Macro-F1", "c"))
    ):
        ax = axes[row, 0]
        matrix = _cwru_matrix(cwru, metric)
        image = ax.imshow(matrix, cmap=continuous_cmap, norm=continuous_norm, aspect="auto")
        continuous_images.append(image)
        ax.set_xticks(range(3), ("5", "10", "25"))
        ax.set_yticks(range(3), ("Load 1", "Load 2", "Load 3"))
        ax.set_xlabel("Real windows/class")
        ax.set_title(f"CWRU source load0 -> held-out load: {title}", fontweight="bold")
        for i, load in enumerate((1, 2, 3)):
            for j, shot in enumerate((5, 10, 25)):
                cell = cwru[
                    cwru["heldout_load"].eq(load)
                    & cwru["n_real"].eq(shot)
                    & cwru["metric"].eq(metric)
                ].iloc[0]
                ax.text(j, i, f"{cell['effect_pp']:+.1f}", ha="center", va="center", fontsize=5.4, color=DARK if abs(cell["effect_pp"]) < cwru_limit * 0.52 else "white")
                ax.scatter(j + 0.30, i - 0.30, s=8, facecolor=DARK if bool(cell["passed_holm"]) else "white", edgecolor=DARK, linewidth=0.55)
        panel_label(ax, label, x=-0.31)

    for row, (version, title, label) in enumerate((("v1", "PU LOCO v1", "b"), ("v2", "PU LOCO v2", "d"))):
        ax = axes[row, 1]
        matrix, conditions = _pu_matrix(pu, version)
        image = ax.imshow(matrix, cmap=discrete_cmap, norm=discrete_norm, aspect="auto")
        discrete_images.append(image)
        ax.set_xticks(range(6), ("5 Acc", "5 F1", "10 Acc", "10 F1", "25 Acc", "25 F1"), rotation=28, ha="right")
        ax.set_yticks(range(len(conditions)), [condition.replace("_", " ") for condition in conditions])
        ax.set_title(f"{title}: positive Holm passes", fontweight="bold")
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                ax.text(j, i, f"{matrix[i, j]}/4", ha="center", va="center", fontsize=5.2, color="white" if matrix[i, j] >= 3 else DARK)
        panel_label(ax, label, x=-0.22)
    cbar1 = fig.colorbar(continuous_images[0], ax=[axes[0, 0], axes[1, 0]], orientation="horizontal", fraction=0.06, pad=0.08)
    cbar1.set_label("LLM - rule effect (percentage points)")
    cbar2 = fig.colorbar(discrete_images[0], ax=[axes[0, 1], axes[1, 1]], orientation="horizontal", fraction=0.06, pad=0.08, ticks=range(5))
    cbar2.ax.set_xticklabels([f"{value}/4" for value in range(5)])
    cbar2.set_label("Registered comparisons passing Holm with positive effect")
    fig.text(0.02, 0.005, "CWRU: filled dot = Holm pass; hollow dot = NS.", ha="left", va="bottom", fontsize=5.4, color=GRAY)
    figure_paths = save_preview(fig, out, "fig7_cross_condition")
    outputs = [cwru_path, pu_path, *figure_paths]
    manifest = data.write_source_manifest(
        out,
        sources[:3],
        {
            "CWRU": "LLM-rule, source pool load0, held-out loads 1-3; lolo_load0 excluded",
            "PU": "v1/v2 count of positive Holm-passing registered comparisons out of four",
        },
        {"cwru_cells": len(cwru), "pu_cells": len(pu)},
        outputs,
        notes=["The CWRU protocol is not presented as a strict four-fold LOLO study."],
    )
    return manifest, outputs, chain


def supplementary_s3(chain: pd.DataFrame) -> tuple[Path, list[Path]]:
    _, _, _, sources = data.build_fig7_data()
    out = data.PREVIEW / "figS3_pu_failure_chain"
    out.mkdir(parents=True, exist_ok=True)
    source_path = out / "source_data.csv"
    chain.to_csv(source_path, index=False, lineterminator="\n")
    apply_style()
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 60 / 25.4), constrained_layout=True)
    x = np.arange(len(chain))
    ax.plot(x, np.zeros_like(x), color="#BEBEBE", lw=1.0, zorder=0)
    for index, row in chain.iterrows():
        formal = bool(row["formal"])
        color = BLUE if formal else ROSE
        face = color if formal else "white"
        ax.scatter(index, 0, s=55, facecolor=face, edgecolor=color, linewidth=1.1, zorder=2)
        ax.text(index, 0.26, row["stage"], ha="center", va="bottom", fontsize=7.0, fontweight="bold", color=color)
        ax.text(index, 0.12, row["scope"], ha="center", va="bottom", fontsize=5.1, color=GRAY)
        ax.text(index, -0.17, row["outcome"], ha="center", va="top", fontsize=5.3, color=DARK, wrap=True)
        ax.text(index, -0.48, "FORMAL" if formal else "STOP: NO HELD-OUT TEST", ha="center", va="top", fontsize=4.9, fontweight="bold", color=color)
    ax.set_xlim(-0.45, len(chain) - 0.55)
    ax.set_ylim(-0.72, 0.55)
    ax.axis("off")
    ax.set_title("PU leave-one-condition-out: complete v1-v6 evidence-stop chain", loc="left", fontweight="bold")
    panel_label(ax, "a", x=-0.02, y=0.93)
    figure_paths = save_preview(fig, out, "figS3_pu_failure_chain")
    outputs = [source_path, *figure_paths]
    manifest = data.write_source_manifest(
        out,
        sources,
        {"stages": "v1-v2 formal held-out; v3-v6 development/admission/source-evidence stops"},
        {"stages": len(chain)},
        outputs,
        notes=["Development stops are not converted into held-out downstream scores."],
    )
    return manifest, outputs


def main() -> None:
    data.PREVIEW.mkdir(parents=True, exist_ok=True)
    manifests = []
    manifests.append(str(figure3()[0]))
    manifests.append(str(figure4()[0]))
    manifests.append(str(supplementary_s1()[0]))
    manifests.append(str(supplementary_s2()[0]))
    manifests.append(str(figure5()[0]))
    manifests.append(str(figure6()[0]))
    fig7_manifest, _, chain = figure7()
    manifests.append(str(fig7_manifest))
    manifests.append(str(supplementary_s3(chain)[0]))
    index = data.PREVIEW / "preview-manifests.json"
    index.write_text(
        json.dumps(
            {"manifests": [data._relative(Path(path)) for path in manifests]},
            indent=2,
        )
        + "\n"
    )
    print(index)


if __name__ == "__main__":
    main()
