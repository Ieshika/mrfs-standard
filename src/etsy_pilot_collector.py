"""
MRFS Etsy Real-Data Pilot -- Collector (src/etsy_pilot_collector.py)

Reference implementation component (see DECISIONS.md D12). Collects public,
read-only search-listing data from Etsy's Open API v3 for the fixed query
set in query_set.py, and shapes it into the events/sellers DataFrame
contract metrics.py expects (see metrics.py's module docstring).

Scope limit (DECISIONS.md D13): Etsy's public endpoints expose listings and
their rank order in a search response, but not click-through or conversion
data. This collector can only populate the columns exposure_share_at_k(),
mean_rank_delta(), and exposure_gini() need. It deliberately does NOT
populate was_clicked/was_converted -- outcome_parity() and
evaluate_thresholds() (which require those) are not called anywhere in this
pilot's pipeline. See generate_audit_report.py for how E1-only thresholds
are evaluated instead.

Rank-position caveat: "rank_position" here means the position a listing was
returned in this collector's single API call with sort_on=score (Etsy's
API-exposed relevance sort -- the closest available proxy to on-site search
order). Etsy does not publish its live production ranking algorithm, and
real buyer-facing results can differ from this due to personalization,
promoted listings, and A/B tests. Treat this as an approximation of
exposure order, not a certified match to what any specific buyer sees.

Usage:
    export ETSY_API_KEY="your_keystring_here"
    export ETSY_SHARED_SECRET="your_shared_secret_here"
    python3 etsy_pilot_collector.py
Writes events.csv and sellers.csv into data/etsy_pilot_runs/<run_timestamp>/.

Shop-info cache: listing search results (events) are always fetched fresh --
that's the whole point of a repeated-measurement study. Shop details
(listing_count, shop_name, create_date) are cached across runs in
data/etsy_shop_cache.csv, keyed by seller_id, and only re-fetched once a
cached row is older than SHOP_CACHE_STALENESS_DAYS. Without this, a
multi-window study re-fetches the same largely-overlapping set of shops on
every window; with it, steady-state daily request volume after the first
day or two is roughly just the query count, well inside Etsy's 5,000/day
quota even at several windows/day. seller_tenure is never itself cached --
it's recomputed from the cached create_date against each run's own "now",
since a shop's age keeps advancing even on a cache hit.

Note: despite the variable name, Etsy's Open API v3 requires every request's
x-api-key header to be "<keystring>:<shared_secret>", not the keystring
alone -- documented at
https://developer.etsy.com/documentation/essentials/authentication/, and
confirmed by their own Quick Start tutorial's example for the public /ping
endpoint. ETSY_SHARED_SECRET is that second value, from the same "Your Apps"
page in the Etsy Developer portal as the keystring.
"""

import os
import sys
import time
from datetime import datetime, timezone

import requests
import pandas as pd

from query_set import QUERIES, QUERY_SET_VERSION

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_BASE = "https://api.etsy.com/v3/application"
LISTINGS_PER_QUERY = 50          # top-50 gives headroom above Volume 2's K=10 threshold
REQUEST_DELAY_SECONDS = 1.0      # polite pacing -- not a substitute for reading Etsy's real rate-limit headers
TENURE_THRESHOLD_DAYS = 365      # Volume 3 Section 3.1: New "<=12mo", Established ">12mo" -- age_days > 365 is Established, exactly 365 is New
SHOP_CACHE_PATH = os.path.join(REPO_ROOT, "data", "etsy_shop_cache.csv")
SHOP_CACHE_STALENESS_DAYS = 7     # re-fetch listing_count/shop_name if the cached row is older than this


class EtsyApiError(RuntimeError):
    pass


def _get_api_key() -> str:
    """Returns the x-api-key header value. Etsy's Open API v3 requires this to
    be "<keystring>:<shared_secret>", not the keystring alone -- see this
    module's docstring."""
    key = os.environ.get("ETSY_API_KEY")
    secret = os.environ.get("ETSY_SHARED_SECRET")
    if not key or not secret:
        raise EtsyApiError(
            "ETSY_API_KEY and ETSY_SHARED_SECRET environment variables must both be set. "
            'Run: export ETSY_API_KEY="your_keystring_here" '
            'ETSY_SHARED_SECRET="your_shared_secret_here"'
        )
    return f"{key}:{secret}"


def _request(path: str, params: dict, api_key: str) -> dict:
    url = f"{API_BASE}{path}"
    resp = requests.get(url, params=params, headers={"x-api-key": api_key}, timeout=30)
    if resp.status_code != 200:
        raise EtsyApiError(
            f"Etsy API request failed: GET {resp.url} -> {resp.status_code} {resp.text[:300]}"
        )
    return resp.json()


def fetch_listings_for_query(query: str, api_key: str, limit: int = LISTINGS_PER_QUERY) -> list:
    """Calls GET /listings/active?keywords=... sorted by Etsy's relevance score.
    Returns the raw list of listing dicts, in the order Etsy's API returned them
    (position in this list = rank_position, 1-indexed, for this pilot's purposes).
    """
    data = _request(
        "/listings/active",
        {
            "keywords": query,
            "limit": limit,
            "offset": 0,
            "sort_on": "score",
            "sort_order": "desc",
        },
        api_key,
    )
    return data.get("results", [])


def fetch_shop(shop_id, api_key: str) -> dict:
    return _request(f"/shops/{shop_id}", {}, api_key)


def _load_shop_cache(path: str = SHOP_CACHE_PATH) -> dict:
    """Loads the persistent shop-info cache. Keyed by seller_id (int). Each
    value holds the raw fields fetched from Etsy's /shops/{id} endpoint plus
    fetched_at_epoch -- never a derived label like seller_tenure, since that
    must be recomputed against "now" on every run even for a cache hit (a
    shop's age keeps advancing even when its listing_count doesn't need a
    fresh look)."""
    if not os.path.exists(path):
        return {}
    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        # An empty cache (e.g. the very first run found zero shops) writes a
        # header-less, columnless CSV; treat that the same as "no cache yet"
        # rather than crashing every subsequent run.
        return {}
    cache = {}
    for _, row in df.iterrows():
        cache[int(row["seller_id"])] = {
            "shop_name": row.get("shop_name"),
            "listing_count": row.get("listing_count"),
            "create_epoch": row.get("create_epoch") if pd.notna(row.get("create_epoch")) else None,
            "fetched_at_epoch": float(row["fetched_at_epoch"]),
        }
    return cache


def _save_shop_cache(cache: dict, path: str = SHOP_CACHE_PATH) -> None:
    """Atomic write (temp file + os.replace) so a run interrupted mid-write
    (e.g. a cron job killed by the machine sleeping) can't corrupt the cache
    other windows depend on."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rows = [
        {"seller_id": seller_id, **fields}
        for seller_id, fields in sorted(cache.items())
    ]
    df = pd.DataFrame(rows)
    tmp_path = path + ".tmp"
    df.to_csv(tmp_path, index=False)
    os.replace(tmp_path, path)


def collect(run_timestamp: str = None):
    """
    Runs every query in QUERIES against Etsy's public listings search,
    fetches shop details for every unique shop encountered, and returns
    (events_df, sellers_df) shaped per metrics.py's input contract
    (minus was_clicked/was_converted -- see module docstring).
    """
    api_key = _get_api_key()
    run_timestamp = run_timestamp or datetime.now(timezone.utc).isoformat()

    event_rows = []
    shop_ids_seen = set()
    event_id = 0

    for query in QUERIES:
        print(f"[collector] querying: {query!r}")
        try:
            listings = fetch_listings_for_query(query, api_key)
        except EtsyApiError as e:
            print(f"[collector] WARNING: query {query!r} failed, skipping: {e}", file=sys.stderr)
            continue

        for idx, listing in enumerate(listings):
            rank_position = idx + 1
            shop_id = listing.get("shop_id")
            if shop_id is None:
                continue
            shop_ids_seen.add(shop_id)
            event_id += 1
            event_rows.append({
                "event_id": event_id,
                "event_timestamp": run_timestamp,
                "query_context": query,
                "query_set_version": QUERY_SET_VERSION,
                "category_id": listing.get("taxonomy_id"),
                "item_id": listing.get("listing_id"),
                "seller_id": shop_id,
                "rank_position": rank_position,
                "title": listing.get("title"),
                "model_version": "etsy-live-search-api",
            })

        time.sleep(REQUEST_DELAY_SECONDS)

    events_df = pd.DataFrame(event_rows)

    # Shop info (listing_count, shop_name, create_epoch) is cached across runs,
    # keyed by seller_id -- see _load_shop_cache's docstring for why
    # seller_tenure itself is never cached. Without this, a multi-window study
    # (e.g. 2x/day for 14 days) would re-fetch the same ~90% of shops on every
    # single window; with it, steady-state cost after the first day or two is
    # roughly the query count alone, comfortably inside Etsy's daily quota.
    shop_cache = _load_shop_cache(SHOP_CACHE_PATH)
    now_epoch = datetime.now(timezone.utc).timestamp()
    staleness_seconds = SHOP_CACHE_STALENESS_DAYS * 86400
    seller_rows = []
    cache_hits = 0
    cache_misses = 0
    cache_fallbacks = 0

    for shop_id in sorted(shop_ids_seen):
        cached = shop_cache.get(shop_id)
        is_fresh = cached is not None and (now_epoch - cached["fetched_at_epoch"]) < staleness_seconds

        if is_fresh:
            fields = cached
            cache_hits += 1
        else:
            try:
                shop = fetch_shop(shop_id, api_key)
                create_epoch = shop.get("create_date") or shop.get("created_timestamp")
                fields = {
                    "shop_name": shop.get("shop_name"),
                    "listing_count": shop.get("listing_active_count"),
                    "create_epoch": create_epoch,
                    "fetched_at_epoch": now_epoch,
                }
                shop_cache[shop_id] = fields
                cache_misses += 1
                time.sleep(REQUEST_DELAY_SECONDS)
            except EtsyApiError as e:
                if cached is not None:
                    # API hiccup on a refresh attempt -- fall back to the stale
                    # cached row rather than dropping this seller from the
                    # window entirely (a transient failure shouldn't cost a
                    # seller's whole observation).
                    print(f"[collector] WARNING: shop {shop_id} refresh failed, using stale cache: {e}", file=sys.stderr)
                    fields = cached
                    cache_fallbacks += 1
                else:
                    print(f"[collector] WARNING: shop {shop_id} failed, skipping: {e}", file=sys.stderr)
                    continue

        create_epoch = fields.get("create_epoch")
        age_days = (now_epoch - create_epoch) / 86400 if create_epoch else None
        seller_rows.append({
            "seller_id": shop_id,
            "shop_name": fields.get("shop_name"),
            "listing_count": fields.get("listing_count"),
            "seller_tenure": (
                # Volume 3 Section 3.1 (Primary Cohort Splits) is boundary-exact:
                # "New: <=12 months on platform" / "Established: >12 months on
                # platform" -- a shop at exactly 365 days belongs in New, not
                # Established. Strict > here, not >=.
                "Established" if age_days is not None and age_days > TENURE_THRESHOLD_DAYS
                else "New" if age_days is not None else None
            ),
        })

    _save_shop_cache(shop_cache, SHOP_CACHE_PATH)
    print(
        f"[collector] shop cache: {cache_hits} hits, {cache_misses} fetched/refreshed, "
        f"{cache_fallbacks} stale fallbacks (staleness window: {SHOP_CACHE_STALENESS_DAYS}d)"
    )

    sellers_df = pd.DataFrame(seller_rows)

    # Seller-size cohort: median split on listing_count, observed-population-relative
    # (per ARCHITECTURE.md's "Small/Large, listing-volume quartile" cohort scheme).
    # NOTE (DECISIONS.md D15): this pilot uses a median split rather than a strict
    # top/bottom quartile split, to keep the full sample rather than discarding the
    # middle 50% -- a deliberate, logged deviation, not an unstated one.
    if not sellers_df.empty and "listing_count" in sellers_df.columns and sellers_df["listing_count"].notna().any():
        median_count = sellers_df["listing_count"].median()
        sellers_df["seller_size"] = sellers_df["listing_count"].apply(
            lambda n: "Large" if pd.notna(n) and n >= median_count else "Small"
        )
    else:
        sellers_df["seller_size"] = None

    return events_df, sellers_df


def save_run(events_df: pd.DataFrame, sellers_df: pd.DataFrame, run_timestamp: str) -> str:
    safe_ts = run_timestamp.replace(":", "-")
    run_dir = os.path.join(REPO_ROOT, "data", "etsy_pilot_runs", safe_ts)
    os.makedirs(run_dir, exist_ok=True)
    events_df.to_csv(os.path.join(run_dir, "events.csv"), index=False)
    sellers_df.to_csv(os.path.join(run_dir, "sellers.csv"), index=False)
    print(f"[collector] wrote {len(events_df)} events, {len(sellers_df)} sellers to {run_dir}")
    return run_dir


if __name__ == "__main__":
    ts = datetime.now(timezone.utc).isoformat()
    _events_df, _sellers_df = collect(run_timestamp=ts)
    save_run(_events_df, _sellers_df, ts)
