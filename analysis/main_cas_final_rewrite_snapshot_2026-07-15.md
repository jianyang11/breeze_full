# BREEZE CAS Final Rewrite Snapshot

Date: 2026-07-15 (Asia/Shanghai)

## Canonical artifact

- Title: `BREEZE: Physics-Verified LLM Recipe Generation for Few-Shot Condition Monitoring`
- Source: `breeze/paper/main_cas.tex`
- Compatibility entry: `breeze/paper/main.tex`
- Compiled PDF: `breeze/paper/main_cas.pdf`
- CAS template: local `els-cas-templates`, class `cas-sc`, bibliography style
  `cas-model2-names`
- Length: 17 pages
- Abstract: 237 words under the conservative source-level counter
- Figures: 10 mounted figures
- References: 46 cited entries; no missing or uncited key and no duplicate key,
  DOI, or normalized title

## Artifact hashes

- `main_cas.tex`: `cd10ba9e98a3c1a8c0b3a64073ab98161a370c4aa66de593fd6a7e5d2c583f09`
- `main_cas.pdf`: `3c8a9f2ca1c35b14c00498be8dfb369223bdb0d884458c4e127bac4d7306abcc`
- `references.bib`: `a8cbec9c0328f0898dfaf3a8dba49363952311fbb3407dfc0865b33a6b33bd7d`
- `generated/numbers.tex`: `f3842d75114b11ad7391f9ee0cec988b24da9299551335d0986987248e126bb8`

These hashes describe the pre-commit final QA artifacts. The synchronized
content commit is recorded in the closeout update after the commit exists.

## Evidence statements frozen into the manuscript

- PU Phase-A v2: all 12 registered LLM-versus-rule/random comparisons pass the
  registered Holm procedure at 5, 10, and 25 real windows per class.
- CWRU: the valid family is 72/72 comparisons across within-load0 and
  load0-source pools evaluated on held-out loads 1--3. The archived
  `lolo_load0` output is excluded because it reuses a load0-derived synthetic
  pool and therefore has target-load provenance.
- Berkeley: qualified partial result, 15/18. All 12 comparisons against noise
  and random open-loop pass; the LLM-versus-rule advantage is restricted to
  the named lower-shot cells.
- PU LOCO: the complete v1--v6 negative chain is retained. Only v1 and v2 are
  formal held-out tests; v3--v6 are development, admission, sanity, or
  source-only evidence stops.
- UMich and MU-TCM contribute no positive result. UMich is stopped for
  condition/process-metadata confounding; MU-TCM stops after 2/6 train-only
  inner-validation comparisons.

## Number and figure governance

- `breeze/scripts/build_paper_tables.py` reads only frozen CSV/JSON sources and
  generates the four result tables plus `generated/numbers.tex`.
- The script asserts full grids, pair counts, comparison directions, Holm pass
  patterns, the CWRU provenance-valid family, PU LOCO failure counts, slot
  accounting, and the MU-TCM stop count.
- The ten figures are generated only with the specified Python 3.12.13
  environment. PDF/SVG remain editable and all PDF fonts are embedded. TIFF
  exports are 600 dpi. SVG line-ending cleanup removes serialization whitespace
  only and does not alter geometry or style.
- The full 17-page PDF was rendered with Poppler at 120 dpi and inspected as a
  contact sheet plus full-size spot checks. No blank page, clipping, overlapping
  content, missing figure, or incoherent float was observed.

## Build and QA commands

```bash
breeze/.venv-breeze/bin/python breeze/scripts/build_paper_tables.py
MPLCONFIGDIR=/private/tmp/breeze-mpl-framework \
  breeze/.venv-breeze/bin/python breeze/src/fig_framework.py
MPLCONFIGDIR=/private/tmp/breeze-mpl-figures \
  breeze/.venv-breeze/bin/python breeze/src/figures.py
cd breeze/paper
env LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 \
  TEXINPUTS=../els-cas-templates//: \
  latexmk -pdf -interaction=nonstopmode -halt-on-error main_cas.tex
```

## Non-blocking build warnings

- The CAS title/abstract implementation emits one empty-box overfull warning at
  `maketitle`; full-size page-1 inspection confirms no visible overflow.
- Narrow fixed-width cells in the two overview tables emit underfull warnings;
  visual inspection confirms readable, contained text.
- BibTeX reports empty page fields for nine conference-style entries whose
  cited records do not require fabricated page ranges. No page value was
  invented merely to silence the warnings.

## Submission blockers

1. `Author One`, `Author Two`, affiliation, corresponding-author, funding,
   ORCID, and approval metadata require author-supplied values.
2. The original PU LLM provider version, top-p, and provider-side seed were not
   captured. Frozen pools replay from archived recipes and renderer seeds, but
   the original language responses are not claimed to replay identically.
3. Formal matched TimeGAN/DDPM and additional diagnostic-backbone studies are
   not frozen. Smoke/development outputs remain excluded; no SOTA or universal
   trained-generator superiority claim is made.
4. HAWAN-PIR remains uncited because no verified DOI or stable publisher record
   was available in the audited workspace.

## Explicitly excluded artifacts

- Private-machine-tool experiments and all untracked result directories.
- The CWRU `lolo_load0` fold as unseen-load evidence.
- TimeGAN/DDPM smoke or incomplete formal folders.
- UMich/MU-TCM as positive generation evidence.
- The user-preserved `breeze/OK.md` and original manuscript copies.
- No new LLM API call was made during this rewrite.
