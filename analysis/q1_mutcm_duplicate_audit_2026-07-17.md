# MU-TCM small-subset duplicate audit — 2026-07-17

## Verdict

**PASS** as an integrity audit. The small subset contains
34 files (3.811 GiB).
Exact size and full SHA-256 comparison proves 30 files
(3.811 GiB) duplicate their mapped
`full_dataset/` archive members.

- Size mismatch: 2
- Hash mismatch after equal size: 0
- Missing mapped archive member: 0
- Platform auxiliary metadata: 2

`SIZE_MISMATCH` means “not an exact duplicate”; it is not an integrity failure.
`AUXILIARY_METADATA` is OS-generated cache state, not source-dataset content.
Only `DUPLICATE` rows are reclamation candidates. This audit performs no deletion.
The CSV ledger contains complete paths, byte counts, and both hashes.
