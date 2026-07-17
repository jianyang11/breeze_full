# BREEZE Figure Revision Todos

Status: formal integration complete for Figs. 3--5 and 7; Figure 6 round freeze and integration in progress
Baseline: `origin/main@621dfe7`
Backend: Python/matplotlib only
Formal integration gate: author approved PR #2; Figure 6 requires final QA before merge

## A. Freeze scope and runtime

- [x] Verify local `main` and `origin/main` both resolve to `621dfe7`.
- [x] Confirm tracked manuscript and figure sources are clean at task start.
- [x] Preserve all unrelated untracked experiment and build artifacts.
- [x] Read `nature-figure/SKILL.md`, its manifest, core contract, stance,
  Python backend fragment, chart patterns, Nature observations, and QA contract.
- [x] Read the local Nuwa skill and adopt its topic-skill synthesis discipline:
  primary-source collection, cross-source pattern extraction, explicit
  anti-patterns, and honest boundaries.
- [x] Read the complete `main_cas.tex`, `src/figures.py`, and
  `src/figure_style.py` at the synchronized baseline.
- [x] Verify `.venv-breeze` Python, matplotlib, NumPy, SciPy, pandas, Pillow,
  scikit-learn, and required vector/raster export support.
- [x] Freeze hashes for the manuscript, current result figures, plotting code,
  and every candidate formal data source.
- [x] Create `paper/figs/revision_preview/` without touching formal figure files.

## B. Literature and visual grammar benchmark

- [x] Select 5--8 real, recent papers spanning fault-data generation,
  physics-informed generation, diffusion/GAN augmentation, and BearGen.
- [x] Verify each paper through a publisher page, DOI record, or authoritative
  preprint; reject records without stable primary provenance.
- [x] Inspect each paper's main result figures rather than relying on abstracts.
- [x] Record dataset/task, comparison structure, uncertainty display, statistical
  annotation, physical-evidence organization, and failure/boundary treatment.
- [x] Distill cross-paper expert rules using the Nuwa synthesis pattern:
  recurring mental models, decision heuristics, anti-patterns, and scope limits.
- [x] Write the verified benchmark to `analysis/figure_style_benchmark.md` with
  source links and concrete BREEZE adaptations.

## C. Source-data and claim audit

- [x] Inventory every current Fig. 3--10 source path used by `src/figures.py`.
- [x] Separate formal/frozen sources from smoke, partial, development, ignored,
  or unavailable sources.
- [x] Exclude TimeGAN, DDPM, CFG-DDPM, strong physics generators, and additional
  classifier backbones from all preview figures.
- [x] Exclude private machine-tool data and retain only PU, CWRU, and Berkeley.
- [x] Map every plotted number to frozen CSV/NPZ rows and the generating script.
- [x] Verify train/test provenance for all waveform selection and statistics.
- [x] Verify paired seed definitions and synthetic-pool reuse for downstream
  confidence intervals.
- [x] Audit Holm status sources for every dataset/shot/metric/comparator cell.
- [x] Audit whether cumulative K=0/1/2/3 slot admission can be reconstructed
  exactly from frozen slot/candidate records; stop Fig. 6a if it cannot.
- [x] Audit physical-metric availability per dataset/method/class, especially
  kurtosis-W1 and fault-frequency alignment.
- [x] Write `analysis/figure_source_map.md` before plotting.

## D. Figure contracts

- [x] Write a one-sentence conclusion, evidence hierarchy, archetype, panel map,
  statistics contract, source-data requirement, and reviewer risk for Fig. 3.
- [x] Write the same contract for Fig. 4, including medoid provenance and
  population envelope-spectrum summary.
- [x] Write the same contract for Fig. 5, separating fidelity errors from
  directionless NN diversity.
- [x] Write the same contract for Fig. 6, including the capacity-failure encoding.
- [x] Write the same contract for Fig. 7, separating continuous CWRU effects from
  discrete PU pass states.
- [x] Freeze the common 183 mm style, palette, typography, line widths, panel
  labels, legend rules, and export formats before implementation.

## E. Data snapshot builder

- [x] Implement a preview-only data builder with deterministic outputs and no
  experiment/API execution.
- [x] Build Fig. 3 paired-effect snapshot with mean paired effect, paired
  bootstrap 95% CI, Holm status, and seed count for all 36 cells.
- [x] Fix the bootstrap algorithm and RNG seed; document resampling over paired
  downstream seeds, not independent generated pools.
- [x] Build Fig. 4 medoid-selection snapshot from outer-training-side physical
  features only; record selected indices, source/unit identifiers, distances,
  and feature definitions.
- [x] Build Fig. 4 population envelope-spectrum median/IQR snapshot for OR and IR
  across Real, LLM, Rule, and Random.
- [x] Build Supplementary Fig. S2 healthy medoid waveform and population
  envelope-spectrum snapshot under the identical selection/demodulation rules.
- [x] Build Supplementary Fig. S1 RMS/kurtosis distribution snapshot with real
  and synthetic sample counts.
- [x] Build Fig. 5 class-conditional physical error-ratio snapshot as
  `log2(method distance / rule distance)` without averaging away unavailable
  or unfavourable cells.
- [x] Build Fig. 5 NN-diversity snapshot separately in raw units.
- [x] Build Fig. 6 cumulative-round and marginal admission snapshots from the
  independently hashed 450-record freeze.
- [x] Build Fig. 7 CWRU continuous effect/Holm snapshot and PU v1/v2 discrete
  pass-count snapshot.
- [x] Build Supplementary Fig. S3 v1--v6 failure-chain snapshot from frozen
  reports without converting development stops into held-out results.
- [x] Emit one independent source-data CSV per complete figure and supplementary figure.
- [x] Emit one `source-manifest.json` per figure containing source paths,
  SHA-256, filters, sample counts, generation time, and code version.

## F. Tests before plotting

- [x] Test all expected datasets, classes, shots, metrics, and comparators.
- [x] Test exact paired seed counts: PU 20; CWRU and Berkeley 40.
- [x] Test no duplicate or missing paired seed keys.
- [x] Test Fig. 3 Holm states against frozen registered result files.
- [x] Test first-row shared x limits and explicitly declared second-row limits.
- [x] Test medoid selection is deterministic and never reads held-out/test rows.
- [x] Test envelope spectra use one fixed 500--2000 Hz demodulation configuration.
- [x] Test no per-method waveform amplitude normalization is represented as
  absolute-amplitude evidence.
- [x] Test Fig. 5 ratio signs and NA propagation; reject zero/negative distances.
- [x] Test NN diversity never enters the fidelity-error colormap.
- [x] Test Fig. 6 has 450 unique slots, 150/class, monotone K=0--3 curves,
  exact 286 final admissions, and exact prior-summary agreement.
- [x] Test Fig. 7 excludes the provenance-invalid CWRU held-out-load0 fold.
- [x] Test no private, smoke, partial, trained-baseline, or new-backbone source is
  present in any manifest.
- [x] Test deterministic outputs under a fixed seed and stable row ordering.

## G. Preview implementation

- [x] Add a preview-only Python module; do not redirect existing formal outputs.
- [x] Implement Fig. 3 as a 2x3 paired-effect forest plot.
- [x] Implement Fig. 4 as OR/IR medoid waveforms plus population envelope
  median/IQR panels with shared axes and numeric BPFO/BPFI labels.
- [x] Implement Fig. 5 as three dataset-specific relative-error matrices plus a
  separate neutral NN-diversity point panel.
- [x] Implement Supplementary Fig. S1 as ECDF distributions with grayscale-safe line styles.
- [x] Implement Supplementary Fig. S2 as the healthy counterpart to Fig. 4.
- [x] Implement Fig. 6 as cumulative class/pooled admission and class-stacked
  marginal admissions, without inventing uncertainty over independent pools.
- [x] Implement Fig. 7 as a 2x2 mixed continuous/discrete heatmap grid.
- [x] Implement Supplementary Fig. S3 as the complete PU v1--v6 failure chain.
- [x] Export editable PDF/SVG, 600 dpi TIFF, and preview PNG for every complete figure.
- [x] Keep all outputs under `paper/figs/revision_preview/`.

## H. Statistical and source verification

- [x] Independently recompute every Fig. 3 plotted effect from seed-level rows.
- [x] Independently verify every bootstrap interval contains no unpaired draws.
- [x] Verify all Holm marker fills match frozen registered decisions.
- [x] Verify all Fig. 4 medoid indices reproduce exactly across two runs.
- [x] Verify physical log-ratios reproduce from raw frozen class-level metrics.
- [x] Verify all CWRU/PU heatmap annotations reproduce from frozen summaries.
- [x] Compare source CSV row counts and hashes against each manifest.

## I. Visual QA at final size

- [x] Render each preview at exactly 183 mm final width.
- [x] Inspect 5.5--7 pt body text and 8--9 pt bold lowercase panel labels.
- [x] Inspect axes, zero lines, CI visibility, legends, whitespace, and clipping.
- [x] Verify the rule-comparison row uses one shared x range across datasets.
- [x] Verify non-structured comparison ranges are explicitly labelled.
- [x] Run color-vision-deficiency checks for protanopia, deuteranopia, and
  tritanopia using a documented simulation.
- [x] Run grayscale contrast checks and confirm marker/line encodings survive.
- [x] Verify SVG text remains editable and PDF fonts are embedded as text.
- [x] Verify TIFF files are 600 dpi and all exported dimensions are recorded.
- [x] Create old/new per-figure comparison sheets and an aggregate contact sheet.
- [x] Build a temporary CAS QA copy outside formal paper outputs and inspect
  previews at manuscript reading size without modifying `main_cas.tex`.

## J. Reports and first-stage delivery

- [x] Write `analysis/figure_revision_report.md` with per-figure scientific
  question, design rationale, exact sources, statistics, limitations, and QA.
- [x] Record any blocked requirement explicitly; never infer unavailable K-round
  records or physical metrics.
- [x] Confirm formal `paper/figs/*`, `main_cas.tex`, and `main_cas.pdf` are
  byte-unchanged from the synchronized baseline.
- [x] Review all prompt requirements line by line and record pass/block status.
- [x] After author review, commit only preview code/data/figures, tests, manifests, benchmarks,
  reports, and this checklist.
- [x] After author review, push the preview-stage commit and verify remote HEAD if requested.
- [x] Stop before formal integration and request author review of previews.
