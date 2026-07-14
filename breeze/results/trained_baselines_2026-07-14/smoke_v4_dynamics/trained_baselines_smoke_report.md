# Trained-baseline PU smoke report

Status: PASSED

This is a pipeline smoke test only. It uses a capped training subset, one seed, and one epoch per generator stage. It is not a registered result and must not be used in the manuscript or in any comparison.

## Detail

Both selected trained-baseline pipelines completed their checkpoint, sampling, pool persistence, and downstream-evaluation paths.

## Produced rows

| method | train mode | n_real | seed | n_syn | Acc | Macro-F1 |
|---|---|---:|---:|---:|---:|---:|
| timegan | full_train | 5 | 0 | 60 | 0.312890 | 0.177029 |
| timegan | few_shot | 5 | 0 | 60 | 0.316008 | 0.180118 |
| ddpm | full_train | 5 | 0 | 60 | 0.312890 | 0.159133 |
| ddpm | few_shot | 5 | 0 | 60 | 0.312890 | 0.159007 |
