# BREEZE major-revision audit

Status: closeout verified; author metadata remains blocked. This log records
the revision prompted by the review of
`origin/main@b4e6981` and the 19-page CAS manuscript dated 2026-07-16.

## Immutable starting point

- Review attachment:
  `/Users/jianyang/.codex/attachments/35974ac0-7b38-4d15-a741-1147ccba2378/pasted-text.txt`.
- Repository: local `HEAD` and `origin/main` were both
  `b4e698105842943891b120cf14437ee0f97be0f7` before this round.
- Canonical source SHA-256:
  `45561c0d6b4a1c35d4f3bec3d982405e244eebef18864031ee61d0c793311389`.
- Canonical PDF SHA-256:
  `bc551a6d76e12169c2d6463e9113089414a933b1d8345bb04efac940dccf8472`.
- Baseline PDF: 19 pages, 544.252 by 742.677 pt.
- API boundary: the evidence ledger reconciles 1231/3000 calls; no call is
  authorized by this audit entry.
- Existing untracked result directories and user files shown by `git status`
  are preserved. They are not silently staged, deleted, or reclassified.

## Execution environment decision

The project interpreter `breeze/.venv-breeze/bin/python` is a Python 3.12.13
virtual environment created from the bundled Codex runtime. An initial reading
of the generic task instruction prompted an Anaconda compatibility audit; the
Anaconda base environment failed to import SciPy, while an unrelated existing
Conda environment could import the core stack. No experiment was started with
either Conda environment.

The user then explicitly resolved the ambiguity: all BREEZE work in this round
must continue with `breeze/.venv-breeze/bin/python`. That project interpreter is
therefore the sole authorized Python executable for new and resumed work. No
formal directory may mix it with a Conda runtime.

## E1 environment pause and resume

The TimeGAN/DDPM `formal_pu_v2` service was briefly stopped via its `launchctl`
label while the environment instruction was ambiguous. All append-only outputs
and checkpoints remained in place. At the stop boundary the directory contained:

- 3 completed downstream cells;
- 9 completed class-level cost rows;
- 2880 epoch/stage dynamics rows.

The user's explicit decision to retain `breeze/.venv-breeze/bin/python` makes
the existing v2 runtime consistent with the current instruction. The service
was briefly resubmitted, after which the user replaced the experimental scope
with an immediate Q2 closeout requiring zero new training. The service was
therefore stopped again and will not be resumed in this revision. The pause and
stop do not alter existing rows or checkpoints. Partial results remain
ineligible for paper use and the absence of formal trained-generator baselines
is disclosed once in the limitations.

## Final scope for this round

The controlling instruction is an immediate SCI Q2 / CAS Q2 closeout. This
round permits source/formula fixes, zero-API audits over frozen data, statistical
recalculation, generated tables, claim narrowing, reproducibility documentation,
and submission mechanics. It explicitly excludes TimeGAN/DDPM completion,
independent LLM pools, additional backbones, new cross-specimen splits, and new
API ablations. Those items may appear only as future work or limitations.

## Initial hard-error trace

The one-sided predicate error is in the manuscript, not in the archived v2
implementation. The implementation uses distinct relations:

- train-supported statistics and soft-spectrum coordinates: two-sided bounds;
- PSD-W1 and healthy fault prominence: upper bounds;
- fault envelope prominence and an optional MCSA prominence: lower bounds;
- resonance-band energy: two-sided bounds.

The manuscript instead joins the upper- and lower-bound alternatives with a
logical OR, which is tautological when the lower bound does not exceed the
upper bound. The revision must define disjoint predicate direction sets.

The current `nn_diversity` metric is the mean nearest-neighbour distance among
synthetic samples in a real-reference-scaled log-RMS/PSD-CDF feature space. It
does not compute synthetic-to-real distance. The first selected sample passes
the pool-diversity stage when the admitted set is empty; subsequent samples
must meet the lower distance bound. The current section title and prose that
infer non-copying or distance to the closest real reference are unsupported and
must be removed before a dedicated memorization audit is introduced.

## Revision evidence rule

Each review item will end in exactly one of four states: `fixed` for a verified
source/formula correction, `measured` for a completed evidence artifact,
`qualified` for a narrowed claim, or `blocked` with the missing authority/data
named explicitly. Partial long-run output is never a fifth state and cannot be
converted into a result.

## Final disposition

- H1 fixed: manuscript predicates now match the source implementation; 14
  predicate checks pass.
- H2 measured and qualified: a checkpointed all-pool audit completed for 2200
  synthetic windows. Available pools contain no byte-identical training
  windows, but high cross-correlation prevents an independence claim.
- H3--H4 fixed: complete kurtosis/alignment cells are generated, and Figure 5
  uses the full PU real reference population used by W1.
- H5 measured: the 102-hypothesis global BH sensitivity family preserves all
  102 registered decisions. Statistical inference is scoped to repeated
  few-shot/CNN training around one fixed pool.
- C1--C4 qualified: title, abstract, main claims, boundaries, and Berkeley
  effect sizes are aligned with the evidence ledger.
- M1, M3, M4, and M5 are verified or qualified. M2 remains the sole submission
  blocker because author names, affiliations, ORCIDs, corresponding-author
  details, funding, contributions, and approval metadata require user input.
- The final 21-page PDF has 46 resolved references. Poppler page rendering,
  embedded-font inspection, targeted table/equation inspection, and the full
  contact sheet show no clipping, overlap, blank figure, missing glyph, or
  unresolved reference.
