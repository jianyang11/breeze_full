"""Replay frozen PU K=3 candidates to isolate verifier gate contributions.

This script is intentionally an offline, zero-API ablation.  It reads the
archived K=3 candidate waveforms in ``runs/pool_physics_file_k3`` and never
changes that archive or the frozen Phase-A v2 snapshot.  Every ablation uses
the original file split, renderer output cache, B=150/class synthetic budget,
20 paired downstream seeds, and the frozen SimpleCNN protocol.

The gate mapping is fixed before execution:

* M2: train-supported time-statistics union (``stats_union``);
* M3: soft spectral shape and PSD-CDF W1 (both must be disabled together);
* M4: multi-band envelope evidence (``envelope_multi``);
* M5: pool-level nearest-neighbour diversity.

The PU current-sideband score is audit-only in the frozen protocol, so it is
never silently disabled here.  If a newly admitted cached candidate has no
archived expansion renders, the script keeps only the archived candidate.  It
does not invent new renderer seeds or post-process any rejected waveform.

The ``full`` replay is a hard provenance check: its raw accepted pool must be
bitwise equal to ``runs/rescreen_v2_full/pool_v2.npz`` before any ablated pool
is materialized.  Its balanced B=150/class pool is then checked against the
read-only Phase-A v2 pool.  Any discrepancy raises an error.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
SRC = BREEZE / "src"
SCRIPTS = BREEZE / "scripts"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(SCRIPTS))

from config import CLASSES, FS, MAIN_COND, fault_freqs  # noqa: E402
from data import load_file_split  # noqa: E402
from rescreen_v2 import calibrate_or_load  # noqa: E402
from verifier.v2 import BreezeVerifierV2, physical_embedding  # noqa: E402
from compute_physics_metrics import bearing_metrics, specs  # noqa: E402


ARCHIVE = BREEZE / "runs" / "pool_physics_file_k3"
FROZEN_RESCREEN = BREEZE / "runs" / "rescreen_v2_full"
FROZEN_PHASE_A = BREEZE / "results" / "phaseA_v2_frozen_2026-07-06"
FROZEN_BALANCED = (
    FROZEN_PHASE_A
    / "breeze"
    / "runs"
    / "phaseA_v2_balanced"
    / "phaseA_v2_llm_k3_B150.npz"
)
FROZEN_BALANCED_MANIFEST = FROZEN_BALANCED.with_name("phaseA_v2_llm_k3_B150_manifest.csv")
FROZEN_DOWNSTREAM = FROZEN_PHASE_A / "breeze" / "results" / "phaseA_v2_downstream_cnn.csv"

SLOTS_PER_CLASS = 150
B_PER_CLASS = 150
K_MAX = 3
COVERAGE = 0.90
PROFILE = "soft_w1"
DIVERSITY_PCTL = 1.0
SELECTION_SEED = 20260715
SHOTS = (5, 10, 25)
SEEDS = 20


@dataclass(frozen=True)
class Variant:
    name: str
    disabled_gates: frozenset[str]
    diversity_scale: float | None
    use_frozen_balanced_pool: bool = False


VARIANTS = {
    "full": Variant("full", frozenset(), 1.0, True),
    "no_M2_stats": Variant("no_M2_stats", frozenset({"stats_union"}), 1.0),
    "no_M3_spectral": Variant("no_M3_spectral", frozenset({"soft_spectrum", "psd_w1"}), 1.0),
    "no_M4_envelope": Variant("no_M4_envelope", frozenset({"envelope_multi"}), 1.0),
    "no_M5_diversity": Variant("no_M5_diversity", frozenset(), None),
    "delta_0p5": Variant("delta_0p5", frozenset(), 0.5),
    "delta_1": Variant("delta_1", frozenset(), 1.0, True),
    "delta_2": Variant("delta_2", frozenset(), 2.0),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def class_slot_jsons(slots_per_class: int) -> list[Path]:
    paths: list[Path] = []
    for cls in CLASSES:
        found = sorted(ARCHIVE.glob(f"{cls}_*.json"), key=lambda p: int(p.stem.split("_")[1]))
        if len(found) < slots_per_class:
            raise RuntimeError(f"{cls}: requested {slots_per_class} slots, archive has {len(found)}")
        paths.extend(found[:slots_per_class])
    return paths


def round_path(cls: str, slot: int, round_id: int) -> Path:
    return ARCHIVE / f"{cls}_{slot:04d}_r{round_id}.npy"


def expansions_for_slot(cls: str, slot: int) -> list[Path]:
    return sorted(ARCHIVE.glob(f"{cls}_{slot:04d}_x*.npy"))


def jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    return value


def active_feasible(report: dict[str, Any], disabled_gates: frozenset[str]) -> bool:
    gates = report["gates"]
    active = [name for name in gates if name not in disabled_gates]
    if "sanity" not in active:
        raise RuntimeError("sanity must remain active in every gate ablation")
    return bool(all(bool(gates[name]["passed"]) for name in active))


def gate_map(report: dict[str, Any]) -> dict[str, bool]:
    return {name: bool(entry["passed"]) for name, entry in report["gates"].items()}


def original_selected_path(cls: str, slot: int) -> str | None:
    record_path = FROZEN_RESCREEN / "records" / f"{cls}_{slot:04d}.json"
    if not record_path.exists():
        raise RuntimeError(f"missing frozen full record: {rel(record_path)}")
    selected = json.loads(record_path.read_text()).get("selected")
    return None if selected is None else str(Path(selected["path"]).resolve())


def existing_records(path: Path) -> dict[tuple[str, int], dict[str, Any]]:
    if not path.exists():
        return {}
    records: dict[tuple[str, int], dict[str, Any]] = {}
    with path.open() as handle:
        for line in handle:
            if line.strip():
                record = json.loads(line)
                key = (record["class"], int(record["slot"]))
                if key in records:
                    raise RuntimeError(f"duplicate checkpoint record for {key} in {rel(path)}")
                records[key] = record
    return records


def replay_slot(slot_json: Path, verifier: BreezeVerifierV2, variant: Variant) -> dict[str, Any]:
    source = json.loads(slot_json.read_text())
    cls = str(source["class"])
    slot = int(source["slot"])
    candidates: list[dict[str, Any]] = []
    selected: dict[str, Any] | None = None
    for history in source.get("history", []):
        round_id = int(history.get("round", -1))
        if round_id < 0 or round_id > K_MAX or "recipe" not in history:
            continue
        path = round_path(cls, slot, round_id)
        if not path.exists():
            candidates.append({"round": round_id, "path": rel(path), "missing": True})
            continue
        report = verifier.verify(np.load(path), cls)
        candidate = {
            "round": round_id,
            "path": rel(path),
            "gates": gate_map(report),
            "full_feasible": bool(report["feasible"]),
            "active_feasible": active_feasible(report, variant.disabled_gates),
        }
        candidates.append(candidate)
        if selected is None and candidate["active_feasible"]:
            selected = candidate

    expansions: list[dict[str, Any]] = []
    expansion_status = "no_selected_candidate"
    if selected is not None:
        archived_parent = original_selected_path(cls, slot)
        selected_parent = str((ROOT / selected["path"]).resolve())
        if selected_parent != archived_parent:
            expansion_status = "unavailable_for_newly_admitted_candidate"
        else:
            expansion_status = "evaluated_from_archived_selected_recipe"
            for path in expansions_for_slot(cls, slot):
                report = verifier.verify(np.load(path), cls)
                expansions.append(
                    {
                        "path": rel(path),
                        "gates": gate_map(report),
                        "full_feasible": bool(report["feasible"]),
                        "active_feasible": active_feasible(report, variant.disabled_gates),
                    }
                )
    return {
        "class": cls,
        "slot": slot,
        "source_json": rel(slot_json),
        "variant": variant.name,
        "selected": selected,
        "candidates": candidates,
        "expansions": expansions,
        "expansion_status": expansion_status,
    }


def replay_variant(out_dir: Path, verifier: BreezeVerifierV2, variant: Variant, slots_per_class: int) -> list[dict[str, Any]]:
    variant_dir = out_dir / "variants" / variant.name
    checkpoint = variant_dir / "records.jsonl"
    done = existing_records(checkpoint)
    all_slots = class_slot_jsons(slots_per_class)
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    with checkpoint.open("a") as handle:
        for index, slot_json in enumerate(all_slots, 1):
            meta = json.loads(slot_json.read_text())
            key = (str(meta["class"]), int(meta["slot"]))
            if key not in done:
                record = replay_slot(slot_json, verifier, variant)
                handle.write(json.dumps(jsonable(record), sort_keys=True) + "\n")
                handle.flush()
                done[key] = record
            if index % 25 == 0 or index == len(all_slots):
                accepted = sum(record["selected"] is not None for record in done.values())
                print(f"{variant.name}: {index}/{len(all_slots)} slots, accepted={accepted}", flush=True)
    records = [done[(str(json.loads(path.read_text())["class"]), int(json.loads(path.read_text())["slot"]))] for path in all_slots]
    return records


def accepted_items(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for record in records:
        selected = record["selected"]
        if selected is None:
            continue
        items.append(
            {
                "class": record["class"],
                "slot": int(record["slot"]),
                "kind": "selected",
                "path": selected["path"],
            }
        )
        for expansion in record["expansions"]:
            if expansion["active_feasible"]:
                items.append(
                    {
                        "class": record["class"],
                        "slot": int(record["slot"]),
                        "kind": "expansion",
                        "path": expansion["path"],
                    }
                )
    return items


def diversity_filter(
    items: list[dict[str, Any]],
    verifier: BreezeVerifierV2,
    scale: float | None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    X_real, y_real, _ = load_file_split("train", MAIN_COND)
    kept: list[dict[str, Any]] = []
    details: dict[str, dict[str, Any]] = {}
    for class_id, cls in enumerate(CLASSES):
        class_items = [item for item in items if item["class"] == cls]
        if not class_items:
            details[cls] = {"before": 0, "after": 0, "base_delta": None, "active_delta": None, "enabled": scale is not None}
            continue
        real_class = X_real[y_real == class_id]
        real_features = np.asarray([physical_embedding(window, cls, verifier.calib) for window in real_class])
        center = real_features.mean(axis=0)
        spread = real_features.std(axis=0) + 1e-9
        real_z = (real_features - center) / spread
        distances = np.sqrt(((real_z[:, None] - real_z[None]) ** 2).sum(axis=-1))
        np.fill_diagonal(distances, np.inf)
        base_delta = float(np.percentile(distances.min(axis=1), DIVERSITY_PCTL))
        active_delta = None if scale is None else float(scale * base_delta)
        selected_z: list[np.ndarray] = []
        for item in class_items:
            window = np.load(ROOT / item["path"])
            z = (physical_embedding(window, cls, verifier.calib) - center) / spread
            if active_delta is None or not selected_z:
                kept.append(item)
                selected_z.append(z)
                continue
            nearest = min(float(np.linalg.norm(z - previous)) for previous in selected_z)
            if nearest >= active_delta:
                kept.append(item)
                selected_z.append(z)
        details[cls] = {
            "before": len(class_items),
            "after": sum(item["class"] == cls for item in kept),
            "base_delta": base_delta,
            "active_delta": active_delta,
            "enabled": scale is not None,
        }
    return kept, details


def pool_from_items(items: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    windows = [np.load(ROOT / item["path"]).astype(np.float32) for item in items]
    labels = [CLASSES.index(item["class"]) for item in items]
    if not windows:
        return np.zeros((0, 3, 2048), dtype=np.float32), np.zeros(0, dtype=np.int64)
    return np.stack(windows), np.asarray(labels, dtype=np.int64)


def choose_balanced(
    items: list[dict[str, Any]], variant: Variant, b_per_class: int
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    if variant.use_frozen_balanced_pool:
        if b_per_class != B_PER_CLASS:
            raise RuntimeError(
                f"{variant.name}: smoke pools cannot reuse the frozen B={B_PER_CLASS} selection; "
                "run smoke only for non-frozen variants"
            )
        source = np.load(FROZEN_BALANCED, allow_pickle=True)
        X = source["X"].astype(np.float32)
        y = source["y"].astype(np.int64)
        manifest = read_csv(FROZEN_BALANCED_MANIFEST)
        return X, y, [dict(row) for row in manifest]
    X, y = pool_from_items(items)
    rng = np.random.default_rng(SELECTION_SEED)
    xs, ys, manifest = [], [], []
    for class_id, cls in enumerate(CLASSES):
        indexes = np.where(y == class_id)[0]
        if len(indexes) < b_per_class:
            raise RuntimeError(
                f"{variant.name}/{cls}: only {len(indexes)} cached admitted windows; "
                f"requires fixed B={b_per_class} without creating new renders"
            )
        chosen = np.sort(rng.choice(indexes, size=b_per_class, replace=False))
        xs.append(X[chosen])
        ys.append(np.full(b_per_class, class_id, dtype=np.int64))
        for rank, source_index in enumerate(chosen.tolist()):
            manifest.append(
                {
                    "variant": variant.name,
                    "class": cls,
                    "rank_in_class": rank,
                    "source_index": source_index,
                    "source_path": items[source_index]["path"],
                    "source_kind": items[source_index]["kind"],
                    "slot": items[source_index]["slot"],
                    "selection_seed": SELECTION_SEED,
                }
            )
    return np.concatenate(xs).astype(np.float32), np.concatenate(ys), manifest


def save_npz(path: Path, X: np.ndarray, y: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.stem + ".tmp.npz")
    np.savez_compressed(temporary, X=X, y=y, class_names=np.asarray(CLASSES))
    temporary.replace(path)


def check_full_replay(items: list[dict[str, Any]], variant: Variant) -> None:
    if variant.name != "full":
        return
    X, y = pool_from_items(items)
    reference = np.load(FROZEN_RESCREEN / "pool_v2.npz", allow_pickle=True)
    if not np.array_equal(X, reference["X"]) or not np.array_equal(y, reference["y"]):
        raise RuntimeError(
            "full gate replay differs from frozen rescreen_v2_full pool; "
            "stop before materializing any ablation pool"
        )


def materialize_variant(
    out_dir: Path,
    verifier: BreezeVerifierV2,
    variant: Variant,
    slots_per_class: int,
    b_per_class: int,
) -> dict[str, Any]:
    records = replay_variant(out_dir, verifier, variant, slots_per_class)
    items = accepted_items(records)
    kept, diversity = diversity_filter(items, verifier, variant.diversity_scale)
    if slots_per_class == SLOTS_PER_CLASS:
        check_full_replay(kept, variant)
    class_counts = {cls: sum(item["class"] == cls for item in kept) for cls in CLASSES}
    shortfalls = {cls: count for cls, count in class_counts.items() if count < b_per_class}
    variant_dir = out_dir / "variants" / variant.name
    common_row = {
        "variant": variant.name,
        "disabled_gates": ";".join(sorted(variant.disabled_gates)),
        "diversity_scale": "disabled" if variant.diversity_scale is None else variant.diversity_scale,
        "slots_per_class": slots_per_class,
        "slots_total": len(records),
        "accepted_slots": sum(record["selected"] is not None for record in records),
        "slot_acceptance_rate": sum(record["selected"] is not None for record in records) / len(records),
        "items_before_diversity": len(items),
        "items_after_diversity": len(kept),
        "kept_healthy": class_counts["healthy"],
        "kept_OR": class_counts["OR"],
        "kept_IR": class_counts["IR"],
        "diversity": diversity,
    }
    if shortfalls:
        capacity_status = ";".join(
            f"{cls}={count}<{b_per_class}" for cls, count in shortfalls.items()
        )
        row = {
            **common_row,
            "pool_available": False,
            "capacity_status": capacity_status,
            "selected_per_class": "not_materialized",
            "pool_path": "",
            "pool_sha256": "",
        }
        write_json(
            variant_dir / "capacity_failure.json",
            jsonable(
                {
                    **row,
                    "reason": "The cached archive cannot supply the fixed B=150/class budget. "
                    "No render, resampling, budget reduction, or downstream evaluation is permitted.",
                }
            ),
        )
        write_json(variant_dir / "pool_summary.json", jsonable(row))
        return row
    X, y, manifest = choose_balanced(kept, variant, b_per_class)
    if variant.use_frozen_balanced_pool:
        frozen = np.load(FROZEN_BALANCED, allow_pickle=True)
        if not np.array_equal(X, frozen["X"]) or not np.array_equal(y, frozen["y"]):
            raise RuntimeError(f"{variant.name}: balanced replay differs from read-only Phase-A v2 pool")
    save_npz(variant_dir / "pool_B150.npz", X, y)
    write_csv(
        variant_dir / "selected_manifest.csv",
        manifest,
        list(manifest[0].keys()) if manifest else ["variant", "class"],
    )
    row = {
        **common_row,
        "pool_available": True,
        "capacity_status": "sufficient",
        "selected_per_class": b_per_class,
        "pool_path": rel(variant_dir / "pool_B150.npz"),
        "pool_sha256": sha256(variant_dir / "pool_B150.npz"),
        "diversity": diversity,
    }
    write_json(variant_dir / "pool_summary.json", jsonable(row))
    return row


def protocol_manifest(
    out_dir: Path,
    variants: list[Variant],
    slots_per_class: int,
    b_per_class: int,
    calibration_path: Path | None,
) -> None:
    input_paths = [FROZEN_BALANCED, FROZEN_BALANCED_MANIFEST, FROZEN_DOWNSTREAM, FROZEN_RESCREEN / "pool_v2.npz"]
    for path in class_slot_jsons(slots_per_class):
        input_paths.append(path)
    if calibration_path is not None:
        if not calibration_path.exists():
            raise FileNotFoundError(f"requested calibration checkpoint is missing: {calibration_path}")
        input_paths.append(calibration_path)
    write_json(
        out_dir / "run_manifest.json",
        {
            "purpose": "zero-API cached-candidate PU verifier gate ablation",
            "protocol": {
                "condition": MAIN_COND,
                "split": "frozen PU file split",
                "k_max": K_MAX,
                "slots_per_class": slots_per_class,
                "budget_per_class": b_per_class,
                "downstream_shots": list(SHOTS),
                "downstream_seeds": SEEDS,
                "downstream_model": "frozen SimpleCNN, 60 epochs",
                "selection_seed_for_nonfrozen_variants": SELECTION_SEED,
                "api_calls": 0,
            },
            "gate_mapping": {
                "M2": ["stats_union"],
                "M3": ["soft_spectrum", "psd_w1"],
                "M4": ["envelope_multi"],
                "M5": ["pool-level nearest-neighbour diversity"],
                "always_active": ["sanity", "vector_mcsa when available"],
            },
            "variants": [
                {
                    "name": variant.name,
                    "disabled_gates": sorted(variant.disabled_gates),
                    "diversity_scale": variant.diversity_scale,
                    "uses_frozen_balanced_pool": variant.use_frozen_balanced_pool,
                }
                for variant in variants
            ],
            "cached-expansion-policy": "Use an archived expansion only when its archived parent recipe remains selected. Newly admitted cached candidates without archived expansions contribute their archived candidate waveform only; no new renderer seed is created.",
            "inputs": [{"path": rel(path), "sha256": sha256(path)} for path in input_paths],
        },
    )


def run_replay(
    out_dir: Path,
    variants: list[Variant],
    slots_per_class: int,
    b_per_class: int,
    calibration_path: Path | None,
) -> list[dict[str, Any]]:
    if slots_per_class > SLOTS_PER_CLASS:
        raise ValueError(f"slots_per_class must be <= {SLOTS_PER_CLASS}")
    if b_per_class <= 0 or b_per_class > B_PER_CLASS:
        raise ValueError(f"b_per_class must be in [1, {B_PER_CLASS}]")
    calibration = calibration_path or (out_dir / f"verifier_v2_{MAIN_COND}_c90_{PROFILE}.json")
    protocol_manifest(out_dir, variants, slots_per_class, b_per_class, calibration_path)
    verifier = calibrate_or_load(calibration, COVERAGE, PROFILE, force=False)
    updated_summaries = [
        materialize_variant(out_dir, verifier, variant, slots_per_class, b_per_class)
        for variant in variants
    ]
    summary_by_variant: dict[str, dict[str, Any]] = {}
    for name in VARIANTS:
        summary_path = out_dir / "variants" / name / "pool_summary.json"
        if summary_path.exists():
            existing = json.loads(summary_path.read_text())
            existing.setdefault("pool_available", bool(existing.get("pool_path")))
            existing.setdefault("capacity_status", "sufficient" if existing["pool_available"] else "unknown")
            summary_by_variant[name] = existing
    for item in updated_summaries:
        summary_by_variant[item["variant"]] = item
    summaries = [summary_by_variant[name] for name in VARIANTS if name in summary_by_variant]
    flat_rows = []
    for summary in summaries:
        flat_rows.append(
            {
                key: value
                for key, value in summary.items()
                if key != "diversity"
            }
        )
        for cls, detail in summary["diversity"].items():
            flat_rows[-1][f"delta_{cls}"] = detail["active_delta"]
    fields = [
        "variant", "disabled_gates", "diversity_scale", "slots_per_class", "slots_total", "accepted_slots",
        "slot_acceptance_rate", "items_before_diversity", "items_after_diversity", "kept_healthy", "kept_OR",
        "kept_IR", "pool_available", "capacity_status", "selected_per_class", "pool_path", "pool_sha256",
        "delta_healthy", "delta_OR", "delta_IR",
    ]
    write_csv(out_dir / "gate_ablation_pool_summary.csv", flat_rows, fields)
    return summaries


def physics_rows(out_dir: Path, variants: list[Variant]) -> list[dict[str, Any]]:
    X_ref, y_ref, _ = load_file_split("train", MAIN_COND)
    pu_spec = specs()["pu"]
    frequencies = fault_freqs(900.0 / 60.0)
    rows: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    for variant in variants:
        pool_path = out_dir / "variants" / variant.name / "pool_B150.npz"
        if not pool_path.exists():
            coverage.append({"variant": variant.name, "physics_evaluated": False, "reason": "fixed B=150 pool unavailable"})
            continue
        coverage.append({"variant": variant.name, "physics_evaluated": True, "reason": ""})
        data = np.load(pool_path, allow_pickle=True)
        X_pool, y_pool = data["X"].astype(np.float32), data["y"].astype(np.int64)
        for class_id, cls in enumerate(CLASSES):
            values = bearing_metrics(
                X_pool[y_pool == class_id],
                X_ref[y_ref == class_id],
                FS,
                pu_spec.band_edges,
                None if cls == "healthy" else frequencies["BPFO" if cls == "OR" else "BPFI"],
            )
            for metric, value in values.items():
                rows.append({"variant": variant.name, "class": cls, "metric": metric, "value": float(value)})
    write_csv(out_dir / "gate_ablation_physics.csv", rows, ["variant", "class", "metric", "value"])
    write_csv(out_dir / "gate_ablation_physics_coverage.csv", coverage, ["variant", "physics_evaluated", "reason"])
    return rows


def run_downstream(out_dir: Path, variants: list[Variant]) -> None:
    evaluator = BREEZE / "src" / "eval_custom_pool.py"
    representative_by_hash: dict[str, str] = {}
    for variant in variants:
        if variant.use_frozen_balanced_pool:
            continue
        pool = out_dir / "variants" / variant.name / "pool_B150.npz"
        if not pool.exists():
            print(f"[downstream skipped] {variant.name}: fixed B=150 pool unavailable", flush=True)
            continue
        pool_hash = sha256(pool)
        if pool_hash in representative_by_hash:
            representative = representative_by_hash[pool_hash]
            write_json(
                out_dir / "variants" / variant.name / "downstream_equivalence.json",
                {
                    "variant": variant.name,
                    "equivalent_to": representative,
                    "pool_sha256": pool_hash,
                    "reason": "The two B=150 pools are byte-identical; the deterministic paired downstream input is therefore identical.",
                },
            )
            print(f"[downstream equivalent] {variant.name} -> {representative}: identical pool sha256", flush=True)
            continue
        representative_by_hash[pool_hash] = variant.name
        output = out_dir / "variants" / variant.name / "downstream.csv"
        command = [
            sys.executable,
            str(evaluator),
            "--pool", str(pool),
            "--baseline", variant.name,
            "--seeds", str(SEEDS),
            "--n_real", *[str(shot) for shot in SHOTS],
            "--n_syn", str(B_PER_CLASS),
            "--out", str(output),
        ]
        print("[downstream]", " ".join(command), flush=True)
        subprocess.run(command, cwd=ROOT, check=True)


def downstream_rows_for_variant(out_dir: Path, variant: Variant) -> tuple[list[dict[str, str]], str]:
    direct = out_dir / "variants" / variant.name / "downstream.csv"
    if direct.exists():
        return read_csv(direct), variant.name
    equivalence = out_dir / "variants" / variant.name / "downstream_equivalence.json"
    if not equivalence.exists():
        raise FileNotFoundError(f"missing downstream output for {variant.name}")
    detail = json.loads(equivalence.read_text())
    if detail.get("pool_sha256") != sha256(out_dir / "variants" / variant.name / "pool_B150.npz"):
        raise RuntimeError(f"{variant.name}: downstream-equivalence pool hash no longer matches")
    representative = str(detail["equivalent_to"])
    source = out_dir / "variants" / representative / "downstream.csv"
    if not source.exists():
        raise FileNotFoundError(f"{variant.name}: equivalent source output is missing: {rel(source)}")
    return read_csv(source), representative


def frozen_baseline_rows() -> list[dict[str, str]]:
    return [
        row for row in read_csv(FROZEN_DOWNSTREAM)
        if row["baseline"] == "phaseA_v2_llm_k3" and int(row["n_real"]) in SHOTS
    ]


def numerical_summary(values: list[float]) -> tuple[float, float]:
    array = np.asarray(values, dtype=float)
    return float(array.mean()), float(array.std(ddof=1))


def summary(out_dir: Path, variants: list[Variant]) -> None:
    pools = {row["variant"]: row for row in read_csv(out_dir / "gate_ablation_pool_summary.csv")}
    available = {
        variant.name
        for variant in variants
        if pools[variant.name].get("pool_available", "True").strip().lower() == "true"
    }
    reference = frozen_baseline_rows()
    reference_by_key = {(int(row["n_real"]), int(row["seed"])): row for row in reference}
    if len(reference_by_key) != len(SHOTS) * SEEDS:
        raise RuntimeError("frozen Phase-A v2 baseline is incomplete for the gate-ablation cells")
    downstream_rows: list[dict[str, Any]] = []
    for variant in variants:
        if variant.name not in available:
            continue
        if variant.use_frozen_balanced_pool:
            rows = reference
            downstream_source = "frozen_full"
        else:
            rows, downstream_source = downstream_rows_for_variant(out_dir, variant)
        for shot in SHOTS:
            shot_rows = sorted((row for row in rows if int(row["n_real"]) == shot), key=lambda row: int(row["seed"]))
            if len(shot_rows) != SEEDS:
                raise RuntimeError(f"{variant.name} n={shot}: expected {SEEDS} downstream rows, found {len(shot_rows)}")
            for metric in ("acc", "macro_f1"):
                vals = [float(row[metric]) for row in shot_rows]
                base = [float(reference_by_key[(shot, int(row["seed"]))][metric]) for row in shot_rows]
                mean, std = numerical_summary(vals)
                downstream_rows.append(
                    {
                        "variant": variant.name,
                        "n_real": shot,
                        "metric": metric,
                        "n": len(vals),
                        "mean": mean,
                        "std": std,
                        "mean_delta_vs_frozen_full": float(np.mean(np.asarray(vals) - np.asarray(base))),
                        "downstream_source": downstream_source,
                    }
                )
    write_csv(
        out_dir / "gate_ablation_downstream_summary.csv",
        downstream_rows,
        ["variant", "n_real", "metric", "n", "mean", "std", "mean_delta_vs_frozen_full", "downstream_source"],
    )

    physics = read_csv(out_dir / "gate_ablation_physics.csv")
    physics_rows: list[dict[str, Any]] = []
    for variant in variants:
        if variant.name not in available:
            continue
        for metric in ("psd_w1_mean", "rms_w1", "band_energy_relative_error_mean", "nn_diversity"):
            vals = [float(row["value"]) for row in physics if row["variant"] == variant.name and row["metric"] == metric]
            physics_rows.append({"variant": variant.name, "metric": metric, "class_averaged_value": float(np.mean(vals))})
    write_csv(out_dir / "gate_ablation_physics_summary.csv", physics_rows, ["variant", "metric", "class_averaged_value"])

    downstream_index = {(row["variant"], int(row["n_real"]), row["metric"]): row for row in downstream_rows}
    physics_index = {(row["variant"], row["metric"]): row for row in physics_rows}
    lines = [
        "# PU verifier-gate ablation",
        "",
        "## Protocol",
        "",
        "This zero-API experiment re-screens the frozen 450-slot-per-class K=3 PU candidate archive. M2 disables only the statistics union, M3 disables both soft-spectrum and PSD-W1 checks, M4 disables multi-band envelope evidence, and M5 disables only pool-level diversity. Sanity and any available current-sideband check remain active. The full replay must exactly reproduce the frozen raw rescreen pool before variants are materialized. Every evaluable downstream variant uses B=150/class, the frozen file split, 20 paired seeds, and the same 60-epoch SimpleCNN.",
        "",
        "## Gate ablation summary",
        "",
        "| variant | slot acceptance | items after diversity | PSD-W1 (class avg.) | n=5 Acc delta | n=5 F1 delta | n=10 Acc delta | n=10 F1 delta | n=25 Acc delta | n=25 F1 delta | status |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for variant in variants:
        pool = pools[variant.name]
        if variant.name not in available:
            lines.append(
                f"| {variant.name} (capacity-limited) | {float(pool['slot_acceptance_rate']):.4f} | "
                f"{int(pool['items_after_diversity'])} | n/a | n/a | n/a | n/a | n/a | n/a | n/a | "
                f"{pool['capacity_status']} |"
            )
            continue
        cells = []
        for shot in SHOTS:
            cells.append(float(downstream_index[(variant.name, shot, "acc")]["mean_delta_vs_frozen_full"]))
            cells.append(float(downstream_index[(variant.name, shot, "macro_f1")]["mean_delta_vs_frozen_full"]))
        psd = float(physics_index[(variant.name, "psd_w1_mean")]["class_averaged_value"])
        lines.append(
            f"| {variant.name} | {float(pool['slot_acceptance_rate']):.4f} | {int(pool['items_after_diversity'])} | {psd:.6f} | "
            + " | ".join(f"{value:+.4f}" for value in cells)
            + " | sufficient |"
        )
    lines.extend(
        [
            "",
            "The downstream deltas are paired descriptive differences from the frozen full-gate Phase-A v2 LLM rows; this ablation does not replace the registered recipe-source test family. Physical values are class-averaged reference-relative diagnostics and do not provide a universal generator ranking.",
            "",
            "The `delta_0p5`, `delta_1`, and `delta_2` rows form the preregistered diversity-threshold sensitivity table. `delta_1` reuses the verified frozen balanced pool after the full raw replay check. A threshold variant without B=150 cached windows in every class is recorded as capacity-limited and is not given a reduced-budget downstream comparison.",
        ]
    )
    (out_dir / "gate_ablation_report.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="breeze/results/ablation_2026-07-15/gate_ablation_v1")
    parser.add_argument("--stage", choices=["replay", "physics", "downstream", "summary", "all"], default="all")
    parser.add_argument("--variants", nargs="+", choices=sorted(VARIANTS), default=["full", "no_M2_stats", "no_M3_spectral", "no_M4_envelope", "no_M5_diversity", "delta_0p5", "delta_1", "delta_2"])
    parser.add_argument("--slots-per-class", type=int, default=SLOTS_PER_CLASS)
    parser.add_argument("--b-per-class", type=int, default=B_PER_CLASS)
    parser.add_argument("--calibration", help="read-only calibration checkpoint from an identical prior smoke run")
    args = parser.parse_args()

    out_dir = (ROOT / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out).resolve()
    variants = [VARIANTS[name] for name in args.variants]
    calibration = None if args.calibration is None else Path(args.calibration).resolve()
    if args.stage in {"replay", "all"}:
        run_replay(out_dir, variants, args.slots_per_class, args.b_per_class, calibration)
    if args.stage in {"physics", "all"}:
        physics_rows(out_dir, variants)
    if args.stage in {"downstream", "all"}:
        if args.slots_per_class != SLOTS_PER_CLASS or args.b_per_class != B_PER_CLASS:
            raise RuntimeError("downstream is prohibited for smoke-sized candidate replays")
        run_downstream(out_dir, variants)
    if args.stage in {"summary", "all"}:
        if args.slots_per_class != SLOTS_PER_CLASS or args.b_per_class != B_PER_CLASS:
            raise RuntimeError("summary is prohibited for smoke-sized candidate replays")
        summary(out_dir, variants)


if __name__ == "__main__":
    main()
