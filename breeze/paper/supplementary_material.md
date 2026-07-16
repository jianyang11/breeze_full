# Supplementary Material Outline

This outline follows the final public-dataset manuscript. It excludes private
machine-tool development artifacts and uses the frozen protocol names reported
in analysis/evidence_ledger.md.

## S1. Frozen public-data protocols

- PU Phase-A v2: condition N09_M07_F10, retained channels vibration_1,
  phase_current_1, and phase_current_2, acquisition-file split before
  windowing, and n_real={5,10,25}.
- CWRU patch-v2: within-load0 plus source-load0 to held-out-load1/2/3.
  The archived held-out-load0 fold is excluded because the fixed synthetic
  pool has target-load provenance.
- Berkeley binary formal: case/run grouping before windowing, healthy VB<0.2
  versus degraded VB>=0.2, and n_real={2,5,10}.

For every protocol, list split-manifest hashes, training/test acquisition
units, window counts, channel definitions, and fixed synthetic budgets.

## S2. Recipe, renderer, and verifier records

- Prompt builder and JSON schema: breeze/src/llm.py.
- Seeded renderer: breeze/src/renderer.py.
- Verifier implementation: breeze/src/verifier/v2.py and
  breeze/src/verifier/features.py.
- PU frozen pool/seed manifests:
  breeze/results/phaseA_v2_frozen_2026-07-06/breeze/runs/phaseA_v2_balanced/.
- Full gate predicate semantics audit:
  analysis/gate_predicate_semantics_audit_2026-07-16.md.

Include representative archived recipes and complete per-candidate gate
records in the versioned supplementary archive. The original PU provider
version, top-p, and provider-side seed are unavailable; replay therefore starts
from archived recipes rather than regenerating the original LLM response.

## S3. Complete downstream and statistical tables

- PU seed rows, summaries, and Wilcoxon/Holm tables from the Phase-A v2 frozen
  directory.
- CWRU seed rows and the provenance-valid 72-row subset from
  breeze/results/cwru_patch_v2_2026-07-07_frozen/.
- Berkeley 40-seed rows and all 18 rule/noise/random comparisons from
  breeze/results/milling_berkeley_v2_binary_formal_2026-07-08/.
- Global BH sensitivity CSV and report from
  breeze/results/global_bh_sensitivity_2026-07-16/.

State that seeds combine few-shot subset selection and CNN initialization while
reusing one fixed synthetic pool per method; they are not independent
generation-pool replicates.

## S4. Complete physical and similarity diagnostics

- Physics-v3 PU, CWRU, and Berkeley CSVs under
  breeze/results/ablation_2026-07-14/.
- Every PU/CWRU kurtosis-W1 and bearing fault-frequency-alignment cell,
  including cells in which rule or noise augmentation is better.
- Synthetic-to-real NRMSE, maximum cross-correlation, and byte-identity audit
  from breeze/results/ablation_2026-07-16/memorization_frozen_v1/.
- Gate and diversity-threshold ablations from
  breeze/results/ablation_2026-07-15/gate_ablation_v1/.

Berkeley uses TPF amplitude-ratio diagnostics and a train-only exemplar
background; it does not use the bearing fault-frequency metric.

## S5. Reproducibility inventory and release boundary

The tracked repository contains table/figure scripts, frozen statistical CSVs,
PU pool arrays and manifests, physics manifests with SHA-256 hashes, and
generation code. Primary CWRU/Berkeley arrays and detailed candidate records
currently reside under ignored breeze/runs/ paths. They must be deposited as a
versioned repository-release or data-repository archive for exact waveform
replay; until then the Git repository supports numerical-result audit but not
complete CWRU/Berkeley waveform replay.

## S6. Boundaries and stopped protocols

- Six PU LOCO stages define a failed cross-condition morphology-transfer line.
- UMich is stopped because experiment-level condition/process metadata remain
  confounded with wear under the frozen split.
- MU-TCM stops at a 2/6 train-only inner gate and has no formal test.
- Formal TimeGAN/DDPM comparisons, independent-pool inference, additional
  backbones, and cross-specimen/cross-machine protocols are future work.
