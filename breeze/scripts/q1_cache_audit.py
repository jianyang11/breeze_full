#!/usr/bin/env python3
"""Classify rebuildable caches separately from scientific and build evidence."""

from __future__ import annotations

import argparse
import csv
import os
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GIB = 1024**3
LATEX_TRANSIENT_SUFFIXES = {
    ".aux",
    ".blg",
    ".fdb_latexmk",
    ".fls",
    ".log",
    ".out",
    ".synctex.gz",
}


def path_size(path: Path) -> tuple[int, int]:
    """Return byte/file counts without following symlinks."""
    if path.is_symlink():
        return path.lstat().st_size, 1
    if path.is_file():
        return path.stat().st_size, 1
    total = 0
    files = 0
    for current, directories, filenames in os.walk(path, followlinks=False):
        directories[:] = [
            name for name in directories if not (Path(current) / name).is_symlink()
        ]
        for name in filenames:
            child = Path(current) / name
            try:
                total += child.lstat().st_size
                files += 1
            except FileNotFoundError:
                # Temporary caches can change during enumeration; never invent size.
                continue
    return total, files


def latex_category(path: Path) -> tuple[str, str, str]:
    if path.suffix.lower() == ".bbl":
        return (
            "BIBLIOGRAPHY_BUILD_EVIDENCE",
            "PRESERVE",
            "Preserve until the exact BibTeX/biber toolchain is locked and replayed.",
        )
    suffix = ".synctex.gz" if path.name.endswith(".synctex.gz") else path.suffix.lower()
    if suffix in LATEX_TRANSIENT_SUFFIXES:
        return (
            "LATEX_TRANSIENT_CACHE",
            "REBUILDABLE_PENDING_AUTHORIZATION",
            "Rebuild with the frozen latexmk publication command.",
        )
    raise ValueError(f"not a classified LaTeX artifact: {path}")


def display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def row_for(path: Path, category: str, action: str, evidence: str) -> dict:
    byte_count, file_count = path_size(path)
    return {
        "path": display_path(path),
        "category": category,
        "bytes": byte_count,
        "file_count": file_count,
        "action": action,
        "rebuild_evidence": evidence,
    }


def repository_cache_directories() -> list[Path]:
    selected: list[Path] = []
    excluded = {".git", ".venv-breeze"}
    for current, directories, _files in os.walk(ROOT, topdown=True, followlinks=False):
        directories[:] = [name for name in directories if name not in excluded]
        current_path = Path(current)
        for name in tuple(directories):
            if name in {"__pycache__", ".pytest_cache"}:
                selected.append(current_path / name)
                directories.remove(name)
    return sorted(selected)


def collect_rows(private_tmp: Path = Path("/private/tmp")) -> list[dict]:
    rows: list[dict] = []
    environment = ROOT / "breeze" / ".venv-breeze"
    if environment.exists():
        rows.append(
            row_for(
                environment,
                "PYTHON_ENVIRONMENT",
                "PRESERVE_UNTIL_LOCKED_REBUILD",
                "requirements.txt exists, but an exact clean-environment replay is still required.",
            )
        )

    for path in repository_cache_directories():
        category = "PYTHON_BYTECODE_CACHE" if path.name == "__pycache__" else "PYTEST_CACHE"
        command = "Python import/compile" if path.name == "__pycache__" else "pytest"
        rows.append(
            row_for(
                path,
                category,
                "REBUILDABLE_PENDING_AUTHORIZATION",
                f"Convention-defined cache rebuilt by {command}; contains no source of record.",
            )
        )

    paper = ROOT / "breeze" / "paper"
    if paper.exists():
        for path in sorted(paper.rglob("*")):
            if not path.is_file():
                continue
            suffix = ".synctex.gz" if path.name.endswith(".synctex.gz") else path.suffix.lower()
            if suffix == ".bbl" or suffix in LATEX_TRANSIENT_SUFFIXES:
                category, action, evidence = latex_category(path)
                rows.append(row_for(path, category, action, evidence))

    workspace_tmp = ROOT / "tmp"
    if workspace_tmp.exists():
        rows.append(
            row_for(
                workspace_tmp,
                "WORKSPACE_TEMP_REVIEW",
                "PRESERVE_USER_DIRTY_ASSET",
                "Untracked workspace content may contain active visual-QA evidence.",
            )
        )

    if private_tmp.exists():
        for path in sorted(private_tmp.iterdir()):
            if path.name.startswith("breeze"):
                rows.append(
                    row_for(
                        path,
                        "PRIVATE_TMP_BREEZE_ARTIFACT",
                        "REVIEW_RENDER_PROVENANCE",
                        "Temporary-location naming is insufficient proof of reconstructability.",
                    )
                )
    return rows


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
                    "path",
                    "category",
                    "bytes",
                    "file_count",
                    "action",
                    "rebuild_evidence",
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


def render_report(rows: list[dict]) -> str:
    rebuildable = [
        row for row in rows if row["action"] == "REBUILDABLE_PENDING_AUTHORIZATION"
    ]
    environments = [row for row in rows if row["category"] == "PYTHON_ENVIRONMENT"]
    bibliography = [
        row for row in rows if row["category"] == "BIBLIOGRAPHY_BUILD_EVIDENCE"
    ]
    private = [
        row for row in rows if row["category"] == "PRIVATE_TMP_BREEZE_ARTIFACT"
    ]
    return f"""# Cache and build-artifact audit — 2026-07-17

## Verdict

**PASS (classification only).** The audit separates convention-defined caches
from environments, bibliography evidence, active workspace artifacts, and
private render outputs. It identified {len(rebuildable)} repository cache/build
entries totaling {sum(int(row['bytes']) for row in rebuildable) / GIB:.3f} GiB
as rebuildable candidates. No file was deleted.

## Non-cache preservation boundaries

- Python environment: {len(environments)} entry, {sum(int(row['bytes']) for row in environments) / GIB:.3f} GiB. It remains preserved until a clean install from the pinned specification passes the complete test suite.
- `.bbl` bibliography evidence: {len(bibliography)} file(s). It remains preserved until the exact publication toolchain reproduces it.
- `/private/tmp` BREEZE artifacts: {len(private)} top-level entries, {sum(int(row['bytes']) for row in private) / GIB:.3f} GiB. A temporary path alone is not treated as reconstruction proof.
- Workspace `tmp/` is marked as user-dirty visual-QA material and is not a cache candidate.

## Reclamation boundary

Only rows marked `REBUILDABLE_PENDING_AUTHORIZATION` can enter the low-risk
cache batch. The reclamation plan must retain their generating command and must
request explicit authorization before removal. Virtual environments, `.bbl`,
workspace `tmp/`, and unmapped render artifacts are excluded from that batch.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "analysis" / "q1_cache_audit_2026-07-17.md",
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        default=ROOT / "analysis" / "q1_cache_inventory_2026-07-17.csv",
    )
    args = parser.parse_args()
    rows = collect_rows()
    atomic_write_csv(args.ledger.resolve(), rows)
    from q1_storage_audit import atomic_write_text

    atomic_write_text(args.report.resolve(), render_report(rows))
    print(
        f"cache audit PASS: entries={len(rows)} "
        f"bytes={sum(int(row['bytes']) for row in rows) / GIB:.3f} GiB",
        flush=True,
    )


if __name__ == "__main__":
    main()
