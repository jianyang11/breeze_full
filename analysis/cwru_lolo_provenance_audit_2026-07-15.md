# CWRU LOLO Synthetic-Pool Provenance Audit

Date: 2026-07-15 (Asia/Shanghai)

## Finding

The frozen CWRU scheduler uses the same LLM and rule pools for the within-load0
split and all four leave-one-load-out (LOLO) folds:

- `breeze/scripts/run_cwru_patch_v2_downstream.py` maps `llm` to
  `breeze/runs/phaseB_cwru_within_load0_llm_full_v1_combined/pool.npz`;
- the same scheduler maps `rule` to
  `breeze/runs/phaseB_cwru_within_load0_rule_pilot_v1/pool.npz`;
- those method definitions are reused unchanged for `lolo_load0` through
  `lolo_load3`.

Both pool summaries explicitly record `"split": "within_load0"`. Therefore,
the archived `lolo_load0` result is not a strict unseen-load evaluation: its
synthetic pool was derived from the target load0 provenance even though its
real classifier training split contains loads 1--3.

## Evidence-safe interpretation

- `within_load0` remains a valid within-load file-disjoint result.
- `lolo_load1`, `lolo_load2`, and `lolo_load3` remain provenance-valid transfer
  tests because the reused source load0 belongs to each fold's real training
  side and the held-out load is 1, 2, or 3.
- `lolo_load0` is retained in the frozen raw results for auditability but is
  excluded from manuscript transfer claims and summary figures.

The resulting claim set contains four valid splits, three shot counts, two
metrics, and three LLM comparisons per cell: 72 registered comparisons. All
72 have 40 paired seeds, a positive mean delta, and `passed_holm=True` in the
frozen `cwru_patch_v2_wilcoxon.csv`.

## Corrective actions

1. `scripts/build_paper_tables.py` continues to assert the complete 90-row raw
   grid, then computes manuscript claims only from the 72 provenance-valid
   rows.
2. The CWRU cross-load figure excludes held-out load0 and labels the remaining
   folds as source-load0 to held-out-load1/2/3 transfer.
3. The evidence ledger, claim map, abstract, methods, results, discussion, and
   conclusion state the 72/72 boundary explicitly.
4. No frozen downstream result is modified or rerun.
