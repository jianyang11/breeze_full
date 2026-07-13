# S4 v1.1 sanity failure — healthy admission recovered, class discrimination did not

## Scope

This zero-API rerun uses the v1.1 amendment only: target-frequency healthy
calibration and a source q10 asserted-rate-versus-competing-rate contrast. All
four target verifiers use only the other three operating conditions'
train-bearing windows. No pseudo-held-out or formal held-out waveform was
loaded. v1 artifacts remain unchanged in the parent directory.

## Predeclared result

| target | raw healthy rate | minimum source healthy rate | prohibited negatives admitted / 800 | status |
|---|---:|---:|---:|---|
| N09_M07_F10 | 0.783 | 0.710 | 103 | fail |
| N15_M01_F10 | 0.867 | 0.740 | 203 | fail |
| N15_M07_F04 | 0.883 | 0.740 | 180 | fail |
| N15_M07_F10 | 0.923 | 0.880 | 231 | fail |

The healthy requirement is met in every target, confirming that v1's
source-frequency healthy-absence calibration was the cause of the previous
99%-style healthy rejection. However, the unchanged mandatory negative
criterion remains violated: all targets admit wrong-label faults and many
OR/IR white-noise controls. Constants and healthy-labeled white noise remain
rejected, so this is not a shape/sanity issue.

## Consequence

S4 v1.1 is not an admission regime for BREEZE pools. S1, S2, and S5 remain
closed, and no downstream comparison or formal experiment is run. Raising the
existing contrast quantile after observing these controls would be an
unprincipled threshold chase. The only admissible next diagnostic is to test,
on source train data alone, whether a **new physical rate/harmonic/modulation
feature** separates true class evidence from wrong-class and white-noise
evidence. If no such source-only separation exists, S4 is frozen as an honest
failure rather than further relaxed or tuned.
