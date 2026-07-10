# Private Machine-Tool Preflight Gate Report

- Status: PASS
- Allowed next stage: llm_smoke
- Class mapping confirmed: True
- Exact train/test raw-file duplicates: 0
- Exact train/test window duplicates: 0
- Metadata confound passed: True
- Signal learnability passed: True
- CNN learnability passed: True

## Gate Metrics

- metadata_safe ExtraTrees mean Macro-F1: 0.3222
- window_position_only ExtraTrees mean Macro-F1: 0.2298
- signal_feature_only full mean Macro-F1: 0.7981
- signal_feature_only full worst-fold Macro-F1: 0.5372
- SimpleCNN full mean Macro-F1: 0.8200

## Reasons

- All preflight gates passed.

## Evidence Boundary

- The 1/2/3 class mapping is confirmed by the project owner on 2026-07-10.
- The mapping is not treated as published MechaForge PDF content.
- Test file IDs 7/8 were used only for inventory and leakage integrity checks in this preflight.
- No LLM/API call, synthetic waveform, synthetic recipe, or formal held-out test was run.
