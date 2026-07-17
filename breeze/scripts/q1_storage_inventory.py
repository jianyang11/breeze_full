#!/usr/bin/env python3
"""Build a reproducible inventory of large BREEZE workspace files.

The inventory is read-only with respect to research artifacts.  It records
large-file location, size, modification time, semantic storage class, and Git
visibility.  Hashing and deletion are deliberately separate audited steps.
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCOPES = (ROOT / "data", ROOT / "proc", ROOT / "breeze" / "runs")
ARCHIVE_SUFFIXES = {".7z", ".zip", ".rar", ".tar", ".tgz", ".gz", ".bz2", ".xz"}
CHECKPOINT_SUFFIXES = {".pt", ".pth", ".ckpt", ".safetensors"}
CACHE_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def classify(path: Path) -> str:
    """Assign one non-overlapping storage role from path semantics."""

    rel = path.relative_to(ROOT)
    parts = set(rel.parts)
    suffix = path.suffix.lower()
    if parts & CACHE_PARTS or suffix in {".pyc", ".pyo"}:
        return "cache"
    if "checkpoints" in parts or suffix in CHECKPOINT_SUFFIXES:
        return "checkpoint"
    if rel.parts[0] == "data":
        if suffix in ARCHIVE_SUFFIXES:
            return "raw_archive"
        return "extracted_raw"
    if rel.parts[0] == "proc":
        return "processed_array"
    if rel.parts[:2] == ("breeze", "runs"):
        if suffix == ".npz" or "pool" in path.name.lower() or "pool" in parts:
            return "generated_pool"
        return "run_record"
    return "other"


def tracked_paths() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return {item.decode("utf-8") for item in result.stdout.split(b"\0") if item}


def git_visibility(path: Path, tracked: set[str]) -> str:
    rel = path.relative_to(ROOT).as_posix()
    if rel in tracked:
        result = subprocess.run(
            ["git", "status", "--porcelain=v1", "--", rel],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return "tracked_modified" if result.stdout.strip() else "tracked_clean"
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "--", rel],
        cwd=ROOT,
        check=False,
    )
    return "ignored" if ignored.returncode == 0 else "untracked"


def iter_large_files(scopes: tuple[Path, ...], minimum_bytes: int):
    scanned = 0
    for scope in scopes:
        if not scope.exists():
            continue
        for path in scope.rglob("*"):
            if not path.is_file():
                continue
            scanned += 1
            if scanned % 5000 == 0:
                print(f"inventory heartbeat: scanned={scanned}", flush=True)
            stat = path.stat()
            if stat.st_size >= minimum_bytes:
                yield path, stat
    print(f"inventory scan complete: scanned={scanned}", flush=True)


def atomic_write_csv(output: Path, rows: list[dict[str, str | int]]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = ["path", "bytes", "gib", "mtime_utc", "category", "git_visibility"]
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


def build_inventory(scopes: tuple[Path, ...], minimum_bytes: int) -> list[dict[str, str | int]]:
    tracked = tracked_paths()
    rows: list[dict[str, str | int]] = []
    for path, stat in iter_large_files(scopes, minimum_bytes):
        rows.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": stat.st_size,
                "gib": f"{stat.st_size / (1024**3):.6f}",
                "mtime_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "category": classify(path),
                "git_visibility": git_visibility(path, tracked),
            }
        )
    rows.sort(key=lambda row: (-int(row["bytes"]), str(row["path"])))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "analysis" / "q1_storage_inventory_2026-07-17.csv",
    )
    parser.add_argument("--minimum-mib", type=float, default=50.0)
    parser.add_argument("--scope", action="append", type=Path)
    args = parser.parse_args()
    if args.minimum_mib <= 0:
        raise SystemExit("--minimum-mib must be positive")
    scopes = tuple(path.resolve() for path in args.scope) if args.scope else DEFAULT_SCOPES
    minimum_bytes = int(args.minimum_mib * 1024**2)
    rows = build_inventory(scopes, minimum_bytes)
    output = args.output.resolve()
    atomic_write_csv(output, rows)
    total_bytes = sum(int(row["bytes"]) for row in rows)
    print(
        f"wrote {len(rows)} rows ({total_bytes / (1024**3):.3f} GiB listed) to {output}",
        flush=True,
    )


if __name__ == "__main__":
    main()
