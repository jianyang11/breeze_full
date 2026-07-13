"""Build PU LOCO v3 internal-simulation candidate pools.

Option-B development boundary:
- use only train-bearing data inside each operating condition;
- use the pseudo held-out condition only as metadata during generation;
- never read pseudo held-out windows while constructing or calibrating pools.

The candidate source remains the accepted LOCO LLM recipe pool from v1. v3
projects those LLM recipe structures onto a condition-aware morphology model:

1. morphology_idw: inverse-distance interpolation of morphology distributions
   from the three internal training conditions;
2. morphology_nearest: morphology borrowed from the nearest training condition.

Both candidates use held-out-condition bearing kinematics and a train-only v2
verifier whose kinematic target frequencies are extrapolated to the pseudo
held-out rpm.
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

from config import CLASSES, CONDITIONS, PROC_DIR, SPLIT, fault_freqs  # noqa: E402
from recipe_ablation import ClassProfile, build_profiles, diversity_mask, stable_seed, tolist  # noqa: E402
from renderer import BANDS, render  # noqa: E402
from verifier.v2 import BreezeVerifierV2  # noqa: E402


V1_LLM_ROOT = BREEZE / "runs" / "pu_loco_llm_smoke_2026-07-07_v3"
CANDIDATES = ("morphology_idw", "morphology_nearest")


def class_for_bearing(bearing: str) -> str:
    if bearing.startswith("K0"):
        return "healthy"
    if bearing.startswith("KA"):
        return "OR"
    if bearing.startswith("KI"):
        return "IR"
    raise ValueError(f"unknown PU bearing id: {bearing}")


def load_train_condition(cond: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    bearings: list[str] = []
    for path in sorted(PROC_DIR.glob(f"{cond}_*.npz")):
        data = np.load(path, allow_pickle=True)
        bearing = str(data["bearing"])
        cls = class_for_bearing(bearing)
        if bearing not in set(SPLIT["train"][cls]):
            continue
        W = data["windows"].astype(np.float32)
        xs.append(W)
        ys.append(np.full(len(W), CLASSES.index(cls), dtype=np.int64))
        bearings.extend([bearing] * len(W))
    if not xs:
        raise FileNotFoundError(f"no train-bearing windows for {cond}")
    return np.concatenate(xs), np.concatenate(ys), np.asarray(bearings)


def condition_scale() -> np.ndarray:
    meta = np.asarray([CONDITIONS[c] for c in CONDITIONS], dtype=float)
    scale = meta.std(axis=0)
    return np.where(scale > 1e-12, scale, 1.0)


def distances(target: str, train_conditions: list[str]) -> dict[str, float]:
    target_meta = np.asarray(CONDITIONS[target], dtype=float)
    scale = condition_scale()
    return {
        cond: float(np.sqrt((((np.asarray(CONDITIONS[cond], dtype=float) - target_meta) / scale) ** 2).sum()))
        for cond in train_conditions
    }


def idw_weights(target: str, train_conditions: list[str]) -> dict[str, float]:
    d = distances(target, train_conditions)
    raw = {cond: 1.0 / (dist + 1e-6) for cond, dist in d.items()}
    total = sum(raw.values())
    return {cond: val / total for cond, val in raw.items()}


def nearest_condition(target: str, train_conditions: list[str]) -> str:
    d = distances(target, train_conditions)
    return min(train_conditions, key=lambda c: (d[c], c))


def _weighted_float(
    profiles: dict[str, dict[str, ClassProfile]],
    weights: dict[str, float],
    cls: str,
    attr: str,
) -> float:
    return float(sum(weights[c] * float(getattr(profiles[c][cls], attr)) for c in weights))


def _scaled_values(values: list[float], source_median: float, target_median: float) -> list[float]:
    arr = np.asarray(values, dtype=float)
    scale = float(target_median) / max(float(source_median), 1e-12)
    out = np.clip(arr * scale, 1e-12, None)
    return out.astype(float).tolist()


def _subsample(values: list[float], label: str, n: int = 600) -> list[float]:
    if len(values) <= n:
        return values
    rng = np.random.default_rng(stable_seed(f"pu-loco-v3-subsample:{label}"))
    idx = rng.choice(len(values), n, replace=False)
    return [float(values[int(i)]) for i in idx]


def envelope_band_pool(
    profiles: dict[str, dict[str, ClassProfile]],
    train_conditions: list[str],
    cls: str,
    per_condition: int = 200,
) -> list[list[float]]:
    """Return a balanced union of train-condition spectral-shape support.

    The morphology map marks condition-sensitive band features as not
    predictable. A target-condition point estimate for those features would
    be unsupported. Sampling full empirical band vectors from every source
    condition preserves their joint dependencies while deliberately covering
    the three-condition envelope.
    """
    pool: list[list[float]] = []
    for cond in train_conditions:
        rows = profiles[cond][cls].band_pool
        if not rows:
            rows = [profiles[cond][cls].band_median]
        take = min(len(rows), per_condition)
        rng = np.random.default_rng(stable_seed(f"pu-loco-v4-band-envelope:{cond}:{cls}"))
        for index in rng.choice(len(rows), take, replace=False):
            band = np.asarray(rows[int(index)], dtype=float)
            band = np.clip(band, 1e-12, None)
            pool.append((band / band.sum()).astype(float).tolist())
    if not pool:
        raise ValueError(f"empty morphology envelope for {cls}")
    return pool


def interpolate_profile(
    profiles: dict[str, dict[str, ClassProfile]],
    weights: dict[str, float],
    cls: str,
) -> ClassProfile:
    target_rms = _weighted_float(profiles, weights, cls, "rms_q50")
    target_peak = _weighted_float(profiles, weights, cls, "peak_q50")
    target_kurt = _weighted_float(profiles, weights, cls, "kurtosis_q50")
    target_current_rms = _weighted_float(profiles, weights, cls, "current_rms_q50")
    target_current_kurt = _weighted_float(profiles, weights, cls, "current_kurtosis_q50")
    target_current_crest = _weighted_float(profiles, weights, cls, "current_crest_q50")

    band_pool = envelope_band_pool(profiles, list(weights), cls)
    band = np.median(np.asarray(band_pool, dtype=float), axis=0)
    band = np.clip(band, 1e-12, None)
    band = band / band.sum()

    # Build train-supported distributions by normalizing each source
    # condition's values to the predicted target median. This preserves the
    # empirical spread while removing the source-condition location shift.
    rms_values: list[float] = []
    peak_values: list[float] = []
    kurtosis_values: list[float] = []
    current_rms_values: list[float] = []
    current_kurtosis_values: list[float] = []
    current_crest_values: list[float] = []
    for cond, w in weights.items():
        prof = profiles[cond][cls]
        quota = max(40, int(round(600 * w)))
        rms_values.extend(_scaled_values(_subsample(prof.rms_values, f"{cond}:{cls}:rms", quota), prof.rms_q50, target_rms))
        peak_values.extend(_scaled_values(_subsample(prof.peak_values, f"{cond}:{cls}:peak", quota), prof.peak_q50, target_peak))
        kurtosis_values.extend(_scaled_values(_subsample(prof.kurtosis_values, f"{cond}:{cls}:kurt", quota), prof.kurtosis_q50, target_kurt))
        current_rms_values.extend(
            _scaled_values(_subsample(prof.current_rms_values, f"{cond}:{cls}:crms", quota), prof.current_rms_q50, target_current_rms)
        )
        current_kurtosis_values.extend(
            _scaled_values(
                _subsample(prof.current_kurtosis_values, f"{cond}:{cls}:ckurt", quota),
                prof.current_kurtosis_q50,
                target_current_kurt,
            )
        )
        current_crest_values.extend(
            _scaled_values(
                _subsample(prof.current_crest_values, f"{cond}:{cls}:ccrest", quota),
                prof.current_crest_q50,
                target_current_crest,
            )
        )
    nearest = max(weights, key=weights.get)
    base = profiles[nearest][cls]
    comp_scale = target_rms / max(base.rms_q50, 1e-12)
    components = [
        {"freq_hz": float(c["freq_hz"]), "amp": float(c["amp"] * comp_scale)}
        for c in base.components
    ]

    return ClassProfile(
        rms_q05=_weighted_float(profiles, weights, cls, "rms_q05"),
        rms_q50=target_rms,
        rms_q95=_weighted_float(profiles, weights, cls, "rms_q95"),
        kurtosis_q50=target_kurt,
        band_median=band.astype(float).tolist(),
        components=components,
        current_rms_q05=_weighted_float(profiles, weights, cls, "current_rms_q05"),
        current_rms_q50=target_current_rms,
        current_rms_q95=_weighted_float(profiles, weights, cls, "current_rms_q95"),
        current_kurtosis_q50=target_current_kurt,
        current_crest_q50=target_current_crest,
        peak_q50=target_peak,
        rms_values=_subsample(rms_values, f"idw:{cls}:rms"),
        peak_values=_subsample(peak_values, f"idw:{cls}:peak"),
        kurtosis_values=_subsample(kurtosis_values, f"idw:{cls}:kurt"),
        band_pool=band_pool[:600] if band_pool else [band.astype(float).tolist()],
        current_rms_values=_subsample(current_rms_values, f"idw:{cls}:crms"),
        current_kurtosis_values=_subsample(current_kurtosis_values, f"idw:{cls}:ckurt"),
        current_crest_values=_subsample(current_crest_values, f"idw:{cls}:ccrest"),
    )


def target_rate(cls: str, freqs: dict[str, float]) -> float:
    if cls == "OR":
        return float(freqs["BPFO"])
    if cls == "IR":
        return float(freqs["BPFI"])
    return 0.0


def accepted_recipe(record: dict[str, Any]) -> dict[str, Any] | None:
    if not record.get("accepted"):
        return None
    for hist in record.get("history", []):
        if hist.get("n_feasible_expansions", 0) > 0 and isinstance(hist.get("recipe"), dict):
            return hist["recipe"]
    for hist in record.get("history", []):
        if isinstance(hist.get("recipe"), dict):
            return hist["recipe"]
    return None


def source_records(heldout: str) -> list[Path]:
    root = V1_LLM_ROOT / f"loco_{heldout}" / "llm"
    if not root.exists():
        raise FileNotFoundError(root)
    return sorted(p for p in root.glob("*.json") if p.name != "summary.json")


def sample_profile(profile: ClassProfile, cls: str, slot_key: str) -> dict[str, Any]:
    rng = np.random.default_rng(stable_seed(f"pu-loco-v3-profile:{slot_key}"))

    def sample(values: list[float], default: float) -> float:
        if not values:
            return float(default)
        return float(values[int(rng.integers(0, len(values)))])

    if profile.band_pool:
        band = np.asarray(profile.band_pool[int(rng.integers(0, len(profile.band_pool)))], dtype=float)
    else:
        band = np.asarray(profile.band_median, dtype=float)
    band = np.clip(band, 1e-12, None)
    band = band / band.sum()

    return {
        "target_rms": sample(profile.rms_values, profile.rms_q50),
        "target_peak": sample(profile.peak_values, profile.peak_q50),
        "target_kurtosis": sample(profile.kurtosis_values, profile.kurtosis_q50),
        "current_rms": sample(profile.current_rms_values, profile.current_rms_q50),
        "current_kurtosis": sample(profile.current_kurtosis_values, profile.current_kurtosis_q50),
        "current_crest": sample(profile.current_crest_values, profile.current_crest_q50),
        "band_weights": band.astype(float).tolist(),
        "profile_rms_q50": float(profile.rms_q50),
        "components": profile.components,
    }


def physical_resonance(cls: str, seed_key: str, base_value: float | None) -> float:
    if cls == "OR":
        lo, hi = 600.0, 1200.0
    elif cls == "IR":
        lo, hi = 3000.0, 3600.0
    else:
        return float(base_value) if base_value is not None else 1800.0
    rng = np.random.default_rng(stable_seed(f"pu-loco-v4-resonance-envelope:{seed_key}"))
    return float(rng.uniform(lo, hi))


def project_recipe(
    recipe: dict[str, Any],
    cls: str,
    heldout: str,
    profile: ClassProfile,
    seed_key: str,
) -> dict[str, Any]:
    out = json.loads(json.dumps(recipe))
    freqs = fault_freqs(CONDITIONS[heldout][0] / 60.0)
    vals = sample_profile(profile, cls, seed_key)
    old_rms = float(out.get("target_rms", vals["profile_rms_q50"]))
    new_rms = max(float(vals["target_rms"]), 1e-8)
    scale = new_rms / max(old_rms, 1e-8)

    out["fr_hz"] = float(freqs["fr"])
    out["target_rms"] = new_rms
    rate = target_rate(cls, freqs)

    imp = out.setdefault("impacts", {})
    imp["rate_hz"] = rate
    imp["amp"] = float(max(float(imp.get("amp", 0.0)) * scale, 0.0))
    imp["resonance_hz"] = physical_resonance(cls, seed_key, imp.get("resonance_hz"))
    if cls == "healthy":
        imp["amp"] = 0.0
        imp["modulation"] = {"type": "none", "depth": 0.0}
    else:
        imp.setdefault("modulation", {"type": "shaft" if cls == "IR" else "none", "depth": 0.0})
        if cls == "IR":
            imp["modulation"]["type"] = "shaft"
        elif cls == "OR":
            imp["modulation"]["type"] = "none"
            imp["modulation"]["depth"] = 0.0

    bg = out.setdefault("background", {})
    bg["band_weights"] = vals["band_weights"]
    bg["noise_rms"] = float(max(float(bg.get("noise_rms", 0.10 * old_rms)) * scale, 0.02 * new_rms))
    for comp in bg.get("components", []):
        comp["amp"] = float(max(float(comp.get("amp", 0.0)) * scale, 0.0))
    ri = bg.get("random_impulses")
    if ri:
        ri["amp"] = float(max(float(ri.get("amp", 0.0)) * scale, 0.0))
        ri["resonance_hz"] = physical_resonance(cls, f"{seed_key}:ri", ri.get("resonance_hz"))

    cur = out.setdefault("currents", {})
    cur["fe_hz"] = float(cur.get("fe_hz", 60.0))
    cur["rms"] = float(max(vals["current_rms"], 1e-8))
    cur["kurtosis"] = float(vals["current_kurtosis"])
    cur["crest"] = float(vals["current_crest"])
    cur["fault_freq_hz"] = rate
    if cls == "healthy":
        cur["sideband_depth"] = 0.0
    else:
        cur["sideband_depth"] = float(cur.get("sideband_depth", 0.04))

    out["v3_projection"] = {
        "heldout_condition": heldout,
        "shape_model": "train-condition morphology projection",
        "target_rms": new_rms,
        "target_peak": float(vals["target_peak"]),
        "target_kurtosis": float(vals["target_kurtosis"]),
        "band_weights_source": "three-source-condition support envelope",
    }
    return out


def patch_verifier_freqs(verifier: BreezeVerifierV2, heldout: str) -> None:
    freqs = fault_freqs(CONDITIONS[heldout][0] / 60.0)
    verifier.calib["freqs"] = freqs
    verifier.calib["boundary"]["freqs"] = freqs
    if verifier.boundary is not None:
        verifier.boundary.freqs = freqs


def calibrate_verifier(
    candidate: str,
    heldout: str,
    out_dir: Path,
    loaded: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],
    train_conditions: list[str],
    nearest: str,
) -> BreezeVerifierV2:
    path = out_dir / f"verifier_{candidate}_to_{heldout}_c90_soft_w1.json"
    if path.exists():
        return BreezeVerifierV2.load(path)
    # Both candidates are admitted against the union of all three source
    # conditions. The nearest candidate changes the generation morphology, not
    # the training-only support available to the verifier.
    conds = train_conditions
    X = np.concatenate([loaded[c][0] for c in conds])
    y = np.concatenate([loaded[c][1] for c in conds])
    bearings = np.concatenate([loaded[c][2] for c in conds])
    verifier = BreezeVerifierV2(coverage=0.90, profile="soft_w1")
    verifier.calibrate(X, y, conds[0], bearings=bearings)
    verifier.calib["candidate"] = candidate
    verifier.calib["source_conditions"] = conds
    verifier.calib["pseudo_heldout_condition"] = heldout
    patch_verifier_freqs(verifier, heldout)
    verifier.save(path)
    return verifier


def gate_pass(report: dict[str, Any]) -> dict[str, bool]:
    return {name: bool(entry.get("passed", False)) for name, entry in report.get("gates", {}).items()}


def violations(report: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for gate_name, gate in report.get("gates", {}).items():
        if gate.get("passed", True):
            continue
        messages = gate.get("messages") or [gate_name]
        out.extend(str(m) for m in messages)
    return out


def run_record(
    rec_path: Path,
    candidate: str,
    heldout: str,
    out_dir: Path,
    profiles: dict[str, ClassProfile],
    verifier: BreezeVerifierV2,
    expansions: int,
) -> dict[str, Any] | None:
    src = json.loads(rec_path.read_text())
    if not src.get("accepted"):
        return None
    cls = str(src.get("class"))
    source_condition = str(src.get("condition"))
    slot = int(src.get("slot", -1))
    if cls not in CLASSES:
        return None
    out_rec_path = out_dir / f"{source_condition}_{cls}_{slot:04d}_{candidate}_{rec_path.stem}.json"
    if out_rec_path.exists():
        return json.loads(out_rec_path.read_text())
    recipe0 = accepted_recipe(src)
    if recipe0 is None:
        return None
    recipe = project_recipe(recipe0, cls, heldout, profiles[cls], f"{candidate}:{heldout}:{source_condition}:{cls}:{slot}:{rec_path.stem}")
    accepted_paths: list[str] = []
    reports: list[dict[str, Any]] = []
    for exp in range(expansions):
        seed = stable_seed(f"pu-loco-v3:{candidate}:{heldout}:{source_condition}:{cls}:{slot}:{rec_path.stem}:e{exp}")
        try:
            w = render(recipe, seed)
            report = verifier.verify(w, cls)
        except Exception as exc:
            reports.append({"feasible": False, "error": f"{type(exc).__name__}: {exc}", "gates": {}})
            continue
        reports.append(report)
        if report.get("feasible"):
            path = out_dir / f"{source_condition}_{cls}_{slot:04d}_{candidate}_{rec_path.stem}_e{exp}.npy"
            np.save(path, w)
            accepted_paths.append(str(path.relative_to(ROOT)))
    record = {
        "source": "llm_v3_internal",
        "candidate": candidate,
        "heldout": heldout,
        "source_condition": source_condition,
        "class": cls,
        "slot": slot,
        "source_json": str(rec_path.relative_to(ROOT)),
        "accepted": bool(accepted_paths),
        "accepted_paths": accepted_paths,
        "history": [
            {
                "round": 0,
                "recipe": recipe,
                "source_recipe": recipe0,
                "n_candidates": expansions,
                "n_feasible_expansions": len(accepted_paths),
                "reports": reports,
                "gate_pass": gate_pass(reports[0]) if reports else {},
                "violations": violations(reports[0]) if reports else [],
            }
        ],
    }
    out_rec_path.write_text(json.dumps(tolist(record), indent=2) + "\n")
    return record


def build_pool(heldout: str, out_dir: Path, Xtrain_all: np.ndarray, ytrain_all: np.ndarray) -> dict[str, Any]:
    xs: list[np.ndarray] = []
    ys: list[int] = []
    manifest: list[dict[str, Any]] = []
    slot_rows: list[dict[str, Any]] = []
    failures: Counter[str] = Counter()
    for rec_path in sorted(out_dir.glob("*.json")):
        if rec_path.name.startswith("verifier_") or rec_path.name == "summary.json":
            continue
        rec = json.loads(rec_path.read_text())
        if rec.get("source") != "llm_v3_internal":
            continue
        cls = rec["class"]
        ci = CLASSES.index(cls)
        paths = rec.get("accepted_paths", [])
        slot_rows.append(
            {
                "heldout": heldout,
                "source_condition": rec.get("source_condition", ""),
                "class": cls,
                "slot": rec.get("slot", ""),
                "accepted": bool(paths),
                "n_paths": len(paths),
                "source_json": rec.get("source_json", ""),
            }
        )
        if not paths:
            for hist in rec.get("history", []):
                for rep in hist.get("reports", [])[:1]:
                    for msg in violations(rep):
                        failures[f"{cls}: {msg}"] += 1
        for rel in paths:
            xs.append(np.load(ROOT / rel))
            ys.append(ci)
            manifest.append(
                {
                    "heldout": heldout,
                    "source_condition": rec.get("source_condition", ""),
                    "class": cls,
                    "slot": rec.get("slot", ""),
                    "path": rel,
                    "source_json": rec.get("source_json", ""),
                }
            )
    if xs:
        X = np.stack(xs).astype(np.float32)
        y = np.asarray(ys, dtype=np.int64)
        keep = diversity_mask(X, y, Xtrain_all, ytrain_all)
        Xk = X[keep]
        yk = y[keep]
    else:
        keep = np.zeros((0,), dtype=bool)
        Xk = np.zeros((0, 3, 2048), dtype=np.float32)
        yk = np.zeros((0,), dtype=np.int64)
    for row, kept in zip(manifest, keep.tolist()):
        row["kept_after_diversity"] = bool(kept)
    np.savez_compressed(out_dir / "pool.npz", X=Xk, y=yk, class_names=np.asarray(CLASSES))
    with (out_dir / "manifest.csv").open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["heldout", "source_condition", "class", "slot", "path", "source_json", "kept_after_diversity"],
        )
        writer.writeheader()
        writer.writerows(manifest)
    with (out_dir / "slot_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["heldout", "source_condition", "class", "slot", "accepted", "n_paths", "source_json"])
        writer.writeheader()
        writer.writerows(slot_rows)
    summary = {
        "heldout": heldout,
        "slots": len(slot_rows),
        "accepted_slots": int(sum(1 for r in slot_rows if r["accepted"])),
        "accepted_paths_before_diversity": len(manifest),
        "kept_after_diversity": int(len(yk)),
        "kept_counts": {CLASSES[i]: int((yk == i).sum()) for i in range(len(CLASSES))},
        "kept_by_source_condition": dict(Counter(row["source_condition"] for row in manifest if row.get("kept_after_diversity"))),
        "top_failures": dict(failures.most_common(20)),
    }
    (out_dir / "summary.json").write_text(json.dumps(tolist(summary), indent=2) + "\n")
    return summary


def candidate_profiles(
    candidate: str,
    heldout: str,
    train_conditions: list[str],
    profiles_by_cond: dict[str, dict[str, ClassProfile]],
    nearest: str,
) -> dict[str, ClassProfile]:
    if candidate == "morphology_nearest":
        return {cls: profiles_by_cond[nearest][cls] for cls in CLASSES}
    if candidate == "morphology_idw":
        weights = idw_weights(heldout, train_conditions)
        return {cls: interpolate_profile(profiles_by_cond, weights, cls) for cls in CLASSES}
    raise ValueError(candidate)


def build_candidate_fold(args: argparse.Namespace, candidate: str, heldout: str) -> dict[str, Any]:
    train_conditions = [cond for cond in CONDITIONS if cond != heldout]
    loaded = {cond: load_train_condition(cond) for cond in train_conditions}
    profiles_by_cond = {cond: build_profiles(loaded[cond][0], loaded[cond][1]) for cond in train_conditions}
    nearest = nearest_condition(heldout, train_conditions)
    profiles = candidate_profiles(candidate, heldout, train_conditions, profiles_by_cond, nearest)

    fold_dir = ROOT / args.out_root / candidate / f"internal_loco_{heldout}" / "llm"
    fold_dir.mkdir(parents=True, exist_ok=True)
    verifier = calibrate_verifier(candidate, heldout, fold_dir, loaded, train_conditions, nearest)

    records = [p for p in source_records(heldout) if json.loads(p.read_text()).get("accepted")]
    # Recipe records provide LLM structural templates, not target morphology.
    # Restricting them to a nearest condition discards available training-only
    # diversity and can leave classes below the fixed 20-sample pool target.
    if args.max_records_per_class > 0:
        kept: list[Path] = []
        by_class_condition: dict[str, dict[str, list[Path]]] = {cls: {} for cls in CLASSES}
        for path in records:
            source = json.loads(path.read_text())
            cls = str(source.get("class", ""))
            cond = str(source.get("condition", ""))
            if cls in by_class_condition:
                by_class_condition[cls].setdefault(cond, []).append(path)
        for cls in CLASSES:
            groups = by_class_condition[cls]
            selected = 0
            offsets = {cond: 0 for cond in groups}
            while selected < args.max_records_per_class:
                added = False
                for cond in sorted(groups):
                    index = offsets[cond]
                    if index >= len(groups[cond]) or selected >= args.max_records_per_class:
                        continue
                    kept.append(groups[cond][index])
                    offsets[cond] += 1
                    selected += 1
                    added = True
                if not added:
                    break
        records = kept

    for rec_path in records:
        run_record(rec_path, candidate, heldout, fold_dir, profiles, verifier, args.expansions)

    Xtrain_all = np.concatenate([loaded[cond][0] for cond in train_conditions])
    ytrain_all = np.concatenate([loaded[cond][1] for cond in train_conditions])
    summary = build_pool(heldout, fold_dir, Xtrain_all, ytrain_all)
    summary["candidate"] = candidate
    summary["nearest_condition"] = nearest
    summary["train_conditions"] = train_conditions
    summary["idw_weights"] = idw_weights(heldout, train_conditions)
    print(
        f"candidate={candidate} heldout={heldout} nearest={nearest} "
        f"slots={summary['slots']} accepted={summary['accepted_slots']} kept={summary['kept_counts']}",
        flush=True,
    )
    return summary


def write_report(out_root: Path, result_dir: Path, summaries: list[dict[str, Any]]) -> None:
    result_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for s in summaries:
        row = {
            "candidate": s["candidate"],
            "heldout": s["heldout"],
            "nearest_condition": s["nearest_condition"],
            "slots": s["slots"],
            "accepted_slots": s["accepted_slots"],
            "accepted_paths_before_diversity": s["accepted_paths_before_diversity"],
            "kept_after_diversity": s["kept_after_diversity"],
            "idw_weights_json": json.dumps(tolist(s["idw_weights"]), sort_keys=True, separators=(",", ":")),
        }
        row.update({f"kept_{cls}": s["kept_counts"].get(cls, 0) for cls in CLASSES})
        rows.append(row)
    if rows:
        with (result_dir / "pu_loco_v3_internal_candidate_pool_summary.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    lines = ["# PU LOCO v3 Internal Candidate Pool Report", ""]
    lines.append("- Scope: internal simulated LOCO only; no formal held-out LOCO test is touched.")
    lines.append("- API usage: 0 calls for morphology_idw/morphology_nearest; accepted v1 LLM recipes are reused as structural templates.")
    lines.append(f"- Output root: `{out_root}`")
    lines.append("- Generation/calibration data: only train-bearing windows from the three internal training conditions per fold.")
    lines.append("- Pseudo held-out data use: metadata only for rpm/torque/load kinematics and morphology prediction target.")
    lines.append("")
    lines.append("| candidate | pseudo heldout | nearest | accepted slots | kept healthy | kept OR | kept IR | status |")
    lines.append("|---|---|---|---:|---:|---:|---:|---|")
    for s in summaries:
        counts = s["kept_counts"]
        ok = all(counts.get(cls, 0) >= 20 for cls in CLASSES)
        lines.append(
            f"| {s['candidate']} | {s['heldout']} | {s['nearest_condition']} | "
            f"{s['accepted_slots']}/{s['slots']} | {counts.get('healthy', 0)} | "
            f"{counts.get('OR', 0)} | {counts.get('IR', 0)} | {'ready_for_smoke' if ok else 'pool_short'} |"
        )
    (result_dir / "pu_loco_v3_internal_candidate_pool_report.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-root", default="breeze/runs/pu_loco_v3_internal_candidates_2026-07-08")
    parser.add_argument("--result-dir", default="breeze/results/pu_loco_v4_s2_morphology_2026-07-13")
    parser.add_argument("--candidates", nargs="+", default=list(CANDIDATES))
    parser.add_argument("--heldout", nargs="+", default=list(CONDITIONS))
    parser.add_argument("--expansions", type=int, default=10)
    parser.add_argument("--max-records-per-class", type=int, default=0)
    args = parser.parse_args()

    for cand in args.candidates:
        if cand not in CANDIDATES:
            raise SystemExit(f"unknown candidate: {cand}")
    for heldout in args.heldout:
        if heldout not in CONDITIONS:
            raise SystemExit(f"unknown condition: {heldout}")

    summaries: list[dict[str, Any]] = []
    for cand in args.candidates:
        for heldout in args.heldout:
            summaries.append(build_candidate_fold(args, cand, heldout))
    write_report(ROOT / args.out_root, ROOT / args.result_dir, summaries)


if __name__ == "__main__":
    main()
