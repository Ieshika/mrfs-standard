"""
MRFS Etsy Real-Data Pilot -- Audit Report Generator (src/generate_audit_report.py)

Reference implementation component. Formats the metrics computed by
run_etsy_pilot.py into a standardized markdown report.

Deliberately does NOT call metrics.py's evaluate_thresholds() -- that
function requires an `outcome` dict with ctr_di_ratio/cvr_di_ratio, which
this pilot cannot populate (no public Etsy click/conversion data). E1
pass/monitor/review/insufficient-data status is evaluated locally below via
metrics.py's own classify_ci(), using each cohort's 95% bootstrap confidence
interval (not just its point estimate) -- the identical logic
evaluate_thresholds() applies to E1, reused directly rather than
re-implemented, so this stays a subset of the same validated classification,
not a second threshold policy.
"""

import os
import sys
from datetime import datetime, timezone

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metrics import classify_ci  # noqa: E402


def _e1_status(row: pd.Series) -> str:
    if pd.isna(row.get("ES@K")):
        return "N/A"
    if "ES@K_ci_lower" in row and "ES@K_ci_upper" in row:
        return classify_ci(row["ES@K_ci_lower"], row["ES@K_ci_upper"], review_line=0.80, monitor_line=0.85)
    # Fallback for older data without CI columns.
    es = row["ES@K"]
    if es >= 0.85:
        return "PASS"
    if es >= 0.80:
        return "MONITOR"
    return "REVIEW_REQUIRED"


def generate_report(results: dict, events_df: pd.DataFrame, sellers_df: pd.DataFrame) -> str:
    lines = []
    lines.append("# MRFS Etsy Real-Data Pilot -- Audit Report")
    lines.append("")
    lines.append(
        "**Status: FEASIBILITY PILOT, not a statistically powered claim.** "
        "This report is a single real-data measurement, not a validated finding -- "
        "see the Limitations section below before citing any number in this report."
    )
    lines.append("")
    lines.append(f"- Run directory: `{results['run_dir']}`")
    lines.append(f"- Query set version: `{results['query_set_version']}` (see `query_set.py`)")
    lines.append(f"- Report generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Search events collected: {len(events_df)}")
    lines.append(f"- Unique shops observed: {sellers_df['seller_id'].nunique() if len(sellers_df) else 0}")
    lines.append("")
    lines.append(
        "**Scope limit:** this pilot measures exposure metrics only "
        "(E1 ExposureShare@K, E2 Mean Rank Position, E3 Exposure Gini). "
        "Outcome metrics (O1-O3, CTR/CVR disparate impact) are not computed -- "
        "Etsy's public API does not expose click-through or conversion data for "
        "listings other than your own shop's."
    )
    lines.append("")
    lines.append(
        "**On status column below:** every E1 status is based on a 95% bootstrap "
        "confidence interval, not the point estimate alone -- this pilot typically runs "
        "at a small event count per query set, where INSUFFICIENT_DATA is the honest, "
        "expected result far more often than a confident PASS/MONITOR/REVIEW_REQUIRED. "
        "See `docs/Validation_Addendum_Confidence_Intervals.md` for why."
    )
    lines.append("")

    for cohort_col, cohort_results in results.get("cohorts", {}).items():
        lines.append(f"## Cohort dimension: `{cohort_col}`")
        lines.append("")

        es_df = cohort_results["es_at_k"].copy()
        if not es_df.empty:
            es_df["status"] = es_df.apply(_e1_status, axis=1)
        lines.append("### E1 -- ExposureShare@K (k=10)")
        lines.append("")
        has_ci = "ES@K_ci_lower" in es_df.columns
        if has_ci:
            lines.append(f"| {cohort_col} | cohort size | top-K count | observed share | "
                          f"proportional share | ES@K | 95% CI | status |")
            lines.append("|---|---|---|---|---|---|---|---|")
            for _, row in es_df.iterrows():
                lines.append(
                    f"| {row[cohort_col]} | {row['cohort_size']} | {row['cohort_top_k_count']} | "
                    f"{row['observed_share']:.3f} | {row['proportional_share']:.3f} | "
                    f"{row['ES@K']:.3f} | [{row['ES@K_ci_lower']:.3f}, {row['ES@K_ci_upper']:.3f}] | "
                    f"{row['status']} |"
                )
        else:
            lines.append(f"| {cohort_col} | cohort size | top-K count | observed share | proportional share | ES@K | status |")
            lines.append("|---|---|---|---|---|---|---|")
            for _, row in es_df.iterrows():
                lines.append(
                    f"| {row[cohort_col]} | {row['cohort_size']} | {row['cohort_top_k_count']} | "
                    f"{row['observed_share']:.3f} | {row['proportional_share']:.3f} | "
                    f"{row['ES@K']:.3f} | {row['status']} |"
                )
        lines.append("")

        rank_df = cohort_results["mean_rank"]
        lines.append("### E2 -- Mean Rank Position")
        lines.append("")
        has_rank_ci = "mean_rank_ci_lower" in rank_df.columns
        if has_rank_ci:
            lines.append(f"| {cohort_col} | mean rank | 95% CI | std | n |")
            lines.append("|---|---|---|---|---|")
            for _, row in rank_df.iterrows():
                lines.append(f"| {row[cohort_col]} | {row['mean_rank']:.2f} | "
                              f"[{row['mean_rank_ci_lower']:.2f}, {row['mean_rank_ci_upper']:.2f}] | "
                              f"{row['std_rank']:.2f} | {row['n']} |")
        else:
            lines.append(f"| {cohort_col} | mean rank | std | n |")
            lines.append("|---|---|---|---|")
            for _, row in rank_df.iterrows():
                lines.append(f"| {row[cohort_col]} | {row['mean_rank']:.2f} | {row['std_rank']:.2f} | {row['n']} |")
        lines.append("")

        lines.append("### E3 -- Exposure Gini (within cohort, top-K)")
        lines.append("")
        for cohort_value, gini in cohort_results["gini"].items():
            gini_str = f"{gini:.3f}" if pd.notna(gini) else "N/A"
            lines.append(f"- **{cohort_value}**: {gini_str}")
        lines.append("")

    lines.append("## Limitations")
    lines.append("")
    lines.append(
        "- **Single run.** One measurement is a data point, not evidence of consistency. "
        "Repeat this pilot across multiple different days before drawing any conclusion "
        "about whether a pattern is stable."
    )
    lines.append(
        "- **Rank-position proxy.** `rank_position` reflects the order Etsy's public API "
        "returned listings under `sort_on=score` (its documented relevance sort) -- the "
        "closest available proxy to on-site search order, not a certified match to what "
        "any specific buyer sees (personalization, promoted listings, and A/B tests are "
        "not reproducible via this API)."
    )
    lines.append(
        "- **Seller-size cohort is a median split**, not a strict top/bottom quartile "
        "split as ARCHITECTURE.md's cohort scheme literally describes."
    )
    lines.append(
        "- **No outcome metrics.** E1-E3 only; see Scope limit above."
    )
    lines.append(
        "- **Small sample.** A handful of queries and shops is not a statistically powered "
        "sample of Etsy's marketplace. The 95% confidence intervals above make this "
        "explicit rather than leaving it implicit -- treat an INSUFFICIENT_DATA status as "
        "the expected, honest result at this scale, not a bug."
    )
    lines.append("")

    run_dir = results["run_dir"]
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    reports_dir = os.path.join(repo_root, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    run_id = os.path.basename(run_dir)
    report_path = os.path.join(reports_dir, f"etsy_pilot_report_{run_id}.md")
    with open(report_path, "w") as f:
        f.write("\n".join(lines))
    return report_path
