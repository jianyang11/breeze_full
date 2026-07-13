# Private machine-tool v3 admission audit

- Stage: zero-API inner-train audit only; formal IDs `7/8` were not read.
- Decision: `PASS`; next allowed stage: `s_a_s_b_smoke`.
- Real-carrier required core admission rate: `0.80` per class and nonzero rate per source file.
- Wrong-label controls admitted: `0/2960`.
- White-noise controls admitted: `0/300`.
- Constant controls admitted: `0/300`.

## Real-carrier results

| class | rate | source-file rates |
|---|---:|---|
| normal_machining | 0.934 | `{"1_1": 0.93717277486911, "1_2": 0.9085714285714286, "1_4": 0.9217391304347826, "1_5": 0.975609756097561}` |
| lead_screw_anomaly | 0.932 | `{"2_1": 0.8253968253968254, "2_2": 1.0, "2_4": 0.9577464788732394, "2_5": 0.9436619718309859}` |
| base_imbalance | 0.933 | `{"3_1": 0.9700598802395209, "3_2": 0.8909952606635071, "3_4": 0.9652173913043478, "3_5": 0.9243697478991597}` |

## Interpretation boundary

The reused generic verifier and existing ExtraTrees identity check are exploratory admission components, not component-physics evidence. No machine speed, lead, sensor mounting, or current semantics are inferred by this audit.
