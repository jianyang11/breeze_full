# XJTU-SY multipart archive audit — 2026-07-17

## Integrity verdict

**PASS** for RAR header and manifest integrity. `rarfile`
4.3 resolved one contiguous six-volume chain, and every
volume has a recorded full SHA-256. The first five volumes have the fixed
volume size and the sixth is the non-empty final volume.

- Compressed volumes: 6 (4.139 GiB)
- Archive entries/files: 9236 / 9217
- Files: 9216 CSV + 1 PDF
- Declared uncompressed bytes: 12220812451 (11.382 GiB)
- Regimes/bearings: 3 / 15
- Regimes: `35Hz12kN;37.5Hz11kN;40Hz10kN`
- Entries spanning a next volume: 5
- Encrypted entries: 0

This validates the RAR5 volume chain and complete header/member traversal. It
does not claim full payload CRC testing because no compatible `unrar`/`unar`
extractor is installed and no 11.38 GiB extraction was created under the 50 GB
budget.

## Current-artifact reference audit

The structured config/manifest scan found 2 XJTU label
references and 0 bindings to `data/xjtu` or a RAR
part. Hits are:

- `breeze/results/phaseB_api_usage_log.csv` (dataset_label_only)
- `breeze/results/phaseB_xjtu_physics_config.json` (dataset_label_only)

Historical registry/config references therefore do not prove that these local
parts fed any current pool or result. No extracted XJTU data, processed XJTU
array, split manifest, generated pool, or evaluated result is present.

## Storage decision

Candidate state: `HIGH_RISK_RECLAMATION_CANDIDATE_PENDING_EXPLICIT_AUTHORIZATION_AND_EXTERNAL_REDOWNLOAD_CHECK`.

The Q1 main protocols are PU, CWRU, and Berkeley; the historical audit records
XJTU-SY as skipped and its label semantics as run-to-failure prognostics rather
than ready-made fault-class windows. The six parts are not needed by a current
result, but they are the only local raw copy. External re-download availability
was not successfully revalidated in this audit. Therefore they are **not** a
safe automatic deletion: retain unless the user explicitly accepts that risk
after a fresh external recovery check. No file was deleted.
