# MU-TCM source archive audit — 2026-07-17

## Verdict

**PASS**. The original archive directory, the recorded extraction
manifest, and the local `signals_synced` directory contain the same
67 MAT file names. Every local file size equals its
recorded extraction size. Three files sampled without replacement from the
largest size quartile were streamed directly from the archive; `bsdtar`
decompression completed successfully and every streamed SHA-256 equals the
corresponding extracted-file SHA-256.

This establishes tested reconstructability of the retained synced subset; it
does not claim that untested archive members have been exhaustively rehashed.

## Archive identity

- Path: `data/MU-TCM face-milling dataset/full_dataset.7z`
- Bytes: 4426244593
- SHA-256: `c653f3dc2e762c9bfd21e8a9248cc12494ff6ae6e5991f93c4b6845a50f37223`
- Archive members: 223
- Synced MAT members: 67
- Size manifest: `breeze/results/mutcm_v2_synced_2026-07-09/mutcm_v2_synced_file_sizes.csv`
- Manifest/local counts: 67 / 67

## Deterministic sample rule

- Sampling frame: largest quartile by manifest byte size
  (17 of 67 files).
- RNG seed: `20260717`.
- Sample size: 3 without replacement.
- Integrity test: archive-member decompression exit status, streamed byte count,
  and SHA-256 equality against the extracted file.

| file | size (GiB) | matched SHA-256 prefix | status |
|---|---:|---|---|
| `Insert0Edge2_Vc200.0_fz0.1_ap1.5_VB0.018_Rep1.mat` | 0.437 | `79a7dae4fa437ef1…` | PASS |
| `Insert1Edge1_Vc50.0_fz0.1_ap1.5_VB0.137_Rep1.mat` | 0.491 | `cefe1efd38c0331f…` | PASS |
| `Insert3Edge1_Vc50.0_fz0.05_ap1.5_VB0.202_Rep3.mat` | 0.725 | `3097e456e705bfe3…` | PASS |

## Rebuild implication

The 67-file synced directory can be regenerated selectively from the retained
archive member prefix `full_dataset/signals_synced/`. Any reclamation remains a
separate, explicitly authorized action; this audit deletes nothing.
