# Limitations {#sec:limitations}

The following limitations apply to every MRFS result and are restated in every audit report where relevant.

- **Associations, not causes.** Results describe associations between cohort membership and exposure. They do not identify causes or establish unfair treatment.
- **No relevance adjustment.** E1 and E2 are not adjusted for relevance, inventory quality or buyer intent; a cohort can legitimately score below 1 or above 0.5.
- **Scope of the comparison population.** Exclusion before the declared reference stage is not measured. External assessments cover placement among retrieved results only, and sellers never retrieved are unobserved.
- **Cohort measures.** Measures of commercial scale partly reflect past ranking; conclusions can depend on the measure chosen (Section 3.6).
- **Uncertainty.** Intervals assume independent, equally likely ranking events. Clustering by query or day, unequal sampling, and very small counts reduce their accuracy. No correction for multiple comparisons is applied.
- **Precision.** Cohorts holding a small share of the comparison population need many ranking events; the Monitor status in particular may not be confirmable at realistic volumes.
- **Thresholds.** 0.80 is adopted by analogy to the four-fifths rule and is not a validated threshold for ranking exposure; 0.85 and the drift lines are MRFS defaults (Section 2.6).
- **Outcome metrics.** Outcome rates are not adjusted for position.
- **Validation.** The reference implementation has been tested on synthetic data with a known truth. It has not been validated against a live marketplace's internal data (MRFS Validation Report).
