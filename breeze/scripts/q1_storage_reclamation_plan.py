#!/usr/bin/env python3
"""Build an exact, non-destructive storage reclamation manifest."""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GIB = 1024**3
MUTCM_ROOT = ROOT / "data" / "MU-TCM face-milling dataset"
MUTCM_ARCHIVE = MUTCM_ROOT / "full_dataset.7z"
MUTCM_ARCHIVE_SHA256 = "c653f3dc2e762c9bfd21e8a9248cc12494ff6ae6e5991f93c4b6845a50f37223"
IMS_ROOT = ROOT / "data" / "ims" / "raw"
MUTCM_LEDGER = ROOT / "analysis" / "q1_mutcm_duplicate_ledger_2026-07-17.csv"
IMS_LEDGER = ROOT / "analysis" / "q1_ims_archive_relationships_2026-07-17.csv"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def checked_file(path: Path, byte_count: int) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    observed = path.stat().st_size
    if observed != byte_count:
        raise ValueError(f"size drift for {path}: expected={byte_count} observed={observed}")


def build_manifest(
    mutcm_rows: list[dict[str, str]], ims_rows: list[dict[str, str]]
) -> list[dict]:
    manifest: list[dict] = []
    if not MUTCM_ARCHIVE.is_file():
        raise FileNotFoundError(MUTCM_ARCHIVE)
    for row in mutcm_rows:
        if row["status"] != "DUPLICATE":
            continue
        target = ROOT / row["small_path"]
        byte_count = int(row["local_bytes"])
        if row["local_sha256"] != row["archive_sha256"]:
            raise ValueError(f"MU-TCM ledger hash mismatch: {target}")
        checked_file(target, byte_count)
        manifest.append(
            {
                "batch": "MUTCM_EXACT_SMALL_SUBSET_DUPLICATES",
                "target": target.relative_to(ROOT).as_posix(),
                "bytes": byte_count,
                "target_sha256": row["local_sha256"],
                "retained_path": MUTCM_ARCHIVE.relative_to(ROOT).as_posix(),
                "retained_sha256": MUTCM_ARCHIVE_SHA256,
                "restore_member": row["archive_member"],
                "restore_recipe": "BSDTAR_ARCHIVE_MEMBER_STREAM_ATOMIC",
                "risk": "LOW_EXACT_ARCHIVE_MEMBER_DUPLICATE",
                "state": "PRESERVE_PENDING_TRANSPARENT_ARCHIVE_READER",
            }
        )

    outer = next(row for row in ims_rows if row["status"] == "CANONICAL_OUTER_WRAPPER")
    outer_path = IMS_ROOT / outer["artifact"]
    checked_file(outer_path, int(outer["bytes"]))
    duplicates = [row for row in ims_rows if row["status"] == "EXACT_NESTED_DUPLICATE"]
    duplicates.sort(key=lambda row: (0 if row["artifact"] == "IMS.7z" else 1, row["artifact"]))
    for row in duplicates:
        target = IMS_ROOT / row["artifact"]
        byte_count = int(row["bytes"])
        checked_file(target, byte_count)
        restore_member = row["contained_path"]
        manifest.append(
            {
                "batch": "IMS_EXACT_NESTED_DUPLICATES",
                "target": target.relative_to(ROOT).as_posix(),
                "bytes": byte_count,
                "target_sha256": row["sha256"],
                "retained_path": outer_path.relative_to(ROOT).as_posix(),
                "retained_sha256": outer["sha256"],
                "restore_member": restore_member,
                "restore_recipe": "OUTER_ZIP_THEN_BSDTAR_7Z_ATOMIC",
                "risk": "LOW_EXACT_NESTED_DUPLICATE",
                "state": "PRESERVE_PENDING_TRANSPARENT_ARCHIVE_READER",
            }
        )
    return manifest


def allocated_bytes(path: Path) -> int:
    result = subprocess.run(
        ["du", "-sk", str(path)], check=True, capture_output=True, text=True
    )
    return int(result.stdout.split()[0]) * 1024


def atomic_write_csv(output: Path, rows: list[dict]) -> None:
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
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "batch",
                    "target",
                    "bytes",
                    "target_sha256",
                    "retained_path",
                    "retained_sha256",
                    "restore_member",
                    "restore_recipe",
                    "risk",
                    "state",
                ],
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()


def render_report(rows: list[dict], current_bytes: int) -> str:
    by_batch: dict[str, list[dict]] = {}
    for row in rows:
        by_batch.setdefault(str(row["batch"]), []).append(row)
    mutcm = by_batch["MUTCM_EXACT_SMALL_SUBSET_DUPLICATES"]
    ims = by_batch["IMS_EXACT_NESTED_DUPLICATES"]
    reclaim_bytes = sum(int(row["bytes"]) for row in rows)
    predicted = current_bytes - reclaim_bytes
    return f"""# Q1 storage reclamation plan — 2026-07-17

## Decision

The audit identified a smallest byte-preserving reclamation set: two batches
contain {len(rows)} files totaling {reclaim_bytes / GIB:.6f} GiB. The current
allocated project size is {current_bytes / GIB:.6f} GiB; subtracting logical
candidate bytes would predict {predicted / GIB:.6f} GiB, below the 47 GiB working
watermark. This is not an execution decision: follow-up dependency inspection
found scripts that directly open the duplicate paths, and deletion authorization
was rejected. Both batches are therefore preserved.

No deletion has been performed. Every target is locked as
`PRESERVE_PENDING_TRANSPARENT_ARCHIVE_READER` in
`analysis/q1_storage_reclamation_manifest_2026-07-17.csv`.

## Audited but deferred batch A — MU-TCM exact small-subset copies

- Targets: {len(mutcm)} files, {sum(int(row['bytes']) for row in mutcm) / GIB:.6f} GiB.
- Evidence: each target and its mapped `full_dataset/` archive member has equal
  byte count and full SHA-256 in `q1_mutcm_duplicate_ledger_2026-07-17.csv`.
- Preserved: `full_dataset.7z` (archive SHA-256 `{mutcm[0]['retained_sha256']}`), both
  size-different subset CSVs, and both platform-metadata files.
- Restore: stream the named `restore_member` from the retained 7z with system
  `bsdtar` to a same-directory temporary file, verify `target_sha256`, then
  atomically rename it to `target`.
- Operational dependency: `audit_mutcm_small_subset.py` directly opens
  `small_subset`; a transparent archive reader or tested automatic materializer
  is required before reconsideration.
- Decision: preserve after the user declined deletion authorization.

## Audited but deferred batch B — IMS exact nested copies

- Targets: {len(ims)} files, {sum(int(row['bytes']) for row in ims) / GIB:.6f} GiB.
- Evidence: full stream hashes prove that retained `4_Bearings.zip` contains the
  exact `IMS.7z`, which contains the exact three RAR files and PDF.
- Preserved: `data/ims/raw/4_Bearings.zip` with SHA-256
  `{ims[0]['retained_sha256']}` and every audit manifest.
- Restore chain: atomically stream `4. Bearings/IMS.7z` from the ZIP and verify
  its hash; extract each named member from that 7z using system `bsdtar` into a
  temporary path, verify its hash, then atomically rename.
- Risk: low exact nested duplication. The Set-3 semantic README conflict remains
  documented and is not altered by retaining the byte-identical outer wrapper.
- Operational dependency: `ims_manifest.py` directly opens the three local RARs
  and README; exact recoverability alone does not keep that command runnable.
- Decision: preserve until a direct-from-wrapper reader is implemented and tested.

## Explicit exclusions

- `breeze/runs/`: 1.406 GiB of exact file-level candidates stay retained because
  removing files can break complete run-root provenance even when content exists
  elsewhere.
- DIRG NPZs (4.685 GiB): retained until checkpointed, atomic regeneration exists.
- XJTU archive (4.139 GiB): retained as the only local raw source.
- MU-TCM `full_dataset/`, original archive, virtual environment, `.bbl`, user-dirty
  `tmp/`, and formal release roots: retained.
- Convention caches (0.003 GiB): omitted because they add deletion risk without
  materially changing the storage constraint.

## Execution and verification contract

1. Before each batch, recompute every target hash and every retained-source hash;
   any drift aborts the entire batch.
2. Delete only manifest paths, without a glob and without deleting directories.
3. Append each completed target to `analysis/q1_storage_ledger.csv` so the batch
   is resumable after interruption.
4. After each batch, rerun its source audit, verify all non-target paths, inspect
   Git status, and measure both project allocation and filesystem free space.
5. If the first batch already satisfies the measured watermark, the second can
   be skipped; the core scientific target is never exchanged for extra space.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "analysis" / "q1_storage_reclamation_plan_2026-07-17.md",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "analysis" / "q1_storage_reclamation_manifest_2026-07-17.csv",
    )
    args = parser.parse_args()
    rows = build_manifest(read_rows(MUTCM_LEDGER), read_rows(IMS_LEDGER))
    current_bytes = allocated_bytes(ROOT)
    atomic_write_csv(args.manifest.resolve(), rows)
    from q1_storage_audit import atomic_write_text

    atomic_write_text(args.report.resolve(), render_report(rows, current_bytes))
    print(
        f"reclamation plan PASS: files={len(rows)} "
        f"candidate_gib={sum(int(row['bytes']) for row in rows) / GIB:.6f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
