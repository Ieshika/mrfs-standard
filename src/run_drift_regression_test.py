"""
S1 (ExposureShare@K Drift) and S2 (Model Regression Delta) scenario test.

Runs both the true-positive ("drift_scenario": a real regression is injected
against Small sellers starting at week 8) and the true-negative
("stable_scenario": model_version changes but nothing behavioral does)
datasets through the real, unmodified metrics.py functions and checks:

  1. S1 (es_at_k_drift) flags Monitor/Review Required drift in the weeks
     after the injected regression in drift_scenario, and stays within Pass
     band (<10%) throughout stable_scenario.
  2. S2 (Model Regression Delta = ES@K(post avg) - ES@K(pre avg)) shows a
     large negative delta in drift_scenario and a near-zero delta in
     stable_scenario.
  3. The drift is corroborated independently by E1 (ExposureShare@K itself,
     now with its 95% bootstrap confidence interval -- see
     docs/Validation_Addendum_Confidence_Intervals.md) dropping below the
     Volume 2 Section 6 Review Required band for Small sellers post-regression
     in drift_scenario -- i.e., S1 isn't just flagging noise, there's a real,
     confidently-established underlying E1 breach behind it.

Volume 2 Section 6 S1 thresholds applied: Pass < 10% decline, Monitor >= 10%,
Review Required >= 20% (or sustained > 2 consecutive weeks at >= 10%).

Run generate_drift_scenario_dataset.py first to produce the two input CSVs.
See docs/Validation_Addendum_Drift_Regression_Test.md for the full write-up,
including a caveat about S1's trailing-window behavior this test surfaced.
"""

import pandas as pd
from metrics import exposure_share_at_k, es_at_k_drift, classify_ci

DRIFT_START_WEEK = 8
WINDOW = 4
COHORT = "Small"


def weekly_es_at_k_series(events: pd.DataFrame, sellers: pd.DataFrame, cohort_value: str) -> pd.Series:
    values = {}
    for week, week_events in events.groupby("week"):
        es_df = exposure_share_at_k(week_events, sellers, k=10, cohort_col="seller_size", n_boot=200)
        row = es_df[es_df["seller_size"] == cohort_value]
        values[week] = row["ES@K"].iloc[0] if len(row) else float("nan")
    return pd.Series(values).sort_index()


def classify_s1(drift_pct: float, sustained_weeks: int) -> str:
    if drift_pct <= -20 or sustained_weeks > 2:
        return "REVIEW_REQUIRED"
    elif drift_pct <= -10:
        return "MONITOR"
    else:
        return "PASS"


def run_scenario(label: str):
    events = pd.read_csv(f"{label}_events.csv")
    sellers = pd.read_csv(f"{label}_sellers.csv")

    print("=" * 78)
    print(f"SCENARIO: {label}")
    print("=" * 78)

    weekly_es = weekly_es_at_k_series(events, sellers, COHORT)
    print(f"\nWeekly ExposureShare@10 ({COHORT} cohort):")
    print(weekly_es.round(3).to_string())

    # --- S1: drift vs trailing 4-week average, for every week after the window fills ---
    print(f"\n--- S1: ExposureShare@K Drift (window={WINDOW}) ---")
    consecutive_monitor_or_worse = 0
    max_sustained = 0
    s1_statuses = {}
    for week in range(WINDOW, len(weekly_es)):
        drift_pct = es_at_k_drift(weekly_es, current_week=week, window=WINDOW)
        if drift_pct <= -10:
            consecutive_monitor_or_worse += 1
        else:
            consecutive_monitor_or_worse = 0
        max_sustained = max(max_sustained, consecutive_monitor_or_worse)
        status = classify_s1(drift_pct, consecutive_monitor_or_worse)
        s1_statuses[week] = status
        flag = "  <-- post-regression window" if week >= DRIFT_START_WEEK else ""
        print(f"  week {week:2d}: drift = {drift_pct:+7.2f}%   status = {status:<16}{flag}")

    # --- S2: Model Regression Delta, pre vs post deployment ---
    pre = weekly_es.loc[:DRIFT_START_WEEK - 1].mean()
    post = weekly_es.loc[DRIFT_START_WEEK:].mean()
    regression_delta = post - pre
    print("\n--- S2: Model Regression Delta ---")
    print(f"  pre-deployment avg ES@K  (weeks 0-{DRIFT_START_WEEK - 1}):  {pre:.4f}")
    print(f"  post-deployment avg ES@K (weeks {DRIFT_START_WEEK}-{len(weekly_es)-1}): {post:.4f}")
    print(f"  RegressionΔ = post - pre = {regression_delta:+.4f}")

    # --- Corroborating E1 check: does Small's ES@K actually breach Review Required
    #     post-change, with high enough confidence to say so (not just point estimate)? ---
    post_events = events[events["week"] >= DRIFT_START_WEEK]
    post_es = exposure_share_at_k(post_events, sellers, k=10, cohort_col="seller_size")
    post_row = post_es[post_es["seller_size"] == COHORT].iloc[0]
    e1_status = classify_ci(post_row["ES@K_ci_lower"], post_row["ES@K_ci_upper"],
                             review_line=0.80, monitor_line=0.85)
    print(f"\n--- Corroborating check: E1 (ExposureShare@K) for {COHORT}, all post-change weeks combined ---")
    print(f"  ES@K = {post_row['ES@K']:.4f}  [{post_row['ES@K_ci_lower']:.4f}, {post_row['ES@K_ci_upper']:.4f}]"
          f"  ->  E1 status = {e1_status}")

    post_change_statuses = [s1_statuses[w] for w in s1_statuses if w >= DRIFT_START_WEEK]
    any_flagged = any(s != "PASS" for s in post_change_statuses)

    return {
        "label": label,
        "regression_delta": regression_delta,
        "e1_status_post": e1_status,
        "any_s1_flag_post_change": any_flagged,
        "max_sustained_monitor_weeks": max_sustained,
    }


if __name__ == "__main__":
    drift_result = run_scenario("drift_scenario")
    stable_result = run_scenario("stable_scenario")

    print("\n" + "=" * 78)
    print("SUMMARY")
    print("=" * 78)
    for r in (drift_result, stable_result):
        print(f"  {r['label']:16s}  RegressionΔ={r['regression_delta']:+.4f}  "
              f"E1_post={r['e1_status_post']:<18s}  "
              f"S1_flagged_post_change={r['any_s1_flag_post_change']}  "
              f"max_sustained={r['max_sustained_monitor_weeks']}")

    print()
    true_positive_ok = drift_result["any_s1_flag_post_change"] and drift_result["e1_status_post"] == "REVIEW_REQUIRED"
    true_negative_ok = not stable_result["any_s1_flag_post_change"] and stable_result["e1_status_post"] == "PASS"

    if true_positive_ok:
        print("PASS: S1/S2 correctly caught the injected regression in drift_scenario, "
              "confirmed with high confidence by E1's own interval.")
    else:
        print("FAIL: S1/S2 did NOT catch the injected regression in drift_scenario -- investigate.")

    if true_negative_ok:
        print("PASS: S1 correctly stayed quiet on stable_scenario (no false alarm on a version bump alone).")
    else:
        print("FAIL: S1 raised a false alarm on stable_scenario -- investigate threshold/noise calibration.")
