# BREEZE final Q2 closeout checklist

Audit date: 2026-07-16. Canonical manuscript:
breeze/paper/main_cas.tex. Final PDF: breeze/paper/main_cas.pdf.

| Item | Status | Verified evidence |
|---|---|---|
| H1 directional gate formula | verified | Equation 3 uses disjoint interval, upper, and lower predicate sets plus an explicit empty-diversity-set convention. Code-path audit is in analysis/gate_predicate_semantics_audit_2026-07-16.md; dedicated tests pass. |
| H2 synthetic-to-real copying claim | qualified | The unsupported claim is deleted. A zero-API 2200-window audit reports exact identity, NRMSE, and maximum cross-correlation. No available window is byte-identical, but high correlations remain and no independence claim is made. Berkeley is explicitly exemplar-background simulation. |
| H3 complete physical metrics | verified | Generated Tables 7 and 8 include class-averaged and every per-class PU/CWRU kurtosis-W1/fault-frequency cell, including rule/noise-favouring entries and explicit NA. |
| H4 reference population consistency | verified | Figure 5 now uses all PU outer-training reference windows, 1200/1202/1444 by class, matching the W1 calculations. Caption and in-figure annotation state the reference population. |
| H5 multiplicity and inference unit | verified | Global BH is recomputed from 102 frozen core p-values and agrees with registered Holm decisions in all 102 cells. The paper defines seeds as paired subset/CNN repeats around one fixed pool and excludes independent-pool inference. |
| C1 final positioning | verified | Title, Abstract, Introduction, Discussion, Conclusion, cover letter, and highlights consistently describe training-free, auditable LLM-mediated recipe augmentation with train-calibrated physical admission on three frozen public protocols. |
| C2 Berkeley wording | verified | The complete 12/12 unstructured comparison pattern is retained; generated macros supply the 0.267, 0.468, 0.407 percentage-point passing rule effects and 10-shot convergence values. |
| C3 trained-generator baseline boundary | verified | Smoke/development values are absent. Formal TimeGAN/DDPM absence appears once in the manuscript limitations/reproducibility subsection, apart from neutral related-work mentions. |
| C4 LLM knowledge source and circularity | verified | Prompt-supplied kinematics, train statistics, exemplar descriptions, and feedback are disclosed. Claims use LLM-mediated selection. Shared renderer/verifier definitions and the exact role of rule, random-plus-verifier, and random open-loop controls are stated. |
| M1 stale mechanical text | verified | Short title is synchronized; submission checklist states 21 pages; supplementary outline no longer describes the old private-data/v2 submission. |
| M2 author metadata | BLOCKER | Author One/Two, short authors, Department/City/Country, ORCIDs, corresponding author/email, funding, contribution, and approval metadata require author input. No identity metadata was guessed. |
| M3 optional adjacent citations | not required | Existing related work is adequate for the bounded Q2 claim. No unverified or decorative citation was added. |
| M4 reproducibility package | qualified | Prompt/schema, renderer, verifier, PU pools, formal statistics, and physics hashes are addressable. The ignored CWRU/Berkeley pools and detailed records require a checksum-indexed release; Data availability states this limitation. See analysis/reproducibility_inventory_2026-07-16.md. |
| M5 final PDF audit | verified | Table builder and 19 targeted tests pass. Latexmk produces a 21-page PDF with 46 resolved references and no unresolved citation/reference warning. All fonts are embedded. Poppler rendering and page-by-page contact-sheet inspection show no blank page, clipping, overlap, missing glyph, or blank figure. |

## Build diagnostics

- No LaTeX citation, reference, label, or package warning remains after the
  final rerun.
- The CAS class emits one front-matter overfull-box diagnostic at maketitle and
  narrow-cell underfull diagnostics in the dataset table. Page 1 and page 7
  were visually inspected; no text crosses a page boundary or is clipped.
- The complete physical table is explicitly resized to text width; its earlier
  overfull diagnostic is resolved.

## Scope audit

- Zero new training experiment and zero API call were used.
- Frozen formal result directories were read only.
- No state-of-the-art, trained-generator superiority, zero-real-data, formal
  physical-correctness, cross-specimen, cross-machine, or independent-pool
  claim remains.
- The only upload blocker is author-supplied metadata in M2.
