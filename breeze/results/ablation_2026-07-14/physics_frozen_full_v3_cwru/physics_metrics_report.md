# Physics Metrics Report

Status: preliminary zero-API report for frozen recipe pools. Trained-baseline pools are intentionally absent until their formal 40-seed run is complete; smoke pools are excluded.

## Protocol

Each metric compares a class-conditional synthetic pool against the matching outer-training reference. The pool size is fixed per run and recorded in the machine-readable manifest. Noise augmentation is regenerated deterministically from the same outer-training data and the registered scale/jitter transform; its manifest is saved alongside the metrics.

## Availability

| dataset | pool | status | reason |
|---|---|---|---|
| cwru | llm | available | deterministic_metric_subsample_of_frozen_pool |
| cwru | rule | available | deterministic_metric_subsample_of_frozen_pool |
| cwru | random_open_loop | unavailable | no matching frozen pool exists for this protocol |
| cwru | noise_aug | available | deterministic_noise_aug_outer_train |

## Metric definitions

- `envelope_frequency_alignment_error_hz`: mean nearest envelope-spectrum peak error at the class's registered bearing frequency; it is not applicable to healthy windows.
- `rms_w1` and `kurtosis_w1`: Wasserstein-1 distance between synthetic and real window-level distributions.
- `psd_w1_mean`: mean Wasserstein distance between a synthetic PSD CDF and the real class median PSD CDF.
- `band_energy_relative_error_mean`: mean relative error of class-mean PSD-band energy fractions.
- `nn_diversity`: mean nearest-neighbour distance among synthetic log-RMS and PSD-CDF feature vectors after real-reference scaling; `real_nn_diversity` is the corresponding real-reference value. Kurtosis is excluded from this vector because it is undefined for constant windows, while `kurtosis_w1` remains a separate fidelity metric.
- Berkeley additionally uses `tpf_amplitude_ratio_w1`, evaluated at its documented 826 rpm and six-tooth TPF.

Machine-readable values: `physics_metrics.csv`; exact source and sampling provenance: `physics_pool_manifest.csv`.
