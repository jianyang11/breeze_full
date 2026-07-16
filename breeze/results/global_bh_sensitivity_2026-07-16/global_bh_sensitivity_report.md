# Global BH sensitivity audit

This is a zero-training, zero-API recalculation over the 102 core paired hypotheses:
12 PU Phase-A v2 source comparisons at n={5,10,25}, 72 provenance-valid
CWRU comparisons, and all 18 Berkeley binary comparisons. Registered
within-family Holm decisions remain primary.

| Dataset | hypotheses | Holm pass | global BH pass | agreeing decisions |
|---|---:|---:|---:|---:|
| PU | 12 | 12 | 12 | 12 |
| CWRU | 72 | 72 | 72 | 72 |
| Berkeley | 18 | 15 | 15 | 18 |
| **Total** | **102** | **99** | **99** | **102** |

The global BH sensitivity analysis preserves every registered pass/fail
decision. It does not replace the preregistered family-wise Holm analysis.

Frozen input SHA-256:
- PU: 61ff36947cbefefed977dab50c930e9c950266b012dfcd5828f6cbf7fead798a
- CWRU: a3b3ddda37d6d312326a7c1ce3f9d1e684b2b33b4d213154b1005a5409c70b0b
- Berkeley: 281c2eed1297797d2e3596797650a8f4de95009f1f4665e68caf4d3ae3ed6fdc
