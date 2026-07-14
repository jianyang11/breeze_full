# Private machine-tool v3 — S-C capacity failure

## Frozen outcome

S-C stopped at `98/100` counted API attempts with no eligible pending slot:

| class | admitted / target |
|---|---:|
| normal machining | 20 / 20 |
| lead-screw anomaly | 20 / 20 |
| base imbalance | 18 / 20 |

The two remaining base-imbalance slots each exhausted the fixed initial-plus-
three-feedback request limit. The run therefore stopped below 100 rather than
inventing new slots, increasing a feedback limit, relaxing a gate, or making
requests merely to consume the budget. A balanced S-C pool does not exist, so
S-C has no downstream result and cannot be considered for formal evaluation.

## Ledger accounting

- Formal IDs `7/8` read: `0`.
- API requests: `98`; admitted requests: `58`.
- Logged outcome groups: 58 admitted, 31 recipe-schema rejections, 5 `psd_w1`
  rejections, 4 API/JSON failures.
- The first three parser-only failures remain counted. The amendment-1 decoder
  accepted wrapped JSON but did not relax the exact recipe schema.

The bottleneck is not a permissive admission gate: accepted candidates pass
the unchanged verifier, existing class-identity certificate, duplicate check,
and diversity check. It is the fixed finite request/feedback capacity under a
strict recipe schema, concentrated in base-imbalance slots. No rejected
waveform was repaired or retried outside its registered feedback round.
