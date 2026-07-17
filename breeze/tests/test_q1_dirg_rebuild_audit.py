from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "breeze" / "scripts" / "q1_dirg_rebuild_audit.py"
SPEC = importlib.util.spec_from_file_location("q1_dirg_rebuild_audit", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_npy_member_hash_excludes_container_metadata(tmp_path: Path) -> None:
    values = np.arange(24, dtype=np.float32).reshape(4, 2, 3)
    path = tmp_path / "arrays.npz"
    np.savez_compressed(path, X=values)
    digest, shape, dtype, size = MODULE.hash_npy_member(path, "X", heartbeat_mib=1)
    assert digest == hashlib.sha256(values.tobytes(order="C")).hexdigest()
    assert shape == values.shape
    assert dtype == values.dtype.str
    assert size == values.nbytes


def test_split_hashes_match_numpy_subsets(tmp_path: Path) -> None:
    values = np.arange(30, dtype=np.int32).reshape(10, 3)
    mask = np.array([False, True, False, False, True, False, True, False, False, True])
    path = tmp_path / "arrays.npz"
    np.savez_compressed(path, values=values)
    train_hash, test_hash, train_shape, dtype, train_bytes, test_bytes = (
        MODULE.split_npy_member_hashes(path, "values", mask)
    )
    assert train_hash == hashlib.sha256(values[~mask].tobytes(order="C")).hexdigest()
    assert test_hash == hashlib.sha256(values[mask].tobytes(order="C")).hexdigest()
    assert train_shape == values[~mask].shape
    assert dtype == values.dtype.str
    assert train_bytes == values[~mask].nbytes
    assert test_bytes == values[mask].nbytes
