# Private machine-tool v3 — S-C API amendment 2

**Frozen:** 2026-07-14, after S-C amendment-1 smoke and before any further request.

## Observed smoke state

At six cumulative S-C requests, the robust transport decoder admitted one
`base_imbalance` and one `lead_screw_anomaly` candidate. The pending
`normal_machining` slot produced a valid recipe whose three deterministic
expansions all retained correct class identity and passed diversity, sanity,
soft-spectrum, and statistics gates. Each was rejected only by the unchanged
Y-channel `psd_w1` gate: observed values `0.09481`, `0.09504`, and `0.09770`
exceeded the fixed threshold `0.08519`.

The original S-C plan permits an initial response plus three structured
feedback rounds per pending slot. The normal slot has used only one
recipe-level feedback round after its parser-only transport failure. This
amendment permits up to two further requests, solely for normal slot 0, using
the recorded `psd_w1` feedback. The total smoke ceiling is therefore eight
requests; if normal is admitted earlier the run stops immediately.

No verifier threshold, response schema, renderer, discriminative statistic,
candidate pool, class identity evidence, or formal boundary is changed. The
extra calls are feedback resampling, not waveform repair. A still-unbalanced
smoke at the eight-request ceiling ends S-C before full-pool generation.
