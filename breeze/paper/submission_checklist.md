# AEI / Elsevier submission checklist

## Completed evidence and manuscript checks

- The manuscript source is [main.tex](main.tex), and its current PDF is
  [main.pdf](main.pdf).
- Main result tables are generated from frozen CSV files by
  `breeze/scripts/build_paper_tables.py`; the generated fragments are under
  `breeze/paper/generated/`.
- The manuscript uses the frozen evidence ledger and preserves its claim
  boundaries: PU Phase-A v2 positive result; CWRU 90/90 registered comparisons;
  Berkeley partial/no-go (15/18); PU LOCO, UMich, and MU-TCM negative results.
- The CWRU physical-diagnostic replay agrees exactly with the frozen full LLM
  quality rows. The new physical tables record source hashes and availability;
  no CWRU random-open-loop substitute is used.
- The current manuscript compiles with `pdflatex` without undefined references
  or citations. The generated tables use only editable LaTeX.
- Highlights and this cover-letter draft use the same qualified claims as the
  evidence ledger.

## Pending before submission

- Complete the formal 40-seed TimeGAN/DDPM baseline runs, generate their cost
  and instability report, and insert only the final non-smoke values.
- Complete the predeclared PU K and gate ablations, or label them unavailable
  rather than using the legacy v1/offline-rescreen products as substitutes.
- Replace author, affiliation, funding, ORCID, and conflict-of-interest
  placeholders with author-supplied metadata.
- Check the final manuscript against the current AEI author guide and prepare
  any journal-specific files, including a graphical abstract if the authors
  elect to submit one.
- Rebuild `main_cas.tex` from the new evidence-aligned manuscript before
  final upload; it is not yet synchronized with this rewrite.
- Run institutional similarity checking outside this workspace.

## Non-negotiable claim boundary

- Do not claim zero-real-data fault diagnosis, cross-condition PU success,
  UMich or MU-TCM positive augmentation, Berkeley state of the art, or a
  trained-baseline cost advantage before the corresponding frozen evidence is
  available.
