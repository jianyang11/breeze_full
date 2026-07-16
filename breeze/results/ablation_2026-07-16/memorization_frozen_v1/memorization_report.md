# Synthetic-to-real memorization audit

Status: complete zero-API frozen-pool audit.

The audit uses the exact synthetic selections in the physics-v3 manifests and class-matched outer-training windows. `raw_nrmse` is RMSE after class-reference per-channel standardization. `feature_distance` uses the same real-scaled log-RMS/PSD-CDF representation as the within-pool diversity metric, but measures synthetic-to-real distance. `max_abs_xcorr` is the largest absolute global-energy-normalized multichannel cross-correlation over all linear lags. Only byte-identical float32 equality is called an exact copy; no distance or correlation cutoff was selected after viewing results.

## Availability

| dataset | pool | status | reason |
|---|---|---|---|
| pu | llm | available | frozen_balanced_pool |
| pu | rule | available | frozen_balanced_pool |
| pu | random_open_loop | available | frozen_balanced_pool |
| pu | noise_aug | available | deterministic_noise_aug_outer_train |
| cwru | llm | available | deterministic_metric_subsample_of_frozen_pool |
| cwru | rule | available | deterministic_metric_subsample_of_frozen_pool |
| cwru | random_open_loop | unavailable | no matching frozen pool exists for this protocol |
| cwru | noise_aug | available | deterministic_noise_aug_outer_train |
| berkeley | llm | available | deterministic_metric_subsample_of_frozen_pool |
| berkeley | rule | available | deterministic_metric_subsample_of_frozen_pool |
| berkeley | random_open_loop | available | deterministic_metric_subsample_of_frozen_pool |
| berkeley | noise_aug | available | deterministic_noise_aug_outer_train |

## Per-class summary

| dataset | pool | class | n syn/ref | exact | min NRMSE | min feature distance | max |xcorr| |
|---|---|---|---:|---:|---:|---:|---:|
| berkeley | llm | degraded | 20/1207 | 0 | 0.4248 | 11.7558 | 0.9887 |
| berkeley | llm | healthy | 20/629 | 0 | 0.3104 | 11.3811 | 0.9318 |
| berkeley | noise_aug | degraded | 20/1207 | 0 | 0.0347 | 1.7360 | 0.9995 |
| berkeley | noise_aug | healthy | 20/629 | 0 | 0.0430 | 9.6903 | 0.9995 |
| berkeley | random_open_loop | degraded | 20/1207 | 0 | 1.4943 | 46.1266 | 0.8059 |
| berkeley | random_open_loop | healthy | 20/629 | 0 | 3.9252 | 48.5935 | 0.8258 |
| berkeley | rule | degraded | 20/1207 | 0 | 0.3366 | 1.0610 | 0.9986 |
| berkeley | rule | healthy | 20/629 | 0 | 0.3326 | 1.5086 | 0.9694 |
| cwru | llm | B | 20/163 | 0 | 0.1492 | 2844.9899 | 0.2524 |
| cwru | llm | IR | 20/163 | 0 | 0.6499 | 13641.1234 | 0.2809 |
| cwru | llm | OR | 20/287 | 0 | 0.7884 | 256.5630 | 0.3013 |
| cwru | llm | healthy | 20/83 | 0 | 1.2836 | 46.3961 | 0.3003 |
| cwru | noise_aug | B | 20/163 | 0 | 0.0184 | 868.5679 | 1.0000 |
| cwru | noise_aug | IR | 20/163 | 0 | 0.0374 | 15315.9878 | 0.9998 |
| cwru | noise_aug | OR | 20/287 | 0 | 0.0383 | 181.8766 | 0.9997 |
| cwru | noise_aug | healthy | 20/83 | 0 | 0.2605 | 572015.4098 | 0.9719 |
| cwru | rule | B | 20/163 | 0 | 0.1422 | 3788.8929 | 0.2403 |
| cwru | rule | IR | 20/163 | 0 | 0.6104 | 7115.3429 | 0.3198 |
| cwru | rule | OR | 20/287 | 0 | 0.7746 | 342.6531 | 0.3469 |
| cwru | rule | healthy | 20/83 | 0 | 0.9254 | 1156.2876 | 0.6706 |
| pu | llm | IR | 150/1444 | 0 | 0.6572 | 66.4080 | 0.9969 |
| pu | llm | OR | 150/1202 | 0 | 0.3478 | 4.4726 | 0.9975 |
| pu | llm | healthy | 150/1200 | 0 | 0.4054 | 66.7369 | 0.9981 |
| pu | noise_aug | IR | 150/1444 | 0 | 0.0317 | 450.8767 | 0.9997 |
| pu | noise_aug | OR | 150/1202 | 0 | 0.0275 | 15.8693 | 0.9997 |
| pu | noise_aug | healthy | 150/1200 | 0 | 0.0317 | 665.0193 | 0.9996 |
| pu | random_open_loop | IR | 150/1444 | 0 | 0.5743 | 66.0543 | 0.9967 |
| pu | random_open_loop | OR | 150/1202 | 0 | 0.3534 | 7.6716 | 0.9915 |
| pu | random_open_loop | healthy | 150/1200 | 0 | 0.4275 | 78.3520 | 0.9958 |
| pu | rule | IR | 150/1444 | 0 | 0.7437 | 81.1718 | 0.9969 |
| pu | rule | OR | 150/1202 | 0 | 0.4398 | 7.0324 | 0.9969 |
| pu | rule | healthy | 150/1200 | 0 | 0.4998 | 69.5765 | 0.9968 |

Machine-readable per-sample results are in `memorization_per_sample.csv`.
