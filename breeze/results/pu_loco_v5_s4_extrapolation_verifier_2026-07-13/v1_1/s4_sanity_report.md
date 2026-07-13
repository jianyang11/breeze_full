# PU LOCO v5 S4 extrapolation sanity audit

## Boundary

all audits are train-bearing-only; no pseudo-held-out or formal held-out waveform is read

## Decision

- Overall sanity status: **FAIL**.
- Predeclared healthy criterion: pooled raw rate >= 0.60 and every source raw rate >= 0.40.
- Predeclared negative-control criterion: 0 admitted wrong-label, white-noise, and constant windows.

## Healthy carrier admission

| target | pooled raw rate | source raw rates | target sanity |
|---|---:|---|---|
| N09_M07_F10 | 0.783 | N15_M01_F10=0.820, N15_M07_F04=0.710, N15_M07_F10=0.820 | FAIL |
| N15_M01_F10 | 0.867 | N09_M07_F10=0.740, N15_M07_F04=0.950, N15_M07_F10=0.910 | FAIL |
| N15_M07_F04 | 0.883 | N09_M07_F10=0.740, N15_M01_F10=0.930, N15_M07_F10=0.980 | FAIL |
| N15_M07_F10 | 0.923 | N09_M07_F10=0.880, N15_M01_F10=0.900, N15_M07_F04=0.990 | FAIL |

## Negative controls

| target | control | admitted / n |
|---|---|---:|
| N09_M07_F10 | real_OR_labeled_IR | 31 / 100 |
| N09_M07_F10 | real_IR_labeled_OR | 27 / 100 |
| N09_M07_F10 | white_noise_labeled_healthy | 0 / 100 |
| N09_M07_F10 | white_noise_labeled_OR | 45 / 100 |
| N09_M07_F10 | white_noise_labeled_IR | 0 / 100 |
| N09_M07_F10 | constant_labeled_healthy | 0 / 100 |
| N09_M07_F10 | constant_labeled_OR | 0 / 100 |
| N09_M07_F10 | constant_labeled_IR | 0 / 100 |
| N15_M01_F10 | real_OR_labeled_IR | 54 / 100 |
| N15_M01_F10 | real_IR_labeled_OR | 37 / 100 |
| N15_M01_F10 | white_noise_labeled_healthy | 0 / 100 |
| N15_M01_F10 | white_noise_labeled_OR | 58 / 100 |
| N15_M01_F10 | white_noise_labeled_IR | 54 / 100 |
| N15_M01_F10 | constant_labeled_healthy | 0 / 100 |
| N15_M01_F10 | constant_labeled_OR | 0 / 100 |
| N15_M01_F10 | constant_labeled_IR | 0 / 100 |
| N15_M07_F04 | real_OR_labeled_IR | 27 / 100 |
| N15_M07_F04 | real_IR_labeled_OR | 42 / 100 |
| N15_M07_F04 | white_noise_labeled_healthy | 0 / 100 |
| N15_M07_F04 | white_noise_labeled_OR | 59 / 100 |
| N15_M07_F04 | white_noise_labeled_IR | 52 / 100 |
| N15_M07_F04 | constant_labeled_healthy | 0 / 100 |
| N15_M07_F04 | constant_labeled_OR | 0 / 100 |
| N15_M07_F04 | constant_labeled_IR | 0 / 100 |
| N15_M07_F10 | real_OR_labeled_IR | 48 / 100 |
| N15_M07_F10 | real_IR_labeled_OR | 42 / 100 |
| N15_M07_F10 | white_noise_labeled_healthy | 0 / 100 |
| N15_M07_F10 | white_noise_labeled_OR | 59 / 100 |
| N15_M07_F10 | white_noise_labeled_IR | 82 / 100 |
| N15_M07_F10 | constant_labeled_healthy | 0 / 100 |
| N15_M07_F10 | constant_labeled_OR | 0 / 100 |
| N15_M07_F10 | constant_labeled_IR | 0 / 100 |

## Fault transfer audit

The source-kinematics column measures morphology-boundary transfer. The literal-target column is a strict kinematic mismatch control, not a success metric.

| target | source | class | transfer pass / n | literal-target pass / n |
|---|---|---|---:|---:|
| N09_M07_F10 | N15_M01_F10 | OR | 81 / 100 | 34 / 100 |
| N09_M07_F10 | N15_M01_F10 | IR | 83 / 100 | 79 / 100 |
| N09_M07_F10 | N15_M07_F04 | OR | 83 / 100 | 33 / 100 |
| N09_M07_F10 | N15_M07_F04 | IR | 63 / 100 | 67 / 100 |
| N09_M07_F10 | N15_M07_F10 | OR | 85 / 100 | 30 / 100 |
| N09_M07_F10 | N15_M07_F10 | IR | 80 / 100 | 81 / 100 |
| N15_M01_F10 | N09_M07_F10 | OR | 91 / 100 | 31 / 100 |
| N15_M01_F10 | N09_M07_F10 | IR | 83 / 100 | 74 / 100 |
| N15_M01_F10 | N15_M07_F04 | OR | 78 / 100 | 78 / 100 |
| N15_M01_F10 | N15_M07_F04 | IR | 65 / 100 | 65 / 100 |
| N15_M01_F10 | N15_M07_F10 | OR | 81 / 100 | 81 / 100 |
| N15_M01_F10 | N15_M07_F10 | IR | 87 / 100 | 87 / 100 |
| N15_M07_F04 | N09_M07_F10 | OR | 86 / 100 | 31 / 100 |
| N15_M07_F04 | N09_M07_F10 | IR | 77 / 100 | 66 / 100 |
| N15_M07_F04 | N15_M01_F10 | OR | 73 / 100 | 73 / 100 |
| N15_M07_F04 | N15_M01_F10 | IR | 80 / 100 | 80 / 100 |
| N15_M07_F04 | N15_M07_F10 | OR | 73 / 100 | 73 / 100 |
| N15_M07_F04 | N15_M07_F10 | IR | 81 / 100 | 81 / 100 |
| N15_M07_F10 | N09_M07_F10 | OR | 94 / 100 | 36 / 100 |
| N15_M07_F10 | N09_M07_F10 | IR | 84 / 100 | 74 / 100 |
| N15_M07_F10 | N15_M01_F10 | OR | 81 / 100 | 81 / 100 |
| N15_M07_F10 | N15_M01_F10 | IR | 86 / 100 | 86 / 100 |
| N15_M07_F10 | N15_M07_F04 | OR | 79 / 100 | 79 / 100 |
| N15_M07_F10 | N15_M07_F04 | IR | 64 / 100 | 64 / 100 |
