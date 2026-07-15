# Cover Letter Draft

Dear Editor,

We submit the manuscript ``Training-free, physics-verified LLM recipe
generation for industrial machinery condition monitoring'' for consideration
in Advanced Engineering Informatics.

The paper studies a training-free alternative to fitting a new signal generator
for each machine. An LLM proposes a structured signal recipe, a deterministic
renderer produces the waveform, and train-calibrated physical gates admit or
reject the candidate. The verifier creates auditable admission records; it does
not repair waveforms or claim formal physical correctness.

The evidence is reported with its protocol boundaries. On the Paderborn
University bearing benchmark, a frozen 20-seed file-split experiment shows
LLM recipes outperforming rule and random open-loop recipes for Accuracy and
Macro-F1 at 5, 10, and 25 real windows per class under registered Holm tests.
On CWRU, 90/90 registered LLM-comparator tests across within-load and four
leave-one-load-out folds pass Holm correction (40 seeds). The Berkeley milling
binary experiment is explicitly partial: 15/18 comparisons pass; all
non-structured-baseline comparisons pass, while the LLM advantage over the
rule baseline is limited to lower-shot settings. We additionally report six
failed PU cross-condition attempts and two stopped milling lines, including a
metadata-confounding boundary in UMich.

We believe the manuscript fits the journal because it combines industrial AI,
condition monitoring, deterministic signal rendering, and auditable synthetic
data admission. Rather than presenting a universal generator claim, it makes
the supported few-shot results and their limits equally visible.

The manuscript is original and is not under consideration elsewhere. All
authors have approved the submission. Author names, affiliations, funding, and
conflict-of-interest statements must be finalized by the authors before
submission.

Sincerely,

The authors
