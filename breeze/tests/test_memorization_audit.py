from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "breeze" / "scripts"))

from compute_memorization_audit import ReferenceIndex, window_digest  # noqa: E402


def _fixture() -> tuple[np.ndarray, np.ndarray]:
    time = np.linspace(0.0, 1.0, 64, endpoint=False)
    first = np.stack([np.sin(2 * np.pi * time), np.cos(4 * np.pi * time)])
    second = np.stack([np.sin(6 * np.pi * time + 0.2), np.cos(2 * np.pi * time - 0.1)])
    reference = np.stack([first, second]).astype(np.float32)
    return reference, np.asarray([10, 11], dtype=np.int64)


def test_exact_copy_has_zero_raw_and_feature_distance_and_unit_correlation():
    reference, indexes = _fixture()
    audit = ReferenceIndex(reference, indexes, fs_hz=64.0)
    exact, exact_index = audit.exact_match(reference[1].copy())
    raw_index, raw_distance = audit.raw_nearest(reference[1])
    feature_index, feature_distance = audit.feature_nearest(reference[1])
    xcorr_index, correlation, lag = audit.maximum_xcorr(reference[1])

    assert exact is True and exact_index == 11
    assert raw_index == 11 and raw_distance < 1e-7
    assert feature_index == 11 and feature_distance < 1e-7
    assert xcorr_index == 11 and correlation > 0.999999
    assert lag == 0


def test_shifted_window_is_not_exact_but_full_lag_correlation_detects_it():
    reference, indexes = _fixture()
    audit = ReferenceIndex(reference, indexes, fs_hz=64.0)
    shifted = np.zeros_like(reference[0])
    shifted[:, 5:] = reference[0, :, :-5]

    exact, _ = audit.exact_match(shifted)
    xcorr_index, correlation, lag = audit.maximum_xcorr(shifted)

    assert exact is False
    assert xcorr_index == 10
    assert correlation > 0.95
    assert abs(lag) == 5


def test_digest_includes_shape_and_float32_values():
    reference, _ = _fixture()
    assert window_digest(reference[0]) == window_digest(reference[0].astype(np.float64))
    assert window_digest(reference[0]) != window_digest(reference[0, :1])
