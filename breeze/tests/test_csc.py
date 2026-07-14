from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "breeze" / "src"))

from verifier.csc import (  # noqa: E402
    CSCohSettings,
    alpha_grid,
    fault_csc_evidence,
)


FS = 8000
WIN = 2048
FREQS = {"fr": 15.0, "BPFO": 46.0, "BPFI": 74.0}


def _periodic_impact_train(rate_hz: float, seed: int = 3) -> np.ndarray:
    """Deterministic resonant impulse train with a known cyclic frequency."""
    rng = np.random.default_rng(seed)
    signal = np.zeros(WIN, dtype=float)
    kernel_time = np.arange(160, dtype=float) / FS
    kernel = np.exp(-kernel_time * 420.0) * np.sin(2.0 * np.pi * 1000.0 * kernel_time)
    impact_locations = np.rint(np.arange(0.0, WIN / FS, 1.0 / rate_hz) * FS).astype(int)
    for location in impact_locations:
        stop = min(WIN, location + len(kernel))
        signal[location:stop] += kernel[: stop - location]
    return signal + 0.03 * rng.normal(size=WIN)


def test_bpfo_impulse_train_dominates_competing_bpfi_cyclic_family():
    evidence = fault_csc_evidence(_periodic_impact_train(FREQS["BPFO"]), FS, FREQS, "OR")

    assert evidence["n_segments"] == 13
    assert evidence["target_strength"] > evidence["competing_strength"]
    assert evidence["margin"] > 0.0


def test_seeded_white_noise_has_no_bpfo_identity_margin():
    noise = np.random.default_rng(20260714).normal(size=WIN)
    evidence = fault_csc_evidence(noise, FS, FREQS, "OR")

    assert abs(evidence["margin"]) < 0.10


def test_invalid_signal_and_alpha_contracts_raise():
    with pytest.raises(ValueError, match="one-dimensional"):
        fault_csc_evidence(np.zeros((2, WIN)), FS, FREQS, "OR")
    with pytest.raises(ValueError, match="shorter"):
        fault_csc_evidence(np.zeros(100), FS, FREQS, "OR")
    with pytest.raises(ValueError, match="positive"):
        alpha_grid(0.0)
    with pytest.raises(ValueError, match="noverlap"):
        CSCohSettings(nperseg=16, noverlap=16)
