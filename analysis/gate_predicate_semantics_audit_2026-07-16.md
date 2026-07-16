# Gate predicate semantics audit

Status: verified against `breeze/src/verifier/v2.py` and the corrected
`breeze/paper/main_cas.tex` on 2026-07-16.

## Finding

The frozen in-domain v2 verifier does not contain the manuscript's former
tautological one-sided predicate. The error was confined to the mathematical
summary in the paper. The implementation uses the following acceptance logic:

| Predicate family | Implemented acceptance relation | Source location |
|---|---|---|
| legacy statistics | every feature lies in its train-supported interval | `verifier/v2.py::_legacy_stats_check` |
| robust statistics | axis distance is at most its calibrated threshold; the active union accepts legacy interval or axis ellipsoid | `verifier/v2.py::verify` |
| soft spectrum | every coordinate lies in its train-supported interval | `verifier/v2.py::verify` |
| PSD-W1 | distance is at most the calibrated upper threshold | `verifier/v2.py::verify` |
| fault envelope | prominence is at least its lower floor and band energy lies in its interval for at least one supported band | `verifier/v2.py::_verify_envelope` |
| healthy envelope suppression | fault prominence is at most its upper ceiling | `verifier/v2.py::_verify_envelope` |
| optional hard MCSA | sideband prominence is at least its lower floor | `verifier/v2.py::verify` |
| pool diversity | the first per-class item passes diversity when the selected set is empty; subsequent items require nearest selected-item distance at least `delta_y` | `scripts/run_pu_gate_ablation.py::diversity_filter` and `src/rescreen_v2.py` |

The paper now partitions active feature gates into disjoint interval,
upper-bound, and lower-bound index sets. It also makes the empty-set diversity
convention explicit. The empty-set clause affects diversity only and never
bypasses per-candidate signal or physical gates.

## Regression guard

`breeze/tests/test_paper_gate_semantics.py` checks the LaTeX direction-specific
relations, prohibits restoration of the old OR expression, verifies the
empty-set clause, and locks the corresponding source-level comparison
operators. This is a semantics/source regression test; it does not rerun or
modify any frozen result.
