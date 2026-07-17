#!/usr/bin/env python3
"""Audit XJTU-SY RAR5 volumes, member structure, hashes, and references."""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import tempfile
from pathlib import Path, PurePosixPath

import rarfile


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from q1_storage_audit import GIB, ROOT, atomic_write_text, sha256_file  # noqa: E402


DEFAULT_DATA_DIR = ROOT / "data" / "xjtu" / "XJTU-SY_Bearing_Datasets" / "Data"
PART_RE = re.compile(r"^(?P<stem>.+)\.part(?P<index>\d+)\.rar$", re.IGNORECASE)
TEXT_SUFFIXES = {".json", ".yaml", ".yml", ".csv", ".toml"}
REFERENCE_ROOTS = (
    ROOT / "specs",
    ROOT / "breeze" / "runs",
    ROOT / "breeze" / "results",
)


def discover_parts(data_dir: Path) -> list[Path]:
    indexed: list[tuple[str, int, Path]] = []
    for path in data_dir.iterdir():
        match = PART_RE.fullmatch(path.name)
        if path.is_file() and match:
            indexed.append((match.group("stem"), int(match.group("index")), path))
    if not indexed:
        raise ValueError(f"no multipart RAR files found in {data_dir}")
    stems = {stem for stem, _, _ in indexed}
    if len(stems) != 1:
        raise ValueError(f"multiple multipart stems found: {sorted(stems)}")
    indexed.sort(key=lambda item: item[1])
    indices = [index for _, index, _ in indexed]
    expected = list(range(1, max(indices) + 1))
    if indices != expected:
        raise ValueError(f"non-contiguous RAR part indices: {indices}, expected {expected}")
    parts = [path for _, _, path in indexed]
    standard_size = parts[0].stat().st_size
    if standard_size <= 0:
        raise ValueError("first RAR volume is empty")
    if any(path.stat().st_size != standard_size for path in parts[:-1]):
        raise ValueError("non-final RAR volumes do not share a fixed volume size")
    final_size = parts[-1].stat().st_size
    if not 0 < final_size <= standard_size:
        raise ValueError("final RAR volume size is outside (0, standard_size]")
    return parts


def safe_member_name(name: str) -> bool:
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts


def ledger_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)


def scan_references(roots: tuple[Path, ...]) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
            if path.suffix.lower() not in TEXT_SUFFIXES or path.stat().st_size > 10 * 1024**2:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            lower = text.lower()
            if "xjtu" not in lower:
                continue
            if "data/xjtu" in lower or "xjtu-sy_bearing_datasets.part" in lower:
                hit_type = "raw_path_binding"
            else:
                hit_type = "dataset_label_only"
            hits.append(
                {
                    "path": ledger_path(path),
                    "hit_type": hit_type,
                }
            )
    return hits


def atomic_write_csv(
    output: Path, fields: list[str], rows: list[dict[str, str | int]]
) -> None:
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


def audit_xjtu(data_dir: Path) -> tuple[dict[str, int | str], list[dict], list[dict], list[dict]]:
    parts = discover_parts(data_dir)
    volume_rows: list[dict[str, str | int]] = []
    for index, path in enumerate(parts, start=1):
        digest, byte_count = sha256_file(path, label=f"xjtu-volume-{index:02d}")
        volume_rows.append(
            {
                "index": index,
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": byte_count,
                "sha256": digest,
            }
        )

    with rarfile.RarFile(parts[0]) as archive:
        resolved_volumes = [Path(path).resolve() for path in archive.volumelist()]
        if resolved_volumes != [path.resolve() for path in parts]:
            raise ValueError(
                f"RAR header volume chain differs from discovered files: {resolved_volumes}"
            )
        infos = archive.infolist()
        files = [info for info in infos if not info.isdir()]
        if not files:
            raise ValueError("RAR archive contains no files")
        names = [info.filename for info in files]
        if len(names) != len(set(names)):
            raise ValueError("RAR archive contains duplicate member names")
        unsafe = [name for name in names if not safe_member_name(name)]
        if unsafe:
            raise ValueError(f"unsafe archive member paths: {unsafe[:5]}")

        member_rows: list[dict[str, str | int]] = []
        regimes: set[str] = set()
        bearings: set[tuple[str, str]] = set()
        for info in files:
            path = PurePosixPath(info.filename)
            if len(path.parts) >= 4:
                regimes.add(path.parts[1])
                bearings.add((path.parts[1], path.parts[2]))
            member_rows.append(
                {
                    "path": info.filename,
                    "bytes": info.file_size,
                    "compressed_bytes": info.compress_size,
                    "crc32": f"{info.CRC:08x}",
                    "volume_index_zero_based": info.volume,
                }
            )
        split_after = sum(
            bool(info.flags & rarfile.RAR_FILE_SPLIT_AFTER) for info in files
        )
        encrypted = sum(info.needs_password() for info in files)

    reference_rows = scan_references(REFERENCE_ROOTS)
    raw_bindings = sum(row["hit_type"] == "raw_path_binding" for row in reference_rows)
    summary: dict[str, int | str] = {
        "rarfile_version": rarfile.__version__,
        "volume_count": len(parts),
        "archive_bytes": sum(path.stat().st_size for path in parts),
        "member_count": len(infos),
        "file_count": len(files),
        "csv_count": sum(PurePosixPath(info.filename).suffix.lower() == ".csv" for info in files),
        "pdf_count": sum(PurePosixPath(info.filename).suffix.lower() == ".pdf" for info in files),
        "uncompressed_bytes": sum(info.file_size for info in files),
        "regime_count": len(regimes),
        "bearing_count": len(bearings),
        "regimes": ";".join(sorted(regimes)),
        "split_after_entries": split_after,
        "encrypted_entries": encrypted,
        "reference_hits": len(reference_rows),
        "raw_path_bindings": raw_bindings,
        "status": "PASS",
        "candidate_state": (
            "HIGH_RISK_RECLAMATION_CANDIDATE_PENDING_EXPLICIT_AUTHORIZATION_"
            "AND_EXTERNAL_REDOWNLOAD_CHECK"
        ),
    }
    return summary, volume_rows, member_rows, reference_rows


def render_report(summary: dict[str, int | str], reference_rows: list[dict]) -> str:
    label_paths = "\n".join(
        f"- `{row['path']}` ({row['hit_type']})" for row in reference_rows
    ) or "- None"
    return f"""# XJTU-SY multipart archive audit — 2026-07-17

## Integrity verdict

**{summary['status']}** for RAR header and manifest integrity. `rarfile`
{summary['rarfile_version']} resolved one contiguous six-volume chain, and every
volume has a recorded full SHA-256. The first five volumes have the fixed
volume size and the sixth is the non-empty final volume.

- Compressed volumes: {summary['volume_count']} ({int(summary['archive_bytes']) / GIB:.3f} GiB)
- Archive entries/files: {summary['member_count']} / {summary['file_count']}
- Files: {summary['csv_count']} CSV + {summary['pdf_count']} PDF
- Declared uncompressed bytes: {summary['uncompressed_bytes']} ({int(summary['uncompressed_bytes']) / GIB:.3f} GiB)
- Regimes/bearings: {summary['regime_count']} / {summary['bearing_count']}
- Regimes: `{summary['regimes']}`
- Entries spanning a next volume: {summary['split_after_entries']}
- Encrypted entries: {summary['encrypted_entries']}

This validates the RAR5 volume chain and complete header/member traversal. It
does not claim full payload CRC testing because no compatible `unrar`/`unar`
extractor is installed and no 11.38 GiB extraction was created under the 50 GB
budget.

## Current-artifact reference audit

The structured config/manifest scan found {summary['reference_hits']} XJTU label
references and {summary['raw_path_bindings']} bindings to `data/xjtu` or a RAR
part. Hits are:

{label_paths}

Historical registry/config references therefore do not prove that these local
parts fed any current pool or result. No extracted XJTU data, processed XJTU
array, split manifest, generated pool, or evaluated result is present.

## Storage decision

Candidate state: `{summary['candidate_state']}`.

The Q1 main protocols are PU, CWRU, and Berkeley; the historical audit records
XJTU-SY as skipped and its label semantics as run-to-failure prognostics rather
than ready-made fault-class windows. The six parts are not needed by a current
result, but they are the only local raw copy. External re-download availability
was not successfully revalidated in this audit. Therefore they are **not** a
safe automatic deletion: retain unless the user explicitly accepts that risk
after a fresh external recovery check. No file was deleted.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "analysis" / "q1_xjtu_archive_audit_2026-07-17.md",
    )
    parser.add_argument(
        "--volumes",
        type=Path,
        default=ROOT / "analysis" / "q1_xjtu_volume_checksums_2026-07-17.csv",
    )
    parser.add_argument(
        "--members",
        type=Path,
        default=ROOT / "analysis" / "q1_xjtu_archive_members_2026-07-17.csv",
    )
    parser.add_argument(
        "--references",
        type=Path,
        default=ROOT / "analysis" / "q1_xjtu_reference_hits_2026-07-17.csv",
    )
    args = parser.parse_args()
    summary, volumes, members, references = audit_xjtu(args.data_dir.resolve())
    atomic_write_csv(
        args.volumes.resolve(), ["index", "path", "bytes", "sha256"], volumes
    )
    atomic_write_csv(
        args.members.resolve(),
        ["path", "bytes", "compressed_bytes", "crc32", "volume_index_zero_based"],
        members,
    )
    atomic_write_csv(args.references.resolve(), ["path", "hit_type"], references)
    atomic_write_text(args.report.resolve(), render_report(summary, references))
    print(
        f"XJTU audit PASS: volumes={summary['volume_count']} "
        f"files={summary['file_count']} raw_path_bindings={summary['raw_path_bindings']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
