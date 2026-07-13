# S4 design — extrapolation-regime admission verifier

## Status and freeze point

This document is the preregistered design for S4. It was written before any
S4 calibration or S4 real-window verification. Once the first S4 sanity audit
starts, the rules below are frozen. S4 is an internal-development method only:
registered PU LOCO held-out windows are not read for calibration, selection,
or tuning.

The trigger is the v4 carrier audit: a target-kinematic in-domain v2 verifier
admitted only 0--1 of 100 real source-condition healthy windows per source
condition. That result is incompatible with using the frozen in-domain
morphology domain as an admission domain for a different operating condition.
It does not justify admitting arbitrary signals.

## Scope and invariants

- Existing `BreezeVerifierV2` behavior is the `in_domain` regime and is not
  changed or rerun. Historical v1--v4 artifacts remain in-domain artifacts.
- `extrapolation` is calibrated from the three source-condition train-bearing
  windows for one internal target plus fixed condition metadata
  `(rpm, torque, radial load)`. Target waveform windows are not read.
- The deterministic condition predictor is inverse-distance weighting after
  scaling each metadata coordinate by its standard deviation across the four
  configured PU conditions. It is the same geometry used by the v3
  morphology diagnostic; it is not fitted to an outcome.
- The interval multiplier is fixed at **k = 2.0**. A predictable-feature
  target interval is `IDW(q05), IDW(q95)` expanded on each side by
  `2.0 × LOO-MAE(median)`, where LOO-MAE is computed by withholding one of
  the three source conditions at a time. No target window selects k, a
  quantile, a feature, or an interval.
- All candidates are evaluated once. Rejection discards the waveform; it
  never triggers waveform repair, threshold adaptation, or admission by
  retry.

## Certificate semantics and cross-condition audit semantics

Every S4 certificate records `regime: extrapolation`, `morphology_target`,
`kinematics_condition`, and a `boundary_source` for every gate.

At generation time both conditions are the target: morphology is admitted to
the target extrapolation interval and physical frequencies are checked at the
target rpm. For a *real source-window audit*, a source fault window cannot
truthfully meet a different-rpm target BPFO/BPFI. The audit therefore records
two distinct cases:

1. **Morphology-transfer audit:** target-B morphology intervals with source-A
   observed kinematics. This tests whether the target-domain morphology
   admission boundary falsely rejects real source-condition signals while
   preserving their known physical frequency.
2. **Literal target-kinematics mismatch control:** the same source-A fault
   evaluated at target-B kinematics. It is expected to be rejected whenever
   the target frequencies differ; counting such a signal as a target-B pass
   would weaken the hard physical constraint.

Healthy signals have no fault rate, so their carrier audit uses target
kinematics directly.

## Gate table

| Gate | in-domain v2 behavior | extrapolation behavior | boundary source and rationale |
|---|---|---|---|
| Sanity | finite, exact `(3, WIN)` shape, nonconstant channels, no large repeated segment | **hard, unchanged** | `strict`: these are representation/measurement validity constraints, independent of operating condition. Constant-signal negative control must fail here. |
| Robust statistics union | hard legacy-quantile OR axis-ellipsoid test over the pooled sources | **report-only** | `report-only`: it entangles amplitude, kurtosis, currents, and background morphology, several of which are weak or not predictable in the v3 map. The v4 0--1% real-carrier admission proves it is not a valid cross-condition hard domain. Distances are retained in the certificate. |
| Soft spectrum and PSD-W1 | hard pooled-source coordinate interval and median-reference distance | **report-only** | `report-only`: all-band/PSD distances mix predictable and not-predictable background spectrum. In particular IR 500--1000 Hz is `not_predictable` (LOO rel-MAE 0.917); a target point gate is unsupported. Source empirical union statistics are recorded for audit. |
| Predictable vibration morphology | implicit within the in-domain statistics/spectrum gates | **hard predicted interval** for map-supported features | `interpolated`: source-only IDW q05/q95 plus fixed 2×LOO-MAE. Features are: healthy `{vib_rms, vib_crest, band_3000_4000, ir_resonance_3000_3600}`; OR `{vib_crest, band_500_1000, or_resonance_600_1200}`; IR `{vib_crest, vib_kurtosis, env_peak_prominence, mod_depth_fr, ir_resonance_3000_3600}`. These are the v3 map's `interpolatable` entries. |
| Weak/not-predictable morphology | implicitly hard when carried by the pooled v2 vectors | **report-only** | `report-only`: weak features and, specifically, IR 500--1000 Hz and IR 600--1200 Hz have no defensible target point prediction. The certificate records value plus source-condition empirical union; it never turns the union into a target-selected threshold. |
| Fault envelope kinematics | hard envelope evidence in source-selected resonance bands | **hard** in fixed physical demodulation bands: OR 600--1200 Hz, IR 3000--3600 Hz | `strict`: the maximum must be within the resolution/2%-of-fault-frequency tolerance around the applicable BPFO/BPFI and its prominence must exceed the fixed pooled-source q01 evidence floor. This preserves target rate/peak-location physics while using a conservative source-only floor. |
| Healthy fault absence | hard forbidden-fault envelope maximum | **hard** target-frequency absence test | `strict`: at target BPFO/BPFI, prominence must not exceed the fixed pooled-source q99 healthy floor. This prevents a periodic fault waveform from entering the healthy class without treating broad background morphology as a target point estimate. |
| Vector-current MCSA | hard only when v2 source faults separate from healthy | **hard when separable; otherwise report-only** | `strict` when a pooled-source q01 fault-evidence floor is above the pooled healthy q99 floor; locations remain tied to `fe ± BPFO/BPFI` with the existing resolution/2% tolerance. If the source data do not establish separation, no arbitrary current threshold is invented; the score/location is report-only. |

The envelope and MCSA q01/q99 tails are fixed prior to S4 testing. They are
not selected from target outcomes and are deliberately used only for physical
presence/absence evidence, not for target-specific background similarity.

## Step 1 pass/fail criteria

For each target verifier, sample 100 source train-bearing healthy windows per
source condition using the v4 deterministic carrier-audit schedule. The
predeclared necessary condition is pooled **raw** healthy admission of at
least 60/100 and no source-condition raw admission below 40/100. Frozen-noise
admission is reported but does not select a boundary.

The fault transfer audit reports OR and IR separately under the two semantics
above. It is diagnostic evidence, not a source of threshold tuning. Negative
controls are mandatory: a real OR window labeled IR, a real IR window labeled
OR, white-noise windows, and constant windows must all be rejected. If the
healthy criterion or any negative control fails, no S2/S1 pool is reopened;
the result is an S4 failure/audit report rather than a relaxed gate.

## Downstream protocol after a successful sanity audit

Only then: all four internal pseudo-LOCO targets run zero-API
`morphology_idw`, `morphology_nearest`, and BREEZE-H at five/class smoke,
followed by `n_syn=20/class` only for balanced pools. BREEZE-U uses exactly
half `noise_aug` and half the selected admitted BREEZE pool per class. The
internal evaluator uses `--normalize none`, `n_real={5,10,25}`, 10 fixed
seeds, and the frozen four-fold rule on both Accuracy and Macro-F1. Formal
held-out access remains prohibited unless one unique candidate passes every
required internal cell and a v5 preregistration is committed first.

## Reproducibility and API ledger

Result roots, commands, calibration JSON, certificate summaries, and
non-sensitive hashes are retained per subexperiment. Raw data, generated
arrays, checkpoints, and credentials are not committed. S4 through the first
internal comparison add zero API calls; the existing ledger remains 1131/3000.
