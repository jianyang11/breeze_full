#!/usr/bin/env python3
"""Audit the MU-TCM source archive against the extracted synced signals.

The audit is intentionally read-only for source data.  It hashes the original
archive, reconciles the archive member list with the extraction manifest and
local directory, and streams three seeded samples directly from the archive
for byte-level SHA-256 comparison.  Large reads emit progress heartbeats.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
import os
import random
import selectors
import subprocess
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_ROOT = ROOT / "data" / "MU-TCM face-milling dataset"
DEFAULT_ARCHIVE = DEFAULT_DATASET_ROOT / "full_dataset.7z"
DEFAULT_SYNCED_DIR = DEFAULT_DATASET_ROOT / "full_dataset" / "signals_synced"
DEFAULT_SIZE_MANIFEST = (
    ROOT
    / "breeze"
    / "results"
    / "mutcm_v2_synced_2026-07-09"
    / "mutcm_v2_synced_file_sizes.csv"
)
SYNCED_PREFIX = "full_dataset/signals_synced/"
MIB = 1024**2
GIB = 1024**3


def sha256_file(path: Path, *, label: str, heartbeat_mib: int = 512) -> tuple[str, int]:
    """Hash one file in chunks and report deterministic byte-count heartbeats."""

    digest = hashlib.sha256()
    total = 0
    next_heartbeat = heartbeat_mib * MIB
    started = time.monotonic()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * MIB):
            digest.update(chunk)
            total += len(chunk)
            if total >= next_heartbeat:
                elapsed = max(time.monotonic() - started, 1e-9)
                print(
                    f"hash heartbeat: label={label} read_gib={total / GIB:.3f} "
                    f"rate_mib_s={total / MIB / elapsed:.1f}",
                    flush=True,
                )
                next_heartbeat += heartbeat_mib * MIB
    print(f"hash complete: label={label} bytes={total}", flush=True)
    return digest.hexdigest(), total


def archive_members(archive: Path, bsdtar: str) -> list[str]:
    """Return the exact archive member names, failing on a corrupt directory."""

    result = subprocess.run(
        [bsdtar, "-tf", str(archive)],
        check=True,
        capture_output=True,
        text=True,
    )
    members = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    print(f"archive directory complete: members={len(members)}", flush=True)
    return members


def load_size_manifest(path: Path) -> dict[str, int]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"file_name", "exists", "size_bytes"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"invalid size manifest schema: {path}")
    if any(row["exists"].strip().lower() != "true" for row in rows):
        raise ValueError(f"size manifest contains missing files: {path}")
    parsed = {row["file_name"]: int(row["size_bytes"]) for row in rows}
    if len(parsed) != len(rows):
        raise ValueError(f"size manifest contains duplicate names: {path}")
    return parsed


def choose_large_samples(
    sizes: dict[str, int], *, seed: int, count: int = 3
) -> tuple[list[str], int]:
    """Seed-sample files from the largest size quartile without replacement."""

    if len(sizes) < count:
        raise ValueError("not enough files for requested sample count")
    ordered = sorted(sizes, key=lambda name: (-sizes[name], name))
    population_size = max(count, math.ceil(len(ordered) * 0.25))
    population = ordered[:population_size]
    selected = random.Random(seed).sample(population, count)
    selected.sort()
    return selected, population_size


def sha256_archive_members(
    archive: Path,
    members: list[str],
    expected_sizes: dict[str, int],
    *,
    bsdtar: str,
    heartbeat_mib: int = 512,
) -> dict[str, tuple[str, int]]:
    """Hash ordered members in one archive scan using exact byte boundaries.

    ``bsdtar`` emits selected members in archive order.  Callers therefore pass
    ``members`` in that same order.  Manifest sizes define unambiguous member
    boundaries in the concatenated stdout stream.
    """

    if not members or set(members) != set(expected_sizes):
        raise ValueError("members and expected_sizes must be the same non-empty set")
    if any(expected_sizes[member] < 0 for member in members):
        raise ValueError("expected member sizes must be non-negative")

    process = subprocess.Popen(
        [bsdtar, "-xOf", str(archive), *members],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    assert process.stderr is not None
    digests = {member: hashlib.sha256() for member in members}
    observed = {member: 0 for member in members}
    member_index = 0
    total = 0
    next_heartbeat = heartbeat_mib * MIB
    started = time.monotonic()
    next_time_heartbeat = started + 10.0
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    try:
        stdout_open = True
        while stdout_open:
            events = selector.select(timeout=1.0)
            for key, _ in events:
                chunk = os.read(key.fileobj.fileno(), 8 * MIB)
                if not chunk:
                    selector.unregister(process.stdout)
                    stdout_open = False
                    break
                view = memoryview(chunk)
                while view:
                    if member_index >= len(members):
                        raise ValueError("archive emitted bytes beyond manifest boundaries")
                    current = members[member_index]
                    remaining = expected_sizes[current] - observed[current]
                    take = min(len(view), remaining)
                    digests[current].update(view[:take])
                    observed[current] += take
                    view = view[take:]
                    if observed[current] == expected_sizes[current]:
                        print(
                            f"archive member boundary: member={Path(current).name} "
                            f"bytes={observed[current]}",
                            flush=True,
                        )
                        member_index += 1
                total += len(chunk)
                if total >= next_heartbeat:
                    elapsed = max(time.monotonic() - started, 1e-9)
                    print(
                        f"archive byte heartbeat: members={len(members)} "
                        f"read_gib={total / GIB:.3f} "
                        f"rate_mib_s={total / MIB / elapsed:.1f}",
                        flush=True,
                    )
                    while total >= next_heartbeat:
                        next_heartbeat += heartbeat_mib * MIB
            now = time.monotonic()
            if now >= next_time_heartbeat:
                print(
                    f"archive process heartbeat: members={len(members)} "
                    f"elapsed_s={now - started:.1f} output_gib={total / GIB:.3f} "
                    f"state={'running' if process.poll() is None else 'exited'}",
                    flush=True,
                )
                next_time_heartbeat = now + 10.0
        return_code = process.wait()
        stderr = process.stderr.read().decode("utf-8", errors="replace").strip()
    finally:
        selector.close()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    if return_code != 0:
        raise RuntimeError(
            f"bsdtar failed for {members} with code {return_code}: {stderr}"
        )
    incomplete = {
        member: (observed[member], expected_sizes[member])
        for member in members
        if observed[member] != expected_sizes[member]
    }
    if incomplete or member_index != len(members):
        raise ValueError(f"archive stream ended outside manifest boundaries: {incomplete}")
    print(
        f"archive stream complete: members={len(members)} bytes={total}",
        flush=True,
    )
    return {
        member: (digests[member].hexdigest(), observed[member]) for member in members
    }


def atomic_write_csv(output: Path, rows: list[dict[str, str | int]]) -> None:
    fields = [
        "file_name",
        "archive_member",
        "manifest_bytes",
        "local_bytes",
        "archive_bytes",
        "local_sha256",
        "archive_sha256",
        "status",
    ]
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


def atomic_write_text(output: Path, content: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=output.name,
        suffix=".tmp",
        dir=output.parent,
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()


def audit(
    archive: Path,
    synced_dir: Path,
    size_manifest_path: Path,
    *,
    bsdtar: str,
    seed: int,
) -> tuple[dict[str, str | int], list[dict[str, str | int]]]:
    for required in (archive, synced_dir, size_manifest_path):
        if not required.exists():
            raise FileNotFoundError(required)

    archive_sha256, archive_bytes = sha256_file(archive, label=archive.name)
    members = archive_members(archive, bsdtar)
    archive_synced = {
        member.removeprefix(SYNCED_PREFIX)
        for member in members
        if member.startswith(SYNCED_PREFIX) and member.lower().endswith(".mat")
    }
    manifest_sizes = load_size_manifest(size_manifest_path)
    local_sizes = {path.name: path.stat().st_size for path in synced_dir.glob("*.mat")}

    manifest_names = set(manifest_sizes)
    local_names = set(local_sizes)
    names_match = archive_synced == manifest_names == local_names
    sizes_match = local_sizes == manifest_sizes
    if not names_match:
        raise ValueError(
            "synced file-name sets differ: "
            f"archive_only={sorted(archive_synced - manifest_names)} "
            f"manifest_only={sorted(manifest_names - archive_synced)} "
            f"local_only={sorted(local_names - manifest_names)} "
            f"manifest_missing_local={sorted(manifest_names - local_names)}"
        )
    if not sizes_match:
        mismatches = {
            name: (manifest_sizes.get(name), local_sizes.get(name))
            for name in sorted(manifest_names | local_names)
            if manifest_sizes.get(name) != local_sizes.get(name)
        }
        raise ValueError(f"manifest/local size mismatch: {mismatches}")

    selected, population_size = choose_large_samples(manifest_sizes, seed=seed)
    local_hashes: dict[str, tuple[str, int]] = {}
    for index, name in enumerate(selected, start=1):
        print(f"local sample {index}/{len(selected)} start: {name}", flush=True)
        local_hashes[name] = sha256_file(
            synced_dir / name, label=f"local:{name}"
        )
    selected_set = set(selected)
    ordered_members = [
        member
        for member in members
        if member.startswith(SYNCED_PREFIX)
        and member.removeprefix(SYNCED_PREFIX) in selected_set
    ]
    expected_sizes = {
        member: manifest_sizes[member.removeprefix(SYNCED_PREFIX)]
        for member in ordered_members
    }
    print(
        f"joint archive sample start: members={len(ordered_members)} "
        f"expected_gib={sum(expected_sizes.values()) / GIB:.3f}",
        flush=True,
    )
    archive_hashes = sha256_archive_members(
        archive, ordered_members, expected_sizes, bsdtar=bsdtar
    )

    rows: list[dict[str, str | int]] = []
    for name in selected:
        member = f"{SYNCED_PREFIX}{name}"
        local_sha256, local_bytes = local_hashes[name]
        streamed_sha256, streamed_bytes = archive_hashes[member]
        status = (
            "PASS"
            if local_sha256 == streamed_sha256
            and local_bytes == streamed_bytes == manifest_sizes[name]
            else "FAIL"
        )
        rows.append(
            {
                "file_name": name,
                "archive_member": member,
                "manifest_bytes": manifest_sizes[name],
                "local_bytes": local_bytes,
                "archive_bytes": streamed_bytes,
                "local_sha256": local_sha256,
                "archive_sha256": streamed_sha256,
                "status": status,
            }
        )
    if any(row["status"] != "PASS" for row in rows):
        raise ValueError("one or more sampled archive members failed byte-level comparison")

    summary: dict[str, str | int] = {
        "archive_path": archive.relative_to(ROOT).as_posix(),
        "archive_bytes": archive_bytes,
        "archive_sha256": archive_sha256,
        "archive_member_count": len(members),
        "archive_synced_mat_count": len(archive_synced),
        "manifest_count": len(manifest_sizes),
        "local_count": len(local_sizes),
        "seed": seed,
        "large_population_count": population_size,
        "sample_count": len(rows),
        "status": "PASS",
    }
    return summary, rows


def render_report(
    summary: dict[str, str | int],
    rows: list[dict[str, str | int]],
    *,
    size_manifest_path: Path,
) -> str:
    sample_lines = "\n".join(
        f"| `{row['file_name']}` | {int(row['manifest_bytes']) / GIB:.3f} | "
        f"`{str(row['local_sha256'])[:16]}…` | {row['status']} |"
        for row in rows
    )
    return f"""# MU-TCM source archive audit — 2026-07-17

## Verdict

**{summary['status']}**. The original archive directory, the recorded extraction
manifest, and the local `signals_synced` directory contain the same
{summary['manifest_count']} MAT file names. Every local file size equals its
recorded extraction size. Three files sampled without replacement from the
largest size quartile were streamed directly from the archive; `bsdtar`
decompression completed successfully and every streamed SHA-256 equals the
corresponding extracted-file SHA-256.

This establishes tested reconstructability of the retained synced subset; it
does not claim that untested archive members have been exhaustively rehashed.

## Archive identity

- Path: `{summary['archive_path']}`
- Bytes: {summary['archive_bytes']}
- SHA-256: `{summary['archive_sha256']}`
- Archive members: {summary['archive_member_count']}
- Synced MAT members: {summary['archive_synced_mat_count']}
- Size manifest: `{size_manifest_path.relative_to(ROOT).as_posix()}`
- Manifest/local counts: {summary['manifest_count']} / {summary['local_count']}

## Deterministic sample rule

- Sampling frame: largest quartile by manifest byte size
  ({summary['large_population_count']} of {summary['manifest_count']} files).
- RNG seed: `{summary['seed']}`.
- Sample size: {summary['sample_count']} without replacement.
- Integrity test: archive-member decompression exit status, streamed byte count,
  and SHA-256 equality against the extracted file.

| file | size (GiB) | matched SHA-256 prefix | status |
|---|---:|---|---|
{sample_lines}

## Rebuild implication

The 67-file synced directory can be regenerated selectively from the retained
archive member prefix `full_dataset/signals_synced/`. Any reclamation remains a
separate, explicitly authorized action; this audit deletes nothing.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--synced-dir", type=Path, default=DEFAULT_SYNCED_DIR)
    parser.add_argument("--size-manifest", type=Path, default=DEFAULT_SIZE_MANIFEST)
    parser.add_argument("--bsdtar", default="bsdtar")
    parser.add_argument("--seed", type=int, default=20260717)
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "analysis" / "q1_mutcm_archive_audit_2026-07-17.md",
    )
    parser.add_argument(
        "--checksums",
        type=Path,
        default=ROOT / "analysis" / "q1_mutcm_archive_checksums_2026-07-17.csv",
    )
    args = parser.parse_args()
    summary, rows = audit(
        args.archive.resolve(),
        args.synced_dir.resolve(),
        args.size_manifest.resolve(),
        bsdtar=args.bsdtar,
        seed=args.seed,
    )
    atomic_write_csv(args.checksums.resolve(), rows)
    atomic_write_text(
        args.report.resolve(),
        render_report(summary, rows, size_manifest_path=args.size_manifest.resolve()),
    )
    print(f"audit PASS: report={args.report.resolve()}", flush=True)
    print(f"audit PASS: checksums={args.checksums.resolve()}", flush=True)


if __name__ == "__main__":
    main()
