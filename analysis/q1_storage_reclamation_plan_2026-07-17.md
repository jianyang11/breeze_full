# Q1 storage reclamation plan — 2026-07-17

## Decision

The audit identified a smallest byte-preserving reclamation set: two batches
contain 35 files totaling 5.800669 GiB. The current
allocated project size is 50.812199 GiB; subtracting logical
candidate bytes would predict 45.011530 GiB, below the 47 GiB working
watermark. This is not an execution decision: follow-up dependency inspection
found scripts that directly open the duplicate paths, and deletion authorization
was rejected. Both batches are therefore preserved.

No deletion has been performed. Every target is locked as
`PRESERVE_PENDING_TRANSPARENT_ARCHIVE_READER` in
`analysis/q1_storage_reclamation_manifest_2026-07-17.csv`.

## Audited but deferred batch A — MU-TCM exact small-subset copies

- Targets: 30 files, 3.810511 GiB.
- Evidence: each target and its mapped `full_dataset/` archive member has equal
  byte count and full SHA-256 in `q1_mutcm_duplicate_ledger_2026-07-17.csv`.
- Preserved: `full_dataset.7z` (archive SHA-256 `c653f3dc2e762c9bfd21e8a9248cc12494ff6ae6e5991f93c4b6845a50f37223`), both
  size-different subset CSVs, and both platform-metadata files.
- Restore: stream the named `restore_member` from the retained 7z with system
  `bsdtar` to a same-directory temporary file, verify `target_sha256`, then
  atomically rename it to `target`.
- Operational dependency: `audit_mutcm_small_subset.py` directly opens
  `small_subset`; a transparent archive reader or tested automatic materializer
  is required before reconsideration.
- Decision: preserve after the user declined deletion authorization.

## Audited but deferred batch B — IMS exact nested copies

- Targets: 5 files, 1.990158 GiB.
- Evidence: full stream hashes prove that retained `4_Bearings.zip` contains the
  exact `IMS.7z`, which contains the exact three RAR files and PDF.
- Preserved: `data/ims/raw/4_Bearings.zip` with SHA-256
  `21001ac266c465f5d345ec42d7b508c6a6328487fd9d4d7774422dd5ea10ad83` and every audit manifest.
- Restore chain: atomically stream `4. Bearings/IMS.7z` from the ZIP and verify
  its hash; extract each named member from that 7z using system `bsdtar` into a
  temporary path, verify its hash, then atomically rename.
- Risk: low exact nested duplication. The Set-3 semantic README conflict remains
  documented and is not altered by retaining the byte-identical outer wrapper.
- Operational dependency: `ims_manifest.py` directly opens the three local RARs
  and README; exact recoverability alone does not keep that command runnable.
- Decision: preserve until a direct-from-wrapper reader is implemented and tested.

## Explicit exclusions

- `breeze/runs/`: 1.406 GiB of exact file-level candidates stay retained because
  removing files can break complete run-root provenance even when content exists
  elsewhere.
- DIRG NPZs (4.685 GiB): retained until checkpointed, atomic regeneration exists.
- XJTU archive (4.139 GiB): retained as the only local raw source.
- MU-TCM `full_dataset/`, original archive, virtual environment, `.bbl`, user-dirty
  `tmp/`, and formal release roots: retained.
- Convention caches (0.003 GiB): omitted because they add deletion risk without
  materially changing the storage constraint.

## Execution and verification contract

1. Before each batch, recompute every target hash and every retained-source hash;
   any drift aborts the entire batch.
2. Delete only manifest paths, without a glob and without deleting directories.
3. Append each completed target to `analysis/q1_storage_ledger.csv` so the batch
   is resumable after interruption.
4. After each batch, rerun its source audit, verify all non-target paths, inspect
   Git status, and measure both project allocation and filesystem free space.
5. If the first batch already satisfies the measured watermark, the second can
   be skipped; the core scientific target is never exchanged for extra space.
