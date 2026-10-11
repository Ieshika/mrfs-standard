"""
Sample audit report (MRFS Technical Standard, Appendix A) generated from the deterministic synthetic
marketplace. Every number in the report comes from metrics.py applied to
data produced by generate_synthetic_audit.py with the seeds below, so the
report can be regenerated exactly:

    python generate_sample_audit_report.py

Outputs, in sample_audit_report/:
    sample_audit_report.md     the report
    sample_audit_results.json  every figure in the report
    declaration.json           the audit declaration

Scenario (known to the generator, not to the metrics)
    Weeks 1 to 8   ranking version v1, which ignores seller cohort.
    Weeks 9 to 12  ranking version v2, which adds a score penalty to listings
                   of Small sellers and lowers their click probability.
    The audit window is weeks 9 to 12. Tenure cohorts are not penalised.
The report is a demonstration of the method on synthetic data. It is not
evidence about any real marketplace.
"""

import json
import os

import numpy as np
import pandas as pd

import metrics as M
from generate_synthetic_audit import AUDIT_START, generate, make_sellers, default_declaration

SEED = 20260105
N_SELLERS = 2000
EVENTS_PER_WEEK = 1500
WEEKS = 12
CHANGE_WEEK = 9
SMALL_PENALTY_V2 = 0.024
SMALL_CLICK_SCALE_V2 = 0.80
K = 10
OUT = "sample_audit_report"


def build():
    sellers = make_sellers(N_SELLERS, np.random.default_rng(SEED))
    weekly = {}
    for w in range(1, WEEKS + 1):
        v2 = w >= CHANGE_WEEK
        ev, _ = generate(n_events=EVENTS_PER_WEEK, sellers=sellers, seed=SEED + w, event_prefix=f"W{w:02d}_",
                         penalty={"Small": SMALL_PENALTY_V2 if v2 else 0.0},
                         click_scale={"Small": SMALL_CLICK_SCALE_V2} if v2 else None)
        ev["week"] = w
        ev["event_timestamp"] = ev["event_timestamp"] + pd.to_timedelta((w - 1) * 7, unit="D")
        ev["model_version"] = "v2" if v2 else "v1"
        weekly[w] = ev
    return sellers, weekly


def r3(x):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), 3)


REPORT_ID = "MRFS-SAMPLE-2026-W09-W12"
DQ_CRITERIA = {   # pre-specified for this example audit; MRFS sets no universal values
    "max_rows_without_cohort_label_pct": 1.0,
    "max_events_excluded_pct": 1.0,
    "max_events_with_incomplete_top_k_pct": 1.0,
}


def declaration():
    d = default_declaration(k=K)
    d.data_quality_criteria = dict(DQ_CRITERIA)
    d.ordered_depth = 50
    d.windows = {"audit_window": f"weeks {CHANGE_WEEK} to {WEEKS}", "monitoring_window": "1 week",
                 "baseline_windows": 4}
    return d


def run():
    sellers, weekly = build()
    decl = declaration()
    decl.validate()
    audit = pd.concat([weekly[w] for w in range(CHANGE_WEEK, WEEKS + 1)], ignore_index=True)
    prior = pd.concat([weekly[w] for w in range(CHANGE_WEEK - 4, CHANGE_WEEK)], ignore_index=True)
    res = {"report_id": REPORT_ID, "declaration": decl.to_dict(),
           "design": {"seed": SEED, "sellers": N_SELLERS, "events_per_week": EVENTS_PER_WEEK, "weeks": WEEKS,
                      "audit_window_weeks": [CHANGE_WEEK, WEEKS], "audit_start": AUDIT_START,
                      "ranking_events_in_audit_window": int(audit["event_id"].nunique()),
                      "candidate_rows_in_audit_window": int(len(audit))},
           "software": {"metrics": "metrics.py version 2", "numpy": np.__version__, "pandas": pd.__version__}}

    known = set(sellers["seller_id"])
    per_event = audit.groupby("event_id").agg(n=("item_id", "size"), ordered=("rank_position", "count"))
    q = {"rows_without_cohort_label_pct": r3(100 * (~audit["seller_id"].isin(known)).mean()),
         "events_excluded_pct": r3(100 * (per_event["n"] <= K).mean()),
         "events_with_incomplete_top_k_pct": r3(100 * (per_event["ordered"] < K).mean()),
         "candidate_set_size_min_median_max": [int(per_event["n"].min()), int(per_event["n"].median()), int(per_event["n"].max())],
         "ordered_depth_min_max": [int(per_event["ordered"].min()), int(per_event["ordered"].max())]}
    q["criteria_met"] = (q["rows_without_cohort_label_pct"] <= DQ_CRITERIA["max_rows_without_cohort_label_pct"]
                         and q["events_excluded_pct"] <= DQ_CRITERIA["max_events_excluded_pct"]
                         and q["events_with_incomplete_top_k_pct"] <= DQ_CRITERIA["max_events_with_incomplete_top_k_pct"])
    res["data_quality"] = q

    res["cohorts"] = {}
    for col in ("seller_size", "seller_tenure"):
        share_sellers = sellers[col].value_counts(normalize=True)
        cand = audit.merge(sellers[["seller_id", col]], on="seller_id")[col].value_counts(normalize=True)
        res["cohorts"][col] = {c: {"share_of_sellers": r3(share_sellers[c]), "share_of_candidate_listings": r3(cand[c])}
                               for c in share_sellers.index}

    res["E1"], res["E2"], res["E3"] = {}, {}, {}
    for col in ("seller_size", "seller_tenure"):
        e1 = M.exposure_ratio(audit, sellers, k=K, cohort_col=col, seed=SEED)
        st = M.evaluate_statuses(decl, e1)
        res["E1"][col] = [{"cohort": x["cohort"], "E1": r3(x["E1"]), "ci": [r3(x["ci_lower"]), r3(x["ci_upper"])],
                           "status": x["status"]} for x in st["E1"]]
        e2 = M.mean_rank_position(audit, sellers, cohort_col=col, seed=SEED, ordered_depth=decl.ordered_depth)
        res["E2"][col] = [{"cohort": r[col], "E2": r3(r["E2"]), "ci": [r3(r["E2_ci_lower"]), r3(r["E2_ci_upper"])]}
                          for _, r in e2.iterrows()]
        e3 = M.exposure_concentration(audit, sellers, k=K, cohort_col=col)
        res["E3"][col] = [{"cohort": r[col], "E3": r3(r["E3"]), "sellers": int(r["n_sellers"]),
                           "sellers_with_no_top_k": int(r["n_sellers_zero_top_k"])} for _, r in e3.iterrows()]

    res["O"] = []
    for col, d_, r_ in (("seller_size", "Small", "Large"), ("seller_tenure", "New", "Established")):
        o = M.outcome_parity(audit, sellers, k=K, cohort_col=col, disadvantaged=d_, reference=r_, seed=SEED)
        for name, rate in (("ctr", "Click-through rate"), ("cvr", "Conversion rate")):
            lo, hi = o[f"O3_{name}_ci_lower"], o[f"O3_{name}_ci_upper"]
            res["O"].append({"comparison": f"{d_} against {r_}", "outcome": rate,
                             "rate_cohort": r3(o[f"{name}_disadvantaged"]), "rate_reference": r3(o[f"{name}_reference"]),
                             "O3": r3(o[f"O3_{name}"]), "ci": [r3(lo), r3(hi)],
                             "status": M.classify_ci(lo, hi, decl.review_line, decl.monitor_line)})

    res["S1"] = []
    for w in range(5, WEEKS + 1):
        d = M.exposure_drift(weekly[w], [weekly[x] for x in range(w - 4, w)], sellers, "Small", k=K, seed=SEED + w)
        wk = M.exposure_ratio(weekly[w], sellers, k=K, seed=SEED + w).set_index("seller_size").loc["Small"]
        res["S1"].append({"week": w, "version": "v2" if w >= CHANGE_WEEK else "v1",
                          "E1_week": r3(d["E1_current"]), "E1_week_ci": [r3(wk["E1_ci_lower"]), r3(wk["E1_ci_upper"])],
                          "E1_week_status": M.classify_ci(wk["E1_ci_lower"], wk["E1_ci_upper"], decl.review_line, decl.monitor_line),
                          "E1_baseline_mean": r3(d["E1_baseline_mean"]), "S1_pct": r3(d["S1_pct"]),
                          "ci": [r3(d["S1_ci_lower"]), r3(d["S1_ci_upper"])],
                          "status": M.classify_drift_ci(d["S1_ci_lower"], d["S1_ci_upper"],
                                                        decl.drift_monitor_pct, decl.drift_review_pct)})

    res["S2"] = []
    for cohort in ("Small", "Medium", "Large"):
        s2 = M.model_regression(prior, audit, sellers, cohort, k=K, design="independent", seed=SEED)
        res["S2"].append({"cohort": cohort, "E1_v1": r3(s2["E1_current_version"]), "E1_v2": r3(s2["E1_new_version"]),
                          "S2_ratio": r3(s2["S2_ratio"]), "ci": [r3(s2["S2_ci_lower"]), r3(s2["S2_ci_upper"])]})

    # sensitivity: size cohorts from active listing count instead of completed orders
    alt = sellers.copy()
    alt["seller_size"] = M.assign_size_cohorts(alt["listing_count"])
    e1a = M.exposure_ratio(audit, alt, k=K, seed=SEED)
    sta = M.evaluate_statuses(decl, e1a)
    agree = float((alt["seller_size"] == sellers["seller_size"]).mean())
    res["sensitivity"] = {"agreement_of_size_labels": r3(agree),
                          "E1_by_listing_count": [{"cohort": x["cohort"], "E1": r3(x["E1"]),
                                                   "ci": [r3(x["ci_lower"]), r3(x["ci_upper"])], "status": x["status"]}
                                                  for x in sta["E1"]]}
    res["Q"] = "Not evaluated: no fairness mitigation was under evaluation in this audit."
    return res


def fmt_ci(ci):
    return f"{ci[0]:.3f} to {ci[1]:.3f}" if ci[0] is not None else "no interval"


def label(status):
    return {"PASS": "Pass", "MONITOR": "Monitor", "REVIEW_REQUIRED": "Review Required",
            "INSUFFICIENT_DATA": "Insufficient Data", None: "no status"}[status]


def ruled_out(status, ci, review=0.80, monitor=0.85):
    if status != "INSUFFICIENT_DATA" or ci[0] is None:
        return ""
    if ci[1] < monitor:
        return " (Pass ruled out)"
    if ci[0] >= review:
        return " (Review Required ruled out)"
    return ""


def to_markdown(res):
    d, q, dec = res["design"], res["data_quality"], res["declaration"]
    crit = dec["data_quality_criteria"]
    L = []
    a = L.append
    a("# Sample Audit Report (synthetic demonstration)\n")
    a(f"Report identifier: {res['report_id']}. Every figure is produced by `metrics.py` from data generated by "
      "`generate_synthetic_audit.py` and can be regenerated with `python generate_sample_audit_report.py`. "
      "It is not evidence about any real marketplace.\n")
    a("## 1. Audit declaration\n")
    a("| Item | Declared value |\n|---|---|")
    a(f"| Kind of assessment | {dec['audit_mode']} audit |")
    a(f"| Comparison population | {dec['population_type']}: {dec['population_detail']} |")
    a(f"| Stages before the reference stage not captured | {dec['upstream_not_captured']} |")
    a(f"| K; ordered depth for E2 | {dec['k']}; {dec['ordered_depth']} |")
    a(f"| Size cohorts | {dec['cohort_definitions']['seller_size']} |")
    a(f"| Tenure cohorts | {dec['cohort_definitions']['seller_tenure']} |")
    a(f"| Thresholds (E1, O3) | MRFS defaults: Review line {dec['review_line']:.2f}, Monitor line {dec['monitor_line']:.2f}, applied to the whole 95% interval |")
    a(f"| Thresholds (S1) | MRFS defaults: Monitor line {dec['drift_monitor_pct']:.0f}%, Review line {dec['drift_review_pct']:.0f}% |")
    a(f"| Data-quality acceptance criteria | rows without a cohort label at most {crit['max_rows_without_cohort_label_pct']}%; "
      f"events excluded at most {crit['max_events_excluded_pct']}%; events with an incomplete top K at most "
      f"{crit['max_events_with_incomplete_top_k_pct']}% |")
    a(f"| Windows | audit window {dec['windows']['audit_window']}; monitoring window {dec['windows']['monitoring_window']}; "
      f"{dec['windows']['baseline_windows']} baseline windows |")
    a(f"| Resampling unit; strata | {dec['resampling_unit']}; {dec['strata']} |")
    a(f"| Declaration fixed on | {dec['fixed_on']} |\n")
    a("Statuses apply to the declared candidate stage only. A status indicates a potential disparity that calls for "
      "investigation; it does not establish unfair treatment or its cause.\n")
    a("## 2. Data\n")
    a(f"- Audit window: weeks {d['audit_window_weeks'][0]} to {d['audit_window_weeks'][1]} "
      f"({d['ranking_events_in_audit_window']:,} ranking events, {d['candidate_rows_in_audit_window']:,} candidate rows); "
      "all events used, no sampling.")
    a(f"- Monitoring history: {d['weeks']} weeks at {d['events_per_week']:,} ranking events per week; {d['sellers']:,} sellers.")
    a(f"- Candidate set size per event: minimum {q['candidate_set_size_min_median_max'][0]}, median "
      f"{q['candidate_set_size_min_median_max'][1]}, maximum {q['candidate_set_size_min_median_max'][2]}; "
      f"ordered depth {q['ordered_depth_min_max'][0]} to {q['ordered_depth_min_max'][1]}.")
    a(f"- Rows without a cohort label: {q['rows_without_cohort_label_pct']}%. Events excluded because the candidate set "
      f"was no larger than K: {q['events_excluded_pct']}%. Events with an incomplete top K: {q['events_with_incomplete_top_k_pct']}%. "
      f"Declared criteria: {'met' if q['criteria_met'] else 'not met'}. No Unassigned group arises.\n")
    a("| Cohort | Share of sellers | Share of candidate listings |\n|---|---|---|")
    for col in ("seller_size", "seller_tenure"):
        for c, v in res["cohorts"][col].items():
            a(f"| {c} | {v['share_of_sellers']:.1%} | {v['share_of_candidate_listings']:.1%} |")
    a("")
    a("## 3. Exposure\n")
    a("### E1, exposure ratio at 10\n")
    a("| Cohort | E1 | 95% interval | Status |\n|---|---|---|---|")
    for col in ("seller_size", "seller_tenure"):
        for x in res["E1"][col]:
            a(f"| {x['cohort']} | {x['E1']:.3f} | {fmt_ci(x['ci'])} | {label(x['status'])}{ruled_out(x['status'], x['ci'])} |")
    a("")
    a("### E2, mean rank position (normalised; lower is better; 0.5 is the reference midpoint; no status)\n")
    a("| Cohort | E2 | 95% interval |\n|---|---|---|")
    for col in ("seller_size", "seller_tenure"):
        for x in res["E2"][col]:
            a(f"| {x['cohort']} | {x['E2']:.3f} | {fmt_ci(x['ci'])} |")
    a("")
    a("### E3, exposure concentration (Gini of top-10 positions across sellers in the comparison population; no status)\n")
    a("| Cohort | E3 | Sellers | Sellers with no top-10 position |\n|---|---|---|---|")
    for col in ("seller_size", "seller_tenure"):
        for x in res["E3"][col]:
            if col == "seller_tenure" and x["cohort"] == "All sellers":
                continue
            a(f"| {x['cohort']} | {x['E3']:.3f} | {x['sellers']:,} | {x['sellers_with_no_top_k']:,} |")
    a("")
    a("## 4. Outcomes (top-10 impressions)\n")
    a("| Comparison | Outcome | Cohort rate | Reference rate | O3 | 95% interval | Status |\n|---|---|---|---|---|---|---|")
    for x in res["O"]:
        a(f"| {x['comparison']} | {x['outcome']} | {x['rate_cohort']:.3f} | {x['rate_reference']:.3f} | {x['O3']:.3f} | "
          f"{fmt_ci(x['ci'])} | {label(x['status'])}{ruled_out(x['status'], x['ci'])} |")
    a("")
    a("## 5. Stability\n")
    a("### Weekly monitoring of Small sellers: E1 for the week (level) and S1 against the mean of the four preceding weeks (change)\n")
    a("| Week | Version | E1 | E1 interval | E1 status | Baseline mean | S1 | S1 interval | S1 status |\n|---|---|---|---|---|---|---|---|---|")
    for x in res["S1"]:
        a(f"| {x['week']} | {x['version']} | {x['E1_week']:.3f} | {fmt_ci(x['E1_week_ci'])} | {label(x['E1_week_status'])} | "
          f"{x['E1_baseline_mean']:.3f} | {x['S1_pct']:+.1f}% | {x['ci'][0]:+.1f}% to {x['ci'][1]:+.1f}% | {label(x['status'])} |")
    a("")
    a("### S2, model regression (v2 in weeks 9 to 12 against v1 in weeks 5 to 8; no status)\n")
    a("The two versions were observed in different weeks, so this comparison is confounded with time.\n")
    a("| Cohort | E1 under v1 | E1 under v2 | Ratio | 95% interval |\n|---|---|---|---|---|")
    for x in res["S2"]:
        a(f"| {x['cohort']} | {x['E1_v1']:.3f} | {x['E1_v2']:.3f} | {x['S2_ratio']:.3f} | {fmt_ci(x['ci'])} |")
    a("")
    a("## 6. Quality guardrails\n")
    a(res["Q"] + "\n")
    s = res["sensitivity"]
    a("## 7. Sensitivity check: size cohorts by active listing count\n")
    a(f"Size cohorts recomputed from active listing count instead of completed orders. "
      f"{s['agreement_of_size_labels']:.1%} of sellers keep the same size label.\n")
    a("| Cohort (by listing count) | E1 | 95% interval | Status |\n|---|---|---|---|")
    for x in s["E1_by_listing_count"]:
        a(f"| {x['cohort']} | {x['E1']:.3f} | {fmt_ci(x['ci'])} | {label(x['status'])}{ruled_out(x['status'], x['ci'])} |")
    a("")
    a("## 8. What the generator did\n")
    a(f"For checking the result against the truth: ranking version v2 (weeks {CHANGE_WEEK} to {WEEKS}) added a score "
      f"penalty of {SMALL_PENALTY_V2} to listings of Small sellers, as defined by completed orders, and multiplied their "
      f"click probability by {SMALL_CLICK_SCALE_V2}. Version v1 ignored cohort. Tenure was never used by either version. "
      f"The observed click-through ratio is lower than {SMALL_CLICK_SCALE_V2} because penalised listings also sit lower "
      "within the top 10, where click probability is lower: O1 to O3 are not adjusted for position.\n")
    sw = res["software"]
    a("## Appendix\n")
    a("- Formulas: MRFS Technical Standard, Sections 2.2 to 2.4. Statuses: Section 2.6. Intervals: 95% percentile bootstrap "
      "over ranking events, 1,000 resamples (Section 2.7).")
    a(f"- Software: {sw['metrics']}; numpy {sw['numpy']}; pandas {sw['pandas']}.")
    a(f"- Seeds: catalogue and weekly data from seed {d['seed']} (week w uses {d['seed']} + w); bootstrap seed {d['seed']}.")
    return "\n".join(L)


if __name__ == "__main__":
    results = run()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "sample_audit_results.json"), "w") as f:
        json.dump(results, f, indent=1)
    with open(os.path.join(OUT, "declaration.json"), "w") as f:
        json.dump(results["declaration"], f, indent=1)
    with open(os.path.join(OUT, "sample_audit_report.md"), "w") as f:
        f.write(to_markdown(results))
    print(to_markdown(results))
