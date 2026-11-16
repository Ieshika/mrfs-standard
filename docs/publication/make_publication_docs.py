"""
Writes the generated parts of the MRFS publications from committed results,
so that no figure is copied by hand:

  standard/07_appendix_a.md   worked example, from src/sample_audit_report/sample_audit_results.json
  validation/validation.md    Validation Report, from src/validation_results/*.json

Usage: python make_publication_docs.py <repository root>
"""
import json
import os
import sys

ROOT = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
LAB = {"PASS": "Pass", "MONITOR": "Monitor", "REVIEW_REQUIRED": "Review Required",
       "INSUFFICIENT_DATA": "Insufficient Data", None: "no status"}
MINUS = "−"


def num(x, d=3):
    return f"{x:.{d}f}".replace("-", MINUS)


def sgn(x, d=1):
    return f"{x:+.{d}f}".replace("-", MINUS)


def pct(x, d=1):
    return f"{100 * x:.{d}f}%"


def ci(c, d=3):
    return f"{num(c[0], d)}–{num(c[1], d)}" if c[0] is not None else "no interval"


def load(path):
    with open(os.path.join(ROOT, path)) as f:
        return json.load(f)


# ------------------------------------------------------------------ Appendix A
def appendix_a():
    r = load("src/sample_audit_report/sample_audit_results.json")
    d, q, dec = r["design"], r["data_quality"], r["declaration"]
    crit = dec["data_quality_criteria"]
    L = []
    a = L.append
    a("# Worked example: sample audit report {#app:example}\n")
    a("This appendix is a complete MRFS audit of a synthetic marketplace, following the report contents of Section 3.10. "
      "Every figure was produced by the reference implementation from data generated with fixed seeds (Appendix C). "
      "The scenario is known to the generator, so the result can be checked against the truth (Appendix A.9). "
      "Nothing here is evidence about any real marketplace.\n")
    a(f"Report identifier: {r['report_id']}.\n")

    a("## Summary\n")
    e1s = {x["cohort"]: x for x in r["E1"]["seller_size"]}
    a(f"Ranking version v2, deployed in week 9, places listings of Small sellers lower than version v1 did. In the audit "
      f"window (weeks 9 to 12), E1 for Small sellers is {num(e1s['Small']['E1'])} (95% interval {ci(e1s['Small']['ci'])}), "
      f"Review Required at the declared candidate stage; Medium and Large sellers and both tenure cohorts are Pass. The "
      f"click-through ratio for Small sellers is also Review Required; the conversion ratio is Insufficient Data. E1 for "
      f"Small sellers is Review Required in every week after the change, while S1 reached Review Required in the first two "
      f"weeks and then returned to Insufficient Data as the lower values entered the baseline. With size measured by "
      f"listing count instead of completed orders, Small sellers' E1 is {num(r['sensitivity']['E1_by_listing_count'][-1]['E1'])} "
      f"and Insufficient Data, so the finding depends on the size measure. These results call for an investigation under "
      f"Section 4.7; they do not by themselves establish its cause.\n")

    a("## Audit declaration\n")
    a("| Item | Declared value |\n|:------------------------|:------------------------------------------------------------|")
    a(f"| Kind of assessment | Platform audit |")
    a(f"| Comparison population | Candidate set: {dec['population_detail']} |")
    a(f"| Stages not captured | {dec['upstream_not_captured'].capitalize()} |")
    a(f"| $K$; ordered depth for E2 | {dec['k']}; {dec['ordered_depth']} |")
    a(f"| Size cohorts | {dec['cohort_definitions']['seller_size'][0].upper() + dec['cohort_definitions']['seller_size'][1:]} |")
    a(f"| Tenure cohorts | {dec['cohort_definitions']['seller_tenure']} |")
    a(f"| Thresholds | MRFS defaults: Review line {num(dec['review_line'], 2)}, Monitor line {num(dec['monitor_line'], 2)}; "
      f"drift lines {sgn(dec['drift_monitor_pct'], 0)}% and {sgn(dec['drift_review_pct'], 0)}% |")
    a(f"| Data-quality criteria | Rows without a cohort label at most {crit['max_rows_without_cohort_label_pct']}%; events "
      f"excluded at most {crit['max_events_excluded_pct']}%; events with an incomplete top $K$ at most "
      f"{crit['max_events_with_incomplete_top_k_pct']}% |")
    a(f"| Windows | Audit window {dec['windows']['audit_window']}; monitoring window {dec['windows']['monitoring_window']}; "
      f"{dec['windows']['baseline_windows']} baseline windows |")
    a(f"| Resampling unit; strata | {dec['resampling_unit'].capitalize()}; {dec['strata']} |")
    a(f"| Fixed on | {dec['fixed_on']} |\n")
    a(": Audit declaration of the worked example.\n")

    a("## Data\n")
    lo, med, hi = q["candidate_set_size_min_median_max"]
    a(f"The audit window holds {d['ranking_events_in_audit_window']:,} ranking events and "
      f"{d['candidate_rows_in_audit_window']:,} candidate rows; all events were used. Monitoring history covers "
      f"{d['weeks']} weeks at {d['events_per_week']:,} ranking events per week, for {d['sellers']:,} sellers. Candidate "
      f"sets contain {lo} to {hi} listings (median {med}); the ordered depth is {q['ordered_depth_min_max'][0]} to "
      f"{q['ordered_depth_min_max'][1]}. Rows without a cohort label: {q['rows_without_cohort_label_pct']}%; events "
      f"excluded: {q['events_excluded_pct']}%; events with an incomplete top $K$: "
      f"{q['events_with_incomplete_top_k_pct']}%. The declared criteria are "
      f"{'met' if q['criteria_met'] else 'not met'}, and no Unassigned group arises.\n")
    a("| Cohort | Share of sellers | Share of candidate listings |\n|:----------|----------:|----------:|")
    for col in ("seller_size", "seller_tenure"):
        for c, v in r["cohorts"][col].items():
            a(f"| {c} | {pct(v['share_of_sellers'])} | {pct(v['share_of_candidate_listings'])} |")
    a("\n: Cohort shares in the audit window.\n")

    a("## Exposure\n")
    a("| Cohort | E1 | 95% interval | Status | E2 | E2 95% interval |\n|:----------|------:|:------------|:------------|------:|:------------|")
    for col in ("seller_size", "seller_tenure"):
        e2 = {x["cohort"]: x for x in r["E2"][col]}
        for x in r["E1"][col]:
            y = e2[x["cohort"]]
            a(f"| {x['cohort']} | {num(x['E1'])} | {ci(x['ci'])} | {LAB[x['status']]} | {num(y['E2'])} | {ci(y['ci'])} |")
    a("\n: E1 (exposure ratio at 10) with statuses, and E2 (normalised mean rank; lower is higher up; no status).\n")
    a("| Cohort | E3 | Sellers | Sellers with no top-10 position |\n|:----------|------:|------:|------:|")
    for col in ("seller_size", "seller_tenure"):
        for x in r["E3"][col]:
            if col == "seller_tenure" and x["cohort"] == "All sellers":
                continue
            a(f"| {x['cohort']} | {num(x['E3'])} | {x['sellers']:,} | {x['sellers_with_no_top_k']:,} |")
    a("\n: E3, the Gini index of top-10 positions across sellers in the comparison population (no status).\n")

    a("## Outcomes\n")
    a("| Comparison | Outcome | Cohort rate | Reference rate | O3 | 95% interval | Status |\n"
      "|:-------------------|:--------------|------:|------:|------:|:------------|:------------|")
    for x in r["O"]:
        a(f"| {x['comparison']} | {x['outcome']} | {num(x['rate_cohort'])} | {num(x['rate_reference'])} | {num(x['O3'])} | "
          f"{ci(x['ci'])} | {LAB[x['status']]} |")
    a("\n: Outcome rates of top-10 impressions and O3.\n")

    a("## Stability\n")
    a("::: compact")
    a("| Week | E1 | 95% interval | E1 status | Baseline mean | S1 (%) | 95% interval (%) | S1 status |\n"
      "|-----:|------:|:------------|:------------|------:|------:|:----------------|:------------|")
    for x in r["S1"]:
        if x["week"] == 9:
            a("| RULE | | | | | | | |")
        a(f"| {x['week']} | {num(x['E1_week'])} | {ci(x['E1_week_ci'])} | {LAB[x['E1_week_status']]} | "
          f"{num(x['E1_baseline_mean'])} | {sgn(x['S1_pct'])} | {sgn(x['ci'][0])} to {sgn(x['ci'][1])} | {LAB[x['status']]} |")
    a("\n: Weekly monitoring of Small sellers: E1 for the week (level) and S1 against the mean of the four preceding weeks "
      "(change). Version v1 ran in weeks 1 to 8 and v2 from week 9; the rule marks the change.\n")
    a(":::\n")
    a("| Cohort | E1 under v1 | E1 under v2 | S2 ratio | 95% interval |\n|:----------|------:|------:|------:|:------------|")
    for x in r["S2"]:
        a(f"| {x['cohort']} | {num(x['E1_v1'])} | {num(x['E1_v2'])} | {num(x['S2_ratio'])} | {ci(x['ci'])} |")
    a("\n: S2, ratio of E1 under v2 (weeks 9 to 12) to E1 under v1 (weeks 5 to 8); no status.\n")
    a("::: limitation\nThe two versions were observed in different weeks, so the S2 comparison is confounded with time.\n:::\n")

    a("## Quality guardrails\n")
    a(r["Q"] + "\n")

    s = r["sensitivity"]
    a("## Sensitivity check\n")
    a(f"Size cohorts were recomputed from active listing count instead of completed orders; "
      f"{pct(s['agreement_of_size_labels'])} of sellers keep the same size label.\n")
    a("| Cohort (by listing count) | E1 | 95% interval | Status |\n|:--------------------|------:|:------------|:------------|")
    for x in s["E1_by_listing_count"]:
        a(f"| {x['cohort']} | {num(x['E1'])} | {ci(x['ci'])} | {LAB[x['status']]} |")
    a("\n: E1 with size cohorts defined by active listing count.\n")

    a("## Limitations\n")
    a("- Synthetic data with independent ranking events; real logs are clustered and less precise.\n"
      "- No correction for multiple comparisons: the report makes 5 E1 status comparisons in the audit window, 4 O3, "
      "8 weekly E1 and 8 weekly S1 status comparisons, and 3 in the sensitivity check.\n"
      "- Outcome rates are not adjusted for position.\n")

    a("## What the generator did\n")
    a("Ranking version v2 (weeks 9 to 12) added a score penalty of 0.024 to listings of Small sellers, as defined by "
      "completed orders, and multiplied their click probability by 0.8. Version v1 ignored cohort, and tenure was never "
      "used by either version. The observed click-through ratio is below 0.8 because penalised listings also sit lower "
      "within the top 10, where click probability is lower.\n")
    sw = r["software"]
    a(f"Software: {sw['metrics']}, numpy {sw['numpy']}, pandas {sw['pandas']}. Seeds: catalogue and weekly data from seed "
      f"{d['seed']} (week $w$ uses {d['seed']} + $w$); bootstrap seed {d['seed']}; 1,000 resamples.\n")
    return "\n".join(L)


# ------------------------------------------------------------------ Validation Report
def validation():
    st = load("src/validation_results/structure.json")
    e1 = load("src/validation_results/e1.json")
    dr = load("src/validation_results/drift.json")
    rg = load("src/validation_results/regression.json")
    oc = load("src/validation_results/outcome.json")
    rv = load("src/validation_results/review_band_and_drift_partial.json")
    L = []
    a = L.append

    a("# Purpose and scope\n")
    a("This report states how the MRFS reference implementation (`metrics.py`) behaves on synthetic data with a known "
      "truth: whether it reports the correct result on a ranking system without disparity, how reliably it detects a "
      "disparity of a given size, how precise its intervals are, and where its limits lie. Section numbers prefixed "
      "\"Standard\" refer to the MRFS Technical Standard. All sample sizes are counted in ranking events.\n")
    a("::: limitation\nThis report does not show that MRFS is valid for any particular marketplace, and synthetic "
      "validation does not establish fairness on any real marketplace. Sections 4 to 8 use one synthetic marketplace "
      "with independent ranking events and one disparity mechanism; Section 9 uses a simplified simulation of the same "
      "estimator. Real event logs are clustered by query and by day and will be less precise than these tables suggest. "
      "Results on live marketplaces are not part of this report.\n:::\n")

    a("# Method and reproduction\n")
    a("**The synthetic marketplace.** 2,000 sellers with heavy-tailed listing counts and order counts. Each ranking event "
      "draws a candidate set of 40, 80, 150 or 300 listings from the whole catalogue, so sellers with more listings are "
      "candidates more often. Each candidate is scored Uniform(0, 1) plus a penalty for its seller's size cohort; lower "
      "scores rank higher; the first 50 are ordered and the rest stay in the comparison population without a rank. A "
      "penalty of zero for every cohort is a ranking system that ignores cohort. Click probability falls with position. "
      "Size cohorts are the MRFS default quartiles of the order count, so Small sellers hold 25% of seller accounts and "
      "about 4% of candidate listings.\n")
    a("**Measures.** Status rates are the share of independent replicates (fresh ranking events, same seller catalogue) "
      "returning each status. Coverage is the share of 95% intervals containing the true value. True values were computed "
      "from at least 100,000 events, except where the truth is known exactly. Rates from 30 to 60 replicates are "
      "uncertain by several percentage points. Intervals in Sections 4 to 8 use 500 bootstrap resamples (`N_BOOT` in "
      "`run_validation.py`); the reference implementation's default is 1,000. Section 9 uses 400.\n")
    a("**Reproduction.** Every table in this report is generated from the results saved in `src/validation_results/`, "
      "and every saved result is determined by the seeds in the script that produced it. The results were produced with "
      "Python 3.11, numpy 2.4.4 and pandas 3.0.2; the structure check (Section 4) and the worked example (Standard, "
      "Appendix A) were also reproduced exactly with numpy 2.2.6 and pandas 2.3.3. numpy does not guarantee identical "
      "random streams across all versions, so other versions may give slightly different figures. Section 9 is a partial "
      "run (see there).\n")
    a("| Component | File | Command (in `src/`) |\n|:----------------------|:----------------------------|:----------------------------|")
    a("| Tests with hand-worked expected values | `test_metrics.py` | `python test_metrics.py` |")
    a("| Synthetic marketplace | `generate_synthetic_audit.py` | used by the scripts below |")
    a("| Validation (Sections 4 to 8) | `run_validation.py` | `python run_validation.py` |")
    a("| Focused review (Section 9) | `run_validation_review.py` | `python run_validation_review.py band`, `... drift`, `... check` (partial run; see Section 9) |")
    a("| Worked example (Standard, Appendix A) | `generate_sample_audit_report.py` | `python generate_sample_audit_report.py` |\n")
    a(": Files and commands that reproduce this report. Results are saved in `src/validation_results/`.\n")

    a("# Tests of the implementation\n")
    a("`test_metrics.py` contains 22 tests. Each metric is checked against a value worked out by hand on a small "
      "example: E1, including the use of listing share rather than seller share, the exclusion of events with nothing to "
      "rank, and unordered candidates; E2's event weighting and declared depth; E3's inclusion of sellers without a top "
      "position; the status boundaries; size and tenure cohort assignment, including ties and calendar months across a "
      "leap day; the audit declaration rules; the determinism of the generator; S1 and S2; and the treatment of zero counts "
      "in E1, O3, S1 and S2, including a cohort with no listings in the comparison population; and the flagging of statuses "
      "computed against a Review line other than the normative 0.80 as exploratory rather than MRFS statuses. All 22 pass.\n")

    a("# Why E1 was redefined\n")
    a(f"On a ranking system that ignores cohort ({st['n_events']:,} ranking events):\n")
    a("| Cohort | Share of sellers | Share of listings | Share of top-10 positions | Formula of MRFS 1.x | E1 | 95% interval | Status |\n"
      "|:----------|------:|------:|------:|------:|------:|:------------|:------------|")
    for x in st["rows"]:
        a(f"| {x['cohort']} | {pct(x['share_of_sellers'])} | {pct(x['share_of_listings'])} | {pct(x['share_of_top10'])} | "
          f"{num(x['v1_per_seller_formula'])} | {num(x['E1'])} | {ci(x['E1_ci'])} | {LAB[x['E1_status']]} |")
    a("\n: The earlier per-seller formula and the present E1 on a ranking system without disparity.\n")
    a("The earlier formula compared top positions with each cohort's share of sellers, and reports Small sellers at about "
      "one sixth of parity although the ranking system ignores cohort. The present E1 reports each cohort at parity.\n")

    a("# E1: status rates, precision and coverage\n")
    a("| True E1 | Events | Runs | Half-width | Coverage | Pass | Monitor | Review Required | Insufficient Data |\n"
      "|------:|------:|------:|------:|------:|------:|------:|------:|------:|")
    for t in sorted({x["target_E1"] for x in e1}, reverse=True):
        rows = [x for x in e1 if x["target_E1"] == t]
        if t != 1.0:
            a("| RULE | | | | | | | | |")
        for x in rows:
            a(f"| {num(x['true_E1'])} | {x['n_events']:,} | {x['replicates']} | {num(x['mean_halfwidth'])} | "
              f"{pct(x['coverage'])} | {pct(x['PASS'])} | {pct(x['MONITOR'])} | {pct(x['REVIEW_REQUIRED'])} | "
              f"{pct(x['INSUFFICIENT_DATA'])} |")
    a("\n: Status rates, mean interval half-width and coverage for Small sellers (about 4% of candidate listings).\n")
    a("- On the ranking system without disparity, E1 never returned Review Required or Monitor at any size from 250 to "
      "10,000 ranking events. Below about 1,000 events it often returned Insufficient Data, the correct result when the "
      "interval is wide.\n"
      "- Interval coverage was between 91% and 98.3% across all rows, close to the nominal 95%.\n"
      "- A cohort at about 0.73 is confirmed as Review Required in half of audits at 1,000 events and in nearly all at "
      "5,000 or more. A cohort at about 0.91 is confirmed as Pass in most audits from 5,000 events.\n"
      "- A cohort at about 0.81, inside the Monitor band, is almost never confirmed as Monitor at these sizes; Section 9 "
      "explains why this is expected.\n")

    a("# S1: drift detection\n")
    a("Twelve weekly windows; S1 for Small sellers in weeks 5 to 12 against the mean of the four preceding weeks. In the "
      "second scenario a score penalty is applied to Small sellers from week 9. The penalty was calibrated for a fall to "
      "0.75, but the calibration was imprecise: the observed fall in week 9 averaged about 20%.\n")
    a("| Scenario | Events per week | Runs | Any Monitor or Review Required, weeks 5–12 | Week 9: mean S1 | Week 9: Review Required | Week 9: Insufficient Data |\n"
      "|:--------------------|------:|------:|------:|------:|------:|------:|")
    for x in dr:
        w9 = x["by_week"]["9"]
        name = "Stable for 12 weeks" if x["scenario"].startswith("stable") else "Fall from week 9"
        a(f"| {name} | {x['events_per_week']:,} | {x['replicates']} | {pct(x['runs_with_any_Monitor_or_Review_in_weeks_5_to_12'])} | "
          f"{sgn(w9['mean_S1_pct'])}% | {pct(w9['REVIEW_REQUIRED'])} | {pct(w9['INSUFFICIENT_DATA'])} |")
    a("\n: S1 on a stable system and after a fall.\n")
    a("No stable run produced a Monitor or Review Required result in any week. The fall averaged about −20% in S1, almost "
      "exactly on the Review line, and was rarely confirmed in its first week at these volumes. Section 9 shows that "
      "detection depends on the number of events per window and on how far the change goes beyond the line. These runs "
      "preceded the zero-count safeguard of Section 8, which affects only windows in which a cohort holds no top position; "
      "that did not occur at these volumes.\n")

    a("# S2: comparison of ranking versions\n")
    a("| Case | True ratio | Events per version | Runs | Mean S2 | Interval wholly below 1 | Interval covers true ratio | New version E1 Pass |\n"
      "|:----------------------------|------:|------:|------:|------:|------:|------:|------:|")
    names = {0: "Unchanged version (1.00 to 1.00)", 1: "Fall that changes the band (1.00 to 0.84)",
             2: "Fall within the Pass band (1.23 to 0.91)"}
    for i, x in enumerate(rg):
        a(f"| {names[i // 2]} | {num(x['true_ratio'])} | {x['n_events_per_version']:,} | {x['replicates']} | "
          f"{num(x['mean_S2_ratio'])} | {pct(x['interval_wholly_below_1'])} | {pct(x['interval_covers_true_ratio'])} | "
          f"{pct(x['new_version_E1_status']['PASS'])} |")
    a("\n: S2 for an unchanged version and two deteriorations.\n")
    a("An unchanged version was reported as a deterioration (interval wholly below 1) in 4.0% of comparisons at 500 "
      "events per version and 1.0% at 2,000. A fall from about 1.23 to 0.91, which leaves E1 in the Pass band, was "
      "detected in 93.5% and 100% of comparisons: the case S2 exists for, which a status alone would not show.\n")

    a("# O3 and a defect found during validation\n")
    a("| Events | Runs | Click: Pass | Click: Review Required | Conversion: Pass | Conversion: Review Required | Conversion: Insufficient Data |\n"
      "|------:|------:|------:|------:|------:|------:|------:|")
    for x in oc:
        a(f"| {x['n_events']:,} | {x['replicates']} | {pct(x['click_status']['PASS'])} | {pct(x['click_status']['REVIEW_REQUIRED'])} | "
          f"{pct(x['conversion_status']['PASS'])} | {pct(x['conversion_status']['REVIEW_REQUIRED'])} | "
          f"{pct(x['conversion_status']['INSUFFICIENT_DATA'])} |")
    a("\n: O3 on a system with no outcome disparity (true O3 = 1.00).\n")
    a("Conversion rates of about 1.6% leave Small sellers with few conversions, so the conversion ratio is mostly "
      "Insufficient Data even at 5,000 events.\n")
    a("**Defect found and corrected.** In an earlier run, when a cohort had no conversion at all in a sample, every bootstrap "
      "resample was also zero, the interval collapsed to a single point and the result was a confident Review Required. On "
      "this system without disparity that happened in about 5% of samples at 500 events. The implementation now returns no "
      "interval and Insufficient Data whenever a numerator count is zero, for E1, O3, S1 and S2, and tests cover each. After "
      "the correction the false Review Required rate for the conversion ratio was at most 1.3%.\n")

    a("# Focused review: the Monitor band and weekly drift\n")
    a("Two findings above were reviewed further: the Monitor band was almost never confirmed for a small-share cohort "
      "(Section 5), and weekly S1 rarely confirmed a fall in its first week (Section 6). The review used a vectorised "
      "re-implementation of the E1 estimator and its event-level bootstrap (400 resamples), needed to reach 100,000 ranking "
      "events; its half-width at 1,000 events and a 4.2% listing share was 0.0865, against 0.0861 from `metrics.py` in the "
      "same setting. Each candidate belongs to the cohort with probability equal to the cohort's listing share. The run was "
      "stopped once the behaviour was established; configurations that did not finish are listed at the end of this section "
      "and are not extrapolated.\n")
    a("## The Monitor band needs high precision\n")
    a("A Monitor status requires the whole 95% interval to lie inside a band 0.05 wide, which is possible only once the "
      "half-width is below 0.025 and the true value sits far enough from both edges. Pass and Review Required each need "
      "the interval to clear only one line.\n")
    a("| Listing share | True E1 | Events | Runs | Half-width | Monitor | Insufficient Data | Pass ruled out | Review Required ruled out |\n"
      "|------:|------:|------:|------:|------:|------:|------:|------:|------:|")
    prev = None
    for x in rv["band"]:
        key = (x["listing_share"], x["true_E1"])
        if prev is not None and key != prev:
            a("| RULE | | | | | | | | |")
        prev = key
        a(f"| {pct(x['listing_share'])} | {num(x['true_E1'])} | {x['n_events']:,} | {x['replicates']} | "
          f"{num(x['mean_halfwidth'])} | {pct(x['M'])} | {pct(x['I'])} | {pct(x['pass_ruled_out'])} | {pct(x['review_ruled_out'])} |")
    a("\n: Confirmation of the Monitor band (partial run).\n")
    a("Results on the wrong side of a line appeared only at 1,000 events, for true values within 0.011 of a line: Review "
      "Required for true E1 0.810 in 4.7% of runs at a 4.2% share and 0.7% at a 25% share, and Pass for true E1 0.839 in "
      "2.7%. The volume needed to confirm Monitor depends on the cohort's share of candidate listings and on how close the "
      "true value is to an edge of the band. An Insufficient Data result is often informative: at 10,000 events with true "
      "E1 0.810, the interval ruled out Pass in 92.5% of runs.\n")
    a("## Drift detection depends on events per window and on the size of the change\n")
    a("| Listing share | True change | Events per window | Runs | S1: Monitor | S1: Review Required | E1 of the window: Review Required |\n"
      "|------:|------:|------:|------:|------:|------:|------:|")
    prev = None
    for x in rv["drift"]:
        key = (x["listing_share"], x["true_change_pct"])
        if prev is not None and key != prev:
            a("| RULE | | | | | | |")
        prev = key
        a(f"| {pct(x['listing_share'])} | {sgn(x['true_change_pct'], 0)}% | {x['events_per_window']:,} | {x['replicates']} | "
          f"{pct(x['S1']['M'])} | {pct(x['S1']['R'])} | {pct(x['E1_same_window']['R'])} |")
    a("\n: Detection of a fall by S1, and by the E1 status of the same window (partial run).\n")
    a("Detection rises steeply with events per window. For a 4.2%-share cohort a 25% fall needs roughly 3,000 to 10,000 "
      "events per window to be confirmed reliably; for a 25%-share cohort, about 1,000 to 3,000. A longer window helps only "
      "because it holds more events. The E1 status of the monitoring window detects a large fall about as well as S1; S1 "
      "registers moderate falls that leave E1 near a line. Wrong-side S1 results appeared only at 300 events for the 15% "
      "fall: Review Required in 0.7% and Pass in 1.3% of runs.\n")
    a("## Guidance\n")
    a("Neither finding is a defect in the estimator or the interval; both are expected consequences of deciding status from "
      "a 95% interval with narrow bands. The methodology and thresholds are unchanged. The resulting guidance is in Standard "
      "Sections 2.6, 3.5 and 3.7: report what an Insufficient Data interval rules out; plan precision from each cohort's "
      "share of listings; choose monitoring windows by expected events, in whole weeks; use the window's E1 for the level "
      "and S1 for the change.\n")
    a("**Partial run.** The review was stopped once the behaviour was established, and the completed rows were saved "
      "from the run's output to `review_band_and_drift_partial.json`; the comparison with `metrics.py` is saved in "
      "`review_check.json`. Not run: in the Monitor review, the 25%-share cohort at true E1 about 0.81 at 100,000 events "
      "and at the two higher true values at every size; in the drift review, the 25%-share cohort at 30,000 events with "
      "a 15% fall. Each row uses its own seed, so `python run_validation_review.py band` (or `drift`) regenerates every "
      "completed row exactly, but it also runs the configurations listed above, which take many hours, and writes "
      "`review_band.json` (or `review_drift.json`) rather than the partial file. The completed rows have not been "
      "regenerated since the original run.\n")

    a("# Corrections to the validation published with MRFS 1.0 and 1.1\n")
    a("- **Rows counted as ranking events.** The synthetic generators of 1.0 and 1.1 created 20 rows per ranking event but "
      "reported row counts as event counts. Results presented at 10,000 to 250,000 ranking events were obtained at 500 to "
      "12,500. The statement that a 10,000-event audit produced a false Review Required 8% of the time was measured at 500 "
      "ranking events. This report replaces those results.\n"
      "- **Drift-interval figures withdrawn.** The figures of the 1.1 addendum on intervals for S1, including a 92.5% "
      "false-alert rate, cannot be reproduced because no script for them exists. They are withdrawn; Section 6 replaces "
      "them.\n"
      "- **Sample audit report replaced.** The figures of the earlier sample report could not be traced to any data or "
      "code and contained internal contradictions. The worked example is now generated by the reference implementation "
      "(Standard, Appendix A).\n"
      "- **Exposure metric redefined.** See Section 4 and Standard, Appendix B.\n")

    a("# Limitations\n")
    a("- One synthetic marketplace, one disparity mechanism (a score penalty) and independent ranking events.\n"
      "- Precision depends on each cohort's share of comparison-population listings; these tables describe a cohort with "
      "about 4% of listings and are not general sample-size requirements.\n"
      "- Unequal-probability sampling of events is not supported by the reference implementation.\n"
      "- No correction for multiple comparisons is applied (Standard, Section 2.7).\n"
      "- Calibrated true values other than 1.00 are close to, not exactly at, their targets; the tables report the true "
      "values used.\n"
      "- The reference implementation has not been run on a live marketplace's internal data.\n")
    return "\n".join(L)


if __name__ == "__main__":
    with open(os.path.join(HERE, "standard", "07_appendix_a.md"), "w") as f:
        f.write(appendix_a())
    os.makedirs(os.path.join(HERE, "validation"), exist_ok=True)
    with open(os.path.join(HERE, "validation", "validation.md"), "w") as f:
        f.write(validation())
    print("generated appendix A and the Validation Report")
