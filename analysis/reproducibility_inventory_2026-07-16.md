# BREEZE reproducibility inventory

Audit date: 2026-07-16. Scope: the final public-data manuscript only.

## Versioned and directly addressable

| Component | Repository path | Audit result |
|---|---|---|
| Prompt template and recipe schema | breeze/src/llm.py | Tracked |
| Deterministic renderer and local seed handling | breeze/src/renderer.py | Tracked |
| Verifier implementation | breeze/src/verifier/v2.py; breeze/src/verifier/features.py | Tracked |
| Paper table generator | breeze/scripts/build_paper_tables.py | Tracked |
| Figure generator | breeze/src/figures.py | Tracked |
| PU fixed pools and pool manifests | breeze/results/phaseA_v2_frozen_2026-07-06/breeze/runs/phaseA_v2_balanced/ | Tracked |
| PU freeze checksums | breeze/results/phaseA_v2_frozen_2026-07-06/manifest_sha256.csv | Tracked |
| CWRU formal seed rows and tests | breeze/results/cwru_patch_v2_2026-07-07_frozen/ | Tracked |
| Berkeley formal seed rows and tests | breeze/results/milling_berkeley_v2_binary_formal_2026-07-08/ | Tracked |
| PU/CWRU/Berkeley physics metrics and pool hashes | breeze/results/ablation_2026-07-14/physics_frozen_full_v3_*/ | Tracked |
| Gate-ablation manifests and results | breeze/results/ablation_2026-07-15/gate_ablation_v1/ | Tracked |
| Synthetic-to-real audit script | breeze/scripts/compute_memorization_audit.py | Added in final audit |
| Global BH sensitivity script | breeze/scripts/compute_global_bh_sensitivity.py | Added in final audit |

The PU physics manifest resolves to the versioned frozen pool arrays. It
records exact SHA-256 values for LLM, rule, random open-loop, and deterministic
noise-augmentation pools.

## Present locally but excluded by the Git ignore policy

The following primary arrays and records exist in the audited workspace, but
the repository rule for breeze/runs/ excludes them from the versioned Git tree:

- CWRU LLM pool and manifest:
  breeze/runs/phaseB_cwru_within_load0_llm_full_v1_combined/
- CWRU rule pool and manifest:
  breeze/runs/phaseB_cwru_within_load0_rule_pilot_v1/
- Berkeley LLM pool, recipe JSON records, and renderer expansions:
  breeze/runs/milling_berkeley_v2_binary_formal_2026-07-08_v11_repair_eq_coherent/
- Berkeley rule and random open-loop pools:
  breeze/runs/milling_berkeley_v2_binary_formal_2026-07-08_rule_random/
- PU detailed per-candidate recipe/gate records:
  breeze/runs/rescreen_v2_full/records/

The tracked physics-v3 manifests record the exact paths, source indices, and
SHA-256 hashes of these CWRU/Berkeley pools, but a fresh clone cannot replay
their waveforms until the arrays and detailed records are deposited separately.

## Required public release action

Package the ignored CWRU/Berkeley pools, manifests, recipe JSON, renderer seeds,
and detailed gate records in a versioned GitHub release or data-repository
supplement. Publish a checksum index and cite its persistent identifier in the
final Data and code availability statement. Until that deposit, the repository
supports numerical-result verification and exact PU pool replay, not complete
CWRU/Berkeley waveform replay.

## Provenance boundary

The original PU provider version, top-p, and provider-side sampling seed are not
recoverable. Archived PU recipes and local renderer seeds reproduce the frozen
PU pool; they do not reproduce the original provider response bit for bit.
