# Private Machine-Tool Confound Audit

All diagnostics in this file use train-only leave-one-file-ID-out folds.
Class prefixes, filenames, source paths, labels, and test files are not classifier inputs.

## Metadata Diagnostics

| Baseline | Model | Mean Macro-F1 | Worst Macro-F1 |
|---|---|---:|---:|
| acquisition_index | extra_trees | 0.1667 | 0.1667 |
| acquisition_index | logistic_regression | 0.1667 | 0.1667 |
| metadata_safe | extra_trees | 0.3222 | 0.0000 |
| metadata_safe | logistic_regression | 0.4444 | 0.0000 |

## Window Position Diagnostic

| Baseline | Model | Mean Macro-F1 | Worst Macro-F1 |
|---|---|---:|---:|
| window_position_only | extra_trees | 0.2298 | 0.0000 |

## File-Level Signal Diagnostic

| Baseline | Model | Mean Macro-F1 | Worst Macro-F1 |
|---|---|---:|---:|
| file_level_signal_features | extra_trees | 0.7778 | 0.3333 |
