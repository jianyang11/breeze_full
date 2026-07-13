"""Audit the preregistered S4 extrapolation verifier on train-only PU windows.

The script has one checkpoint JSON per internal target.  Calibration uses only
the other three conditions' train-bearing windows; a target condition's
waveforms are never loaded.  Raw arrays and calibration checkpoints stay in
``breeze/runs`` while this script writes only aggregate certificates to the
requested results directory.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "breeze" / "src"))
sys.path.insert(0, str(ROOT / "breeze" / "scripts"))

from build_pu_loco_v3_internal_candidates import load_train_condition  # noqa: E402
from config import CLASSES, CONDITIONS, WIN  # noqa: E402
from verifier.v2 import BreezeVerifierV2  # noqa: E402


DEFAULT_RUN_ROOT = "breeze/runs/pu_loco_v5_s4_extrapolation_verifier_2026-07-13"
DEFAULT_RESULT_DIR = "breeze/results/pu_loco_v5_s4_extrapolation_verifier_2026-07-13"


def tolist(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): tolist(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [tolist(v) for v in value]
    return value


def source_data(target: str) -> tuple[list[str], dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]]:
    sources = [condition for condition in CONDITIONS if condition != target]
    return sources, {condition: load_train_condition(condition) for condition in sources}


def calibrate_target(target: str, run_root: Path) -> BreezeVerifierV2:
    target_root = run_root / f"internal_loco_{target}"
    target_root.mkdir(parents=True, exist_ok=True)
    path = target_root / "verifier_extrapolation_c90_soft_w1.json"
    if path.exists():
        verifier = BreezeVerifierV2.load(path)
        if verifier.regime != "extrapolation" or verifier.calib.get("target_condition") != target:
            raise RuntimeError(f"checkpoint {path} is not the expected S4 extrapolation verifier")
        return verifier
    sources, loaded = source_data(target)
    X = np.concatenate([loaded[condition][0] for condition in sources])
    y = np.concatenate([loaded[condition][1] for condition in sources])
    bearings = np.concatenate([loaded[condition][2] for condition in sources])
    condition_labels = np.concatenate([np.full(len(loaded[condition][0]), condition) for condition in sources])
    verifier = BreezeVerifierV2(coverage=0.90, profile="soft_w1", regime="extrapolation")
    verifier.calibrate(
        X,
        y,
        sources[0],
        bearings=bearings,
        source_conditions=sources,
        target_condition=target,
        condition_labels=condition_labels,
    )
    verifier.save(path)
    return verifier


def failure_messages(report: dict[str, Any]) -> list[str]:
    messages: list[str] = []
    for name, gate in report.get("gates", {}).items():
        if not gate.get("passed", True):
            messages.extend(f"{name}: {message}" for message in gate.get("messages", []))
    return messages


def _sample_indices(rng: np.random.Generator, count: int, n: int) -> np.ndarray:
    if count < n:
        raise RuntimeError(f"required {n} deterministic samples, found only {count}")
    return rng.choice(count, n, replace=False)


def _audit_healthy(
    verifier: BreezeVerifierV2,
    target: str,
    sources: list[str],
    loaded: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],
    n_per_condition: int,
    seed: int,
) -> tuple[list[dict[str, Any]], Counter[str]]:
    rng = np.random.default_rng(seed)
    healthy_index = CLASSES.index("healthy")
    failures: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []
    for source in sources:
        X, y, _ = loaded[source]
        windows = X[y == healthy_index]
        chosen = _sample_indices(rng, len(windows), n_per_condition)
        std = float(np.std(windows[:, 0, :]))
        raw_pass = 0
        noise_pass = 0
        for index in chosen:
            raw = windows[int(index)]
            raw_report = verifier.verify(raw, "healthy")
            raw_pass += int(raw_report["feasible"])
            if not raw_report["feasible"]:
                failures.update(failure_messages(raw_report))
            perturbed = raw.copy()
            perturbed[0] = perturbed[0] * rng.normal(1.0, 0.04) + rng.normal(0.0, 0.03 * std, size=perturbed[0].shape)
            noise_report = verifier.verify(perturbed, "healthy")
            noise_pass += int(noise_report["feasible"])
            if not noise_report["feasible"]:
                failures.update(failure_messages(noise_report))
        rows.append({
            "target_condition": target,
            "source_condition": source,
            "class": "healthy",
            "n": n_per_condition,
            "raw_pass": raw_pass,
            "noise_aug_scale_jitter_pass": noise_pass,
        })
    return rows, failures


def _audit_fault_transfer(
    verifier: BreezeVerifierV2,
    target: str,
    sources: list[str],
    loaded: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],
    n_per_condition: int,
    seed: int,
) -> tuple[list[dict[str, Any]], Counter[str]]:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    failures: Counter[str] = Counter()
    for source in sources:
        X, y, _ = loaded[source]
        for cls in ("OR", "IR"):
            windows = X[y == CLASSES.index(cls)]
            chosen = _sample_indices(rng, len(windows), n_per_condition)
            transfer_pass = 0
            literal_target_pass = 0
            for index in chosen:
                window = windows[int(index)]
                transfer = verifier.verify(window, cls, observed_condition=source)
                literal = verifier.verify(window, cls)
                transfer_pass += int(transfer["feasible"])
                literal_target_pass += int(literal["feasible"])
                if not transfer["feasible"]:
                    failures.update(failure_messages(transfer))
            rows.append({
                "target_condition": target,
                "source_condition": source,
                "class": cls,
                "n": n_per_condition,
                "morphology_transfer_source_kinematics_pass": transfer_pass,
                "literal_target_kinematics_pass": literal_target_pass,
            })
    return rows, failures


def _negative_controls(
    verifier: BreezeVerifierV2,
    target: str,
    sources: list[str],
    loaded: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],
    n: int,
    seed: int,
) -> tuple[list[dict[str, Any]], Counter[str]]:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    failure_reasons: Counter[str] = Counter()
    wrong_pairs = (("OR", "IR"), ("IR", "OR"))
    for actual, asserted in wrong_pairs:
        passes = 0
        candidates: list[tuple[str, int]] = []
        for source in sources:
            X, y, _ = loaded[source]
            windows = X[y == CLASSES.index(actual)]
            candidates.extend((source, int(index)) for index in range(len(windows)))
        chosen = _sample_indices(rng, len(candidates), n)
        for candidate_index in chosen:
            source, index = candidates[int(candidate_index)]
            X, y, _ = loaded[source]
            windows = X[y == CLASSES.index(actual)]
            report = verifier.verify(windows[index], asserted, observed_condition=source)
            passes += int(report["feasible"])
            if not report["feasible"]:
                failure_reasons.update(failure_messages(report))
        rows.append({
            "target_condition": target,
            "control": f"real_{actual}_labeled_{asserted}",
            "n": n,
            "admitted": passes,
        })
    for control in ("white_noise", "constant"):
        for cls in CLASSES:
            passes = 0
            for _ in range(n):
                window = (
                    rng.normal(0.0, 1.0, size=(3, WIN)).astype(np.float32)
                    if control == "white_noise"
                    else np.zeros((3, WIN), dtype=np.float32)
                )
                report = verifier.verify(window, cls)
                passes += int(report["feasible"])
                if not report["feasible"]:
                    failure_reasons.update(failure_messages(report))
            rows.append({"target_condition": target, "control": f"{control}_labeled_{cls}", "n": n, "admitted": passes})
    return rows, failure_reasons


def audit_target(args: argparse.Namespace, target: str) -> dict[str, Any]:
    checkpoint = Path(args.out_dir) / f"s4_target_{target}.json"
    if checkpoint.exists() and not args.force:
        return json.loads(checkpoint.read_text())
    sources, loaded = source_data(target)
    verifier = calibrate_target(target, Path(args.run_root))
    healthy_rows, healthy_failures = _audit_healthy(verifier, target, sources, loaded, args.n_per_condition, args.seed)
    fault_rows, fault_failures = _audit_fault_transfer(verifier, target, sources, loaded, args.n_per_condition, args.seed + 1)
    negative_rows, negative_failures = _negative_controls(verifier, target, sources, loaded, args.n_per_condition, args.seed + 2)
    healthy_rate = sum(row["raw_pass"] for row in healthy_rows) / sum(row["n"] for row in healthy_rows)
    source_rates = {row["source_condition"]: row["raw_pass"] / row["n"] for row in healthy_rows}
    negative_pass = sum(row["admitted"] for row in negative_rows)
    result = {
        "target_condition": target,
        "boundary": "only the three non-target conditions' config.SPLIT train-bearing windows are loaded; target and formal held-out windows are unread",
        "regime": "extrapolation",
        "source_conditions": sources,
        "n_per_source_condition": args.n_per_condition,
        "healthy_carrier_rows": healthy_rows,
        "fault_transfer_rows": fault_rows,
        "negative_control_rows": negative_rows,
        "criteria": {
            "healthy_pooled_raw_rate_min": 0.60,
            "healthy_source_raw_rate_min": 0.40,
            "negative_admitted_required": 0,
        },
        "decision": {
            "healthy_pooled_raw_rate": healthy_rate,
            "healthy_source_raw_rates": source_rates,
            "negative_admitted": negative_pass,
            "sanity_pass": bool(healthy_rate >= 0.60 and min(source_rates.values()) >= 0.40 and negative_pass == 0),
        },
        "top_healthy_failures": dict(healthy_failures.most_common(20)),
        "top_fault_transfer_failures": dict(fault_failures.most_common(20)),
        "top_negative_rejections": dict(negative_failures.most_common(20)),
    }
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.write_text(json.dumps(tolist(result), indent=2) + "\n")
    return result


def write_report(out_dir: Path, targets: list[dict[str, Any]]) -> None:
    overall = {
        "boundary": "all audits are train-bearing-only; no pseudo-held-out or formal held-out waveform is read",
        "regime": "extrapolation",
        "n_targets": len(targets),
        "targets": targets,
        "overall_sanity_pass": all(target["decision"]["sanity_pass"] for target in targets),
    }
    (out_dir / "s4_sanity_summary.json").write_text(json.dumps(tolist(overall), indent=2) + "\n")
    lines = ["# PU LOCO v5 S4 extrapolation sanity audit", "", "## Boundary", "", overall["boundary"], ""]
    lines.extend(["## Decision", "", f"- Overall sanity status: **{'PASS' if overall['overall_sanity_pass'] else 'FAIL'}**.", "- Predeclared healthy criterion: pooled raw rate >= 0.60 and every source raw rate >= 0.40.", "- Predeclared negative-control criterion: 0 admitted wrong-label, white-noise, and constant windows.", ""])
    lines.extend(["## Healthy carrier admission", "", "| target | pooled raw rate | source raw rates | target sanity |", "|---|---:|---|---|"])
    for target in targets:
        decision = target["decision"]
        rates = ", ".join(f"{condition}={rate:.3f}" for condition, rate in decision["healthy_source_raw_rates"].items())
        lines.append(f"| {target['target_condition']} | {decision['healthy_pooled_raw_rate']:.3f} | {rates} | {'PASS' if decision['sanity_pass'] else 'FAIL'} |")
    lines.extend(["", "## Negative controls", "", "| target | control | admitted / n |", "|---|---|---:|"])
    for target in targets:
        for row in target["negative_control_rows"]:
            lines.append(f"| {target['target_condition']} | {row['control']} | {row['admitted']} / {row['n']} |")
    lines.extend(["", "## Fault transfer audit", "", "The source-kinematics column measures morphology-boundary transfer. The literal-target column is a strict kinematic mismatch control, not a success metric.", "", "| target | source | class | transfer pass / n | literal-target pass / n |", "|---|---|---|---:|---:|"])
    for target in targets:
        for row in target["fault_transfer_rows"]:
            lines.append(f"| {target['target_condition']} | {row['source_condition']} | {row['class']} | {row['morphology_transfer_source_kinematics_pass']} / {row['n']} | {row['literal_target_kinematics_pass']} / {row['n']} |")
    (out_dir / "s4_sanity_report.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", nargs="+", default=list(CONDITIONS), choices=CONDITIONS)
    parser.add_argument("--n-per-condition", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260713)
    parser.add_argument("--run-root", default=DEFAULT_RUN_ROOT)
    parser.add_argument("--out-dir", default=DEFAULT_RESULT_DIR)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.n_per_condition != 100:
        raise SystemExit("S4 design freezes --n-per-condition at 100")
    args.run_root = str(ROOT / args.run_root) if not Path(args.run_root).is_absolute() else args.run_root
    args.out_dir = str(ROOT / args.out_dir) if not Path(args.out_dir).is_absolute() else args.out_dir
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    targets = [audit_target(args, target) for target in args.targets]
    write_report(out_dir, targets)
    print(json.dumps({"targets": args.targets, "overall_sanity_pass": all(target["decision"]["sanity_pass"] for target in targets)}, sort_keys=True))


if __name__ == "__main__":
    main()
