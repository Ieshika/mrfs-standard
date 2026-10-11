# Purpose and scope

This report states how the MRFS reference implementation (`metrics.py`) behaves on synthetic data with a known truth: whether it reports the correct result on a ranking system without disparity, how reliably it detects a disparity of a given size, how precise its intervals are, and where its limits lie. Section numbers prefixed "Standard" refer to the MRFS Technical Standard. All sample sizes are counted in ranking events.

::: limitation
This report does not show that MRFS is valid for any particular marketplace, and synthetic validation does not establish fairness on any real marketplace. Sections 4 to 8 use one synthetic marketplace with independent ranking events and one disparity mechanism; Section 9 uses a simplified simulation of the same estimator. Real event logs are clustered by query and by day and will be less precise than these tables suggest. Results on live marketplaces are not part of this report.
:::

# Method and reproduction

**The synthetic marketplace.** 2,000 sellers with heavy-tailed listing counts and order counts. Each ranking event draws a candidate set of 40, 80, 150 or 300 listings from the whole catalogue, so sellers with more listings are candidates more often. Each candidate is scored Uniform(0, 1) plus a penalty for its seller's size cohort; lower scores rank higher; the first 50 are ordered and the rest stay in the comparison population without a rank. A penalty of zero for every cohort is a ranking system that ignores cohort. Click probability falls with position. Size cohorts are the MRFS default quartiles of the order count, so Small sellers hold 25% of seller accounts and about 4% of candidate listings.

**Measures.** Status rates are the share of independent replicates (fresh ranking events, same seller catalogue) returning each status. Coverage is the share of 95% intervals containing the true value. True values were computed from at least 100,000 events, except where the truth is known exactly. Rates from 30 to 60 replicates are uncertain by several percentage points.

**Reproduction.** Every table in this report is generated from the results saved in `src/validation_results/`, and every saved result is determined by the seeds in the script that produced it. The results were produced with Python 3.11, numpy 2.4.4 and pandas 3.0.2; the structure check (Section 4) and the worked example (Standard, Appendix A) were also reproduced exactly with numpy 2.2.6 and pandas 2.3.3. numpy does not guarantee identical random streams across all versions, so other versions may give slightly different figures. Section 9 is a partial run (see there).

| Component | File | Command (in `src/`) |
|:----------------------|:----------------------------|:----------------------------|
| Tests with hand-worked expected values | `test_metrics.py` | `python test_metrics.py` |
| Synthetic marketplace | `generate_synthetic_audit.py` | used by the scripts below |
| Validation (Sections 4 to 8) | `run_validation.py` | `python run_validation.py` |
| Focused review (Section 9) | `run_validation_review.py` | `python run_validation_review.py band`, `... drift`, `... check` (partial run; see Section 9) |
| Worked example (Standard, Appendix A) | `generate_sample_audit_report.py` | `python generate_sample_audit_report.py` |

: Files and commands that reproduce this report. Results are saved in `src/validation_results/`.

# Tests of the implementation

`test_metrics.py` contains 21 tests. Each metric is checked against a value worked out by hand on a small example: E1, including the use of listing share rather than seller share, the exclusion of events with nothing to rank, and unordered candidates; E2's event weighting and declared depth; E3's inclusion of sellers without a top position; the status boundaries; size and tenure cohort assignment, including ties and calendar months across a leap day; the audit declaration rules; the determinism of the generator; S1 and S2; and the treatment of zero counts in E1, O3, S1 and S2, including a cohort with no listings in the comparison population. All 21 pass.

# Why E1 was redefined

On a ranking system that ignores cohort (5,000 ranking events):

| Cohort | Share of sellers | Share of listings | Share of top-10 positions | Formula of MRFS 1.x | E1 | 95% interval | Status |
|:----------|------:|------:|------:|------:|------:|:------------|:------------|
| Large | 25.0% | 62.0% | 62.2% | 2.489 | 1.005 | 0.998–1.011 | Pass |
| Medium | 49.9% | 33.8% | 33.6% | 0.673 | 0.993 | 0.981–1.004 | Pass |
| Small | 25.1% | 4.3% | 4.2% | 0.166 | 0.992 | 0.955–1.034 | Pass |

: The earlier per-seller formula and the present E1 on a ranking system without disparity.

The earlier formula compared top positions with each cohort's share of sellers, and reports Small sellers at about one sixth of parity although the ranking system ignores cohort. The present E1 reports each cohort at parity.

# E1: status rates, precision and coverage

| True E1 | Events | Runs | Half-width | Coverage | Pass | Monitor | Review Required | Insufficient Data |
|------:|------:|------:|------:|------:|------:|------:|------:|------:|
| 1.000 | 250 | 200 | 0.172 | 95.0% | 40.0% | 0.0% | 0.0% | 60.0% |
| 1.000 | 500 | 200 | 0.121 | 91.0% | 68.5% | 0.0% | 0.0% | 31.5% |
| 1.000 | 1,000 | 200 | 0.086 | 95.0% | 92.5% | 0.0% | 0.0% | 7.5% |
| 1.000 | 2,500 | 100 | 0.054 | 98.0% | 100.0% | 0.0% | 0.0% | 0.0% |
| 1.000 | 5,000 | 60 | 0.039 | 98.3% | 100.0% | 0.0% | 0.0% | 0.0% |
| 1.000 | 10,000 | 30 | 0.028 | 96.7% | 100.0% | 0.0% | 0.0% | 0.0% |
| RULE | | | | | | | | |
| 0.909 | 250 | 200 | 0.165 | 95.5% | 11.5% | 0.0% | 0.0% | 88.5% |
| 0.909 | 500 | 200 | 0.116 | 95.0% | 13.0% | 0.0% | 0.5% | 86.5% |
| 0.909 | 1,000 | 200 | 0.082 | 93.0% | 24.0% | 0.0% | 0.0% | 76.0% |
| 0.909 | 2,500 | 100 | 0.052 | 96.0% | 53.0% | 0.0% | 0.0% | 47.0% |
| 0.909 | 5,000 | 60 | 0.037 | 98.3% | 83.3% | 0.0% | 0.0% | 16.7% |
| 0.909 | 10,000 | 30 | 0.026 | 93.3% | 100.0% | 0.0% | 0.0% | 0.0% |
| RULE | | | | | | | | |
| 0.806 | 250 | 200 | 0.157 | 91.5% | 1.5% | 0.0% | 4.0% | 94.5% |
| 0.806 | 500 | 200 | 0.111 | 95.0% | 0.0% | 0.0% | 2.5% | 97.5% |
| 0.806 | 1,000 | 200 | 0.078 | 96.5% | 0.0% | 0.0% | 2.0% | 98.0% |
| 0.806 | 2,500 | 100 | 0.050 | 96.0% | 0.0% | 0.0% | 1.0% | 99.0% |
| 0.806 | 5,000 | 60 | 0.035 | 91.7% | 0.0% | 0.0% | 1.7% | 98.3% |
| 0.806 | 10,000 | 30 | 0.025 | 96.7% | 0.0% | 0.0% | 0.0% | 100.0% |
| RULE | | | | | | | | |
| 0.729 | 250 | 200 | 0.151 | 93.0% | 0.0% | 0.0% | 14.5% | 85.5% |
| 0.729 | 500 | 200 | 0.106 | 94.0% | 0.0% | 0.0% | 28.0% | 72.0% |
| 0.729 | 1,000 | 200 | 0.075 | 95.0% | 0.0% | 0.0% | 50.0% | 50.0% |
| 0.729 | 2,500 | 100 | 0.048 | 92.0% | 0.0% | 0.0% | 86.0% | 14.0% |
| 0.729 | 5,000 | 60 | 0.034 | 91.7% | 0.0% | 0.0% | 95.0% | 5.0% |
| 0.729 | 10,000 | 30 | 0.024 | 93.3% | 0.0% | 0.0% | 100.0% | 0.0% |

: Status rates, mean interval half-width and coverage for Small sellers (about 4% of candidate listings).

- On the ranking system without disparity, E1 never returned Review Required or Monitor at any size from 250 to 10,000 ranking events. Below about 1,000 events it often returned Insufficient Data, the correct result when the interval is wide.
- Interval coverage was between 91% and 98.3% across all rows, close to the nominal 95%.
- A cohort at about 0.73 is confirmed as Review Required in half of audits at 1,000 events and in nearly all at 5,000 or more. A cohort at about 0.91 is confirmed as Pass in most audits from 5,000 events.
- A cohort at about 0.81, inside the Monitor band, is almost never confirmed as Monitor at these sizes; Section 9 explains why this is expected.

# S1: drift detection

Twelve weekly windows; S1 for Small sellers in weeks 5 to 12 against the mean of the four preceding weeks. In the second scenario a score penalty is applied to Small sellers from week 9. The penalty was calibrated for a fall to 0.75, but the calibration was imprecise: the observed fall in week 9 averaged about 20%.

| Scenario | Events per week | Runs | Any Monitor or Review Required, weeks 5–12 | Week 9: mean S1 | Week 9: Review Required | Week 9: Insufficient Data |
|:--------------------|------:|------:|------:|------:|------:|------:|
| Stable for 12 weeks | 300 | 100 | 0.0% | −1.5% | 0.0% | 87.0% |
| Stable for 12 weeks | 1,000 | 60 | 0.0% | −1.3% | 0.0% | 53.3% |
| Fall from week 9 | 300 | 100 | 4.0% | −19.6% | 4.0% | 95.0% |
| Fall from week 9 | 1,000 | 60 | 3.3% | −20.6% | 3.3% | 96.7% |

: S1 on a stable system and after a fall.

No stable run produced a Monitor or Review Required result in any week. The fall averaged about −20% in S1, almost exactly on the Review line, and was rarely confirmed in its first week at these volumes. Section 9 shows that detection depends on the number of events per window and on how far the change goes beyond the line. These runs preceded the zero-count safeguard of Section 8, which affects only windows in which a cohort holds no top position; that did not occur at these volumes.

# S2: comparison of ranking versions

| Case | True ratio | Events per version | Runs | Mean S2 | Interval wholly below 1 | Interval covers true ratio | New version E1 Pass |
|:----------------------------|------:|------:|------:|------:|------:|------:|------:|
| Unchanged version (1.00 to 1.00) | 1.000 | 500 | 200 | 1.004 | 4.0% | 94.0% | 72.5% |
| Unchanged version (1.00 to 1.00) | 1.000 | 2,000 | 100 | 1.003 | 1.0% | 97.0% | 100.0% |
| Fall that changes the band (1.00 to 0.84) | 0.836 | 500 | 200 | 0.840 | 47.5% | 96.0% | 1.0% |
| Fall that changes the band (1.00 to 0.84) | 0.836 | 2,000 | 100 | 0.848 | 93.0% | 95.0% | 3.0% |
| Fall within the Pass band (1.23 to 0.91) | 0.743 | 500 | 200 | 0.751 | 93.5% | 96.0% | 14.0% |
| Fall within the Pass band (1.23 to 0.91) | 0.743 | 2,000 | 100 | 0.749 | 100.0% | 91.0% | 57.0% |

: S2 for an unchanged version and two deteriorations.

An unchanged version was reported as a deterioration (interval wholly below 1) in 4.0% of comparisons at 500 events per version and 1.0% at 2,000. A fall from about 1.23 to 0.91, which leaves E1 in the Pass band, was detected in 93.5% and 100% of comparisons: the case S2 exists for, which a status alone would not show.

# O3 and a defect found during validation

| Events | Runs | Click: Pass | Click: Review Required | Conversion: Pass | Conversion: Review Required | Conversion: Insufficient Data |
|------:|------:|------:|------:|------:|------:|------:|
| 500 | 200 | 12.5% | 0.0% | 2.0% | 0.5% | 97.5% |
| 2,000 | 150 | 38.7% | 0.0% | 10.0% | 0.0% | 90.0% |
| 5,000 | 80 | 78.7% | 0.0% | 15.0% | 1.3% | 83.8% |

: O3 on a system with no outcome disparity (true O3 = 1.00).

Conversion rates of about 1.6% leave Small sellers with few conversions, so the conversion ratio is mostly Insufficient Data even at 5,000 events.

**Defect found and corrected.** In an earlier run, when a cohort had no conversion at all in a sample, every bootstrap resample was also zero, the interval collapsed to a single point and the result was a confident Review Required. On this system without disparity that happened in about 5% of samples at 500 events. The implementation now returns no interval and Insufficient Data whenever a numerator count is zero, for E1, O3, S1 and S2, and tests cover each. After the correction the false Review Required rate for the conversion ratio was at most 1.3%.

# Focused review: the Monitor band and weekly drift

Two findings above were reviewed further: the Monitor band was almost never confirmed for a small-share cohort (Section 5), and weekly S1 rarely confirmed a fall in its first week (Section 6). The review used a vectorised re-implementation of the E1 estimator and its event-level bootstrap (400 resamples), needed to reach 100,000 ranking events; its half-width at 1,000 events and a 4.2% listing share was 0.0865, against 0.0861 from `metrics.py` in the same setting. Each candidate belongs to the cohort with probability equal to the cohort's listing share. The run was stopped once the behaviour was established; configurations that did not finish are listed at the end of this section and are not extrapolated.

## The Monitor band needs high precision

A Monitor status requires the whole 95% interval to lie inside a band 0.05 wide, which is possible only once the half-width is below 0.025 and the true value sits far enough from both edges. Pass and Review Required each need the interval to clear only one line.

| Listing share | True E1 | Events | Runs | Half-width | Monitor | Insufficient Data | Pass ruled out | Review Required ruled out |
|------:|------:|------:|------:|------:|------:|------:|------:|------:|
| 4.2% | 0.810 | 1,000 | 150 | 0.079 | 0.0% | 95.3% | 16.7% | 4.0% |
| 4.2% | 0.810 | 5,000 | 100 | 0.035 | 0.0% | 100.0% | 56.0% | 7.0% |
| 4.2% | 0.810 | 10,000 | 80 | 0.025 | 2.5% | 97.5% | 92.5% | 10.0% |
| 4.2% | 0.810 | 25,000 | 60 | 0.016 | 15.0% | 85.0% | 100.0% | 15.0% |
| 4.2% | 0.810 | 50,000 | 40 | 0.011 | 32.5% | 67.5% | 100.0% | 32.5% |
| 4.2% | 0.810 | 100,000 | 25 | 0.008 | 68.0% | 32.0% | 100.0% | 68.0% |
| RULE | | | | | | | | |
| 4.2% | 0.826 | 1,000 | 150 | 0.080 | 0.0% | 100.0% | 6.7% | 9.3% |
| 4.2% | 0.826 | 5,000 | 100 | 0.036 | 0.0% | 100.0% | 23.0% | 35.0% |
| 4.2% | 0.826 | 10,000 | 80 | 0.025 | 1.3% | 98.8% | 52.5% | 45.0% |
| 4.2% | 0.826 | 25,000 | 60 | 0.016 | 65.0% | 35.0% | 73.3% | 91.7% |
| 4.2% | 0.826 | 50,000 | 40 | 0.011 | 100.0% | 0.0% | 100.0% | 100.0% |
| 4.2% | 0.826 | 100,000 | 25 | 0.008 | 100.0% | 0.0% | 100.0% | 100.0% |
| RULE | | | | | | | | |
| 4.2% | 0.839 | 1,000 | 150 | 0.080 | 0.0% | 97.3% | 2.7% | 21.3% |
| 4.2% | 0.839 | 5,000 | 100 | 0.036 | 0.0% | 100.0% | 7.0% | 62.0% |
| 4.2% | 0.839 | 10,000 | 80 | 0.025 | 3.7% | 96.3% | 8.8% | 92.5% |
| 4.2% | 0.839 | 25,000 | 60 | 0.016 | 23.3% | 76.7% | 23.3% | 100.0% |
| 4.2% | 0.839 | 50,000 | 40 | 0.011 | 50.0% | 50.0% | 50.0% | 100.0% |
| 4.2% | 0.839 | 100,000 | 25 | 0.008 | 72.0% | 28.0% | 72.0% | 100.0% |
| RULE | | | | | | | | |
| 25.0% | 0.811 | 1,000 | 150 | 0.030 | 0.0% | 99.3% | 65.3% | 14.7% |
| 25.0% | 0.811 | 5,000 | 100 | 0.014 | 33.0% | 67.0% | 100.0% | 33.0% |
| 25.0% | 0.811 | 10,000 | 80 | 0.010 | 55.0% | 45.0% | 100.0% | 55.0% |
| 25.0% | 0.811 | 25,000 | 60 | 0.006 | 90.0% | 10.0% | 100.0% | 90.0% |
| 25.0% | 0.811 | 50,000 | 40 | 0.004 | 100.0% | 0.0% | 100.0% | 100.0% |

: Confirmation of the Monitor band (partial run).

Results on the wrong side of a line appeared only at 1,000 events, for true values within 0.011 of a line: Review Required for true E1 0.810 in 4.7% of runs at a 4.2% share and 0.7% at a 25% share, and Pass for true E1 0.839 in 2.7%. The volume needed to confirm Monitor depends on the cohort's share of candidate listings and on how close the true value is to an edge of the band. An Insufficient Data result is often informative: at 10,000 events with true E1 0.810, the interval ruled out Pass in 92.5% of runs.

## Drift detection depends on events per window and on the size of the change

| Listing share | True change | Events per window | Runs | S1: Monitor | S1: Review Required | E1 of the window: Review Required |
|------:|------:|------:|------:|------:|------:|------:|
| 4.2% | −25% | 300 | 150 | 0.0% | 12.7% | 12.0% |
| 4.2% | −25% | 1,000 | 150 | 0.0% | 15.3% | 19.3% |
| 4.2% | −25% | 3,000 | 100 | 0.0% | 59.0% | 63.0% |
| 4.2% | −25% | 10,000 | 60 | 0.0% | 93.3% | 100.0% |
| 4.2% | −25% | 30,000 | 30 | 0.0% | 100.0% | 100.0% |
| RULE | | | | | | |
| 4.2% | −15% | 300 | 150 | 0.0% | 0.7% | 1.3% |
| 4.2% | −15% | 1,000 | 150 | 0.0% | 0.0% | 0.0% |
| 4.2% | −15% | 3,000 | 100 | 1.0% | 0.0% | 0.0% |
| 4.2% | −15% | 10,000 | 60 | 80.0% | 0.0% | 0.0% |
| 4.2% | −15% | 30,000 | 30 | 100.0% | 0.0% | 0.0% |
| RULE | | | | | | |
| 25.0% | −25% | 300 | 150 | 0.0% | 30.7% | 38.0% |
| 25.0% | −25% | 1,000 | 150 | 0.0% | 82.7% | 86.0% |
| 25.0% | −25% | 3,000 | 100 | 0.0% | 100.0% | 100.0% |
| 25.0% | −25% | 10,000 | 60 | 0.0% | 100.0% | 100.0% |
| 25.0% | −25% | 30,000 | 30 | 0.0% | 100.0% | 100.0% |
| RULE | | | | | | |
| 25.0% | −15% | 300 | 150 | 0.0% | 0.0% | 0.0% |
| 25.0% | −15% | 1,000 | 150 | 66.7% | 0.0% | 0.0% |
| 25.0% | −15% | 3,000 | 100 | 99.0% | 0.0% | 0.0% |
| 25.0% | −15% | 10,000 | 60 | 100.0% | 0.0% | 0.0% |

: Detection of a fall by S1, and by the E1 status of the same window (partial run).

Detection rises steeply with events per window. For a 4.2%-share cohort a 25% fall needs roughly 3,000 to 10,000 events per window to be confirmed reliably; for a 25%-share cohort, about 1,000 to 3,000. A longer window helps only because it holds more events. The E1 status of the monitoring window detects a large fall about as well as S1; S1 registers moderate falls that leave E1 near a line. Wrong-side S1 results appeared only at 300 events for the 15% fall: Review Required in 0.7% and Pass in 1.3% of runs.

## Guidance

Neither finding is a defect in the estimator or the interval; both are expected consequences of deciding status from a 95% interval with narrow bands. The methodology and thresholds are unchanged. The resulting guidance is in Standard Sections 2.6, 3.5 and 3.7: report what an Insufficient Data interval rules out; plan precision from each cohort's share of listings; choose monitoring windows by expected events, in whole weeks; use the window's E1 for the level and S1 for the change.

**Partial run.** The review was stopped once the behaviour was established, and the completed rows were saved from the run's output to `review_band_and_drift_partial.json`; the comparison with `metrics.py` is saved in `review_check.json`. Not run: in the Monitor review, the 25%-share cohort at true E1 about 0.81 at 100,000 events and at the two higher true values at every size; in the drift review, the 25%-share cohort at 30,000 events with a 15% fall. Each row uses its own seed, so `python run_validation_review.py band` (or `drift`) regenerates every completed row exactly, but it also runs the configurations listed above, which take many hours, and writes `review_band.json` (or `review_drift.json`) rather than the partial file. The completed rows have not been regenerated since the original run.

# Corrections to the validation published with MRFS 1.0 and 1.1

- **Rows counted as ranking events.** The synthetic generators of 1.0 and 1.1 created 20 rows per ranking event but reported row counts as event counts. Results presented at 10,000 to 250,000 ranking events were obtained at 500 to 12,500. The statement that a 10,000-event audit produced a false Review Required 8% of the time was measured at 500 ranking events. This report replaces those results.
- **Drift-interval figures withdrawn.** The figures of the 1.1 addendum on intervals for S1, including a 92.5% false-alert rate, cannot be reproduced because no script for them exists. They are withdrawn; Section 6 replaces them.
- **Sample audit report replaced.** The figures of the earlier sample report could not be traced to any data or code and contained internal contradictions. The worked example is now generated by the reference implementation (Standard, Appendix A).
- **Exposure metric redefined.** See Section 4 and Standard, Appendix B.

# Limitations

- One synthetic marketplace, one disparity mechanism (a score penalty) and independent ranking events.
- Precision depends on each cohort's share of comparison-population listings; these tables describe a cohort with about 4% of listings and are not general sample-size requirements.
- Unequal-probability sampling of events is not supported by the reference implementation.
- No correction for multiple comparisons is applied (Standard, Section 2.7).
- Calibrated true values other than 1.00 are close to, not exactly at, their targets; the tables report the true values used.
- The reference implementation has not been run on a live marketplace's internal data.
