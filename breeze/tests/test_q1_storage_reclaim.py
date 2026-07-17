from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "breeze" / "scripts" / "q1_storage_reclaim.py"
SPEC = importlib.util.spec_from_file_location("q1_storage_reclaim", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_resolve_inside_rejects_boundary_escape() -> None:
    with pytest.raises(ValueError, match="escapes"):
        MODULE.resolve_inside("../outside", ROOT / "data")


def test_delete_requires_exact_authorization_token() -> None:
    with pytest.raises(PermissionError, match="authorization"):
        MODULE.delete_rows([], ROOT / "unused.csv", "almost")


def test_preservation_lock_overrides_old_authorization_token() -> None:
    row = {"state": MODULE.PRESERVE_STATE, "target": "data/locked.bin"}
    with pytest.raises(PermissionError, match="preservation-locked"):
        MODULE.delete_rows([row], ROOT / "unused.csv", MODULE.AUTHORIZATION_TOKEN)


def test_atomic_zip_member_restore(tmp_path: Path) -> None:
    archive = tmp_path / "source.zip"
    payload = b"scientific-bytes"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("nested/payload.bin", payload)
    target = tmp_path / "restored.bin"
    import hashlib

    MODULE.atomic_stream_zip_member(
        archive, "nested/payload.bin", target, hashlib.sha256(payload).hexdigest()
    )
    assert target.read_bytes() == payload
    assert not list(tmp_path.glob("*.restore.tmp"))
