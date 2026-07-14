# Phase-B CWRU Pool Quality Smoke

| method | class | n | pass rate | band L1 | PSD W1 mean | PSD W1 p90 | env prom mean | NN syn-real mean |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| rule_smoke_v5 | healthy | 38 | 1.000 | 0.0768 | 29.352 | 44.177 |  | 0.115 |
| rule_smoke_v5 | IR | 92 | 1.000 | 0.0377 | 226.938 | 242.247 | 9.361 | 0.529 |
| rule_smoke_v5 | B | 80 | 1.000 | 0.0520 | 79.720 | 102.721 | 10.047 | 0.245 |
| rule_smoke_v5 | OR | 99 | 1.000 | 0.0961 | 208.870 | 222.061 | 10.331 | 0.619 |
| llm_frozen_full_v1 | healthy | 603 | 1.000 | 0.0107 | 34.253 | 42.805 |  | 0.148 |
| llm_frozen_full_v1 | IR | 750 | 1.000 | 0.0406 | 231.536 | 244.067 | 11.538 | 0.549 |
| llm_frozen_full_v1 | B | 631 | 1.000 | 0.0529 | 99.429 | 123.445 | 9.697 | 0.251 |
| llm_frozen_full_v1 | OR | 750 | 1.000 | 0.0962 | 223.098 | 238.788 | 12.725 | 0.622 |

These are diagnostics only; they do not establish downstream superiority.
