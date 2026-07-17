#!/usr/bin/env python3
"""Verify, delete, or atomically restore only the audited Q1 storage manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import shutil
import subprocess
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GIB = 1024**3
MANIFEST = ROOT / "analysis" / "q1_storage_reclamation_manifest_2026-07-17.csv"
LEDGER = ROOT / "analysis" / "q1_storage_ledger.csv"
AUTHORIZATION_TOKEN = "USER_AUTHORIZED_Q1_EXACT_RECLAMATION_2026_07_17"
DELETION_ELIGIBLE_STATE = "PENDING_EXPLICIT_AUTHORIZATION"
PRESERVE_STATE = "PRESERVE_PENDING_TRANSPARENT_ARCHIVE_READER"
MUTCM_BATCH = "MUTCM_EXACT_SMALL_SUBSET_DUPLICATES"
IMS_BATCH = "IMS_EXACT_NESTED_DUPLICATES"
EXPECTED = {
    MUTCM_BATCH: (30, 4_091_504_602),
    IMS_BATCH: (5, 2_136_916_387),
}
ALLOWED_TARGET_ROOTS = {
    MUTCM_BATCH: ROOT / "data" / "MU-TCM face-milling dataset" / "small_subset",
    IMS_BATCH: ROOT / "data" / "ims" / "raw",
}
EXPECTED_RETAINED = {
    MUTCM_BATCH: ROOT / "data" / "MU-TCM face-milling dataset" / "full_dataset.7z",
    IMS_BATCH: ROOT / "data" / "ims" / "raw" / "4_Bearings.zip",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def resolve_inside(relative: str, boundary: Path) -> Path:
    candidate = (ROOT / relative).resolve()
    if not candidate.is_relative_to(boundary.resolve()):
        raise ValueError(f"path escapes audited boundary: {relative}")
    return candidate


def validate_manifest(rows: list[dict[str, str]], *, require_all: bool = True) -> None:
    required = {
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
    }
    if not rows:
        raise ValueError("manifest is empty")
    if set(rows[0]) != required:
        raise ValueError("manifest schema drift")
    observed_batches = set(row["batch"] for row in rows)
    unknown = sorted(observed_batches - set(EXPECTED))
    if unknown:
        raise ValueError(f"unknown manifest batches: {unknown}")
    if require_all and observed_batches != set(EXPECTED):
        raise ValueError(f"manifest is missing an audited batch: {observed_batches}")
    for batch in sorted(observed_batches):
        expected_count, expected_bytes = EXPECTED[batch]
        selected = [row for row in rows if row["batch"] == batch]
        observed_bytes = sum(int(row["bytes"]) for row in selected)
        if (len(selected), observed_bytes) != (expected_count, expected_bytes):
            raise ValueError(
                f"manifest batch drift: {batch} expected={(expected_count, expected_bytes)} "
                f"observed={(len(selected), observed_bytes)}"
            )
        for row in selected:
            if row["state"] not in {DELETION_ELIGIBLE_STATE, PRESERVE_STATE}:
                raise ValueError(f"unexpected manifest state: {row['target']}")
            resolve_inside(row["target"], ALLOWED_TARGET_ROOTS[batch])
            retained = resolve_inside(row["retained_path"], ROOT / "data")
            if retained != EXPECTED_RETAINED[batch].resolve():
                raise ValueError(f"retained-source drift: {row['target']}")
            if len(row["target_sha256"]) != 64 or len(row["retained_sha256"]) != 64:
                raise ValueError(f"invalid hash length: {row['target']}")


def sha256_file(path: Path, label: str) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    next_heartbeat = 256 * 1024**2
    started = time.monotonic()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024**2):
            digest.update(chunk)
            total += len(chunk)
            if total >= next_heartbeat:
                elapsed = max(time.monotonic() - started, 1e-9)
                print(
                    f"hash heartbeat: {label} read_gib={total / GIB:.3f} "
                    f"rate_mib_s={total / 1024**2 / elapsed:.1f}",
                    flush=True,
                )
                while total >= next_heartbeat:
                    next_heartbeat += 256 * 1024**2
    return digest.hexdigest(), total


def completed_deletions(ledger: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {
        row["target"]: row
        for row in ledger
        if row.get("action") == "DELETE" and row.get("status") == "COMPLETE"
    }


def preflight(rows: list[dict[str, str]], ledger: list[dict[str, str]]) -> None:
    validate_manifest(rows, require_all=False)
    recorded = completed_deletions(ledger)
    retained_cache: dict[str, str] = {}
    for row in rows:
        retained_path = ROOT / row["retained_path"]
        if row["retained_path"] not in retained_cache:
            observed_hash, _bytes = sha256_file(retained_path, row["retained_path"])
            if observed_hash != row["retained_sha256"]:
                raise ValueError(f"retained-source hash drift: {retained_path}")
            retained_cache[row["retained_path"]] = observed_hash
        target = ROOT / row["target"]
        if not target.exists():
            recorded_row = recorded.get(row["target"])
            if not recorded_row or recorded_row.get("sha256") != row["target_sha256"]:
                raise FileNotFoundError(f"unrecorded missing target: {target}")
            continue
        if target.stat().st_size != int(row["bytes"]):
            raise ValueError(f"target size drift: {target}")
        observed_hash, observed_bytes = sha256_file(target, row["target"])
        if observed_bytes != int(row["bytes"]) or observed_hash != row["target_sha256"]:
            raise ValueError(f"target hash drift: {target}")
    print(
        f"preflight PASS: targets={len(rows)} retained_sources={len(retained_cache)}",
        flush=True,
    )


def atomic_write_ledger(path: Path, rows: list[dict[str, str]]) -> None:
    fields = ["timestamp_utc", "action", "batch", "target", "bytes", "sha256", "status"]
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        newline="",
        encoding="utf-8",
        prefix=path.name,
        suffix=".tmp",
        dir=path.parent,
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
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def append_ledger(
    ledger_path: Path, ledger: list[dict[str, str]], row: dict[str, str], action: str
) -> None:
    ledger.append(
        {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "batch": row["batch"],
            "target": row["target"],
            "bytes": row["bytes"],
            "sha256": row["target_sha256"],
            "status": "COMPLETE",
        }
    )
    atomic_write_ledger(ledger_path, ledger)


def delete_rows(
    rows: list[dict[str, str]], ledger_path: Path, authorization_token: str
) -> None:
    if authorization_token != AUTHORIZATION_TOKEN:
        raise PermissionError("exact explicit authorization token is required")
    blocked = [row["target"] for row in rows if row["state"] != DELETION_ELIGIBLE_STATE]
    if blocked:
        raise PermissionError(
            "manifest is preservation-locked pending transparent archive readers: "
            f"{len(blocked)} targets"
        )
    ledger = read_csv(ledger_path)
    preflight(rows, ledger)
    recorded = completed_deletions(ledger)
    reclaimed = 0
    for index, row in enumerate(rows, start=1):
        target = ROOT / row["target"]
        if not target.exists() and row["target"] in recorded:
            print(f"delete resume: {index}/{len(rows)} already complete {row['target']}", flush=True)
            reclaimed += int(row["bytes"])
            continue
        target.unlink()
        append_ledger(ledger_path, ledger, row, "DELETE")
        reclaimed += int(row["bytes"])
        print(
            f"delete heartbeat: {index}/{len(rows)} reclaimed_gib={reclaimed / GIB:.3f} "
            f"target={row['target']}",
            flush=True,
        )


def atomic_stream_process(command: list[str], target: Path, expected_hash: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w+b", prefix=target.name, suffix=".restore.tmp", dir=target.parent, delete=False
    )
    temporary = Path(handle.name)
    try:
        with handle:
            process = subprocess.Popen(command, stdout=handle)
            last_heartbeat = time.monotonic()
            while process.poll() is None:
                time.sleep(1)
                if time.monotonic() - last_heartbeat >= 10:
                    print(
                        f"restore heartbeat: target={target.relative_to(ROOT)} "
                        f"written_gib={temporary.stat().st_size / GIB:.3f}",
                        flush=True,
                    )
                    last_heartbeat = time.monotonic()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, command)
            handle.flush()
            os.fsync(handle.fileno())
        observed_hash, _bytes = sha256_file(temporary, f"restore:{target.relative_to(ROOT)}")
        if observed_hash != expected_hash:
            raise ValueError(f"restored hash mismatch: {target}")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_stream_zip_member(
    archive: Path, member: str, target: Path, expected_hash: str
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w+b", prefix=target.name, suffix=".restore.tmp", dir=target.parent, delete=False
    )
    temporary = Path(handle.name)
    try:
        digest = hashlib.sha256()
        with handle, zipfile.ZipFile(archive) as source_zip, source_zip.open(member) as source:
            while chunk := source.read(8 * 1024**2):
                handle.write(chunk)
                digest.update(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        if digest.hexdigest() != expected_hash:
            raise ValueError(f"restored ZIP member hash mismatch: {target}")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def restore_rows(rows: list[dict[str, str]], ledger_path: Path) -> None:
    validate_manifest(rows, require_all=False)
    ledger = read_csv(ledger_path)
    for index, row in enumerate(rows, start=1):
        target = ROOT / row["target"]
        if target.exists():
            observed_hash, _bytes = sha256_file(target, f"existing:{row['target']}")
            if observed_hash != row["target_sha256"]:
                raise ValueError(f"existing restore target hash drift: {target}")
            continue
        if row["batch"] == MUTCM_BATCH:
            atomic_stream_process(
                ["bsdtar", "-xOf", str(ROOT / row["retained_path"]), row["restore_member"]],
                target,
                row["target_sha256"],
            )
        elif row["target"].endswith("/IMS.7z"):
            atomic_stream_zip_member(
                ROOT / row["retained_path"],
                row["restore_member"],
                target,
                row["target_sha256"],
            )
        else:
            ims_archive = ROOT / "data" / "ims" / "raw" / "IMS.7z"
            if not ims_archive.is_file():
                raise FileNotFoundError("IMS.7z must be restored before its members")
            atomic_stream_process(
                ["bsdtar", "-xOf", str(ims_archive), row["restore_member"]],
                target,
                row["target_sha256"],
            )
        append_ledger(ledger_path, ledger, row, "RESTORE")
        print(f"restore complete: {index}/{len(rows)} {row['target']}", flush=True)


def select_batch(rows: list[dict[str, str]], batch: str) -> list[dict[str, str]]:
    if batch == "all":
        return rows
    mapping = {"mutcm": MUTCM_BATCH, "ims": IMS_BATCH}
    return [row for row in rows if row["batch"] == mapping[batch]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "delete", "restore"))
    parser.add_argument("--batch", choices=("mutcm", "ims", "all"), default="all")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--ledger", type=Path, default=LEDGER)
    parser.add_argument("--authorization-token", default="")
    args = parser.parse_args()
    all_rows = read_csv(args.manifest.resolve())
    validate_manifest(all_rows)
    rows = select_batch(all_rows, args.batch)
    if args.mode == "preflight":
        preflight(rows, read_csv(args.ledger.resolve()))
    elif args.mode == "delete":
        delete_rows(rows, args.ledger.resolve(), args.authorization_token)
    else:
        restore_rows(rows, args.ledger.resolve())


if __name__ == "__main__":
    main()
