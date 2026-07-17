# IMS nested-archive audit — 2026-07-17

## Integrity and containment verdict

**PASS**. Full streaming SHA-256 comparison proves the local
`IMS.7z` is byte-identical to `4_Bearings.zip::4. Bearings/IMS.7z`. A second full
stream proves the three local RAR files and README PDF are each byte-identical
to their `IMS.7z` members. ZIP CRC `08955097` and both container
extractor return paths completed successfully; no large extracted copy was made.

- Exact nested duplicate relationships: 5
- RAR payload headers: 3 archives,
  9464 files,
  6.077 GiB declared uncompressed
- Cross-RAR `(file_size, CRC32)` overlaps: 0

The three RARs are therefore unique test payloads relative to one another, but
their standalone archive files are exact duplicates of members already inside
`IMS.7z`, which is itself duplicated inside the outer ZIP.

## Semantic blocker

The included README says Set 3 contains 4,448 files ending on 2004-04-04. The
actual `3rd_test.rar` header contains 6324 files under
`4th_test` and extends to 2004-04-18. This discrepancy is
preserved as evidence and blocks supervised label/protocol claims until it is
reconciled from an authoritative source. It is not silently renamed or trimmed.

Semantic state: `BLOCKED_FOR_LABEL_PROTOCOL_RECONCILIATION`.

## Recoverability and candidate status

Retaining the outer `4_Bearings.zip` preserves the original wrapper and can
recreate `IMS.7z`, all three RARs, and the README exactly. The proven duplicate
local copies total 1.990 GiB and may be
listed in the reclamation plan, but no deletion occurs before explicit user
authorization. The two CSV ledgers retain all artifact hashes and RAR manifest
fingerprints.
