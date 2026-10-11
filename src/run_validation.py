"""
Synthetic validation of metrics.py (version 2). All sizes are ranking events.

Usage:  python run_validation.py [section ...]     sections: structure e1 drift regression outcome
        python run_validation.py                   runs every section
Results are written to validation_results/<section>.json and are fully
determined by the seeds in this file.

What each section asks
  structure   On a ranker that ignores cohort, what do E1 (v2) and the superseded
              per-seller formula (v1) report?
  e1          How often does each status result, for a cohort whose true E1 is
              1.00, 0.90, 0.82 or 0.75, at 250 to 10,000 ranking events?
  drift       How often does S1 raise a status on a stable system, and how
              often does it detect a real fall?
  regression  Does S2 stay quiet for a relabelled but unchanged version, and
              does it detect a real deterioration, including one that leaves
              the status at Pass?
  outcome     How often does O3 reach a status on a system with no outcome
              disparity?

Limits: independent ranking events, one synthetic marketplace, one disparity
mechanism (a score penalty on Small sellers). Real event logs are clustered
by query and by day and will be less precise than these tables suggest.
"""

import json
import os
import sys
from collections import Counter
from multiprocessing import Pool

import numpy as np

import metrics as M
from generate_synthetic_audit import generate, make_sellers

OUT = "validation_results"
CATALOGUE_SEED = 20260105
N_SELLERS = 2000
N_BOOT = 500
STATUSES = ("PASS", "MONITOR", "REVIEW_REQUIRED", "INSUFFICIENT_DATA")


def catalogue():
    return make_sellers(N_SELLERS, np.random.default_rng(CATALOGUE_SEED))


def true_e1(penalty, sellers, seed, n_events=6000):
    """E1 of Small sellers on a large sample, accumulated in batches to bound memory."""
    obs = exp = 0.0
    done, batch = 0, 0
    while done < n_events:
        n = min(10000, n_events - done)
        ev, _ = generate(n_events=n, sellers=sellers, penalty={"Small": penalty}, seed=seed * 1000 + batch)
        r = M.exposure_ratio(ev, sellers, n_boot=0).set_index("seller_size").loc["Small"]
        obs, exp = obs + r["top_k_positions"], exp + r["expected_positions"]
        done, batch = done + n, batch + 1
    return float(obs / exp)


def calibrate(target, sellers, seed, lo=-0.05, hi=0.08):
    """Score penalty on Small sellers that gives the target true E1 (bisection)."""
    for i in range(11):
        mid = (lo + hi) / 2
        if true_e1(mid, sellers, seed + i, 4000) > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def rates(statuses):
    c = Counter(statuses)
    return {s: round(c.get(s, 0) / len(statuses), 3) for s in STATUSES}


# ---------------------------------------------------------------- structure
def section_structure():
    sellers = catalogue()
    ev, _ = generate(n_events=5000, sellers=sellers, seed=101)
    e1 = M.exposure_ratio(ev, sellers, seed=101)
    top = ev[ev["rank_position"] <= 10].merge(sellers[["seller_id", "seller_size"]], on="seller_id")
    listings = sellers.groupby("seller_size")["listing_count"].sum() / sellers["listing_count"].sum()
    rows = []
    for _, r in e1.iterrows():
        c = r["seller_size"]
        share_sellers = float((sellers["seller_size"] == c).mean())
        share_top = float((top["seller_size"] == c).mean())
        rows.append({"cohort": c, "share_of_sellers": round(share_sellers, 3),
                     "share_of_listings": round(float(listings[c]), 3), "share_of_top10": round(share_top, 3),
                     "v1_per_seller_formula": round(share_top / share_sellers, 3),
                     "E1": round(r["E1"], 3), "E1_ci": [round(r["E1_ci_lower"], 3), round(r["E1_ci_upper"], 3)],
                     "E1_status": M.classify_ci(r["E1_ci_lower"], r["E1_ci_upper"])})
    return {"n_events": 5000, "ranker": "ignores cohort", "rows": rows,
            "E2": M.mean_rank_position(ev, sellers, seed=101).round(4).to_dict("records"),
            "E3": M.exposure_concentration(ev, sellers).round(4).to_dict("records")}


# ---------------------------------------------------------------- e1
def _e1_task(args):
    penalty, n, seed = args
    sellers = catalogue()
    ev, _ = generate(n_events=n, sellers=sellers, penalty={"Small": penalty}, seed=seed)
    r = M.exposure_ratio(ev, sellers, n_boot=N_BOOT, seed=seed).set_index("seller_size").loc["Small"]
    return r["E1"], r["E1_ci_lower"], r["E1_ci_upper"]


def section_e1(pool):
    sellers = catalogue()
    out = []
    for t_i, target in enumerate((1.00, 0.90, 0.82, 0.75)):
        pen = 0.0 if target == 1.00 else calibrate(target, sellers, 5000 + 100 * t_i)
        truth = 1.0 if target == 1.00 else true_e1(pen, sellers, 7000 + t_i, 200000)  # a cohort-blind ranker is exactly 1
        for n, reps in ((250, 200), (500, 200), (1000, 200), (2500, 100), (5000, 60), (10000, 30)):
            res = pool.map(_e1_task, [(pen, n, 100000 * (t_i + 1) + 1000 * n + r) for r in range(reps)])
            a = np.array(res)
            row = {"target_E1": target, "true_E1": round(truth, 4), "penalty": round(pen, 5), "n_events": n,
                   "replicates": reps, "mean_halfwidth": round(float(((a[:, 2] - a[:, 1]) / 2).mean()), 4),
                   "coverage": round(float(((a[:, 1] <= truth) & (truth <= a[:, 2])).mean()), 3),
                   "point_estimate_below_0.80": round(float((a[:, 0] < 0.80).mean()), 3),
                   **rates([M.classify_ci(lo, hi) for _, lo, hi in res])}
            print(json.dumps(row), flush=True)
            row["replicate_values"] = [[round(float(v), 4) for v in x] for x in res]   # E1, lower, upper
            out.append(row)
    return out


# ---------------------------------------------------------------- drift
def _drift_task(args):
    pen_after, per_week, seed = args
    sellers = catalogue()
    weeks = [generate(n_events=per_week, sellers=sellers, seed=seed * 20 + w, event_prefix=f"W{w}_",
                      penalty={"Small": pen_after if w >= 9 else 0.0})[0] for w in range(1, 13)]
    res = []
    for w in range(5, 13):
        d = M.exposure_drift(weeks[w - 1], weeks[w - 5:w - 1], sellers, "Small", n_boot=N_BOOT, seed=seed + w)
        res.append((w, d["S1_pct"], M.classify_drift_ci(d["S1_ci_lower"], d["S1_ci_upper"])))
    return res


def section_drift(pool):
    sellers = catalogue()
    pen = calibrate(0.75, sellers, 5200)
    out = []
    for label, p in (("stable for 12 weeks", 0.0), ("true E1 falls from 1.00 to 0.75 at week 9", pen)):
        for per_week, reps in ((300, 100), (1000, 60)):
            res = pool.map(_drift_task, [(p, per_week, 300000 + per_week * 100 + r + (0 if p == 0 else 50000))
                                         for r in range(reps)])
            by_week = {}
            for w in range(5, 13):
                st = [x[2] for run in res for x in run if x[0] == w]
                pt = [x[1] for run in res for x in run if x[0] == w]
                by_week[w] = {**rates(st), "mean_S1_pct": round(float(np.mean(pt)), 1),
                              "point_estimate_at_or_below_-10": round(float(np.mean(np.array(pt) <= -10)), 3)}
            any_alert = np.mean([any(x[2] in ("MONITOR", "REVIEW_REQUIRED") for x in run) for run in res])
            row = {"scenario": label, "events_per_week": per_week, "replicates": reps,
                   "runs_with_any_Monitor_or_Review_in_weeks_5_to_12": round(float(any_alert), 3), "by_week": by_week}
            out.append(row)
            print(json.dumps(row), flush=True)
    return out


# ---------------------------------------------------------------- regression
def _s2_task(args):
    pen_cur, pen_new, n, seed = args
    sellers = catalogue()
    cur, _ = generate(n_events=n, sellers=sellers, penalty={"Small": pen_cur}, seed=seed, event_prefix="C")
    new, _ = generate(n_events=n, sellers=sellers, penalty={"Small": pen_new}, seed=seed + 1, event_prefix="N")
    r = M.model_regression(cur, new, sellers, "Small", design="independent", n_boot=N_BOOT, seed=seed)
    e_new = M.exposure_ratio(new, sellers, n_boot=N_BOOT, seed=seed).set_index("seller_size").loc["Small"]
    return r["S2_ratio"], r["S2_ci_lower"], r["S2_ci_upper"], M.classify_ci(e_new["E1_ci_lower"], e_new["E1_ci_upper"])


def section_regression(pool):
    sellers = catalogue()
    p120, p090, p085 = (calibrate(t, sellers, 5400 + i * 50) for i, t in enumerate((1.20, 0.90, 0.85)))
    cases = (("unchanged version (relabelled only): 1.00 to 1.00", 0.0, 0.0),
             ("deterioration that changes the band: 1.00 to 0.85", 0.0, p085),
             ("deterioration within the Pass band: 1.20 to 0.90", p120, p090))
    out = []
    for c_i, (label, pc, pn) in enumerate(cases):
        if pc == pn:                       # the same ranker twice: the true ratio is exactly 1
            t_cur = t_new = 1.0 if pc == 0 else true_e1(pc, sellers, 7100 + c_i, 100000)
        else:
            t_cur, t_new = true_e1(pc, sellers, 7100 + c_i, 100000), true_e1(pn, sellers, 7200 + c_i, 100000)
        for n, reps in ((500, 200), (2000, 100)):
            res = pool.map(_s2_task, [(pc, pn, n, 500000 + 10000 * c_i + n * 10 + 2 * r) for r in range(reps)])
            a = np.array([x[:3] for x in res], dtype=float)
            row = {"case": label, "true_E1_current": round(t_cur, 3), "true_E1_new": round(t_new, 3),
                   "true_ratio": round(t_new / t_cur, 3), "n_events_per_version": n, "replicates": reps,
                   "mean_S2_ratio": round(float(a[:, 0].mean()), 3),
                   "interval_wholly_below_1": round(float((a[:, 2] < 1).mean()), 3),
                   "interval_covers_true_ratio": round(float(((a[:, 1] <= t_new / t_cur) & (t_new / t_cur <= a[:, 2])).mean()), 3),
                   "new_version_E1_status": rates([x[3] for x in res])}
            out.append(row)
            print(json.dumps(row), flush=True)
    return out


# ---------------------------------------------------------------- outcome
def _o3_task(args):
    n, seed = args
    sellers = catalogue()
    ev, _ = generate(n_events=n, sellers=sellers, seed=seed)
    o = M.outcome_parity(ev, sellers, n_boot=N_BOOT, seed=seed)
    return (o["O3_ctr"], M.classify_ci(o["O3_ctr_ci_lower"], o["O3_ctr_ci_upper"]),
            o["O3_cvr"], M.classify_ci(o["O3_cvr_ci_lower"], o["O3_cvr_ci_upper"]),
            o["ctr_disadvantaged"], o["cvr_disadvantaged"])


def section_outcome(pool):
    out = []
    for n, reps in ((500, 200), (2000, 150), (5000, 80)):
        res = pool.map(_o3_task, [(n, 700000 + n * 10 + r) for r in range(reps)])
        row = {"system": "no outcome disparity (true O3 = 1.00)", "n_events": n, "replicates": reps,
               "mean_click_rate_small": round(float(np.mean([x[4] for x in res])), 3),
               "mean_conversion_rate_small": round(float(np.mean([x[5] for x in res])), 4),
               "click_point_estimate_below_0.80": round(float(np.mean([x[0] < 0.8 for x in res])), 3),
               "click_status": rates([x[1] for x in res]),
               "conversion_point_estimate_below_0.80": round(float(np.mean([x[2] < 0.8 for x in res])), 3),
               "conversion_status": rates([x[3] for x in res])}
        out.append(row)
        print(json.dumps(row), flush=True)
    return out


if __name__ == "__main__":
    wanted = sys.argv[1:] or ["structure", "e1", "drift", "regression", "outcome"]
    os.makedirs(OUT, exist_ok=True)
    with Pool(int(os.environ.get("MRFS_WORKERS", "2"))) as pool:
        for name in wanted:
            fn = globals()[f"section_{name}"]
            result = fn() if name == "structure" else fn(pool)
            with open(os.path.join(OUT, f"{name}.json"), "w") as f:
                json.dump(result, f, indent=1)
            print(f"wrote {OUT}/{name}.json", flush=True)
