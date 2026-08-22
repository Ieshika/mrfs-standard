"""
MRFS Metrics Implementation (v1.0)
Implements the metrics defined in Volume 2 (Evaluation Metric Catalog):
  E1 - ExposureShare@K
  E2 - Mean Rank Position (Delta)
  E3 - Exposure Gini
  O1 - CTR Parity Ratio
  O2 - CVR Parity Ratio
  O3 - CTR/CVR Disparate Impact Ratio
  S1 - ExposureShare@K Drift

Input contract (per Volume 3, Audit Protocol, Section 2):
  ranking_events: DataFrame with columns
    event_id, event_timestamp, query_context, category_id, item_id,
    seller_id, rank_position, was_clicked, was_converted, model_version
  seller_attributes: DataFrame with columns
    seller_id, seller_size (Small/Large), seller_tenure (New/Established),
    category_primary, listing_count
"""

import numpy as np
import pandas as pd


def exposure_share_at_k(events: pd.DataFrame, sellers: pd.DataFrame, k: int = 10,
                         cohort_col: str = "seller_size") -> pd.DataFrame:
    """
    E1: ExposureShare@K = [cohort's top-K count / total top-K slots] / [cohort size / total sellers]
    Returns one row per cohort value with the ES@K ratio.
    """
    merged = events.merge(sellers[["seller_id", cohort_col]], on="seller_id", how="left")
    top_k = merged[merged["rank_position"] <= k]

    total_top_k_slots = len(top_k)
    total_sellers = sellers["seller_id"].nunique()

    rows = []
    for cohort_value, group in top_k.groupby(cohort_col):
        cohort_top_k_count = len(group)
        cohort_size = sellers[sellers[cohort_col] == cohort_value]["seller_id"].nunique()

        observed_share = cohort_top_k_count / total_top_k_slots if total_top_k_slots else np.nan
        proportional_share = cohort_size / total_sellers if total_sellers else np.nan
        es_at_k = observed_share / proportional_share if proportional_share else np.nan

        rows.append({
            cohort_col: cohort_value,
            "k": k,
            "cohort_top_k_count": cohort_top_k_count,
            "cohort_size": cohort_size,
            "observed_share": observed_share,
            "proportional_share": proportional_share,
            "ES@K": es_at_k,
        })
    return pd.DataFrame(rows)


def mean_rank_delta(events: pd.DataFrame, sellers: pd.DataFrame,
                     cohort_col: str = "seller_size") -> pd.DataFrame:
    """
    E2: Mean Rank Position and the delta between cohort means.
    """
    merged = events.merge(sellers[["seller_id", cohort_col]], on="seller_id", how="left")
    means = merged.groupby(cohort_col)["rank_position"].agg(["mean", "std", "count"]).reset_index()
    means.columns = [cohort_col, "mean_rank", "std_rank", "n"]

    if len(means) == 2:
        v0, v1 = means["mean_rank"].iloc[0], means["mean_rank"].iloc[1]
        means["mean_rank_delta_vs_other"] = [v1 - v0, v0 - v1]
    return means


def exposure_gini(events: pd.DataFrame, sellers: pd.DataFrame, k: int = 10,
                   cohort_col: str = "seller_size", cohort_value: str = None) -> float:
    """
    E3: Gini index of top-K appearance distribution within a single cohort.
    0.0 = perfectly equitable across sellers in the cohort; 1.0 = one seller captures all visibility.
    """
    merged = events.merge(sellers[["seller_id", cohort_col]], on="seller_id", how="left")
    top_k = merged[merged["rank_position"] <= k]
    if cohort_value is not None:
        top_k = top_k[top_k[cohort_col] == cohort_value]

    counts = top_k.groupby("seller_id").size().values
    if len(counts) == 0:
        return np.nan

    sorted_counts = np.sort(counts)
    n = len(sorted_counts)
    cum = np.cumsum(sorted_counts)
    gini = (n + 1 - 2 * np.sum(cum) / cum[-1]) / n
    return float(gini)


def outcome_parity(events: pd.DataFrame, sellers: pd.DataFrame, k: int = 10,
                    cohort_col: str = "seller_size",
                    disadvantaged: str = "Small", reference: str = "Large") -> dict:
    """
    O1: CTR Parity Ratio, O2: CVR Parity Ratio, O3: Disparate Impact ratio
    (EEOC four-fifths rule analogy, applied here to CTR and CVR).
    """
    merged = events.merge(sellers[["seller_id", cohort_col]], on="seller_id", how="left")
    top_k = merged[merged["rank_position"] <= k]

    def rates(group):
        impressions = len(group)
        clicks = group["was_clicked"].sum()
        conversions = group["was_converted"].sum()
        ctr = clicks / impressions if impressions else np.nan
        cvr = conversions / impressions if impressions else np.nan
        return ctr, cvr

    disadv_group = top_k[top_k[cohort_col] == disadvantaged]
    ref_group = top_k[top_k[cohort_col] == reference]

    ctr_d, cvr_d = rates(disadv_group)
    ctr_r, cvr_r = rates(ref_group)

    ctr_parity = ctr_d / ctr_r if ctr_r else np.nan
    cvr_parity = cvr_d / cvr_r if cvr_r else np.nan

    return {
        "ctr_disadvantaged": ctr_d, "ctr_reference": ctr_r, "ctr_parity_ratio": ctr_parity,
        "cvr_disadvantaged": cvr_d, "cvr_reference": cvr_r, "cvr_parity_ratio": cvr_parity,
        "ctr_di_ratio": ctr_parity, "cvr_di_ratio": cvr_parity,
    }


def es_at_k_drift(weekly_es_at_k: pd.Series, current_week: int, window: int = 4) -> float:
    """
    S1: relative change in ExposureShare@K vs. trailing N-week moving average.
    weekly_es_at_k: Series indexed by week number, values = ES@K for that week.
    """
    trailing = weekly_es_at_k.loc[max(0, current_week - window):current_week - 1]
    if len(trailing) == 0 or trailing.mean() == 0:
        return np.nan
    current = weekly_es_at_k.loc[current_week]
    return float((current - trailing.mean()) / trailing.mean() * 100)


def evaluate_thresholds(es_at_k_df: pd.DataFrame, outcome: dict) -> dict:
    """
    Applies Volume 2 Section 6 consolidated thresholds and returns pass/monitor/review status
    per cohort and metric, plus an overall status.
    """
    results = {"E1": [], "O3": None, "overall": "PASS"}

    for _, row in es_at_k_df.iterrows():
        es = row["ES@K"]
        if es >= 0.85:
            status = "PASS"
        elif es >= 0.80:
            status = "MONITOR"
        else:
            status = "REVIEW_REQUIRED"
        results["E1"].append({row[es_at_k_df.columns[0]]: status, "ES@K": es})
        if status == "REVIEW_REQUIRED":
            results["overall"] = "REVIEW_REQUIRED"
        elif status == "MONITOR" and results["overall"] == "PASS":
            results["overall"] = "MONITOR"

    di = min(outcome["ctr_di_ratio"], outcome["cvr_di_ratio"])
    if di >= 0.85:
        di_status = "PASS"
    elif di >= 0.80:
        di_status = "MONITOR"
    else:
        di_status = "REVIEW_REQUIRED"
    results["O3"] = {"status": di_status, "min_di_ratio": di}
    if di_status == "REVIEW_REQUIRED":
        results["overall"] = "REVIEW_REQUIRED"
    elif di_status == "MONITOR" and results["overall"] == "PASS":
        results["overall"] = "MONITOR"

    return results
