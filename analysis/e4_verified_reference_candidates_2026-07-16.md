# E4 verified citation candidates

These are the source-verified records used for the CAS revision's
few-shot/meta-learning and leakage-protocol paragraphs. They have been merged
into `references.bib` and cited in `main_cas.tex`; this log preserves the
source-level audit and the intentionally limited wording.

## Few-shot and meta-learning fault diagnosis

- Li, C., Li, S., Zhang, A., He, Q., Liao, Z., and Hu, J. *Meta-learning for
  few-shot bearing fault diagnosis under complex working conditions*.
  Neurocomputing 439 (2021), 197--211.
  DOI: `10.1016/j.neucom.2021.01.099`.
  Publisher record: <https://www.sciencedirect.com/science/article/abs/pii/S0925231221001818>.
- Wu, J., Zhao, Z., Sun, C., Yan, R., and Chen, X. *Few-shot transfer learning
  for intelligent fault diagnosis of machine*. Measurement 166 (2020), 108202.
  DOI: `10.1016/j.measurement.2020.108202`.
  Publisher record: <https://www.sciencedirect.com/science/article/abs/pii/S0263224120307405>.
- Su, H., Xiang, L., Hu, A., Xu, Y., and Yang, X. *A novel method based on
  meta-learning for bearing fault diagnosis with small sample learning under
  different working conditions*. Mechanical Systems and Signal Processing 169
  (2022), 108765. DOI: `10.1016/j.ymssp.2021.108765`.
- Feng, Y., Chen, J., Xie, J., Zhang, T., Lv, H., and Pan, T. *Meta-learning as
  a promising approach for few-shot cross-domain fault diagnosis: Algorithms,
  applications, and prospects*. Knowledge-Based Systems 235 (2022), 107646.
  DOI: `10.1016/j.knosys.2021.107646`.
  Publisher record: <https://www.sciencedirect.com/science/article/abs/pii/S0950705121009084>.

## Leakage and grouping protocol

- Wheat, L., Mohrenschildt, M. V., Habibi, S., and Al-Ani, D. *Impact of Data
  Leakage in Vibration Signals Used for Bearing Fault Diagnosis*. IEEE Access
  12 (2024), 169879--169895. DOI: `10.1109/ACCESS.2024.3497716`.
  The article explicitly compares three splitting methods and reports an
  accuracy drop exceeding 40 percentage points in its datasets.
  Publisher-indexed record: <https://doi.org/10.1109/ACCESS.2024.3497716>.
- Kapoor, S. and Narayanan, A. *Leakage and the reproducibility crisis in
  machine-learning-based science*. Patterns 4(9) (2023), 100804.
  DOI: `10.1016/j.patter.2023.100804`.
  Publisher record: <https://doi.org/10.1016/j.patter.2023.100804>.

## Intended use

Use the four few-shot sources to frame BREEZE as augmentation under the stated
split, rather than as a claim to replace transfer or meta-learning.  Cite
Wheat et al. for the bearing-specific motivation for acquisition-unit grouping
and Kapoor--Narayanan for the general methodological framing.  Do not use them
to claim that every window-level split is leaky; the manuscript should describe
its own manifest and overlap audit precisely.
