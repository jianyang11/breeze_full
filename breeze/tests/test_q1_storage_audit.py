from __future__ import annotations

import csv
import importlib.util
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "breeze" / "scripts" / "q1_storage_audit.py"
SPEC = importlib.util.spec_from_file_location("q1_storage_audit", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_sha256_file_matches_known_digest(tmp_path: Path) -> None:
    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"BREEZE research integrity\n")
    digest, size = MODULE.sha256_file(payload, label="test", heartbeat_mib=1)
    assert digest == "51fd55ef96e83d70b4f5bac78a49766cf01e42bcdb8eb3bb60cfb57a69dcdffb"
    assert size == 26


def test_large_sample_is_seeded_and_confined_to_top_quartile() -> None:
    sizes = {f"f{index:02d}.mat": index for index in range(1, 21)}
    first, population_size = MODULE.choose_large_samples(sizes, seed=20260717)
    second, _ = MODULE.choose_large_samples(sizes, seed=20260717)
    assert first == second
    assert population_size == 5
    assert set(first) <= {"f16.mat", "f17.mat", "f18.mat", "f19.mat", "f20.mat"}


def test_joint_archive_member_stream_matches_sources(tmp_path: Path) -> None:
    first = tmp_path / "first.bin"
    second = tmp_path / "second.bin"
    first.write_bytes(b"0123456789" * 1000)
    second.write_bytes(b"abcdefgh" * 1700)
    archive = tmp_path / "sample.tar"
    subprocess.run(
        [
            "bsdtar",
            "-cf",
            str(archive),
            "-C",
            str(tmp_path),
            first.name,
            second.name,
        ],
        check=True,
    )
    first_digest, first_size = MODULE.sha256_file(first, label="test:first")
    second_digest, second_size = MODULE.sha256_file(second, label="test:second")
    results = MODULE.sha256_archive_members(
        archive,
        [first.name, second.name],
        {first.name: first_size, second.name: second_size},
        bsdtar="bsdtar",
    )
    assert results[first.name] == (first_digest, first_size)
    assert results[second.name] == (second_digest, second_size)


def test_checksum_csv_has_stable_schema(tmp_path: Path) -> None:
    output = tmp_path / "checksums.csv"
    row = {
        "file_name": "sample.mat",
        "archive_member": "full_dataset/signals_synced/sample.mat",
        "manifest_bytes": 3,
        "local_bytes": 3,
        "archive_bytes": 3,
        "local_sha256": "abc",
        "archive_sha256": "abc",
        "status": "PASS",
    }
    MODULE.atomic_write_csv(output, [row])
    with output.open(newline="", encoding="utf-8") as handle:
        assert list(csv.DictReader(handle)) == [
            {key: str(value) for key, value in row.items()}
        ]
    assert not list(tmp_path.glob("*.tmp"))
