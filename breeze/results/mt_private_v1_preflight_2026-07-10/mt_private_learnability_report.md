# Private Machine-Tool Train-Only LOFO Learnability

All rows use train files only and leave one file ID out at a time. File IDs 7/8
are not used for model selection, thresholding, feature selection, or parameter
selection in this audit.

| Baseline | Model | n_real | Mean Acc | Mean Macro-F1 | Worst Macro-F1 |
|---|---|---:|---:|---:|---:|
| majority | majority | full | 0.3626 | 0.1767 | 0.1379 |
| real_only | simple_cnn | 10 | 0.3433 | 0.2525 | 0.1147 |
| real_only | simple_cnn | 25 | 0.4174 | 0.3530 | 0.1873 |
| real_only | simple_cnn | 50 | 0.5316 | 0.4948 | 0.1748 |
| real_only | simple_cnn | full | 0.8394 | 0.8200 | 0.4938 |
| signal_feature_only | extra_trees | 10 | 0.7871 | 0.7354 | 0.3309 |
| signal_feature_only | extra_trees | 25 | 0.8201 | 0.7869 | 0.3032 |
| signal_feature_only | extra_trees | 50 | 0.8251 | 0.7922 | 0.4509 |
| signal_feature_only | extra_trees | full | 0.8353 | 0.7981 | 0.5372 |
| window_position_only | extra_trees | full | 0.2397 | 0.2298 | 0.0000 |
