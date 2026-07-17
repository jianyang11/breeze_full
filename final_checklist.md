# BREEZE final closure checklist

Last verified: 2026-07-17 Asia/Shanghai

## Hard-error and claim audit

- [x] H1: the manuscript defines separate interval, upper, and lower predicates;
  `breeze/tests/test_paper_gate_semantics.py` checks the paper predicate against
  the implemented gate semantics.
- [x] H2: synthetic-to-real NRMSE, maximum cross-correlation, and byte identity
  are reported separately from within-pool diversity; Berkeley exemplar
  background is disclosed.
- [x] H3: kurtosis-W1 and fault-frequency-alignment cells are retained,
  including comparator-favouring cells; the prose states that LLM is not best
  on every physical metric.
- [x] H4: the plotted PU reference population matches the full class-matched
  outer-training population used by the W1 audit.
- [x] H5: global BH sensitivity accompanies family-wise Holm; seeds and the
  fixed-pool inference unit are explicit; random open-loop is not called a
  matched control.
- [x] Claims remain bounded to training-free, auditable LLM-mediated recipe
  selection under the three frozen public few-shot protocols. No SOTA,
  trained-generator superiority, zero-real-data, formal physical correctness,
  cross-specimen, or cross-machine claim is made.
- [x] Berkeley is reported as 12/12 against non-structured comparators and as a
  small, metric-specific lower-shot advantage over rule, with ten-shot
  convergence.
- [x] TimeGAN/DDPM formal comparison remains one concentrated limitation; smoke
  values are absent from claims.

## Admission-mechanism evidence and figure

- [x] All 450 local round JSON files have a committed SHA-256 manifest.
- [x] First-pass aggregation is strict: selected candidate equals the minimum
  archived round with `feasible=true` for every slot.
- [x] The aggregate has 450 unique slots, 150 per class, and exactly 286 final
  admissions, matching the old frozen `slot_summary.csv` row by row.
- [x] K=0--3 cumulative admissions are 205, 241, 268, and 286; no archive-depth
  proxy, imputation, or inferred round is used.
- [x] The admission figure exports editable PDF/SVG, 300-dpi PNG, and 600-dpi
  TIFF at 183 mm width; source and output hashes pass manifest QA.
- [x] Color, grayscale, CAS reading-size, clipping, and label-overlap checks
  pass. The revision-contract Fig. 6 is formal Figure 7 in the compiled paper
  because the manuscript retains the separate physical-distance figure.
- [x] The formal `acceptance_k.pdf`, Results prose, caption, generated numerical
  macros, evidence ledger, and submission checklist are synchronized.

## Build and release

- [x] `build_paper_tables.py` regenerates all LaTeX numbers from frozen CSV/JSON
  inputs and asserts the new round-level counts.
- [x] Figure exports are byte-deterministic across two consecutive runs.
- [x] `breeze/tests/test_figure_revision_preview.py`: 9/9 passed.
- [x] CAS compilation completed with 21 pages, 46 resolved references, and no
  unresolved citation or cross-reference.
- [x] All 21 PDF pages were rendered and visually checked; no blank page,
  clipped figure, overlap, or unreadable caption was found.
- [ ] Author order, affiliations, ORCIDs, corresponding-author email, funding,
  contributions, and approval metadata remain the sole author-supplied blocker.
- [x] Push the audited Fig. 6 commit to PR #2 and verify the remote PR head.
- [ ] Merge PR #2 and verify `origin/main` at the merge commit.
