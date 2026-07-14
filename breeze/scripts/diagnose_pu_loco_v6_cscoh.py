"""Run the frozen train-only PU LOCO v6 CSCoh source-evidence diagnostic.

For every internal pseudo-held-out condition, only the three other operating
conditions' ``config.SPLIT['train']`` bearing windows are loaded.  The target
condition is metadata only.  Derived CSCoh scores are cached under ``runs``;
this script commits only aggregate audit records under its dedicated result
root.
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
from scipy.stats import wilcoxon


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "breeze" / "src"))
sys.path.insert(0, str(ROOT / "breeze" / "scripts"))

from build_pu_loco_v3_internal_candidates import load_train_condition  # noqa: E402
from config import CLASSES, CONDITIONS, FS, WIN, fault_freqs  # noqa: E402
from verifier.csc import DEFAULT_SETTINGS, fault_csc_evidence  # noqa: E402


DEFAULT_RUN_ROOT = "breeze/runs/pu_loco_v6_cscoh_2026-07-14"
DEFAULT_RESULT_DIR = "breeze/results/pu_loco_v6_cscoh_2026-07-14"
SEED = 20260714
NOISE_WINDOWS = 300
NOISE_PER_SOURCE = 100
POOL_SIZE = 20
POOLS_PER_SOURCE = 20
POOL_ALPHA = 0.01


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _seed(*parts: object) -> int:
    text = ":".join(str(part) for part in (SEED, *parts))
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "little")


def _condition_freqs(condition: str) -> dict[str, float]:
    return fault_freqs(CONDITIONS[condition][0] / 60.0)


def _cache_path(run_root: Path, condition: str) -> Path:
    return run_root / "features" / f"{condition}_train_csc_scores.npz"


def _feature_cache(condition: str, run_root: Path, force: bool) -> dict[str, np.ndarray]:
    """Load source train windows and cache only their derived CSCoh evidence."""
    path = _cache_path(run_root, condition)
    expected_settings = json.dumps(DEFAULT_SETTINGS.as_dict(), sort_keys=True)
    if path.exists() and not force:
        with np.load(path, allow_pickle=False) as cached:
            settings = str(cached["settings_json"].item())
            cached_condition = str(cached["condition"].item())
            if settings != expected_settings or cached_condition != condition:
                raise RuntimeError(f"CSCoh cache contract mismatch: {path}")
            return {name: cached[name].copy() for name in cached.files if name not in {"settings_json", "condition"}}

    X, y, _ = load_train_condition(condition)
    freqs = _condition_freqs(condition)
    rows = {
        "labels": y.astype(np.int64),
        "or_target_strength": np.empty(len(X), dtype=float),
        "or_competing_strength": np.empty(len(X), dtype=float),
        "or_margin": np.empty(len(X), dtype=float),
        "ir_target_strength": np.empty(len(X), dtype=float),
        "ir_competing_strength": np.empty(len(X), dtype=float),
        "ir_margin": np.empty(len(X), dtype=float),
    }
    for index, window in enumerate(X):
        for prefix, asserted in (("or", "OR"), ("ir", "IR")):
            evidence = fault_csc_evidence(window[0], FS, freqs, asserted)
            rows[f"{prefix}_target_strength"][index] = evidence["target_strength"]
            rows[f"{prefix}_competing_strength"][index] = evidence["competing_strength"]
            rows[f"{prefix}_margin"][index] = evidence["margin"]
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, settings_json=np.asarray(expected_settings), condition=np.asarray(condition), **rows)
    return rows


def _margins(cache: dict[str, np.ndarray], asserted: str, actual: str) -> np.ndarray:
    key = "or_margin" if asserted == "OR" else "ir_margin"
    return np.asarray(cache[key][cache["labels"] == CLASSES.index(actual)], dtype=float)


def _noise_margins(target: str, asserted: str, sources: list[str]) -> np.ndarray:
    if len(sources) * NOISE_PER_SOURCE != NOISE_WINDOWS:
        raise RuntimeError("the v6 frozen white-noise schedule requires three source conditions")
    result: list[float] = []
    for source in sources:
        rng = np.random.default_rng(_seed("single_noise", target, asserted, source))
        freqs = _condition_freqs(source)
        for _ in range(NOISE_PER_SOURCE):
            vibration = rng.normal(0.0, 1.0, size=WIN)
            result.append(float(fault_csc_evidence(vibration, FS, freqs, asserted)["margin"]))
    return np.asarray(result, dtype=float)


def _pool_decision(margins: np.ndarray) -> dict[str, Any]:
    values = np.asarray(margins, dtype=float)
    if values.shape != (POOL_SIZE,):
        raise ValueError(f"pool must contain exactly {POOL_SIZE} margins")
    if not np.all(np.isfinite(values)):
        raise ValueError("pool margins must be finite")
    nonzero = values[values != 0.0]
    if len(nonzero) != POOL_SIZE:
        return {
            "n_nonzero": int(len(nonzero)),
            "median_margin": float(np.median(values)),
            "p_greater": None,
            "passed": False,
        }
    p_value = float(wilcoxon(values, alternative="greater", zero_method="wilcox", method="exact").pvalue)
    median = float(np.median(values))
    return {
        "n_nonzero": POOL_SIZE,
        "median_margin": median,
        "p_greater": p_value,
        "passed": bool(median > 0.0 and p_value < POOL_ALPHA),
    }


def _pooled_real_decisions(
    cache: dict[str, np.ndarray],
    target: str,
    source: str,
    actual: str,
    asserted: str,
) -> list[dict[str, Any]]:
    values = _margins(cache, asserted, actual)
    if len(values) < POOL_SIZE:
        raise RuntimeError(f"{source}/{actual} contains fewer than {POOL_SIZE} train windows")
    rows = []
    for replicate in range(POOLS_PER_SOURCE):
        rng = np.random.default_rng(_seed("pool", target, source, actual, asserted, replicate))
        chosen = rng.choice(len(values), POOL_SIZE, replace=False)
        row = _pool_decision(values[chosen])
        row.update({
            "source_condition": source,
            "category": "true" if actual == asserted else "wrong_class",
            "actual_class": actual,
            "asserted_class": asserted,
            "replicate": replicate,
        })
        rows.append(row)
    return rows


def _pooled_noise_decisions(target: str, source: str, asserted: str) -> list[dict[str, Any]]:
    rng = np.random.default_rng(_seed("pool_noise", target, source, asserted))
    freqs = _condition_freqs(source)
    rows = []
    for replicate in range(POOLS_PER_SOURCE):
        margins = np.empty(POOL_SIZE, dtype=float)
        for index in range(POOL_SIZE):
            vibration = rng.normal(0.0, 1.0, size=WIN)
            margins[index] = float(fault_csc_evidence(vibration, FS, freqs, asserted)["margin"])
        row = _pool_decision(margins)
        row.update({
            "source_condition": source,
            "category": "white_noise",
            "actual_class": "white_noise",
            "asserted_class": asserted,
            "replicate": replicate,
        })
        rows.append(row)
    return rows


def _class_diagnostic(target: str, sources: list[str], caches: dict[str, dict[str, np.ndarray]], asserted: str) -> dict[str, Any]:
    actual_wrong = "IR" if asserted == "OR" else "OR"
    true_values = np.concatenate([_margins(caches[source], asserted, asserted) for source in sources])
    wrong_values = np.concatenate([_margins(caches[source], asserted, actual_wrong) for source in sources])
    noise_values = _noise_margins(target, asserted, sources)
    summary = {
        "asserted_class": asserted,
        "wrong_actual_class": actual_wrong,
        "single_window": {
            "true_n": int(len(true_values)),
            "wrong_n": int(len(wrong_values)),
            "white_noise_n": int(len(noise_values)),
            "true_q10": float(np.quantile(true_values, 0.10)),
            "wrong_q90": float(np.quantile(wrong_values, 0.90)),
            "white_noise_q90": float(np.quantile(noise_values, 0.90)),
        },
    }
    single = summary["single_window"]
    single["passed"] = bool(single["true_q10"] > single["wrong_q90"] and single["true_q10"] > single["white_noise_q90"])

    pools: list[dict[str, Any]] = []
    for source in sources:
        pools.extend(_pooled_real_decisions(caches[source], target, source, asserted, asserted))
        pools.extend(_pooled_real_decisions(caches[source], target, source, actual_wrong, asserted))
        pools.extend(_pooled_noise_decisions(target, source, asserted))
    true_pools = [row for row in pools if row["category"] == "true"]
    negative_pools = [row for row in pools if row["category"] != "true"]
    summary["pool"] = {
        "pool_size": POOL_SIZE,
        "pools_per_source_category": POOLS_PER_SOURCE,
        "alpha": POOL_ALPHA,
        "true_pool_count": len(true_pools),
        "negative_pool_count": len(negative_pools),
        "true_passed": int(sum(row["passed"] for row in true_pools)),
        "negative_admitted": int(sum(row["passed"] for row in negative_pools)),
        "passed": bool(all(row["passed"] for row in true_pools) and not any(row["passed"] for row in negative_pools)),
        "rows": pools,
    }
    summary["source_evidence_pass"] = bool(single["passed"] or summary["pool"]["passed"])
    return summary


def _target_diagnostic(target: str, run_root: Path, out_dir: Path, force: bool) -> dict[str, Any]:
    checkpoint = out_dir / f"source_separability_{target}.json"
    if checkpoint.exists() and not force:
        return json.loads(checkpoint.read_text())
    sources = [condition for condition in CONDITIONS if condition != target]
    caches = {source: _feature_cache(source, run_root, force) for source in sources}
    classes = {asserted: _class_diagnostic(target, sources, caches, asserted) for asserted in ("OR", "IR")}
    terminal_failure = all(
        not classes[asserted]["single_window"]["passed"] and not classes[asserted]["pool"]["passed"]
        for asserted in ("OR", "IR")
    )
    result = {
        "target_condition": target,
        "boundary": "only config.SPLIT train-bearing windows from the three non-target conditions are loaded; pseudo-held-out and formal held-out windows are unread",
        "source_conditions": sources,
        "estimator": DEFAULT_SETTINGS.as_dict(),
        "seed": SEED,
        "classes": classes,
        "decision": {
            "terminal_cscoh_failure": terminal_failure,
            "next_step_allowed": not terminal_failure,
            "rule": "terminal only when both asserted fault classes fail both frozen single-window and frozen pool criteria",
        },
    }
    checkpoint.write_text(json.dumps(_jsonable(result), indent=2) + "\n")
    return result


def _write_summary(out_dir: Path, targets: list[dict[str, Any]]) -> None:
    flat_rows = []
    for target in targets:
        for asserted, result in target["classes"].items():
            single = result["single_window"]
            pool = result["pool"]
            flat_rows.append({
                "target_condition": target["target_condition"],
                "asserted_class": asserted,
                "true_q10": single["true_q10"],
                "wrong_q90": single["wrong_q90"],
                "white_noise_q90": single["white_noise_q90"],
                "single_window_pass": single["passed"],
                "true_pools_passed": pool["true_passed"],
                "true_pools_total": pool["true_pool_count"],
                "negative_pools_admitted": pool["negative_admitted"],
                "negative_pools_total": pool["negative_pool_count"],
                "pool_pass": pool["passed"],
                "source_evidence_pass": result["source_evidence_pass"],
                "target_terminal_cscoh_failure": target["decision"]["terminal_cscoh_failure"],
            })
    with (out_dir / "source_separability_summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0]))
        writer.writeheader()
        writer.writerows(flat_rows)
    overall = {
        "boundary": "all v6 Step 1 diagnostics are train-bearing-only; pseudo-held-out and formal held-out PU windows are unread",
        "targets": targets,
        "overall_terminal_cscoh_failure": all(target["decision"]["terminal_cscoh_failure"] for target in targets),
        "step_2_allowed_for_any_target": any(target["decision"]["next_step_allowed"] for target in targets),
    }
    (out_dir / "source_separability_summary.json").write_text(json.dumps(_jsonable(overall), indent=2) + "\n")
    lines = [
        "# PU LOCO v6 CSCoh source-only separability diagnostic",
        "",
        "## Boundary",
        "",
        overall["boundary"],
        "",
        "## Frozen decision",
        "",
        "- Window criterion: true-class q10 must exceed wrong-class and white-noise q90.",
        "- Pool criterion: every 20-window true pool must pass the one-sided paired Wilcoxon test (`p < 0.01`, median margin > 0), while every wrong-class and white-noise pool must fail.",
        "- A target terminates v6 CSCoh only when both OR and IR fail both criteria.",
        "",
        "| target | asserted | true q10 | wrong q90 | white q90 | single | true pools | negative admitted | pool | target decision |",
        "|---|---|---:|---:|---:|---|---:|---:|---|---|",
    ]
    for row in flat_rows:
        lines.append(
            f"| {row['target_condition']} | {row['asserted_class']} | {row['true_q10']:.5f} | "
            f"{row['wrong_q90']:.5f} | {row['white_noise_q90']:.5f} | "
            f"{'PASS' if row['single_window_pass'] else 'FAIL'} | "
            f"{row['true_pools_passed']}/{row['true_pools_total']} | "
            f"{row['negative_pools_admitted']}/{row['negative_pools_total']} | "
            f"{'PASS' if row['pool_pass'] else 'FAIL'} | "
            f"{'STOP' if row['target_terminal_cscoh_failure'] else 'CONTINUE'} |"
        )
    lines.extend([
        "",
        "## Overall",
        "",
        f"- Overall terminal CSCoh failure: **{'YES' if overall['overall_terminal_cscoh_failure'] else 'NO'}**.",
        f"- At least one target permits the predeclared next step: **{'YES' if overall['step_2_allowed_for_any_target'] else 'NO'}**.",
    ])
    (out_dir / "source_separability_report.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", nargs="+", choices=CONDITIONS, default=list(CONDITIONS))
    parser.add_argument("--run-root", default=DEFAULT_RUN_ROOT)
    parser.add_argument("--out-dir", default=DEFAULT_RESULT_DIR)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run_root = Path(args.run_root)
    out_dir = Path(args.out_dir)
    if not run_root.is_absolute():
        run_root = ROOT / run_root
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    targets = [_target_diagnostic(target, run_root, out_dir, args.force) for target in args.targets]
    _write_summary(out_dir, targets)
    print(json.dumps({
        "targets": args.targets,
        "overall_terminal_cscoh_failure": all(target["decision"]["terminal_cscoh_failure"] for target in targets),
        "step_2_allowed_for_any_target": any(target["decision"]["next_step_allowed"] for target in targets),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
