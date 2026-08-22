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

# E1 - ExposureShare@K
es_k10 = exposure_share_at_k(events, sellers, k=10, cohort_col="seller_size")
print("\n--- E1: ExposureShare@10 ---")
print(es_k10.to_string(index=False))

# E2 - Mean Rank Delta
mrd = mean_rank_delta(events, sellers, cohort_col="seller_size")
print("\n--- E2: Mean Rank Position ---")
print(mrd.to_string(index=False))

# E3 - Exposure Gini (per cohort)
print("\n--- E3: Exposure Gini (within cohort) ---")
for cohort in sellers["seller_size"].unique():
    g = exposure_gini(events, sellers, k=10, cohort_col="seller_size", cohort_value=cohort)
    print(f"  {cohort}: {g:.3f}")

# O1/O2/O3 - Outcome parity (Small vs Large, matching Vol 6's comparison)
outcome = outcome_parity(events, sellers, k=10, cohort_col="seller_size",
                          disadvantaged="Small", reference="Large")
print("\n--- O1/O2/O3: Outcome Parity (Small vs Large) ---")
for k, v in outcome.items():
    print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

# Threshold evaluation
es_small_large = es_k10[es_k10["seller_size"].isin(["Small", "Large"])]
verdict = evaluate_thresholds(es_small_large, outcome)
print("\n--- THRESHOLD EVALUATION (Volume 2, Section 6) ---")
print(verdict)

print("\n" + "=" * 70)
if verdict["overall"] == "PASS":
    print("RESULT: PASS — protocol correctly did NOT flag a genuinely fair dataset.")
elif verdict["overall"] == "MONITOR":
    print("RESULT: MONITOR — some metrics near threshold; expected under random noise at this scale.")
else:
    print("RESULT: REVIEW_REQUIRED — FALSE POSITIVE. Investigate metric/threshold calibration.")
print("=" * 70)
