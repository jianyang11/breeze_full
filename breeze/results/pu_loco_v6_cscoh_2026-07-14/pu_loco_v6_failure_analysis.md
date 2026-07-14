# PU LOCO v6 failure analysis — CSCoh source evidence is not discriminative

## Frozen outcome

v6 stops at Step 1. The predeclared CSCoh source-evidence gate failed in all
four internal pseudo-held-out targets. The all-target source-only batch had
already been launched when the first target (`N09_M07_F10`) met the terminal
condition, so its other three independent checkpoints were allowed to finish
and are retained below; they were not used to alter a rule or start a
subsequent experiment. Each checkpoint loads only its three source operating
conditions' train-bearing windows. Pseudo-held-out target waveforms and all
registered formal LOCO windows were unread. Step 2 verifier integration, the
four-piece admission audit, synthetic-pool construction, downstream
comparison, preregistration, and formal held-out execution are prohibited.

The API increment is **0**. No recipe generation, waveform repair, threshold
change, class-specific tuning, or candidate-family addition was attempted.

## Frozen CSCoh protocol

The design was committed before this diagnostic. It used a training-free
Hann-tapered averaged cyclic periodogram (`nperseg=512`, overlap `384`,
`nfft=2048`, 500--3800 Hz carrier band) and fixed BPFO/BPFI/shaft alpha
families with one-bin (±3.90625 Hz) tolerance. OR/IR identity was the
predeclared log ratio of target-family to competing-family strength.

For each asserted label, the single-window criterion required true-class
margin q10 above both real wrong-class and white-noise q90. The pool criterion
used 20 fixed-replicate 20-window pools per source condition (60 true pools,
60 wrong-class pools, and 60 white-noise pools): every true pool had to pass a
one-sided paired Wilcoxon test (`p < 0.01`, positive median), while every
negative pool had to fail. Because the score uses vibration channel 0 only,
unit-variance white-noise vibration sequences used 100 windows at each source
condition's own kinematic alpha family (300 windows total per asserted class).

## Result

| internal target | asserted class | true q10 | wrong-class q90 | white-noise q90 | single-window | true pools passed | negative pools admitted | pool |
|---|---|---:|---:|---:|---|---:|---:|---|
| N09_M07_F10 | OR | -0.41138 | -0.34577 | -0.33450 | fail | 0 / 60 | 0 / 120 | fail |
| N09_M07_F10 | IR | 0.16845 | 0.25782 | 0.20627 | fail | 60 / 60 | 120 / 120 | fail |
| N15_M01_F10 | OR | -0.40650 | 0.06072 | 0.06423 | fail | 20 / 60 | 40 / 120 | fail |
| N15_M01_F10 | IR | -0.01599 | 0.25274 | 0.19703 | fail | 40 / 60 | 80 / 120 | fail |
| N15_M07_F04 | OR | -0.40419 | 0.06071 | 0.06117 | fail | 20 / 60 | 40 / 120 | fail |
| N15_M07_F04 | IR | -0.01599 | 0.24827 | 0.19999 | fail | 40 / 60 | 80 / 120 | fail |
| N15_M07_F10 | OR | -0.40087 | 0.06069 | 0.06201 | fail | 20 / 60 | 40 / 120 | fail |
| N15_M07_F10 | IR | -0.01598 | 0.24443 | 0.19747 | fail | 40 / 60 | 80 / 120 | fail |

For OR, the true class has a lower, not higher, lower-tail margin than both
negative references in every target; only 0--20 of 60 true pools are accepted.
For IR, the apparent positive pool evidence is non-discriminative: 80--120 of
120 wrong-class/white-noise pools meet the same test. Thus multi-window
aggregation amplifies a shared signed bias rather than separating IR from
prohibited controls.

Both asserted classes fail both predeclared criteria in every target. This
meets the v6 terminal CSCoh condition; there is no admissible parameter
adjustment or subsequent cross-condition candidate under the frozen protocol.
The detailed, machine-readable records are the four
`source_separability_N*.json` checkpoints,
`source_separability_summary.csv`, and `source_separability_summary.json`.

## Interpretation

The v6 hypothesis is falsified on the source-only evidence boundary. For this
PU representation and fixed short-window estimator, cyclic spectral coherence
does not turn OR/IR rate evidence into a class-discriminative certificate: OR
has the wrong signed ordering, and IR is equally supported by wrong-class real
windows and white noise. The failure is about evidence discrimination, not
about an insufficiently permissive acceptance threshold.

## Manuscript-safe scope

> Cross-condition PU LOCO was retained as a stress test rather than a claimed
> generalization result. A final source-only cyclic-spectral-coherence audit
> found that OR evidence had the wrong signed ordering and that IR pool-level
> evidence also accepted wrong-class and white-noise controls. We therefore
> froze the analysis before verifier deployment or synthetic-pool construction.
> The result delineates the method's scope: richer spectral representations do
> not by themselves establish a transferable class-identity certificate.
