# BREEZE Result-Figure Benchmark

Date: 2026-07-16

Scope: recent signal-generation and physics-guided fault-diagnosis papers used
to define the visual evidence grammar for the Fig. 3+ preview revision. This is
a Nuwa-style thematic synthesis, not an imitation of any author. Bibliographic
identity, datasets, and reported evidence were checked against a publisher
page, DOI record, or an authoritative full preprint. A visual detail is stated
only when the full figure, caption, or publisher figure description was
available.

## Verified papers and figure grammar

| Paper | Method and data | Baselines and metrics | Main-result figure grammar actually verified | BREEZE adaptation |
|---|---|---|---|---|
| Lee et al., **BearGen**, *Advanced Engineering Informatics* 71 (2026) 104400, [DOI](https://doi.org/10.1016/j.aei.2026.104400) | LLM descriptions condition a learned diffusion generator. CWRU, PU, HIT, IMS, XJTU, DIRG, JUST, and NCEPU; balanced, imbalanced, and few-shot protocols. | Time-GAN, SigCWGAN, TTS-GAN, TTS-CGAN, DDPM, CFG-DDPM; FID, KID, Accuracy, F1, imbalance, few-shot, guidance, and cost. | Full PDF inspected. Fig. 8 is a class-column grid with time waveform, FFT, and envelope spectrum; reference peaks are vertical dashed lines. Figs. 13--14 use dataset panels and shot-grouped downstream bars. Tables 4--5 carry mean and standard deviation. t-SNE is auxiliary. | Keep physical observables and downstream utility separate. Replace single chosen examples with a reproducible medoid plus population median/IQR. Replace dense bars with paired-effect forest plots. |
| Yi et al., **TSDM**, *Mechanical Systems and Signal Processing* 216 (2024) 111481, [DOI](https://doi.org/10.1016/j.ymssp.2024.111481), [full preprint](https://arxiv.org/pdf/2312.07981) | DDPM adapted to one-dimensional vibration. Synthetic single/multiple-frequency data and CWRU, XJTU, HIT bearing datasets. | VQ-VAE, TimeGAN, DiffWave and ablated/original diffusion variants; frequency error/VF and small-sample CNN, RNN-LSTM, and TST accuracy. | Full preprint inspected. Representative traces and spectra are separate figures; group spectral peaks are summarized by boxplots; downstream training repetitions are shown as boxplots and tables. | Use individual traces only as interpretable representatives. Make the population envelope distribution and paired downstream effects the evidential panels. |
| Kim et al., **SGAN-DDS**, *Advanced Engineering Informatics* 62 (2024) 102821, [DOI](https://doi.org/10.1016/j.aei.2024.102821) | Spectrum-guided GAN plus density-directionality latent sampling. Signallink rotor testbed and CWRU. | GAN and latent-sampling comparisons; time/frequency fidelity, diversity, and downstream diagnosis under imbalance. | Publisher full-article text and figure descriptions inspected. The paper first diagrams fidelity and diversity failure modes, then reports time/frequency comparisons and separates quantitative fidelity from diversity. | Keep reference-relative physical error and NN diversity in different encodings; the latter has no universal best direction. |
| Liu et al., **DFE-GAN**, *Mechanical Systems and Signal Processing* 163 (2022) 108139, [DOI](https://doi.org/10.1016/j.ymssp.2021.108139) | Pull-away regularized/self-attention GAN with an automatic filter. CWRU zero-load ten-state data and an electric-locomotive bearing dataset. | GAN-family and imbalance methods; generated-data statistics/visualization and CNN diagnosis. | Publisher full-article text inspected. The evidence chain is generator/filter mechanism, generated-signal quality, then downstream diagnosis on laboratory and engineering data. The accessible publisher page does not expose every figure caption, so no unverified geometry is borrowed. | Make verifier behavior visible, but do not present filtering itself as novel. Link each admission panel to an auditable frozen record. |
| Guo et al., **DiffUCD**, *Measurement* 242 (2025) 115951, [DOI](https://doi.org/10.1016/j.measurement.2024.115951) | Condition-guided diffusion and an unsupervised clustering filter. Public SDUST and PU, including unseen-condition generation. | Generative comparators; MMD, GAN-train/test, downstream unknown-condition diagnosis, and hyperparameter analysis. | Publisher full-article page inspected. Architecture/framework figures lead into condition-transfer tables and filter analysis. | A cross-condition figure must distinguish genuine held-out downstream effects from verifier-only or stopped protocols. Label CWRU as load0 pool to held-out load, and show PU failures discretely. |
| Tian et al., **ReF-DDPM**, *Reliability Engineering & System Safety* 251 (2024) 110343, [DOI](https://doi.org/10.1016/j.ress.2024.110343) | Reparameterized residual DDPM for imbalanced rolling-bearing diagnosis. The accessible case description verifies CWRU at 1797 rpm and 0 hp; the publisher page does not expose every protocol detail. | DDPM/GAN augmentation comparisons and downstream imbalanced diagnosis. | Publisher full-article page inspected. A numbered generation workflow precedes case-specific diagnosis results. Exact result-panel geometry was not asserted where captions were unavailable. | Preserve a mechanism-to-outcome narrative, but do not add this unfinished trained-generator baseline to current BREEZE plots. |
| Xu et al., **MR-DDIM**, *Sensors* 26 (2026) 3091, [DOI](https://doi.org/10.3390/s26103091) | Wavelet/FiLM conditional DDIM with spectral losses on the BJTU-RAO high-speed-train gearbox dataset under few-shot protocols. | Ablated diffusion designs and diagnostic comparisons; MR-SCC, class-intrinsic MMD, Accuracy, spectral consistency, sampling settings, and robustness. | Open full article inspected. Fig. 5 compares real/generated population log-amplitude spectra with fluctuation bands rather than isolated spectra; later figures cover distribution, ablation, hyperparameters, and diagnosis. | Use population median/IQR spectra in Fig. 4 and reserve single windows for medoid morphology. Make unavailable metrics explicit rather than silently changing the physical observable. |
| Gao et al., physics-constrained multimodal GAN, *Measurement Science and Technology* 36 (2025) 116109, [DOI](https://doi.org/10.1088/1361-6501/ae1a04) | Dual-path time/frequency GAN with differentiable decaying-impact and speed-modulation constraints on two public bearing datasets. | Reported evidence includes DTW, envelope-spectrum deviation/MSE, statistical similarity, coverage, downstream F1, and physical-loss ablation. | DOI/publisher metadata and indexed figure descriptions were verified. The local file named `.pdf` is HTML, so exact figure geometry is not treated as inspected evidence. | Include fault-frequency alignment beside statistics and PSD error, but call it an empirical diagnostic check rather than physical truth. |

`HAWAN-PIR 2025` remains excluded: no stable DOI, publisher page, or supplied PDF
was found in the available records. It is not used to justify any visual choice.

## Distilled expert rules

1. **One panel answers one question.** Mechanism, fidelity, diversity,
   downstream utility, and cross-condition scope are distinct evidence types.
2. **Population evidence outranks an attractive example.** A representative
   waveform requires a fixed selection rule; a spectrum claim requires a
   population interval or distribution.
3. **Effects should be plotted on the comparison scale.** Paired differences
   and their uncertainty answer whether augmentation helped more directly than
   side-by-side absolute bars.
4. **Physics is multidimensional.** Time statistics, PSD shape, band energy,
   and fault-frequency alignment can disagree; unfavorable cells must remain.
5. **Fidelity and diversity are not one scalar objective.** A low
   real-reference distance has a direction; within-pool NN diversity does not
   have a universal optimum.
6. **Cross-condition labels must describe the actual protocol.** Source-pool
   condition, held-out condition, and stopped development stages cannot be
   merged into a generic generalization claim.

## Anti-patterns rejected for this revision

- Dense grouped bars when paired seeds are available.
- Independently normalized example amplitudes used to imply amplitude fidelity.
- First-file or visually chosen examples.
- Rainbow or sequential heatmaps for signed effects.
- A shared color scale for continuous effects and discrete pass counts.
- t-SNE/UMAP as core physical evidence.
- Empty cells reserved for unfinished trained-generator or classifier results.

