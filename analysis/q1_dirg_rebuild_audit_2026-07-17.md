# DIRG deterministic rebuild audit — 2026-07-17

## Verdict

**PASS** at array-content level. The audit reloaded all
119 selected MAT members from the source ZIP one at a
time, regenerated 14875 windows and every metadata
array using the checked-in preprocessing implementation, and matched the data
section SHA-256, shape, and dtype of all 16 arrays in the
full NPZ. It then streamed the frozen 300 Hz / 1400 N mask and matched every
train/test array hash (14000 / 875 windows).

No second large NPZ or extracted raw copy was created.

## Provenance identities

- Raw ZIP bytes/SHA-256: 1642952410 / `e7b76ad2c65228a6ae70910666bb95521d207c636c4f56edcc6be6b6dbeb4e8b`
- Preprocessor SHA-256: `fdb1bb08095a1e15a26a6339bc4eb30746d735eed4b0771d07ae8f4869c501ab`
- Full NPZ container SHA-256: `a8393a68b2098eaa7f6c109a4b9d53fa55472379429d8c79726d2680da647d73`
- Train NPZ container SHA-256: `a27d436fafa70a7e6cc275019fb2c4457f3af4b1fa3a720e06da3028c795d8aa`
- Test NPZ container SHA-256: `fbee1f49fbd6b95fb956a43501c09969f3ca3252fa06b35bdc25c7b0b818f9ff`
- Semantic manifest SHA-256: `1ea960e5b205c18bafe249e5e0b32727372a9ab952236bd138436096150f8cad`

Container hashes identify the current files; the semantic manifest is the
determinism proof because compressed NPZ container metadata need not be stable
across rebuild times.

## Storage decision

The three large NPZ files total 4.685 GiB
and are semantically reconstructable from the retained raw ZIP plus the pinned
preprocessor. Candidate state is `REBUILDABLE_BUT_RETAIN_UNTIL_CHECKPOINTED_REBUILDER_EXISTS`: the current
preprocessor lacks per-file checkpoints and atomic large-output commits, so
these result-referenced arrays stay retained until the long-run contract is
implemented and tested. No file was deleted.
