# Private machine-tool v3 — zero-API downstream report

## Scope and integrity

- Inner train: file IDs `1/2/4/5`; inner validation: ID `10` only.
- Formal IDs `7/8` read: `0`; API requests: `0`.
- Ten fixed seeds per cell; v2 CNN/normalization settings; Acc and Macro-F1.
- Under downstream amendment 1, the synthetic budget is 10/class at
  `n_real=10`, and 20/class at `n_real=25/50`, for every non-real method.

## Means over ten seeds

| method | `n_real` | Acc | Macro-F1 | `noise_aug` Acc / Macro-F1 | cells at least `noise_aug` |
|---|---:|---:|---:|---:|---:|
| S-A directional | 10 | 0.2591 | 0.2690 | 0.3004 / 0.2884 | no / no |
| S-A directional | 25 | 0.3323 | 0.3173 | 0.3117 / 0.3036 | yes / yes |
| S-A directional | 50 | 0.4101 | 0.4016 | 0.3654 / 0.3744 | yes / yes |
| S-B carrier mix | 10 | 0.2175 | 0.2097 | 0.3004 / 0.2884 | no / no |
| S-B carrier mix | 25 | 0.2615 | 0.2531 | 0.3117 / 0.3036 | no / no |
| S-B carrier mix | 50 | 0.3891 | 0.3856 | 0.3654 / 0.3744 | yes / yes |

The frozen success rule requires both metrics to be at least `noise_aug` in at
least five of six shot-by-metric cells. S-A reaches `4/6`; S-B reaches `2/6`.
Both are therefore `BLOCKED`. The corresponding one-sided paired
Wilcoxon-plus-Holm tables are stored beside the seed rows; neither candidate
has a Holm-adjusted significant advantage over `noise_aug` in any cell.

## Decision boundary

S-A is descriptively the stronger of the two zero-API methods, but it is not
eligible for formal evaluation. The conditional S-C branch is now eligible
only after a separate user confirmation that a `DASHSCOPE_API_KEY` is
configured without placing a credential in source control. S-E remains
unstarted because the frozen design has no outcome-independent rule selecting
one of the two BREEZE pools for a union after both fail the primary gate. No
formal data will be read while these conditions remain unresolved.
