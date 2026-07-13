# PU LOCO v4 internal S2/S1 acceptance failure record

## Boundary

- All evidence below is from train-bearing-only internal pseudo-LOCO work.
  Registered PU LOCO held-out windows were not read.
- API ledger: no new API request was made. The ledger remains 1131/3000.
- No formal preregistration or formal held-out experiment was run.

## S2: condition-aware morphology candidates

The v4 implementation corrects the old v3 development candidates by:

1. calibrating each v2 gate on the union of all three source conditions;
2. using all accepted training-source LLM recipe structures rather than
   discarding non-nearest templates;
3. sampling full band-weight vectors from the balanced union of the three
   source-condition empirical supports, rather than a target point estimate;
4. sampling OR/IR resonance within their documented support bands.

The first internal pseudo-held-out fold, `N09_M07_F10`, did not satisfy the
mandatory five-accepted-samples-per-class smoke gate:

| candidate | template sampling | kept healthy | kept OR | kept IR | outcome |
|---|---|---:|---:|---:|---|
| morphology_idw | 2 source-stratified templates/class × 5 renderer seeds | 1 | 5 | 1 | fail |
| morphology_idw | 5 source-stratified templates/class × 5 renderer seeds | 1 | 16 | 5 | fail |
| morphology_nearest | 5 source-stratified templates/class × 5 renderer seeds | 3 | 10 | 6 | fail |

All rejections were retained in slot manifests with v2 gate reports. No rejected
waveform was repaired or admitted. Since neither zero-API candidate can build a
balanced 5/class smoke pool in the first fold, neither is eligible for the
10-seed `n_syn=20/class` downstream comparison.

## S1: BREEZE-H real healthy carrier plus synthetic fault injection

The hybrid implementation samples source-condition healthy vibration carriers,
adds target-kinematic fault impulses before admission, and uses rendered current
channels. Fault amplitude is the LLM recipe's impulse-to-target-RMS ratio scaled
to the selected real carrier RMS. Healthy samples use only the frozen
`noise_aug` magnitude (`N(1, 0.04)` scale plus `0.03σ` jitter). Every complete
sample then receives one unmodified v2 admission decision.

For the same pseudo-held-out fold:

| trial | healthy attempts | kept healthy | kept OR | kept IR | outcome |
|---|---:|---:|---:|---:|---|
| nominal smoke | 5 | 0 | 1 | 1 | fail |
| capacity diagnostic | 800 | 4 | 1 | 1 | fail |

The carrier-only audit explains the failure. Among 100 deterministically sampled
healthy training windows per source condition, the target-kinematic v2 gate
accepted raw / noise-perturbed carriers as follows:

| source condition | raw pass | frozen-noise pass |
|---|---:|---:|
| N15_M01_F10 | 1/100 | 1/100 |
| N15_M07_F04 | 0/100 | 0/100 |
| N15_M07_F10 | 1/100 | 1/100 |

The low healthy acceptance rate is therefore a property of the frozen
train-only target-kinematic gate, not an absent real-background carrier. A
20/class hybrid pool would require an unbounded or near-copy-prone rejection
search; it is not advanced to downstream evaluation and no gate threshold is
altered.

## Next admissible step

The protocol now calls for the third candidate: explicit LLM condition
extrapolation from the three source-condition morphology feature tables, capped
at 50 new API requests. It cannot run in the current environment because
`OPENAI_API_KEY` is not configured. Once the user supplies a valid configured
credential, the next run will record the exact request count and remain within
the 50-call ceiling. Until then, BREEZE-U cannot be formed fairly because no
balanced admitted BREEZE pool exists.
