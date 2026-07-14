# PU LOCO v6 design — cyclic spectral coherence and multi-window evidence

## Status, scope, and freeze point

This document is the v6 design freeze. It is written before any v6 CSCoh
calibration, real-window diagnostic, verifier audit, pool construction, or
downstream result. v6 is the final permitted PU cross-condition attempt. All
development evidence is restricted to `config.SPLIT['train']` bearings. For
each internal pseudo-held-out operating condition, its waveform windows are
unread during calibration; only the other three source-condition train-bearing
windows and the configured condition metadata may be used. Registered formal
LOCO windows remain unread unless a later preregistration is committed.

The v5 failure is treated as an evidence-source failure, not an invitation to
tune an envelope threshold: one-window envelope-rate scores did not separate
true faults from wrong-class faults or white noise. v6 replaces that identity
evidence with a fixed cyclic-spectral-coherence (CSCoh) measurement and a
predeclared pool-level statistic. No parameter below may be selected from v6
real-window, negative-control, pool, or downstream outcomes.

API increment through Steps 1--3 is fixed at zero. The existing ledger is
1131/3000; no recipe-generation request is permitted without an owner-approved
amendment capped at 50 requests.

## Candidate family (complete and closed)

The only possible pool families are `BREEZE-H`, `morphology_idw`,
`morphology_nearest`, and `BREEZE-U`. `BREEZE-H` is the existing real
source-healthy carrier plus target-kinematic injection construction;
`morphology_idw` and `morphology_nearest` are the existing source-only
morphology constructions. Each is passed once, unmodified, through the v6
admission verifier. `BREEZE-U` contains exactly half frozen `noise_aug` and
half one already-admitted base family per class. Its base family is the unique
winner of the already-frozen internal comparison rule; a tie or no unique
winner makes `BREEZE-U` ineligible. No further candidate family, threshold,
or rejected-waveform repair is allowed after this design.

## CSCoh estimator

For vibration channel 0, v6 uses the magnitude of the normalized averaged
cyclic periodogram:

\[
C_x^\alpha(f) =
 \frac{|\operatorname{mean}_m\{X_m(f+\alpha/2)X_m^*(f-\alpha/2)\}|}
 {\sqrt{\operatorname{mean}_m|X_m(f+\alpha/2)|^2\;
        \operatorname{mean}_m|X_m(f-\alpha/2)|^2}+10^{-12}}.
\]

`m` indexes deterministic overlapping Hann-tapered segments. This is a
training-free Fast-SC/averaged-cyclic-periodogram estimator: it has no learned
component and shares no fitted parameter across classes. The fixed estimator
settings are:

| quantity | frozen value | reason |
|---|---:|---|
| sampling rate | 8000 Hz | processed PU contract |
| analysis length | 2048 samples | processed PU window contract |
| segment length (`nperseg`) | 512 samples | four shaft/fault periods at the slowest BPFO while retaining 13 overlapped estimates per window |
| overlap (`noverlap`) | 384 samples | 128-sample hop gives 13 deterministic segment estimates/window |
| FFT length (`nfft`) | 2048 | 3.90625 Hz interpolation grid, matched to the full window's frequency resolution |
| taper | Hann | standard spectral-leakage control fixed before data inspection |
| carrier-frequency band | 500--3800 Hz | covers the fixed 600--1200 Hz OR and 3000--3600 Hz IR resonance regions without a class-selected band |
| alpha tolerance | ±3.90625 Hz | one fixed FFT-grid interval around each kinematic cyclic frequency |

Complex spectra at non-bin `f ± α/2` are linearly interpolated on the fixed
FFT grid; no peak location is fitted. The feature cache stores only derived
CSCoh scores under `breeze/runs/`, never source waveforms, and is keyed by
window identity, estimator settings, observed condition, and asserted class.

For a condition with shaft rate `fr`, the complete alpha family is
`{fr, 2fr, 3fr, BPFO, 2BPFO, 3BPFO, BPFI, 2BPFI, 3BPFI,
BPFI-fr, BPFI+fr}`. Each member is evaluated at its centre and at the two
fixed tolerance endpoints. Non-positive alpha members are excluded by the
mathematical definition; none occur in the configured PU conditions.

## Fixed window evidence scores

For any alpha family member, its score is the mean CSCoh across the fixed
500--3800 Hz carrier band. Its tolerance score is the maximum of the three
predeclared alpha-grid scores (`centre ± 3.90625 Hz`); this handles the known
FFT grid uncertainty and is applied symmetrically to target and competing
families.

For an asserted OR label, the target family is `{BPFO, 2BPFO, 3BPFO}` and the
competing family is `{BPFI, 2BPFI, 3BPFI}`. For an asserted IR label, the
target family is `{BPFI, 2BPFI, 3BPFI, BPFI-fr, BPFI+fr}` and the competing
family is `{BPFO, 2BPFO, 3BPFO}`. A family strength is the arithmetic mean of
its member tolerance scores. The signed identity margin is

\[
M_c = \log\{(S_{c,\mathrm{target}}+10^{-12}) /
             (S_{c,\mathrm{competing}}+10^{-12})\}.
\]

The log ratio is scale-free and imposes equal treatment of OR and IR. A v6
certificate records both strengths, every alpha score, the margin, and all
estimator settings. Healthy admission retains v5 S4 v1.1 morphology and
sanity semantics; CSCoh identity is only an OR/IR evidence component.

## Source-only Step 1 gate

Each internal target is calibrated only from its three source conditions. For
each asserted fault class, the single-window criterion is fixed to the v5
standard: the true-class margin `q10` must exceed both the wrong-class and
unit-variance white-noise margin `q90`. Because CSCoh uses vibration channel
0 only, the white-noise reference comprises exactly 300 deterministic
2048-sample unit-variance vibration sequences for each `(internal target,
asserted class)` pair, generated with a seed key derived from `20260714` and
that pair. They are split as 100 windows at each source condition's own
kinematic alpha family, so the noise reference has the same three-source
composition as the real distribution; it is independent of the source-window
count. No quantile, count, or tolerance may be relaxed.

The multi-window check forms 20 independent, source-condition-stratified
20-window pools per actual class and per white-noise control for every source
condition (60 pools per category/internal target). A pool succeeds for its
asserted label only if all are true: (1) exactly 20 nonzero paired margins,
(2) median margin is greater than zero, and (3) the two-sided-zero-free
Wilcoxon signed-rank test under the predeclared one-sided alternative
`margin > 0` returns `p < 0.01`. Every true-class pool must succeed; every
wrong-class and white-noise pool asserted as the tested label must fail.
Sampling uses seed `20260714`, with a distinct deterministic key for target,
source, actual class, asserted class, and replicate. Windows are sampled
without replacement within a pool; pools may reuse windows between fixed
replicates.

The v6 evidence upgrade is useful only if the fixed source evidence is
separable. If both fault labels fail both the single-window and pool criteria,
v6 freezes immediately as a CSCoh failure and Steps 2--4 are prohibited. If
single-window evidence fails but the predeclared pool test passes, Step 2 may
proceed because v6 explicitly uses the single-window margin as a soft score
and the pool test as the hard class-identity decision; this is a planned
multi-window aggregation, not a post-hoc relaxation. Conversely, a pool
failure means an individual window cannot be admitted as a fault merely on a
positive margin.

## Step 2 verifier and mandatory admission audit

If Step 1 does not stop, the v6 extrapolation verifier inherits S4 v1.1
sanity and predictable-morphology boundaries exactly. It replaces the fault
class-identity component with the frozen CSCoh window score and 20-window
pool decision above. Calibration distributions and all decision quantities are
computed from three source-condition train-bearing windows only.

Before any pool is built, all four internal targets must pass the following
audit with the existing deterministic S4 schedule: real healthy admission
(pooled raw >= 0.60 and each source >= 0.40), real OR asserted IR and real IR
asserted OR controls (0 admitted), unit-variance white-noise controls (0
admitted), and constant controls (0 admitted). The CSCoh source separability
record from Step 1 is the fourth audit component. Any failed component blocks
pool construction and is recorded as v6 failure analysis; there is no
threshold or morphology amendment.

## Downstream and formal boundary

Only audit-passing base families may run five-per-class smoke pools, then
20/class pools. Internal pseudo-LOCO uses `--normalize none`,
`n_real={5,10,25}`, a 10-seed smoke run before completion, and the existing
fixed 10-seed comparison. A base candidate must meet or exceed `noise_aug` on
both Accuracy and Macro-F1 in at least three of four folds for every
shot-count cell. A single unique candidate satisfying this rule is locked in a
v6 preregistration (code/pool hashes, 40 seeds, paired Wilcoxon, and Holm)
before one formal held-out execution. Any other outcome is frozen as a
cross-condition failure.

## Reproducibility

The implementation test uses a synthetic periodic BPFO impulse train and
white noise. v6 records commands, estimator version/settings, source-only
boundary, seed, result summaries, and failure analyses. Raw datasets,
derived arrays, virtual environments, checkpoints, credentials, and generated
pools are not committed.
