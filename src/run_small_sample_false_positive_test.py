"""
Small-sample false-positive test (CI-aware version).

Re-runs the same fair (no built-in disparity) dataset construction across
many seeds at a range of scales, now using the CI-aware exposure_share_at_k /
outcome_parity / evaluate_thresholds. Reports status counts including the new
INSUFFICIENT_DATA status, and the false "Review Required" rate, to confirm
the confidence-interval fix actually closes the gap the point-estimate-only
version had at small sample sizes (see
docs/Validation_Addendum_Confidence_Intervals.md).
"""

import pandas as pd
from generate_fair_dataset import generate_fair_dataset
from metrics import exposure_share_at_k, outcome_parity, evaluate_thresholds


def run_trial(n_events: int, seed: int) -> dict:
    events, sellers = generate_fair_dataset(n_sellers=5000, n_events=n_events, weeks=12, seed=seed)

    es_k10 = exposure_share_at_k(events, sellers, k=10, cohort_col="seller_size",
                                  n_boot=500, seed=seed + 500000)
    es_small_large = es_k10[es_k10["seller_size"].isin(["Small", "Large"])]

    outcome = outcome_parity(events, sellers, k=10, cohort_col="seller_size",
                              disadvantaged="Small", reference="Large",
                              n_boot=500, seed=seed + 700000)

    verdict = evaluate_thresholds(es_small_large, outcome)
    return {"seed": seed, "n_events": n_events, "overall": verdict["overall"]}


def run_scale(n_events: int, n_trials: int) -> pd.DataFrame:
    return pd.DataFrame([run_trial(n_events, seed) for seed in range(n_trials)])


if __name__ == "__main__":
    print("=" * 95)
    print("SMALL-SAMPLE FALSE-POSITIVE TEST -- CI-AWARE VERSION")
    print("=" * 95)

    scales = [(10_000, 50), (25_000, 40), (50_000, 30), (100_000, 20), (250_000, 15)]
    print(f"\n  {'n_events':>10} | {'trials':>6} | {'PASS':>4} | {'MONITOR':>7} | {'REVIEW_REQ':>10} | "
          f"{'INSUFF_DATA':>11} | {'false REVIEW rate':>18}")
    for n_events, n_trials in scales:
        df = run_scale(n_events, n_trials)
        counts = df["overall"].value_counts().reindex(
            ["PASS", "MONITOR", "REVIEW_REQUIRED", "INSUFFICIENT_DATA"], fill_value=0)
        fp_rate_review = (df["overall"] == "REVIEW_REQUIRED").mean()
        print(f"  {n_events:>10,} | {n_trials:>6} | {counts['PASS']:>4} | {counts['MONITOR']:>7} | "
              f"{counts['REVIEW_REQUIRED']:>10} | {counts['INSUFFICIENT_DATA']:>11} | {fp_rate_review:>17.1%}")

    print("\nExpected: false REVIEW rate at 0.0% across every scale, including 10,000 -- small")
    print("scales should report INSUFFICIENT_DATA rather than a false confident verdict.")
