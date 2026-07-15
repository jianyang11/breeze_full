# BREEZE final figure contracts

Frozen on 2026-07-15. Backend: Python 3.12.13 in
`breeze/.venv-breeze`. Style contract: `nature-figure`; narrative ordering:
field-theme distillation through `huashu-nuwa`. Every data figure must fail
when a listed source is absent or structurally incomplete.

| ID / file | One-sentence conclusion | Panels and archetype | Frozen source | Main review risk | Final size |
|---|---|---|---|---|---|
| Fig. 1 `framework` | BREEZE converts structured LLM proposals into an auditable admission loop without optimizing a target-data generator. | Phase-led workflow: real-train calibration, LLM recipe, deterministic renderer, mixed verifier, feedback, admitted pool, downstream classifier. | Method code and manuscript equations; no empirical values. | Confusing calibration with generator training. | 178 mm x 100 mm |
| Fig. 2 `responsibility_boundary` | Proposal, signal construction, admission and downstream utility are separate responsibilities. | Four-column responsibility matrix with inputs, outputs and non-claims. | `src/llm.py`, `src/renderer.py`, verifier modules, downstream protocol. | Attributing renderer or verifier behavior to intrinsic LLM physics. | 178 mm x 78 mm |
| Fig. 3 `waveforms` | The four PU sources have visibly different waveform/envelope structure under a deterministic, non-cherry-picked sample rule. | Three class blocks; columns are real, LLM, rule and random; paired time trace and envelope spectrum. | PU real training split plus the three frozen `phaseA_v2_balanced/*.npz` pools; first ordered class item only. | Treating selected traces as distributional proof. Caption must state the deterministic selection rule. | 178 mm x 175 mm |
| Fig. 4 `boxplots` | LLM admission changes class-wise time statistics but does not collapse the pool to the real marginal distribution. | RMS and kurtosis boxplots by PU class/source; all frozen synthetic windows and deterministic capped real reference. | Same frozen PU pools; PU outer-training windows. | Hiding outliers or unequal sample counts. Use full boxes, state n, no claim of optimal direction. | 178 mm x 92 mm |
| Fig. 5 `metric_distances` | Physical diagnostics are complementary and dataset-specific rather than a scalar generator ranking. | Faceted heatmaps/point plots for normalized RMS W1, PSD W1, band-energy error and NN diversity on PU/CWRU/Berkeley, with missing cells explicit. | `physics_frozen_full_v3_{pu,cwru,berkeley}/physics_metrics.csv` and availability files. | Comparing incomparable scales or replacing missing pools. Normalize only within each dataset/metric and preserve NA. | 178 mm x 112 mm |
| Fig. 6 `downstream_bars` | LLM recipes improve paired few-shot outcomes on PU/CWRU and yield a qualified Berkeley advantage. | Seed-level paired-delta distributions against rule and strongest registered non-structured comparator; zero reference and 95% bootstrap CI for description only. | Frozen PU per-seed CSV, CWRU downstream files, Berkeley formal per-seed source named by its report. | Bars hiding variance; unregistered cross-dataset pooling. Show points/violin or box/strip and keep each protocol separate. | 178 mm x 105 mm |
| Fig. 7 `acceptance_k` | Offline v2 rescreening of the archived K=3 candidate tree distinguishes proposal slots, admitted slots and rendered windows. | Cumulative slot admission by available attempt depth; class-wise slot-to-window mapping; source-level verifier acceptance. | Frozen rescreen/rule/random `slot_summary.csv` and `summary.json`, plus budget summary. | Calling the offline rescreen a newly executed v2 LLM loop or equating slots with windows. | 178 mm x 82 mm |
| Fig. 8 `cross_condition_heatmap` | CWRU load transfer is positive under its registered protocol, while PU LOCO is not uniformly supported. | CWRU LOLO LLM-minus-rule matrices for Accuracy/Macro-F1; PU v1/v2 registered pass/fail matrices or complete pass counts. | Frozen CWRU summary/tests; PU LOCO v1/v2 frozen summary/tests. | Selective condition display or extrapolating CWRU load transfer to PU. | 178 mm x 118 mm |
| Fig. 9 `failure_reasons` | Admission failures are class- and source-dependent, and random recipes can fail every slot under the same verifier. | Stacked/non-exclusive gate-failure shares plus admitted-slot/rendered-window counts. | `phaseA_v2_failure_gate_summary.csv`, gate report and frozen summary JSON files. | Summing non-exclusive reasons as if mutually exclusive. Use rates and state overlap. | 178 mm x 80 mm |
| Fig. 10 `failure_case` | Six PU LOCO development stages terminate for different evidence failures before any broad transfer claim is justified. | Evidence-chain timeline v1--v6: formal failure counts, frequency mismatch, morphology/admission stops and CSCoh non-separability. | Reports enumerated in `analysis/evidence_ledger.md`; v1/v2 registered tests; v3--v6 frozen stop reports. | Presenting internal-development stops as formal held-out tests. Encode test stage explicitly. | 178 mm x 82 mm |

## Shared graphical rules

- Use Arial/Helvetica-compatible sans serif, 7--8 pt final text, 0.6--1.0 pt
  lines, and bold lowercase panel labels.
- Keep semantic colors stable: real/neutral black, LLM blue, rule orange,
  random grey, noise teal, rejection red. Do not use rainbow colormaps.
- Export editable PDF/SVG plus LZW-compressed 600 dpi TIFF. Raster outputs
  must use the physical final width rather than relying only on a DPI tag.
- Captions must define sample count, split unit, seed count, uncertainty or
  test family, deterministic sample-selection rule, and whether a panel is
  descriptive, registered formal evidence, or an internal stop.
- No t-SNE/UMAP is used as core evidence.
