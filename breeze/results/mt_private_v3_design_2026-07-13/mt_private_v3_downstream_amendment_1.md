# Private machine-tool v3 — downstream amendment 1

**Frozen:** 2026-07-13, before any private-MT v3 downstream metric was produced. This amendment is part of the inner-development protocol only and does not authorize reading formal IDs `7/8`.

## Trigger and scope

The original design specified `n_real={10,25,50}` and `n_syn=20/class` for every non-real method. The first attempted `n_real=10` execution reached the existing `noise_augment` capacity check before any model fit or result row: the no-replacement noise baseline cannot draw 20 source windows per class from a 10-per-class real subset. No downstream CSV, metric, selection decision, formal window, or API request was produced by that attempt.

Changing `noise_aug` to reuse source carriers would alter its frozen definition. Removing the low-shot cell would remove the intended few-shot test. This amendment instead applies one common, pre-execution budget rule to every non-real comparator.

## Amended synthetic budget

| `n_real` per class | `n_syn` per class for `noise_aug`, S-A, S-B, and any later S-C/S-E/union comparator |
|---:|---:|
| 10 | 10 |
| 25 | 20 |
| 50 | 20 |

Thus the `n_real=10` cell uses a 1:1 real-to-synthetic expansion. The `n_real=25` and `50` cells retain the original 20-per-class synthetic budget. `real_only` always records `n_syn=0`.

For S-A/S-B at `n_real=10`, the first ten immutable admitted windows per class, ordered by frozen deterministic attempt index in the existing 20/class manifest, are used. The remaining ten are neither modified nor selected on the validation result. `noise_aug` continues to use distinct source windows and no replacement; renderer rules, admission, pool membership, seeds, CNN settings, metrics, paired Wilcoxon direction, Holm family, access boundary, and formal-selection rule are unchanged.

This amendment is a capacity correction made before outcome observation, not a response to a downstream result.
