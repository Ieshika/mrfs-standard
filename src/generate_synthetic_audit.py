"""
Deterministic synthetic marketplace for testing MRFS metrics (version 2).

Everything is produced from a seed, so every number derived from this
generator can be regenerated exactly. One ranking event = one request with
its own candidate set; sizes below are always counted in ranking events.

Model
-----
Sellers have a number of listings (heavy-tailed) and a number of completed
orders in the 12 months before the audit (correlated with listings). Size
cohorts are the MRFS default quartiles of the order count; tenure cohorts
are the MRFS default 12 calendar months from the seller's opening date.

Each ranking event draws its candidate set from all listings, so sellers
with more listings are candidates more often. That is deliberate: it gives
small sellers a small share of candidates, which is the situation the v2
exposure metric is designed to handle.

Every candidate gets a score = Uniform(0,1) + penalty for its seller's size
cohort in that week. Candidates are ordered by score, lowest first. The
first `ordered_depth` receive a rank; the rest stay in the comparison
population with an empty rank. A penalty of zero for every cohort is a
ranker that ignores cohort.

Clicks and conversions are simulated for the top K only: the click
probability falls with position, and can be scaled per cohort.
"""

import argparse
import json
import os

import numpy as np
import pandas as pd

from metrics import AuditDeclaration, assign_size_cohorts, assign_tenure_cohorts

AUDIT_START = "2026-01-05"   # a Monday; weeks are whole calendar weeks from here
CANDIDATE_SIZES = (40, 80, 150, 300)


def make_sellers(n_sellers: int, rng: np.random.Generator) -> pd.DataFrame:
    scale = rng.lognormal(mean=0.0, sigma=1.2, size=n_sellers)
    listings = np.maximum(1, np.round(8 * scale * rng.lognormal(0.0, 0.5, n_sellers))).astype(int)
    orders = np.round(60 * scale * rng.lognormal(0.0, 0.7, n_sellers)).astype(int)
    opened = pd.Timestamp(AUDIT_START) - pd.to_timedelta(rng.integers(1, 6 * 365, n_sellers), unit="D")
    s = pd.DataFrame({"seller_id": [f"S{i:05d}" for i in range(n_sellers)],
                      "listing_count": listings, "size_basis_value": orders,
                      "tenure_reference_date": opened.strftime("%Y-%m-%d")})
    s["seller_size"] = assign_size_cohorts(s["size_basis_value"])
    s["seller_tenure"] = assign_tenure_cohorts(s["tenure_reference_date"], AUDIT_START)
    s["cohort_effective_date"] = AUDIT_START
    return s


def generate(n_events: int = 2000, n_sellers: int = 2000, weeks: int = 1, k: int = 10,
             ordered_depth: int = 50, penalty: dict = None, penalty_by_week: dict = None,
             model_version_by_week: dict = None, base_ctr: float = 0.30, base_cvr: float = 0.12,
             click_scale: dict = None, seed: int = 20260105, sellers: pd.DataFrame = None,
             event_prefix: str = "E"):
    """
    Returns (events, sellers). `penalty` maps a size cohort to a score
    penalty applied in every week; `penalty_by_week` maps week number
    (1-based) to such a dict and overrides `penalty` for that week.
    """
    rng = np.random.default_rng(seed)
    if sellers is None:
        sellers = make_sellers(n_sellers, rng)
    penalty = penalty or {}
    penalty_by_week = penalty_by_week or {}
    model_version_by_week = model_version_by_week or {}
    click_scale = click_scale or {}

    listing_seller = np.repeat(np.arange(len(sellers)), sellers["listing_count"].values)
    n_listings = len(listing_seller)
    size_of_seller = sellers["seller_size"].values
    seller_ids = sellers["seller_id"].values

    week_of_event = np.sort(rng.integers(1, weeks + 1, size=n_events))
    sizes = rng.choice(CANDIDATE_SIZES, size=n_events)
    frames = []
    for L in CANDIDATE_SIZES:
        idx = np.where(sizes == L)[0]
        if not len(idx):
            continue
        cand = np.stack([rng.choice(n_listings, size=L, replace=False) for _ in idx])   # (events, L) listing ids
        seller_idx = listing_seller[cand]
        cohort = size_of_seller[seller_idx]
        pen = np.zeros(cand.shape)
        for row, ev in enumerate(idx):
            p = penalty_by_week.get(int(week_of_event[ev]), penalty)
            for c, v in p.items():
                if v:
                    pen[row] += v * (cohort[row] == c)
        score = rng.random(cand.shape) + pen
        rank = score.argsort(axis=1).argsort(axis=1) + 1
        pos_decay = 1.0 / np.log2(rank + 1)
        scale = np.ones(cand.shape)
        for c, v in click_scale.items():
            scale = np.where(cohort == c, v, scale)
        in_top = rank <= k
        clicked = in_top & (rng.random(cand.shape) < base_ctr * pos_decay * scale)
        converted = clicked & (rng.random(cand.shape) < base_cvr)
        ev_rep = np.repeat(idx, L)
        wk = week_of_event[ev_rep]
        offset = np.repeat(rng.integers(0, 7 * 24 * 3600, size=len(idx)), L)   # one time per event
        ts = pd.Timestamp(AUDIT_START) + pd.to_timedelta((wk - 1) * 7 * 86400 + offset, unit="s")
        rank_flat = rank.ravel().astype(float)
        rank_flat[rank_flat > ordered_depth] = np.nan
        frames.append(pd.DataFrame({
            "event_id": [f"{event_prefix}{e:07d}" for e in ev_rep],
            "week": wk,
            "event_timestamp": ts,
            "item_id": [f"L{x:07d}" for x in cand.ravel()],
            "seller_id": seller_ids[seller_idx.ravel()],
            "rank_position": rank_flat,
            "was_clicked": clicked.ravel().astype(int),
            "was_converted": converted.ravel().astype(int),
            "model_version": [model_version_by_week.get(int(w), "v1") for w in wk],
        }))
    events = pd.concat(frames, ignore_index=True).sort_values(["event_id", "rank_position"], na_position="last")
    events["rank_position"] = events["rank_position"].astype("Int64")
    return events.reset_index(drop=True), sellers


def default_declaration(k: int = 10) -> AuditDeclaration:
    return AuditDeclaration(
        audit_mode="platform", population_type="candidates",
        population_detail="synthetic candidate set (all listings drawn for the request)", k=k,
        cohort_definitions={
            "seller_size": "quartiles of completed orders in the 12 calendar months before audit start; "
                           "Small at or below the lower quartile, Large at or above the upper quartile, Medium between",
            "seller_tenure": "New if the opening date is later than 12 calendar months before audit start",
        },
        upstream_not_captured="none (synthetic)", fixed_on=AUDIT_START)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--events", type=int, default=2000, help="number of ranking events")
    ap.add_argument("--sellers", type=int, default=2000)
    ap.add_argument("--weeks", type=int, default=1)
    ap.add_argument("--small-penalty", type=float, default=0.0, help="score penalty for Small sellers")
    ap.add_argument("--seed", type=int, default=20260105)
    ap.add_argument("--out", default="synthetic_audit")
    a = ap.parse_args()
    ev, se = generate(n_events=a.events, n_sellers=a.sellers, weeks=a.weeks,
                      penalty={"Small": a.small_penalty}, seed=a.seed)
    os.makedirs(a.out, exist_ok=True)
    ev.to_csv(os.path.join(a.out, "events.csv"), index=False)
    se.to_csv(os.path.join(a.out, "sellers.csv"), index=False)
    with open(os.path.join(a.out, "declaration.json"), "w") as f:
        json.dump(default_declaration().to_dict(), f, indent=2)
    print(f"{ev['event_id'].nunique()} ranking events, {len(ev)} candidate rows, {len(se)} sellers -> {a.out}/")
