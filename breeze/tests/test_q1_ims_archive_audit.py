from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "breeze" / "scripts" / "q1_ims_archive_audit.py"
SPEC = importlib.util.spec_from_file_location("q1_ims_archive_audit", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_zip_member_hash_matches_local_payload(tmp_path: Path) -> None:
    payload = b"IMS nested payload" * 1000
    archive = tmp_path / "wrapper.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        handle.writestr("nested/data.bin", payload)
    digest, size, crc32 = MODULE.sha256_zip_member(
        archive, "nested/data.bin", heartbeat_mib=1
    )
    expected = tmp_path / "payload.bin"
    expected.write_bytes(payload)
    expected_digest, expected_size = MODULE.sha256_file(expected, label="test")
    assert (digest, size) == (expected_digest, expected_size)
    assert crc32 != 0


def test_manifest_fingerprint_is_order_invariant() -> None:
    class Info:
        def __init__(self, filename: str, file_size: int, crc: int):
            self.filename = filename
            self.file_size = file_size
            self.CRC = crc

    first = Info("a", 1, 2)
    second = Info("b", 3, 4)
    assert MODULE.member_manifest_fingerprint([first, second]) == (
        MODULE.member_manifest_fingerprint([second, first])
    )
