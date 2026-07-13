# PU LOCO v4 S3 — scale-invariant downstream protocol

## Development boundary

This directory contains internal pseudo-LOCO development evidence only.
Every pseudo-held-out fold uses `config.SPLIT['train']` bearings: the selected
condition is internal pseudo-test and the other three conditions are inner
training data. Registered PU LOCO held-out windows are never read.

## Representation contract

`per-window-rms` independently maps every window `x` to
`x[c, :] / sqrt(mean(x[c, :] ** 2))` for each channel. It rejects non-finite
values and zero-RMS channels. The transform occurs after each method has
assembled its full augmented training set and independently for evaluation.
Thus it applies equally to `real_only`, `noise_aug`, and `custom_pool`.

`noise_aug` is unchanged: scale `N(1, 0.04)` plus jitter `0.03 ×` the
few-shot channel standard deviation, before the representation transform.

## Fixed schedule

- Folds: `N09_M07_F10`, `N15_M01_F10`, `N15_M07_F04`, `N15_M07_F10`.
- Baselines: `real_only`, `noise_aug`; shots: `5`, `10`, `25` per class.
- `noise_aug` uses `20` synthetic samples per class; `SimpleCNN` uses 20 epochs.
- Smoke: 2 seeds. Completion: 10 seeds. Checkpoints include normalization mode.

Run with the mandated interpreter and compare `--normalize none` with
`--normalize per-window-rms` through `run_pu_loco_downstream.py`. Summarize
only completed matrices with `summarize_pu_loco_internal.py`.
