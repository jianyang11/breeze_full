# BREEZE Evidence Ledger

Status: frozen for manuscript use through 2026-07-17 (Asia/Shanghai).

This ledger is the sole claim boundary for the closing-stage manuscript. A
manuscript statement is permitted only when it is no broader than the evidence
and protocol recorded below. Frozen source directories are read-only; this
ledger records their results and does not replace them.

## Final statistical and similarity audit (2026-07-16)

- The statistical seeds combine a paired few-shot subset draw and CNN
  initialization. Each method reuses one fixed synthetic pool within a frozen
  dataset protocol. The supported inference is that the archived pool is
  stably useful across repeated few-shot training; it is not an
  independent-generation-pool inference.
- A zero-training global Benjamini--Hochberg sensitivity family combines the
  12 core PU, 72 provenance-valid CWRU, and 18 Berkeley hypotheses. Its
  pass/fail decisions agree with the registered within-family Holm decisions
  for all 102 hypotheses: PU 12/12, CWRU 72/72, and Berkeley 15/18. Source:
  breeze/results/global_bh_sensitivity_2026-07-16/.
- The synthetic-to-real audit finds zero byte-identical float32 windows among
  all available audited pools, but several pools have high maximum
  cross-correlation. Because no copying threshold was declared, this is a
  descriptive similarity audit and cannot support an independence or
  “without copying” claim. Berkeley must be described separately because its
  renderer intentionally uses a real train-only exemplar background. Source:
  breeze/results/ablation_2026-07-16/memorization_frozen_v1/.
- Complete PU/CWRU kurtosis-W1 and fault-frequency-alignment cells must remain
  visible. LLM is not best on every physical metric; its supported PU fidelity
  advantage is concentrated in RMS, PSD, and band-energy summaries, while rule
  or noise augmentation is better in multiple kurtosis/alignment cells.

## Closed-loop admission-record audit (2026-07-17)

- SHA-256 was computed for all 450 local PU `rescreen_v2_full` round records.
  Strict aggregation assigns a slot to the minimum candidate round with
  `feasible=true` and verifies that candidate is exactly the record's selected
  candidate. The aggregate contains 150 slots per class and matches every row
  of the prior frozen slot summary.
- Pooled cumulative admissions are 205 at K=0, 241 at K=1, 268 at K=2, and 286
  at K=3. The corresponding marginal admissions are 205, 36, 27, and 18;
  K=3 class totals are 90 healthy, 90 OR, and 106 IR slots.
- These values are complete descriptive accounting for one frozen
  pool-generation run. They do not estimate variability over independent LLM
  recipe pools. Source:
  `breeze/results/admission_round_freeze_2026-07-17/`.

## Audit basis

- Repository rewrite baseline: `main` = `origin/main` = `5aa92cd`
  (`docs: rewrite evidence-aligned manuscript`) after `git fetch origin main`.
  The audited CAS rewrite is content commit
  `1f258f6b4c82fdca374713409f97d78385e9095d`; no frozen experiment was rerun
  to create that commit.
- Preserved user worktree items: `breeze/OK.md` and the untracked `complete/`,
  `smoke/`, and `verified_complete/` subdirectories beneath
  `breeze/results/pu_loco_v4_s3_scale_invariant_2026-07-13/`. None was read,
  edited, rerun, or used as formal evidence here.
- API reconciliation: the central `phaseB_api_usage_log.csv` ends at
  1131 requests, while the later
  `mt_private_v3_s_c_api_log.csv` contains 100 requests. The current
  auditable total is therefore **1231/3000**, before any new close-stage work.
  The close-stage incremental cap remains **300**.

## Manuscript-safe positive results

| Evidence line | Permitted wording | Protocol boundary and source |
|---|---|---|
| PU primary condition, Phase-A v2 | On the PU `N09_M07_F10` file split, cached LLM K=3 recipes significantly outperformed rule recipes and random open-loop recipes for Accuracy and Macro-F1 at `n_real={5,10,25}` under the registered, within-family Holm-corrected one-sided Wilcoxon tests. At `n_real=50`, the registered auxiliary tests support that LLM is not worse than rule and is better than real-only. | 20 seeds; `n_syn=450`; no new API calls in the v2 rerun. Use only the stated file-split, few-shot scope. Source: `breeze/results/phaseA_v2_frozen_2026-07-06/breeze/results/phaseA_v2_gate_report.md`. |
| CWRU within-load and leave-one-load-out | On CWRU within-load0 and the provenance-valid held-out-load1/2/3 folds, LLM exceeded rule, noise augmentation, and real-only in all 72 registered comparisons, with positive deltas and Holm `q<0.05`. The archived held-out-load0 fold is excluded from transfer claims because all folds reused a `within_load0` LLM/rule pool, giving that fold target-load provenance. | 40 fixed seeds, `n_real={5,10,25}`, `n_syn=20/class`. The evidence supports source-load0 to held-out-load1/2/3 transfer, not arbitrary cross-dataset transfer or a strict four-fold LOLO result. Sources: `breeze/results/cwru_patch_v2_2026-07-07_frozen/cwru_patch_v2_report.md`, its 90-row `cwru_patch_v2_wilcoxon.csv`, and `analysis/cwru_lolo_provenance_audit_2026-07-15.md`. |
| Berkeley milling, binary protocol | The frozen binary task is learnable. LLM is significantly better than `noise_aug` and `random_open_loop` for both Accuracy and Macro-F1 at every tested shot (`n_real={2,5,10}`). Against rule, the significant results are n=2 Accuracy and both n=5 metrics; n=2 Macro-F1 and both n=10 metrics do not pass Holm correction. | One preregistered 40-seed formal test; `n_syn=20/class`; task is healthy `VB<0.2` versus degraded `VB>=0.2`. This is a qualified, partial result, not a passed milling dataset. Sources: `breeze/results/milling_berkeley_v2_binary_formal_2026-07-08/berkeley_v2_binary_final_report.md` and `berkeley_v2_binary_formal_gate_report.md`. |

## Boundary evidence and negative results

| Evidence line | Frozen conclusion | Manuscript-safe use |
|---|---|---|
| PU LOCO v1 | The held-out condition protocol is not uniformly significant: 57/96 registered comparisons fail Holm with a positive delta. | Report as the initial negative result; do not aggregate selective successful cells into a transfer claim. Source: `breeze/results/pu_loco_2026-07-07_v1_frozen/pu_loco_report.md`. |
| PU LOCO v2 | Correcting kinematic fields does not resolve the failure: 60/96 registered comparisons fail Holm. The report attributes the remaining mismatch to non-frequency morphology across load/torque conditions. | Supports the narrow conclusion that frequency correction alone is insufficient. Source: `breeze/results/pu_loco_v2_2026-07-08/pu_loco_v2_failure_analysis.md`. |
| PU LOCO v3--v5 | Train-only morphology diagnostics, candidate-pool admission, and extrapolation-gate attempts did not yield an admissible balanced cross-condition pool. No associated formal held-out test was run. | Describe these as development/admission failures, not downstream failures. Sources: `pu_loco_v3_2026-07-08/morphology_condition_map.md`, `pu_loco_v4_s2_morphology_2026-07-13/s2_s1_acceptance_failure.md`, and `pu_loco_v5_s4_extrapolation_verifier_2026-07-13/pu_loco_v5_failure_analysis.md`. |
| PU LOCO v6 | The predeclared source-only CSCoh evidence gate fails for OR and IR in all four internal pseudo-held-out targets: OR has the wrong signed ordering; the apparent IR evidence also accepts wrong-class and white-noise controls. Integration, pool construction, and formal testing were correctly stopped. | This is the final falsification of a transferable class-identity certificate under this representation and protocol. Source: `breeze/results/pu_loco_v6_cscoh_2026-07-14/pu_loco_v6_failure_analysis.md`. |
| UMich v4 | The all-label raw real-only variants are near chance, but the defensible stop reason is **condition/metadata confounding**, not simple non-learnability: metadata-only and stage-only diagnostics can equal signal-only performance. No LLM generation, preregistration, or formal test was run. | State that UMich does not provide a defensible signal-only worn/unworn result under the frozen split. Do not write merely “real-only is approximately 0.5” without the confound qualification. Sources: `breeze/results/milling_umich_v4_task_repair_2026-07-09/umich_v4_task_repair_report.md` and `learnability_audit/umich_v4_learnability_audit.md`. |
| MU-TCM v3 | The inner-validation gate passes 2/6 core comparisons; no preregistration or formal held-out test is permitted. | Report only as a stopped inner-validation line, never as a positive milling result. Source: `breeze/results/mutcm_v3_llm_inner_2026-07-09/mutcm_v3_inner_gate_report.md`. |

## Prohibited or unsupported manuscript claims

- “Zero real data”, “empty-handed”, or an equivalent claim. Every positive
  protocol uses real training-fold calibration and few-shot exemplars.
- A successful PU leave-one-condition-out, cross-speed, cross-load, or
  cross-dataset generalization claim.
- A blanket milling claim, “milling SOTA”, or a statement that Berkeley is a
  passed milling dataset.
- “Structured physical recipes (LLM and rule) are significantly better than
  all unstructured baselines” for Berkeley. The frozen formal table only tests
  LLM-versus-baseline comparisons; it does not establish the required
  rule-versus-unstructured significance tests.
- “LLM beats rule at n=2/5” for Berkeley without naming the metric. The n=2
  Macro-F1 comparison fails Holm correction.
- A simple UMich unlearnability claim that omits the confound audit, any
  UMich success claim, or any MU-TCM formal-test claim.
- Direct accuracy comparisons with work using window-level random splits.
  Such work may be discussed only as a protocol difference and leakage risk.

## Wording guards for the manuscript

- Name the exact split unit, shot count, synthetic budget, seed count, and
  correction family wherever a result is first introduced.
- For Berkeley, lead with “qualified binary milling result” and report all
  three failed LLM-versus-rule cells alongside the 15/18 total.
- For PU LOCO, present the whole v1--v6 chain as a predeclared stress-test
  boundary. Never use the internal v3--v6 diagnostics to imply a formal test.
- Do not call the verifier a proof of physical truth. It is a deterministic,
  protocol-bounded admission mechanism whose validity is shown only for the
  evidence lines above.

## Closing-stage control rules

- Phase-A v2, CWRU patch-v2, PU LOCO v1--v6, Berkeley v2 binary formal,
  MU-TCM v3, and UMich v2--v4 are immutable evidence. Do not rerun or
  overwrite them.
- New baseline, ablation, and metric work must reuse the matching frozen split
  manifest, be checkpoint/resume capable, and write CSV/JSON plus a Markdown
  report.
- Results not listed above, including the later private-machine-tool v3
  artifacts, are excluded from the present manuscript claim set until a
  separate evidence review explicitly adds them to this ledger.

## Required review before final manuscript freeze

1. Generate every numerical table directly from its frozen CSV rather than
   copying values into LaTeX.
2. Recheck each sentence containing “significant”, “transfer”, “training-free”,
   “milling”, or “physical” against this ledger.
3. Reconcile the API total again before any regeneration call and record any
   increment in the central ledger as well as the run-local log.
