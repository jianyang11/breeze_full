# S3 decision — retain the original downstream representation

## Protocol and integrity

- Scope: four train-bearing-only internal pseudo-LOCO folds; registered PU
  LOCO held-out windows were not read.
- Matrix: `real_only` and `noise_aug`, `n_real={5,10,25}`, 10 fixed seeds,
  20 epochs, with both `none` and `per-window-rms` representations.
- Verified evidence: `verified_complete/` contains eight CSV files, each with
  exactly 30 unique `(normalization, n_real, seed)` rows. The full summary is
  `verified_complete_report.md`.
- An earlier `complete/` execution is retained as an invalid concurrency audit:
  it contains 14 duplicated keys created after a lost front-end session was
  restarted before its child writers finished. Its bit-identical duplicates are
  not deduplicated or used in this decision. The evaluator now holds an
  exclusive POSIX lock for the entire read-compute-append transaction, and the
  clean matrix was regenerated from scratch.

## Result

Per-window RMS normalization helps the weak `real_only` baseline at low shots,
but it does not consistently improve the development reference baseline
`noise_aug`, which is the S2/S1/S5 comparison target:

| `noise_aug` four-fold mean | Acc delta (RMS − none) | Macro-F1 delta (RMS − none) |
|---|---:|---:|
| n_real=5 | +0.0154 | -0.0052 |
| n_real=10 | +0.0324 | +0.0158 |
| n_real=25 | -0.0932 | -0.1389 |

At `n_real=25`, RMS reduces both metrics in every pseudo-held-out fold. It
therefore cannot be selected as a generally beneficial cross-condition
representation under the preregistered internal-development rule.

## Decision

Subsequent S2, S1, and S5 comparisons will use `--normalize none` for every
method, preserving the original representation and a fair comparison to
`noise_aug`. S3 is an honest negative ablation, not a candidate for formal
held-out evaluation.

The optional order-domain branch is not implemented: every current processed
PU NPZ contains only `windows`, `file_ids`, `cls`, `bearing`, and `cond`; it
does not include a tachometer, angular position, or window-level speed trace.
Constructing an angular resampling reference from these files would require an
unobserved signal contract and is therefore prohibited.
