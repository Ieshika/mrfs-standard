"""
MRFS Etsy Pilot -- Query Set Validation (src/validate_query_set.py)

Empirically validates a candidate query set BEFORE it's committed to
query_set.py and BEFORE any longitudinal collection starts. Runs the exact
same collect() logic the real pilot uses (same auth, same shop-info cache,
same seller_tenure/seller_size derivation), against CANDIDATE_QUERIES plus
BACKUP_QUERIES below in a single pass, and reports per-query diagnostics so
a weak or narrow query can be caught and swapped before it costs 28
collection windows -- without a second API round-trip for the backups.

For each candidate query, reports:
  - listings returned (out of the requested top-50)
  - unique shops in that query's top-50
  - uniqueness ratio (unique shops / listings) -- low means a handful of
    shops repeat across many of that query's top-50 slots
  - max single-shop listing count within that query (concentration signal)
  - % Small / Large and % New / Established among that query's unique shops,
    under the *current* seller_size (median split, pooled across all 30
    candidate queries together, matching how the real study computes it --
    not a per-query median) and seller_tenure rules

Flags any query whose unique-shop count, uniqueness ratio, or max
single-shop concentration falls outside the thresholds below, rather than
asserting a verdict from category name alone.

This run also warms the shop-info cache (data/etsy_shop_cache.csv) for
whichever shops it touches, so the first real longitudinal window benefits
from it rather than starting cold.

Usage:
    export ETSY_API_KEY="your_keystring_here"
    export ETSY_SHARED_SECRET="your_shared_secret_here"
    python3 validate_query_set.py
Writes nothing into data/etsy_pilot_runs/ (kept separate from real study
windows) -- output is a console report only.
"""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import etsy_pilot_collector as collector

# Proposed v2 query set (2026-08-31 draft, pending this validation and user
# review): the existing 10 (v1, unchanged per query_set.py's "don't edit in
# place" rule) plus 20 new, spanning ~14 distinct broad, high-competition
# categories rather than clustering in one or two verticals. "wedding
# invitation" is singular to match the existing convention (every v1 query
# is singular except "earrings," which has no natural singular form for the
# category). Not yet written to query_set.py.
CANDIDATE_QUERIES = [
    # v1, unchanged
    "necklace", "earrings", "wall art", "candle", "tumbler",
    "sticker", "mug", "phone case", "planner", "coaster",
    # v2 proposed additions
    "tote bag", "keychain", "bracelet", "wedding invitation", "baby blanket",
    "wall clock", "throw pillow", "soap", "dog collar", "sweatshirt",
    "phone charm", "wallet", "bookmark", "wind chime", "hair clip",
    "tea towel", "apron", "stuffed animal", "yoga mat", "doormat",
]

# "phone charm" and "wall clock" were flagged in user review as possibly
# less "high competition" than the rest of the list, going only on category
# name rather than evidence -- hence this script. Bar for "phone charm"
# specifically, per explicit user direction: it stays in the primary 30
# only if the API results show it's unusually strong, not merely
# adequate/passing the generic thresholds below.
#
# "ring" and "belt" are backup candidates, run in this SAME validation pass
# (one API round-trip, per explicit user direction) so a replacement can be
# picked from real data if phone charm doesn't clear that bar. They are NOT
# part of the primary 30 and are reported in a separate section below.
# Decision rule, stated explicitly because it matters: whichever backup (or
# neither) gets used is chosen on the SAME data-quality criteria as every
# other query in this report -- unique shops, uniqueness ratio, single-shop
# concentration, cohort coverage -- never on which one happens to produce a
# more "interesting" apparent Small/Large or New/Established disparity. That
# would be selecting the query set based on the outcome it's supposed to
# measure, which is exactly the kind of post-hoc distortion this project's
# validation discipline (D9) exists to avoid.
BACKUP_QUERIES = ["ring", "belt"]

# Flag thresholds -- not hard cutoffs, just what makes a query worth a
# second look rather than an automatic verdict.
MIN_UNIQUE_SHOPS = 30          # out of up to 50 listings
MIN_UNIQUENESS_RATIO = 0.60    # unique_shops / listings
MAX_SINGLE_SHOP_SHARE = 0.15   # any one shop's share of that query's listings


def validate():
    all_queries = CANDIDATE_QUERIES + BACKUP_QUERIES
    collector.QUERIES = all_queries
    print(
        f"[validate] running {len(CANDIDATE_QUERIES)} candidate queries + "
        f"{len(BACKUP_QUERIES)} backup candidates ({', '.join(BACKUP_QUERIES)}) "
        f"against the real Etsy API..."
    )
    events_df, sellers_df = collector.collect()

    if events_df.empty:
        print("[validate] no events collected at all -- check ETSY_API_KEY/ETSY_SHARED_SECRET and try again.")
        return None

    print(
        "\n[validate] NOTE: the pct_small/pct_large/pct_new/pct_established columns below are computed "
        f"against the seller_size median split pooled across all {len(all_queries)} queries run in this "
        "validation pass (the 30 primary candidates AND the 2 backups together) -- not the eventual "
        "30-query study pool, which will exclude whichever backup isn't used. The per-query unique_shops / "
        "uniqueness_ratio / concentration numbers are query-local and unaffected by this; only the cohort "
        "percentage columns carry this minor, disclosed approximation."
    )

    sellers_by_id = sellers_df.set_index("seller_id") if not sellers_df.empty else pd.DataFrame()

    rows = []
    for query in all_queries:
        q_events = events_df[events_df["query_context"] == query]
        listings = len(q_events)
        shop_counts = q_events["seller_id"].value_counts()
        unique_shops = shop_counts.shape[0]
        uniqueness_ratio = (unique_shops / listings) if listings else 0.0
        max_shop_listings = int(shop_counts.max()) if listings else 0
        max_shop_share = (max_shop_listings / listings) if listings else 0.0

        if unique_shops > 0 and not sellers_by_id.empty:
            q_shop_ids = [sid for sid in shop_counts.index if sid in sellers_by_id.index]
            q_sellers = sellers_by_id.loc[q_shop_ids] if q_shop_ids else pd.DataFrame()
        else:
            q_sellers = pd.DataFrame()

        def pct(series, value):
            if series is None or len(series) == 0:
                return None
            return round(100 * (series == value).sum() / len(series), 1)

        pct_small = pct(q_sellers.get("seller_size"), "Small") if not q_sellers.empty else None
        pct_large = pct(q_sellers.get("seller_size"), "Large") if not q_sellers.empty else None
        pct_new = pct(q_sellers.get("seller_tenure"), "New") if not q_sellers.empty else None
        pct_established = pct(q_sellers.get("seller_tenure"), "Established") if not q_sellers.empty else None

        flags = []
        if listings == 0:
            flags.append("NO RESULTS")
        else:
            if unique_shops < MIN_UNIQUE_SHOPS:
                flags.append(f"low unique shops ({unique_shops})")
            if uniqueness_ratio < MIN_UNIQUENESS_RATIO:
                flags.append(f"low uniqueness ratio ({uniqueness_ratio:.2f})")
            if max_shop_share > MAX_SINGLE_SHOP_SHARE:
                flags.append(f"concentrated ({max_shop_listings}/{listings} listings from one shop, {max_shop_share:.0%})")

        rows.append({
            "query": query,
            "group": "backup" if query in BACKUP_QUERIES else "primary",
            "listings": listings,
            "unique_shops": unique_shops,
            "uniqueness_ratio": round(uniqueness_ratio, 2),
            "max_shop_listings": max_shop_listings,
            "pct_small": pct_small,
            "pct_large": pct_large,
            "pct_new": pct_new,
            "pct_established": pct_established,
            "flags": "; ".join(flags) if flags else "",
        })

    report_df = pd.DataFrame(rows)
    primary_df = report_df[report_df["group"] == "primary"].drop(columns="group")
    backup_df = report_df[report_df["group"] == "backup"].drop(columns="group")

    pd.set_option("display.max_rows", None)
    pd.set_option("display.width", 200)

    print(f"\n=== PRIMARY {len(CANDIDATE_QUERIES)} (the proposed v2 query set) ===")
    print(primary_df.to_string(index=False))

    flagged = primary_df[primary_df["flags"] != ""]
    print(f"\n[validate] {len(flagged)} of {len(CANDIDATE_QUERIES)} primary queries flagged for review:")
    if not flagged.empty:
        print(flagged[["query", "flags"]].to_string(index=False))
    else:
        print("  (none)")

    print(f"\n=== BACKUP CANDIDATES ({', '.join(BACKUP_QUERIES)}) -- not part of the primary 30 ===")
    print(backup_df.to_string(index=False))
    print(
        "\n[validate] Choose a backup (or neither) using the SAME columns as every other query above -- "
        "unique_shops, uniqueness_ratio, max_shop_listings/concentration, and flags. Do not choose based on "
        "which one shows a bigger apparent pct_small/pct_large or pct_new/pct_established gap -- that would be "
        "selecting the query set based on the outcome it's meant to measure."
    )

    total_unique_shops = sellers_df["seller_id"].nunique() if not sellers_df.empty else 0
    print(f"\n[validate] pooled across all {len(all_queries)} queries run in this pass: {len(events_df)} events, {total_unique_shops} unique shops")
    if not sellers_df.empty and "seller_size" in sellers_df.columns:
        size_counts = sellers_df["seller_size"].value_counts(normalize=True) * 100
        tenure_counts = sellers_df["seller_tenure"].value_counts(normalize=True) * 100
        print(f"[validate] pooled seller_size split (caveat above applies): {size_counts.to_dict()}")
        print(f"[validate] pooled seller_tenure split (caveat above applies): {tenure_counts.to_dict()}")

    return report_df


if __name__ == "__main__":
    validate()
