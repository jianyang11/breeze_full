"""Recalculate one global BH sensitivity family from frozen core hypotheses.

No model is fitted and no experiment output is modified. The audit family is
the union of the manuscript's core PU, provenance-valid CWRU, and Berkeley
paired hypotheses. Registered decisions remain the original within-family
Holm decisions.
"""

from __future__ import annotations

import csv
import hashlib
import os
import tempfile
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PU = ROOT / "breeze" / "results" / "phaseA_v2_frozen_2026-07-06" / "breeze" / "results" / "phaseA_v2_wilcoxon.csv"
CWRU = ROOT / "breeze" / "results" / "cwru_patch_v2_2026-07-07_frozen" / "cwru_patch_v2_wilcoxon.csv"
BERKELEY = ROOT / "breeze" / "results" / "milling_berkeley_v2_binary_formal_2026-07-08" / "berkeley_v2_binary_formal_wilcoxon_holm.csv"
OUT = ROOT / "breeze" / "results" / "global_bh_sensitivity_2026-07-16"


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def bh_adjust(p_values: list[float]) -> list[float]:
    """Benjamini--Hochberg adjusted p values with monotonicity enforcement."""
    m = len(p_values)
    if not m:
        raise ValueError("BH family cannot be empty")
    if any(not 0.0 <= value <= 1.0 for value in p_values):
        raise ValueError("p values must lie in [0, 1]")
    order = sorted(range(m), key=p_values.__getitem__)
    sorted_q = [0.0] * m
    running = 1.0
    for rank_index in range(m - 1, -1, -1):
        original_index = order[rank_index]
        rank = rank_index + 1
        running = min(running, p_values[original_index] * m / rank)
        sorted_q[rank_index] = min(running, 1.0)
    adjusted = [0.0] * m
    for rank_index, original_index in enumerate(order):
        adjusted[original_index] = sorted_q[rank_index]
    return adjusted


def core_rows() -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []

    pu_rows = [
        row
        for row in read_rows(PU)
        if row["test_type"] == "pre_registered_superiority"
        and int(row["n_real"]) in {5, 10, 25}
    ]
    if len(pu_rows) != 12:
        raise ValueError(f"expected 12 core PU hypotheses, found {len(pu_rows)}")
    for row in pu_rows:
        selected.append(
            {
                "dataset": "PU",
                "protocol": "phaseA_v2",
                "split": "main_condition",
                "n_real": int(row["n_real"]),
                "metric": row["metric"],
                "comparison": row["comparison"],
                "n_pairs": int(row["n_pairs"]),
                "raw_p": float(row["p_value"]),
                "holm_q_registered_family": float(row["holm_q_in_family"]),
                "holm_pass": float(row["holm_q_in_family"]) < 0.05,
            }
        )

    valid_cwru_splits = {"within_load0", "lolo_load1", "lolo_load2", "lolo_load3"}
    cwru_rows = [row for row in read_rows(CWRU) if row["split"] in valid_cwru_splits]
    if len(cwru_rows) != 72:
        raise ValueError(f"expected 72 provenance-valid CWRU hypotheses, found {len(cwru_rows)}")
    for row in cwru_rows:
        selected.append(
            {
                "dataset": "CWRU",
                "protocol": "within_plus_load0_to_1_2_3",
                "split": row["split"],
                "n_real": int(row["n_real"]),
                "metric": row["metric"],
                "comparison": row["comparison"],
                "n_pairs": int(row["n_pairs"]),
                "raw_p": float(row["p_value"]),
                "holm_q_registered_family": float(row["holm_q_in_family"]),
                "holm_pass": row["passed_holm"] == "True",
            }
        )

    berkeley_rows = read_rows(BERKELEY)
    if len(berkeley_rows) != 18:
        raise ValueError(f"expected 18 Berkeley hypotheses, found {len(berkeley_rows)}")
    for row in berkeley_rows:
        selected.append(
            {
                "dataset": "Berkeley",
                "protocol": "binary_formal",
                "split": "case_run_grouped",
                "n_real": int(row["n_real"]),
                "metric": row["metric"],
                "comparison": row["comparison"],
                "n_pairs": int(row["n_pairs"]),
                "raw_p": float(row["p_raw"]),
                "holm_q_registered_family": float(row["holm_q"]),
                "holm_pass": row["pass"] == "True",
            }
        )

    if len(selected) != 102:
        raise ValueError(f"global core family must contain 102 hypotheses, found {len(selected)}")
    keys = {
        (row["dataset"], row["split"], row["n_real"], row["metric"], row["comparison"])
        for row in selected
    }
    if len(keys) != len(selected):
        raise ValueError("duplicate hypothesis keys in global BH family")
    return selected


def main() -> None:
    rows = core_rows()
    adjusted = bh_adjust([float(row["raw_p"]) for row in rows])
    for row, value in zip(rows, adjusted):
        row["global_bh_q"] = value
        row["global_bh_pass"] = value < 0.05
        row["decision_agrees"] = bool(row["holm_pass"]) == bool(row["global_bh_pass"])

    fieldnames = [
        "dataset", "protocol", "split", "n_real", "metric", "comparison",
        "n_pairs", "raw_p", "holm_q_registered_family", "holm_pass",
        "global_bh_q", "global_bh_pass", "decision_agrees",
    ]
    stream = StringIO()
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_text(OUT / "global_bh_sensitivity.csv", stream.getvalue())

    counts = []
    for dataset, expected in (("PU", 12), ("CWRU", 72), ("Berkeley", 18)):
        subset = [row for row in rows if row["dataset"] == dataset]
        if len(subset) != expected:
            raise ValueError(f"{dataset}: expected {expected} rows")
        counts.append(
            (
                dataset,
                len(subset),
                sum(bool(row["holm_pass"]) for row in subset),
                sum(bool(row["global_bh_pass"]) for row in subset),
                sum(bool(row["decision_agrees"]) for row in subset),
            )
        )
    if sum(row[2] for row in counts) != 99 or sum(row[3] for row in counts) != 99:
        raise ValueError("global BH sensitivity no longer matches the frozen 99/102 decision pattern")

    report = [
        "# Global BH sensitivity audit",
        "",
        "This is a zero-training, zero-API recalculation over the 102 core paired hypotheses:",
        "12 PU Phase-A v2 source comparisons at n={5,10,25}, 72 provenance-valid",
        "CWRU comparisons, and all 18 Berkeley binary comparisons. Registered",
        "within-family Holm decisions remain primary.",
        "",
        "| Dataset | hypotheses | Holm pass | global BH pass | agreeing decisions |",
        "|---|---:|---:|---:|---:|",
    ]
    report.extend(
        f"| {dataset} | {total} | {holm} | {bh} | {agree} |"
        for dataset, total, holm, bh, agree in counts
    )
    report.extend(
        [
            f"| **Total** | **102** | **{sum(row[2] for row in counts)}** | "
            f"**{sum(row[3] for row in counts)}** | **{sum(row[4] for row in counts)}** |",
            "",
            "The global BH sensitivity analysis preserves every registered pass/fail",
            "decision. It does not replace the preregistered family-wise Holm analysis.",
            "",
            "Frozen input SHA-256:",
            f"- PU: {sha256(PU)}",
            f"- CWRU: {sha256(CWRU)}",
            f"- Berkeley: {sha256(BERKELEY)}",
            "",
        ]
    )
    atomic_text(OUT / "global_bh_sensitivity_report.md", "\n".join(report))
    print(OUT)


if __name__ == "__main__":
    main()
