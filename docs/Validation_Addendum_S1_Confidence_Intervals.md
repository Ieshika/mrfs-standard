# MRFS Validation Addendum: S1 Confidence Intervals and the Floor-Scale Detection Tradeoff

**Status: A real problem was found and is now fixed and verified at medium-and-above weekly monitoring volume.** At floor-scale weekly volume specifically, the fix trades detection power for eliminating a severe false-alert rate — a real, quantified tradeoff that this addendum documents but does not resolve. It requires an explicit governance sign-off under Volume 4 (see Section 8) before floor-scale deployments should be considered fully validated.

## 1. What the investigation found

S1 (ExposureShare@K Drift) compares each week's ExposureShare@K for a cohort against the trailing 4-week moving average, and classifies the result Pass / Monitor / Review Required based on how far it has declined. Unlike E1, E2, and O1-O3 (see `Validation_Addendum_Confidence_Intervals.md`), S1 had **no confidence interval anywhere in its calculation** — a pure point-estimate comparison of two noisy quantities.

Testing S1 on a genuinely stable, undrifted synthetic marketplace (true ExposureShare@K ratio = 1.0 for every cohort, by construction) across three weekly-volume scales, 3 cohorts × 8 evaluated weeks per trial:

| Scale | events/week | trials | checks/trial | per-check false-alert rate | family-wise false-alert rate (≥1 per trial) |
|---|---|---|---|---|---|
| floor | ~42 | 40 | 24 | **10.7%** (103/960) | **92.5%** (37/40) |
| medium | ~250 | 40 | 24 | 0.10% (1/960) | 2.5% (1/40) |
| large | ~1,250 | 30 | 24 | 0.0% (0/720) | 0.0% (0/30) |

At realistic low-weekly-volume monitoring conditions, a genuinely fair, undrifted marketplace triggered a false Monitor-or-worse alert on **92.5% of monitoring cycles**. The problem is concentrated at floor-scale volume and essentially disappears by medium volume.

This is not primarily a multiple-comparisons problem. A single S1 check at floor scale already carried a 10.7% per-check error rate, more than double any nominal 5% a multiplicity correction would assume as its starting point — the 92.5% family-wise rate is the compounding of an already-miscalibrated individual test across cohorts and weeks, not principally a "many independent 5%-level tests" story. A companion investigation into E1/O3's own multiplicity exposure (using the same methodology) found the existing D19 confidence-interval fix already keeps those signals near-nominal without any correction; the S1 problem documented here is a different, more fundamental gap — total absence of uncertainty quantification, not test volume.

Detection power on a real, sizeable injected regression (Configuration used in this section only: a 0.35 rank-position penalty against a cohort, injected at week 8 of a 16-week series — the original Phase 2 scenario generator, distinct from the target-ratio-decline configuration used in Sections 5-6 below) was unaffected by this defect: the uncorrected point-estimate classifier caught it 100% of the time within 2 weeks, at every scale tested. The false-alert problem and the detection-power headroom were independent findings.

## 2. The fix

`es_at_k_drift_ci()` adds a 95% bootstrap confidence interval on the drift statistic itself, using the same event-level resampling convention D19 established for E1/E2/O1-O3: whole ranking events are resampled with replacement (not individual top-K rows, which are correlated within an event and would understate variance if resampled independently). For each of `B=1000` replicates, the current week's events and each of the four trailing baseline weeks' events are resampled independently (they are disjoint calendar weeks with no shared events, so independent resampling per week is the standard stratified-bootstrap construction), each week's point estimate is recomputed on the resampled data with the unchanged formula, the four baseline replicates are averaged, and the drift replicate is computed with the unchanged `es_at_k_drift` formula. A percentile CI is taken across the resulting replicates.

**The window and rate-of-change formula are unchanged.** The 1-week-current / 4-week-baseline window (Volume 3 §6.1, Volume 5 §8; **Configuration A** below) and S1's role as a rate-of-change detector, distinct from ExposureShare@K's own sustained-disparity role, are both preserved exactly. Two wider window configurations were investigated at floor scale as an alternative to accepting any detection-power cost, using the same CI-based classifier and the same target-ratio-decline injected regression (true drift ≈ -35%, detailed in Section 5) throughout: **Configuration B** (2-week current / 6-week baseline) and **Configuration C** (4-week current / 8-week baseline). All three configurations held the false-alert rate at 0.0% (25 trials, 24-week null series, floor scale). Detection of the injected regression, confirmed at n=50 trials across two independent scenario parameterizations (series length and drift-injection timing), was: Configuration A 60-78%, Configuration B 80-86%, Configuration C 96-98%. Only Configuration C closed the detection gap; Configuration B's improvement over A was real but partial, not a resolution. Configuration C was rejected, not merely deferred, despite closing the gap most fully — a 4-week rolling current window conflicts with Volume 4 §C5's post-mitigation monitoring clause (which specifies exactly 4 consecutive weekly readings after a deployment — a wider window would not produce a single clean post-mitigation-only reading within that span), erodes the "lightweight weekly tripwire" role Volume 3 §5.4 assigns to this signal ahead of the monthly full audit, and would require revising the window itself in Volumes 3 and 5 rather than only adding uncertainty quantification around an unchanged comparison. The window was not the defect; the defect is narrowly that S1 had no uncertainty quantification.

**Classification uses a new, small function, not the existing `classify_ci()`.** `classify_ci()`'s inclusive/exclusive boundary convention (good side inclusive, bad side exclusive) does not reproduce the original point-estimate classifier's convention (bad side inclusive) exactly at the -10%/-20% threshold values. `classify_s1_ci(lower, upper, monitor_line=-10, review_line=-20)` is written to match the original semantics exactly instead:

```
lower > monitor_line                          -> PASS
upper <= review_line                          -> REVIEW_REQUIRED
lower > review_line and upper <= monitor_line -> MONITOR
otherwise (interval straddles a threshold)    -> INSUFFICIENT_DATA
```

Verified by construction: collapsing the interval to a point (`lower = upper = drift_pct`) reduces every branch to the original single-threshold comparison, at every value including exactly -10% and exactly -20%.

`_bootstrap_percentile_ci()`'s replicate filter was widened from NaN-only to `np.isfinite()`. E1/E2/O1-O3's bootstraps divide by a fixed, non-resampled population constant and can never produce `Inf`, so this is a no-op for them. S1's drift replicate divides by a *resampled* baseline, which can independently land at exactly zero for a given replicate even when the real baseline isn't zero — producing `Inf`, not `NaN` — which the original filter would have let through uncaught for small or niche cohorts.

## 3. Coverage check: is the interval actually correct?

An initial n=30 trial run of the null (true drift = 0%) case showed 86.7% coverage, below the 95% nominal target — investigated rather than accepted at face value. Re-run at n=80: 95.0% (true drift = 0%) and 96.25% (true drift = -30%), both consistent with correct calibration; the n=30 result was sampling noise (expected standard error at that trial count is ~5.5%, so an 8.3-point gap was roughly 1.5 SE, not a real miscalibration).

## 4. Confirmation the fix eliminates the false-alert problem

Re-running the false-alert check from Section 1 against the CI-based classifier, floor scale (~42 events/week), 30 trials, 240 checks:

| Version | per-check false-alert rate | family-wise false-alert rate | INSUFFICIENT_DATA rate |
|---|---|---|---|
| OLD (point estimate) | 12.1% | 73.3% | n/a (status did not exist) |
| NEW (CI-based) | **0.0%** | **0.0%** | 83.3% |

(This is a separately-run, smaller-scope re-check than Section 1's pilot — 8 checks per trial here versus Section 1's 24 (3 cohorts × 8 weeks); the investigation log records the trial and total-check counts shown but does not further break down this re-check's per-trial composition. Its rates, not its raw check totals, are what corroborate Section 1's finding: 73.3%/12.1% here vs. 92.5%/10.7% there — the same order-of-magnitude problem, confirming it is not an artifact of trial count or check design.)

At medium scale (~250 events/week), OLD was already 0.0%/0.0%; NEW is also 0.0%/0.0%, with INSUFFICIENT_DATA dropping to 20%. The false-alert problem and its fix are both concentrated at floor-scale volume specifically.

## 5. The floor-scale tradeoff: detection power

Detection power and latency, OLD vs. NEW, on a real, large injected decline (Configuration used in this section and Section 6: a direct exposure-ratio decline, target ratio 1.0 → 0.65 starting mid-series, i.e. true drift ≈ -35% — a separate scenario generator from Section 1's rank-position-penalty configuration, though of comparable magnitude):

| Scale | Version | detected at all | mean latency (weeks, among detections) |
|---|---|---|---|
| floor (~42/wk, 25 trials) | OLD | 100% | 0.0 |
| floor (~42/wk, 25 trials) | NEW | **68%** | 0.35 |
| medium (~250/wk, 25 trials) | OLD | 100% | 0.0 |
| medium (~250/wk, 25 trials) | NEW | 100% | 0.0 |

**This is the one genuine, material cost this fix introduces, and it is stated here plainly: at floor-scale volume, the CI-based fix misses a strong, real 35%-magnitude regression in roughly 32% of trials across the entire post-change monitoring window** — not merely a detection delay, but no flag raised at all in about a third of cases. At floor-scale volume the bootstrap CI on the drift statistic is frequently wide enough to straddle the -10% line even when the point estimate itself is comfortably past it, producing an honest INSUFFICIENT_DATA rather than a confident MONITOR/REVIEW_REQUIRED. By medium scale, this cost disappears entirely — detection and latency both match the pre-fix behavior exactly.

Configuration A's (the current, unchanged window's) floor-scale detection rate was checked four separate times in this investigation and was not stable across those checks: 68% (25 trials, 16-week series, drift injected at week 8 — the table above), 60% (a same-parameters re-check using this pilot's pooled-window implementation; trial count not separately logged in the investigation record), 80% (20 trials, a longer 32-week series with drift injected at week 16), and — in a dedicated n=50 confirmatory run designed specifically to settle whether these differences were real or noise — 78% (32-week series, drift at week 16) and 60% (16-week series, drift at week 8) across those same two scenario designs. The 18-point gap between the two n=50 results is too large to be Monte Carlo noise at that trial count, confirming Configuration A's floor-scale detection power is genuinely sensitive to the scenario's series length and drift timing, not just noisy. 60-80% is the honestly-measured range across all four checks; the two n=50 results (60%, 78%) are the most reliable individual estimates within it, and are the same Configuration-A numbers cited in Section 2's window-comparison paragraph.

## 6. Sustained-weeks escalation: a second floor-scale gap

`sustained_weeks` increments on any week classified MONITOR or REVIEW_REQUIRED and resets on either PASS or INSUFFICIENT_DATA — the conservative reading of "sustained" as an unbroken run of *confirmed* bad weeks, not merely point-estimate-bad weeks, chosen because resetting only on PASS would let scattered, non-consecutive ambiguous weeks quietly accumulate toward a REVIEW_REQUIRED verdict that the standard's "3 consecutive weeks" language does not intend.

A dedicated check, isolated from the aggregate detection-rate measurement above, decomposed *how* REVIEW_REQUIRED verdicts are actually reached at floor scale (40 trials, the same target-ratio-decline injected regression used in Section 5 above — 12 checks per trial; the investigation log records this trial/check total but does not further decompose the per-trial composition beyond noting it reuses that same scenario design): of 26 REVIEW_REQUIRED verdicts observed across 480 checks, **all 26 (100%) were reached via a direct single-week CI breach** (the interval's upper bound confidently at or below -20%); **zero were reached via the 3-consecutive-week sustained path.** Because INSUFFICIENT_DATA occurs 83% of the time at floor scale (Section 4), an unbroken 3-week MONITOR-or-worse streak essentially never survives long enough to complete under the reset-on-INSUFFICIENT_DATA rule.

**Practical implication: at floor-scale weekly volume, Volume 2/3's "≥20% or sustained > 2 weeks" threshold is, in effect, just "≥20%."** The sustained clause contributes no additional detection at this scale under this design. This is now a measured, documented characteristic, not an assumption, and is a second respect (alongside Section 5's headline detection-rate cost) in which the low-volume version of this fix is narrower than the standard's text describes.

## 7. Volume 3 §6.2: a pre-existing spec/code gap this fix closes

Volume 3 §6.2 states, immediately after the alert-thresholds table (which includes the ExposureShare@K-change / S1 row): *"Each signal in the table above is evaluated using its 95% confidence interval, not its point estimate alone."* This statement was **not accurate for S1 prior to this fix** — the D19 confidence-interval fix was scoped to `exposure_share_at_k()`, `mean_rank_delta()`, and `outcome_parity()` only; `es_at_k_drift()` was explicitly documented as unchanged and point-estimate-only. This is the same category of gap the D19 addendum itself documented for Volume 3 §5.2 and Volume 2 §7 (text specifying a level of rigor the implementation did not yet have) — not a new inaccuracy introduced now, but a standing one this fix closes. No change to Volume 3 §6.2's text is needed as a result of this fix; the sentence becomes accurate now that S1 has a confidence interval. This note records that it was not accurate before.

## 8. Governance decision required — not resolved by this document

**The following is quantified here but not decided here, and should not be read as accepted by anything in this addendum.**

At floor-scale weekly volume (~42 events/week), the validated design detects roughly 60-80% of a large, genuinely sustained regression (down from ~100% under the prior uncorrected method), in exchange for eliminating a ~73-92%-family-wise false-alert rate on a genuinely stable system. Additionally, per Section 6, essentially all of that detection at floor scale comes from the single-week direct threshold breach — the standard's "or sustained > 2 weeks" alternative path is not meaningfully reachable at this volume under this design.

This tradeoff requires an explicit, named sign-off from whoever holds the authority Volume 4 assigns to this class of decision — the Fairness Lead for routine operation (§A5), or the Board-level escalation path (§A7), given that this affects what "Mitigation Required" detection coverage actually means at low weekly volume. For the specific synthetic configurations tested — the scales, cohort designs, and injected-regression scenarios described in Sections 1, 3, 4, 5, and 6 — the statistics are settled: coverage-validated (Section 3), false-alert-rate-validated (Section 4), and path-decomposed (Section 6). That conclusion is bounded to those tested configurations; it has not been checked against real marketplace data, other cohort definitions, other regression magnitudes or shapes, or short-lived (1-2 week) declines (see Section 9), and should not be read as a general claim beyond them. What is not settled, even within the tested configurations, is whether a roughly 20-40% miss rate on real regressions at low weekly volume, with the standard's own sustained-decline safeguard non-functional at that volume, is an acceptable operating characteristic, or whether floor-scale deployments should instead be flagged as having insufficient volume for reliable S1 monitoring, or handled some other way. This is a policy decision, not a statistical one, and is recorded as open pending that sign-off.

## 9. What this establishes, and what it doesn't

**Establishes:** the confidence-interval methodology is correctly calibrated (Section 3); it eliminates the measured false-alert problem at medium-and-above weekly volume with zero cost to detection power or latency (Section 4); at floor-scale volume it trades a quantified amount of detection power for eliminating a quantified false-alert rate (Section 5), and a second floor-scale characteristic — the sustained-weeks path being effectively non-functional at that volume — is now measured rather than assumed (Section 6).

**Does not establish:**
- Whether the floor-scale tradeoff in Sections 5-6 is an acceptable operating characteristic — see Section 8.
- Whether a short-lived (1-2 week) decline, as opposed to the sustained regression tested here, is detected reliably by any window size — this was identified as a real, plausible gap during the window-widening investigation (Section 2) and has not been tested.
- Whether any multiple-comparisons correction is warranted on top of this fix. Per the same discipline applied to E1/O3 (see `Validation_Addendum_Confidence_Intervals.md`), that question should be re-measured on this fixed version rather than assumed, and remains out of scope for this addendum.
- Behavior under real marketplace confounds that synthetic data cannot represent — the same limitation already noted in the other validation addenda.

## 10. Reproducibility

Code: `src/metrics.py` (`es_at_k_drift_ci`, `classify_s1_ci`, `_weekly_topk_arrays`, `_week_point_estimate`, `_week_bootstrap_replicates`, `_bootstrap_percentile_ci`), `src/run_drift_regression_test.py` (re-validated end-to-end against the new code: both the true-positive `drift_scenario` and true-negative `stable_scenario` cases still pass). The original point-estimate `es_at_k_drift()` is unchanged and still available for callers that only need the point estimate. Seeded for reproducibility throughout.
