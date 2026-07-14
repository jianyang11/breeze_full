"""Training-free cyclic spectral coherence features for PU fault identity.

The estimator is the frozen v6 averaged cyclic periodogram.  It measures
second-order spectral correlation across overlapping, Hann-tapered vibration
segments; it is not a learned classifier or a fitted spectral template.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

import numpy as np


EPSILON = 1e-12


@dataclass(frozen=True)
class CSCohSettings:
    """The preregistered v6 averaged-cyclic-periodogram settings."""

    nperseg: int = 512
    noverlap: int = 384
    nfft: int = 2048
    carrier_low_hz: float = 500.0
    carrier_high_hz: float = 3800.0
    alpha_tolerance_hz: float = 3.90625

    def __post_init__(self) -> None:
        if self.nperseg < 2:
            raise ValueError("nperseg must be at least 2")
        if not 0 <= self.noverlap < self.nperseg:
            raise ValueError("noverlap must be in [0, nperseg)")
        if self.nfft < self.nperseg:
            raise ValueError("nfft must be at least nperseg")
        if not 0.0 <= self.carrier_low_hz < self.carrier_high_hz:
            raise ValueError("carrier band must be strictly increasing and nonnegative")
        if self.alpha_tolerance_hz <= 0.0:
            raise ValueError("alpha_tolerance_hz must be positive")

    @property
    def hop(self) -> int:
        return self.nperseg - self.noverlap

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_SETTINGS = CSCohSettings()


def alpha_grid(alpha_hz: float, settings: CSCohSettings = DEFAULT_SETTINGS) -> tuple[float, float, float]:
    """Return the frozen centre-and-one-bin tolerance alpha grid."""
    if not np.isfinite(alpha_hz) or alpha_hz <= 0.0:
        raise ValueError("alpha_hz must be finite and positive")
    offsets = (-settings.alpha_tolerance_hz, 0.0, settings.alpha_tolerance_hz)
    values = tuple(float(alpha_hz + offset) for offset in offsets)
    if min(values) <= 0.0:
        raise ValueError("alpha tolerance produces a nonpositive cyclic frequency")
    return values


def all_alpha_frequencies(freqs: dict[str, float]) -> tuple[float, ...]:
    """Return the complete preregistered v6 alpha-family centres."""
    required = ("fr", "BPFO", "BPFI")
    if any(key not in freqs for key in required):
        raise ValueError(f"freqs must contain {required}")
    fr, bpfo, bpfi = (float(freqs[key]) for key in required)
    if not all(np.isfinite(value) and value > 0.0 for value in (fr, bpfo, bpfi)):
        raise ValueError("fr, BPFO, and BPFI must be finite and positive")
    values = [
        fr,
        2.0 * fr,
        3.0 * fr,
        bpfo,
        2.0 * bpfo,
        3.0 * bpfo,
        bpfi,
        2.0 * bpfi,
        3.0 * bpfi,
        bpfi - fr,
        bpfi + fr,
    ]
    return tuple(value for value in values if value > 0.0)


def _fault_alpha_families(freqs: dict[str, float], asserted_class: str) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Return target and competing alpha centres for a claimed OR/IR label."""
    all_alpha_frequencies(freqs)
    bpfo, bpfi, fr = (float(freqs[key]) for key in ("BPFO", "BPFI", "fr"))
    if asserted_class == "OR":
        return (bpfo, 2.0 * bpfo, 3.0 * bpfo), (bpfi, 2.0 * bpfi, 3.0 * bpfi)
    if asserted_class == "IR":
        return (
            bpfi,
            2.0 * bpfi,
            3.0 * bpfi,
            bpfi - fr,
            bpfi + fr,
        ), (bpfo, 2.0 * bpfo, 3.0 * bpfo)
    raise ValueError("asserted_class must be 'OR' or 'IR'")


def _as_signal(signal: np.ndarray, settings: CSCohSettings) -> np.ndarray:
    values = np.asarray(signal, dtype=float)
    if values.ndim != 1:
        raise ValueError("CSCoh requires a one-dimensional vibration signal")
    if len(values) < settings.nperseg:
        raise ValueError("signal is shorter than nperseg")
    if not np.all(np.isfinite(values)):
        raise ValueError("signal must be finite")
    return values


def _complex_interpolate(spectra: np.ndarray, positions: np.ndarray) -> np.ndarray:
    """Linearly interpolate each row of a uniformly sampled complex spectrum."""
    lower = np.floor(positions).astype(np.int64)
    upper = lower + 1
    if lower.min(initial=0) < 0 or upper.max(initial=0) >= spectra.shape[1]:
        raise ValueError("requested cyclic frequency lies outside the FFT grid")
    weight = positions - lower
    return spectra[:, lower] * (1.0 - weight) + spectra[:, upper] * weight


class AveragedCyclicPeriodogram:
    """Reusable segment spectra with memoized CSCoh alpha-band strengths."""

    def __init__(self, signal: np.ndarray, fs: float, settings: CSCohSettings = DEFAULT_SETTINGS):
        if not np.isfinite(fs) or fs <= 0.0:
            raise ValueError("fs must be finite and positive")
        self.settings = settings
        self.fs = float(fs)
        values = _as_signal(signal, settings)
        starts = np.arange(0, len(values) - settings.nperseg + 1, settings.hop, dtype=np.int64)
        if len(starts) < 2:
            raise ValueError("CSCoh requires at least two analysis segments")
        frames = np.stack([values[start : start + settings.nperseg] for start in starts])
        frames = frames - frames.mean(axis=1, keepdims=True)
        frames *= np.hanning(settings.nperseg)[None, :]
        self._spectra = np.fft.rfft(frames, n=settings.nfft, axis=1)
        self._df = self.fs / settings.nfft
        self._frequencies = np.fft.rfftfreq(settings.nfft, d=1.0 / self.fs)
        self._strength_cache: dict[float, float] = {}

    @property
    def n_segments(self) -> int:
        return int(self._spectra.shape[0])

    def coherence(self, alpha_hz: float) -> tuple[np.ndarray, np.ndarray]:
        """Return carrier frequency and normalized CSCoh at one cyclic frequency."""
        if not np.isfinite(alpha_hz) or alpha_hz <= 0.0:
            raise ValueError("alpha_hz must be finite and positive")
        half_alpha = float(alpha_hz) / 2.0
        low = self.settings.carrier_low_hz + half_alpha
        high = self.settings.carrier_high_hz - half_alpha
        mask = (self._frequencies >= low) & (self._frequencies <= high)
        carrier = self._frequencies[mask]
        if len(carrier) == 0:
            raise ValueError("alpha leaves no valid carrier frequencies in the fixed band")
        positive = _complex_interpolate(self._spectra, (carrier + half_alpha) / self._df)
        negative = _complex_interpolate(self._spectra, (carrier - half_alpha) / self._df)
        cyclic = np.mean(positive * np.conj(negative), axis=0)
        denominator = np.sqrt(
            np.mean(np.abs(positive) ** 2, axis=0) * np.mean(np.abs(negative) ** 2, axis=0)
        )
        coherence = np.abs(cyclic) / np.maximum(denominator, EPSILON)
        return carrier, coherence

    def alpha_strength(self, alpha_hz: float) -> float:
        """Return mean fixed-band CSCoh strength, memoized by alpha frequency."""
        key = float(alpha_hz)
        if key not in self._strength_cache:
            _, coherence = self.coherence(key)
            self._strength_cache[key] = float(np.mean(coherence))
        return self._strength_cache[key]

    def tolerance_strength(self, alpha_hz: float) -> tuple[float, dict[str, float]]:
        """Return the fixed maximum across centre and one-bin alpha tolerance."""
        scores = {f"{candidate:.8f}": self.alpha_strength(candidate) for candidate in alpha_grid(alpha_hz, self.settings)}
        return float(max(scores.values())), scores


def csc_coherence(
    signal: np.ndarray,
    fs: float,
    alpha_hz: float,
    settings: CSCohSettings = DEFAULT_SETTINGS,
) -> tuple[np.ndarray, np.ndarray]:
    """Calculate CSCoh for one alpha without exposing mutable estimator state."""
    return AveragedCyclicPeriodogram(signal, fs, settings).coherence(alpha_hz)


def _family_evidence(
    estimator: AveragedCyclicPeriodogram,
    alphas: Iterable[float],
) -> tuple[float, list[dict[str, Any]]]:
    rows = []
    for alpha in alphas:
        strength, tolerance_scores = estimator.tolerance_strength(float(alpha))
        rows.append({
            "alpha_hz": float(alpha),
            "strength": strength,
            "tolerance_scores": tolerance_scores,
        })
    if not rows:
        raise ValueError("CSCoh alpha family must not be empty")
    return float(np.mean([row["strength"] for row in rows])), rows


def fault_csc_evidence(
    signal: np.ndarray,
    fs: float,
    freqs: dict[str, float],
    asserted_class: str,
    settings: CSCohSettings = DEFAULT_SETTINGS,
) -> dict[str, Any]:
    """Compute frozen v6 paired CSCoh evidence for an asserted OR/IR class."""
    target_alphas, competing_alphas = _fault_alpha_families(freqs, asserted_class)
    estimator = AveragedCyclicPeriodogram(signal, fs, settings)
    target_strength, target_rows = _family_evidence(estimator, target_alphas)
    competing_strength, competing_rows = _family_evidence(estimator, competing_alphas)
    margin = float(np.log((target_strength + EPSILON) / (competing_strength + EPSILON)))
    return {
        "asserted_class": asserted_class,
        "settings": settings.as_dict(),
        "n_segments": estimator.n_segments,
        "target_strength": target_strength,
        "competing_strength": competing_strength,
        "margin": margin,
        "target_alpha_rows": target_rows,
        "competing_alpha_rows": competing_rows,
        "all_alpha_centres_hz": list(all_alpha_frequencies(freqs)),
    }
