# Changes from MRFS 1.0 and 1.1 {#app:changes}

| Area | MRFS 1.0 and 1.1 | This version |
|:----------------------|:----------------------------------------------|:----------------------------------------------------|
| E1 benchmark | Cohort's share of top-$K$ positions ÷ cohort's share of sellers | Top-$K$ positions held ÷ positions expected from the cohort's share of listings in a declared comparison population, event by event |
| Comparison population | Not defined | Declared: candidate set at a named stage, or results retrieved to depth $N$ |
| Statuses | Assigned for every assessment | Assigned only for candidate-set populations, scoped to the declared stage |
| E2 | Mean rank and its difference between cohorts, with position thresholds | Event-weighted normalised mean rank; no status |
| E3 | Gini over sellers with at least one top-$K$ position; contextual flag | Gini including sellers with no top-$K$ position; no status |
| O1 to O3 | Parity ratio and disparate-impact ratio reported as two metrics | O1 and O2 rates; one O3 ratio per outcome |
| S1 | Change against a trailing average, with an undefined "sustained" rule | Change against the mean of the preceding baseline windows; "sustained" rule withdrawn |
| S2 | Difference of averages, no interval | Ratio between versions with an interval; no status |
| Sample sizes | Fixed minimum event counts | None; sufficiency decided by the interval |
| Data quality | Fixed coverage and completeness thresholds | Audit-specific criteria declared in advance; rates reported |
| Thresholds | 0.85 and 0.80 attributed to the four-fifths rule | 0.80 an MRFS choice by analogy; 0.85 and drift lines MRFS defaults |
| Governance | Release gates that passed on "no degradation"; alert colours | Documented investigation and decision; optional, declared release-gate integration; MRFS does not approve releases |
| Documents | Six volumes | One technical standard, an overview and a validation report |

: Principal changes from MRFS 1.0 and 1.1.

**Comparability.** E1 values from MRFS 1.0 and 1.1 are not comparable with E1 in this version. The earlier formula corresponds to a per-seller exposure index, which is not part of this standard. On a synthetic ranking system that ignores cohort, the earlier formula reports Small sellers, who hold a quarter of seller accounts but about 4% of listings, at about one sixth of parity, while the present E1 reports every cohort at parity (MRFS Validation Report, Section 4).

**Validation.** The synthetic validation published with MRFS 1.0 and 1.1 counted log rows as ranking events and is replaced by the MRFS Validation Report, which also lists the earlier figures that were withdrawn.

# Reference implementation {#app:implementation}

The reference implementation is `src/metrics.py`, published under the MIT License in the MRFS repository. It is tested against hand-worked examples in `src/test_metrics.py`.

| Standard | Implementation |
|:----------------------------------------|:----------------------------------------------|
| E1 (Section 2.2.1) | `exposure_ratio` |
| E2 (Section 2.2.2) | `mean_rank_position` |
| E3 (Section 2.2.3) | `exposure_concentration` |
| O1 to O3 (Section 2.3) | `outcome_parity` |
| S1 (Section 2.4.1) | `exposure_drift` |
| S2 (Section 2.4.2) | `model_regression` |
| Status rules (Section 2.6) | `classify_ci`, `classify_drift_ci`, `evaluate_statuses` |
| Audit declaration (Sections 3.2 and 5.4) | `AuditDeclaration` |
| Default size cohorts (Section 3.4) | `assign_size_cohorts` |
| Default tenure cohorts (Section 3.4) | `assign_tenure_cohorts` |

: Mapping of this standard to the reference implementation.

Q1 to Q3 and the optional diagnostics are not implemented. The implementation does not support unequal-probability sampling weights.

**Reproducing the published results.**

| Result | Command (in `src/`) |
|:----------------------------------------|:----------------------------------------------|
| Tests | `python test_metrics.py` |
| Synthetic validation | `python run_validation.py` |
| Worked example (Appendix A) | `python generate_sample_audit_report.py` |

: Commands that reproduce the published results.

# Design choices and their sources {#app:choices}

This appendix separates what MRFS takes from external sources from what it chooses itself.

| Element | Source | Nature |
|:------------------------------|:--------------------|:----------------------------------------------------------------|
| Exposure in rankings as the quantity of interest | [8] | Externally established framing; MRFS uses simpler, count-based measures |
| Group representation in ranked lists | [7], [2] | Externally established measures; not used directly |
| Effect of rank position on what consumers examine | [10] | External evidence from one field experiment on a travel platform |
| E1 benchmark: share of listings in a declared comparison population | — | MRFS design choice |
| Review line 0.80 | [4], [3], [11] | MRFS normative choice by analogy to the four-fifths rule; not validated for ranking exposure |
| Monitor line 0.85 | — | MRFS default, changeable if pre-specified |
| Drift lines −10% and −20% | — | MRFS defaults, changeable if pre-specified |
| $K = 10$ | — | MRFS default |
| Quartile size cohorts; completed orders; 12-month tenure | — | MRFS defaults, changeable if pre-specified |
| 95% percentile bootstrap resampling ranking events | — | Standard statistical method; the resampling unit is an MRFS choice |
| No fixed minimum event count; no universal data-quality thresholds | — | MRFS design choice |
| Recommended cadence | — | MRFS recommendation, not derived |
| NDCG | [5] | External definition |
| Charter structure | [9] | Informed by the AI RMF functions; the mapping is the author's |

: Design choices and their sources.
