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

Confidence intervals (E1, E2, O1-O3):
  A small-sample validation test (see
  docs/Validation_Addendum_Confidence_Intervals.md) found that at Volume 3's
  previously-documented minimum audit scale (10,000 events), point-estimate
  thresholds alone produced a false "Review Required" verdict on a
  genuinely fair marketplace 8% of the time, purely from sampling noise.
  E1, E2, and O1-O3 now compute a 95% confidence interval alongside the
  point estimate, via a nonparametric bootstrap, and `evaluate_thresholds()`
  uses the interval (not just the point estimate) to decide status.

  The bootstrap resamples whole ranking EVENTS (query instances) with
  replacement, not individual top-K rows. This matters: a single ranking
  event contributes multiple top-K rows (e.g. 10 rows for one query), and
  those rows are not independent of each other -- they're all one query's
  outcome. Resampling at the row level would treat correlated rows as
  independent evidence and understate the true uncertainty. Resampling
  whole events preserves that correlation structure, so the resulting
  interval is not artificially narrow.
"""

import numpy as np
import pandas as pd


def _bootstrap_percentile_ci(boot_values: np.ndarray, ci_level: float = 0.95):
    """Two-sided percentile CI from an array of bootstrap replicate values."""
    boot_values = boot_values[~np.isnan(boot_values)]
    if len(boot_values) == 0:
        return np.nan, np.nan
    alpha = 1 - ci_level
    lower = float(np.percentile(boot_values, 100 * alpha / 2))
    upper = float(np.percentile(boot_values, 100 * (1 - alpha / 2)))
    return lower, upper


def exposure_share_at_k(events: pd.DataFrame, sellers: pd.DataFrame, k: int = 10,
                         cohort_col: str = "seller_size",
                         n_boot: int = 1000, ci_level: float = 0.95, seed: int = None) -> pd.DataFrame:
    """
    E1: ExposureShare@K = [cohort's top-K count / total top-K slots] / [cohort size / total sellers]
    Returns one row per cohort value with the ES@K ratio and a 95% bootstrap CI
    (event-level block bootstrap -- see module docstring for why).
    """
    merged = events.merge(sellers[["seller_id", cohort_col]], on="seller_id", how="left")
    top_k = merged[merged["rank_position"] <= k]

    total_top_k_slots = len(top_k)
    total_sellers = sellers["seller_id"].nunique()
    cohort_sizes = sellers.groupby(cohort_col)["seller_id"].nunique()

    # --- point estimates (unchanged from the original implementation) ---
    point_rows = {}
    for cohort_value, group in top_k.groupby(cohort_col):
        cohort_top_k_count = len(group)
        cohort_size = int(cohort_sizes.get(cohort_value, 0))
        observed_share = cohort_top_k_count / total_top_k_slots if total_top_k_slots else np.nan
        proportional_share = cohort_size / total_sellers if total_sellers else np.nan
        es_at_k = observed_share / proportional_share if proportional_share else np.nan
        point_rows[cohort_value] = {
            "cohort_top_k_count": cohort_top_k_count,
            "cohort_size": cohort_size,
            "observed_share": observed_share,
            "proportional_share": proportional_share,
            "ES@K": es_at_k,
        }

    # --- event-level bootstrap for the CI ---
    all_event_ids = events["event_id"].unique()
    n_events = len(all_event_ids)
    cohort_values = list(point_rows.keys())

    pivot = (top_k.groupby(["event_id", cohort_col]).size()
             .unstack(fill_value=0).reindex(all_event_ids, fill_value=0))
    pivot = pivot.reindex(columns=cohort_values, fill_value=0)
    per_event_counts = pivot.values  # (n_events, n_cohorts)
    per_event_total = top_k.groupby("event_id").size().reindex(all_event_ids, fill_value=0).values  # (n_events,)

    proportional_shares = np.array([
        (int(cohort_sizes.get(cv, 0)) / total_sellers) if total_sellers else np.nan
        for cv in cohort_values
    ])

    boot_es = np.full((n_boot, len(cohort_values)), np.nan)
    if n_events > 0:
        rng = np.random.default_rng(seed)
        for b in range(n_boot):
            idx = rng.integers(0, n_events, size=n_events)
            boot_counts = per_event_counts[idx].sum(axis=0)
            boot_total = per_event_total[idx].sum()
            if boot_total == 0:
                continue
            observed_share_b = boot_counts / boot_total
            with np.errstate(divide="ignore", invalid="ignore"):
                boot_es[b] = observed_share_b / proportional_shares

    rows = []
    for j, cohort_value in enumerate(cohort_values):
        lower, upper = _bootstrap_percentile_ci(boot_es[:, j], ci_level)
        n_valid_boot = int(np.sum(~np.isnan(boot_es[:, j])))
        row = {cohort_col: cohort_value, "k": k, **point_rows[cohort_value],
               "ES@K_ci_lower": lower, "ES@K_ci_upper": upper, "n_bootstrap": n_valid_boot}
        rows.append(row)
    return pd.DataFrame(rows)


def mean_rank_delta(events: pd.DataFrame, sellers: pd.DataFrame,
                     cohort_col: str = "seller_size",
                     n_boot: int = 1000, ci_level: float = 0.95, seed: int = None) -> pd.DataFrame:
    """
    E2: Mean Rank Position and the delta between cohort means, with a 95%
    bootstrap CI on each cohort's mean rank (same event-level resampling as E1).
    """
    merged = events.merge(sellers[["seller_id", cohort_col]], on="seller_id", how="left")
    means = merged.groupby(cohort_col)["rank_position"].agg(["mean", "std", "count"]).reset_index()
    means.columns = [cohort_col, "mean_rank", "std_rank", "n"]

    if len(means) == 2:
        v0, v1 = means["mean_rank"].iloc[0], means["mean_rank"].iloc[1]
        means["mean_rank_delta_vs_other"] = [v1 - v0, v0 - v1]

    all_event_ids = events["event_id"].unique()
    n_events = len(all_event_ids)
    cohort_values = means[cohort_col].tolist()

    sum_pivot = (merged.groupby(["event_id", cohort_col])["rank_position"].sum()
                 .unstack(fill_value=0).reindex(all_event_ids, fill_value=0)
                 .reindex(columns=cohort_values, fill_value=0))
    count_pivot = (merged.groupby(["event_id", cohort_col])["rank_position"].count()
                   .unstack(fill_value=0).reindex(all_event_ids, fill_value=0)
                   .reindex(columns=cohort_values, fill_value=0))
    sum_arr = sum_pivot.values
    count_arr = count_pivot.values

    lowers, uppers, n_boots = [], [], []
    if n_events > 0:
        rng = np.random.default_rng(seed)
        boot_means = np.full((n_boot, len(cohort_values)), np.nan)
        for b in range(n_boot):
            idx = rng.integers(0, n_events, size=n_events)
            boot_sum = sum_arr[idx].sum(axis=0)
            boot_count = count_arr[idx].sum(axis=0)
            with np.errstate(divide="ignore", invalid="ignore"):
                boot_means[b] = boot_sum / boot_count
        for j in range(len(cohort_values)):
            lower, upper = _bootstrap_percentile_ci(boot_means[:, j], ci_level)
            lowers.append(lower)
            uppers.append(upper)
            n_boots.append(int(np.sum(~np.isnan(boot_means[:, j]))))
    else:
        lowers = uppers = [np.nan] * len(cohort_values)
        n_boots = [0] * len(cohort_values)

    means["mean_rank_ci_lower"] = lowers
    means["mean_rank_ci_upper"] = uppers
    means["n_bootstrap"] = n_boots
    return means


def exposure_gini(events: pd.DataFrame, sellers: pd.DataFrame, k: int = 10,
                   cohort_col: str = "seller_size", cohort_value: str = None) -> float:
    """
    E3: Gini index of top-K appearance distribution within a single cohort.
    0.0 = perfectly equitable across sellers in the cohort; 1.0 = one seller captures all visibility.
    (No CI: Volume 2 does not define a hard threshold for E3, only a contextual
    flag, so the false-positive problem this addendum addresses does not apply here.)
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
                    disadvantaged: str = "Small", reference: str = "Large",
                    n_boot: int = 1000, ci_level: float = 0.95, seed: int = None) -> dict:
    """
    O1: CTR Parity Ratio, O2: CVR Parity Ratio, O3: Disparate Impact ratio
    (EEOC four-fifths rule analogy, applied here to CTR and CVR), with 95%
    bootstrap CIs on both ratios (same event-level resampling as E1/E2).
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

    # --- event-level bootstrap for CI on both ratios ---
    all_event_ids = events["event_id"].unique()
    n_events = len(all_event_ids)

    def per_event_sums(group, label):
        imp = group.groupby("event_id").size().reindex(all_event_ids, fill_value=0)
        clk = group.groupby("event_id")["was_clicked"].sum().reindex(all_event_ids, fill_value=0)
        cvt = group.groupby("event_id")["was_converted"].sum().reindex(all_event_ids, fill_value=0)
        return imp.values, clk.values, cvt.values

    imp_d, clk_d, cvt_d = per_event_sums(disadv_group, "disadv")
    imp_r, clk_r, cvt_r = per_event_sums(ref_group, "ref")

    ctr_boot = np.full(n_boot, np.nan)
    cvr_boot = np.full(n_boot, np.nan)
    if n_events > 0:
        rng = np.random.default_rng(seed)
        for b in range(n_boot):
            idx = rng.integers(0, n_events, size=n_events)
            b_imp_d, b_clk_d, b_cvt_d = imp_d[idx].sum(), clk_d[idx].sum(), cvt_d[idx].sum()
            b_imp_r, b_clk_r, b_cvt_r = imp_r[idx].sum(), clk_r[idx].sum(), cvt_r[idx].sum()
            if b_imp_d > 0 and b_imp_r > 0:
                b_ctr_d, b_ctr_r = b_clk_d / b_imp_d, b_clk_r / b_imp_r
                b_cvr_d, b_cvr_r = b_cvt_d / b_imp_d, b_cvt_r / b_imp_r
                if b_ctr_r > 0:
                    ctr_boot[b] = b_ctr_d / b_ctr_r
                if b_cvr_r > 0:
                    cvr_boot[b] = b_cvr_d / b_cvr_r

    ctr_lower, ctr_upper = _bootstrap_percentile_ci(ctr_boot, ci_level)
    cvr_lower, cvr_upper = _bootstrap_percentile_ci(cvr_boot, ci_level)

    return {
        "ctr_disadvantaged": ctr_d, "ctr_reference": ctr_r, "ctr_parity_ratio": ctr_parity,
        "cvr_disadvantaged": cvr_d, "cvr_reference": cvr_r, "cvr_parity_ratio": cvr_parity,
        "ctr_di_ratio": ctr_parity, "cvr_di_ratio": cvr_parity,
        "ctr_di_ci_lower": ctr_lower, "ctr_di_ci_upper": ctr_upper,
        "cvr_di_ci_lower": cvr_lower, "cvr_di_ci_upper": cvr_upper,
        "n_bootstrap": int(np.sum(~np.isnan(ctr_boot))),
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


def classify_ci(lower: float, upper: float, review_line: float, monitor_line: float) -> str:
    """
    Classifies a metric as PASS / MONITOR / REVIEW_REQUIRED / INSUFFICIENT_DATA
    based on where its full confidence interval falls relative to the two
    Volume 2 Section 6 threshold lines, not just the point estimate.

      - Entire interval >= monitor_line             -> PASS
      - Entire interval in [review_line, monitor_line) -> MONITOR
      - Entire interval  < review_line               -> REVIEW_REQUIRED
      - Interval straddles a threshold line          -> INSUFFICIENT_DATA
        (the data can't distinguish between the two adjacent statuses --
        this is the status a small/noisy sample should honestly report,
        instead of a confident-sounding but potentially wrong PASS/MONITOR/
        REVIEW_REQUIRED verdict.)
    """
    if lower is None or upper is None or np.isnan(lower) or np.isnan(upper):
        return "INSUFFICIENT_DATA"
    if lower >= monitor_line:
        return "PASS"
    if upper < review_line:
        return "REVIEW_REQUIRED"
    if lower >= review_line and upper < monitor_line:
        return "MONITOR"
    return "INSUFFICIENT_DATA"


def evaluate_thresholds(es_at_k_df: pd.DataFrame, outcome: dict) -> dict:
    """
    Applies Volume 2 Section 6 consolidated thresholds using each metric's
    95% confidence interval (not just its point estimate) to decide status.
    Adds a fourth status, INSUFFICIENT_DATA, for the case where the interval
    straddles a threshold line -- i.e., the audit doesn't have enough data at
    this sample size to confidently tell PASS from MONITOR, or MONITOR from
    REVIEW_REQUIRED. This replaces the point-estimate-only version that
    produced an 8% false "Review Required" rate on a genuinely fair
    marketplace at Volume 3's previously-documented minimum scale (10,000
    events) -- see docs/Validation_Addendum_Confidence_Intervals.md.

    Falls back to point-estimate classification (with a printed warning) if
    es_at_k_df/outcome don't have CI columns -- e.g. if called with output
    from an older version of exposure_share_at_k()/outcome_parity().
    """
    results = {"E1": [], "O3": None, "overall": "PASS"}
    has_ci_cols = "ES@K_ci_lower" in es_at_k_df.columns and "ES@K_ci_upper" in es_at_k_df.columns

    def _bump_overall(current_overall, status):
        rank = {"PASS": 0, "INSUFFICIENT_DATA": 1, "MONITOR": 2, "REVIEW_REQUIRED": 3}
        return status if rank[status] > rank[current_overall] else current_overall

    for _, row in es_at_k_df.iterrows():
        es = row["ES@K"]
        if has_ci_cols:
            status = classify_ci(row["ES@K_ci_lower"], row["ES@K_ci_upper"],
                                         review_line=0.80, monitor_line=0.85)
        else:
            if es >= 0.85:
                status = "PASS"
            elif es >= 0.80:
                status = "MONITOR"
            else:
                status = "REVIEW_REQUIRED"
        results["E1"].append({row[es_at_k_df.columns[0]]: status, "ES@K": es,
                               "ci_lower": row.get("ES@K_ci_lower"), "ci_upper": row.get("ES@K_ci_upper")})
        results["overall"] = _bump_overall(results["overall"], status)

    di = min(outcome["ctr_di_ratio"], outcome["cvr_di_ratio"])
    has_o3_ci = "ctr_di_ci_lower" in outcome and "cvr_di_ci_lower" in outcome
    if has_o3_ci:
        # Use whichever of CTR/CVR DI has the tighter (more conservative, i.e. lower) upper bound
        # paired with its own lower bound -- classify each ratio's interval, take the worse status.
        ctr_status = classify_ci(outcome["ctr_di_ci_lower"], outcome["ctr_di_ci_upper"], 0.80, 0.85)
        cvr_status = classify_ci(outcome["cvr_di_ci_lower"], outcome["cvr_di_ci_upper"], 0.80, 0.85)
        di_status = "PASS"
        di_status = _bump_overall(di_status, ctr_status)
        di_status = _bump_overall(di_status, cvr_status)
    else:
        if di >= 0.85:
            di_status = "PASS"
        elif di >= 0.80:
            di_status = "MONITOR"
        else:
            di_status = "REVIEW_REQUIRED"

    results["O3"] = {"status": di_status, "min_di_ratio": di}
    results["overall"] = _bump_overall(results["overall"], di_status)

    return results
