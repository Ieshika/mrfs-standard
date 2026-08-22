"""
MRFS Etsy Real-Data Pilot -- Metrics Runner (src/run_etsy_pilot.py)

Reference implementation component (see DECISIONS.md D12). Loads the most
recent Etsy pilot data collected by etsy_pilot_collector.py, runs it through
the real MRFS metrics (metrics.py), and calls generate_audit_report.py to
produce a written report.

Scope limit (D13): only E1 (ExposureShare@K), E2 (Mean Rank Position), and
E3 (Exposure Gini) are computed -- outcome metrics (O1-O3) require
click/conversion data that isn't public on Etsy, so they are not attempted
here. Do not add them without a real outcome-data source (see D14).

Usage:
    python3 run_etsy_pilot.py                   # uses the most recent run
    python3 run_etsy_pilot.py <run_timestamp>    # uses a specific run directory
"""

import os
import sys
import glob

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metrics import exposure_share_at_k, mean_rank_delta, exposure_gini  # noqa: E402
from generate_audit_report import generate_report  # noqa: E402
from query_set import QUERY_SET_VERSION  # noqa: E402

K = 10  # matches Volume 2 Section 6's E1 threshold definition
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _find_run_dir(run_timestamp: str = None) -> str:
    base = os.path.join(REPO_ROOT, "data", "etsy_pilot_runs")
    if run_timestamp:
        safe_ts = run_timestamp.replace(":", "-")
        run_dir = os.path.join(base, safe_ts)
        if not os.path.isdir(run_dir):
            raise FileNotFoundError(f"No run directory found at {run_dir}")
        return run_dir

    candidates = sorted(glob.glob(os.path.join(base, "*")))
    if not candidates:
        raise FileNotFoundError(
            f"No pilot runs found under {base}/ -- run etsy_pilot_collector.py first."
        )
    return candidates[-1]


def run(run_timestamp: str = None) -> dict:
    run_dir = _find_run_dir(run_timestamp)
    events_df = pd.read_csv(os.path.join(run_dir, "events.csv"))
    sellers_df = pd.read_csv(os.path.join(run_dir, "sellers.csv"))

    results = {"run_dir": run_dir, "query_set_version": QUERY_SET_VERSION, "cohorts": {}}

    for cohort_col in ["seller_size", "seller_tenure"]:
        if cohort_col not in sellers_df.columns or sellers_df[cohort_col].isna().all():
            continue
        es_at_k_df = exposure_share_at_k(events_df, sellers_df, k=K, cohort_col=cohort_col)
        rank_delta_df = mean_rank_delta(events_df, sellers_df, cohort_col=cohort_col)
        gini_by_cohort = {
            cohort_value: exposure_gini(events_df, sellers_df, k=K, cohort_col=cohort_col, cohort_value=cohort_value)
            for cohort_value in sellers_df[cohort_col].dropna().unique()
        }
        results["cohorts"][cohort_col] = {
            "es_at_k": es_at_k_df,
            "mean_rank": rank_delta_df,
            "gini": gini_by_cohort,
        }

    report_path = generate_report(results, events_df, sellers_df)
    print(f"[runner] report written to {report_path}")
    return results


if __name__ == "__main__":
    run_ts_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run(run_ts_arg)
