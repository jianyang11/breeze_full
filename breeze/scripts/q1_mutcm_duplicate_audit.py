#!/usr/bin/env python3
"""Prove which MU-TCM small-subset files duplicate the full source archive.

Every local small-subset file is mapped by relative path to the corresponding
``full_dataset/`` archive member.  Size equality is checked before any hashing;
all same-size candidates are then streamed in one solid-archive pass and
compared by SHA-256.  The script never deletes or modifies research data.
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from q1_storage_audit import (  # noqa: E402
    DEFAULT_ARCHIVE,
    DEFAULT_DATASET_ROOT,
    GIB,
    ROOT,
    archive_members,
    atomic_write_text,
    sha256_archive_members,
    sha256_file,
)


DEFAULT_SMALL_ROOT = DEFAULT_DATASET_ROOT / "small_subset"
FULL_PREFIX = "full_dataset/"
PLATFORM_METADATA_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}


def archive_member_sizes(archive: Path, bsdtar: str) -> dict[str, int]:
    """Parse exact uncompressed member sizes from ``bsdtar -tvf``."""

    result = subprocess.run(
        [bsdtar, "-tvf", str(archive)],
        check=True,
        capture_output=True,
        text=True,
    )
    sizes: dict[str, int] = {}
    for line in result.stdout.splitlines():
        fields = line.split(maxsplit=8)
        if len(fields) != 9:
            raise ValueError(f"unexpected bsdtar verbose-listing line: {line!r}")
        name = fields[8]
        size = int(fields[4])
        if name in sizes:
            raise ValueError(f"duplicate archive member name: {name}")
        sizes[name] = size
    if not sizes:
        raise ValueError(f"archive listing is empty: {archive}")
    print(f"archive size listing complete: members={len(sizes)}", flush=True)
    return sizes


def map_small_files(small_root: Path) -> dict[str, Path]:
    mapped: dict[str, Path] = {}
    for path in sorted(candidate for candidate in small_root.rglob("*") if candidate.is_file()):
        member = f"{FULL_PREFIX}{path.relative_to(small_root).as_posix()}"
        if member in mapped:
            raise ValueError(f"duplicate mapped member: {member}")
        mapped[member] = path
    if not mapped:
        raise ValueError(f"small-subset directory contains no files: {small_root}")
    return mapped


def ledger_path(path: Path) -> str:
    """Use repository-relative paths in production and absolute fixture paths."""

    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)


def atomic_write_rows(output: Path, rows: list[dict[str, str | int]]) -> None:
    fields = [
        "small_path",
        "archive_member",
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


def audit_duplicates(
    archive: Path, small_root: Path, *, bsdtar: str
) -> tuple[dict[str, int | str], list[dict[str, str | int]]]:
    if not archive.is_file():
        raise FileNotFoundError(archive)
    if not small_root.is_dir():
        raise FileNotFoundError(small_root)

    ordered_archive_members = archive_members(archive, bsdtar)
    archive_sizes = archive_member_sizes(archive, bsdtar)
    mapped = map_small_files(small_root)
    auxiliary = {
        member for member, path in mapped.items() if path.name in PLATFORM_METADATA_NAMES
    }
    research_members = set(mapped) - auxiliary
    missing = sorted(research_members - set(archive_sizes))
    same_size = {
        member
        for member, path in mapped.items()
        if member in research_members
        and member in archive_sizes
        and path.stat().st_size == archive_sizes[member]
    }
    ordered_candidates = [
        member for member in ordered_archive_members if member in same_size
    ]
    if set(ordered_candidates) != same_size:
        raise ValueError("verbose and plain archive listings disagree")

    local_hashes: dict[str, tuple[str, int]] = {}
    for index, member in enumerate(ordered_candidates, start=1):
        print(
            f"local duplicate candidate {index}/{len(ordered_candidates)}: "
            f"{mapped[member].relative_to(small_root)}",
            flush=True,
        )
        local_hashes[member] = sha256_file(
            mapped[member], label=f"small:{mapped[member].relative_to(small_root)}"
        )

    archive_hashes: dict[str, tuple[str, int]] = {}
    if ordered_candidates:
        expected_sizes = {member: archive_sizes[member] for member in ordered_candidates}
        print(
            f"joint duplicate archive scan start: files={len(ordered_candidates)} "
            f"expected_gib={sum(expected_sizes.values()) / GIB:.3f}",
            flush=True,
        )
        archive_hashes = sha256_archive_members(
            archive, ordered_candidates, expected_sizes, bsdtar=bsdtar
        )

    rows: list[dict[str, str | int]] = []
    for member, path in sorted(mapped.items()):
        local_bytes = path.stat().st_size
        archive_bytes = archive_sizes.get(member, "")
        local_sha256 = ""
        archive_sha256 = ""
        if member in auxiliary:
            status = "AUXILIARY_METADATA"
        elif member in missing:
            status = "MISSING_FROM_ARCHIVE"
        elif member not in same_size:
            status = "SIZE_MISMATCH"
        else:
            local_sha256, hashed_local_bytes = local_hashes[member]
            archive_sha256, hashed_archive_bytes = archive_hashes[member]
            if hashed_local_bytes != local_bytes or hashed_archive_bytes != archive_bytes:
                raise ValueError(f"hashed size drift for {member}")
            status = "DUPLICATE" if local_sha256 == archive_sha256 else "HASH_MISMATCH"
        rows.append(
            {
                "small_path": ledger_path(path),
                "archive_member": member,
                "local_bytes": local_bytes,
                "archive_bytes": archive_bytes,
                "local_sha256": local_sha256,
                "archive_sha256": archive_sha256,
                "status": status,
            }
        )

    duplicate_bytes = sum(
        int(row["local_bytes"]) for row in rows if row["status"] == "DUPLICATE"
    )
    counts = {
        status: sum(row["status"] == status for row in rows)
        for status in (
            "DUPLICATE",
            "SIZE_MISMATCH",
            "HASH_MISMATCH",
            "MISSING_FROM_ARCHIVE",
            "AUXILIARY_METADATA",
        )
    }
    summary: dict[str, int | str] = {
        "small_file_count": len(mapped),
        "small_total_bytes": sum(path.stat().st_size for path in mapped.values()),
        "duplicate_bytes": duplicate_bytes,
        **counts,
        "status": (
            "PASS"
            if counts["HASH_MISMATCH"] == 0 and counts["MISSING_FROM_ARCHIVE"] == 0
            else "FAIL"
        ),
    }
    return summary, rows


def render_report(summary: dict[str, int | str]) -> str:
    return f"""# MU-TCM small-subset duplicate audit — 2026-07-17

## Verdict

**{summary['status']}** as an integrity audit. The small subset contains
{summary['small_file_count']} files ({int(summary['small_total_bytes']) / GIB:.3f} GiB).
Exact size and full SHA-256 comparison proves {summary['DUPLICATE']} files
({int(summary['duplicate_bytes']) / GIB:.3f} GiB) duplicate their mapped
`full_dataset/` archive members.

- Size mismatch: {summary['SIZE_MISMATCH']}
- Hash mismatch after equal size: {summary['HASH_MISMATCH']}
- Missing mapped archive member: {summary['MISSING_FROM_ARCHIVE']}
- Platform auxiliary metadata: {summary['AUXILIARY_METADATA']}

`SIZE_MISMATCH` means “not an exact duplicate”; it is not an integrity failure.
`AUXILIARY_METADATA` is OS-generated cache state, not source-dataset content.
Only `DUPLICATE` rows are reclamation candidates. This audit performs no deletion.
The CSV ledger contains complete paths, byte counts, and both hashes.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--small-root", type=Path, default=DEFAULT_SMALL_ROOT)
    parser.add_argument("--bsdtar", default="bsdtar")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "analysis" / "q1_mutcm_duplicate_ledger_2026-07-17.csv",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "analysis" / "q1_mutcm_duplicate_audit_2026-07-17.md",
    )
    args = parser.parse_args()
    summary, rows = audit_duplicates(
        args.archive.resolve(), args.small_root.resolve(), bsdtar=args.bsdtar
    )
    atomic_write_rows(args.output.resolve(), rows)
    atomic_write_text(args.report.resolve(), render_report(summary))
    print(
        f"duplicate audit {summary['status']}: duplicate_gib="
        f"{int(summary['duplicate_bytes']) / GIB:.3f}",
        flush=True,
    )
    if summary["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
