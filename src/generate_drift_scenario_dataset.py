"""
Generates synthetic weekly marketplace ranking datasets for the S1 (drift)
and S2 (model regression) scenario test.

Two scenarios, same generator, one flag:

  inject_drift=True  -- "TRUE POSITIVE" scenario. Weeks 0..drift_start_week-1
                        run under model_version v1.0 with proportionally-fair
                        rank assignment (independent of seller cohort, same
                        construction as generate_fair_dataset.py). At
                        drift_start_week, model_version changes to v1.1 and a
                        real rank-position penalty is introduced against
                        "Small" sellers -- this is the regression S1/S2 must
                        catch.

  inject_drift=False -- "TRUE NEGATIVE" / null-control scenario. Same model
                        version change at the same week, same seed family,
                        but NO rank penalty is applied -- rank stays
                        independent of cohort throughout. S1 must NOT flag
                        this as drift; it exists to check the drift metric
                        doesn't cry wolf on an ordinary version bump with no
                        underlying behavioral change.

See docs/Validation_Addendum_Drift_Regression_Test.md for the full write-up.
"""

import numpy as np
import pandas as pd


def generate_weekly_dataset(n_sellers: int = 2000, weeks: int = 16,
                            events_per_week: int = 6000, drift_start_week: int = 8,
                            inject_drift: bool = True, drift_penalty: float = 0.35,
                            seed: int = 42):
    rng = np.random.default_rng(seed)

    seller_ids = [f"seller_{i:05d}" for i in range(n_sellers)]
    sizes = rng.choice(["Small", "Large", "Medium"], size=n_sellers, p=[0.25, 0.25, 0.50])
    tenure = rng.choice(["New", "Established"], size=n_sellers, p=[0.30, 0.70])
    categories = [f"cat_{i}" for i in range(10)]
    primary_cat = rng.choice(categories, size=n_sellers)
    listing_count = rng.integers(1, 500, size=n_sellers)

    sellers = pd.DataFrame({
        "seller_id": seller_ids,
        "seller_size": sizes,
        "seller_tenure": tenure,
        "category_primary": primary_cat,
        "listing_count": listing_count,
    })
    size_lookup = sellers.set_index("seller_id")["seller_size"]

    events_per_batch = 20
    n_batches_per_week = events_per_week // events_per_batch

    rows = []
    for week in range(weeks):
        model_version = "v1.0" if week < drift_start_week else "v1.1"
        post_change = week >= drift_start_week
        base_ts = pd.Timestamp("2026-01-01") + pd.Timedelta(weeks=week)

        for b in range(n_batches_per_week):
            event_id = f"evt_w{week:02d}_{b:05d}"
            cat = rng.choice(categories)
            chosen = rng.choice(seller_ids, size=events_per_batch, replace=False)

            if inject_drift and post_change:
                # Real regression: Small sellers get a penalty pushing them toward
                # worse (higher-numbered) rank positions. Noise + penalty, then rank
                # by score ascending -> rank 1 (best) .. 20 (worst).
                chosen_sizes = size_lookup.loc[chosen].values
                score = rng.random(events_per_batch)
                score = score + np.where(chosen_sizes == "Small", drift_penalty, 0.0)
                order = np.argsort(score)
                rank_order = np.empty(events_per_batch, dtype=int)
                rank_order[order] = np.arange(1, events_per_batch + 1)
            else:
                # Fair / independent-of-cohort assignment, before AND after the
                # version bump in the null-control scenario -- version string
                # changes but nothing behavioral does.
                rank_order = rng.permutation(events_per_batch) + 1

            for seller_id, rank in zip(chosen, rank_order):
                click_prob = max(0.02, 0.35 - 0.015 * rank)
                was_clicked = rng.random() < click_prob
                was_converted = bool(was_clicked and (rng.random() < 0.15))

                rows.append({
                    "event_id": event_id,
                    "event_timestamp": base_ts,
                    "query_context": f"query_{b % 200}",
                    "category_id": cat,
                    "item_id": f"item_{seller_id}_{rank}",
                    "seller_id": seller_id,
                    "rank_position": int(rank),
                    "was_clicked": bool(was_clicked),
                    "was_converted": was_converted,
                    "model_version": model_version,
                    "week": week,
                })

    events = pd.DataFrame(rows)
    return events, sellers


if __name__ == "__main__":
    for label, inject in [("drift_scenario", True), ("stable_scenario", False)]:
        events, sellers = generate_weekly_dataset(inject_drift=inject, seed=42 if inject else 43)
        events.to_csv(f"{label}_events.csv", index=False)
        sellers.to_csv(f"{label}_sellers.csv", index=False)
        print(f"{label}: {len(events):,} events, {sellers['seller_id'].nunique():,} sellers, "
              f"weeks {events['week'].min()}-{events['week'].max()}")
