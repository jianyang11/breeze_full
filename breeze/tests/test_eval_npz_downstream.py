"""Unit tests for the downstream evaluation representation contract."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "breeze" / "src"))

from eval_npz_downstream import done_keys, normalize_per_window_rms  # noqa: E402


def test_per_window_rms_normalization_preserves_shape_and_sets_each_channel_rms() -> None:
    X = np.asarray(
        [
            [[3.0, 4.0, 0.0], [2.0, -2.0, 2.0]],
            [[-6.0, 8.0, 0.0], [1.0, 1.0, -1.0]],
        ],
        dtype=np.float32,
    )

    actual = normalize_per_window_rms(X)

    assert actual.shape == X.shape
    np.testing.assert_allclose(np.sqrt(np.mean(actual.astype(np.float64) ** 2, axis=2)), 1.0, rtol=1e-6, atol=1e-6)


@pytest.mark.parametrize(
    "X",
    [
        np.zeros((1, 2, 4), dtype=np.float32),
        np.asarray([[[1.0, np.nan]]], dtype=np.float32),
        np.ones((1, 4), dtype=np.float32),
    ],
)
def test_per_window_rms_normalization_rejects_invalid_windows(X: np.ndarray) -> None:
    with pytest.raises(ValueError):
        normalize_per_window_rms(X)


def test_downstream_checkpoint_keys_are_separated_by_normalization_mode(tmp_path: Path) -> None:
    path = tmp_path / "results.csv"
    fields = ["dataset", "split", "baseline", "normalization", "n_real", "seed"]
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerow(
            {
                "dataset": "PU",
                "split": "internal_loco_example",
                "baseline": "noise_aug",
                "normalization": "none",
                "n_real": 5,
                "seed": 0,
            }
        )

    completed = done_keys(path)

    assert ("PU", "internal_loco_example", "noise_aug", "none", 5, 0) in completed
    assert ("PU", "internal_loco_example", "noise_aug", "per-window-rms", 5, 0) not in completed
