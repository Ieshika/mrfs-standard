# MRFS Validation Addendum: Confidence Intervals and the Small-Sample False-Positive Fix

**Status: A real problem was found, and is now fixed and verified.** This addendum documents a genuine defect the small-sample false-positive test surfaced in the point-estimate-only version of E1/O3 threshold evaluation, the fix (bootstrap confidence intervals plus a new INSUFFICIENT_DATA status), and the evidence that the fix actually closes the gap rather than just reframing it.

## 1. What the small-sample test found

The original false-positive counter-test ran once, at n=250,000 ranking events -- well above Volume 3 Section 2.3's documented data-quality floor of 10,000 events. That single large-N run said nothing about whether the floor itself was safe.

Repeating the same fair (zero built-in disparity, by construction) dataset generation across many independent seeds, at the documented floor and above, found:

| n_events (audit window size) | independent trials | false "Review Required" rate | any false alarm (Monitor or worse) |
|---|---|---|---|
| 10,000 (Volume 3's documented floor) | 50 | 8.0% | 18.0% |
| 25,000 | 40 | 2.5% | 5.0% |
| 50,000 | 30 | 0.0% | 3.3% |
| 100,000 | 20 | 0.0% | 0.0% |
| 250,000 (original test's scale) | 15 | 0.0% | 0.0% |

At exactly the scale Volume 3 called "a minimum ... for statistical reliability," a genuinely fair marketplace was incorrectly flagged Review Required about 1 in 12 times, purely from sampling noise. Volume 3's claim was not true as written.

## 2. Root cause

`exposure_share_at_k()` and `outcome_parity()` returned a single point estimate (e.g. ES@K = 0.78), and `evaluate_thresholds()` compared that number directly against the 0.80/0.85 lines with no accounting for how much that number could plausibly be off by at a given sample size. A point estimate with no uncertainty attached is not distinguishable, by the code, from a supremely confident measurement -- so a noisy small-sample estimate that happened to land at 0.78 was treated exactly the same as a large-sample estimate that reliably lands at 0.78.

**Notably, this was not a new requirement invented for this fix.** Volume 3 Section 5.2 ("Statistical Confidence") already stated: *"All cohort comparisons include 95% confidence intervals via bootstrapping (1,000 resamples) or large-sample approximation."* Volume 2 Section 7 ("Notes") already said confidence intervals were "recommended for E1 and E2." Both statements predate this session's work. `metrics.py` simply never implemented either one -- the standard's own text specified a level of statistical rigor its reference implementation did not actually have, since the project's inception. This fix closes that pre-existing gap between the documented spec and the code, rather than introducing a new idea.

## 3. The fix

`exposure_share_at_k()`, `mean_rank_delta()`, and `outcome_parity()` now each return a 95% confidence interval alongside their point estimate. `evaluate_thresholds()` uses the interval, not just the point estimate, to decide status, and a fourth status -- **INSUFFICIENT_DATA** -- is returned whenever the interval straddles a threshold line (part of it above, part below), meaning the audit genuinely cannot distinguish between the two adjacent statuses at its current sample size. This is the honest result at small sample sizes; forcing a straddling interval into PASS, MONITOR, or REVIEW_REQUIRED is exactly what produced the false positives in Section 1.

**Method, and why:** a nonparametric bootstrap, resampling whole ranking **events** (query instances) with replacement -- not individual top-K rows. A single ranking event contributes multiple top-K rows (e.g. 10 rows for one query), and those rows are not independent of each other; they are all one query's outcome. Resampling at the row level (e.g. a naive binomial/Wilson interval treating each top-K slot as an independent trial) would treat correlated rows as independent evidence and understate the true uncertainty. Resampling whole events preserves that correlation structure, so the interval is not artificially narrow. The same event-level resampling is used for E1, E2, and O1-O3, for methodological consistency.

## 4. Coverage check: is the interval actually correct?

Before trusting a new confidence interval implementation, its coverage needs to be checked empirically, not just assumed from the formula. Because the fair-dataset generator produces exposure that is proportional *by construction* (true ES@K = 1.0 exactly, for any realized seller population, by the symmetry of uniform-random seller selection independent of cohort), a correctly-calibrated 95% interval should contain 1.0 in ~95% of independent trials.

| n_events | trials | Small cohort coverage | Large cohort coverage | Medium cohort coverage |
|---|---|---|---|---|
| 10,000 | 100 | 98.0% | 96.0% | 99.0% |
| 100,000 | 40 | 97.5% | 97.5% | 95.0% |

All observed coverage rates are at or slightly above the 95% target (i.e., slightly conservative -- wider intervals than strictly necessary -- which is the safe direction for this fix, not the dangerous one). This is within normal sampling variation for the trial counts used.

## 5. Confirmation the fix works

Re-running the exact small-sample test from Section 1, now using the CI-aware `evaluate_thresholds()`:

| n_events | trials | PASS | MONITOR | REVIEW_REQUIRED | INSUFFICIENT_DATA | false REVIEW rate |
|---|---|---|---|---|---|---|
| 10,000 | 50 | 2 | 0 | 0 | 48 | **0.0%** |
| 25,000 | 40 | 9 | 0 | 0 | 31 | **0.0%** |
| 50,000 | 30 | 19 | 0 | 0 | 11 | **0.0%** |
| 100,000 | 20 | 13 | 0 | 0 | 7 | **0.0%** |
| 250,000 | 15 | 15 | 0 | 0 | 0 | **0.0%** |

False "Review Required" rate is 0% at every scale, including the original 10,000-event floor. At small sample sizes, the honest INSUFFICIENT_DATA verdict replaces what used to be a coin-flip between a correct PASS and an incorrect REVIEW_REQUIRED. As sample size grows, INSUFFICIENT_DATA gives way to a confident PASS, exactly as it should.

The original false-positive test (n=250,000) and the S1/S2 drift and regression scenario test were both re-run against the new CI-aware code and produce the same substantive conclusions as before (see their respective addenda) -- the fix does not change any previously-reported result, it only removes the small-sample failure mode.

## 6. What this establishes, and what it doesn't

**Establishes:** the confidence-interval methodology is correctly calibrated (Section 4), and it closes the specific, measured false-positive gap at small sample sizes (Section 5), without changing any large-sample conclusion already reported elsewhere in this project.

**Does not establish:**
- That 1,000 (E1/E2) bootstrap resamples is the optimal count for every deployment context -- it is fast enough to run in the tests here and matches Volume 3 Section 5.2's originally-specified count, but was not separately tuned.
- Behavior under real marketplace confounds (seasonal effects, category mix shifts) that synthetic data cannot represent -- same limitation already noted in the other validation addenda.
- Whether INSUFFICIENT_DATA is the right status name/framing for a governance audience unfamiliar with confidence intervals -- Volume 2/3/4/6 now explain it in plain language, but this hasn't been tested on an actual reader.

## 7. Reproducibility

Code: `src/metrics.py` (`exposure_share_at_k`, `mean_rank_delta`, `outcome_parity`, `evaluate_thresholds`, `classify_ci`), `src/generate_fair_dataset.py` (dataset construction, unchanged), `src/run_small_sample_false_positive_test.py` (Sections 1 and 5), `src/run_false_positive_test.py` and `src/run_drift_regression_test.py` (re-validated against the new code). Seeded for reproducibility throughout.
