# Cache and build-artifact audit — 2026-07-17

## Verdict

**PASS (classification only).** The audit separates convention-defined caches
from environments, bibliography evidence, active workspace artifacts, and
private render outputs. It identified 18 repository cache/build
entries totaling 0.003 GiB
as rebuildable candidates. No file was deleted.

## Non-cache preservation boundaries

- Python environment: 1 entry, 0.815 GiB. It remains preserved until a clean install from the pinned specification passes the complete test suite.
- `.bbl` bibliography evidence: 1 file(s). It remains preserved until the exact publication toolchain reproduces it.
- `/private/tmp` BREEZE artifacts: 22 top-level entries, 0.038 GiB. A temporary path alone is not treated as reconstruction proof.
- Workspace `tmp/` is marked as user-dirty visual-QA material and is not a cache candidate.

## Reclamation boundary

Only rows marked `REBUILDABLE_PENDING_AUTHORIZATION` can enter the low-risk
cache batch. The reclamation plan must retain their generating command and must
request explicit authorization before removal. Virtual environments, `.bbl`,
workspace `tmp/`, and unmapped render artifacts are excluded from that batch.
