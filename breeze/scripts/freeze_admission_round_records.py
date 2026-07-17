#!/usr/bin/env python3
"""Freeze and validate PU round-level admission records without rerunning them.

The raw round JSON files are local run artifacts.  This script hashes every
file, reconstructs the first feasible feedback round for every proposal slot,
and checks the result against the immutable Phase-A v2 slot summary.  Outputs
are deterministic and write-once: an existing file is accepted only when its
bytes exactly match the newly reconstructed content.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Iterable


REPO = Path(__file__).resolve().parents[2]
DEFAULT_RECORDS = REPO / "breeze" / "runs" / "rescreen_v2_full" / "records"
DEFAULT_SUMMARY = (
    REPO
    / "breeze"
    / "results"
    / "phaseA_v2_frozen_2026-07-06"
    / "breeze"
    / "runs"
    / "rescreen_v2_full"
    / "slot_summary.csv"
)
DEFAULT_OUTPUT = (
    REPO / "breeze" / "results" / "admission_round_freeze_2026-07-17"
)
CLASS_ORDER = ("healthy", "OR", "IR")
EXPECTED_SLOTS_PER_CLASS = 150
EXPECTED_SLOTS = 450
EXPECTED_FINAL_ADMITTED = 286
MAX_FEEDBACK_ROUND = 3


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_relative(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def strict_bool(value: str) -> bool:
    if value == "True":
        return True
    if value == "False":
        return False
    raise RuntimeError(f"invalid frozen Boolean: {value!r}")


def load_slot_summary(path: Path) -> dict[tuple[str, int], dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    expected_columns = {
        "class",
        "slot",
        "accepted_before_diversity",
        "n_candidates",
        "n_feasible_expansions",
    }
    if set(rows[0]) != expected_columns:
        raise RuntimeError(f"unexpected slot-summary columns: {set(rows[0])}")
    parsed: dict[tuple[str, int], dict[str, Any]] = {}
    for row in rows:
        key = (row["class"], int(row["slot"]))
        if key in parsed:
            raise RuntimeError(f"duplicate frozen slot-summary row: {key}")
        parsed[key] = {
            "accepted": strict_bool(row["accepted_before_diversity"]),
            "n_candidates": int(row["n_candidates"]),
            "n_feasible_expansions": int(row["n_feasible_expansions"]),
        }
    expected_keys = {
        (class_name, slot)
        for class_name in CLASS_ORDER
        for slot in range(EXPECTED_SLOTS_PER_CLASS)
    }
    if set(parsed) != expected_keys:
        missing = sorted(expected_keys - set(parsed))[:5]
        extra = sorted(set(parsed) - expected_keys)[:5]
        raise RuntimeError(
            f"slot-summary key mismatch: missing={missing}, extra={extra}"
        )
    return parsed


def parse_record(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        record = json.load(handle)
    expected_keys = {
        "class",
        "slot",
        "source_json",
        "selected",
        "candidates",
        "expansions",
    }
    if set(record) != expected_keys:
        raise RuntimeError(f"{path}: unexpected record keys {set(record)}")
    class_name = record["class"]
    slot = record["slot"]
    if class_name not in CLASS_ORDER or not isinstance(slot, int):
        raise RuntimeError(f"{path}: invalid class/slot {class_name!r}/{slot!r}")
    expected_name = f"{class_name}_{slot:04d}.json"
    if path.name != expected_name:
        raise RuntimeError(f"{path}: filename does not match record ({expected_name})")

    candidates = record["candidates"]
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= 4:
        raise RuntimeError(f"{path}: invalid candidate count {len(candidates)}")
    rounds = []
    feasible_candidates = []
    for candidate in candidates:
        round_index = candidate.get("round")
        feasible = candidate.get("feasible")
        if not isinstance(round_index, int) or not isinstance(feasible, bool):
            raise RuntimeError(f"{path}: invalid candidate round/feasible value")
        rounds.append(round_index)
        if feasible:
            feasible_candidates.append(candidate)
    if rounds != list(range(len(candidates))) or rounds[-1] > MAX_FEEDBACK_ROUND:
        raise RuntimeError(f"{path}: non-consecutive feedback rounds {rounds}")

    first = feasible_candidates[0] if feasible_candidates else None
    selected = record["selected"]
    if selected != first:
        raise RuntimeError(
            f"{path}: selected candidate is not the first feasible round"
        )
    first_pass_round = None if first is None else int(first["round"])

    expansions = record["expansions"]
    if not isinstance(expansions, list):
        raise RuntimeError(f"{path}: expansions must be a list")
    for expansion in expansions:
        if not isinstance(expansion.get("feasible"), bool):
            raise RuntimeError(f"{path}: invalid expansion feasible value")
    n_feasible_expansions = sum(bool(item["feasible"]) for item in expansions)

    return {
        "class": class_name,
        "slot": slot,
        "n_candidates": len(candidates),
        "n_expansions": len(expansions),
        "n_feasible_expansions": n_feasible_expansions,
        "first_pass_round": first_pass_round,
        "final_admitted": first_pass_round is not None,
        "candidate_rounds": ";".join(map(str, rounds)),
    }


def csv_bytes(rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_once(path: Path, content: bytes) -> None:
    if path.exists():
        if path.read_bytes() != content:
            raise RuntimeError(f"refusing to overwrite changed frozen output: {path}")
        return
    path.write_bytes(content)


def build_freeze(
    records_dir: Path, slot_summary_path: Path
) -> tuple[dict[str, bytes], dict[str, Any]]:
    if not records_dir.is_dir():
        raise FileNotFoundError(records_dir)
    paths = sorted(records_dir.glob("*.json"))
    if len(paths) != EXPECTED_SLOTS:
        raise RuntimeError(
            f"expected {EXPECTED_SLOTS} round JSON files, found {len(paths)}"
        )
    other_files = sorted(path for path in records_dir.iterdir() if path.is_file() and path.suffix != ".json")
    if other_files:
        raise RuntimeError(f"unexpected non-JSON record files: {other_files[:5]}")

    frozen_summary = load_slot_summary(slot_summary_path)
    manifest_rows = []
    aggregate_rows = []
    seen: set[tuple[str, int]] = set()
    for path in paths:
        parsed = parse_record(path)
        key = (parsed["class"], parsed["slot"])
        if key in seen:
            raise RuntimeError(f"duplicate round record: {key}")
        seen.add(key)
        expected = frozen_summary[key]
        observed = {
            "accepted": parsed["final_admitted"],
            "n_candidates": parsed["n_candidates"],
            "n_feasible_expansions": parsed["n_feasible_expansions"],
        }
        if observed != expected:
            raise RuntimeError(
                f"{path}: aggregate differs from frozen slot summary: "
                f"observed={observed}, expected={expected}"
            )
        file_hash = sha256(path)
        manifest_rows.append(
            {
                "record_path": repo_relative(path),
                "class": parsed["class"],
                "slot": parsed["slot"],
                "size_bytes": path.stat().st_size,
                "sha256": file_hash,
            }
        )
        aggregate_rows.append(
            {
                "class": parsed["class"],
                "slot": parsed["slot"],
                "candidate_rounds": parsed["candidate_rounds"],
                "n_candidates": parsed["n_candidates"],
                "n_expansions": parsed["n_expansions"],
                "n_feasible_expansions": parsed["n_feasible_expansions"],
                "first_pass_round": (
                    "" if parsed["first_pass_round"] is None else parsed["first_pass_round"]
                ),
                "final_admitted": parsed["final_admitted"],
                "record_sha256": file_hash,
            }
        )

    expected_keys = set(frozen_summary)
    if seen != expected_keys:
        missing = sorted(expected_keys - seen)[:5]
        extra = sorted(seen - expected_keys)[:5]
        raise RuntimeError(f"round-record key mismatch: missing={missing}, extra={extra}")

    class_rank = {name: index for index, name in enumerate(CLASS_ORDER)}
    manifest_rows.sort(key=lambda row: (class_rank[row["class"]], row["slot"]))
    aggregate_rows.sort(key=lambda row: (class_rank[row["class"]], row["slot"]))
    cumulative_rows = []
    previous = {class_name: 0 for class_name in CLASS_ORDER}
    previous["all"] = 0
    for feedback_round in range(MAX_FEEDBACK_ROUND + 1):
        for class_name in (*CLASS_ORDER, "all"):
            subset = (
                aggregate_rows
                if class_name == "all"
                else [row for row in aggregate_rows if row["class"] == class_name]
            )
            cumulative = sum(
                row["first_pass_round"] != ""
                and int(row["first_pass_round"]) <= feedback_round
                for row in subset
            )
            total = len(subset)
            cumulative_rows.append(
                {
                    "feedback_round_k": feedback_round,
                    "class": class_name,
                    "newly_admitted": cumulative - previous[class_name],
                    "cumulative_admitted": cumulative,
                    "total_slots": total,
                    "cumulative_rate": f"{cumulative / total:.12f}",
                }
            )
            previous[class_name] = cumulative

    final_admitted = sum(row["final_admitted"] for row in aggregate_rows)
    if len(aggregate_rows) != EXPECTED_SLOTS or final_admitted != EXPECTED_FINAL_ADMITTED:
        raise RuntimeError(
            f"admission assertion failed: slots={len(aggregate_rows)}, "
            f"admitted={final_admitted}"
        )
    class_final = {
        class_name: sum(
            row["final_admitted"] for row in aggregate_rows if row["class"] == class_name
        )
        for class_name in CLASS_ORDER
    }
    validation = {
        "status": "passed",
        "freeze_date": "2026-07-17",
        "source_records_directory": repo_relative(records_dir),
        "canonical_slot_summary": repo_relative(slot_summary_path),
        "canonical_slot_summary_sha256": sha256(slot_summary_path),
        "assertions": {
            "record_json_count": len(paths),
            "unique_slot_count": len(seen),
            "slots_per_class": {
                class_name: sum(row["class"] == class_name for row in aggregate_rows)
                for class_name in CLASS_ORDER
            },
            "final_admitted_slots": final_admitted,
            "final_admitted_by_class": class_final,
            "selected_equals_first_feasible_candidate": True,
            "slot_summary_rows_match_exactly": True,
            "feedback_rounds": list(range(MAX_FEEDBACK_ROUND + 1)),
        },
        "interpretation": (
            "Counts describe all archived PU proposal slots. They are population "
            "accounting for one frozen pool-generation run, not uncertainty over "
            "independent LLM pool generations."
        ),
    }
    outputs = {
        "round_records_manifest.csv": csv_bytes(
            manifest_rows,
            ["record_path", "class", "slot", "size_bytes", "sha256"],
        ),
        "slot_first_pass_round.csv": csv_bytes(
            aggregate_rows,
            [
                "class",
                "slot",
                "candidate_rounds",
                "n_candidates",
                "n_expansions",
                "n_feasible_expansions",
                "first_pass_round",
                "final_admitted",
                "record_sha256",
            ],
        ),
        "cumulative_admission_by_class.csv": csv_bytes(
            cumulative_rows,
            [
                "feedback_round_k",
                "class",
                "newly_admitted",
                "cumulative_admitted",
                "total_slots",
                "cumulative_rate",
            ],
        ),
        "validation_report.json": json_bytes(validation),
    }
    return outputs, validation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records-dir", type=Path, default=DEFAULT_RECORDS)
    parser.add_argument("--slot-summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    outputs, validation = build_freeze(
        args.records_dir.resolve(), args.slot_summary.resolve()
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        write_once(args.output_dir / name, content)
    print(json.dumps(validation["assertions"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
