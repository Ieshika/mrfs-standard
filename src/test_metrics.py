"""
Tests for metrics.py (version 2). Run with `python test_metrics.py` or pytest.
Every expected value below is worked out by hand in the comment beside it.
"""

import hashlib

import numpy as np
import pandas as pd

import metrics as M
from generate_synthetic_audit import generate, default_declaration


def _ev(rows):
    return pd.DataFrame(rows, columns=["event_id", "item_id", "seller_id", "rank_position"])


SELLERS = pd.DataFrame({"seller_id": ["a", "b", "c", "d"],
                        "seller_size": ["Small", "Small", "Large", "Large"]})


def _two_events(k_fill=None):
    # Event 1: 4 listings, ranks 1..4 -> sellers a(Small), c, d, b(Small)
    # Event 2: 6 listings, ranks 1..6 -> c, d, c, a(Small), b(Small), a(Small)
    r = [("e1", "i1", "a", 1), ("e1", "i2", "c", 2), ("e1", "i3", "d", 3), ("e1", "i4", "b", 4),
         ("e2", "i5", "c", 1), ("e2", "i6", "d", 2), ("e2", "i7", "c", 3),
         ("e2", "i8", "a", 4), ("e2", "i9", "b", 5), ("e2", "i10", "a", 6)]
    return _ev(r)


def test_e1_hand_example():
    # K = 2.
    # Event 1: Small holds 1 of the top 2. Small is 2 of 4 listings -> expected 2 * 2/4 = 1.0
    # Event 2: Small holds 0 of the top 2. Small is 3 of 6 listings -> expected 2 * 3/6 = 1.0
    # E1(Small) = (1 + 0) / (1.0 + 1.0) = 0.5 ; E1(Large) = (1 + 2) / (1.0 + 1.0) = 1.5
    e1 = M.exposure_ratio(_two_events(), SELLERS, k=2, n_boot=0).set_index("seller_size")
    assert abs(e1.loc["Small", "E1"] - 0.5) < 1e-12
    assert abs(e1.loc["Large", "E1"] - 1.5) < 1e-12
    assert e1.loc["Small", "n_events"] == 2 and e1.loc["Small", "n_events_excluded"] == 0


def test_e1_uses_listing_share_not_seller_share():
    # One event, K = 1, 10 listings: 9 from Large seller c, 1 from Small seller a, a ranked 5th.
    # Sellers are 50% Small. Small expected positions = 1 * 1/10 = 0.1, observed 0 -> E1 = 0.
    # Large expected 0.9, observed 1 -> E1 = 1/0.9. (The v1 formula would have used 0.5 for both.)
    rows = [("e", f"i{r}", "c" if r != 5 else "a", r) for r in range(1, 11)]
    e1 = M.exposure_ratio(_ev(rows), SELLERS, k=1, n_boot=0).set_index("seller_size")
    assert abs(e1.loc["Large", "E1"] - 1 / 0.9) < 1e-12 and e1.loc["Small", "E1"] == 0
    assert abs(e1.loc["Small", "expected_positions"] - 0.1) < 1e-12


def test_zero_count_gives_no_interval_and_insufficient_data():
    # Small holds no top-1 position in either event. Every bootstrap resample is also zero,
    # so no interval is returned and the status is Insufficient Data, never Review Required.
    ev = _two_events()
    ev.loc[ev.event_id == "e1", "rank_position"] = [4, 1, 2, 3]      # a moves from rank 1 to rank 4
    e1 = M.exposure_ratio(ev, SELLERS, k=1, n_boot=200, seed=1).set_index("seller_size")
    assert e1.loc["Small", "E1"] == 0 and np.isnan(e1.loc["Small", "E1_ci_lower"])
    assert M.classify_ci(e1.loc["Small", "E1_ci_lower"], e1.loc["Small", "E1_ci_upper"]) == "INSUFFICIENT_DATA"
    ev["was_clicked"] = (ev["seller_id"] == "c").astype(int)        # only Large sellers are ever clicked
    ev["was_converted"] = 0
    o = M.outcome_parity(ev, SELLERS, k=6, n_boot=200, seed=1)
    assert o["O3_ctr"] == 0 and np.isnan(o["O3_ctr_ci_lower"]) and np.isnan(o["O3_cvr_ci_lower"])


def test_zero_counts_in_s1_and_s2_give_no_interval():
    # A window or version in which the cohort holds no top-K position cannot produce an interval.
    ev, se = generate(n_events=300, n_sellers=600, seed=13)
    zero = ev.copy()
    small = set(se.loc[se["seller_size"] == "Small", "seller_id"])
    is_small = zero["seller_id"].isin(small)
    zero.loc[is_small & (zero["rank_position"] <= 10), "rank_position"] = pd.NA   # Small never in the top 10
    d = M.exposure_drift(zero, [ev], se, "Small", seed=1, n_boot=200)
    assert np.isnan(d["S1_ci_lower"]) and M.classify_drift_ci(d["S1_ci_lower"], d["S1_ci_upper"]) == "INSUFFICIENT_DATA"
    for design in ("paired", "independent"):
        r = M.model_regression(ev, zero, se, "Small", design=design, seed=1, n_boot=200)
        assert np.isnan(r["S2_ci_lower"]) and np.isnan(r["S2_ci_upper"]), design


def test_e2_respects_declared_depth():
    # Depth 2 keeps ranks 1-2 only. Event 1: a (Small) rank 1 -> 0.25 ; event 2: no Small in ranks 1-2.
    # E2(Small) = 0.25 over the one event containing it. Large: e1 rank 2 -> 0.75 ; e2 ranks 1, 2 -> 0.5 ; mean 0.625
    e2 = M.mean_rank_position(_two_events(), SELLERS, n_boot=0, ordered_depth=2).set_index("seller_size")
    assert abs(e2.loc["Small", "E2"] - 0.25) < 1e-12 and abs(e2.loc["Large", "E2"] - 0.625) < 1e-12


def test_e1_excludes_events_with_nothing_to_rank():
    # K = 4: event 1 has exactly 4 listings (no ranking choice) and is excluded; event 2 (6) is kept.
    e1 = M.exposure_ratio(_two_events(), SELLERS, k=4, n_boot=0)
    assert (e1["n_events"] == 1).all() and (e1["n_events_excluded"] == 1).all()


def test_e1_counts_unordered_candidates_in_population():
    # Event 2 again, but the three lowest candidates were never ordered (empty rank).
    # They still count in the comparison population: Small is 3 of 6, expected 2 * 3/6 = 1.0 at K = 2.
    ev = _two_events()
    ev["rank_position"] = ev["rank_position"].astype("Int64")
    ev.loc[(ev.event_id == "e2") & (ev.rank_position > 3), "rank_position"] = pd.NA
    e1 = M.exposure_ratio(ev[ev.event_id == "e2"], SELLERS, k=2, n_boot=0).set_index("seller_size")
    assert abs(e1.loc["Small", "expected_positions"] - 1.0) < 1e-12 and e1.loc["Small", "E1"] == 0


def test_unassigned_group_is_reported_and_has_no_status():
    ev = _two_events()
    ev.loc[ev.seller_id == "d", "seller_id"] = "zz"          # zz is not in the seller table
    e1 = M.exposure_ratio(ev, SELLERS, k=2, n_boot=0)
    assert M.UNASSIGNED in set(e1["seller_size"])
    st = M.evaluate_statuses(default_declaration(k=2), e1)
    assert [x["status"] for x in st["E1"] if x["cohort"] == M.UNASSIGNED] == [None]


def test_e2_hand_example_event_weighted():
    # Normalised rank = (rank - 0.5) / depth.
    # Event 1 (depth 4): Small at ranks 1 and 4 -> (0.125 + 0.875) / 2 = 0.5
    # Event 2 (depth 6): Small at ranks 4, 5, 6 -> (3.5 + 4.5 + 5.5) / 6 / 3 = 0.75
    # Each event counts equally: E2(Small) = (0.5 + 0.75) / 2 = 0.625
    # (Pooling the five listings instead would give (1.0 + 2.25) / 5 = 0.65.)
    # Large: event 1 ranks 2, 3 -> 0.5 ; event 2 ranks 1, 2, 3 -> 0.25 ; E2 = 0.375
    e2 = M.mean_rank_position(_two_events(), SELLERS, n_boot=0).set_index("seller_size")
    assert abs(e2.loc["Small", "E2"] - 0.625) < 1e-12
    assert abs(e2.loc["Large", "E2"] - 0.375) < 1e-12


def test_e3_includes_sellers_with_no_top_k_position():
    # K = 2 over both events. Top-2 positions: e1 -> a, c ; e2 -> c, d.
    # Small: a = 1, b = 0. Gini of (0, 1) = 0.5.  Large: c = 2, d = 1. Gini of (1, 2) = 1/6.
    e3 = M.exposure_concentration(_two_events(), SELLERS, k=2).set_index("seller_size")
    assert abs(e3.loc["Small", "E3"] - 0.5) < 1e-12
    assert abs(e3.loc["Large", "E3"] - 1 / 6) < 1e-12
    assert e3.loc["Small", "n_sellers_zero_top_k"] == 1
    # All four sellers: counts (0, 1, 1, 2). Gini = 0.375.
    assert abs(e3.loc["All sellers", "E3"] - 0.375) < 1e-12


def test_classify_boundaries():
    assert M.classify_ci(0.85, 1.00) == "PASS"
    assert M.classify_ci(0.80, 0.849) == "MONITOR"
    assert M.classify_ci(0.60, 0.799) == "REVIEW_REQUIRED"
    assert M.classify_ci(0.79, 0.81) == "INSUFFICIENT_DATA"
    assert M.classify_ci(0.84, 0.86) == "INSUFFICIENT_DATA"
    assert M.classify_ci(np.nan, 0.9) == "INSUFFICIENT_DATA"
    assert M.classify_drift_ci(-9.9, 5.0) == "PASS"
    assert M.classify_drift_ci(-19.9, -10.0) == "MONITOR"
    assert M.classify_drift_ci(-40.0, -20.0) == "REVIEW_REQUIRED"
    assert M.classify_drift_ci(-25.0, -15.0) == "INSUFFICIENT_DATA"
    # thresholds are parameters, not constants
    assert M.classify_ci(0.86, 0.88, review_line=0.80, monitor_line=0.90) == "MONITOR"


def test_size_cohorts_ties_and_missing():
    v = pd.Series([1, 1, 1, 2, 3, 4, 5, 9, 9, np.nan])
    c = M.assign_size_cohorts(v)
    # nine values: lower quartile = 1, upper quartile = 5. Ties at a cut-off stay together.
    assert list(c[:3]) == ["Small"] * 3 and list(c[6:9]) == ["Large"] * 3
    assert list(c[3:6]) == ["Medium"] * 3 and c.iloc[9] == M.UNASSIGNED
    try:
        M.assign_size_cohorts(pd.Series([7, 7, 7, 7]))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_size_cohorts_partition_under_heavy_ties():
    # heavy ties at both cut-offs, and a shuffled copy: every labelled seller gets exactly one of
    # Small/Medium/Large, missing values get Unassigned, and the result does not depend on row order
    for v in (pd.Series([1] * 5 + [2] + [3] * 5), pd.Series([1, 1, 1, 2, 2, 3, 3, 3]),
              pd.Series([0, 0, 0, 5, 5, 5, 5, 5, 5, 9, 9, 9, np.nan])):
        c = M.assign_size_cohorts(v)
        assert set(c[v.notna()]) <= {"Small", "Medium", "Large"} and (c[v.isna()] == M.UNASSIGNED).all()
        lo, hi = v.quantile(0.25), v.quantile(0.75)
        assert not ((c == "Small") & (v > lo)).any() and not ((c == "Large") & (v < hi)).any()
        p = np.random.default_rng(3).permutation(len(v))
        assert (M.assign_size_cohorts(v.iloc[p]).sort_index() == c).all()
    # [1,2,2,2,2,2,2,3]: both quartiles fall inside the run of 2s -> refused, never a silent overlap
    try:
        M.assign_size_cohorts(pd.Series([1, 2, 2, 2, 2, 2, 2, 3]))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_e1_cohort_without_listings_is_not_evaluated():
    ev = pd.DataFrame({"event_id": ["e1"] * 12 + ["e2"] * 12, "seller_id": [f"s{i % 6}" for i in range(24)],
                       "rank_position": list(range(1, 13)) * 2})
    sel = pd.DataFrame({"seller_id": [f"s{i}" for i in range(6)],
                        "seller_size": ["Small", "Small", "Medium", "Medium", "Large", "Large"]})
    base = M.exposure_ratio(ev, sel, n_boot=200, seed=1).set_index("seller_size")
    # a cohort with no listings anywhere, and one present only in an excluded event (no more than K listings)
    sel2 = pd.concat([sel, pd.DataFrame({"seller_id": ["g1", "x1"], "seller_size": ["Ghost", "Excluded"]})])
    ev2 = pd.concat([ev, pd.DataFrame({"event_id": ["e3"] * 3, "seller_id": ["x1"] * 3, "rank_position": [1, 2, 3]})])
    r = M.exposure_ratio(ev2, sel2, n_boot=200, seed=1).set_index("seller_size")
    for c in ("Ghost", "Excluded"):
        assert r.loc[c, "expected_positions"] == 0 and np.isnan(r.loc[c, "E1"])
        assert np.isnan(r.loc[c, "E1_ci_lower"]) and np.isnan(r.loc[c, "E1_ci_upper"])
    pd.testing.assert_frame_equal(r.loc[base.index, ["E1", "E1_ci_lower", "E1_ci_upper"]],
                                  base[["E1", "E1_ci_lower", "E1_ci_upper"]])
    st = {x["cohort"]: x["status"] for x in M.evaluate_statuses(default_declaration(), r.reset_index())["E1"]}
    assert st["Ghost"] == st["Excluded"] == "NOT_EVALUATED"
    assert all(st[c] != "NOT_EVALUATED" for c in base.index)


def test_tenure_uses_calendar_months():
    # Audit start 29 Feb 2024; 12 calendar months earlier is 28 Feb 2023 (no 29 Feb 2023).
    d = pd.Series(["2023-02-28", "2023-03-01", "2022-06-01", None])
    c = M.assign_tenure_cohorts(d, "2024-02-29")
    assert list(c) == ["Established", "New", "Established", M.UNASSIGNED]
    # 365 days is not 12 months across a leap day: 1 Mar 2023 is 365 days before 29 Feb 2024
    # yet is New under the calendar rule.
    assert (pd.Timestamp("2024-02-29") - pd.Timestamp("2023-03-01")).days == 365


def test_declaration_rules_and_retrieved_scope_has_no_status():
    d = default_declaration()
    d.validate()
    ext = M.AuditDeclaration(audit_mode="external", population_type="retrieved",
                             population_detail="top 50 results", fixed_on="2026-01-05")
    ext.validate()
    e1 = M.exposure_ratio(_two_events(), SELLERS, k=2, n_boot=0)
    st = M.evaluate_statuses(ext, e1)
    assert st["carries_status"] is False and all(x["status"] is None for x in st["E1"])
    assert st["O3"] == "Not evaluated"
    for bad in (dict(audit_mode="external", population_type="candidates"),
                dict(audit_mode="platform", population_type="candidates", fixed_on="")):
        kw = dict(audit_mode="platform", population_type="candidates", population_detail="x", fixed_on="2026-01-05")
        kw.update(bad)
        try:
            M.AuditDeclaration(**kw).validate()
            assert False, "expected ValueError"
        except ValueError:
            pass


def test_generator_is_deterministic():
    def digest(seed):
        ev, se = generate(n_events=120, n_sellers=300, seed=seed)
        return hashlib.sha256((ev.to_csv(index=False) + se.to_csv(index=False)).encode()).hexdigest()
    assert digest(11) == digest(11) and digest(11) != digest(12)


def test_neutral_ranker_passes_and_v1_formula_would_not():
    ev, se = generate(n_events=1500, n_sellers=1500, seed=5)
    e1 = M.exposure_ratio(ev, se, seed=5)
    st = M.evaluate_statuses(default_declaration(), e1)
    assert all(x["status"] == "PASS" for x in st["E1"])
    for _, r in e1.iterrows():
        assert r["E1_ci_lower"] <= 1.0 <= r["E1_ci_upper"] or abs(r["E1"] - 1) < 0.03
    # the superseded per-seller formula on the same data: Small far below 0.80 with no ranking bias at all
    top = ev[ev["rank_position"] <= 10].merge(se[["seller_id", "seller_size"]], on="seller_id")
    v1_small = (top["seller_size"] == "Small").mean() / (se["seller_size"] == "Small").mean()
    assert v1_small < 0.5


def test_penalised_cohort_is_flagged():
    ev, se = generate(n_events=1500, n_sellers=1500, seed=6, penalty={"Small": 0.05})
    e1 = M.exposure_ratio(ev, se, seed=6).set_index("seller_size")
    assert M.classify_ci(e1.loc["Small", "E1_ci_lower"], e1.loc["Small", "E1_ci_upper"]) == "REVIEW_REQUIRED"


def test_s2_identical_versions_and_a_worse_version():
    ev, se = generate(n_events=800, n_sellers=1000, seed=7)
    same = M.model_regression(ev, ev, se, "Small", design="paired", seed=1)
    assert abs(same["S2_ratio"] - 1) < 1e-12 and same["S2_ci_lower"] == 1 and same["S2_ci_upper"] == 1
    worse, _ = generate(n_events=800, seed=8, penalty={"Small": 0.03}, sellers=se, event_prefix="N")
    r = M.model_regression(ev, worse, se, "Small", design="independent", seed=1)
    assert r["S2_ci_upper"] < 1 and r["S2_ratio"] < 1


def test_s1_stable_then_drop():
    _, se = generate(n_events=10, n_sellers=1000, seed=9)
    weeks = [generate(n_events=700, seed=20 + i, sellers=se, event_prefix=f"W{i}_")[0] for i in range(5)]
    # A stable system must not be reported as a confirmed decline. (A 95% interval
    # excludes zero about one time in twenty by construction, so the test checks the
    # status, which needs the whole interval at or below the -10% line to raise Monitor.)
    stable = M.exposure_drift(weeks[4], weeks[:4], se, "Small", seed=1)
    assert M.classify_drift_ci(stable["S1_ci_lower"], stable["S1_ci_upper"]) in ("PASS", "INSUFFICIENT_DATA")
    dropped, _ = generate(n_events=700, seed=30, sellers=se, penalty={"Small": 0.05}, event_prefix="D")
    d = M.exposure_drift(dropped, weeks[:4], se, "Small", seed=1)
    assert M.classify_drift_ci(d["S1_ci_lower"], d["S1_ci_upper"]) == "REVIEW_REQUIRED"
    # hand check of the point formula
    assert abs(d["S1_pct"] - 100 * (d["E1_current"] / d["E1_baseline_mean"] - 1)) < 1e-9


def test_non_mrfs_review_line_is_flagged_exploratory():
    ev = pd.DataFrame({"event_id": ["e1"] * 12, "item_id": [f"i{i}" for i in range(12)],
                       "seller_id": ["a"] * 6 + ["b"] * 6, "rank_position": list(range(1, 13))})
    se = pd.DataFrame({"seller_id": ["a", "b"], "seller_size": ["Small", "Large"]})
    e1 = M.exposure_ratio(ev, se, k=10, seed=1)
    base = dict(audit_mode="platform", population_type="candidates", population_detail="final stage",
                fixed_on="2026-11-15")
    std = M.evaluate_statuses(M.AuditDeclaration(**base), e1)
    assert std["mrfs_status"] is True and std["note"] == ""
    assert all(r["mrfs_status"] for r in std["E1"] if r["status"] is not None)
    alt = M.evaluate_statuses(M.AuditDeclaration(review_line=0.75, **base), e1)
    assert alt["mrfs_status"] is False and "not MRFS statuses" in alt["note"]
    assert not any(r["mrfs_status"] for r in alt["E1"])
    ext = M.evaluate_statuses(M.AuditDeclaration(audit_mode="external", population_type="retrieved",
                                                 population_detail="top 30", fixed_on="2026-11-15"), e1)
    assert ext["mrfs_status"] is False and all(r["status"] is None for r in ext["E1"])


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        fn()
        print("ok  ", name)
    print(f"{len(tests)} tests passed")
