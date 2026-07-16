# Reviewer-revision integration log: E3 and E4

Date: 2026-07-16
Scope: zero-API verifier-gate ablation (E3) and verified related-work additions
(E4). Frozen result directories were read only; this update creates no new LLM
recipes and makes no claim from the still-running trained-baseline queue (E1).

## E3: cached-candidate verifier ablation

The implementation and protocol are recorded in
`breeze/scripts/run_pu_gate_ablation.py` and
`analysis/gate_ablation_protocol_2026-07-15.md`. It replays the archived PU
`K=3` 450-slot-per-class candidate archive, rather than rendering, repairing,
or re-querying any recipe. The complete-gate replay reproduced the frozen
balanced pool exactly (pool SHA-256
`2118c800dfe8986dbf80e95e076e646a6a72c70d946a0aaa86058c6d1d3a145c`).

M2 disables the statistical union; M3 disables the soft-spectrum and PSD-W1
checks together; M4 disables multi-band envelope evidence; and M5 disables
only pool-level diversity. Sanity and available current-sideband evidence remain
active. Every evaluable condition retains the frozen file split, 150 synthetic
windows per class, the same 60-epoch CNN, and 20 paired seeds.

The generated report
`breeze/results/ablation_2026-07-15/gate_ablation_v1/gate_ablation_report.md`
shows a negative paired mean Accuracy and Macro-F1 difference at every
`n_real in {5, 10, 25}` after each individual M2--M5 removal. The direction is
therefore reported descriptively; this post-freeze ablation does not replace the
registered recipe-source Wilcoxon/Holm family. M3 removal worsens class-averaged
PSD-W1, while M4 removal can lower that single diagnostic but still lowers
downstream metrics, so no one physical distance is reinterpreted as a universal
quality score.

The diversity sensitivity table is also generated from the replay. `1.0 delta_y`
is the verified full pool, `0.5 delta_y` is byte-identical to the no-M5 pool
under the fixed selection seed, and `2.0 delta_y` reaches only 64 healthy
windows against the predeclared 150-window budget. The last variant is recorded
as a capacity stop; no lower-budget pool or downstream comparison was made.

## E4: literature and manuscript integration

Six publisher-verified references were added for few-shot/meta-learning and
split-validity context. Exact source records, identifiers, and the deliberately
limited intended wording are in
`analysis/e4_verified_reference_candidates_2026-07-16.md`. The manuscript
positions classifier-side meta/transfer learning as complementary to BREEZE, not
as a direct performance comparison. It also explains the acquisition-unit split
choice without claiming that all window-level studies are invalid.

`breeze/scripts/build_paper_tables.py` now validates the E3 CSV grids and exact
equivalences before generating `breeze/paper/generated/gate_ablation.tex`. The
Results section introduces the table and retains the capacity-stop qualification.
The CAS manuscript compiled with all new citations resolved; PDF pages containing
the new table and bibliography were rendered and visually checked.

## E1 boundary at this checkpoint

The formal PU v2 TimeGAN/DDPM queue remains incomplete and is deliberately not
used in the manuscript. Its output root is
`breeze/results/trained_baselines_2026-07-16/formal_pu_v2/`; the v1 duplicate-
resume incident remains preserved and excluded in
`analysis/trained_baseline_v1_audit_2026-07-16.md`. The runner now holds an
advisory output-root lock, preventing a competing resume invocation from
creating duplicate cells. No result, cost comparison, or trained-baseline claim
will be inserted before the complete 40-seed grid is available and audited.
