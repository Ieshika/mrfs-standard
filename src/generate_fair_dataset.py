"""
Generates a synthetic marketplace ranking dataset with NO built-in exposure
disparity: rank position is assigned independent of seller cohort, so a
correctly-functioning audit should NOT flag Review Required status.

This is the counter-test to the existing Sample Audit Report (Volume 6),
which used a dataset intentionally built WITH a disparity. Without this
companion test, there was no evidence the protocol avoids false positives
on a genuinely fair system.
"""

import numpy as np
import pandas as pd


def generate_fair_dataset(n_sellers: int = 5000, n_events: int = 250_000,
                           weeks: int = 12, seed: int = 42):
    rng = np.random.default_rng(seed)

    seller_ids = [f"seller_{i:05d}" for i in range(n_sellers)]
    # Same cohort split as the original Sample Audit Report for comparability: 25/25/50
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

    # Ranking events: for each event, sample ~20 sellers uniformly at random
    # (independent of cohort) and assign rank positions 1..20 by random order.
    # This is the "fair" construction: cohort membership has zero influence
    # on rank position, so exposure should track cohort size proportionally.
    events_per_batch = 20
    n_batches = n_events // events_per_batch

    rows = []
    model_version = "v1.0"
    for b in range(n_batches):
        week = int(b / n_batches * weeks)
        if week == 7:  # mirror the model-version change point used in Vol 6 for comparability
            model_version = "v1.1"
        event_id = f"evt_{b:07d}"
        cat = rng.choice(categories)
        chosen = rng.choice(seller_ids, size=events_per_batch, replace=False)
        rank_order = rng.permutation(events_per_batch) + 1  # ranks 1..20, randomly assigned

        base_ts = pd.Timestamp("2026-01-01") + pd.Timedelta(weeks=week)
        for seller_id, rank in zip(chosen, rank_order):
            # Click/conversion probability depends only on rank (position bias),
            # NOT on cohort -- this is what makes the dataset "fair."
            click_prob = max(0.02, 0.35 - 0.015 * rank)
            was_clicked = rng.random() < click_prob
            was_converted = was_clicked and (rng.random() < 0.15)

            rows.append({
                "event_id": event_id,
                "event_timestamp": base_ts,
                "query_context": f"query_{b % 500}",
                "category_id": cat,
                "item_id": f"item_{seller_id}_{rank}",
                "seller_id": seller_id,
                "rank_position": int(rank),
                "was_clicked": bool(was_clicked),
                "was_converted": bool(was_converted),
                "model_version": model_version,
            })

    events = pd.DataFrame(rows)
    return events, sellers


if __name__ == "__main__":
    events, sellers = generate_fair_dataset()
    events.to_csv("/home/claude/project/src/fair_dataset_events.csv", index=False)
    sellers.to_csv("/home/claude/project/src/fair_dataset_sellers.csv", index=False)
    print(f"Generated {len(events)} events across {sellers['seller_id'].nunique()} sellers")
    print(sellers["seller_size"].value_counts())
