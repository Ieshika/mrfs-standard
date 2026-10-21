# Applying MRFS to your own ranking data

This guide shows how to run an MRFS audit on your own data with the reference implementation. It takes about 15 minutes. Everything runs on your own machine: no data is sent anywhere.

It is a practical guide, not part of the standard. Definitions and decision rules are in the [MRFS Technical Standard](MRFS-Technical-Standard.pdf).

## 1. Set up

You need Python 3 with numpy and pandas.

```
git clone https://github.com/Ieshika/mrfs-standard.git
cd mrfs-standard
pip install -r requirements.txt
```

## 2. Prepare two files

**`events.csv`**: one row per listing in the comparison population of each ranking event. A ranking event is one search or recommendation request that returns an ordered list.

| Column | Meaning |
|---|---|
| `event_id` | Identifier of the ranking event, shared by all its rows |
| `item_id` | Identifier of the listing |
| `seller_id` | Identifier of the listing's seller |
| `rank_position` | Position in the ordered list (1 = top). Leave empty for a candidate that was considered but not placed in the list |

Include every candidate the ranking system considered at the stage you are auditing, not only the listings shown. Without the candidates, E1 cannot tell whether a group is under-represented relative to what was available. If you can only see public results, see [External assessment](#external-assessment-public-results-only) below.

**`sellers.csv`**: one row per seller.

| Column | Meaning |
|---|---|
| `seller_id` | Matches `events.csv` |
| `seller_size` | The seller's group, e.g. Small, Medium, Large |

Sellers missing from this file are reported as "Unassigned". If you have each seller's completed orders over the 12 months before the audit, `metrics.assign_size_cohorts()` creates the MRFS default size groups (quartiles).

Identifiers can be pseudonymised. Nothing else is needed for the exposure measures.

**No data yet?** To try the steps on a synthetic marketplace, run from the repository root:

```
python -c "import sys; sys.path.insert(0,'src'); import numpy as np; from generate_synthetic_audit import generate, make_sellers; s=make_sellers(2000, np.random.default_rng(1)); e,_=generate(n_events=3000, sellers=s, penalty={'Small':0.03}, seed=7); e[['event_id','item_id','seller_id','rank_position']].to_csv('events.csv', index=False); s[['seller_id','seller_size']].to_csv('sellers.csv', index=False)"
```

This builds a marketplace in which Small sellers are deliberately ranked lower, so the audit has something to find.

## 3. Declare your choices, then run

Save the following as `run_my_audit.py` in the repository root. Fill in the declaration **before** you look at any results: MRFS requires the audit's choices to be fixed in advance.

```python
import sys
import pandas as pd
sys.path.insert(0, "src")          # run from the repository root
import metrics as M

events = pd.read_csv("events.csv")
sellers = pd.read_csv("sellers.csv")

# 1. Declare your choices before looking at any results.
declaration = M.AuditDeclaration(
    audit_mode="platform",                  # "platform" or "external"
    population_type="candidates",           # "candidates" (platform) or "retrieved" (external)
    population_detail="all candidates returned by retrieval",  # name the stage, or the depth N
    k=10,
    cohort_definitions={"seller_size": "quartiles of completed orders, 12 months before the audit"},
    fixed_on="2026-10-20",                  # the date you fixed these choices
)

# 2. Compute the measures.
e1 = M.exposure_ratio(events, sellers, k=declaration.k, cohort_col="seller_size", seed=1)
e2 = M.mean_rank_position(events, sellers, cohort_col="seller_size", seed=1)
e3 = M.exposure_concentration(events, sellers, k=declaration.k, cohort_col="seller_size")
statuses = M.evaluate_statuses(declaration, e1)

# 3. Report.
pd.set_option("display.width", 160); pd.set_option("display.max_columns", None)
print(e1[["seller_size", "top_k_positions", "expected_positions", "E1", "E1_ci_lower", "E1_ci_upper", "n_events"]].round(3))
print()
print(f"ranking events used: {int(e1['n_events'].iloc[0])}, excluded: {int(e1['n_events_excluded'].iloc[0])}")
if e1["n_events"].iloc[0] == 0:
    print("No ranking events could be used: each needs more than K listings in its comparison population.")
for r in statuses["E1"]:
    print(f"{r['cohort']:<12} E1 {r['E1']:.3f}  status: {r['status'] or 'none (external assessment)'}")
print()
print(e2.round(3))
print()
print(e3.round(3))
```

Then run `python run_my_audit.py`.

### External assessment (public results only)

If you can see only the results a platform shows (for example, results you collected for a fixed set of searches), run an external assessment. Three things change:

1. **`events.csv`** holds every result retrieved for each search, down to a fixed depth N, all with a `rank_position`. There are no unranked candidates.
2. **N must be greater than K.** Searches with no more than K results in the file are excluded, so with N = K every search is excluded and E1 is empty. For K = 10, collect at least the top 20 or 30 results.
3. **The declaration** says so:

```python
declaration = M.AuditDeclaration(
    audit_mode="external",
    population_type="retrieved",
    population_detail="top 30 results for a fixed panel of 200 searches",
    k=10,
    cohort_definitions={"seller_size": "quartiles of active listing count (proxy), observed sellers"},
    fixed_on="2026-10-20",
)
```

The results describe placement among the retrieved results only, and carry no status. In an external assessment the seller groups usually come from publicly visible information such as listing counts, which should be labelled as a proxy. Collect and use only data you are entitled to use under the platform's terms.

## 4. Read the output

On the synthetic example, the first lines look like this:

```
  seller_size  top_k_positions  expected_positions     E1  E1_ci_lower  E1_ci_upper  n_events
0       Large          20155.0           19654.708  1.025        1.018        1.033      3000
1      Medium           9079.0            8999.333  1.009        0.993        1.024      3000
2       Small            766.0            1345.958  0.569        0.532        0.607      3000

ranking events used: 3000, excluded: 0
Large        E1 1.025  status: PASS
Medium       E1 1.009  status: PASS
Small        E1 0.569  status: REVIEW_REQUIRED
```

- **E1** is the group's top-K positions divided by the number it would hold in proportion to its share of the candidates. 1.0 means proportional; below 1.0 means fewer top positions.
- **E1_ci_lower / E1_ci_upper** is the 95% confidence interval.
- **Status** is decided from the whole interval, using the MRFS defaults:

| Status | Meaning |
|---|---|
| PASS | The whole interval is at or above 0.85 |
| MONITOR | The whole interval is between 0.80 and 0.85 |
| REVIEW_REQUIRED | The whole interval is below 0.80: a potential disparity to investigate |
| INSUFFICIENT_DATA | The interval crosses a line. The data cannot decide; this is a legitimate result, not a pass. More ranking events narrow the interval |
| NOT_EVALUATED | The group had no listings in the comparison population |

- **E2** (normalised mean rank; 0.5 = middle of the list, lower is better) and **E3** (concentration of top positions across sellers; 0 = evenly spread) are descriptive and carry no status.
- An **external assessment** (`population_type="retrieved"`) reports ratios and intervals only, with no status.

A REVIEW_REQUIRED status is a signal for investigation, not proof of unfair treatment. E1 is not adjusted for relevance, inventory quality or buyer intent; Sections 3 to 6 of the Technical Standard explain how to investigate and what the results cannot show.

## 5. Questions and feedback

If you apply MRFS to real data, I would value hearing what worked, what was unclear and what went wrong, including results that seem implausible. You need not share any data or results to do so.

Ieshika Chandra · https://github.com/Ieshika/mrfs-standard · https://doi.org/10.5281/zenodo.22073259
