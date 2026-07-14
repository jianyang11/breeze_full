"""Private machine-tool v3 discriminative conditional synthesis.

This entry point implements the preregistered zero-API S-A/S-B line.  It is
deliberately isolated from formal file IDs 7/8 and reuses the v2 generic
verifier plus its already-approved exploratory class-identity certificate.
No component-specific frequency or machine parameter is inferred here.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
from scipy.stats import wilcoxon
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

SCRIPT_DIR = Path(__file__).resolve().parent
BREEZE_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(BREEZE_DIR / "src"))

from data_mt import MT_CHANNELS, MT_CLASSES, WIN_MT, class_name_to_raw_id  # noqa: E402
from mt_private_v2_llm_smoke import (  # noqa: E402
    DevData,
    Admission,
    apply_soft_band_gain,
    admit_candidate,
    build_admission,
    candidate_feedback,
    class_exemplar_statistics,
    iaaft_surrogate,
    load_development_train,
    load_inner_validation,
    noise_augment,
    normalize_recipe,
    normalize_train_val,
    predict_cnn,
    prompt_messages,
    recipe_schema,
    render_mt_recipe,
    robust_scale,
    sample_real_subset,
    stable_seed,
    train_cnn,
)
from mt_verifier import MachineToolVerifier, soft_spectrum_vector, structure_vector  # noqa: E402
from config import LLM_BASE_URL, LLM_MIN_INTERVAL, LLM_MODEL  # noqa: E402


STAGE_DATE = "2026-07-13"
OUT_DIR = BREEZE_DIR / "results" / f"mt_private_v3_conditional_{STAGE_DATE}"
RUN_DIR = BREEZE_DIR / "runs" / f"mt_private_v3_conditional_{STAGE_DATE}"
INNER_TRAIN_FILE_IDS = ("1", "2", "4", "5")
INNER_VAL_FILE_ID = "10"
FORBIDDEN_FILE_IDS = {"7", "8"}
N_BANDS = 8
CONTROLS_PER_CLASS = 100
REAL_CORE_MIN_RATE = 0.80
MAX_ATTEMPTS_PER_CLASS = 80
DIRECTION_GAIN_STRENGTH = 0.08
DIRECTION_CLIP = 2.0
MIX_ALPHAS = (0.35, 0.50, 0.65)
DOWNSTREAM_SEEDS = 10
DOWNSTREAM_N_REALS = (10, 25, 50)
POOL_N_SYN = 20
DOWNSTREAM_N_SYN_BY_N_REAL = {10: 10, 25: 20, 50: 20}
S_C_API_BUDGET = 100
S_C_SMOKE_REQUESTS = 3
S_C_AMENDMENT_1_SMOKE_REQUESTS = 6
S_C_MAX_FEEDBACK_ROUNDS = 3
S_C_EXPANSIONS_PER_RECIPE = 3


def json_ready(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_ready(value), indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows([{key: json_ready(value) for key, value in row.items()} for row in rows])


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def ensure_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name in ("audit", "profiles", "pools", "candidates", "checkpoints"):
        (RUN_DIR / name).mkdir(parents=True, exist_ok=True)


@dataclass
class Context:
    dev: DevData
    verifier: MachineToolVerifier
    admission: Admission
    templates: dict[str, np.ndarray]
    sources: dict[str, np.ndarray]
    profile: dict[str, dict[str, np.ndarray]]


def _class_indices(dev: DevData, cls: str) -> np.ndarray:
    return np.flatnonzero(dev.y_train == MT_CLASSES.index(cls))


def directional_profile(dev: DevData) -> dict[str, dict[str, np.ndarray]]:
    """Compute fixed signed, renderer-controllable directions from inner train only."""
    soft = np.asarray([soft_spectrum_vector(window) for window in dev.X_train], dtype=np.float64)
    channel_std = np.asarray([np.std(window, axis=1) for window in dev.X_train], dtype=np.float64)
    profile: dict[str, dict[str, np.ndarray]] = {}
    for ci, cls in enumerate(MT_CLASSES):
        target = dev.y_train == ci
        other = ~target
        soft_scale = np.sqrt((robust_scale(soft[target]) ** 2 + robust_scale(soft[other]) ** 2) / 2.0)
        std_scale = np.sqrt((robust_scale(channel_std[target]) ** 2 + robust_scale(channel_std[other]) ** 2) / 2.0)
        soft_direction = (np.median(soft[target], axis=0) - np.median(soft[other], axis=0)) / (soft_scale + 1e-12)
        std_direction = (np.median(channel_std[target], axis=0) - np.median(channel_std[other], axis=0)) / (std_scale + 1e-12)
        profile[cls] = {
            "soft_direction": soft_direction.reshape(len(MT_CHANNELS), N_BANDS),
            "soft_gain": np.exp(DIRECTION_GAIN_STRENGTH * np.clip(soft_direction, -DIRECTION_CLIP, DIRECTION_CLIP)).reshape(len(MT_CHANNELS), N_BANDS),
            "std_direction": std_direction,
            "std_gain": np.exp(DIRECTION_GAIN_STRENGTH * np.clip(std_direction, -DIRECTION_CLIP, DIRECTION_CLIP)),
        }
    return profile


def build_context() -> Context:
    dev = load_development_train()
    verifier = MachineToolVerifier(coverage=0.90)
    verifier.calibrate(dev.X_train, dev.y_train, dev.train_files)
    admission = build_admission(dev, verifier)
    templates, sources = {}, {}
    for cls in MT_CLASSES:
        indices = _class_indices(dev, cls)
        templates[cls] = dev.X_train[indices]
        sources[cls] = dev.train_files[indices]
    return Context(dev, verifier, admission, templates, sources, directional_profile(dev))


def core_admit(window: np.ndarray, asserted_class: str, context: Context) -> dict[str, Any]:
    """Admission for audit controls, excluding synthetic-only duplicate/diversity checks."""
    verifier = context.verifier.verify(window, asserted_class)
    failed_hard_gates = [name for name, gate in verifier["gates"].items() if not gate["passed"]]
    if not verifier["feasible"]:
        return {
            "asserted_class": asserted_class,
            "raw_class_id": class_name_to_raw_id(asserted_class),
            "core_accepted": False,
            "hard_gates_passed": False,
            "identity_passed": False,
            "identity_prediction": "not_evaluated_after_hard_gate_failure",
            "identity_probability": 0.0,
            "failure_reasons": failed_hard_gates,
            "gate_status": {name: bool(gate["passed"]) for name, gate in verifier["gates"].items()},
        }
    feature = structure_vector(window)
    probabilities = context.admission.identity.predict_proba(feature.reshape(1, -1))[0]
    asserted_index = MT_CLASSES.index(asserted_class)
    predicted_index = int(np.argmax(probabilities))
    identity_passed = predicted_index == asserted_index
    failures = list(failed_hard_gates)
    if not identity_passed:
        failures.append("class_identity")
    return {
        "asserted_class": asserted_class,
        "raw_class_id": class_name_to_raw_id(asserted_class),
        "core_accepted": bool(verifier["feasible"] and identity_passed),
        "hard_gates_passed": bool(verifier["feasible"]),
        "identity_passed": bool(identity_passed),
        "identity_prediction": MT_CLASSES[predicted_index],
        "identity_probability": float(probabilities[asserted_index]),
        "failure_reasons": failures,
        "gate_status": {name: bool(gate["passed"]) for name, gate in verifier["gates"].items()},
    }


def _audit_row(control: str, source_class: str, source_file: str, asserted_class: str, seed: int | str, report: dict[str, Any]) -> dict[str, Any]:
    return {
        "control": control,
        "source_class": source_class,
        "source_file": source_file,
        "asserted_class": asserted_class,
        "seed": seed,
        "core_accepted": report["core_accepted"],
        "hard_gates_passed": report["hard_gates_passed"],
        "identity_passed": report["identity_passed"],
        "identity_prediction": report["identity_prediction"],
        "identity_probability": report["identity_probability"],
        "failure_reasons": "|".join(report["failure_reasons"]),
        "gate_status": json.dumps(report["gate_status"], sort_keys=True, separators=(",", ":")),
    }


def run_admission_audit(context: Context, controls_per_class: int = CONTROLS_PER_CLASS) -> dict[str, Any]:
    if controls_per_class != CONTROLS_PER_CLASS:
        raise ValueError(f"controls_per_class is frozen at {CONTROLS_PER_CLASS}")
    rows: list[dict[str, Any]] = []
    real_by_class: dict[str, list[dict[str, Any]]] = {cls: [] for cls in MT_CLASSES}
    for ci, source_class in enumerate(MT_CLASSES):
        indices = np.flatnonzero(context.dev.y_train == ci)
        for index in indices:
            report = core_admit(context.dev.X_train[index], source_class, context)
            row = _audit_row("real_true_label", source_class, str(context.dev.train_files[index]), source_class, int(index), report)
            rows.append(row)
            real_by_class[source_class].append(row)
            for asserted_class in MT_CLASSES:
                if asserted_class == source_class:
                    continue
                wrong = core_admit(context.dev.X_train[index], asserted_class, context)
                rows.append(_audit_row("wrong_label", source_class, str(context.dev.train_files[index]), asserted_class, int(index), wrong))

    for ci, cls in enumerate(MT_CLASSES):
        subset = context.dev.X_train[context.dev.y_train == ci]
        mean = subset.mean(axis=(0, 2))
        std = subset.std(axis=(0, 2))
        for control_index in range(controls_per_class):
            seed = stable_seed("mt_private_v3", "white_noise", cls, control_index)
            rng = np.random.default_rng(seed)
            white = (mean[:, None] + std[:, None] * rng.normal(size=(len(MT_CHANNELS), WIN_MT))).astype(np.float32)
            rows.append(_audit_row("white_noise", "white_noise", "none", cls, seed, core_admit(white, cls, context)))
            constant = np.broadcast_to(mean[:, None], (len(MT_CHANNELS), WIN_MT)).astype(np.float32).copy()
            rows.append(_audit_row("constant", "constant", "none", cls, seed, core_admit(constant, cls, context)))

    write_csv(OUT_DIR / "mt_private_v3_admission_audit_rows.csv", rows)
    real_summary = []
    for cls in MT_CLASSES:
        class_rows = real_by_class[cls]
        source_rates = {
            source: float(np.mean([bool(row["core_accepted"]) for row in class_rows if row["source_file"] == source]))
            for source in sorted({str(row["source_file"]) for row in class_rows})
        }
        real_summary.append({
            "class_name": cls,
            "n": len(class_rows),
            "core_admission_rate": float(np.mean([bool(row["core_accepted"]) for row in class_rows])),
            "source_rates": source_rates,
            "all_sources_nonzero": bool(all(rate > 0.0 for rate in source_rates.values())),
        })
    wrong = [row for row in rows if row["control"] == "wrong_label"]
    white = [row for row in rows if row["control"] == "white_noise"]
    constant = [row for row in rows if row["control"] == "constant"]
    separability = []
    for source_class in MT_CLASSES:
        subset = [row for row in rows if row["control"] == "real_true_label" and row["source_class"] == source_class]
        for predicted_class in MT_CLASSES:
            separability.append({
                "source_class": source_class,
                "identity_prediction": predicted_class,
                "count": sum(row["identity_prediction"] == predicted_class for row in subset),
                "mean_asserted_probability": float(np.mean([float(row["identity_probability"]) for row in subset])),
            })
    write_csv(OUT_DIR / "mt_private_v3_source_separability_report.csv", separability)
    real_ok = all(row["core_admission_rate"] >= REAL_CORE_MIN_RATE and row["all_sources_nonzero"] for row in real_summary)
    decision = {
        "status": "PASS" if real_ok and not any(row["core_accepted"] for row in wrong + white + constant) else "BLOCKED",
        "controls_per_class": CONTROLS_PER_CLASS,
        "real_carrier_min_rate": REAL_CORE_MIN_RATE,
        "real_carrier": real_summary,
        "wrong_label_admitted": int(sum(bool(row["core_accepted"]) for row in wrong)),
        "wrong_label_total": len(wrong),
        "white_noise_admitted": int(sum(bool(row["core_accepted"]) for row in white)),
        "white_noise_total": len(white),
        "constant_admitted": int(sum(bool(row["core_accepted"]) for row in constant)),
        "constant_total": len(constant),
        "formal_test_files_read": 0,
        "api_requests": 0,
        "next_allowed_stage": "s_a_s_b_smoke" if real_ok and not any(row["core_accepted"] for row in wrong + white + constant) else "failure_analysis_only",
    }
    write_json(OUT_DIR / "mt_private_v3_admission_audit_decision.json", decision)
    lines = [
        "# Private machine-tool v3 admission audit",
        "",
        "- Stage: zero-API inner-train audit only; formal IDs `7/8` were not read.",
        f"- Decision: `{decision['status']}`; next allowed stage: `{decision['next_allowed_stage']}`.",
        f"- Real-carrier required core admission rate: `{REAL_CORE_MIN_RATE:.2f}` per class and nonzero rate per source file.",
        f"- Wrong-label controls admitted: `{decision['wrong_label_admitted']}/{decision['wrong_label_total']}`.",
        f"- White-noise controls admitted: `{decision['white_noise_admitted']}/{decision['white_noise_total']}`.",
        f"- Constant controls admitted: `{decision['constant_admitted']}/{decision['constant_total']}`.",
        "",
        "## Real-carrier results",
        "",
        "| class | rate | source-file rates |",
        "|---|---:|---|",
    ]
    lines.extend(f"| {row['class_name']} | {row['core_admission_rate']:.3f} | `{json.dumps(row['source_rates'], sort_keys=True)}` |" for row in real_summary)
    lines.extend([
        "",
        "## Interpretation boundary",
        "",
        "The reused generic verifier and existing ExtraTrees identity check are exploratory admission components, not component-physics evidence. No machine speed, lead, sensor mounting, or current semantics are inferred by this audit.",
    ])
    (OUT_DIR / "mt_private_v3_admission_audit_report.md").write_text("\n".join(lines) + "\n")
    return decision


def _carrier_index(cls: str, attempt: int, context: Context) -> int:
    return int(stable_seed("mt_private_v3", "carrier", cls, attempt) % len(context.templates[cls]))


def render_s_a(cls: str, attempt: int, context: Context) -> tuple[np.ndarray, dict[str, Any]]:
    index = _carrier_index(cls, attempt, context)
    carrier = context.templates[cls][index]
    rng = np.random.default_rng(stable_seed("mt_private_v3", "s_a", cls, attempt))
    gains = context.profile[cls]["soft_gain"]
    std_gain = context.profile[cls]["std_gain"]
    output = np.empty_like(carrier, dtype=np.float64)
    for channel in range(len(MT_CHANNELS)):
        x = iaaft_surrogate(carrier[channel], rng, phase_strength=1.0)
        x = apply_soft_band_gain(x, gains[channel].tolist())
        x = x - x.mean()
        x = x / (x.std() + 1e-12) * (carrier[channel].std() * std_gain[channel])
        output[channel] = x + carrier[channel].mean()
    if not np.all(np.isfinite(output)):
        raise RuntimeError("S-A renderer produced non-finite values")
    return output.astype(np.float32), {
        "carrier_a_index": index,
        "carrier_a_source": str(context.sources[cls][index]),
        "carrier_b_index": "",
        "carrier_b_source": "",
        "alpha": "",
    }


def render_s_b(cls: str, attempt: int, context: Context) -> tuple[np.ndarray, dict[str, Any]]:
    n = len(context.templates[cls])
    first = _carrier_index(cls, attempt, context)
    second = int(stable_seed("mt_private_v3", "carrier_pair", cls, attempt) % n)
    if second == first:
        second = (second + 1) % n
    alpha = MIX_ALPHAS[attempt % len(MIX_ALPHAS)]
    output = alpha * context.templates[cls][first] + (1.0 - alpha) * context.templates[cls][second]
    if not np.all(np.isfinite(output)):
        raise RuntimeError("S-B renderer produced non-finite values")
    return output.astype(np.float32), {
        "carrier_a_index": first,
        "carrier_a_source": str(context.sources[cls][first]),
        "carrier_b_index": second,
        "carrier_b_source": str(context.sources[cls][second]),
        "alpha": alpha,
    }


def _renderer(method: str):
    if method == "s_a_directional":
        return render_s_a
    if method == "s_b_carrier_mix":
        return render_s_b
    raise ValueError(f"unknown method: {method}")


def _pool_dir(method: str, target_per_class: int) -> Path:
    return RUN_DIR / "pools" / method / f"n{target_per_class}"


def pool_manifest_path(method: str, target_per_class: int) -> Path:
    return _pool_dir(method, target_per_class) / "manifest.csv"


def row_is_accepted(row: dict[str, Any]) -> bool:
    """Interpret an in-memory boolean and a CSV-reloaded manifest consistently."""
    value = row["accepted"]
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value == "True":
            return True
        if value == "False":
            return False
    raise ValueError(f"invalid manifest accepted value: {value!r}")


def build_pool(context: Context, method: str, target_per_class: int) -> dict[str, Any]:
    if target_per_class not in {1, 5, 20}:
        raise ValueError("target_per_class must be one of 1, 5, 20")
    if target_per_class == 5 and not pool_is_balanced(method, 1):
        raise RuntimeError("five-per-class pool requires a completed one-per-class smoke")
    if target_per_class == 20 and not pool_is_balanced(method, 5):
        raise RuntimeError("twenty-per-class pool requires a completed five-per-class smoke")
    directory = _pool_dir(method, target_per_class)
    directory.mkdir(parents=True, exist_ok=True)
    manifest = pool_manifest_path(method, target_per_class)
    prior = read_csv(manifest)
    rows = list(prior)
    render = _renderer(method)
    for cls in MT_CLASSES:
        existing = [row for row in rows if row["class_name"] == cls]
        accepted = [row for row in existing if row_is_accepted(row)]
        hashes = {str(row["candidate_sha256"]) for row in accepted}
        done_attempts = {int(row["attempt"]) for row in existing}
        for attempt in range(MAX_ATTEMPTS_PER_CLASS):
            if len(accepted) >= target_per_class:
                break
            if attempt in done_attempts:
                continue
            window, provenance = render(cls, attempt, context)
            report = admit_candidate(window, cls, context.admission, hashes)
            relative = Path("candidates") / method / f"n{target_per_class}" / cls / f"attempt_{attempt:03d}.npy"
            path = RUN_DIR / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            np.save(path, window)
            row = {
                "method": method,
                "target_per_class": target_per_class,
                "class_name": cls,
                "attempt": attempt,
                "accepted": report["accepted"],
                "candidate_sha256": report["candidate_sha256"],
                "path": str(relative),
                "failure_reasons": "|".join(report["failure_reasons"]),
                "hard_gates_passed": report["hard_gates_passed"],
                "diversity_passed": report["diversity_passed"],
                "class_identity_passed": report["class_identity_passed"],
                "class_identity_prediction": report["class_identity_prediction"],
                "nearest_train_distance": report["nearest_train_distance"],
                "diversity_minimum": report["diversity_minimum"],
                "verifier_gates": json.dumps({name: bool(gate["passed"]) for name, gate in report["verifier"]["gates"].items()}, sort_keys=True),
                **provenance,
            }
            rows.append(row)
            if report["accepted"]:
                hashes.add(report["candidate_sha256"])
                accepted.append(row)
    write_csv(manifest, rows)
    selected: dict[str, list[dict[str, Any]]] = {}
    for cls in MT_CLASSES:
        selected[cls] = sorted((row for row in rows if row["class_name"] == cls and row_is_accepted(row)), key=lambda row: int(row["attempt"]))[:target_per_class]
    counts = {cls: len(selected[cls]) for cls in MT_CLASSES}
    decision = {
        "method": method,
        "target_per_class": target_per_class,
        "accepted_counts": counts,
        "balanced": bool(all(count == target_per_class for count in counts.values())),
        "attempt_ceiling_per_class": MAX_ATTEMPTS_PER_CLASS,
        "formal_test_files_read": 0,
        "api_requests": 0,
    }
    write_json(OUT_DIR / f"mt_private_v3_{method}_n{target_per_class}_pool_decision.json", decision)
    write_csv(OUT_DIR / f"mt_private_v3_{method}_n{target_per_class}_pool_manifest.csv", rows)
    return decision


def pool_is_balanced(method: str, target_per_class: int) -> bool:
    decision_path = OUT_DIR / f"mt_private_v3_{method}_n{target_per_class}_pool_decision.json"
    if not decision_path.exists():
        return False
    return bool(json.loads(decision_path.read_text()).get("balanced"))


S_C_API_LOG_FIELDS = [
    "request_index", "slot", "target_class", "round_id", "model", "prompt_hash",
    "response_hash", "http_status", "parse_status", "timestamp", "accepted",
    "rejection_reasons",
]


def s_c_dir() -> Path:
    return RUN_DIR / "s_c"


def s_c_state_path(cls: str, slot: int) -> Path:
    return s_c_dir() / "checkpoints" / f"{cls}_slot_{slot:02d}.json"


def s_c_default_state(cls: str, slot: int) -> dict[str, Any]:
    return {"class_name": cls, "slot": slot, "status": "pending", "history": []}


def s_c_load_state(cls: str, slot: int) -> dict[str, Any]:
    path = s_c_state_path(cls, slot)
    return json.loads(path.read_text()) if path.exists() else s_c_default_state(cls, slot)


def s_c_save_state(state: dict[str, Any]) -> None:
    write_json(s_c_state_path(state["class_name"], int(state["slot"])), state)


def s_c_load_states() -> list[dict[str, Any]]:
    return [s_c_load_state(cls, slot) for slot in range(POOL_N_SYN) for cls in MT_CLASSES]


def s_c_api_log_path() -> Path:
    return OUT_DIR / "mt_private_v3_s_c_api_log.csv"


def s_c_api_attempt_count() -> int:
    return len(read_csv(s_c_api_log_path()))


def append_s_c_api_log(row: dict[str, Any]) -> None:
    path = s_c_api_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fresh = not path.exists()
    with path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=S_C_API_LOG_FIELDS, lineterminator="\n", extrasaction="ignore")
        if fresh:
            writer.writeheader()
        writer.writerow({field: json_ready(row.get(field, "")) for field in S_C_API_LOG_FIELDS})


def parse_s_c_recipe_content(content: str) -> dict[str, Any]:
    """Decode the first JSON object without loosening the recipe schema."""
    decoder = json.JSONDecoder()
    for start, character in enumerate(content):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(content[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("response contains no JSON object")


def s_c_call_recipe_api(
    messages: list[dict[str, str]], request_index: int, slot: int, cls: str, round_id: int, last_call: list[float],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("MIMO_API_KEY")
    if not key:
        raise RuntimeError("Set DASHSCOPE_API_KEY or MIMO_API_KEY in the process environment")
    elapsed = time.monotonic() - last_call[0]
    if elapsed < LLM_MIN_INTERVAL:
        time.sleep(LLM_MIN_INTERVAL - elapsed)
    prompt_bytes = json.dumps(messages, sort_keys=True, separators=(",", ":")).encode("utf-8")
    prompt_hash = hashlib.sha256(prompt_bytes).hexdigest()
    status, text, parsed, parse_status = 0, "", None, "not_attempted"
    try:
        response = requests.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": LLM_MODEL, "messages": messages, "temperature": 0.65, "max_tokens": 1200,
                "enable_thinking": False, "chat_template_kwargs": {"enable_thinking": False},
            },
            timeout=300,
        )
        last_call[0] = time.monotonic()
        status, text = int(response.status_code), response.text
        if status == 200:
            content = response.json()["choices"][0]["message"]["content"]
            parsed = parse_s_c_recipe_content(content)
            parse_status = "json_object_ok"
        else:
            parse_status = "http_error"
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        last_call[0] = time.monotonic()
        parse_status = f"error:{type(exc).__name__}"
    return parsed, {
        "request_index": request_index, "slot": slot, "target_class": cls, "round_id": round_id,
        "model": LLM_MODEL, "prompt_hash": prompt_hash,
        "response_hash": hashlib.sha256(text.encode("utf-8")).hexdigest() if text else "",
        "http_status": status, "parse_status": parse_status,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "accepted": False, "rejection_reasons": "",
    }


def s_c_materials(context: Context) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    exemplar, differences = class_exemplar_statistics(context.dev, context.verifier)
    schema = recipe_schema(max(len(context.templates[cls]) for cls in MT_CLASSES))
    return exemplar, differences, schema


def s_c_prompt_messages(
    cls: str,
    context: Context,
    exemplar: dict[str, Any],
    differences: dict[str, Any],
    schema: dict[str, Any],
    round_id: int,
    feedback: dict[str, Any] | None,
) -> list[dict[str, str]]:
    """Use only frozen inner-train discriminative statistics in an S-C prompt."""
    messages = prompt_messages(cls, exemplar, differences, schema, round_id, feedback)
    payload = json.loads(messages[1]["content"])
    profile = context.profile[cls]
    payload["v3_discriminative_direction"] = {
        "soft_band_signed_effect": profile["soft_direction"],
        "channel_std_signed_effect": profile["std_direction"],
        "reference_directional_gain": profile["soft_gain"],
    }
    payload["s_c_generation_rule"] = (
        "Choose recipe band gains and channel standard-deviation multipliers that explicitly "
        "follow the target class signed discriminative directions while staying within the "
        "provided schema. These are train-only normalized effects, not physical frequencies."
    )
    payload["frozen_rules"].extend([
        "Do not infer machine metadata or physical frequencies from the effects.",
        "Do not copy a real carrier; the deterministic renderer will choose the allowed template.",
    ])
    messages[0]["content"] = (
        "You are an expert in multichannel CNC condition-monitoring signal synthesis. "
        "Return exactly one JSON recipe, and use only the supplied inner-train statistics."
    )
    messages[1]["content"] = json.dumps(json_ready(payload), ensure_ascii=False, separators=(",", ":"))
    return messages


def s_c_write_outputs(smoke: bool) -> dict[str, Any]:
    states = s_c_load_states()
    selected = [state for state in states if not smoke or int(state["slot"]) == 0]
    counts = {cls: sum(state["class_name"] == cls and state["status"] == "accepted" for state in selected) for cls in MT_CLASSES}
    target = 1 if smoke else POOL_N_SYN
    slot_rows, manifest_rows = [], []
    for state in selected:
        report = state.get("accepted_report", {})
        slot_rows.append({
            "class_name": state["class_name"], "slot": state["slot"], "status": state["status"],
            "rounds_attempted": len(state["history"]), "accepted": state["status"] == "accepted",
            "accepted_path": state.get("accepted_path", ""),
            "candidate_sha256": report.get("candidate_sha256", ""),
            "class_identity_prediction": report.get("class_identity_prediction", ""),
            "failure_reasons": "|".join(report.get("failure_reasons", [])),
        })
        if state["status"] == "accepted":
            manifest_rows.append({
                "method": "s_c_llm", "target_per_class": target, "class_name": state["class_name"],
                "slot": state["slot"], "accepted": True, "path": state["accepted_path"],
                "candidate_sha256": report.get("candidate_sha256", ""),
                "class_identity_prediction": report.get("class_identity_prediction", ""),
                "nearest_train_distance": report.get("nearest_train_distance", ""),
                "diversity_minimum": report.get("diversity_minimum", ""),
                "failure_reasons": "|".join(report.get("failure_reasons", [])),
            })
    decision = {
        "method": "s_c_llm", "target_per_class": target, "accepted_counts": counts,
        "balanced": bool(all(count == target for count in counts.values())),
        "api_requests": s_c_api_attempt_count(), "api_budget": S_C_API_BUDGET,
        "formal_test_files_read": 0,
        "next_allowed_stage": "s_c_pool_extension" if smoke and all(count == target for count in counts.values()) else "s_c_downstream" if all(count == target for count in counts.values()) else "failure_analysis_only",
    }
    stem = "mt_private_v3_s_c_smoke" if smoke else "mt_private_v3_s_c_llm_n20_pool"
    write_csv(OUT_DIR / f"{stem}_slots.csv", slot_rows)
    if not smoke:
        write_csv(OUT_DIR / f"{stem}_manifest.csv", manifest_rows)
    write_json(OUT_DIR / f"{stem}_decision.json", decision)
    return decision


def s_c_prepare(context: Context) -> dict[str, Any]:
    exemplar, differences, schema = s_c_materials(context)
    previews = []
    for cls in MT_CLASSES:
        messages = s_c_prompt_messages(cls, context, exemplar, differences, schema, 0, None)
        previews.extend([f"## {cls}", "", "```json", messages[1]["content"], "```", ""])
    (OUT_DIR / "mt_private_v3_s_c_prompt_preview.md").write_text(
        "# Private machine-tool v3 S-C prompt preview\n\n"
        "The prompts contain inner-train statistics only; no API request was made.\n\n" + "\n".join(previews)
    )
    write_json(OUT_DIR / "mt_private_v3_s_c_prepare.json", {
        "api_requests": s_c_api_attempt_count(), "api_budget": S_C_API_BUDGET,
        "smoke_request_cap": S_C_SMOKE_REQUESTS, "max_feedback_rounds": S_C_MAX_FEEDBACK_ROUNDS,
        "expansions_per_recipe": S_C_EXPANSIONS_PER_RECIPE, "formal_test_files_read": 0,
    })
    return json.loads((OUT_DIR / "mt_private_v3_s_c_prepare.json").read_text())


def generate_s_c_pool(context: Context, max_api_requests: int, smoke: bool) -> dict[str, Any]:
    if max_api_requests < 0 or max_api_requests > S_C_API_BUDGET:
        raise ValueError(f"S-C API request ceiling must be in [0,{S_C_API_BUDGET}]")
    if smoke and max_api_requests not in {S_C_SMOKE_REQUESTS, S_C_AMENDMENT_1_SMOKE_REQUESTS}:
        raise ValueError(f"S-C smoke request ceiling must be {S_C_SMOKE_REQUESTS} or {S_C_AMENDMENT_1_SMOKE_REQUESTS}")
    exemplar, differences, schema = s_c_materials(context)
    class_std = {cls: context.templates[cls].std(axis=(0, 2)) for cls in MT_CLASSES}
    accepted_hashes = {
        str(state["accepted_report"]["candidate_sha256"])
        for state in s_c_load_states()
        if state.get("status") == "accepted" and state.get("accepted_report", {}).get("candidate_sha256")
    }
    last_call = [0.0]
    permitted_slots = {0} if smoke else set(range(POOL_N_SYN))
    while s_c_api_attempt_count() < max_api_requests:
        states = [state for state in s_c_load_states() if int(state["slot"]) in permitted_slots]
        accepted_counts = Counter(state["class_name"] for state in states if state["status"] == "accepted")
        eligible = [state for state in states if state["status"] == "pending" and len(state["history"]) <= S_C_MAX_FEEDBACK_ROUNDS]
        if not eligible:
            break
        if smoke:
            eligible.sort(key=lambda state: (len(state["history"]), state["class_name"]))
        else:
            eligible.sort(key=lambda state: (accepted_counts[state["class_name"]], int(state["slot"]), state["class_name"]))
        state = eligible[0]
        cls, slot = state["class_name"], int(state["slot"])
        round_id = len(state["history"])
        feedback = state["history"][-1].get("feedback") if state["history"] else None
        messages = s_c_prompt_messages(cls, context, exemplar, differences, schema, round_id, feedback)
        raw_recipe, api_row = s_c_call_recipe_api(messages, s_c_api_attempt_count() + 1, slot, cls, round_id, last_call)
        record: dict[str, Any] = {"round_id": round_id, "api_request_index": api_row["request_index"], "attempts": []}
        recipe = None
        if raw_recipe is None:
            record["recipe_error"] = api_row["parse_status"]
            record["feedback"] = {"failed_gates": ["api_or_json"], "violations": []}
            api_row["rejection_reasons"] = "api_or_json"
        else:
            try:
                recipe = normalize_recipe(raw_recipe, cls, len(context.templates[cls]))
                record["recipe"] = recipe
                write_json(s_c_dir() / "recipes" / f"{cls}_slot_{slot:02d}_round_{round_id}.json", recipe)
            except (TypeError, ValueError) as exc:
                record["recipe_error"] = str(exc)
                record["feedback"] = {"failed_gates": ["recipe_schema"], "violations": []}
                api_row["rejection_reasons"] = "recipe_schema"
        first_accepted: dict[str, Any] | None = None
        if recipe is not None:
            for expansion_id in range(S_C_EXPANSIONS_PER_RECIPE):
                seed = stable_seed("mt_private_v3", "s_c", cls, slot, round_id, expansion_id)
                try:
                    window = render_mt_recipe(recipe, context.templates, class_std, seed)
                    report = admit_candidate(window, cls, context.admission, accepted_hashes)
                    report.update({"slot": slot, "round_id": round_id, "expansion_id": expansion_id, "seed": seed})
                    if report["accepted"] and first_accepted is None:
                        path = s_c_dir() / "accepted" / f"{cls}_slot_{slot:02d}.npy"
                        path.parent.mkdir(parents=True, exist_ok=True)
                        np.save(path, window)
                        state["accepted_path"] = str(path.relative_to(RUN_DIR))
                        state["accepted_report"] = report
                        first_accepted = report
                        accepted_hashes.add(report["candidate_sha256"])
                    elif report["accepted"]:
                        report["accepted"] = False
                        report["failure_reasons"] = ["slot_already_retained"]
                    else:
                        path = s_c_dir() / "rejected" / f"{cls}_slot_{slot:02d}_round_{round_id}_exp_{expansion_id}.npy"
                        path.parent.mkdir(parents=True, exist_ok=True)
                        np.save(path, window)
                except (RuntimeError, ValueError) as exc:
                    report = {
                        "slot": slot, "round_id": round_id, "expansion_id": expansion_id, "seed": seed,
                        "accepted": False, "failure_reasons": [f"render:{type(exc).__name__}"],
                    }
                record["attempts"].append(report)
                write_json(s_c_dir() / "attempts" / f"{cls}_slot_{slot:02d}_round_{round_id}_exp_{expansion_id}.json", report)
            if first_accepted is None:
                last_report = record["attempts"][-1]
                record["feedback"] = candidate_feedback(last_report) if "verifier" in last_report else {"failed_gates": last_report["failure_reasons"], "violations": []}
                api_row["rejection_reasons"] = "|".join(record["feedback"]["failed_gates"])
        if first_accepted is not None:
            state["status"] = "accepted"
            api_row["accepted"] = True
        elif round_id >= S_C_MAX_FEEDBACK_ROUNDS:
            state["status"] = "exhausted"
        state["history"].append(record)
        s_c_save_state(state)
        append_s_c_api_log(api_row)
    return s_c_write_outputs(smoke)


def load_s_c_pool() -> dict[str, np.ndarray]:
    if not pool_is_balanced("s_c_llm", POOL_N_SYN):
        raise RuntimeError("balanced S-C n=20 pool is unavailable")
    manifest = read_csv(OUT_DIR / "mt_private_v3_s_c_llm_n20_pool_manifest.csv")
    pools: dict[str, np.ndarray] = {}
    for cls in MT_CLASSES:
        rows = sorted((row for row in manifest if row["class_name"] == cls and row_is_accepted(row)), key=lambda row: int(row["slot"]))
        pools[cls] = np.stack([np.load(RUN_DIR / row["path"]) for row in rows]).astype(np.float32)
    return pools


def load_pool(method: str, target_per_class: int = POOL_N_SYN) -> dict[str, np.ndarray]:
    if method == "s_c_llm":
        if target_per_class != POOL_N_SYN:
            raise ValueError("S-C pool is frozen at n=20 per class")
        return load_s_c_pool()
    if not pool_is_balanced(method, target_per_class):
        raise RuntimeError(f"balanced {method} n={target_per_class} pool is unavailable")
    pools: dict[str, np.ndarray] = {}
    for cls in MT_CLASSES:
        rows = sorted((row for row in read_csv(pool_manifest_path(method, target_per_class)) if row["class_name"] == cls and row_is_accepted(row)), key=lambda row: int(row["attempt"]))[:target_per_class]
        pools[cls] = np.stack([np.load(RUN_DIR / row["path"]) for row in rows]).astype(np.float32)
    return pools


def holm_adjust(values: list[float]) -> list[float]:
    order = np.argsort(values)
    adjusted = np.zeros(len(values), dtype=float)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, (len(values) - rank) * values[index])
        adjusted[index] = min(running, 1.0)
    return adjusted.tolist()


def _append_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fresh = not path.exists()
    with path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        if fresh:
            writer.writeheader()
        writer.writerows([{key: json_ready(value) for key, value in row.items()} for row in rows])


DOWNSTREAM_FIELDS = ["method", "n_real", "n_syn", "seed", "train_sample_count", "acc", "macro_f1", *[f"f1_{cls}" for cls in MT_CLASSES], "confusion"]


def n_syn_for_n_real(n_real: int) -> int:
    try:
        return DOWNSTREAM_N_SYN_BY_N_REAL[n_real]
    except KeyError as exc:
        raise ValueError(f"no preregistered synthetic budget for n_real={n_real}") from exc


def run_downstream(context: Context, method: str) -> list[dict[str, Any]]:
    pool = load_pool(method)
    X_val, y_val, _, _, _, files_read = load_inner_validation()
    if any(any(file_id in name for file_id in FORBIDDEN_FILE_IDS) for name in files_read):
        raise RuntimeError("formal private-MT file was loaded")
    path = OUT_DIR / f"mt_private_v3_{method}_downstream.csv"
    prior = read_csv(path)
    done = {(row["method"], int(row["n_real"]), int(row["seed"])) for row in prior}
    class_std = {cls: context.templates[cls].std(axis=(0, 2)) for cls in MT_CLASSES}
    rows: list[dict[str, Any]] = []
    for n_real in DOWNSTREAM_N_REALS:
        n_syn = n_syn_for_n_real(n_real)
        static_x = np.concatenate([pool[cls][:n_syn] for cls in MT_CLASSES])
        static_y = np.concatenate([np.full(n_syn, ci, dtype=np.int64) for ci in range(len(MT_CLASSES))])
        for seed in range(DOWNSTREAM_SEEDS):
            X_real, y_real = sample_real_subset(context.dev.X_train, context.dev.y_train, n_real, seed)
            X_noise, y_noise = noise_augment(X_real, y_real, n_syn, seed, class_std)
            methods = {
                "real_only": (X_real, y_real),
                "noise_aug": (np.concatenate([X_real, X_noise]), np.concatenate([y_real, y_noise])),
                method: (np.concatenate([X_real, static_x]), np.concatenate([y_real, static_y])),
            }
            for method_name, (X_train, y_train) in methods.items():
                if (method_name, n_real, seed) in done:
                    continue
                X_train_norm, X_val_norm = normalize_train_val(X_train, X_val)
                model = train_cnn(X_train_norm.astype(np.float32), y_train, stable_seed("mt_private_v3", "cnn", method_name, n_real, seed))
                predicted = predict_cnn(model, X_val_norm.astype(np.float32))
                per_class = f1_score(y_val, predicted, labels=list(range(len(MT_CLASSES))), average=None, zero_division=0)
                rows.append({
                    "method": method_name,
                    "n_real": n_real,
                    "n_syn": n_syn if method_name != "real_only" else 0,
                    "seed": seed,
                    "train_sample_count": len(y_train),
                    "acc": float(accuracy_score(y_val, predicted)),
                    "macro_f1": float(f1_score(y_val, predicted, labels=list(range(len(MT_CLASSES))), average="macro", zero_division=0)),
                    **{f"f1_{cls}": float(per_class[ci]) for ci, cls in enumerate(MT_CLASSES)},
                    "confusion": json.dumps(
                        confusion_matrix(y_val, predicted, labels=list(range(len(MT_CLASSES)))).tolist(),
                        separators=(",", ":"),
                    ),
                })
                if len(rows) >= 6:
                    _append_csv(path, DOWNSTREAM_FIELDS, rows)
                    rows = []
    _append_csv(path, DOWNSTREAM_FIELDS, rows)
    return read_csv(path)


def summarize_downstream(method: str) -> dict[str, Any]:
    rows = read_csv(OUT_DIR / f"mt_private_v3_{method}_downstream.csv")
    if not rows:
        raise RuntimeError(f"no downstream rows available for {method}")
    frame = pd.DataFrame(rows)
    for column in ["n_real", "n_syn", "seed", "train_sample_count", "acc", "macro_f1", *[f"f1_{cls}" for cls in MT_CLASSES]]:
        frame[column] = pd.to_numeric(frame[column])
    summary_rows: list[dict[str, Any]] = []
    for (name, n_real), group in frame.groupby(["method", "n_real"], sort=True):
        summary_rows.append({
            "method": name,
            "n_real": int(n_real),
            "seeds": len(group),
            **{f"mean_{metric}": float(group[metric].mean()) for metric in ("acc", "macro_f1")},
            **{f"std_{metric}": float(group[metric].std(ddof=1)) for metric in ("acc", "macro_f1")},
        })
    write_csv(OUT_DIR / f"mt_private_v3_{method}_downstream_summary.csv", summary_rows)
    summary = pd.DataFrame(summary_rows).set_index(["method", "n_real"])
    cells, tests = [], []
    for n_real in DOWNSTREAM_N_REALS:
        for metric in ("acc", "macro_f1"):
            candidate = float(summary.loc[(method, n_real), f"mean_{metric}"])
            noise = float(summary.loc[("noise_aug", n_real), f"mean_{metric}"])
            cells.append({"n_real": n_real, "metric": metric, "candidate": candidate, "noise_aug": noise, "candidate_ge_noise": candidate >= noise})
            paired = frame[(frame.method == method) & (frame.n_real == n_real)][["seed", metric]].merge(frame[(frame.method == "noise_aug") & (frame.n_real == n_real)][["seed", metric]], on="seed", suffixes=("_candidate", "_noise")).sort_values("seed")
            delta = paired[f"{metric}_candidate"].to_numpy() - paired[f"{metric}_noise"].to_numpy()
            p_value = 1.0 if len(delta) == 0 or np.allclose(delta, 0) else float(wilcoxon(delta, alternative="greater", zero_method="zsplit").pvalue)
            tests.append({"n_real": n_real, "metric": metric, "comparison": f"{method}>noise_aug", "mean_delta": float(delta.mean()), "p_raw": p_value})
    adjusted = holm_adjust([row["p_raw"] for row in tests])
    for row, value in zip(tests, adjusted, strict=True):
        row["holm_q"] = value
    write_csv(OUT_DIR / f"mt_private_v3_{method}_wilcoxon_holm.csv", tests)
    decision = {
        "method": method,
        "status": "PASS" if sum(bool(row["candidate_ge_noise"]) for row in cells) >= 5 else "BLOCKED",
        "cells_at_least_noise_aug": int(sum(bool(row["candidate_ge_noise"]) for row in cells)),
        "total_cells": len(cells),
        "formal_test_files_read": 0,
        "api_requests": 0,
        "next_allowed_stage": "candidate_selection_or_s_e" if sum(bool(row["candidate_ge_noise"]) for row in cells) >= 5 else "conditional_s_c_or_failure_analysis",
        "cells": cells,
    }
    write_json(OUT_DIR / f"mt_private_v3_{method}_downstream_decision.json", decision)
    return decision


def write_prepare(context: Context) -> None:
    ensure_dirs()
    context.verifier.save(RUN_DIR / "mt_private_v3_inner_train_verifier_c90.json")
    write_json(OUT_DIR / "mt_private_v3_directional_profile.json", context.profile)
    write_json(OUT_DIR / "mt_private_v3_prepare.json", {
        "inner_train_file_ids": list(INNER_TRAIN_FILE_IDS),
        "inner_validation_file_id": INNER_VAL_FILE_ID,
        "forbidden_file_ids": sorted(FORBIDDEN_FILE_IDS),
        "api_requests": 0,
        "formal_test_files_read": 0,
        "renderer_constants": {
            "direction_gain_strength": DIRECTION_GAIN_STRENGTH,
            "direction_clip": DIRECTION_CLIP,
            "mix_alphas": list(MIX_ALPHAS),
            "max_attempts_per_class": MAX_ATTEMPTS_PER_CLASS,
        },
        "files_read": context.dev.files_read,
    })


def audit_passed() -> bool:
    path = OUT_DIR / "mt_private_v3_admission_audit_decision.json"
    return path.exists() and json.loads(path.read_text())["status"] == "PASS"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["prepare", "audit", "smoke", "pool", "s_c_prepare", "s_c_smoke", "s_c_smoke_amendment_1", "s_c_generate", "downstream", "summarize"], required=True)
    parser.add_argument("--method", choices=["s_a_directional", "s_b_carrier_mix", "s_c_llm"], default="s_a_directional")
    parser.add_argument("--target-per-class", type=int, default=None)
    parser.add_argument("--max-api-requests", type=int, default=S_C_API_BUDGET)
    args = parser.parse_args()
    ensure_dirs()
    context = build_context()
    write_prepare(context)
    if args.stage == "prepare":
        print(json.dumps({"status": "passed", "api_requests": 0, "formal_test_files_read": 0}, sort_keys=True))
        return
    if args.stage == "audit":
        print(json.dumps(run_admission_audit(context), sort_keys=True))
        return
    if args.stage == "s_c_prepare":
        print(json.dumps(s_c_prepare(context), sort_keys=True))
        return
    if not audit_passed():
        raise RuntimeError("v3 admission audit is not PASS; pool/downstream stages are prohibited")
    if args.stage == "s_c_smoke":
        print(json.dumps(generate_s_c_pool(context, S_C_SMOKE_REQUESTS, smoke=True), sort_keys=True))
        return
    if args.stage == "s_c_smoke_amendment_1":
        print(json.dumps(generate_s_c_pool(context, S_C_AMENDMENT_1_SMOKE_REQUESTS, smoke=True), sort_keys=True))
        return
    if args.stage == "s_c_generate":
        smoke_path = OUT_DIR / "mt_private_v3_s_c_smoke_decision.json"
        if not smoke_path.exists() or not json.loads(smoke_path.read_text()).get("balanced"):
            raise RuntimeError("S-C full generation requires a balanced committed S-C smoke")
        print(json.dumps(generate_s_c_pool(context, args.max_api_requests, smoke=False), sort_keys=True))
        return
    if args.stage == "smoke":
        if args.method == "s_c_llm":
            raise ValueError("use --stage s_c_smoke for S-C")
        print(json.dumps(build_pool(context, args.method, 1), sort_keys=True))
        return
    if args.stage == "pool":
        if args.method == "s_c_llm":
            raise ValueError("use --stage s_c_generate for S-C")
        if args.target_per_class not in {5, 20}:
            raise ValueError("pool stage requires --target-per-class 5 or 20")
        print(json.dumps(build_pool(context, args.method, args.target_per_class), sort_keys=True))
        return
    if args.stage == "downstream":
        print(json.dumps({"rows": len(run_downstream(context, args.method))}, sort_keys=True))
        return
    print(json.dumps(summarize_downstream(args.method), sort_keys=True))


if __name__ == "__main__":
    main()
