from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "breeze" / "scripts" / "q1_mutcm_duplicate_audit.py"
SPEC = importlib.util.spec_from_file_location("q1_mutcm_duplicate_audit", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_duplicate_audit_distinguishes_exact_and_size_mismatch(tmp_path: Path) -> None:
    archive_source = tmp_path / "archive_source" / "full_dataset"
    archive_source.mkdir(parents=True)
    (archive_source / "exact.bin").write_bytes(b"exact payload")
    (archive_source / "changed.bin").write_bytes(b"archive payload")
    archive = tmp_path / "source.tar"
    subprocess.run(
        ["bsdtar", "-cf", str(archive), "-C", str(tmp_path / "archive_source"), "full_dataset"],
        check=True,
    )

    small = tmp_path / "small_subset"
    small.mkdir()
    (small / "exact.bin").write_bytes(b"exact payload")
    (small / "changed.bin").write_bytes(b"different")
    (small / ".DS_Store").write_bytes(b"finder cache")

    summary, rows = MODULE.audit_duplicates(archive, small, bsdtar="bsdtar")
    statuses = {Path(str(row["small_path"])).name: row["status"] for row in rows}
    assert statuses == {
        ".DS_Store": "AUXILIARY_METADATA",
        "changed.bin": "SIZE_MISMATCH",
        "exact.bin": "DUPLICATE",
    }
    assert summary["DUPLICATE"] == 1
    assert summary["SIZE_MISMATCH"] == 1
    assert summary["AUXILIARY_METADATA"] == 1
    assert summary["status"] == "PASS"


def test_archive_member_sizes_matches_tar_payload(tmp_path: Path) -> None:
    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"1234567")
    archive = tmp_path / "source.tar"
    subprocess.run(
        ["bsdtar", "-cf", str(archive), "-C", str(tmp_path), payload.name],
        check=True,
    )
    assert MODULE.archive_member_sizes(archive, "bsdtar")[payload.name] == 7
