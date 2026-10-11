# Worked example: sample audit report {#app:example}

This appendix is a complete MRFS audit of a synthetic marketplace, following the report contents of Section 3.10. Every figure was produced by the reference implementation from data generated with fixed seeds (Appendix C). The scenario is known to the generator, so the result can be checked against the truth (Appendix A.9). Nothing here is evidence about any real marketplace.

Report identifier: MRFS-SAMPLE-2026-W09-W12.

## Summary

Ranking version v2, deployed in week 9, places listings of Small sellers lower than version v1 did. In the audit window (weeks 9 to 12), E1 for Small sellers is 0.660 (95% interval 0.632–0.688), Review Required at the declared candidate stage; Medium and Large sellers and both tenure cohorts are Pass. The click-through ratio for Small sellers is also Review Required; the conversion ratio is Insufficient Data. E1 for Small sellers is Review Required in every week after the change, while S1 reached Review Required in the first two weeks and then returned to Insufficient Data as the lower values entered the baseline. With size measured by listing count instead of completed orders, Small sellers' E1 is 0.816 and Insufficient Data, so the finding depends on the size measure. These results call for an investigation under Section 4.7; they do not by themselves establish its cause.

## Audit declaration

| Item | Declared value |
|:------------------------|:------------------------------------------------------------|
| Kind of assessment | Platform audit |
| Comparison population | Candidate set: synthetic candidate set (all listings drawn for the request) |
| Stages not captured | None (synthetic) |
| $K$; ordered depth for E2 | 10; 50 |
| Size cohorts | Quartiles of completed orders in the 12 calendar months before audit start; Small at or below the lower quartile, Large at or above the upper quartile, Medium between |
| Tenure cohorts | New if the opening date is later than 12 calendar months before audit start |
| Thresholds | MRFS defaults: Review line 0.80, Monitor line 0.85; drift lines −10% and −20% |
| Data-quality criteria | Rows without a cohort label at most 1.0%; events excluded at most 1.0%; events with an incomplete top $K$ at most 1.0% |
| Windows | Audit window weeks 9 to 12; monitoring window 1 week; 4 baseline windows |
| Resampling unit; strata | Ranking event; none |
| Fixed on | 2026-01-05 |

: Audit declaration of the worked example.

## Data

The audit window holds 6,000 ranking events and 846,110 candidate rows; all events were used. Monitoring history covers 12 weeks at 1,500 ranking events per week, for 2,000 sellers. Candidate sets contain 40 to 300 listings (median 80); the ordered depth is 40 to 50. Rows without a cohort label: 0.0%; events excluded: 0.0%; events with an incomplete top $K$: 0.0%. The declared criteria are met, and no Unassigned group arises.

| Cohort | Share of sellers | Share of candidate listings |
|:----------|----------:|----------:|
| Medium | 49.9% | 33.8% |
| Small | 25.1% | 4.2% |
| Large | 25.0% | 61.9% |
| Established | 83.4% | 85.7% |
| New | 16.7% | 14.3% |

: Cohort shares in the audit window.

## Exposure

| Cohort | E1 | 95% interval | Status | E2 | E2 95% interval |
|:----------|------:|:------------|:------------|------:|:------------|
| Large | 1.014 | 1.008–1.019 | Pass | 0.499 | 0.498–0.500 |
| Medium | 1.018 | 1.008–1.029 | Pass | 0.497 | 0.496–0.499 |
| Small | 0.660 | 0.632–0.688 | Review Required | 0.535 | 0.529–0.540 |
| Established | 1.000 | 0.996–1.003 | Pass | 0.500 | 0.499–0.500 |
| New | 1.001 | 0.981–1.021 | Pass | 0.501 | 0.498–0.504 |

: E1 (exposure ratio at 10) with statuses, and E2 (normalised mean rank; lower is higher up; no status).

| Cohort | E3 | Sellers | Sellers with no top-10 position |
|:----------|------:|------:|------:|
| Large | 0.498 | 500 | 0 |
| Medium | 0.473 | 999 | 9 |
| Small | 0.509 | 501 | 81 |
| All sellers | 0.647 | 2,000 | 90 |
| Established | 0.653 | 1,667 | 77 |
| New | 0.609 | 333 | 13 |

: E3, the Gini index of top-10 positions across sellers in the comparison population (no status).

## Outcomes

| Comparison | Outcome | Cohort rate | Reference rate | O3 | 95% interval | Status |
|:-------------------|:--------------|------:|------:|------:|:------------|:------------|
| Small against Large | Click-through rate | 0.091 | 0.137 | 0.665 | 0.563–0.772 | Review Required |
| Small against Large | Conversion rate | 0.011 | 0.016 | 0.687 | 0.392–1.014 | Insufficient Data |
| New against Established | Click-through rate | 0.134 | 0.136 | 0.979 | 0.921–1.033 | Pass |
| New against Established | Conversion rate | 0.015 | 0.016 | 0.901 | 0.738–1.078 | Insufficient Data |

: Outcome rates of top-10 impressions and O3.

## Stability

::: compact
| Week | E1 | 95% interval | E1 status | Baseline mean | S1 (%) | 95% interval (%) | S1 status |
|-----:|------:|:------------|:------------|------:|------:|:----------------|:------------|
| 5 | 0.969 | 0.903–1.036 | Pass | 0.994 | −2.5 | −10.1 to +5.7 | Insufficient Data |
| 6 | 0.981 | 0.914–1.051 | Pass | 0.999 | −1.8 | −9.1 to +6.4 | Pass |
| 7 | 0.972 | 0.901–1.045 | Pass | 0.998 | −2.6 | −10.6 to +5.5 | Insufficient Data |
| 8 | 1.010 | 0.939–1.078 | Pass | 0.990 | +1.9 | −6.1 to +10.0 | Pass |
| RULE | | | | | | | |
| 9 | 0.648 | 0.586–0.706 | Review Required | 0.983 | −34.0 | −40.8 to −27.6 | Review Required |
| 10 | 0.624 | 0.568–0.691 | Review Required | 0.903 | −30.9 | −37.8 to −23.1 | Review Required |
| 11 | 0.685 | 0.626–0.741 | Review Required | 0.814 | −15.8 | −23.1 to −8.2 | Insufficient Data |
| 12 | 0.682 | 0.622–0.739 | Review Required | 0.742 | −8.0 | −17.0 to +0.3 | Insufficient Data |

: Weekly monitoring of Small sellers: E1 for the week (level) and S1 against the mean of the four preceding weeks (change). Version v1 ran in weeks 1 to 8 and v2 from week 9; the rule marks the change.

:::

| Cohort | E1 under v1 | E1 under v2 | S2 ratio | 95% interval |
|:----------|------:|------:|------:|:------------|
| Small | 0.983 | 0.660 | 0.672 | 0.633–0.712 |
| Medium | 0.997 | 1.018 | 1.022 | 1.006–1.037 |
| Large | 1.003 | 1.014 | 1.010 | 1.002–1.019 |

: S2, ratio of E1 under v2 (weeks 9 to 12) to E1 under v1 (weeks 5 to 8); no status.

::: limitation
The two versions were observed in different weeks, so the S2 comparison is confounded with time.
:::

## Quality guardrails

Not evaluated: no fairness mitigation was under evaluation in this audit.

## Sensitivity check

Size cohorts were recomputed from active listing count instead of completed orders; 67.5% of sellers keep the same size label.

| Cohort (by listing count) | E1 | 95% interval | Status |
|:--------------------|------:|:------------|:------------|
| Large | 1.012 | 1.008–1.017 | Pass |
| Medium | 0.985 | 0.973–0.998 | Pass |
| Small | 0.816 | 0.775–0.857 | Insufficient Data |

: E1 with size cohorts defined by active listing count.

## Limitations

- Synthetic data with independent ranking events; real logs are clustered and less precise.
- No correction for multiple comparisons: the report makes 5 E1 status comparisons in the audit window, 4 O3, 8 weekly E1 and 8 weekly S1 status comparisons, and 3 in the sensitivity check.
- Outcome rates are not adjusted for position.

## What the generator did

Ranking version v2 (weeks 9 to 12) added a score penalty of 0.024 to listings of Small sellers, as defined by completed orders, and multiplied their click probability by 0.8. Version v1 ignored cohort, and tenure was never used by either version. The observed click-through ratio is below 0.8 because penalised listings also sit lower within the top 10, where click probability is lower.

Software: metrics.py version 2, numpy 2.4.4, pandas 3.0.2. Seeds: catalogue and weekly data from seed 20260105 (week $w$ uses 20260105 + $w$); bootstrap seed 20260105; 1,000 resamples.
