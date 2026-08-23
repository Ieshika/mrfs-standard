# MRFS Validation Addendum: S1/S2 Drift and Regression Scenario Test

**Status: PASS, with one methodology caveat surfaced (see Section 4).** This addendum closes a gap flagged in project review: `es_at_k_drift()` (S1) existed in `metrics.py` and the Model Regression Delta (S2) was defined in Volume 2, but neither had ever been exercised against a scenario built to actually contain drift or a regression. This document does that.

## 1. Purpose

Stability metrics are only trustworthy if they satisfy two independent conditions, the same standard already applied to the exposure metrics in the false-positive addendum:
1. They flag a real regression when a model change actually degrades exposure fairness (not previously tested for S1/S2).
2. They stay quiet when nothing has actually changed behaviorally, even if a model-version label changes (not previously tested).

This test builds two synthetic 16-week datasets and runs both through the unmodified `es_at_k_drift()` function and a directly-computed S2 delta.

## 2. Dataset Construction

- 2,000 sellers, ~96,000 ranking events across 16 weekly windows, cohorts Small (25%) / Medium (50%) / Large (25%) by listing volume — same cohort scheme as Volume 3.
- **`drift_scenario` (true positive):** weeks 0–7 run under `model_version` v1.0 with rank position assigned independently of cohort (fair baseline, same construction as `generate_fair_dataset.py`). At week 8, `model_version` changes to v1.1 **and** a real rank-position penalty is applied to Small sellers, systematically pushing them toward worse rank positions for the rest of the run.
- **`stable_scenario` (true negative / null control):** identical structure and the same model-version bump at week 8, but **no** penalty is applied — rank stays independent of cohort in every week, before and after. This isolates whether a version-label change alone can produce a false drift alarm.
- Both scenarios are seeded (42 and 43) for exact reproducibility.

## 3. Results

**S1 (ExposureShare@K Drift, 4-week trailing window), Small cohort:**

| Week | drift_scenario | stable_scenario |
|---|---|---|
| 4–7 (pre-change) | −5% to +6%, all PASS | −9% to +6%, all PASS |
| 8 | **−51.9%, REVIEW REQUIRED** | +6.0%, PASS |
| 9 | **−43.8%, REVIEW REQUIRED** | +2.4%, PASS |
| 10 | **−34.3%, REVIEW REQUIRED** | −1.3%, PASS |
| 11 | **−27.0%, REVIEW REQUIRED** | +3.9%, PASS |
| 12–15 (window re-baselined) | back to PASS — see Section 4 | all PASS |

**S2 (Model Regression Delta = post-deployment avg ES@K − pre-deployment avg ES@K), Small cohort:**

| Scenario | Pre avg (weeks 0–7) | Post avg (weeks 8–15) | RegressionΔ |
|---|---|---|---|
| drift_scenario | 0.9955 | 0.4764 | **−0.5190** |
| stable_scenario | 0.9888 | 0.9957 | +0.0069 |

**Corroborating E1 check** (all post-change weeks combined, not just the rolling window, using E1's 95% bootstrap confidence interval — see `docs/Validation_Addendum_Confidence_Intervals.md`): Small's ExposureShare@10 in `drift_scenario` is 0.996 [0.973, 1.017] in `stable_scenario` (solidly PASS with high confidence) versus 0.476 in `drift_scenario`, whose interval sits entirely below 0.80 — a confident REVIEW_REQUIRED, not a borderline call. The drift signal is not an artifact of the drift metric itself; there's a real, independently-measurable, high-confidence E1 breach behind it.

**Overall verdict:** PASS on both directions asked for — S1/S2 caught the injected regression (immediate Review Required status starting the exact week it was introduced, sustained for 4 consecutive weeks), and neither metric raised a false alarm on a version-label change with no underlying behavioral difference.

## 4. What this establishes, what it doesn't, and one real caveat

**Establishes:** S1 and S2 both react correctly, in the right direction, at the right time, to a genuine model-introduced regression, and both stay quiet on a null-case version bump. This is the true-positive/true-negative pairing this project already treats as the standard of evidence (see the E1/O3 false-positive addendum).

**A caveat this test surfaced, refined after checking the spec text directly:** in `drift_scenario`, S1's status returns to PASS at week 12 — four weeks after the regression started — *even though the regression never went away* (E1 for Small stays at ~0.45–0.50 for the rest of the run). This is expected behavior of a trailing-average drift metric, not a bug: once the entire 4-week trailing window sits inside the new, degraded normal, week-over-week "drift" relative to that window is near zero, because there's no further change left to detect. S1 is a *rate-of-change* detector, not a *sustained-disparity* detector.

Initially this was framed here as something only Volume 4's Release Gate Policy (deployment-time) protects against. Checking Volume 3 Section 6.2 directly (rather than relying on that initial framing) found something better: the standard's own weekly monitoring specification already lists "ExposureShare@k absolute level" as its own independently-monitored signal (Falls below 0.85 = Monitor, below 0.80 = Review Required), separate from "ExposureShare@k change" (the drift signal) — both at *routine weekly monitoring* time, not just at deployment. This test isn't exposing a gap in the design; it's empirical confirmation that Volume 3's two-signal monitoring design is necessary, not redundant — a drift-only monitor would have gone quiet on this exact scenario by week 12, and only the absolute-level signal Volume 3 already requires catches it from then on.

**Practical implication:** an audit process that implements only the drift signal from Section 6.1/6.2, skipping the absolute-level signal listed right next to it, would miss a regression that started and then stabilized between monitoring windows. Volume 3 already specifies both signals; this is a reminder that an implementation must actually build both, not a gap in what the standard requires.

**Does not establish:**
- Behavior on real marketplace data with confounds this synthetic test can't represent (same limitation noted in the false-positive addendum)
- Behavior at smaller data volumes/shorter windows, where weekly ES@K estimates are noisier and both false alarms and missed detection become more likely
- Whether a different drift window length (the catalog's K=20 robustness setting, or a window other than 4 weeks) changes the week-12 re-baselining behavior described above

## 5. Reproducibility

Code: `src/generate_drift_scenario_dataset.py` (dataset construction, both scenarios), `src/metrics.py` (`exposure_share_at_k`, `es_at_k_drift`, `classify_ci`), `src/run_drift_regression_test.py` (test runner, computes weekly ES@K, S1, S2, and the corroborating CI-aware E1 check). Seeded (42 / 43) for exact reproducibility. Re-run against the confidence-interval version of `metrics.py` (see `docs/Validation_Addendum_Confidence_Intervals.md`) with the same results reported above.
