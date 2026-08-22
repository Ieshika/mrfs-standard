# MRFS Validation Addendum: False-Positive (Null-Case) Test

**Status: PASS.** This addendum complements Volume 6 (Sample Audit Report) and closes a validation gap identified in project review: the original Sample Audit Report validated only that the protocol detects a known, intentionally-injected disparity. It did not test whether the protocol avoids flagging a genuinely fair system. This document does that.

## 1. Purpose

A fairness audit methodology is only trustworthy if it satisfies two independent conditions:
1. It flags real disparities when they exist (shown in Volume 6, on a dataset built to contain a known 38-point exposure gap).
2. It does **not** flag disparities that don't exist (not previously tested).

Without (2), "the audit passed" carries little evidential weight — a methodology that always alarms proves nothing. This test constructs a second synthetic dataset in which rank position is assigned **independently of seller cohort**, so a correctly-calibrated methodology should return PASS status across all metrics.

## 2. Dataset Construction

- 5,000 sellers, 250,000 ranking events, 12-week window — same scale as Volume 6 for direct comparability
- Cohorts: Small (25.7%) / Medium (49.1%) / Large (25.2%) by listing volume, matching the Volume 3 cohort scheme
- **Key construction difference from Volume 6:** for each ranking event, sellers are sampled uniformly at random and rank positions assigned by random permutation, with **no dependency on cohort membership**. Click/conversion probability depends only on rank position (standard position bias), not on cohort. This is the null hypothesis: a marketplace with zero cohort-based ranking bias.
- Same model-version change point (week 7, v1.0 → v1.1) retained from Volume 6's scenario for comparability, though no regression is injected.

## 3. Results

| Metric | Small | Medium | Large | Threshold | Status |
|---|---|---|---|---|---|
| ExposureShare@10 (E1) | 1.008 | 0.997 | 0.997 | ≥0.85 Pass | **PASS** |
| Mean Rank Position (E2) | 10.51 | 10.50 | 10.49 | Δ<5 Pass | **PASS** |
| Exposure Gini (E3) | 0.112 | 0.112 | 0.113 | — | Uniform across cohorts, as expected |
| CTR Disparate Impact (O3) | — | — | — | ≥0.85 Pass | **0.995 — PASS** |
| CVR Disparate Impact (O3) | — | — | — | ≥0.85 Pass | **1.019 — PASS** |

**Overall verdict: PASS.** No metric approached even the Monitor band (0.80–0.85), let alone Review Required. Exposure shares landed within ~1% of the proportional target of 1.0 for every cohort — consistent with sampling noise at this scale, not systematic bias.

## 4. What this establishes, and what it doesn't

**Establishes:** the core exposure and outcome metrics (E1, O3) do not produce false positives on a dataset explicitly constructed to be fair, at this data volume and cohort structure. Combined with Volume 6 (true positive on a known-disparity dataset), the protocol now has evidence in both directions on synthetic data.

**Does not establish:**
- Behavior on real marketplace data, which has confounds (category mix shifts, seasonal effects, genuinely different product quality across cohorts) this synthetic test cannot represent
- Behavior at smaller data volumes, where the noise floor is higher and false positives are more likely — this should be tested as a follow-up (e.g., repeat at n=10,000 minimum-viable-audit scale per Volume 3's data quality gate)
- The multiple-comparisons problem flagged separately in project review: this test evaluated one cohort pair at one point in time; running many weekly cohort × category comparisons at α=0.05 without correction remains an open risk not addressed by this test

## 5. Reproducibility

Code: `src/generate_fair_dataset.py` (dataset construction), `src/metrics.py` (metric implementations), `src/run_false_positive_test.py` (test runner). Seeded (seed=42) for exact reproducibility.
