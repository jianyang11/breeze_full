"""Summarize complete, train-bearing-only PU internal LOCO downstream runs."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np


CONDITIONS = ("N09_M07_F10", "N15_M01_F10", "N15_M07_F04", "N15_M07_F10")
METRICS = ("acc", "macro_f1")


def read_rows(results_dir: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(results_dir.glob("*.csv")):
        with path.open(newline="") as fh:
            reader = csv.DictReader(fh)
            required = {"split", "baseline", "normalization", "n_real", "seed", *METRICS}
            if reader.fieldnames is None or not required.issubset(reader.fieldnames):
                raise RuntimeError(f"{path} does not use the normalization-aware downstream schema")
            rows.extend(reader)
    if not rows:
        raise FileNotFoundError(f"no result CSV files in {results_dir}")
    return rows


def internal_condition(split: str) -> str:
    prefix = "internal_loco_"
    if not split.startswith(prefix):
        raise ValueError(f"not an internal LOCO split: {split}")
    condition = split[len(prefix) :]
    if condition not in CONDITIONS:
        raise ValueError(f"unknown internal pseudo-held-out condition: {condition}")
    return condition


def collect(
    rows: list[dict[str, str]],
    methods: tuple[str, ...],
    normalizations: tuple[str, ...],
    n_real_values: tuple[int, ...],
    seeds: int,
) -> dict[tuple[str, str, str, int], np.ndarray]:
    by_key: dict[tuple[str, str, str, int], dict[int, dict[str, float]]] = defaultdict(dict)
    for row in rows:
        condition = internal_condition(row["split"])
        method = row["baseline"]
        normalization = row["normalization"]
        n_real = int(row["n_real"])
        seed = int(row["seed"])
        if method not in methods or normalization not in normalizations or n_real not in n_real_values:
            continue
        key = (condition, method, normalization, n_real)
        if seed in by_key[key]:
            raise RuntimeError(f"duplicate result row for {key}, seed={seed}")
        by_key[key][seed] = {metric: float(row[metric]) for metric in METRICS}

    complete: dict[tuple[str, str, str, int], np.ndarray] = {}
    expected_seeds = set(range(seeds))
    for condition in CONDITIONS:
        for method in methods:
            for normalization in normalizations:
                for n_real in n_real_values:
                    key = (condition, method, normalization, n_real)
                    observed = set(by_key.get(key, {}))
                    if observed != expected_seeds:
                        raise RuntimeError(
                            f"incomplete {key}: expected seeds {sorted(expected_seeds)}, got {sorted(observed)}"
                        )
                    complete[key] = np.asarray(
                        [[by_key[key][seed][metric] for metric in METRICS] for seed in range(seeds)], dtype=float
                    )
    return complete


def mean_sd(values: np.ndarray, metric_index: int) -> tuple[float, float]:
    column = values[:, metric_index]
    return float(column.mean()), float(column.std(ddof=1)) if len(column) > 1 else 0.0


def write_csv(path: Path, values: dict[tuple[str, str, str, int], np.ndarray]) -> None:
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["pseudo_heldout", "baseline", "normalization", "n_real", "seeds", "acc_mean", "acc_sd", "macro_f1_mean", "macro_f1_sd"])
        for key in sorted(values):
            condition, method, normalization, n_real = key
            acc_mean, acc_sd = mean_sd(values[key], 0)
            f1_mean, f1_sd = mean_sd(values[key], 1)
            writer.writerow([condition, method, normalization, n_real, len(values[key]), f"{acc_mean:.6f}", f"{acc_sd:.6f}", f"{f1_mean:.6f}", f"{f1_sd:.6f}"])


def formatted_mean_sd(values: np.ndarray, metric_index: int) -> str:
    mean, sd = mean_sd(values, metric_index)
    return f"{mean:.4f} ± {sd:.4f}"


def write_report(
    path: Path,
    values: dict[tuple[str, str, str, int], np.ndarray],
    methods: tuple[str, ...],
    n_real_values: tuple[int, ...],
    seeds: int,
) -> None:
    lines = [
        "# PU LOCO internal S3 normalization summary",
        "",
        "- Scope: train-bearing-only internal pseudo-LOCO; no registered held-out PU windows are used.",
        "- Comparison: the same downstream protocol is run with `none` and `per-window-rms` representations for each baseline.",
        f"- Completeness: {len(CONDITIONS)} folds × {len(methods)} baselines × {len(n_real_values)} shot counts × 2 representations × {seeds} seeds.",
        "- Delta is `per-window-rms − none`; it is descriptive internal-development evidence, not a formal-test result.",
        "",
        "| pseudo heldout | baseline | n_real | none Acc | RMS Acc | Δ Acc | none Macro-F1 | RMS Macro-F1 | Δ Macro-F1 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        for method in methods:
            for n_real in n_real_values:
                none_values = values[(condition, method, "none", n_real)]
                rms_values = values[(condition, method, "per-window-rms", n_real)]
                none_acc, _ = mean_sd(none_values, 0)
                rms_acc, _ = mean_sd(rms_values, 0)
                none_f1, _ = mean_sd(none_values, 1)
                rms_f1, _ = mean_sd(rms_values, 1)
                lines.append(
                    f"| {condition} | {method} | {n_real} | {formatted_mean_sd(none_values, 0)} | "
                    f"{formatted_mean_sd(rms_values, 0)} | {rms_acc - none_acc:+.4f} | "
                    f"{formatted_mean_sd(none_values, 1)} | {formatted_mean_sd(rms_values, 1)} | {rms_f1 - none_f1:+.4f} |"
                )

    lines.extend(
        [
            "",
            "## Four-fold descriptive means",
            "",
            "| baseline | n_real | none Acc | RMS Acc | Δ Acc | none Macro-F1 | RMS Macro-F1 | Δ Macro-F1 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for method in methods:
        for n_real in n_real_values:
            none_fold_means = np.asarray([values[(condition, method, "none", n_real)].mean(axis=0) for condition in CONDITIONS])
            rms_fold_means = np.asarray([values[(condition, method, "per-window-rms", n_real)].mean(axis=0) for condition in CONDITIONS])
            lines.append(
                f"| {method} | {n_real} | {none_fold_means[:, 0].mean():.4f} | {rms_fold_means[:, 0].mean():.4f} | "
                f"{rms_fold_means[:, 0].mean() - none_fold_means[:, 0].mean():+.4f} | "
                f"{none_fold_means[:, 1].mean():.4f} | {rms_fold_means[:, 1].mean():.4f} | "
                f"{rms_fold_means[:, 1].mean() - none_fold_means[:, 1].mean():+.4f} |"
            )
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--out-csv", required=True)
    parser.add_argument("--out-report", required=True)
    parser.add_argument("--methods", nargs="+", default=["real_only", "noise_aug"])
    parser.add_argument("--n-real", type=int, nargs="+", default=[5, 10, 25])
    parser.add_argument("--seeds", type=int, required=True)
    args = parser.parse_args()

    methods = tuple(args.methods)
    n_real_values = tuple(args.n_real)
    rows = read_rows(Path(args.results_dir))
    values = collect(rows, methods, ("none", "per-window-rms"), n_real_values, args.seeds)
    out_csv = Path(args.out_csv)
    out_report = Path(args.out_report)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_report.parent.mkdir(parents=True, exist_ok=True)
    write_csv(out_csv, values)
    write_report(out_report, values, methods, n_real_values, args.seeds)


if __name__ == "__main__":
    main()
