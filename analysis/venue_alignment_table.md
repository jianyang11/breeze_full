# BREEZE Venue Alignment and Narrative Distillation

Date: 2026-07-15 (Asia/Shanghai)

Target: Advanced Engineering Informatics / comparable CAS engineering venue.
The table distinguishes full-PDF visual inspection from publisher-page or DOI
metadata review. Search snippets alone are not treated as evidence.

| Paper | Method | Data/protocol | Baselines and metrics | Figure/table grammar | Verification level | Transferable lesson for BREEZE |
|---|---|---|---|---|---|---|
| Lee et al., “BearGen: LLM-guided signal generation framework for bearing fault diagnosis,” AEI 71 (2026) 104400, DOI 10.1016/j.aei.2026.104400 | A pretrained LLM creates signal descriptions; knowledge is distilled to a local LLM; a description-guided diffusion model is trained to synthesize signals | Eight public bearing datasets are described; seven enter the main quality/diagnosis tables. The paper reports CWRU, PU, HIT, IMS, XJTU, DIRG, JUST and NCEPU across balanced, imbalanced and few-shot settings | TimeGAN, SigCWGAN, TTS-GAN, TTS-CGAN, DDPM, CFG-DDPM; FID, KID, Accuracy, F1, few-shot and imbalance studies, guidance ablation, training/inference cost | Three-phase workflow hero; local-LLM responsibility diagram; dataset plates; time/FFT/envelope grid; FID bars; t-SNE auxiliary; few-shot grouped bars; cost table | Full user-provided PDF visually inspected, including Figs. 1, 5, 6, 8, 12--14 and Tables 3--12 | Use a phase-led workflow and an explicit component boundary. Pair qualitative waveforms with FFT/envelope evidence and quantitative metrics. Do not borrow BearGen's trained-diffusion superiority claim for a training-free admission method. |
| Kim et al., “Spectrum-guided GAN with density-directionality sampling,” AEI 62 (2024) 102821, DOI 10.1016/j.aei.2024.102821 | Spectrum-guided GAN plus density filtering and direction-aware latent sampling | Signallink rotor testbed and CWRU bearing testbed under limited/imbalanced fault data | GAN/sampling comparisons; diagnostic performance plus separate fidelity and diversity analyses | Problem mechanism figures for instability/mode collapse; method schematic; time/frequency qualitative comparison; fidelity-diversity quantitative panels | Publisher full article page and methods/dataset/figure descriptions verified; PDF layout not locally archived | Treat fidelity and diversity as separate axes. A selection mechanism needs both a rejection rationale and downstream evidence, which supports BREEZE's gate-report and non-copy analyses. |
| Liu et al., “Data synthesis using deep feature enhanced GANs for rolling bearing imbalanced fault diagnosis,” MSSP 163 (2022) 108139, DOI 10.1016/j.ymssp.2021.108139 | Pull-away regularized GAN, self-attention feature enhancement, and an automatic generated-data filter | CWRU zero-load ten-condition setup and an electric-locomotive bearing dataset | GAN/imbalance comparators; generated-data quality and diagnostic performance | GAN workflow, learned-feature/filter diagram, generated-signal comparison and downstream tables | Publisher article page and dataset/method details verified; PDF figure geometry not locally inspected | Generated-data filtering is established prior art. BREEZE's novelty must rest on deterministic train-calibrated physics admission, auditable feedback and no target-generator training, not filtering in the abstract. |
| Guo et al., “Bearing fault diagnostic framework under unknown working conditions based on condition-guided diffusion model,” Measurement 242 (2025) 115951, DOI 10.1016/j.measurement.2024.115951 | Condition-guided diffusion with a condition-embedding U-Net and K-means UCFilter | Public SDUST and PU bearing datasets; unknown-condition generation/diagnosis | State-of-the-art generative comparisons; MMD and GAN-train/test; downstream diagnosis | Diffusion backbone figure, complete framework figure, condition-transfer tables and filter analysis | Publisher full article page verified | Cross-condition claims require generated target-condition pools and downstream tests. BREEZE's failed PU LOCO chain must therefore be shown as a boundary, not softened into a verifier-portability claim. |
| Gao et al., “Bearing fault signal generation method by fusion of physical constraints and multimodal features,” MST 36(11) (2025) 116109, DOI 10.1088/1361-6501/ae1a04 | Time-frequency multimodal GAN with impact-response and speed-modulation priors | Publisher metadata states two public bearing datasets | DTW, envelope-spectrum deviation/MSE, statistical similarity, coverage and downstream F1 are reported in indexed metadata | Expected mechanism-led architecture and multidomain fidelity panels; exact visual layout not asserted | DOI and publisher metadata verified; the local file labelled PDF is HTML, so figure layout remains unverified | Mechanism evidence should include fault-frequency error, envelope prominence/harmonics and distribution statistics. These are empirical checks, not formal physical validity. |
| Liu et al., “Physics-informed diffusion-based augmentation for vibration-based fault diagnosis of rotating machinery,” JVC (online 2026), DOI 10.1177/10775463261455715 | Wavelet-preprocessed temporal-attention diffusion with multiscale priors and asymmetric U-Net | Two bearing test platforms according to the publisher abstract | Representative generative baselines; physical fidelity and downstream diagnosis | Physics-prior architecture, time-frequency examples, quantitative fidelity and classifier results | Publisher abstract and metadata verified; full figures unavailable | Physics-informed diffusion is a strong trained-generator comparator. BREEZE may position itself as a lower-training-cost operating point, but cannot claim performance or cost superiority before the matched formal baseline is frozen. |
| Randall and Antoni, “Rolling element bearing diagnostics--A tutorial,” MSSP 25(2) (2011) 485--520, DOI 10.1016/j.ymssp.2010.07.017 | Signal-processing tutorial: resonance-band selection, spectral kurtosis, demodulation/envelope analysis, cyclostationary interpretation | Multiple bearing case histories spanning low to high speed | Diagnostic examples rather than generative baselines | Physical mechanism sketches, raw/envelope signals, spectra and case-based evidence | Publisher full article page verified | Use envelope evidence as a diagnostic observable with applicability limits. Bearing impulses are stochastic/pseudo-cyclostationary, so overly deterministic periodic templates and single-peak validation are review risks. |

Bibliographic re-audit on 2026-07-15 corrected the VAE DOI to
`10.1088/1361-6501/ab55f8` and added the publisher DOI
`10.1016/j.aei.2025.103666` for FillingGAN. These corrections affect only
reference metadata, not experimental evidence or claims.

## Nuwa-style thematic distillation

This is a theme synthesis, not an imitation of any author.

### Field consensus

1. A synthetic-signal paper must separate generation mechanism, signal
   fidelity, diversity/non-copy evidence, and downstream utility.
2. Time-domain similarity alone is weak; frequency and envelope evidence are
   standard for bearing signals.
3. Cross-condition claims require condition-disjoint generation and diagnosis,
   not recalibration or real-only verifier pass rates.
4. Quality filtering is prior art. The differentiator must be the evidence
   encoded by the filter, its calibration protocol, and whether it produces an
   auditable feedback loop.

### Methodological disagreement

- Learned-generator papers place physics in the training loss or architecture;
  BREEZE places diagnostic evidence at admission time.
- BearGen uses language as a conditioning modality for a trained diffusion
  model; BREEZE uses language to propose structured recipe parameters executed
  by a deterministic renderer.
- DiffUCD treats target-condition generation as a positive capability; the
  frozen BREEZE PU LOCO sequence falsifies that capability for its current
  representation and must remain visible.

### Narrative template for the manuscript

1. Open with the repeated training cost of dataset-specific generators.
2. Introduce recipe-as-data and make the LLM/renderer/verifier boundary
   explicit before discussing results.
3. Establish LLM contribution with matched rule and random recipes.
4. Establish load-transfer evidence on CWRU and qualified milling evidence on
   Berkeley.
5. Close the evidence chain with physical diagnostics, auditability, cost
   scope, and the complete PU LOCO/UMich/MU-TCM boundary.

### Anti-patterns

- Do not use a t-SNE/UMAP picture as proof of physical fidelity.
- Do not equate passing a hand-designed gate with physical truth.
- Do not compare accuracy directly against papers using window-random splits.
- Do not hide failed condition cells or stopped protocols behind an aggregate.
- Do not describe inference-only BREEZE as superior to trained GAN/diffusion
  systems until the matched formal study is complete.
