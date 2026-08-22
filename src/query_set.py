"""
MRFS Etsy Pilot -- Published Query Set (v1)

Per DECISIONS.md D13: a fixed, versioned, published query list, not ad hoc
queries chosen per run. This is what makes the Etsy pilot reproducible by
someone outside this project -- anyone re-running these exact queries
against Etsy's public Search API should be able to compare results against
this pilot's.

Queries are chosen to span broad, high-competition Etsy categories where
many shops of very different sizes plausibly compete for the same search
terms. Narrow/niche queries were deliberately avoided -- a query with only
one or two plausible sellers can't meaningfully test exposure distribution
across seller-size cohorts.

Do not edit this list in place. If the query set needs to change, bump
QUERY_SET_VERSION and log why in DECISIONS.md (same discipline applied to
any other methodology change -- see D9's fix-priority pattern).
"""

QUERY_SET_VERSION = "v1"

QUERIES = [
    "necklace",
    "earrings",
    "wall art",
    "candle",
    "tumbler",
    "sticker",
    "mug",
    "phone case",
    "planner",
    "coaster",
]
