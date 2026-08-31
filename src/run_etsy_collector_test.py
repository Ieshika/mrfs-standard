"""
MRFS Etsy Pilot Collector -- Unit Tests (src/run_etsy_collector_test.py)

Tests the persistent shop-info cache and the seller_tenure boundary logic in
etsy_pilot_collector.py, entirely offline via monkeypatched fetch_shop /
fetch_listings_for_query -- no ETSY_API_KEY, ETSY_SHARED_SECRET, or network
access required.

Covers:
  1-2. Shop cache save/reload round-trip, including an empty-dict save (a
       real bug found and fixed during this test's own development: writing
       an empty cache produced a header-less CSV that crashed the next
       load with pandas.errors.EmptyDataError).
  3.   A cache hit for a fresh entry skips the API call entirely; an
       uncached shop still gets fetched.
  4.   A cache entry older than SHOP_CACHE_STALENESS_DAYS triggers a
       refetch.
  5.   An API failure on a refresh attempt falls back to the stale cached
       row rather than dropping the seller from that window.
  6.   An API failure with no cache at all still skips the seller
       (unchanged legacy behavior).
  7.   seller_tenure boundary exactness against Volume 3 Section 3.1
       ("New: <=12 months on platform" / "Established: >12 months on
       platform") -- a shop at exactly 365 days must classify as New, not
       Established. Uses a monkeypatched fixed clock so the exact-boundary
       case is deterministic rather than racing the real wall clock.

Run: python3 run_etsy_collector_test.py
"""

import os
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import etsy_pilot_collector as c

os.environ["ETSY_API_KEY"] = "test-key"
os.environ["ETSY_SHARED_SECRET"] = "test-secret"

TEST_CACHE = os.path.join(tempfile.gettempdir(), "mrfs_etsy_collector_test_cache.csv")
c.SHOP_CACHE_PATH = TEST_CACHE
if os.path.exists(TEST_CACHE):
    os.remove(TEST_CACHE)

now = datetime.now(timezone.utc).timestamp()

# ---- Tests 1-2: cache save/reload round-trip, including the empty-dict case ----
cache = c._load_shop_cache(TEST_CACHE)
assert cache == {}, cache
print("OK 1: empty cache loads as {}")

fake_cache = {
    111: {"shop_name": "ShopA", "listing_count": 50, "create_epoch": now - 400 * 86400, "fetched_at_epoch": now},
    222: {"shop_name": "ShopB", "listing_count": 12, "create_epoch": None, "fetched_at_epoch": now - 10 * 86400},
}
c._save_shop_cache(fake_cache, TEST_CACHE)
reloaded = c._load_shop_cache(TEST_CACHE)
assert reloaded[111]["shop_name"] == "ShopA"
assert reloaded[111]["listing_count"] == 50
assert reloaded[222]["create_epoch"] is None, reloaded[222]["create_epoch"]
assert abs(reloaded[111]["fetched_at_epoch"] - now) < 1
print("OK 2: save/reload round-trip preserves values, including None create_epoch")

c._save_shop_cache({}, TEST_CACHE)
reloaded_empty = c._load_shop_cache(TEST_CACHE)
assert reloaded_empty == {}, reloaded_empty
print("OK 2b: saving then reloading an empty cache round-trips to {} (regression: used to raise EmptyDataError)")

# ---- Test 3: cache hit skips the API call; uncached shop still gets fetched ----
call_log = []


def fake_fetch_listings(query, api_key, limit=50):
    return [
        {"shop_id": 111, "listing_id": 1, "taxonomy_id": 1, "title": "t1"},
        {"shop_id": 333, "listing_id": 2, "taxonomy_id": 1, "title": "t2"},
    ]


def fake_fetch_shop(shop_id, api_key):
    call_log.append(shop_id)
    if shop_id == 333:
        return {"shop_name": "ShopC", "listing_active_count": 30, "create_date": now - 100 * 86400}
    raise AssertionError(f"should not fetch shop {shop_id}, expected cache hit")


c.fetch_listings_for_query = fake_fetch_listings
c.fetch_shop = fake_fetch_shop
c.QUERIES = ["fakequery"]

c._save_shop_cache(
    {111: {"shop_name": "ShopA", "listing_count": 50, "create_epoch": now - 400 * 86400, "fetched_at_epoch": now}},
    TEST_CACHE,
)
events_df, sellers_df = c.collect(run_timestamp="2026-08-31T00:00:00+00:00")
assert call_log == [333], call_log
print("OK 3: cache hit for shop 111 skipped the API call; only uncached shop 333 was fetched")

assert set(sellers_df["seller_id"]) == {111, 333}
row111 = sellers_df[sellers_df["seller_id"] == 111].iloc[0]
assert row111["seller_tenure"] == "Established"  # 400 days old
row333 = sellers_df[sellers_df["seller_id"] == 333].iloc[0]
assert row333["seller_tenure"] == "New"  # 100 days old
print("OK 3b: seller_tenure correctly derived fresh from cached/fetched create_epoch")

# ---- Test 4: a stale cache entry (older than SHOP_CACHE_STALENESS_DAYS) gets refreshed ----
call_log.clear()
stale_time = now - (c.SHOP_CACHE_STALENESS_DAYS + 1) * 86400
c._save_shop_cache(
    {111: {"shop_name": "ShopA-OLD", "listing_count": 999, "create_epoch": now - 400 * 86400, "fetched_at_epoch": stale_time}},
    TEST_CACHE,
)


def fake_fetch_shop_refresh(shop_id, api_key):
    call_log.append(shop_id)
    return {"shop_name": "ShopA-NEW", "listing_active_count": 55, "create_date": now - 400 * 86400}


def fake_fetch_listings_single(query, api_key, limit=50):
    return [{"shop_id": 111, "listing_id": 1, "taxonomy_id": 1, "title": "t1"}]


c.fetch_shop = fake_fetch_shop_refresh
c.fetch_listings_for_query = fake_fetch_listings_single
events_df, sellers_df = c.collect(run_timestamp="2026-08-31T00:00:00+00:00")
assert call_log == [111], call_log
row = sellers_df[sellers_df["seller_id"] == 111].iloc[0]
assert row["shop_name"] == "ShopA-NEW"
print("OK 4: stale cache entry (older than the staleness window) triggers a refetch")

# ---- Test 5: an API failure on a refresh attempt falls back to the stale cache ----
call_log.clear()
c._save_shop_cache(
    {111: {"shop_name": "ShopA-STALE-BUTOK", "listing_count": 77, "create_epoch": now - 400 * 86400, "fetched_at_epoch": stale_time}},
    TEST_CACHE,
)


def fake_fetch_shop_fail(shop_id, api_key):
    call_log.append(shop_id)
    raise c.EtsyApiError("simulated transient failure")


c.fetch_shop = fake_fetch_shop_fail
events_df, sellers_df = c.collect(run_timestamp="2026-08-31T00:00:00+00:00")
assert 111 in set(sellers_df["seller_id"]), "seller should not be dropped when a stale cache exists to fall back on"
row = sellers_df[sellers_df["seller_id"] == 111].iloc[0]
assert row["shop_name"] == "ShopA-STALE-BUTOK"
print("OK 5: refresh failure with an existing stale cache falls back instead of dropping the seller")

# ---- Test 6: an API failure with no cache at all still skips the seller (unchanged legacy behavior) ----
c._save_shop_cache({}, TEST_CACHE)


def fake_fetch_listings_uncached(query, api_key, limit=50):
    return [{"shop_id": 999, "listing_id": 1, "taxonomy_id": 1, "title": "t1"}]


c.fetch_listings_for_query = fake_fetch_listings_uncached
events_df, sellers_df = c.collect(run_timestamp="2026-08-31T00:00:00+00:00")
assert sellers_df.empty or 999 not in set(sellers_df["seller_id"])
print("OK 6: no-cache + API failure still skips the seller (unchanged behavior)")

# ---- Test 7: seller_tenure boundary exactness ----
# Volume 3 Section 3.1 (Primary Cohort Splits): "New: <=12 months on
# platform" / "Established: >12 months on platform". A shop at exactly 365
# days must land in New, not Established -- this was a real bug (>= instead
# of >) found by inspecting the spec text directly, fixed alongside this
# test. Uses a monkeypatched fixed clock so the exact-boundary case is
# deterministic rather than racing the few milliseconds between constructing
# create_epoch and collect() computing its own now_epoch.
FIXED_NOW = 1_800_000_000.0


class _FakeDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime.fromtimestamp(FIXED_NOW, tz=tz)


c.datetime = _FakeDatetime

boundary_cases = [
    (364, "New"),
    (365, "New"),            # exact boundary: Volume 3 Section 3.1 says <=12mo is New
    (365.0001, "Established"),
    (366, "Established"),
]
for shop_id, (age_days_val, expected) in enumerate(boundary_cases, start=2000):
    c._save_shop_cache({}, TEST_CACHE)
    create_epoch = FIXED_NOW - age_days_val * 86400

    def fake_fetch_listings_boundary(query, api_key, limit=50, _sid=shop_id):
        return [{"shop_id": _sid, "listing_id": 1, "taxonomy_id": 1, "title": "t1"}]

    def fake_fetch_shop_boundary(sid, api_key, _ce=create_epoch):
        return {"shop_name": f"Shop{sid}", "listing_active_count": 10, "create_date": _ce}

    c.fetch_listings_for_query = fake_fetch_listings_boundary
    c.fetch_shop = fake_fetch_shop_boundary
    events_df, sellers_df = c.collect(run_timestamp="2026-08-31T00:00:00+00:00")
    row = sellers_df[sellers_df["seller_id"] == shop_id].iloc[0]
    assert row["seller_tenure"] == expected, f"age_days={age_days_val}: expected {expected}, got {row['seller_tenure']}"
    print(f"OK 7 ({age_days_val}d -> {expected}): correct")

c.datetime = datetime  # restore the real clock

if os.path.exists(TEST_CACHE):
    os.remove(TEST_CACHE)

print("\nALL TESTS PASSED")
