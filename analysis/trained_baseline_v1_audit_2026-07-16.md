# Trained-baseline formal PU v1 audit

Status: excluded from all quantitative claims; preserved read-only for forensic
traceability.

## Finding

`breeze/results/trained_baselines_2026-07-14/formal_pu_v1/` was resumed by
more than one process before the current single-instance guard existed.  Its
append-only checkpoint files remain useful for diagnosing the procedural
failure, but its summary tables cannot be treated as a formal experiment.

At audit time, the downstream CSV contained 6 rows but only 3 unique
`(method, train_mode, n_real, seed)` cells.  The cost CSV contained 22 rows
but only 11 unique `(method, train_mode, n_real, seed, class_id)` cells.
Duplicated rows are retained; none was deleted, merged, or used to select a
result.

## Resolution

`run_trained_baselines.py` now takes a non-blocking OS advisory lock on the
chosen output root for the lifetime of a run.  A second process targeting the
same root exits before it can write a duplicate row.  The formal protocol,
model code, hyperparameters, split, seed family, and API use are unchanged.

The corrected formal run must use a new directory
`breeze/results/trained_baselines_2026-07-16/formal_pu_v2/`.  It starts from
an empty result ledger and is the only directory eligible for E1 reporting.
