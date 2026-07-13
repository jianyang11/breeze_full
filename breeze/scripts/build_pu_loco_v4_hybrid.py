"""Build internal pseudo-LOCO BREEZE-H pools without post-hoc waveform repair.

BREEZE-H keeps an observed healthy vibration carrier from the three source
conditions and injects a target-kinematic fault impulse before admission. The
carrier is sampled only from ``config.SPLIT['train']`` healthy bearings. The
current channels remain deterministic renderer outputs from an accepted LLM
recipe. Every constructed waveform is verified once and rejected waveforms are
discarded rather than modified.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
sys.path.insert(0, str(BREEZE / "src"))
sys.path.insert(0, str(BREEZE / "scripts"))

from build_pu_loco_v3_internal_candidates import (  # noqa: E402
    accepted_recipe,
    class_for_bearing,
    diversity_mask,
    load_train_condition,
    patch_verifier_freqs,
    source_records,
    stable_seed,
    tolist,
)
from config import CLASSES, CONDITIONS, fault_freqs  # noqa: E402
from renderer import _impulse_train, render  # noqa: E402
from verifier.v2 import BreezeVerifierV2  # noqa: E402


def target_recipe(recipe: dict[str, Any], cls: str, heldout: str) -> dict[str, Any]:
    """Project only kinematic fields; preserve LLM-selected injection shape."""
    out = json.loads(json.dumps(recipe))
    freqs = fault_freqs(CONDITIONS[heldout][0] / 60.0)
    rate = 0.0 if cls == "healthy" else float(freqs["BPFO"] if cls == "OR" else freqs["BPFI"])
    out["fr_hz"] = float(freqs["fr"])
    impacts = out.setdefault("impacts", {})
    impacts["rate_hz"] = rate
    if cls == "healthy":
        impacts["amp"] = 0.0
        impacts["modulation"] = {"type": "none", "depth": 0.0}
    currents = out.setdefault("currents", {})
    currents["fault_freq_hz"] = rate
    if cls == "healthy":
        currents["sideband_depth"] = 0.0
    return out


def calibrate_verifier(
    heldout: str,
    fold_dir: Path,
    loaded: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],
    train_conditions: list[str],
) -> BreezeVerifierV2:
    path = fold_dir / f"verifier_hybrid_to_{heldout}_c90_soft_w1.json"
    if path.exists():
        return BreezeVerifierV2.load(path)
    X = np.concatenate([loaded[c][0] for c in train_conditions])
    y = np.concatenate([loaded[c][1] for c in train_conditions])
    bearings = np.concatenate([loaded[c][2] for c in train_conditions])
    verifier = BreezeVerifierV2(coverage=0.90, profile="soft_w1")
    verifier.calibrate(X, y, train_conditions[0], bearings=bearings)
    verifier.calib["candidate"] = "BREEZE-H"
    verifier.calib["source_conditions"] = train_conditions
    verifier.calib["pseudo_heldout_condition"] = heldout
    patch_verifier_freqs(verifier, heldout)
    verifier.save(path)
    return verifier


def healthy_carriers(
    loaded: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]], train_conditions: list[str]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xs: list[np.ndarray] = []
    conds: list[np.ndarray] = []
    bearings: list[np.ndarray] = []
    healthy_index = CLASSES.index("healthy")
    for condition in train_conditions:
        X, y, bearing = loaded[condition]
        mask = y == healthy_index
        xs.append(X[mask])
        conds.append(np.full(int(mask.sum()), condition))
        bearings.append(bearing[mask])
    return np.concatenate(xs), np.concatenate(conds), np.concatenate(bearings)


def hybrid_window(
    carrier: np.ndarray,
    carrier_vibration_std: float,
    recipe: dict[str, Any],
    cls: str,
    seed: int,
) -> tuple[np.ndarray, dict[str, float]]:
    """Construct one waveform before a single verifier admission decision."""
    rng = np.random.default_rng(seed)
    vibration = carrier[0].astype(np.float64, copy=True)
    impacts = recipe.get("impacts", {})
    if cls == "healthy":
        scale = float(rng.normal(1.0, 0.04))
        jitter = rng.normal(0.0, 0.03 * carrier_vibration_std, size=vibration.shape)
        vibration = vibration * scale + jitter
        injection = {"carrier_scale": scale, "impulse_amp": 0.0}
    else:
        carrier_rms = float(np.sqrt(np.mean(vibration * vibration)))
        source_rms = max(float(recipe.get("target_rms", carrier_rms)), 1e-12)
        amplitude_ratio = float(impacts.get("amp", 0.0)) / source_rms
        impulse_amp = amplitude_ratio * carrier_rms
        modulation = impacts.get("modulation", {})
        vibration += _impulse_train(
            rng,
            float(impacts["rate_hz"]),
            impulse_amp,
            float(impacts.get("decay_ms", 2.0)),
            float(impacts.get("resonance_hz", 2000.0)),
            float(impacts.get("jitter_pct", 1.0)),
            float(impacts.get("amp_var_pct", 10.0)),
            str(modulation.get("type", "none")),
            float(modulation.get("depth", 0.0)),
            float(recipe["fr_hz"]),
        )
        injection = {"carrier_scale": 1.0, "impulse_amp": impulse_amp}
    rendered = render(recipe, seed)
    return np.stack([vibration, rendered[1], rendered[2]]).astype(np.float32), injection


def violation_messages(report: dict[str, Any]) -> list[str]:
    messages: list[str] = []
    for gate in report.get("gates", {}).values():
        if not gate.get("passed", True):
            messages.extend(str(message) for message in gate.get("messages", []))
    return messages


def build_fold(args: argparse.Namespace, heldout: str) -> dict[str, Any]:
    train_conditions = [condition for condition in CONDITIONS if condition != heldout]
    loaded = {condition: load_train_condition(condition) for condition in train_conditions}
    fold_dir = ROOT / args.out_root / f"internal_loco_{heldout}" / "hybrid"
    fold_dir.mkdir(parents=True, exist_ok=True)
    verifier = calibrate_verifier(heldout, fold_dir, loaded, train_conditions)
    carriers, carrier_conditions, carrier_bearings = healthy_carriers(loaded, train_conditions)
    carrier_std = float(np.std(carriers[:, 0, :]))
    records = [path for path in source_records(heldout) if json.loads(path.read_text()).get("accepted")]
    recipes: dict[str, list[tuple[Path, dict[str, Any]]]] = {cls: [] for cls in CLASSES}
    for path in records:
        source = json.loads(path.read_text())
        cls = str(source.get("class", ""))
        recipe = accepted_recipe(source)
        if cls in recipes and recipe is not None:
            recipes[cls].append((path, target_recipe(recipe, cls, heldout)))

    accepted_x: list[np.ndarray] = []
    accepted_y: list[int] = []
    manifest: list[dict[str, Any]] = []
    failures: Counter[str] = Counter()
    for cls_index, cls in enumerate(CLASSES):
        if not recipes[cls]:
            raise RuntimeError(f"no accepted LLM recipe template for {heldout}/{cls}")
        n_slots = args.healthy_slots if cls == "healthy" and args.healthy_slots is not None else args.slots_per_class
        for slot in range(n_slots):
            rng = np.random.default_rng(stable_seed(f"pu-loco-v4-hybrid-carrier:{heldout}:{cls}:{slot}"))
            carrier_index = int(rng.integers(0, len(carriers)))
            recipe_path, recipe = recipes[cls][slot % len(recipes[cls])]
            seed = stable_seed(f"pu-loco-v4-hybrid:{heldout}:{cls}:{slot}")
            window, injection = hybrid_window(carriers[carrier_index], carrier_std, recipe, cls, seed)
            report = verifier.verify(window, cls)
            row = {
                "heldout": heldout,
                "class": cls,
                "slot": slot,
                "carrier_condition": str(carrier_conditions[carrier_index]),
                "carrier_bearing": str(carrier_bearings[carrier_index]),
                "carrier_index": carrier_index,
                "recipe_json": str(recipe_path.relative_to(ROOT)),
                "seed": seed,
                "accepted": bool(report.get("feasible")),
                "injection": injection,
                "violations": violation_messages(report),
            }
            if report.get("feasible"):
                npy_path = fold_dir / f"hybrid_{cls}_{slot:04d}.npy"
                np.save(npy_path, window)
                row["path"] = str(npy_path.relative_to(ROOT))
                accepted_x.append(window)
                accepted_y.append(cls_index)
            else:
                row["path"] = ""
                for message in row["violations"]:
                    failures[f"{cls}: {message}"] += 1
            manifest.append(row)

    X_train = np.concatenate([loaded[condition][0] for condition in train_conditions])
    y_train = np.concatenate([loaded[condition][1] for condition in train_conditions])
    X = np.stack(accepted_x).astype(np.float32) if accepted_x else np.zeros((0, 3, 2048), dtype=np.float32)
    y = np.asarray(accepted_y, dtype=np.int64)
    keep = diversity_mask(X, y, X_train, y_train) if len(X) else np.zeros((0,), dtype=bool)
    X_kept, y_kept = X[keep], y[keep]
    accepted_index = 0
    for row in manifest:
        if row["accepted"]:
            row["kept_after_diversity"] = bool(keep[accepted_index])
            accepted_index += 1
        else:
            row["kept_after_diversity"] = False
    np.savez_compressed(fold_dir / "pool.npz", X=X_kept, y=y_kept, class_names=np.asarray(CLASSES))
    with (fold_dir / "manifest.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(manifest[0]) if manifest else [])
        writer.writeheader()
        writer.writerows([{**row, "injection": json.dumps(row["injection"]), "violations": json.dumps(row["violations"])} for row in manifest])
    summary = {
        "heldout": heldout,
        "train_conditions": train_conditions,
        "slots_per_class": args.slots_per_class,
        "healthy_slots": args.healthy_slots,
        "accepted_before_diversity": int(len(X)),
        "kept_counts": {cls: int((y_kept == index).sum()) for index, cls in enumerate(CLASSES)},
        "top_failures": dict(failures.most_common(20)),
    }
    (fold_dir / "summary.json").write_text(json.dumps(tolist(summary), indent=2) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-root", default="breeze/runs/pu_loco_v4_hybrid_2026-07-13")
    parser.add_argument("--result-dir", default="breeze/results/pu_loco_v4_s1_hybrid_2026-07-13")
    parser.add_argument("--heldout", nargs="+", default=list(CONDITIONS))
    parser.add_argument("--slots-per-class", type=int, default=20)
    parser.add_argument("--healthy-slots", type=int)
    args = parser.parse_args()
    if args.slots_per_class <= 0:
        raise SystemExit("--slots-per-class must be positive")
    if args.healthy_slots is not None and args.healthy_slots <= 0:
        raise SystemExit("--healthy-slots must be positive")
    summaries = [build_fold(args, heldout) for heldout in args.heldout]
    result_dir = ROOT / args.result_dir
    result_dir.mkdir(parents=True, exist_ok=True)
    with (result_dir / "hybrid_pool_summary.json").open("w") as fh:
        json.dump(tolist(summaries), fh, indent=2)
        fh.write("\n")
    print(json.dumps(tolist(summaries), sort_keys=True))


if __name__ == "__main__":
    main()
