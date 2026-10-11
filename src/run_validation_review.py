"""
Focused validation review of two findings of run_validation.py (partial run, stopped by decision once the
behaviour was established; completed rows are in validation_results/review_band_and_drift_partial.json).

1. How often can the Monitor band be confirmed, as a function of ranking
   events and of the cohort's share of candidate listings?
2. How does S1 detection depend on events per monitoring window, and how does
   it compare with the E1 status of the same window?

Uses a vectorised re-implementation of metrics.exposure_ratio (same
estimator, same event-level percentile bootstrap) so that tens of thousands
of events can be replicated. Checked against the full implementation in
check_against_metrics(). Candidate-set sizes as in generate_synthetic_audit
(40, 80, 150, 300); cohort membership of each candidate drawn with the
cohort's listing share; score = Uniform(0,1) + penalty for cohort listings.
Independent events.
"""
import json, sys
import numpy as np

K, SIZES, NBOOT = 10, (40, 80, 150, 300), 400

def events(n, p, pen, rng):
    size = rng.choice(SIZES, n)
    T, E = np.empty(n), np.empty(n)
    for L in SIZES:
        idx = np.where(size == L)[0]
        if not len(idx):
            continue
        lab = rng.random((len(idx), L)) < p
        sc = rng.random((len(idx), L)) + pen * lab
        kth = np.partition(sc, K - 1, axis=1)[:, K - 1:K]
        T[idx] = ((sc <= kth) & lab).sum(1)
        E[idx] = K * lab.sum(1) / L
    return T, E

def boot(T, E, rng, nboot=NBOOT):
    n = len(T); out = np.empty(nboot); pr = np.full(n, 1.0 / n); r = 0
    while r < nboot:
        m = min(25, nboot - r); w = rng.multinomial(n, pr, size=m).astype(float)
        with np.errstate(divide="ignore", invalid="ignore"):
            out[r:r + m] = (w @ T) / (w @ E)
        r += m
    return out

def ci(b):
    b = b[np.isfinite(b)]
    return np.percentile(b, [2.5, 97.5]) if len(b) > 20 else (np.nan, np.nan)

def classify(lo, hi, rl=0.80, ml=0.85):
    if not (np.isfinite(lo) and np.isfinite(hi)): return "I"
    if lo >= ml: return "P"
    if hi < rl: return "R"
    if lo >= rl and hi < ml: return "M"
    return "I"

def classify_drift(lo, hi, m=-10.0, r=-20.0):
    if not (np.isfinite(lo) and np.isfinite(hi)): return "I"
    if lo > m: return "P"
    if hi <= r: return "R"
    if lo > r and hi <= m: return "M"
    return "I"

def true_e1(p, pen, seed, n=400000):
    rng = np.random.default_rng(seed); T, E = events(n, p, pen, rng); return T.sum() / E.sum()

def calibrate(p, target, seed):
    lo, hi = -0.3, 0.6
    for i in range(18):
        mid = (lo + hi) / 2
        if true_e1(p, mid, seed + i, 150000) > target: lo = mid
        else: hi = mid
    return (lo + hi) / 2

def monitor_band(rng_seed=1):
    out = []
    for p in (0.042, 0.25):
        for target in (0.81, 0.825, 0.84):
            pen = calibrate(p, target, 10 + int(target * 1000))
            truth = true_e1(p, pen, 99, 800000)
            for n, reps in ((1000, 150), (5000, 100), (10000, 80), (25000, 60), (50000, 40), (100000, 25)):
                rng = np.random.default_rng(rng_seed + n + int(1000 * target) + int(1000 * p))
                st, hws, pass_out, rev_out = [], [], 0, 0
                for _ in range(reps):
                    T, E = events(n, p, pen, rng); lo, hi = ci(boot(T, E, rng))
                    st.append(classify(lo, hi)); hws.append((hi - lo) / 2)
                    pass_out += hi < 0.85; rev_out += lo >= 0.80
                row = dict(listing_share=p, true_E1=round(float(truth), 4), n_events=n, replicates=reps,
                           mean_halfwidth=round(float(np.mean(hws)), 4),
                           **{s: round(st.count(s) / reps, 3) for s in "PMRI"},
                           pass_ruled_out=round(pass_out / reps, 3), review_ruled_out=round(rev_out / reps, 3))
                out.append(row); print(json.dumps(row), flush=True)
    return out

def drift(rng_seed=2):
    out = []
    for p in (0.042, 0.25):
        pen = {t: calibrate(p, t, 500 + int(t * 100)) for t in (0.75, 0.85)}
        for target in (0.75, 0.85):
            for n, reps in ((300, 150), (1000, 150), (3000, 100), (10000, 60), (30000, 30)):
                rng = np.random.default_rng(rng_seed + n + int(100 * target) + int(1000 * p))
                s1, e1 = [], []
                for _ in range(reps):
                    base = [events(n, p, 0.0, rng) for _ in range(4)]
                    cur = events(n, p, pen[target], rng)
                    bb = np.mean([boot(T, E, rng) for T, E in base], axis=0)
                    cb = boot(*cur, rng)
                    lo, hi = ci(100 * (cb / bb - 1)); s1.append(classify_drift(lo, hi))
                    e1.append(classify(*ci(cb)))
                row = dict(listing_share=p, true_change_pct=round(100 * (target - 1)), events_per_window=n, replicates=reps,
                           S1={s: round(s1.count(s) / reps, 3) for s in "PMRI"},
                           E1_same_window={s: round(e1.count(s) / reps, 3) for s in "PMRI"})
                out.append(row); print(json.dumps(row), flush=True)
    return out

def check_against_metrics():
    """Half-width of the vectorised estimator vs src/metrics.py on generator data (neutral, 1,000 events)."""
    rng = np.random.default_rng(5); hw = []
    for _ in range(60):
        T, E = events(1000, 0.042, 0.0, rng); lo, hi = ci(boot(T, E, rng)); hw.append((hi - lo) / 2)
    return {"vectorised_mean_halfwidth_1000_events_share_0.042": round(float(np.mean(hw)), 4),
            "src_metrics_on_generator_data_same_setting": 0.0861}

if __name__ == "__main__":
    part = sys.argv[1]
    res = {"check": check_against_metrics} [part]() if part == "check" else (monitor_band() if part == "band" else drift())
    json.dump(res, open(f"validation_results/review_{part}.json", "w"), indent=1); print(json.dumps(res) if part == "check" else "done")
