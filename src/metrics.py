"""
MRFS metrics, version 2.

This module computes the metrics of the MRFS Technical Standard, Section 2.
It replaces the v1 module of MRFS 1.0 and 1.1; results published with those
versions remain reproducible from their archived releases.

What changed from v1, and why it is a breaking change
-----------------------------------------------------
v1 compared a cohort's share of top-K positions with its share of *sellers*.
A cohort that is 25% of sellers but holds 1% of the listings available to
rank then looks under-exposed under a ranker that ignores cohort entirely.
v2 compares against the cohort's share of *listings in a declared comparison
population*, event by event. v1 and v2 E1 values are not comparable.

Input
-----
events : one row per listing in the declared comparison population of a
    ranking event (a ranking event is one request that returns an ordered
    list). Columns: event_id, item_id, seller_id, rank_position. Listings in
    the comparison population that were never ordered have an empty
    rank_position. Outcome metrics also need was_clicked and was_converted
    (the joined analysis view, MRFS Technical Standard, Section 5.5).
sellers : one row per seller. Columns: seller_id and the cohort column(s),
    for example seller_size and seller_tenure. A seller that is missing from
    this table, or has no cohort label, is reported as "Unassigned".

Comparison population
---------------------
Every result depends on which population the events table holds, and the
audit declaration must say which:
    "candidates"  the candidate set at a named stage (platform audit)
    "retrieved"   the results retrieved to a stated depth (external audit)
Statuses are assigned only for a candidate population, and apply to the
declared stage only. See evaluate_statuses().

Intervals
---------
All intervals are percentile bootstrap intervals that resample whole ranking
events. Numerator and denominator of every ratio are recomputed in each
resample. When the observed count in a numerator is zero (a cohort with no
top-K position, or no click or conversion in the window) every resample is
also zero and the bootstrap cannot express the uncertainty; no interval is
returned and the status is Insufficient Data. Intervals built on very few
positions or outcomes remain imprecise and can under-cover. Events are assumed to be an equal-probability sample; unequal
sampling weights are not supported in this version.

Interpretation
--------------
A status is evidence of a potential disparity that calls for investigation.
It does not establish unfair treatment or its cause. E1 counts every top-K
position equally; it is not an attention-weighted exposure measure.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional

import numpy as np
import pandas as pd

UNASSIGNED = "Unassigned"
MRFS_REVIEW_LINE = 0.80      # normative (Technical Standard, Section 2.6)
_CHUNK = 50


# --------------------------------------------------------------------------
# Audit declaration
# --------------------------------------------------------------------------

@dataclass
class AuditDeclaration:
    """Choices that must be fixed and recorded before results are examined."""
    audit_mode: str                       # "platform" or "external"
    population_type: str                  # "candidates" or "retrieved"
    population_detail: str                # stage name, or retrieval depth N
    k: int = 10
    cohort_definitions: dict = field(default_factory=dict)
    review_line: float = 0.80             # MRFS choice, by analogy to the four-fifths rule
    monitor_line: float = 0.85            # MRFS default early-warning threshold
    drift_monitor_pct: float = -10.0      # MRFS default
    drift_review_pct: float = -20.0       # MRFS default
    data_quality_criteria: dict = field(default_factory=dict)
    upstream_not_captured: str = ""       # known stages before the reference stage
    ordered_depth: Optional[int] = None   # depth of the ordered list used for E2 (None = all ordered positions)
    windows: dict = field(default_factory=dict)   # audit window; monitoring window length; number of baseline windows
    resampling_unit: str = "ranking event"
    strata: str = "none"
    fixed_on: str = ""                    # date these choices were fixed (ISO 8601)

    def validate(self) -> None:
        if self.audit_mode not in ("platform", "external"):
            raise ValueError("audit_mode must be 'platform' or 'external'")
        if self.population_type not in ("candidates", "retrieved"):
            raise ValueError("population_type must be 'candidates' or 'retrieved'")
        if self.audit_mode == "external" and self.population_type != "retrieved":
            raise ValueError("an external audit observes retrieved results only")
        if not str(self.population_detail).strip():
            raise ValueError("population_detail (stage name or depth) is required")
        if not self.fixed_on:
            raise ValueError("fixed_on (the date the declaration was fixed) is required")
        if not (0 < self.review_line <= self.monitor_line):
            raise ValueError("review_line must be positive and not above monitor_line")
        if not (self.drift_review_pct <= self.drift_monitor_pct < 0):
            raise ValueError("drift thresholds must be negative, review at or below monitor")

    @property
    def carries_status(self) -> bool:
        return self.population_type == "candidates"

    @property
    def uses_mrfs_review_line(self) -> bool:
        """True when the Review line is the normative MRFS 0.80. Any other value
        gives exploratory results that are not MRFS statuses (Standard, Section 2.6)."""
        return abs(float(self.review_line) - MRFS_REVIEW_LINE) < 1e-12

    @property
    def scope_label(self) -> str:
        return f"{self.population_type}, {self.population_detail}"

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------
# Cohort assignment helpers
# --------------------------------------------------------------------------

def assign_size_cohorts(values: pd.Series, lower_q: float = 0.25, upper_q: float = 0.75) -> pd.Series:
    """
    Default MRFS size cohorts from a pre-audit size measure: Small at or
    below the lower-quartile value, Large at or above the upper-quartile
    value, Medium between. Sellers tied at a cut-off value all fall on the
    same side, so cohort shares can differ from 25/50/25 and must be reported.
    Missing values give "Unassigned". If the two cut-offs coincide the
    measure cannot separate cohorts and a ValueError is raised.
    """
    v = pd.to_numeric(values, errors="coerce")
    lo, hi = v.quantile(lower_q), v.quantile(upper_q)
    if not lo < hi:
        raise ValueError("size measure cannot separate cohorts: quartile cut-offs coincide")
    out = pd.Series("Medium", index=values.index, dtype=object)
    out[v <= lo] = "Small"
    out[v >= hi] = "Large"
    out[v.isna()] = UNASSIGNED
    return out


def assign_tenure_cohorts(reference_dates: pd.Series, audit_start, months: int = 12) -> pd.Series:
    """
    Default MRFS tenure cohorts. New: the seller's tenure reference date is
    later than the date `months` calendar months before the audit start.
    Exactly `months` months counts as Established. Missing dates give
    "Unassigned". Calendar-month arithmetic: same day of the month, or the
    last day of the month where that day does not exist.
    """
    start = pd.Timestamp(audit_start).normalize()
    cutoff = start - pd.DateOffset(months=months)
    d = pd.to_datetime(reference_dates, errors="coerce").dt.normalize()
    out = pd.Series("Established", index=reference_dates.index, dtype=object)
    out[d > cutoff] = "New"
    out[d.isna()] = UNASSIGNED
    return out


# --------------------------------------------------------------------------
# Internals
# --------------------------------------------------------------------------

def _percentile_ci(boot: np.ndarray, ci_level: float = 0.95):
    boot = np.asarray(boot, dtype=float)
    boot = boot[np.isfinite(boot)]
    if len(boot) < 20:
        return np.nan, np.nan
    a = (1 - ci_level) / 2 * 100
    lo, hi = np.percentile(boot, [a, 100 - a])
    return float(lo), float(hi)


def _resample_counts(n: int, n_boot: int, rng: np.random.Generator):
    """Yield (chunk, n) arrays: how many times each event is drawn in each resample."""
    p = np.full(n, 1.0 / n)
    done = 0
    while done < n_boot:
        m = min(_CHUNK, n_boot - done)
        yield rng.multinomial(n, p, size=m).astype(float)
        done += m


def _with_cohort(events: pd.DataFrame, sellers: pd.DataFrame, cohort_col: str) -> pd.DataFrame:
    lab = sellers[["seller_id", cohort_col]].drop_duplicates("seller_id")
    m = events.merge(lab, on="seller_id", how="left")
    m["rank_position"] = pd.to_numeric(m["rank_position"], errors="coerce").astype(float)   # empty rank -> NaN
    m[cohort_col] = m[cohort_col].where(m[cohort_col].notna(), UNASSIGNED)
    return m


def _exposure_arrays(events: pd.DataFrame, sellers: pd.DataFrame, k: int, cohort_col: str):
    """
    Per-event arrays for E1. Returns (cohorts, T, EXP, n_used, n_excluded):
      T[q, c]    top-K positions held by cohort c in event q
      EXP[q, c]  K_q * (cohort c listings in population of q) / (all listings in population of q)
    Events whose comparison population has no more than K listings are excluded.
    Every cohort labelled in the seller records is included, so a cohort with no
    listings in any included event is reported (with zero expected positions).
    """
    m = _with_cohort(events, sellers, cohort_col)
    m["_top"] = (m["rank_position"] <= k).astype(int)          # empty rank compares False
    cohorts = sorted(set(m[cohort_col].unique()) | set(sellers[cohort_col].dropna().unique()), key=str)
    pop = m.groupby(["event_id", cohort_col]).size().unstack(fill_value=0).reindex(columns=cohorts, fill_value=0)
    top = m.groupby(["event_id", cohort_col])["_top"].sum().unstack(fill_value=0).reindex(columns=cohorts, fill_value=0)
    n_q = pop.sum(axis=1).values.astype(float)
    k_q = top.sum(axis=1).values.astype(float)
    keep = (n_q > k) & (k_q > 0)
    T = top.values.astype(float)[keep]
    EXP = (k_q[keep, None] * pop.values[keep] / n_q[keep, None])
    return cohorts, T, EXP, int(keep.sum()), int((~keep).sum())


# --------------------------------------------------------------------------
# E1  Exposure ratio at K
# --------------------------------------------------------------------------

def exposure_ratio(events: pd.DataFrame, sellers: pd.DataFrame, k: int = 10,
                   cohort_col: str = "seller_size", n_boot: int = 1000,
                   ci_level: float = 0.95, seed: Optional[int] = None) -> pd.DataFrame:
    """
    E1(c) = sum_q T_q(c) / sum_q [ K_q * n_q(c) / n_q ]

    Top-K positions the cohort holds, over the number it would hold if
    position were unrelated to cohort, given each event's comparison
    population. 1.0 means the cohort's top-K presence matches its share of
    that population. A cohort with no listings in the comparison population of
    any included event has zero expected positions: E1 is undefined (NaN), no
    interval is formed, and evaluate_statuses reports it as NOT_EVALUATED.
    """
    cohorts, T, EXP, n_used, n_excl = _exposure_arrays(events, sellers, k, cohort_col)
    obs, exp = T.sum(axis=0), EXP.sum(axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        point = np.where(exp > 0, obs / exp, np.nan)
    boot = np.full((n_boot, len(cohorts)), np.nan)
    if n_used > 1 and n_boot > 0:
        rng = np.random.default_rng(seed)
        row = 0
        for w in _resample_counts(n_used, n_boot, rng):
            with np.errstate(divide="ignore", invalid="ignore"):
                boot[row:row + len(w)] = (w @ T) / (w @ EXP)
            row += len(w)
    rows = []
    for j, c in enumerate(cohorts):
        lo, hi = _percentile_ci(boot[:, j], ci_level) if obs[j] > 0 else (np.nan, np.nan)
        rows.append({cohort_col: c, "k": k, "top_k_positions": obs[j], "expected_positions": exp[j],
                     "E1": float(point[j]), "E1_ci_lower": lo, "E1_ci_upper": hi,
                     "n_events": n_used, "n_events_excluded": n_excl})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# E2  Mean rank position (normalised)
# --------------------------------------------------------------------------

def mean_rank_position(events: pd.DataFrame, sellers: pd.DataFrame,
                       cohort_col: str = "seller_size", n_boot: int = 1000,
                       ci_level: float = 0.95, seed: Optional[int] = None,
                       ordered_depth: Optional[int] = None) -> pd.DataFrame:
    """
    E2(c): mean, over ranking events that contain at least one ordered
    listing of cohort c, of the mean normalised rank of the cohort's listings
    in that event. Normalised rank = (rank - 0.5) / (ordered positions in the
    event). Each event counts equally. Lower is better; 0.5 is the reference
    midpoint obtained when order is unrelated to cohort, not a fairness
    expectation. No status is assigned.
    """
    m = _with_cohort(events, sellers, cohort_col)
    m = m[m["rank_position"].notna()].copy()
    if ordered_depth is not None:                     # declared depth: positions beyond it are not used
        m = m[m["rank_position"] <= ordered_depth]
    cohorts = sorted(m[cohort_col].unique(), key=str)
    depth = m.groupby("event_id")["rank_position"].transform("count")
    m["_u"] = (m["rank_position"] - 0.5) / depth
    mean_u = m.groupby(["event_id", cohort_col])["_u"].mean().unstack().reindex(columns=cohorts)
    present = mean_u.notna().values.astype(float)
    vals = np.nan_to_num(mean_u.values, nan=0.0)
    n = len(mean_u)
    with np.errstate(divide="ignore", invalid="ignore"):
        point = vals.sum(axis=0) / present.sum(axis=0)
    boot = np.full((n_boot, len(cohorts)), np.nan)
    if n > 1 and n_boot > 0:
        rng = np.random.default_rng(seed)
        row = 0
        for w in _resample_counts(n, n_boot, rng):
            with np.errstate(divide="ignore", invalid="ignore"):
                boot[row:row + len(w)] = (w @ vals) / (w @ present)
            row += len(w)
    depths = m.groupby("event_id")["rank_position"].count()
    rows = []
    for j, c in enumerate(cohorts):
        lo, hi = _percentile_ci(boot[:, j], ci_level)
        rows.append({cohort_col: c, "E2": float(point[j]), "E2_ci_lower": lo, "E2_ci_upper": hi,
                     "n_events_with_cohort": int(present[:, j].sum()),
                     "ordered_depth_min": int(depths.min()), "ordered_depth_max": int(depths.max())})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# E3  Exposure concentration
# --------------------------------------------------------------------------

def _gini(counts: np.ndarray) -> float:
    x = np.sort(np.asarray(counts, dtype=float))
    n = len(x)
    if n == 0 or x.sum() == 0:
        return np.nan
    cum = np.cumsum(x)
    return float((n + 1 - 2 * cum.sum() / cum[-1]) / n)


def exposure_concentration(events: pd.DataFrame, sellers: pd.DataFrame, k: int = 10,
                           cohort_col: str = "seller_size") -> pd.DataFrame:
    """
    E3: Gini index of top-K position counts across sellers, per cohort and
    overall. The seller set is every seller with at least one listing in the
    comparison population during the window, including sellers with no top-K
    position. 0 = positions spread evenly across those sellers; values near 1
    = a few sellers hold nearly all of them. Concentration does not establish
    unfair treatment. The value depends on window length and traffic, so it
    is compared only within one audit design. No status is assigned.
    """
    m = _with_cohort(events, sellers, cohort_col)
    m["_top"] = (m["rank_position"] <= k).astype(int)
    per_seller = m.groupby(["seller_id", cohort_col])["_top"].sum().reset_index()
    rows = []
    for c, g in list(per_seller.groupby(cohort_col)) + [("All sellers", per_seller)]:
        rows.append({cohort_col: c, "k": k, "E3": _gini(g["_top"].values), "n_sellers": len(g),
                     "n_sellers_zero_top_k": int((g["_top"] == 0).sum()),
                     "top_k_positions": int(g["_top"].sum())})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# O1-O3  Outcome parity
# --------------------------------------------------------------------------

def outcome_parity(events: pd.DataFrame, sellers: pd.DataFrame, k: int = 10,
                   cohort_col: str = "seller_size", disadvantaged: str = "Small",
                   reference: str = "Large", n_boot: int = 1000,
                   ci_level: float = 0.95, seed: Optional[int] = None) -> dict:
    """
    O1 click-through and O2 conversion rate of each cohort's top-K
    impressions; O3 the ratio of the disadvantaged cohort's rate to the
    reference cohort's, with an event-level bootstrap interval. O3 is one
    quantity per outcome: the "parity ratio" and the "disparate impact
    ratio" of earlier versions were the same number under two names.
    """
    m = _with_cohort(events, sellers, cohort_col)
    top = m[m["rank_position"] <= k]
    ids = pd.Index(m["event_id"].unique())

    def arrays(cohort):
        g = top[top[cohort_col] == cohort].groupby("event_id")
        return (g.size().reindex(ids, fill_value=0).values.astype(float),
                g["was_clicked"].sum().reindex(ids, fill_value=0).values.astype(float),
                g["was_converted"].sum().reindex(ids, fill_value=0).values.astype(float))

    imp_d, clk_d, cvt_d = arrays(disadvantaged)
    imp_r, clk_r, cvt_r = arrays(reference)

    def ratio(num_d, den_d, num_r, den_r):
        with np.errstate(divide="ignore", invalid="ignore"):
            return (num_d / den_d) / (num_r / den_r)

    out = {"disadvantaged": disadvantaged, "reference": reference, "k": k,
           "ctr_disadvantaged": clk_d.sum() / imp_d.sum() if imp_d.sum() else np.nan,
           "ctr_reference": clk_r.sum() / imp_r.sum() if imp_r.sum() else np.nan,
           "cvr_disadvantaged": cvt_d.sum() / imp_d.sum() if imp_d.sum() else np.nan,
           "cvr_reference": cvt_r.sum() / imp_r.sum() if imp_r.sum() else np.nan}
    out["O3_ctr"] = float(ratio(clk_d.sum(), imp_d.sum(), clk_r.sum(), imp_r.sum()))
    out["O3_cvr"] = float(ratio(cvt_d.sum(), imp_d.sum(), cvt_r.sum(), imp_r.sum()))
    n = len(ids)
    b_ctr, b_cvr = np.full(n_boot, np.nan), np.full(n_boot, np.nan)
    if n > 1 and n_boot > 0:
        rng = np.random.default_rng(seed)
        row = 0
        for w in _resample_counts(n, n_boot, rng):
            b_ctr[row:row + len(w)] = ratio(w @ clk_d, w @ imp_d, w @ clk_r, w @ imp_r)
            b_cvr[row:row + len(w)] = ratio(w @ cvt_d, w @ imp_d, w @ cvt_r, w @ imp_r)
            row += len(w)
    nan2 = (np.nan, np.nan)
    out["O3_ctr_ci_lower"], out["O3_ctr_ci_upper"] = _percentile_ci(b_ctr, ci_level) if min(clk_d.sum(), clk_r.sum()) > 0 else nan2
    out["O3_cvr_ci_lower"], out["O3_cvr_ci_upper"] = _percentile_ci(b_cvr, ci_level) if min(cvt_d.sum(), cvt_r.sum()) > 0 else nan2
    out["n_events"] = n
    return out


# --------------------------------------------------------------------------
# S1  Exposure drift,  S2  Model regression
# --------------------------------------------------------------------------

def _e1_replicates(events, sellers, k, cohort_col, cohort_value, n_boot, rng):
    cohorts, T, EXP, n_used, _ = _exposure_arrays(events, sellers, k, cohort_col)
    if cohort_value not in cohorts or n_used < 2:
        return np.nan, np.full(n_boot, np.nan), None
    j = cohorts.index(cohort_value)
    t, e = T[:, j], EXP[:, j]
    point = t.sum() / e.sum() if e.sum() > 0 else np.nan
    reps = np.full(n_boot, np.nan)
    if t.sum() == 0:                      # degenerate: no interval can be formed
        return float(point), reps, (t, e)
    row = 0
    for w in _resample_counts(n_used, n_boot, rng):
        with np.errstate(divide="ignore", invalid="ignore"):
            reps[row:row + len(w)] = (w @ t) / (w @ e)
        row += len(w)
    return float(point), reps, (t, e)


def exposure_drift(current_events: pd.DataFrame, baseline_windows: list, sellers: pd.DataFrame,
                   cohort_value: str, cohort_col: str = "seller_size", k: int = 10,
                   n_boot: int = 1000, ci_level: float = 0.95, seed: Optional[int] = None) -> dict:
    """
    S1: percentage change of E1 in the current monitoring window against the
    mean E1 of the preceding baseline windows (MRFS default: four windows of
    the same length, non-overlapping, same comparison population).

        S1 = 100 * (E1_current / mean(E1_baseline windows) - 1)

    Negative values are declines. The interval resamples the events of each
    window separately.
    """
    rng = np.random.default_rng(seed)
    cur_point, cur_reps, _ = _e1_replicates(current_events, sellers, k, cohort_col, cohort_value, n_boot, rng)
    base = [_e1_replicates(w, sellers, k, cohort_col, cohort_value, n_boot, rng) for w in baseline_windows]
    base_points = [b[0] for b in base]
    if not base or not np.all(np.isfinite(base_points)) or np.mean(base_points) == 0 or not np.isfinite(cur_point):
        return {"S1_pct": np.nan, "S1_ci_lower": np.nan, "S1_ci_upper": np.nan,
                "E1_current": cur_point, "E1_baseline_mean": np.nan, "n_baseline_windows": len(base)}
    base_mean = float(np.mean(base_points))
    base_reps = np.mean([b[1] for b in base], axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        reps = 100 * (cur_reps / base_reps - 1)
    lo, hi = _percentile_ci(reps, ci_level)
    return {"S1_pct": 100 * (cur_point / base_mean - 1), "S1_ci_lower": lo, "S1_ci_upper": hi,
            "E1_current": cur_point, "E1_baseline_mean": base_mean, "n_baseline_windows": len(base)}


def model_regression(current_events: pd.DataFrame, new_events: pd.DataFrame, sellers: pd.DataFrame,
                     cohort_value: str, cohort_col: str = "seller_size", k: int = 10,
                     design: str = "independent", n_boot: int = 1000, ci_level: float = 0.95,
                     seed: Optional[int] = None) -> dict:
    """
    S2: E1 under the new ranking version divided by E1 under the current
    version, with an interval. An interval wholly below 1 is evidence of
    deterioration. No status and no cut-off are applied; the ratio and
    interval are reported for review.

    design:
      "paired"       both versions ranked the same events; the two tables
                     share event_id values and events are resampled jointly
      "independent"  the versions were observed on different events (a
                     concurrent split, or before/after windows); each table
                     is resampled separately. Before/after comparisons are
                     confounded with time, which the report must state.
    """
    if design not in ("paired", "independent"):
        raise ValueError("design must be 'paired' or 'independent'")
    rng = np.random.default_rng(seed)
    if design == "independent":
        p_cur, r_cur, _ = _e1_replicates(current_events, sellers, k, cohort_col, cohort_value, n_boot, rng)
        p_new, r_new, _ = _e1_replicates(new_events, sellers, k, cohort_col, cohort_value, n_boot, rng)
        with np.errstate(divide="ignore", invalid="ignore"):
            reps = r_new / r_cur
    else:
        def per_event(ev):
            m = _with_cohort(ev, sellers, cohort_col)
            m["_top"] = (m["rank_position"] <= k).astype(int)
            m["_c"] = (m[cohort_col] == cohort_value).astype(int)
            g = m.groupby("event_id")
            n_q, k_q = g.size(), g["_top"].sum()
            t = (m["_top"] * m["_c"]).groupby(m["event_id"]).sum()
            e = k_q * g["_c"].sum() / n_q
            keep = (n_q > k) & (k_q > 0)
            return t[keep], e[keep]
        t_c, e_c = per_event(current_events)
        t_n, e_n = per_event(new_events)
        ids = t_c.index.intersection(t_n.index)
        if len(ids) < 2:
            raise ValueError("paired design needs events present in both tables")
        tc, ec, tn, en = (x.reindex(ids).values.astype(float) for x in (t_c, e_c, t_n, e_n))
        p_cur, p_new = tc.sum() / ec.sum(), tn.sum() / en.sum()
        reps = np.full(n_boot, np.nan)
        if tc.sum() > 0 and tn.sum() > 0:     # a zero count leaves no interval (see "Intervals" above)
            row = 0
            for w in _resample_counts(len(ids), n_boot, rng):
                with np.errstate(divide="ignore", invalid="ignore"):
                    reps[row:row + len(w)] = ((w @ tn) / (w @ en)) / ((w @ tc) / (w @ ec))
                row += len(w)
    lo, hi = _percentile_ci(reps, ci_level)
    ratio = p_new / p_cur if p_cur and np.isfinite(p_cur) else np.nan
    return {"S2_ratio": float(ratio), "S2_ci_lower": lo, "S2_ci_upper": hi,
            "E1_current_version": float(p_cur), "E1_new_version": float(p_new), "design": design}


# --------------------------------------------------------------------------
# Statuses
# --------------------------------------------------------------------------

def classify_ci(lower: float, upper: float, review_line: float = 0.80, monitor_line: float = 0.85) -> str:
    """
    Status of a ratio metric from its interval:
      whole interval at or above monitor_line          PASS
      whole interval within [review_line, monitor_line)  MONITOR
      whole interval below review_line                 REVIEW_REQUIRED
      anything else                                    INSUFFICIENT_DATA
    """
    if lower is None or upper is None or not np.isfinite(lower) or not np.isfinite(upper):
        return "INSUFFICIENT_DATA"
    if lower >= monitor_line:
        return "PASS"
    if upper < review_line:
        return "REVIEW_REQUIRED"
    if lower >= review_line and upper < monitor_line:
        return "MONITOR"
    return "INSUFFICIENT_DATA"


def classify_drift_ci(lower: float, upper: float, monitor_pct: float = -10.0, review_pct: float = -20.0) -> str:
    """
    Status of S1 from its interval (percent; declines are negative):
      whole interval above monitor_pct                   PASS
      whole interval within (review_pct, monitor_pct]    MONITOR
      whole interval at or below review_pct              REVIEW_REQUIRED
      anything else                                      INSUFFICIENT_DATA
    """
    if lower is None or upper is None or not np.isfinite(lower) or not np.isfinite(upper):
        return "INSUFFICIENT_DATA"
    if lower > monitor_pct:
        return "PASS"
    if upper <= review_pct:
        return "REVIEW_REQUIRED"
    if lower > review_pct and upper <= monitor_pct:
        return "MONITOR"
    return "INSUFFICIENT_DATA"


def evaluate_statuses(declaration: AuditDeclaration, e1: pd.DataFrame, outcome: Optional[dict] = None) -> dict:
    """
    Statuses for E1 and, where outcome data exist, O3. Statuses are assigned
    only when the declared comparison population is a candidate set, and they
    apply to the declared stage only. For a retrieved-results population the
    ratio and interval are reported without a status. The Unassigned group is
    reported but never given a status. A Review line other than the normative
    0.80 gives exploratory statuses: they are computed, but flagged
    (mrfs_status False, with a note) and must not be reported as MRFS statuses.
    Metrics without data are listed as
    "Not evaluated"; they are never counted as a pass. An E1 row with zero
    expected positions (the cohort had no listings in the comparison
    population) has no defined ratio and is NOT_EVALUATED.
    """
    declaration.validate()
    cohort_col = e1.columns[0]
    mrfs = declaration.carries_status and declaration.uses_mrfs_review_line
    note = "" if declaration.uses_mrfs_review_line else (
        f"Review line {declaration.review_line} differs from the normative MRFS {MRFS_REVIEW_LINE}: "
        "statuses are exploratory and are not MRFS statuses")
    out = {"scope": declaration.scope_label, "carries_status": declaration.carries_status,
           "mrfs_status": mrfs, "note": note, "E1": [], "O3": None}
    for _, r in e1.iterrows():
        status = None
        if declaration.carries_status and r[cohort_col] != UNASSIGNED and not r["expected_positions"] > 0:
            status = "NOT_EVALUATED"
        elif declaration.carries_status and r[cohort_col] != UNASSIGNED:
            status = classify_ci(r["E1_ci_lower"], r["E1_ci_upper"], declaration.review_line, declaration.monitor_line)
        out["E1"].append({"cohort": r[cohort_col], "E1": r["E1"], "ci_lower": r["E1_ci_lower"],
                          "ci_upper": r["E1_ci_upper"], "status": status,
                          "mrfs_status": bool(mrfs and status is not None)})
    if outcome is None:
        out["O3"] = "Not evaluated"
    else:
        o3 = {}
        for name in ("ctr", "cvr"):
            lo, hi = outcome[f"O3_{name}_ci_lower"], outcome[f"O3_{name}_ci_upper"]
            o3[name] = {"O3": outcome[f"O3_{name}"], "ci_lower": lo, "ci_upper": hi,
                        "status": classify_ci(lo, hi, declaration.review_line, declaration.monitor_line)
                        if declaration.carries_status else None}
        out["O3"] = o3
    return out
