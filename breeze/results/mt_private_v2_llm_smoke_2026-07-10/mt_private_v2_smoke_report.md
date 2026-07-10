# Private Machine-Tool v2 LLM Closed-Loop Smoke

Status: inner-validation smoke only; no formal test file was read.

## Gate Summary

- Decision: `BLOCKED`
- Next allowed stage: `failure_analysis_only`
- API requests: `60/60`; cumulative `1131/3000`.
- Formal test files read: `0`.
- Accepted counts: `{'normal_machining': 5, 'lead_screw_anomaly': 5, 'base_imbalance': 5}`; balanced n_syn `5`.
- Feedback rescue rate: `0.632`; feedback gate `True`.
- Downstream gate: `False`; real/noise cells `0/6`, rule `2/6`, random `1/6`.

## Frozen Boundaries

- Development uses file IDs 1/2/4/5 for inner train and file 10 only for inner validation.
- No TPF, rotational-order, bearing-frequency, spindle speed, or invented machine geometry was used.
- Waveforms rejected by the verifier were not repaired; later rounds used new recipes and fresh renders.
