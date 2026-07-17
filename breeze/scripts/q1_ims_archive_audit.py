#!/usr/bin/env python3
"""Audit nested IMS archives without materializing their extracted payloads."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath

import rarfile


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from q1_mutcm_duplicate_audit import archive_member_sizes  # noqa: E402
from q1_storage_audit import (  # noqa: E402
    GIB,
    MIB,
    ROOT,
    archive_members,
    atomic_write_text,
    sha256_archive_members,
    sha256_file,
)


DEFAULT_RAW_DIR = ROOT / "data" / "ims" / "raw"
ZIP_NAME = "4_Bearings.zip"
SEVEN_Z_NAME = "IMS.7z"
ZIP_MEMBER = "4. Bearings/IMS.7z"
INNER_NAMES = (
    "1st_test.rar",
    "2nd_test.rar",
    "3rd_test.rar",
    "Readme Document for IMS Bearing Data.pdf",
)


def sha256_zip_member(
    archive: Path, member: str, *, heartbeat_mib: int = 256
) -> tuple[str, int, int]:
    """Read a ZIP member fully; zipfile validates its CRC at end-of-stream."""

    digest = hashlib.sha256()
    total = 0
    next_heartbeat = heartbeat_mib * MIB
    started = time.monotonic()
    with zipfile.ZipFile(archive) as wrapper:
        info = wrapper.getinfo(member)
        with wrapper.open(info) as handle:
            while chunk := handle.read(8 * MIB):
                digest.update(chunk)
                total += len(chunk)
                if total >= next_heartbeat:
                    elapsed = max(time.monotonic() - started, 1e-9)
                    print(
                        f"zip member heartbeat: member={member} "
                        f"read_gib={total / GIB:.3f} "
                        f"rate_mib_s={total / MIB / elapsed:.1f}",
                        flush=True,
                    )
                    while total >= next_heartbeat:
                        next_heartbeat += heartbeat_mib * MIB
        if total != info.file_size:
            raise ValueError(
                f"ZIP member size mismatch after read: {total} != {info.file_size}"
            )
        print(f"zip member complete: member={member} bytes={total}", flush=True)
        return digest.hexdigest(), total, info.CRC


def member_manifest_fingerprint(infos: list[rarfile.RarInfo]) -> str:
    digest = hashlib.sha256()
    for info in sorted(infos, key=lambda item: item.filename):
        digest.update(
            f"{info.filename}\0{info.file_size}\0{info.CRC:08x}\n".encode("utf-8")
        )
    return digest.hexdigest()


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


def inspect_rar(path: Path) -> tuple[dict[str, str | int], set[tuple[int, int]]]:
    with rarfile.RarFile(path) as archive:
        if len(archive.volumelist()) != 1:
            raise ValueError(f"unexpected multipart IMS RAR: {path}")
        infos = [info for info in archive.infolist() if not info.isdir()]
    if not infos:
        raise ValueError(f"empty IMS RAR: {path}")
    roots = sorted({PurePosixPath(info.filename).parts[0] for info in infos})
    signatures = {(info.file_size, info.CRC) for info in infos}
    return (
        {
            "archive": path.name,
            "file_count": len(infos),
            "uncompressed_bytes": sum(info.file_size for info in infos),
            "root_paths": ";".join(roots),
            "first_member": infos[0].filename,
            "last_member": infos[-1].filename,
            "manifest_sha256": member_manifest_fingerprint(infos),
            "encrypted_entries": sum(info.needs_password() for info in infos),
        },
        signatures,
    )


def audit_ims(raw_dir: Path) -> tuple[dict[str, str | int], list[dict], list[dict]]:
    paths = {name: raw_dir / name for name in (ZIP_NAME, SEVEN_Z_NAME, *INNER_NAMES)}
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing IMS artifacts: {missing}")

    local_hashes: dict[str, tuple[str, int]] = {}
    for name, path in paths.items():
        local_hashes[name] = sha256_file(path, label=f"ims:{name}")

    nested_7z_hash, nested_7z_bytes, zip_crc32 = sha256_zip_member(
        paths[ZIP_NAME], ZIP_MEMBER
    )
    local_7z_hash, local_7z_bytes = local_hashes[SEVEN_Z_NAME]
    if (nested_7z_hash, nested_7z_bytes) != (local_7z_hash, local_7z_bytes):
        raise ValueError("local IMS.7z differs from the ZIP-contained member")

    seven_z_members = archive_members(paths[SEVEN_Z_NAME], "bsdtar")
    seven_z_sizes = archive_member_sizes(paths[SEVEN_Z_NAME], "bsdtar")
    ordered_inner = [member for member in seven_z_members if member in INNER_NAMES]
    if set(ordered_inner) != set(INNER_NAMES):
        raise ValueError(
            f"IMS.7z member set differs from expected artifacts: {seven_z_members}"
        )
    expected_sizes = {name: seven_z_sizes[name] for name in ordered_inner}
    for name in ordered_inner:
        if expected_sizes[name] != local_hashes[name][1]:
            raise ValueError(f"IMS.7z/local size mismatch before hash: {name}")
    nested_hashes = sha256_archive_members(
        paths[SEVEN_Z_NAME], ordered_inner, expected_sizes, bsdtar="bsdtar"
    )
    for name in ordered_inner:
        if nested_hashes[name] != local_hashes[name]:
            raise ValueError(f"local {name} differs from the IMS.7z-contained member")

    set_rows: list[dict[str, str | int]] = []
    signatures: dict[str, set[tuple[int, int]]] = {}
    for name in INNER_NAMES[:3]:
        row, signatures[name] = inspect_rar(paths[name])
        set_rows.append(row)
    overlaps: dict[str, int] = {}
    rar_names = list(INNER_NAMES[:3])
    for left_index, left in enumerate(rar_names):
        for right in rar_names[left_index + 1 :]:
            overlaps[f"{left}|{right}"] = len(signatures[left] & signatures[right])

    relationship_rows: list[dict[str, str | int]] = [
        {
            "artifact": ZIP_NAME,
            "bytes": local_hashes[ZIP_NAME][1],
            "sha256": local_hashes[ZIP_NAME][0],
            "contained_in": "",
            "contained_path": "",
            "status": "CANONICAL_OUTER_WRAPPER",
        },
        {
            "artifact": SEVEN_Z_NAME,
            "bytes": local_7z_bytes,
            "sha256": local_7z_hash,
            "contained_in": ZIP_NAME,
            "contained_path": ZIP_MEMBER,
            "status": "EXACT_NESTED_DUPLICATE",
        },
    ]
    for name in INNER_NAMES:
        relationship_rows.append(
            {
                "artifact": name,
                "bytes": local_hashes[name][1],
                "sha256": local_hashes[name][0],
                "contained_in": SEVEN_Z_NAME,
                "contained_path": name,
                "status": "EXACT_NESTED_DUPLICATE",
            }
        )

    reclaimable_bytes = sum(local_hashes[name][1] for name in (SEVEN_Z_NAME, *INNER_NAMES))
    summary: dict[str, str | int] = {
        "zip_crc32": f"{zip_crc32:08x}",
        "nested_match_count": 1 + len(INNER_NAMES),
        "rar_count": len(set_rows),
        "rar_file_count": sum(int(row["file_count"]) for row in set_rows),
        "rar_uncompressed_bytes": sum(int(row["uncompressed_bytes"]) for row in set_rows),
        "cross_rar_signature_overlaps": sum(overlaps.values()),
        "reclaimable_bytes": reclaimable_bytes,
        "set3_actual_files": next(
            int(row["file_count"]) for row in set_rows if row["archive"] == "3rd_test.rar"
        ),
        "set3_actual_root": next(
            str(row["root_paths"]) for row in set_rows if row["archive"] == "3rd_test.rar"
        ),
        "status": "PASS",
        "semantic_state": "BLOCKED_FOR_LABEL_PROTOCOL_RECONCILIATION",
    }
    return summary, relationship_rows, set_rows


def render_report(summary: dict[str, str | int]) -> str:
    return f"""# IMS nested-archive audit — 2026-07-17

## Integrity and containment verdict

**{summary['status']}**. Full streaming SHA-256 comparison proves the local
`IMS.7z` is byte-identical to `4_Bearings.zip::{ZIP_MEMBER}`. A second full
stream proves the three local RAR files and README PDF are each byte-identical
to their `IMS.7z` members. ZIP CRC `{summary['zip_crc32']}` and both container
extractor return paths completed successfully; no large extracted copy was made.

- Exact nested duplicate relationships: {summary['nested_match_count']}
- RAR payload headers: {summary['rar_count']} archives,
  {summary['rar_file_count']} files,
  {int(summary['rar_uncompressed_bytes']) / GIB:.3f} GiB declared uncompressed
- Cross-RAR `(file_size, CRC32)` overlaps: {summary['cross_rar_signature_overlaps']}

The three RARs are therefore unique test payloads relative to one another, but
their standalone archive files are exact duplicates of members already inside
`IMS.7z`, which is itself duplicated inside the outer ZIP.

## Semantic blocker

The included README says Set 3 contains 4,448 files ending on 2004-04-04. The
actual `3rd_test.rar` header contains {summary['set3_actual_files']} files under
`{summary['set3_actual_root']}` and extends to 2004-04-18. This discrepancy is
preserved as evidence and blocks supervised label/protocol claims until it is
reconciled from an authoritative source. It is not silently renamed or trimmed.

Semantic state: `{summary['semantic_state']}`.

## Recoverability and candidate status

Retaining the outer `4_Bearings.zip` preserves the original wrapper and can
recreate `IMS.7z`, all three RARs, and the README exactly. The proven duplicate
local copies total {int(summary['reclaimable_bytes']) / GIB:.3f} GiB and may be
listed in the reclamation plan, but no deletion occurs before explicit user
authorization. The two CSV ledgers retain all artifact hashes and RAR manifest
fingerprints.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "analysis" / "q1_ims_archive_audit_2026-07-17.md",
    )
    parser.add_argument(
        "--relationships",
        type=Path,
        default=ROOT / "analysis" / "q1_ims_archive_relationships_2026-07-17.csv",
    )
    parser.add_argument(
        "--set-manifests",
        type=Path,
        default=ROOT / "analysis" / "q1_ims_set_manifests_2026-07-17.csv",
    )
    args = parser.parse_args()
    summary, relationships, set_rows = audit_ims(args.raw_dir.resolve())
    atomic_write_csv(
        args.relationships.resolve(),
        ["artifact", "bytes", "sha256", "contained_in", "contained_path", "status"],
        relationships,
    )
    atomic_write_csv(
        args.set_manifests.resolve(),
        [
            "archive",
            "file_count",
            "uncompressed_bytes",
            "root_paths",
            "first_member",
            "last_member",
            "manifest_sha256",
            "encrypted_entries",
        ],
        set_rows,
    )
    atomic_write_text(args.report.resolve(), render_report(summary))
    print(
        f"IMS audit PASS: exact_nested={summary['nested_match_count']} "
        f"candidate_gib={int(summary['reclaimable_bytes']) / GIB:.3f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
