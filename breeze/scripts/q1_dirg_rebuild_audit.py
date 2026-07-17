#!/usr/bin/env python3
"""Prove DIRG processed arrays are deterministic functions of raw MAT files.

The audit recomputes array-content hashes from the raw ZIP one MAT file at a
time and compares them with the data sections inside the existing NPZ files.
It then derives the frozen LOCO split as streaming row hashes.  No second large
NPZ and no extracted raw directory are created.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PREPROCESS_PATH = ROOT / "breeze" / "scripts" / "dirg_preprocess.py"
RAW_PATH = ROOT / "data" / "dirg" / "raw" / "VariableSpeedAndLoad.zip"
ALL_PATH = ROOT / "proc" / "dirg_variable_all.npz"
TRAIN_PATH = ROOT / "proc" / "dirg_variable_loco_speed300_load1400_train.npz"
TEST_PATH = ROOT / "proc" / "dirg_variable_loco_speed300_load1400_test.npz"
MIB = 1024**2
GIB = 1024**3

SPEC = importlib.util.spec_from_file_location("dirg_preprocess_for_audit", PREPROCESS_PATH)
assert SPEC is not None and SPEC.loader is not None
PREPROCESS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PREPROCESS
SPEC.loader.exec_module(PREPROCESS)

PER_WINDOW_KEYS = (
    "X",
    "windows",
    "y",
    "file_index",
    "start_sample",
    "speed_hz",
    "load_mv",
    "nominal_load_n",
    "severity_um",
    "damage_location_id",
)
STATIC_KEYS = (
    "class_names",
    "damage_locations",
    "file_members",
    "file_class_names",
    "file_speed_hz",
    "file_nominal_load_n",
)
ALL_KEYS = PER_WINDOW_KEYS + STATIC_KEYS


def load_module_hash() -> str:
    return hashlib.sha256(PREPROCESS_PATH.read_bytes()).hexdigest()


def parse_npy_header(handle) -> tuple[tuple[int, ...], bool, np.dtype]:
    version = np.lib.format.read_magic(handle)
    if version == (1, 0):
        shape, fortran_order, dtype = np.lib.format.read_array_header_1_0(handle)
    elif version == (2, 0):
        shape, fortran_order, dtype = np.lib.format.read_array_header_2_0(handle)
    else:
        raise ValueError(f"unsupported NPY version {version}")
    return tuple(shape), bool(fortran_order), np.dtype(dtype)


def npz_keys(path: Path) -> set[str]:
    with zipfile.ZipFile(path) as archive:
        names = {PurePath.name.removesuffix(".npy") for PurePath in map(Path, archive.namelist())}
    return names


def hash_npy_member(
    npz_path: Path, key: str, *, heartbeat_mib: int = 512
) -> tuple[str, tuple[int, ...], str, int]:
    digest = hashlib.sha256()
    total = 0
    next_heartbeat = heartbeat_mib * MIB
    started = time.monotonic()
    with zipfile.ZipFile(npz_path) as archive, archive.open(f"{key}.npy") as handle:
        shape, fortran_order, dtype = parse_npy_header(handle)
        if fortran_order:
            raise ValueError(f"Fortran-order array is not supported: {npz_path}:{key}")
        while chunk := handle.read(8 * MIB):
            digest.update(chunk)
            total += len(chunk)
            if total >= next_heartbeat:
                elapsed = max(time.monotonic() - started, 1e-9)
                print(
                    f"NPY hash heartbeat: file={npz_path.name} key={key} "
                    f"read_gib={total / GIB:.3f} rate_mib_s={total / MIB / elapsed:.1f}",
                    flush=True,
                )
                while total >= next_heartbeat:
                    next_heartbeat += heartbeat_mib * MIB
    expected = int(np.prod(shape, dtype=np.int64)) * dtype.itemsize
    if total != expected:
        raise ValueError(f"NPY data size mismatch: {npz_path}:{key} {total} != {expected}")
    return digest.hexdigest(), shape, dtype.str, total


def read_exact(handle, byte_count: int) -> bytes:
    chunks: list[bytes] = []
    remaining = byte_count
    while remaining:
        chunk = handle.read(remaining)
        if not chunk:
            raise EOFError(f"unexpected EOF with {remaining} bytes remaining")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def split_npy_member_hashes(
    npz_path: Path, key: str, test_mask: np.ndarray
) -> tuple[str, str, tuple[int, ...], str, int, int]:
    train_digest = hashlib.sha256()
    test_digest = hashlib.sha256()
    train_bytes = 0
    test_bytes = 0
    started = time.monotonic()
    next_time_heartbeat = started + 10.0
    with zipfile.ZipFile(npz_path) as archive, archive.open(f"{key}.npy") as handle:
        shape, fortran_order, dtype = parse_npy_header(handle)
        if fortran_order or not shape or shape[0] != len(test_mask):
            raise ValueError(f"invalid split source shape/order: {key} {shape}")
        row_bytes = int(np.prod(shape[1:], dtype=np.int64)) * dtype.itemsize
        for index, is_test in enumerate(test_mask):
            payload = read_exact(handle, row_bytes)
            if is_test:
                test_digest.update(payload)
                test_bytes += row_bytes
            else:
                train_digest.update(payload)
                train_bytes += row_bytes
            now = time.monotonic()
            if now >= next_time_heartbeat:
                print(
                    f"split hash heartbeat: key={key} rows={index + 1}/{len(test_mask)} "
                    f"elapsed_s={now - started:.1f}",
                    flush=True,
                )
                next_time_heartbeat = now + 10.0
        if handle.read(1):
            raise ValueError(f"unexpected trailing data in {npz_path}:{key}")
    train_shape = (int((~test_mask).sum()), *shape[1:])
    test_shape = (int(test_mask.sum()), *shape[1:])
    return (
        train_digest.hexdigest(),
        test_digest.hexdigest(),
        train_shape,
        dtype.str,
        train_bytes,
        test_bytes,
    )


def digest_array(array: np.ndarray) -> str:
    return hashlib.sha256(array.tobytes(order="C")).hexdigest()


def raw_rebuild_hashes(raw_path: Path) -> tuple[dict[str, dict], int, int]:
    digests = {key: hashlib.sha256() for key in PER_WINDOW_KEYS}
    file_rows: list[dict] = []
    total_windows = 0
    location_id = {"none": 0, "inner_ring": 1, "roller": 2}
    with zipfile.ZipFile(raw_path) as archive:
        parsed = [PREPROCESS.parse_file(name) for name in archive.namelist()]
        rows = [row for row in parsed if row is not None]
        rows = sorted(
            rows,
            key=lambda row: (
                int(row["label"]),
                int(row["speed_hz"]),
                int(row["nominal_load_n"]),
                int(row["load_mv"]),
                int(row["replicate"]),
            ),
        )
        if not rows:
            raise ValueError("raw archive contains no parsed DIRG MAT members")
        for file_index, row in enumerate(rows):
            print(
                f"raw rebuild heartbeat: file={file_index + 1}/{len(rows)} "
                f"member={row['member']}",
                flush=True,
            )
            array = PREPROCESS.load_member(archive, str(row["member"]))
            windows, starts = PREPROCESS.segment(array)
            count = len(windows)
            total_windows += count
            payload = windows.tobytes(order="C")
            digests["X"].update(payload)
            digests["windows"].update(payload)
            generated = {
                "y": np.full(count, int(row["label"]), dtype=np.int64),
                "file_index": np.full(count, file_index, dtype=np.int32),
                "start_sample": starts,
                "speed_hz": np.full(count, int(row["speed_hz"]), dtype=np.int32),
                "load_mv": np.full(count, int(row["load_mv"]), dtype=np.int32),
                "nominal_load_n": np.full(
                    count, int(row["nominal_load_n"]), dtype=np.int32
                ),
                "severity_um": np.full(count, int(row["severity_um"]), dtype=np.int32),
                "damage_location_id": np.full(
                    count, location_id[str(row["damage_location"])], dtype=np.int32
                ),
            }
            for key, values in generated.items():
                digests[key].update(values.tobytes(order="C"))
            file_rows.append(row)

    static_arrays = {
        "class_names": np.array(
            [PREPROCESS.CLASS_SPECS[f"{index}A"].class_name for index in range(7)]
        ),
        "damage_locations": np.array(["none", "inner_ring", "roller"]),
        "file_members": np.array([str(row["member"]) for row in file_rows]),
        "file_class_names": np.array([str(row["class_name"]) for row in file_rows]),
        "file_speed_hz": np.array(
            [int(row["speed_hz"]) for row in file_rows], dtype=np.int32
        ),
        "file_nominal_load_n": np.array(
            [int(row["nominal_load_n"]) for row in file_rows], dtype=np.int32
        ),
    }
    result: dict[str, dict] = {}
    for key in PER_WINDOW_KEYS:
        if key in {"X", "windows"}:
            shape = (total_windows, 6, PREPROCESS.WIN)
            dtype = np.dtype(np.float32)
        elif key == "y":
            shape, dtype = (total_windows,), np.dtype(np.int64)
        else:
            shape, dtype = (total_windows,), np.dtype(np.int32)
        result[key] = {"sha256": digests[key].hexdigest(), "shape": shape, "dtype": dtype.str}
    for key, array in static_arrays.items():
        result[key] = {
            "sha256": digest_array(array),
            "shape": array.shape,
            "dtype": array.dtype.str,
        }
    return result, len(file_rows), total_windows


def aggregate_semantic_hash(rows: list[dict[str, str | int]]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: str(item["array"])):
        digest.update(
            json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        digest.update(b"\n")
    return digest.hexdigest()


def atomic_write_csv(output: Path, rows: list[dict[str, str | int]]) -> None:
    fields = [
        "array",
        "shape",
        "dtype",
        "raw_rebuild_sha256",
        "full_npz_sha256",
        "train_expected_sha256",
        "train_npz_sha256",
        "test_expected_sha256",
        "test_npz_sha256",
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


def audit_dirg() -> tuple[dict[str, str | int], list[dict[str, str | int]]]:
    required = (RAW_PATH, ALL_PATH, TRAIN_PATH, TEST_PATH, PREPROCESS_PATH)
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    for path in (ALL_PATH, TRAIN_PATH, TEST_PATH):
        if npz_keys(path) != set(ALL_KEYS):
            raise ValueError(f"unexpected NPZ keys in {path}: {sorted(npz_keys(path))}")

    raw_expected, raw_file_count, raw_window_count = raw_rebuild_hashes(RAW_PATH)
    with np.load(ALL_PATH, allow_pickle=False) as full:
        test_mask = (full["speed_hz"] == 300) & (full["nominal_load_n"] == 1400)
    if int(test_mask.sum()) == 0:
        raise ValueError("frozen DIRG LOCO test mask is empty")

    rows: list[dict[str, str | int]] = []
    for key in ALL_KEYS:
        print(f"existing NPZ audit: array={key}", flush=True)
        full_hash, full_shape, full_dtype, _ = hash_npy_member(ALL_PATH, key)
        expected = raw_expected[key]
        if key in PER_WINDOW_KEYS:
            (
                train_expected_hash,
                test_expected_hash,
                train_expected_shape,
                split_dtype,
                _,
                _,
            ) = split_npy_member_hashes(ALL_PATH, key, test_mask)
            if split_dtype != full_dtype:
                raise ValueError(f"split dtype drift for {key}")
            test_expected_shape = (int(test_mask.sum()), *full_shape[1:])
        else:
            train_expected_hash = full_hash
            test_expected_hash = full_hash
            train_expected_shape = full_shape
            test_expected_shape = full_shape
        train_hash, train_shape, train_dtype, _ = hash_npy_member(TRAIN_PATH, key)
        test_hash, test_shape, test_dtype, _ = hash_npy_member(TEST_PATH, key)
        status = (
            "PASS"
            if full_hash == expected["sha256"]
            and full_shape == tuple(expected["shape"])
            and full_dtype == expected["dtype"]
            and train_hash == train_expected_hash
            and test_hash == test_expected_hash
            and train_shape == tuple(train_expected_shape)
            and test_shape == tuple(test_expected_shape)
            and train_dtype == test_dtype == full_dtype
            else "FAIL"
        )
        rows.append(
            {
                "array": key,
                "shape": str(full_shape),
                "dtype": full_dtype,
                "raw_rebuild_sha256": str(expected["sha256"]),
                "full_npz_sha256": full_hash,
                "train_expected_sha256": train_expected_hash,
                "train_npz_sha256": train_hash,
                "test_expected_sha256": test_expected_hash,
                "test_npz_sha256": test_hash,
                "status": status,
            }
        )
    if any(row["status"] != "PASS" for row in rows):
        failed = [row["array"] for row in rows if row["status"] != "PASS"]
        raise ValueError(f"DIRG semantic rebuild mismatch: {failed}")

    from q1_storage_audit import sha256_file

    identities = {}
    for label, path in (
        ("raw", RAW_PATH),
        ("full", ALL_PATH),
        ("train", TRAIN_PATH),
        ("test", TEST_PATH),
    ):
        identities[label] = sha256_file(path, label=f"dirg:{label}")
    summary: dict[str, str | int] = {
        "raw_sha256": identities["raw"][0],
        "raw_bytes": identities["raw"][1],
        "preprocess_sha256": load_module_hash(),
        "full_container_sha256": identities["full"][0],
        "train_container_sha256": identities["train"][0],
        "test_container_sha256": identities["test"][0],
        "processed_bytes": sum(identities[key][1] for key in ("full", "train", "test")),
        "raw_file_count": raw_file_count,
        "raw_window_count": raw_window_count,
        "test_window_count": int(test_mask.sum()),
        "train_window_count": int((~test_mask).sum()),
        "array_count": len(rows),
        "semantic_manifest_sha256": aggregate_semantic_hash(rows),
        "status": "PASS",
        "candidate_state": "REBUILDABLE_BUT_RETAIN_UNTIL_CHECKPOINTED_REBUILDER_EXISTS",
    }
    return summary, rows


def render_report(summary: dict[str, str | int]) -> str:
    return f"""# DIRG deterministic rebuild audit — 2026-07-17

## Verdict

**{summary['status']}** at array-content level. The audit reloaded all
{summary['raw_file_count']} selected MAT members from the source ZIP one at a
time, regenerated {summary['raw_window_count']} windows and every metadata
array using the checked-in preprocessing implementation, and matched the data
section SHA-256, shape, and dtype of all {summary['array_count']} arrays in the
full NPZ. It then streamed the frozen 300 Hz / 1400 N mask and matched every
train/test array hash ({summary['train_window_count']} / {summary['test_window_count']} windows).

No second large NPZ or extracted raw copy was created.

## Provenance identities

- Raw ZIP bytes/SHA-256: {summary['raw_bytes']} / `{summary['raw_sha256']}`
- Preprocessor SHA-256: `{summary['preprocess_sha256']}`
- Full NPZ container SHA-256: `{summary['full_container_sha256']}`
- Train NPZ container SHA-256: `{summary['train_container_sha256']}`
- Test NPZ container SHA-256: `{summary['test_container_sha256']}`
- Semantic manifest SHA-256: `{summary['semantic_manifest_sha256']}`

Container hashes identify the current files; the semantic manifest is the
determinism proof because compressed NPZ container metadata need not be stable
across rebuild times.

## Storage decision

The three large NPZ files total {int(summary['processed_bytes']) / GIB:.3f} GiB
and are semantically reconstructable from the retained raw ZIP plus the pinned
preprocessor. Candidate state is `{summary['candidate_state']}`: the current
preprocessor lacks per-file checkpoints and atomic large-output commits, so
these result-referenced arrays stay retained until the long-run contract is
implemented and tested. No file was deleted.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "analysis" / "q1_dirg_rebuild_audit_2026-07-17.md",
    )
    parser.add_argument(
        "--hashes",
        type=Path,
        default=ROOT / "analysis" / "q1_dirg_semantic_hashes_2026-07-17.csv",
    )
    args = parser.parse_args()
    summary, rows = audit_dirg()
    atomic_write_csv(args.hashes.resolve(), rows)
    from q1_storage_audit import atomic_write_text

    atomic_write_text(args.report.resolve(), render_report(summary))
    print(
        f"DIRG audit PASS: arrays={summary['array_count']} "
        f"processed_gib={int(summary['processed_bytes']) / GIB:.3f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
