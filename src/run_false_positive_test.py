import pandas as pd
from metrics import exposure_share_at_k, mean_rank_delta, exposure_gini, outcome_parity, evaluate_thresholds

events = pd.read_csv("fair_dataset_events.csv")
sellers = pd.read_csv("fair_dataset_sellers.csv")

print("=" * 70)
print("MRFS FALSE-POSITIVE VALIDATION TEST")
print("Dataset: synthetic, proportionally-fair (no built-in disparity)")
print("=" * 70)

print(f"\nTotal events: {len(events):,} | Total sellers: {sellers['seller_id'].nunique():,}")
print(sellers["seller_size"].value_counts().to_string())

# E1 - ExposureShare@K (now with a 95% bootstrap CI alongside the point estimate)
es_k10 = exposure_share_at_k(events, sellers, k=10, cohort_col="seller_size", seed=42)
print("\n--- E1: ExposureShare@10 (with 95% CI) ---")
print(es_k10[["seller_size", "ES@K", "ES@K_ci_lower", "ES@K_ci_upper"]].to_string(index=False))

# E2 - Mean Rank Delta (now with a 95% bootstrap CI on each cohort's mean rank)
mrd = mean_rank_delta(events, sellers, cohort_col="seller_size", seed=42)
print("\n--- E2: Mean Rank Position (with 95% CI) ---")
print(mrd.to_string(index=False))

# E3 - Exposure Gini (per cohort)
print("\n--- E3: Exposure Gini (within cohort) ---")
for cohort in sellers["seller_size"].unique():
    g = exposure_gini(events, sellers, k=10, cohort_col="seller_size", cohort_value=cohort)
    print(f"  {cohort}: {g:.3f}")

# O1/O2/O3 - Outcome parity (Small vs Large, matching Vol 6's comparison), now with CI
outcome = outcome_parity(events, sellers, k=10, cohort_col="seller_size",
                          disadvantaged="Small", reference="Large", seed=42)
print("\n--- O1/O2/O3: Outcome Parity (Small vs Large, with 95% CI on the DI ratios) ---")
for k, v in outcome.items():
    print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

# Threshold evaluation -- now confidence-interval-aware, with a 4th status
# (INSUFFICIENT_DATA) alongside PASS/MONITOR/REVIEW_REQUIRED. See
# docs/Validation_Addendum_Confidence_Intervals.md.
es_small_large = es_k10[es_k10["seller_size"].isin(["Small", "Large"])]
verdict = evaluate_thresholds(es_small_large, outcome)
print("\n--- THRESHOLD EVALUATION (Volume 2, Section 6; CI-aware) ---")
print(verdict)

print("\n" + "=" * 70)
if verdict["overall"] == "PASS":
    print("RESULT: PASS — protocol correctly did NOT flag a genuinely fair dataset,")
    print("        with high enough confidence at this sample size to say so.")
elif verdict["overall"] == "INSUFFICIENT_DATA":
    print("RESULT: INSUFFICIENT_DATA — not enough data at this sample size to")
    print("        confidently distinguish Pass from Monitor/Review. Expected at")
    print("        small N; not a false positive.")
elif verdict["overall"] == "MONITOR":
    print("RESULT: MONITOR — some metrics near threshold; expected under random noise at this scale.")
else:
    print("RESULT: REVIEW_REQUIRED — FALSE POSITIVE. Investigate metric/threshold calibration.")
print("=" * 70)
