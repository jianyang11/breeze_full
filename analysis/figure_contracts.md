# BREEZE Fig. 3+ Contracts

Date: 2026-07-16

Backend: Python/matplotlib only. Full width is 183 mm. Body text is 5.5--7 pt;
panel labels are bold lowercase 8.5 pt. PDF and SVG retain editable text; TIFF
is 600 dpi; PNG is for review. BREEZE/LLM is deep blue `#0F4D92`, rule is orange
`#D67A2C`, and random/noise sources use neutral gray or teal. No visual
parameter may change a numerical result.

## Figure 3: downstream diagnostic effect

- **Scientific question:** Does the admitted LLM-recipe pool improve diagnosis
  relative to the strongest completed structured baseline and to a completed
  non-structured baseline on each public protocol?
- **Conclusion to support:** LLM--rule effects are small and protocol/shot
  dependent, whereas effects against random/noise are generally larger; no
  trained-generator or SOTA claim is made.
- **Archetype:** 2x3 paired-effect forest plot.
- **Panels:** top row LLM--rule for PU/CWRU/Berkeley with one shared symmetric
  x range; bottom row LLM--random for PU and LLM--noise for CWRU/Berkeley, with
  explicitly printed per-panel ranges.
- **Statistics:** paired mean delta in percentage points; 20,000 percentile
  bootstrap resamples over paired seeds with RNG seed 20260716; fixed pool;
  filled marker = registered Holm pass, hollow marker = NS. No star-only code.
- **Source data:** 36 rows: 3 datasets x 3 shots x 2 metrics x 2 comparisons.
- **Reviewer risk:** bootstrap seeds are repeated few-shot subset/CNN
  initialization runs around one fixed synthetic pool, not independent pool
  generations. The caption and source data must say this.

## Figure 4: representative morphology and population envelope spectra

- **Scientific question:** Do the OR/IR pools reproduce inspectable waveform
  morphology and population envelope energy near the registered fault
  frequency without relying on a hand-picked sample?
- **Conclusion to support:** the fixed medoid rule yields auditable examples,
  while all-window median/IQR spectra expose source-level agreement and
  disagreement around BPFO/BPFI.
- **Archetype:** two class bands; Real/LLM/Rule/Random columns; waveform row
  above population envelope-spectrum row.
- **Selection:** actual source window nearest its source/class robust center in
  a shared, class-matched, real-train-scaled physical feature space. Fixed tie
  rule; source index and distance are saved.
- **Signal contract:** raw vibration amplitude, same y limits across sources
  within a class; no per-source amplitude normalization. Envelope spectra use
  fixed 500--2000 Hz demodulation and absolute FFT scaling; median and IQR over
  all windows; same axes within each class. BPFO/BPFI are labelled in Hz.
- **Source data:** selected waveform samples, medoid audit rows, and population
  envelope quantiles. Healthy is emitted only as Supplementary Fig. S2.
- **Reviewer risk:** a medoid is representative, not proof of fidelity. The
  population spectrum and Fig. 5 carry the quantitative evidence.

## Figure 5: physical error relative to rule

- **Scientific question:** On which class-specific physical observables is each
  completed pool closer to the real reference than rule, and where is it worse?
- **Conclusion to support:** the physical evidence is mixed rather than a
  universal ranking; negative log-ratios favor the method and positive values
  favor rule.
- **Archetype:** PU/CWRU/Berkeley diverging matrices plus a separate neutral NN
  diversity point panel.
- **Statistics:** exact frozen class-level metrics; no inferential test is
  invented for these one-pool summaries. Matrix value is
  `log2(method distance / rule distance)`. NA is shown only when the frozen
  metric is undefined/unavailable.
- **Direction:** fidelity matrix centered at zero. NN diversity stays in raw
  units and is labelled as having no universal optimal direction.
- **Source data:** ratio rows, raw numerator/denominator, sample counts, and raw
  NN diversity/real-reference values.
- **Reviewer risk:** metrics have different units and sensitivity. Ratios are
  for within-metric comparison only; raw physical values remain available.

## Figure 6: admission mechanism

- **Scientific question:** How many proposal slots become feasible at each
  bounded feedback round, and does the pattern differ by PU class?
- **Conclusion to support:** 205/450 slots pass at $K=0$; rounds 1--3 add
  36, 27, and 18 slots, reaching 286/450. Feedback adds feasible slots, but
  164 remain unadmitted at $K=3$.
- **Archetype:** cumulative class/pooled line plot plus a class-stacked marginal
  admission bar plot.
- **Statistics:** complete descriptive accounting of one frozen 450-slot run;
  no confidence interval or independent-pool inference is implied.
- **Source data:** a 2026-07-17 write-once freeze containing SHA-256 for all 450
  round JSON records, one first-pass row per slot, a K=0--3 cumulative table,
  and an exact validation against the prior frozen slot summary.
- **Current status:** complete. The aggregate contains 150 slots per class and
  exactly reproduces 286 final LLM admissions.
- **Reviewer risk:** `n_candidates` remains archive depth and is never used as a
  round proxy. First pass is reconstructed only as the minimum archived round
  with `feasible=true`, and must equal the record's selected candidate.

## Figure 7: cross-condition evidence and boundary

- **Scientific question:** Does a load0 CWRU pool transfer to held-out loads,
  and how does that positive/negative evidence compare with the PU v1/v2 LOCO
  pass pattern?
- **Conclusion to support:** CWRU has signed, testable load-transfer effects,
  while PU v1/v2 exposes an incomplete and condition-dependent boundary.
- **Archetype:** 2x2 mixed heatmap: continuous CWRU effects on the left,
  discrete PU pass states on the right.
- **Statistics:** CWRU cell = registered mean LLM--rule percentage-point effect
  plus Holm marker. PU cell = number of positive Holm-passing comparisons out
  of four. CWRU `lolo_load0` is excluded because the pool source is load0.
- **Color:** one symmetric zero-centered diverging scale for both CWRU panels;
  one five-state discrete palette for both PU panels. Colorbars are separate.
- **Source data:** exact cell effects, Holm state, PU numerator/4, and filters.
- **Reviewer risk:** the title must read `source load0 -> held-out load`; PU
  v3--v6 are moved to Supplementary Fig. S3 and remain stopped development
  stages, not hidden cross-condition results.
