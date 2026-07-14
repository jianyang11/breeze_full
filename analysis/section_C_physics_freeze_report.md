# Section C: frozen-pool physical-metrics record

Date: 2026-07-14
Status: completed for the frozen LLM, rule, random-open-loop, and deterministic-noise pools; trained-baseline pools remain pending §B formal completion.

## Scope and API accounting

This evaluation reads only the frozen outer-training references and frozen synthetic pools. It generated deterministic `noise_aug` comparison pools with the registered scale-and-jitter transform, but did not invoke an LLM or alter any frozen pool. It used **0 API calls**. The audited cumulative API count therefore remains **1231/3000**, and this work leaves the Section-C allocation of at most 300 untouched (the total remains at most 1531).

## Citable artifacts

The sole citable physical-metrics outputs are the three v3 directories below. Each contains a CSV of metric values, a source-and-sampling manifest with SHA-256 pool fingerprints, an availability table, and a Markdown definition record.

| protocol | per-class synthetic budget | citable directory | rows |
|---|---:|---|---:|
| PU Phase-A v2 | 150 | `breeze/results/ablation_2026-07-14/physics_frozen_full_v3_pu/` | 80 |
| CWRU within-load0 | 20 | `breeze/results/ablation_2026-07-14/physics_frozen_full_v3_cwru/` | 81 |
| Berkeley v2 binary | 20 | `breeze/results/ablation_2026-07-14/physics_frozen_full_v3_berkeley/` | 48 |

All v3 metric values are finite. CWRU has no matching frozen `random_open_loop` pool; its availability CSV explicitly records that comparator as unavailable rather than substituting any other pool.

Earlier dated `physics_pretrained_v1`, `physics_frozen_full_v1`, and v2 directories are retained as an audit trail and are **not citable**. The first two are incomplete (they wrote deterministic noise pools but no complete metric set). The v2 Berkeley run exposed that kurtosis is undefined for near-constant windows, which made diversity `NaN`. V3 corrects the definition rather than imputing those values: nearest-neighbour diversity uses only log-RMS and PSD-CDF coordinates, quantities defined for every finite window. Kurtosis remains separately reported as a bearing fidelity statistic.

## Metric definitions

All metrics are class-conditional and reference the matching outer-training fold. Lower distributional distances/errors are not a downstream-performance claim.

| family | fidelity metrics | diversity metric |
|---|---|---|
| PU/CWRU bearing | fault-frequency envelope-peak alignment (fault classes only); RMS W1; kurtosis W1; PSD-CDF W1; mean relative PSD-band-energy error | mean nearest-neighbour distance in real-scaled log-RMS + PSD-CDF space, together with the real-reference value |
| Berkeley milling | six-tooth TPF-amplitude-ratio W1 at 826 rpm; RMS W1; PSD-CDF W1; mean relative PSD-band-energy error | the same finite log-RMS + PSD-CDF nearest-neighbour metric |

The new tables are deliberately not numerically equated with the old CWRU quality report: that report used verifier pass rate, band L1, PSD W1 mean/p90, envelope prominence, and nearest synthetic-to-real distance. The new table instead uses the registered Section-C W1/error/diversity definitions above.

## Frozen-report consistency check

Before the full run, the existing CWRU quality script was replayed against the frozen full LLM pool. Its four LLM rows reproduce the frozen `phaseB_cwru_pool_quality_full_v1.csv` values exactly, including the class counts 603/750/631/750 and the reported band-L1, PSD-W1, envelope-prominence, and nearest-synthetic-to-real columns. The replay is retained at:

`breeze/results/ablation_2026-07-14/physics_small_v1/cwru_legacy_compat.csv`

The rule rows in that replay use the available `rule_pilot_v1` pool and are therefore not presented as a numerical replication of the older, smaller `rule_smoke_v5` pool. No frozen-report conflict was found.

## Interpretation boundary

These are physical-fidelity diagnostics for the existing recipe pools. They do not change the registered downstream results, do not constitute an overall pool ranking, and do not alter Berkeley's partial/no-go conclusion (15/18 aggregate comparisons; 12/12 against non-structured baselines; the specified rule boundaries). In particular, an individual diagnostic may favor a different pool without supporting a general superiority claim.

Trained TimeGAN/DDPM pools will be added only after the formal, non-smoke §B run completes. Smoke pools are prohibited from this table.
