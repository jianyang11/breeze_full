#!/usr/bin/env python3
"""Inventory BREEZE run artifacts and prove exact duplicate candidates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "breeze" / "runs"
TRACKED_FROZEN = (
    ROOT
    / "breeze"
    / "results"
    / "phaseA_v2_frozen_2026-07-06"
    / "breeze"
    / "runs"
)
GIB = 1024**3
TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".json",
    ".csv",
    ".yaml",
    ".yml",
    ".toml",
    ".tex",
    ".py",
}

# Frozen by analysis/reproducibility_inventory_2026-07-16.md.
PRIMARY_RELEASE_ROOTS = {
    "phaseB_cwru_within_load0_llm_full_v1_combined",
    "phaseB_cwru_within_load0_rule_pilot_v1",
    "milling_berkeley_v2_binary_formal_2026-07-08_v11_repair_eq_coherent",
    "milling_berkeley_v2_binary_formal_2026-07-08_rule_random",
    "rescreen_v2_full",
}


def root_name(path: Path) -> str:
    relative = path.relative_to(RUNS)
    return relative.parts[0]


def classify_root(name: str, mention_count: int) -> str:
    lower = name.lower()
    if name in PRIMARY_RELEASE_ROOTS:
        return "PRIMARY_RELEASE_REQUIRED"
    if name == "phaseA_v2_balanced":
        return "TRACKED_FROZEN_COPY"
    if any(token in lower for token in ("smoke", "pilot", "prototype")):
        return "DEVELOPMENT_SMOKE_OR_PILOT"
    if mention_count:
        return "REFERENCED_LEGACY_EVIDENCE"
    if Path(name).suffix:
        return "TOP_LEVEL_RUN_RECORD"
    return "DEVELOPMENT_UNCLASSIFIED"


def hash_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024**2):
            digest.update(chunk)
            total += len(chunk)
    return digest.hexdigest(), total


def tracked_text_corpus() -> list[str]:
    import subprocess

    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    )
    corpus: list[str] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        path = ROOT / raw.decode("utf-8")
        if (
            path.is_file()
            and path.suffix.lower() in TEXT_SUFFIXES
            and path.stat().st_size <= 10 * 1024**2
            and not path.is_relative_to(RUNS)
        ):
            corpus.append(path.read_text(encoding="utf-8", errors="replace"))
    return corpus


def count_root_mentions(names: list[str], corpus: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name in names:
        escaped = re.escape(name)
        pattern = re.compile(rf"(?<![A-Za-z0-9_.-])(?:breeze/)?runs/{escaped}(?![A-Za-z0-9_.-])")
        counts[name] = sum(len(pattern.findall(text)) for text in corpus)
    return counts


def choose_keeper(entries: list[dict[str, str | int]]) -> dict[str, str | int]:
    primary = [
        row
        for row in entries
        if row["scope"] == "runs" and row["root"] in PRIMARY_RELEASE_ROOTS
    ]
    if primary:
        return sorted(primary, key=lambda row: str(row["path"]))[0]
    frozen = [row for row in entries if row["scope"] == "tracked_frozen"]
    if frozen:
        return sorted(frozen, key=lambda row: str(row["path"]))[0]
    run_rows = [row for row in entries if row["scope"] == "runs"]
    if not run_rows:
        raise ValueError("duplicate group has no run or frozen entry")
    return sorted(run_rows, key=lambda row: str(row["path"]))[0]


def atomic_write_csv(output: Path, fields: list[str], rows: list[dict]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        newline="",
        encoding="utf-8",
        prefix=output.name,
        suffix=".tmp",
        dir=output.parent,
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()


def scan_files() -> list[dict[str, str | int]]:
    entries: list[tuple[str, Path]] = [
        ("runs", path) for path in sorted(RUNS.rglob("*")) if path.is_file()
    ]
    if TRACKED_FROZEN.exists():
        entries.extend(
            ("tracked_frozen", path)
            for path in sorted(TRACKED_FROZEN.rglob("*"))
            if path.is_file()
        )
    rows: list[dict[str, str | int]] = []
    cumulative_bytes = 0
    next_byte_heartbeat = 256 * 1024**2
    started = time.monotonic()
    for index, (scope, path) in enumerate(entries, start=1):
        digest, byte_count = hash_file(path)
        cumulative_bytes += byte_count
        if index % 1000 == 0 or cumulative_bytes >= next_byte_heartbeat:
            elapsed = max(time.monotonic() - started, 1e-9)
            print(
                f"runs hash heartbeat: files={index}/{len(entries)} "
                f"read_gib={cumulative_bytes / GIB:.3f} "
                f"rate_mib_s={cumulative_bytes / 1024**2 / elapsed:.1f}",
                flush=True,
            )
            while cumulative_bytes >= next_byte_heartbeat:
                next_byte_heartbeat += 256 * 1024**2
        root = root_name(path) if scope == "runs" else "__tracked_frozen__"
        rows.append(
            {
                "scope": scope,
                "path": path.relative_to(ROOT).as_posix(),
                "root": root,
                "bytes": byte_count,
                "sha256": digest,
                "suffix": path.suffix.lower() or "<none>",
                "duplicate_group": "",
                "duplicate_role": "UNIQUE",
            }
        )
    print(
        f"runs hash complete: files={len(entries)} read_gib={cumulative_bytes / GIB:.3f}",
        flush=True,
    )
    return rows


def audit_runs() -> tuple[dict[str, str | int], list[dict], list[dict], list[dict]]:
    rows = scan_files()
    run_rows = [row for row in rows if row["scope"] == "runs"]
    roots = sorted({str(row["root"]) for row in run_rows})
    mentions = count_root_mentions(roots, tracked_text_corpus())

    groups: dict[tuple[int, str], list[dict]] = defaultdict(list)
    for row in rows:
        groups[(int(row["bytes"]), str(row["sha256"]))].append(row)
    duplicate_rows: list[dict] = []
    candidate_paths: set[str] = set()
    group_index = 0
    for (byte_count, digest), entries in sorted(
        groups.items(), key=lambda item: (-item[0][0], item[0][1])
    ):
        if len(entries) < 2:
            continue
        group_index += 1
        group_id = f"D{group_index:05d}"
        keeper = choose_keeper(entries)
        for row in entries:
            row["duplicate_group"] = group_id
            is_keeper = row is keeper
            if is_keeper:
                role = "KEEPER_PRIMARY" if row["root"] in PRIMARY_RELEASE_ROOTS else "KEEPER"
            elif row["scope"] == "tracked_frozen":
                role = "FROZEN_ADDITIONAL_COPY"
            elif row["root"] in PRIMARY_RELEASE_ROOTS:
                role = "PRESERVE_PRIMARY_ADDITIONAL_COPY"
            else:
                role = "EXACT_DUPLICATE_CANDIDATE"
                candidate_paths.add(str(row["path"]))
            row["duplicate_role"] = role
            duplicate_rows.append(
                {
                    "group": group_id,
                    "bytes": byte_count,
                    "sha256": digest,
                    "scope": row["scope"],
                    "root": row["root"],
                    "path": row["path"],
                    "role": role,
                    "keeper_path": keeper["path"],
                }
            )

    root_rows: list[dict] = []
    for root in roots:
        selected = [row for row in run_rows if row["root"] == root]
        suffixes = Counter(str(row["suffix"]) for row in selected)
        candidate_bytes = sum(
            int(row["bytes"]) for row in selected if str(row["path"]) in candidate_paths
        )
        category = classify_root(root, mentions[root])
        deletion_state = (
            "PRESERVE"
            if category == "PRIMARY_RELEASE_REQUIRED"
            else (
                "EXACT_DUPLICATE_FILES_ONLY_PENDING_AUTHORIZATION"
                if candidate_bytes
                else "REVIEW_NOT_AUTOMATIC"
            )
        )
        root_rows.append(
            {
                "root": root,
                "bytes": sum(int(row["bytes"]) for row in selected),
                "file_count": len(selected),
                "npz_count": suffixes[".npz"],
                "npy_count": suffixes[".npy"],
                "json_count": suffixes[".json"],
                "csv_count": suffixes[".csv"],
                "tracked_reference_mentions": mentions[root],
                "category": category,
                "exact_duplicate_candidate_bytes": candidate_bytes,
                "deletion_state": deletion_state,
            }
        )
    root_rows.sort(key=lambda row: (-int(row["bytes"]), str(row["root"])))

    candidate_bytes = sum(
        int(row["bytes"]) for row in run_rows if str(row["path"]) in candidate_paths
    )
    primary_rows = [row for row in run_rows if row["root"] in PRIMARY_RELEASE_ROOTS]
    summary: dict[str, str | int] = {
        "run_files": len(run_rows),
        "run_bytes": sum(int(row["bytes"]) for row in run_rows),
        "root_count": len(roots),
        "duplicate_group_count": group_index,
        "exact_duplicate_candidate_files": len(candidate_paths),
        "exact_duplicate_candidate_bytes": candidate_bytes,
        "primary_files": len(primary_rows),
        "primary_bytes": sum(int(row["bytes"]) for row in primary_rows),
        "status": "PASS",
    }
    return summary, run_rows, root_rows, duplicate_rows


def render_report(summary: dict[str, str | int], root_rows: list[dict]) -> str:
    category_counts = Counter(str(row["category"]) for row in root_rows)
    category_lines = "\n".join(
        f"- {category}: {count} top-level entries"
        for category, count in sorted(category_counts.items())
    )
    return f"""# `breeze/runs` storage and provenance audit — 2026-07-17

## Verdict

**{summary['status']}**. All {summary['run_files']} files under {summary['root_count']}
top-level entries were read and SHA-256 hashed ({int(summary['run_bytes']) / GIB:.3f} GiB).
Exact-content grouping found {summary['duplicate_group_count']} duplicate groups.
After prioritizing the five release-required roots and tracked Phase-A frozen
copies as keepers, {summary['exact_duplicate_candidate_files']} non-primary files
({int(summary['exact_duplicate_candidate_bytes']) / GIB:.3f} GiB) are proven
exact-copy candidates.

No directory is considered duplicate because its name looks similar. Candidate
status requires complete SHA-256 equality and a designated retained copy.

## Preservation boundary

The five roots named by `analysis/reproducibility_inventory_2026-07-16.md` are
hard-preserved: CWRU LLM/rule, Berkeley formal LLM/rule-random, and PU detailed
rescreen records. Together they contain {summary['primary_files']} files and
{int(summary['primary_bytes']) / GIB:.3f} GiB. Their ignored arrays/recipes are
release evidence and must not be removed merely because tracked numerical
summaries exist.

Root categories:

{category_lines}

`DEVELOPMENT_SMOKE_OR_PILOT` is a provenance category, not proof of
reconstructability. Non-duplicate smoke/API/recipe records remain retained
until their generating code, inputs, seeds, and provider boundary are audited.

## Action boundary

Only file-level `EXACT_DUPLICATE_CANDIDATE` rows may enter the reclamation plan.
Primary-release files are preserved even when another identical copy exists.
No deletion was performed; every proposed removal still requires explicit user
authorization and a post-batch hash/path check.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "analysis" / "q1_runs_storage_audit_2026-07-17.md",
    )
    parser.add_argument(
        "--files",
        type=Path,
        default=ROOT / "analysis" / "q1_runs_file_hashes_2026-07-17.csv",
    )
    parser.add_argument(
        "--roots",
        type=Path,
        default=ROOT / "analysis" / "q1_runs_root_inventory_2026-07-17.csv",
    )
    parser.add_argument(
        "--duplicates",
        type=Path,
        default=ROOT / "analysis" / "q1_runs_duplicate_groups_2026-07-17.csv",
    )
    args = parser.parse_args()
    summary, files, roots, duplicates = audit_runs()
    atomic_write_csv(
        args.files.resolve(),
        [
            "scope",
            "path",
            "root",
            "bytes",
            "sha256",
            "suffix",
            "duplicate_group",
            "duplicate_role",
        ],
        files,
    )
    atomic_write_csv(
        args.roots.resolve(),
        [
            "root",
            "bytes",
            "file_count",
            "npz_count",
            "npy_count",
            "json_count",
            "csv_count",
            "tracked_reference_mentions",
            "category",
            "exact_duplicate_candidate_bytes",
            "deletion_state",
        ],
        roots,
    )
    atomic_write_csv(
        args.duplicates.resolve(),
        ["group", "bytes", "sha256", "scope", "root", "path", "role", "keeper_path"],
        duplicates,
    )
    from q1_storage_audit import atomic_write_text

    atomic_write_text(args.report.resolve(), render_report(summary, roots))
    print(
        f"runs audit PASS: roots={summary['root_count']} files={summary['run_files']} "
        f"candidate_gib={int(summary['exact_duplicate_candidate_bytes']) / GIB:.3f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
