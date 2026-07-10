# Private Machine-Tool Duplicate Audit

Exact train/test duplicates are treated as integrity blockers. High nearest-neighbor
cosine similarity is reported as a diagnostic and is not equated with leakage.

- Exact raw train/test duplicate files: 0
- Exact train/test duplicate windows: 0
- Windows embedded for near-duplicate diagnostics: 2223

## Near-Duplicate Distribution

| Diagnostic | min | q05 | median | q95 | max |
|---|---:|---:|---:|---:|---:|
| nearest_train_test_cosine | 0.185197 | 0.210613 | 0.264824 | 0.372677 | 0.496099 |
| same_class_cross_file_cosine | 0.159420 | 0.195090 | 0.251395 | 0.356731 | 0.513400 |
| different_class_cross_file_cosine | 0.181206 | 0.212825 | 0.263178 | 0.358995 | 0.497122 |
