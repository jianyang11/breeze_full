# `breeze/runs` storage and provenance audit — 2026-07-17

## Verdict

**PASS**. All 34171 files under 149
top-level entries were read and SHA-256 hashed (2.708 GiB).
Exact-content grouping found 2985 duplicate groups.
After prioritizing the five release-required roots and tracked Phase-A frozen
copies as keepers, 3854 non-primary files
(1.406 GiB) are proven
exact-copy candidates.

No directory is considered duplicate because its name looks similar. Candidate
status requires complete SHA-256 equality and a designated retained copy.

## Preservation boundary

The five roots named by `analysis/reproducibility_inventory_2026-07-16.md` are
hard-preserved: CWRU LLM/rule, Berkeley formal LLM/rule-random, and PU detailed
rescreen records. Together they contain 1343 files and
0.143 GiB. Their ignored arrays/recipes are
release evidence and must not be removed merely because tracked numerical
summaries exist.

Root categories:

- DEVELOPMENT_SMOKE_OR_PILOT: 62 top-level entries
- DEVELOPMENT_UNCLASSIFIED: 23 top-level entries
- PRIMARY_RELEASE_REQUIRED: 5 top-level entries
- REFERENCED_LEGACY_EVIDENCE: 37 top-level entries
- TOP_LEVEL_RUN_RECORD: 21 top-level entries
- TRACKED_FROZEN_COPY: 1 top-level entries

`DEVELOPMENT_SMOKE_OR_PILOT` is a provenance category, not proof of
reconstructability. Non-duplicate smoke/API/recipe records remain retained
until their generating code, inputs, seeds, and provider boundary are audited.

## Action boundary

Only file-level `EXACT_DUPLICATE_CANDIDATE` rows may enter the reclamation plan.
Primary-release files are preserved even when another identical copy exists.
No deletion was performed; every proposed removal still requires explicit user
authorization and a post-batch hash/path check.
