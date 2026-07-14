# PU LOCO v6 CSCoh source-only separability diagnostic

## Boundary

all v6 Step 1 diagnostics are train-bearing-only; pseudo-held-out and formal held-out PU windows are unread

## Frozen decision

- Window criterion: true-class q10 must exceed wrong-class and white-noise q90.
- Pool criterion: every 20-window true pool must pass the one-sided paired Wilcoxon test (`p < 0.01`, median margin > 0), while every wrong-class and white-noise pool must fail.
- A target terminates v6 CSCoh only when both OR and IR fail both criteria.

| target | asserted | true q10 | wrong q90 | white q90 | single | true pools | negative admitted | pool | target decision |
|---|---|---:|---:|---:|---|---:|---:|---|---|
| N09_M07_F10 | OR | -0.41138 | -0.34577 | -0.33450 | FAIL | 0/60 | 0/120 | FAIL | STOP |
| N09_M07_F10 | IR | 0.16845 | 0.25782 | 0.20627 | FAIL | 60/60 | 120/120 | FAIL | STOP |
| N15_M01_F10 | OR | -0.40650 | 0.06072 | 0.06423 | FAIL | 20/60 | 40/120 | FAIL | STOP |
| N15_M01_F10 | IR | -0.01599 | 0.25274 | 0.19703 | FAIL | 40/60 | 80/120 | FAIL | STOP |
| N15_M07_F04 | OR | -0.40419 | 0.06071 | 0.06117 | FAIL | 20/60 | 40/120 | FAIL | STOP |
| N15_M07_F04 | IR | -0.01599 | 0.24827 | 0.19999 | FAIL | 40/60 | 80/120 | FAIL | STOP |
| N15_M07_F10 | OR | -0.40087 | 0.06069 | 0.06201 | FAIL | 20/60 | 40/120 | FAIL | STOP |
| N15_M07_F10 | IR | -0.01598 | 0.24443 | 0.19747 | FAIL | 40/60 | 80/120 | FAIL | STOP |

## Overall

- Overall terminal CSCoh failure: **YES**.
- At least one target permits the predeclared next step: **NO**.
