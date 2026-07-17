# BREEZE Fig. 3+ Source Map

Date: 2026-07-16

Baseline: `origin/main@621dfe7`

Policy: every preview number must be reconstructed from the source below.
Smoke, partial, mid-training, private-data, trained-generator, and additional
classifier-backbone outputs are forbidden. Each preview directory will contain
the filtered source CSV and a manifest with SHA-256 hashes, row counts, filters,
and code version.

## Figure 3: paired downstream effects

| Dataset/comparison | Seed rows | Registered Holm decision | Generating/summarizing code |
|---|---|---|---|
| PU, LLM--rule and LLM--random open-loop | `breeze/results/phaseA_v2_frozen_2026-07-06/breeze/results/phaseA_v2_downstream_cnn.csv` | `.../phaseA_v2_wilcoxon.csv` | `breeze/scripts/phase_a_v2_summarize.py`; experiment rows are already in the dated freeze |
| CWRU within load0, LLM--rule and LLM--noise | `breeze/results/cwru_patch_v2_2026-07-07_frozen/downstream/within_load0_{llm,rule,noise_aug}_nsyn20.csv` | `.../cwru_patch_v2_wilcoxon.csv`, filter `split=within_load0` | `breeze/scripts/summarize_cwru_patch_v2.py` for registered tests |
| Berkeley binary held-out case split, LLM--rule and LLM--noise | `breeze/results/milling_berkeley_v2_binary_formal_2026-07-08/downstream_40seed_nsyn20/berkeley_v2_binary_{llm,rule,noise_aug}_nsyn20.csv` | `.../berkeley_v2_binary_formal_wilcoxon_holm.csv` | frozen result artifact; no matching formal summarizer was found in the repository, so the manifest records the artifact directly |

Pair key: `(dataset protocol, n_real, seed)`. PU has 20 seeds and shots
5/10/25; CWRU has 40 seeds and shots 5/10/25; Berkeley has 40 seeds and
shots 2/5/10. Accuracy and Macro-F1 are paired before any summary. The plotted
CI will be a fixed-seed percentile bootstrap over paired deltas; it does not
represent independent synthetic-pool generation.

## Figure 4 and Supplementary Figure S2: PU morphology and envelope spectra

| Quantity | Frozen/source data | Code lineage |
|---|---|---|
| Real outer-training windows | `load_file_split("train", "N09_M07_F10")` from `breeze/proc/*.npz`; expected class counts 1200/1202/1444 | `breeze/src/data.py`, `breeze/src/config.py` |
| LLM/rule/random synthetic windows | `breeze/results/phaseA_v2_frozen_2026-07-06/breeze/runs/phaseA_v2_balanced/phaseA_v2_{llm_k3,rule,random_open_loop}_B150.npz` | frozen by `breeze/scripts/freeze_phase_a_v2.py` |
| Medoid feature space | log-RMS plus PSD-CDF coordinates for all three channels | `standard_feature_matrix` in `breeze/scripts/compute_physics_metrics.py`; robust class-matched real-train median/MAD scaling, with degenerate coordinates excluded |
| Envelope spectra | all windows of each source/class, channel 0, fixed 500--2000 Hz FIR demodulation, squared envelope, Hann FFT | `envelope_spectrum` in `breeze/src/verifier/features.py`, with the band fixed by this figure contract |
| BPFO/BPFI | 6203 geometry and 900 rpm condition | `fault_freqs` in `breeze/src/config.py` |

The selected medoid is an actual window nearest the within-source/class median
in the shared real-train-scaled feature space. Ties resolve to the lowest source
index. No test/held-out window is read.

## Figure 5 and Supplementary Figure S1: physical errors and distributions

Primary class-level values:

- `breeze/results/ablation_2026-07-14/physics_frozen_full_v3_pu/physics_metrics.csv`
- `breeze/results/ablation_2026-07-14/physics_frozen_full_v3_cwru/physics_metrics.csv`
- `breeze/results/ablation_2026-07-14/physics_frozen_full_v3_berkeley/physics_metrics.csv`

Availability and exact pool membership come from each adjacent
`physics_pool_availability.csv` and `physics_pool_manifest.csv`. The generating
algorithm is `breeze/scripts/compute_physics_metrics.py`.

Main-matrix metrics are `rms_w1`, `kurtosis_w1`, `psd_w1_mean`,
`band_energy_relative_error_mean`, and
`envelope_frequency_alignment_error_hz`. Berkeley lacks the latter two
bearing-specific quantities (`kurtosis_w1` was not generated and bearing fault
frequency alignment is not defined), so these cells are NA. Its
`tpf_amplitude_ratio_w1` is retained in raw tables but is not relabeled as
bearing frequency alignment. Every matrix cell is
`log2(method distance / class-matched rule distance)`; zero or negative source
distances are rejected rather than regularized.

`nn_diversity` and `real_nn_diversity` remain raw, separate point evidence.
Supplementary Fig. S1 reconstructs PU RMS and kurtosis samples from the same
outer-training windows and frozen balanced pools; it does not read held-out PU
windows.

## Figure 6: admission mechanism

The local `breeze/runs/rescreen_v2_full/records/*.json` archive was promoted to
an independently audited, write-once evidence freeze at
`breeze/results/admission_round_freeze_2026-07-17/`. The committed artifacts
are:

- `round_records_manifest.csv`: path, class, slot, file size, and SHA-256 for
  all 450 JSON files;
- `slot_first_pass_round.csv`: candidate-round trace and the first candidate
  with `feasible=true` for every slot;
- `cumulative_admission_by_class.csv`: K=0--3 marginal and cumulative counts
  for healthy, OR, IR, and all slots;
- `validation_report.json`: exact assertions for 450 unique slots, 150/class,
  286 admitted, selected-candidate equality, and row-level agreement with the
  2026-07-06 frozen `slot_summary.csv`.

The generating and validation code is
`breeze/scripts/freeze_admission_round_records.py`. Figure 6 reads only the
committed aggregate freeze. It never infers a round from `n_candidates`.

## Figure 7: cross-condition effects and boundary

| Panel | Source | Filter/definition | Code lineage |
|---|---|---|---|
| CWRU Accuracy/Macro-F1 | `breeze/results/cwru_patch_v2_2026-07-07_frozen/cwru_patch_v2_summary.csv` and `cwru_patch_v2_wilcoxon.csv` | source pool load0; held-out `lolo_load1`--`lolo_load3`; LLM--rule; 5/10/25 shots; signed percentage-point mean delta and Holm state | `breeze/scripts/summarize_cwru_patch_v2.py` |
| PU v1 | `breeze/results/pu_loco_2026-07-07_v1_frozen/pu_loco_wilcoxon.csv` | each condition/shot/metric: count positive, Holm-passing registered comparisons out of four | `breeze/scripts/summarize_pu_loco.py` |
| PU v2 | `breeze/results/pu_loco_v2_2026-07-08/pu_loco_wilcoxon.csv` | identical 0/4--4/4 count | `breeze/scripts/summarize_pu_loco.py` |

Supplementary Fig. S3 uses the same v1/v2 files and the explicit stop reports:
`morphology_condition_map.md`, `s2_s1_acceptance_failure.md`,
`pu_loco_v5_failure_analysis.md`, and
`pu_loco_v6_cscoh_2026-07-14/source_separability_summary.csv`. Stages v3--v6
remain development/admission stops and are never converted to held-out scores.
