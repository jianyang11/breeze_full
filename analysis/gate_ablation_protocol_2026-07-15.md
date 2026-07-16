# PU verifier-gate ablation protocol

Status: locked before any E3 output is created (2026-07-15).

## Purpose

This is a zero-API, cached-candidate ablation of the verifier contribution on
the PU `N09_M07_F10` Phase-A file split. It is separate from the read-only
Phase-A v2 snapshot and cannot change any frozen pool, CSV, manifest, or claim.

## Fixed inputs and downstream protocol

- Candidate archive: `breeze/runs/pool_physics_file_k3/`, 150 K=3 proposal
  slots per class.
- Full-replay reference: `breeze/runs/rescreen_v2_full/pool_v2.npz`.
- Balanced baseline reference: the read-only Phase-A v2 LLM B=150/class pool.
- Train/test split, few-shot selector, CNN, optimizer, 60 epochs, test set,
  synthetic budget, and seeds follow the frozen Phase-A v2 protocol.
- New downstream evaluations use `n_real={5,10,25}`, 20 paired seeds, and
  150 cached synthetic windows per class. The full-gate reference is read from
  the frozen CSV after the raw-pool replay has passed bitwise equality.
- No LLM/API request, prompt change, gate calibration change, test-set choice,
  waveform repair, or new renderer seed is allowed.

## Gate mapping and variants

| Variant | Disabled evidence | Fixed treatment |
| --- | --- | --- |
| `full` | none | Must reproduce the archived full raw pool and frozen B=150 pool exactly. |
| `no_M2_stats` | `stats_union` | All remaining per-candidate gates remain active. |
| `no_M3_spectral` | `soft_spectrum` and `psd_w1` | Both spectrum predicates are disabled together. |
| `no_M4_envelope` | `envelope_multi` | All other predicates remain active. |
| `no_M5_diversity` | pool-level diversity only | Per-candidate gates remain active. |
| `delta_0p5`, `delta_1`, `delta_2` | none | Diversity lower bound is multiplied by 0.5, 1, or 2. |

Sanity remains active throughout. The PU current-sideband score is audit-only
in the frozen protocol and is never silently changed.

## Cached-expansion rule

An expansion waveform is included only when its parent recipe remains the
selected archived candidate for that slot. If disabling a gate admits an
earlier cached candidate, the archive may not contain expansion renders for
that candidate. It contributes exactly its archived waveform; no new expansion
is rendered. A pool that cannot reach B=150/class under this rule is reported
as capacity-limited and receives no downstream result.

## Output and interpretation

The runner writes a new dated directory containing checkpointed per-slot
records, candidate/pool manifests, acceptance accounting, B=150 pools,
class-conditional physical metrics, and append-only downstream CSVs. The
primary table reports slot acceptance, PSD-CDF W1, Accuracy and Macro-F1
changes from the frozen full-gate LLM pool. These paired deltas are descriptive
for the gate ablation; they do not replace the registered Phase-A recipe-source
Holm family.
