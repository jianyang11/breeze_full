"""Source-only extrapolation-regime calibration for :mod:`verifier.v2`.

The in-domain v2 verifier intentionally represents a source-condition signal
domain.  This module defines a separate, auditable admission regime for a
known target operating condition without ever inspecting target windows.  It
does not fit a model: every condition prediction is fixed inverse-distance
weighting over configured rpm, torque, and radial-load metadata.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np

from config import CLASSES, CONDITIONS, FS
from verifier.features import band_energy_ratio, envelope_spectrum, env_peak_metrics, time_stats
from verifier.verifier import BreezeVerifier


PREDICTABLE_FEATURES = {
    "healthy": ("vib_rms", "vib_crest", "band_3000_4000", "ir_resonance_3000_3600"),
    "OR": ("vib_crest", "band_500_1000", "or_resonance_600_1200"),
    "IR": (
        "vib_crest",
        "vib_kurtosis",
        "env_peak_prominence",
        "mod_depth_fr",
        "ir_resonance_3000_3600",
    ),
}
ALL_MORPHOLOGY_FEATURES = (
    "vib_rms",
    "vib_kurtosis",
    "vib_crest",
    "band_500_1000",
    "band_3000_4000",
    "or_resonance_600_1200",
    "ir_resonance_3000_3600",
    "env_peak_prominence",
    "mod_depth_fr",
)
DEMODULATION_BANDS = {"OR": (600.0, 1200.0), "IR": (3000.0, 3600.0)}
INTERVAL_QUANTILES = (0.05, 0.95)
LOO_MULTIPLIER = 2.0
ENVELOPE_FAULT_LOWER_Q = 0.10
MCSA_FAULT_LOWER_Q = 0.01
PHYSICAL_HEALTHY_UPPER_Q = 0.99


def _condition_scale() -> np.ndarray:
    values = np.asarray([CONDITIONS[c] for c in CONDITIONS], dtype=float)
    scale = np.std(values, axis=0)
    return np.where(scale > 1e-12, scale, 1.0)


def _idw_predict(source_conditions: list[str], values: np.ndarray, target_condition: str) -> float:
    if len(source_conditions) != len(values) or not source_conditions:
        raise ValueError("condition/value inputs must be nonempty and aligned")
    source = np.asarray([CONDITIONS[c] for c in source_conditions], dtype=float)
    target = np.asarray(CONDITIONS[target_condition], dtype=float)
    distance = np.sqrt(np.sum(((source - target) / _condition_scale()) ** 2, axis=1))
    weights = 1.0 / (distance + 1e-6)
    weights /= weights.sum()
    return float(np.sum(weights * values))


def _loo_mae(source_conditions: list[str], medians: np.ndarray) -> float:
    if len(source_conditions) < 3:
        raise ValueError("extrapolation calibration requires at least three source conditions")
    errors = []
    for index, condition in enumerate(source_conditions):
        keep = [i for i in range(len(source_conditions)) if i != index]
        prediction = _idw_predict([source_conditions[i] for i in keep], medians[keep], condition)
        errors.append(abs(prediction - float(medians[index])))
    return float(np.mean(errors))


def _morphology_features(w: np.ndarray, cls: str, freqs: dict[str, float]) -> dict[str, float]:
    vibration = w[0]
    stats = time_stats(vibration)
    values = {
        "vib_rms": float(stats["rms"]),
        "vib_kurtosis": float(stats["kurtosis"]),
        "vib_crest": float(stats["crest"]),
        "band_500_1000": band_energy_ratio(vibration, FS, (500.0, 1000.0)),
        "band_3000_4000": band_energy_ratio(vibration, FS, (3000.0, 4000.0)),
        "or_resonance_600_1200": band_energy_ratio(vibration, FS, (600.0, 1200.0)),
        "ir_resonance_3000_3600": band_energy_ratio(vibration, FS, (3000.0, 3600.0)),
        "env_peak_prominence": 0.0,
        "mod_depth_fr": 0.0,
    }
    if cls in DEMODULATION_BANDS:
        evidence = _envelope_evidence(vibration, cls, freqs)
        values["env_peak_prominence"] = float(evidence["fund_prominence"])
        values["mod_depth_fr"] = float(evidence["shaft_prominence"])
    return values


def _envelope_evidence(vibration: np.ndarray, cls: str, freqs: dict[str, float]) -> dict[str, float]:
    if cls not in DEMODULATION_BANDS:
        raise ValueError(f"no fault envelope definition for {cls}")
    f, spectrum = envelope_spectrum(vibration, FS, DEMODULATION_BANDS[cls])
    f0 = float(freqs["BPFO"] if cls == "OR" else freqs["BPFI"])
    df = float(f[1] - f[0])
    tolerance = max(2.0 * df, 0.02 * f0)
    fundamental = env_peak_metrics(f, spectrum, f0, tolerance)
    competing_hz = float(freqs["BPFI"] if cls == "OR" else freqs["BPFO"])
    competing = env_peak_metrics(f, spectrum, competing_hz, max(2.0 * df, 0.02 * competing_hz))
    shaft = env_peak_metrics(f, spectrum, float(freqs["fr"]), tolerance)
    return {
        "target_hz": f0,
        "tolerance_hz": float(tolerance),
        "fund_prominence": float(fundamental["prominence"]),
        "fund_peak_hz": float(fundamental["peak_freq"]),
        "fund_proximity_err_hz": float(fundamental["proximity_err"]),
        "competing_hz": competing_hz,
        "competing_prominence": float(competing["prominence"]),
        "rate_contrast": float(np.log1p(fundamental["prominence"]) - np.log1p(competing["prominence"])),
        "shaft_prominence": float(shaft["prominence"]),
    }


def _report_bounds(values: np.ndarray) -> dict[str, float]:
    return {
        "q01": float(np.quantile(values, 0.01)),
        "q99": float(np.quantile(values, 0.99)),
    }


def _base_boundary(
    X_train: np.ndarray,
    y_train: np.ndarray,
    target_condition: str,
    bearings: np.ndarray | None,
    coverage: float,
) -> BreezeVerifier:
    boundary = BreezeVerifier(
        coverage=coverage,
        gates={"boundary": False, "energy": False, "envelope": False, "mcsa": False, "spectrum": False},
    )
    boundary.calibrate(X_train, y_train, target_condition, bearings=bearings)
    return boundary


def _boundary_payload(boundary: BreezeVerifier) -> dict[str, Any]:
    return {
        "coverage": boundary.coverage,
        "gates": boundary.gates,
        "cond": boundary.cond,
        "freqs": boundary.freqs,
        "calib": boundary.calib,
    }


def _validate_inputs(
    X_train: np.ndarray,
    y_train: np.ndarray,
    source_conditions: list[str] | None,
    target_condition: str | None,
    condition_labels: np.ndarray | None,
) -> tuple[list[str], str, np.ndarray]:
    if source_conditions is None or target_condition is None or condition_labels is None:
        raise ValueError("extrapolation calibration requires source_conditions, target_condition, and condition_labels")
    if target_condition not in CONDITIONS:
        raise ValueError(f"unknown target condition {target_condition}")
    sources = list(source_conditions)
    if len(sources) < 3 or len(set(sources)) != len(sources):
        raise ValueError("extrapolation calibration requires three distinct source conditions")
    if target_condition in sources:
        raise ValueError("target condition must not appear in source conditions")
    if any(c not in CONDITIONS for c in sources):
        raise ValueError("unknown source condition")
    labels = np.asarray(condition_labels, dtype=str)
    if len(labels) != len(X_train) or len(y_train) != len(X_train):
        raise ValueError("X_train, y_train, and condition_labels must have the same length")
    if set(labels.tolist()) != set(sources):
        raise ValueError("condition_labels must contain exactly the declared source conditions")
    return sources, target_condition, labels


def _class_morphology_calibration(
    X_train: np.ndarray,
    y_train: np.ndarray,
    condition_labels: np.ndarray,
    cls: str,
    source_conditions: list[str],
    target_condition: str,
) -> dict[str, Any]:
    cls_index = CLASSES.index(cls)
    per_condition: dict[str, dict[str, list[float]]] = {}
    for condition in source_conditions:
        mask = (y_train == cls_index) & (condition_labels == condition)
        windows = X_train[mask]
        if len(windows) == 0:
            raise ValueError(f"no {cls} train windows for source condition {condition}")
        freqs = _fault_freqs(condition)
        per_condition[condition] = {key: [] for key in ALL_MORPHOLOGY_FEATURES}
        for window in windows:
            for key, value in _morphology_features(window, cls, freqs).items():
                per_condition[condition][key].append(value)

    predictable: dict[str, Any] = {}
    report_only: dict[str, Any] = {}
    for feature in ALL_MORPHOLOGY_FEATURES:
        q05 = np.asarray([np.quantile(per_condition[c][feature], INTERVAL_QUANTILES[0]) for c in source_conditions])
        q95 = np.asarray([np.quantile(per_condition[c][feature], INTERVAL_QUANTILES[1]) for c in source_conditions])
        medians = np.asarray([np.median(per_condition[c][feature]) for c in source_conditions])
        source_summary = {
            c: {
                "q05": float(q05[index]),
                "median": float(medians[index]),
                "q95": float(q95[index]),
            }
            for index, c in enumerate(source_conditions)
        }
        pooled = np.concatenate([np.asarray(per_condition[c][feature], dtype=float) for c in source_conditions])
        if feature in PREDICTABLE_FEATURES[cls]:
            loo = _loo_mae(source_conditions, medians)
            margin = LOO_MULTIPLIER * loo
            lo = _idw_predict(source_conditions, q05, target_condition) - margin
            hi = _idw_predict(source_conditions, q95, target_condition) + margin
            predictable[feature] = {
                "source_by_condition": source_summary,
                "predicted_q05": float(_idw_predict(source_conditions, q05, target_condition)),
                "predicted_q95": float(_idw_predict(source_conditions, q95, target_condition)),
                "loo_mae_median": loo,
                "multiplier": LOO_MULTIPLIER,
                "interval_lo": float(min(lo, hi)),
                "interval_hi": float(max(lo, hi)),
                "boundary_source": "interpolated_idw_q05_q95_plus_2x_loo_mae",
            }
        else:
            report_only[feature] = {
                "source_by_condition": source_summary,
                "source_empirical_union": _report_bounds(pooled),
                "boundary_source": "report_only_weak_or_not_predictable",
            }
    return {"predictable": predictable, "report_only": report_only}


def _fault_freqs(condition: str) -> dict[str, float]:
    from config import fault_freqs

    return fault_freqs(CONDITIONS[condition][0] / 60.0)


def _physical_calibration(
    X_train: np.ndarray,
    y_train: np.ndarray,
    condition_labels: np.ndarray,
    source_conditions: list[str],
    target_condition: str,
    vector_current_fn: Callable[..., dict[str, float]],
) -> dict[str, Any]:
    physical: dict[str, Any] = {"healthy": {"healthy_absence": {}}}
    healthy_index = CLASSES.index("healthy")
    for fault in ("OR", "IR"):
        fault_index = CLASSES.index(fault)
        fault_env, fault_contrast, fault_mcsa, healthy_env, healthy_mcsa = [], [], [], [], []
        for condition in source_conditions:
            source_freqs = _fault_freqs(condition)
            target_freqs = _fault_freqs(target_condition)
            fault_windows = X_train[(y_train == fault_index) & (condition_labels == condition)]
            healthy_windows = X_train[(y_train == healthy_index) & (condition_labels == condition)]
            for window in fault_windows:
                evidence = _envelope_evidence(window[0], fault, source_freqs)
                fault_env.append(evidence["fund_prominence"])
                fault_contrast.append(evidence["rate_contrast"])
                fault_mcsa.append(vector_current_fn(window[1], window[2], source_freqs, fault)["sideband_prominence"])
            for window in healthy_windows:
                # Healthy has no observed bearing-fault rate.  Its false target
                # evidence must therefore be calibrated at the target rate.
                healthy_env.append(_envelope_evidence(window[0], fault, target_freqs)["fund_prominence"])
                healthy_mcsa.append(vector_current_fn(window[1], window[2], target_freqs, fault)["sideband_prominence"])
        env_fault_floor = float(np.quantile(fault_env, ENVELOPE_FAULT_LOWER_Q))
        contrast_fault_floor = float(np.quantile(fault_contrast, ENVELOPE_FAULT_LOWER_Q))
        env_healthy_ceiling = float(np.quantile(healthy_env, PHYSICAL_HEALTHY_UPPER_Q))
        mc_fault_floor = float(np.quantile(fault_mcsa, MCSA_FAULT_LOWER_Q))
        mc_healthy_ceiling = float(np.quantile(healthy_mcsa, PHYSICAL_HEALTHY_UPPER_Q))
        physical[fault] = {
            "envelope_fault_floor": env_fault_floor,
            "envelope_contrast_floor": contrast_fault_floor,
            "envelope_healthy_ceiling": env_healthy_ceiling,
            "envelope_quantiles": {"fault_lower": ENVELOPE_FAULT_LOWER_Q, "healthy_upper": PHYSICAL_HEALTHY_UPPER_Q},
            "mcsa_fault_floor": mc_fault_floor,
            "mcsa_healthy_ceiling": mc_healthy_ceiling,
            "mcsa_hard_gate": bool(mc_fault_floor > mc_healthy_ceiling),
            "mcsa_quantiles": {"fault_lower": MCSA_FAULT_LOWER_Q, "healthy_upper": PHYSICAL_HEALTHY_UPPER_Q},
        }
        physical["healthy"]["healthy_absence"][fault] = {
            "prominence_ceiling": env_healthy_ceiling,
            "quantile": PHYSICAL_HEALTHY_UPPER_Q,
        }
    return physical


def _report_only_calibration(
    X_train: np.ndarray,
    y_train: np.ndarray,
    soft_band_fn: Callable[[np.ndarray], np.ndarray],
    psd_cdf_fn: Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]],
    psd_w1_fn: Callable[[np.ndarray, np.ndarray], float],
    stat_vector_fn: Callable[[np.ndarray], np.ndarray],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for ci, cls in enumerate(CLASSES):
        windows = X_train[y_train == ci]
        stats = np.asarray([stat_vector_fn(w) for w in windows])
        median = np.median(stats, axis=0)
        scale = (np.quantile(stats, 0.75, axis=0) - np.quantile(stats, 0.25, axis=0)) / 1.349
        scale = np.where(scale > 1e-12, scale, np.std(stats, axis=0) + 1e-9)
        soft = np.asarray([soft_band_fn(w[0]) for w in windows])
        cdfs = np.asarray([psd_cdf_fn(w[0])[1] for w in windows])
        ref_cdf = np.median(cdfs, axis=0)
        w1 = np.asarray([psd_w1_fn(w[0], ref_cdf) for w in windows])
        result[cls] = {
            "stats_median": median,
            "stats_scale": scale,
            "soft_spectrum_q01": np.quantile(soft, 0.01, axis=0),
            "soft_spectrum_q99": np.quantile(soft, 0.99, axis=0),
            "psd_w1_ref_cdf": ref_cdf,
            "psd_w1_q99": float(np.quantile(w1, 0.99)),
            "boundary_source": "report_only_source_empirical_union",
        }
    return result


def calibrate_extrapolation(
    X_train: np.ndarray,
    y_train: np.ndarray,
    bearings: np.ndarray | None,
    coverage: float,
    profile: str,
    source_conditions: list[str] | None,
    target_condition: str | None,
    condition_labels: np.ndarray | None,
    vector_current_fn: Callable[..., dict[str, float]],
    soft_band_fn: Callable[[np.ndarray], np.ndarray],
    psd_cdf_fn: Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]],
    psd_w1_fn: Callable[[np.ndarray, np.ndarray], float],
    stat_vector_fn: Callable[[np.ndarray], np.ndarray],
) -> tuple[dict[str, Any], BreezeVerifier]:
    sources, target, labels = _validate_inputs(X_train, y_train, source_conditions, target_condition, condition_labels)
    boundary = _base_boundary(X_train, y_train, target, bearings, coverage)
    classes = {
        cls: _class_morphology_calibration(X_train, y_train, labels, cls, sources, target)
        for cls in CLASSES
    }
    return ({
        "coverage": coverage,
        "profile": profile,
        "regime": "extrapolation",
        "gates": {"sanity": True, "morphology_interpolated": True, "envelope_kinematics": True},
        "cond": target,
        "freqs": _fault_freqs(target),
        "source_conditions": sources,
        "target_condition": target,
        "interval_rule": {
            "q05": INTERVAL_QUANTILES[0],
            "q95": INTERVAL_QUANTILES[1],
            "loo_multiplier": LOO_MULTIPLIER,
            "condition_scale": _condition_scale(),
        },
        "classes": classes,
        "physical": _physical_calibration(X_train, y_train, labels, sources, target, vector_current_fn),
        "report_only": _report_only_calibration(X_train, y_train, soft_band_fn, psd_cdf_fn, psd_w1_fn, stat_vector_fn),
        "boundary": _boundary_payload(boundary),
    }, boundary)


def _report_only_scores(
    report_calibration: dict[str, Any],
    w: np.ndarray,
    cls: str,
    soft_band_fn: Callable[[np.ndarray], np.ndarray],
    psd_w1_fn: Callable[[np.ndarray, np.ndarray], float],
    stat_vector_fn: Callable[[np.ndarray], np.ndarray],
) -> dict[str, Any]:
    rec = report_calibration[cls]
    stats = stat_vector_fn(w)
    z = (stats - np.asarray(rec["stats_median"])) / np.asarray(rec["stats_scale"])
    return {
        "stats_axis_distance": float(np.sqrt(np.sum(z**2))),
        "soft_spectrum": soft_band_fn(w[0]),
        "soft_spectrum_source_q01": np.asarray(rec["soft_spectrum_q01"]),
        "soft_spectrum_source_q99": np.asarray(rec["soft_spectrum_q99"]),
        "psd_w1": psd_w1_fn(w[0], np.asarray(rec["psd_w1_ref_cdf"])),
        "psd_w1_source_q99": float(rec["psd_w1_q99"]),
    }


def verify_extrapolation(
    calib: dict[str, Any],
    boundary: BreezeVerifier,
    w: np.ndarray,
    cls: str,
    observed_condition: str | None,
    vector_current_fn: Callable[..., dict[str, float]],
    soft_band_fn: Callable[[np.ndarray], np.ndarray],
    psd_w1_fn: Callable[[np.ndarray, np.ndarray], float],
    stat_vector_fn: Callable[[np.ndarray], np.ndarray],
) -> dict[str, Any]:
    if cls not in CLASSES:
        raise ValueError(f"unknown class {cls}")
    kinematics_condition = observed_condition or str(calib["target_condition"])
    if kinematics_condition not in CONDITIONS:
        raise ValueError(f"unknown observed condition {kinematics_condition}")
    base = boundary.verify(w, cls)
    sanity = base["gates"]["sanity"]
    report: dict[str, Any] = {
        "class": cls,
        "profile": calib["profile"],
        "regime": "extrapolation",
        "morphology_target_condition": calib["target_condition"],
        "kinematics_condition": kinematics_condition,
        "feasible": bool(sanity["passed"]),
        "gates": {"sanity": {**sanity, "boundary_source": "strict_signal_validity"}},
        "scores": {},
    }
    if not report["feasible"]:
        return report

    freqs = _fault_freqs(kinematics_condition)
    morphology = _morphology_features(w, cls, freqs)
    predictable = calib["classes"][cls]["predictable"]
    morphology_pass = True
    messages = []
    details = []
    for feature, interval in predictable.items():
        value = float(morphology[feature])
        lo, hi = float(interval["interval_lo"]), float(interval["interval_hi"])
        passed = bool(lo <= value <= hi)
        details.append({"feature": feature, "value": value, "lo": lo, "hi": hi, "passed": passed, "loo_mae_median": interval["loo_mae_median"]})
        if not passed:
            morphology_pass = False
            messages.append(f"{feature}={value:.6g} outside extrapolated interval [{lo:.6g},{hi:.6g}]")
    report["gates"]["morphology_interpolated"] = {
        "passed": morphology_pass,
        "messages": messages,
        "boundary_source": "interpolated_idw_q05_q95_plus_2x_loo_mae",
    }
    report["scores"]["morphology_interpolated"] = details
    report["feasible"] = report["feasible"] and morphology_pass

    report_only = calib["classes"][cls]["report_only"]
    report["gates"]["morphology_report_only"] = {
        "passed": True,
        "messages": ["weak and not-predictable morphology is recorded, not used for extrapolation rejection"],
        "boundary_source": "report_only_weak_or_not_predictable",
    }
    report["scores"]["morphology_report_only"] = [
        {"feature": feature, "value": float(morphology[feature]), "source_empirical_union": rec["source_empirical_union"]}
        for feature, rec in report_only.items()
    ]
    report["gates"]["source_domain_report_only"] = {
        "passed": True,
        "messages": ["statistics, soft spectrum, and PSD-W1 are reported without in-domain rejection"],
        "boundary_source": "report_only_source_empirical_union",
    }
    report["scores"]["source_domain_report_only"] = _report_only_scores(
        calib["report_only"], w, cls, soft_band_fn, psd_w1_fn, stat_vector_fn
    )

    physical = calib["physical"]
    if cls in ("OR", "IR"):
        evidence = _envelope_evidence(w[0], cls, freqs)
        floor = float(physical[cls]["envelope_fault_floor"])
        contrast_floor = float(physical[cls]["envelope_contrast_floor"])
        position_pass = bool(evidence["fund_proximity_err_hz"] <= evidence["tolerance_hz"])
        envelope_pass = bool(
            position_pass
            and evidence["fund_prominence"] >= floor
            and evidence["rate_contrast"] >= contrast_floor
        )
        report["gates"]["envelope_kinematics"] = {
            "passed": envelope_pass,
            "messages": [] if envelope_pass else [
                f"{cls} envelope peak {evidence['fund_peak_hz']:.3f} Hz / prominence {evidence['fund_prominence']:.3f} / rate contrast {evidence['rate_contrast']:.3f} fails strict target-rate evidence"
            ],
            "boundary_source": "strict_fixed_demodulation_band_target_kinematics_source_q10_evidence_and_rate_contrast",
        }
        report["scores"]["envelope_kinematics"] = {
            **evidence,
            "source_q10_prominence_floor": floor,
            "source_q10_rate_contrast_floor": contrast_floor,
        }
        report["feasible"] = report["feasible"] and envelope_pass

        mcsa = vector_current_fn(w[1], w[2], freqs, cls)
        mcsa_cal = physical[cls]
        if mcsa_cal["mcsa_hard_gate"]:
            target = float(freqs["BPFO"] if cls == "OR" else freqs["BPFI"])
            df = FS / w.shape[1]
            tol = max(2.0 * df, 0.02 * target)
            left_ok = np.isfinite(mcsa["left_peak_freq"]) and abs(mcsa["left_peak_freq"] - (mcsa["fe"] - target)) <= tol
            right_ok = np.isfinite(mcsa["right_peak_freq"]) and abs(mcsa["right_peak_freq"] - (mcsa["fe"] + target)) <= tol
            mcsa_pass = bool(left_ok and right_ok and mcsa["sideband_prominence"] >= float(mcsa_cal["mcsa_fault_floor"]))
            mcsa_messages = [] if mcsa_pass else ["vector-current sidebands do not meet strict source-separated target-frequency evidence"]
            source = "strict_target_mcsa_position_source_q01_evidence"
        else:
            mcsa_pass = True
            mcsa_messages = ["MCSA is report-only because source fault and healthy evidence do not separate at fixed q01/q99 tails"]
            source = "report_only_source_fault_healthy_not_separable"
        report["gates"]["vector_mcsa"] = {"passed": mcsa_pass, "messages": mcsa_messages, "boundary_source": source}
        report["scores"]["vector_mcsa"] = {**mcsa, "source_q01_fault_floor": mcsa_cal["mcsa_fault_floor"], "source_q99_healthy_ceiling": mcsa_cal["mcsa_healthy_ceiling"]}
        report["feasible"] = report["feasible"] and mcsa_pass
    else:
        absence_scores = []
        absence_pass = True
        for fault in ("OR", "IR"):
            evidence = _envelope_evidence(w[0], fault, freqs)
            ceiling = float(physical["healthy"]["healthy_absence"][fault]["prominence_ceiling"])
            passed = bool(evidence["fund_prominence"] <= ceiling)
            absence_scores.append({"fault": fault, **evidence, "source_q99_ceiling": ceiling, "passed": passed})
            absence_pass = absence_pass and passed
        report["gates"]["healthy_fault_absence"] = {
            "passed": absence_pass,
            "messages": [] if absence_pass else ["healthy candidate contains source-incompatible periodic fault evidence at target kinematics"],
            "boundary_source": "strict_target_fault_absence_source_q99_ceiling",
        }
        report["scores"]["healthy_fault_absence"] = absence_scores
        report["feasible"] = report["feasible"] and absence_pass
    return report
