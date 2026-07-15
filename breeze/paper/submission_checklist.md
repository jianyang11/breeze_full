# AEI / Elsevier submission checklist

## Completed evidence and manuscript checks

- Canonical source: `breeze/paper/main_cas.tex`; compatibility entry point:
  `breeze/paper/main.tex`; compiled artifact: `breeze/paper/main_cas.pdf`.
- The manuscript uses Elsevier CAS `cas-sc` and `cas-model2-names` from the
  local `els-cas-templates` distribution.
- PU, CWRU, Berkeley, and physical tables are generated from frozen CSV files
  by `breeze/scripts/build_paper_tables.py`, with exact row-grid, pairing,
  direction, and pass-pattern assertions.
- CWRU claims include only the 72 provenance-valid within/load-transfer tests.
  The archived held-out-load0 fold is excluded because it reuses a load0 pool;
  see `analysis/cwru_lolo_provenance_audit_2026-07-15.md`.
- Berkeley is reported as a partial 15/18 result with the complete failed-cell
  pattern. PU LOCO v1--v6, UMich confounding, and the MU-TCM stop remain visible.
- Ten manuscript figures are generated from frozen evidence and exported as
  vector PDF plus 600-dpi TIFF; no missing pool is imputed.
- The CAS manuscript compiles to 17 pages with 46 resolved references and no
  undefined citation or cross-reference.
- A 17-page Poppler render was checked as a contact sheet; no blank page,
  clipping, incoherent overlap, or blank figure was observed.
- Cover letter and five Elsevier-length highlights use the same bounded claims.

## Blocking metadata before upload

- Replace anonymous author, affiliation, funding, ORCID, and approval
  placeholders with author-supplied metadata.
- Confirm journal-required declarations and the final corresponding author.
- Run institutional similarity checking outside this workspace.

## Evidence limitations that must remain explicit

- Formal matched TimeGAN/DDPM and additional diagnostic-backbone experiments
  are not complete; smoke/development outputs are excluded. The manuscript
  therefore makes no SOTA or universal trained-generator superiority claim.
- Original PU LLM provider-version/top-p/provider-seed metadata are incomplete.
  Archived recipes and renderer seeds reproduce frozen pools, but the original
  language responses are not claimed to replay identically.
- Do not claim zero-real-data diagnosis, strict four-fold CWRU LOLO, successful
  PU condition transfer, generic milling superiority, or a formal physical
  guarantee.
