# Cover Letter Draft

Dear Editor,

We submit the manuscript “BREEZE: Training-Free and Auditable LLM Recipe
Augmentation with Physics-Guided Admission” for consideration
in Advanced Engineering Informatics.

The paper studies a training-free augmentation alternative to fitting a new
signal generator for each machine. Using supplied kinematics, training-fold
statistics, and exemplar descriptions, an LLM selects a structured signal
recipe; a deterministic renderer produces the waveform; and train-calibrated
physical gates admit or reject the candidate. The verifier creates auditable
admission records, while the downstream diagnostic classifier remains trained
in the usual way.

The evidence is reported with its protocol boundaries. On the Paderborn
University bearing benchmark, a frozen 20-seed file-split experiment shows
LLM recipes outperforming rule and random open-loop recipes for Accuracy and
Macro-F1 at 5, 10, and 25 real windows per class under registered Holm tests.
On CWRU, paired gains over rule, noise augmentation, and real-only hold within
load0 and from source load0 to held-out loads 1--3 under family-wise Holm
correction (40 seeds); the archived held-out-load0 fold is excluded because it
reuses a load0-derived synthetic pool. In Berkeley milling, LLM recipes beat
both non-structured baselines at every shot, whereas the statistically
significant gain over rule is only 0.2--0.5 percentage points and confined to
lower-shot cells. A global Benjamini--Hochberg sensitivity analysis preserves
every registered decision. We additionally report six failed PU
cross-condition attempts and two stopped milling lines, including a
metadata-confounding boundary in UMich.

We believe the manuscript fits the journal because it combines industrial AI,
condition monitoring, deterministic signal rendering, and auditable synthetic
data admission. The claim is deliberately limited to the three frozen
few-shot protocols and one fixed pool per method.

The manuscript is original and is not under consideration elsewhere. Author
names, affiliations, funding, ORCID records, and approval statements remain
to be finalized by the authors before submission.

Sincerely,

The authors
