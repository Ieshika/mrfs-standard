# Metrics and decision rules {#sec:metrics}

This section defines every metric used in an MRFS audit, how its uncertainty is estimated, and which metrics carry a status. Section 3 describes when and how they are computed.

## Notation and common rules

| Symbol | Meaning |
|:--------------|:-------------------------------------------------------------------|
| $q$ | A ranking event. |
| $K$ | Number of top positions examined; default 10. |
| $n_q$ | Number of listings in the comparison population of event $q$. |
| $n_q(c)$ | Number of those listings that belong to cohort $c$. |
| $T_q(c)$ | Number of top-$K$ positions held by listings of cohort $c$ in event $q$. |
| $K_q$ | Number of top positions actually shown in event $q$, at most $K$. Where a list shows fewer than $K$ positions, $K_q$ is the number shown. |
| $D_q$ | Number of ordered positions in event $q$ used for E2. |

: Notation.

The comparison population of each event is the candidate set at the declared stage (platform audit) or the results retrieved to the declared depth $N$ (external assessment). Sellers without a cohort label are reported as Unassigned; their listings remain in the comparison population.

## Exposure metrics

E1 is the primary exposure measure and the only one that carries formal statuses in platform audits. E2 describes where a cohort's listings rank, and E3 describes how top positions are distributed across sellers. E2 and E3 are descriptive metrics. They are reported to support interpretation and investigation, but do not receive Pass, Monitor, Review Required or Insufficient Data classifications. MRFS does not prescribe fairness thresholds for these metrics. Neither E2 nor E3 independently establishes unfair treatment.

### E1 Exposure ratio at *K*

E1 compares the number of top-$K$ positions a cohort holds with the number it would hold if position were unrelated to cohort, given each event's comparison population. The expectation is formed event by event and then summed, so that an event with a very large comparison population does not dominate.

::: formula
$$
\mathrm{E1}(c) \;=\; \frac{\displaystyle\sum_{q} T_q(c)}{\displaystyle\sum_{q} K_q\,\frac{n_q(c)}{n_q}}
$$
:::

$\mathrm{E1}(c) = 1$ means the cohort's top-$K$ presence matches its share of the comparison population; below 1 means it holds fewer top positions than that share. A cohort with no listings in the comparison population of any included event has no expected positions; its E1 is undefined, no interval is formed, and the result is Not Evaluated.

::: requirement
Events whose comparison population has no more than $K$ listings, events with no ranked position, and events whose top positions are known to be incompletely logged shall be excluded from E1 and counted in the data-quality report. E1 shall carry a status only when the comparison population is a candidate set, and that status applies to the declared stage only.
:::

- Every top-$K$ position counts equally. E1 measures top-$K$ representation; it is not an attention-weighted or position-weighted measure. E2 shows where in the list a cohort sits.
- In an external assessment the comparison population has already been selected by the ranking system being examined, so E1 describes placement among retrieved results and carries no status.

::: limitation
E1 is not adjusted for relevance, inventory quality or buyer intent, and a cohort can legitimately score below 1. A low E1 identifies a potential disparity requiring investigation; it does not establish unfair treatment or its cause.
:::

### E2 Mean rank position, normalised (no status)

For each listing in the ordered part of the comparison population, the normalised rank is

$$
u \;=\; \frac{r - 0.5}{D_q},
$$

where $r$ is the listing's rank. $\mathrm{E2}(c)$ is the mean, over the ranking events containing at least one ordered listing of cohort $c$, of the cohort's mean normalised rank in that event. Each ranking event counts equally, so long lists and cohorts with many listings in one event do not dominate. Every listing appearance counts, including several from one seller.

Values lie between 0 and 1; lower is better. The ordered depth is reported with every value.

::: example
In an event with 50 ordered positions, ranks 1, 25 and 50 have normalised ranks 0.01, 0.49 and 0.99.
:::

::: limitation
0.5 is the reference midpoint obtained when order is unrelated to cohort. It is not a fairness expectation: relevance, inventory and buyer intent can legitimately move a cohort away from it.
:::

### E3 Exposure concentration (no status)

E3 is the Gini index of top-$K$ position counts across sellers. The seller set is every seller with at least one listing in the comparison population during the audit window, including sellers with no top-$K$ position. A seller's count is every top-$K$ position its listings held, summed over events. E3 is reported for each cohort and for all sellers.

A value of 0 means top positions are spread evenly across those sellers; values near 1 mean that a few sellers hold nearly all of them.

::: limitation
Concentration does not establish unfair treatment: sellers with no top-$K$ position may have less relevant inventory or fewer eligible listings. E3 depends on window length and traffic, so values are compared only within one audit design. In an external assessment the seller set is limited to sellers observed in retrieved results.
:::

## Outcome metrics

Outcome metrics are computed where interaction data exist (Section 5.5).

| Metric | Definition | Status |
|:---------------------------|:--------------------------------------------------------------|:-------|
| O1 Click-through rate by cohort | Clicks on the cohort's top-$K$ impressions ÷ the cohort's top-$K$ impressions | No |
| O2 Conversion rate by cohort | Conversions on the cohort's top-$K$ impressions ÷ the cohort's top-$K$ impressions | No |
| O3 Outcome ratio | O1 or O2 of the cohort examined ÷ the same rate of the reference cohort (by default Small against Large, New against Established) | Yes |

: Outcome metrics.

O3 is computed separately for clicks and for conversions; each is one quantity.

::: limitation
Outcome rates are not adjusted for position: a cohort shown lower within the top $K$ tends to have a lower click rate for that reason alone. Section 4.7 describes how to examine this.
:::

## Stability metrics

### S1 Exposure drift

::: formula
$$
\mathrm{S1} \;=\; 100 \times \left( \frac{\mathrm{E1}\ \text{in the current window}}{\text{mean of E1 in the preceding baseline windows}} - 1 \right)
$$
:::

By default S1 uses four baseline windows of the same length as the current window, non-overlapping, computed on the same comparison population and cohort definitions. Negative values are declines.

::: limitation
S1 measures a change, not a level. After a fall, later values of S1 shrink as the lower values enter the baseline; the E1 status of each window reports the level.
:::

### S2 Model regression (no status)

S2 is the ratio of E1 under a new version of the ranking system to E1 under the current version, for each cohort, on the same comparison population and stage, with a 95% interval. The interval method follows how the versions were compared: on the same ranking events (events resampled jointly), or on separate events such as a concurrent split or before-and-after windows (each resampled separately).

S2 has no status and no cut-off. It is reported and read in review: an interval wholly below 1 is evidence of deterioration, including a fall that leaves E1 inside one status band (for example from 1.20 to 0.90).

::: limitation
Before-and-after comparisons are confounded with time, and the report states this.
:::

## Quality guardrails

Quality guardrails apply when a fairness mitigation is being evaluated (Section 4.7). General release-quality checks belong to the platform's own release process.

| Metric | Definition |
|:---------------------------|:----------------------------------------------------------------|
| Q1 Overall click-through rate | Total clicks ÷ total top-$K$ impressions |
| Q2 Overall conversion rate | Total conversions ÷ total top-$K$ impressions |
| Q3 NDCG@$K$ | Normalized Discounted Cumulative Gain at $K$ [5], from the platform's own relevance evaluation |

: Quality guardrails.

::: requirement
The permitted decline for each guardrail shall be pre-specified in the audit declaration; MRFS sets no universal value. For Q3, the platform's evaluation method, population and provenance shall be documented. Where no relevance evidence exists, Q3 shall be reported as Not Evaluated.
:::

## Statuses and thresholds {#sec:statuses}

MRFS uses four statuses, for applicable metrics only: **Pass, Monitor, Review Required, Insufficient Data.** A status indicates evidence and potential risk; it is not proof of unfair treatment.

::: requirement
Each status shall be decided from the metric's 95% confidence interval, never from the point estimate alone, according to the rules below. Metrics without data shall be reported as Not Evaluated, never as a pass.
:::

| Metric | Pass | Monitor | Review Required | Otherwise |
|:-------|:--------------------------------|:----------------------------------------------|:--------------------------------|:-----------|
| E1, O3 | whole interval $\ge$ Monitor line | whole interval within [Review line, Monitor line) | whole interval $<$ Review line | Insufficient Data |
| S1 | whole interval $>$ Monitor drift line | whole interval within (Review drift line, Monitor drift line] | whole interval $\le$ Review drift line | Insufficient Data |

: Status decision rules.

| Threshold | Default | Nature of the value |
|:------------------------|--------:|:-------------------------------------------------------------|
| Review line (E1, O3) | 0.80 | MRFS normative decision threshold, adopted by analogy to the four-fifths rule |
| Monitor line (E1, O3) | 0.85 | MRFS default early-warning threshold |
| Monitor drift line (S1) | −10% | MRFS default |
| Review drift line (S1) | −20% | MRFS default |

: Thresholds.

**Origin of 0.80.** MRFS adopts 0.80 as a normative decision threshold by analogy to the four-fifths rule of the U.S. Uniform Guidelines on Employee Selection Procedures [4]. The four-fifths rule was developed for employment selection rates and does not establish 0.80 as a validated fairness threshold for marketplace ranking exposure. The rule's own guidance describes it as a rule of thumb that provides a basis for drawing an initial inference [3], and its transfer to machine-learning fairness metrics has been criticised [11]. A review of the ranking-fairness literature carried out for MRFS found no agreed numeric threshold for exposure measures.

::: requirement
An implementation may use a different Monitor line or different drift lines, but shall pre-specify and document them in the audit declaration before results are evaluated. The Review line of 0.80 is normative: a result computed against a different Review line is not an MRFS status and shall be labelled as such.
:::

**Insufficient Data** is the honest result when the data cannot distinguish two adjacent statuses. It is never counted as a pass. The interval is reported with it, together with any status it rules out.

::: example
An E1 interval of 0.79 to 0.84 straddles the Review line and gives Insufficient Data. Because the interval lies wholly below 0.85, it rules out Pass.
:::

::: limitation
Monitor is the hardest status to confirm, because the whole interval must fit inside a band 0.05 wide. For a cohort holding a small share of the comparison population this can require tens of thousands of ranking events (MRFS Validation Report, Section 9). An audit that cannot confirm Monitor has reported its precision; it has not failed.
:::

## Uncertainty {#sec:uncertainty}

::: requirement
Intervals shall be 95% percentile bootstrap intervals that resample whole ranking events with replacement. Listings from the same event shall not be resampled separately. For every ratio, numerator and denominator shall be recomputed in each resample.
:::

- When a numerator count is zero (a cohort with no top-$K$ position, or no click or conversion in the window), every resample is also zero and the bootstrap cannot express the uncertainty. No interval is formed and the status is Insufficient Data.
- The method assumes that ranking events are an equal-probability sample of the audit window. Unequal-probability sampling needs inverse-probability weighting.
- Ranking events for the same query or on the same day may be correlated, in which case resampling single events understates uncertainty. An audit may resample larger units, such as queries or days, if they are declared in advance.

::: limitation
Intervals built on very few positions or outcomes are imprecise and can under-cover. Each cohort and metric is a separate comparison and no correction for multiple comparisons is applied: the more statuses an audit reports, the more likely one of them is wrong by chance. Reports list every comparison made. The reference implementation does not provide inverse-probability weighting.
:::

## Optional diagnostics

These are not metrics and carry no status. They help investigate a Review Required result.

- **Unshown-candidate rate.** The share of a cohort's sellers that were in a candidate set at least once during the window but never held a top-$K$ position. It covers only sellers that reached the candidate stage; exclusion before that stage is not measured.
- **Stage breakdown.** Where a ranking system logs more than one stage, the cohort's share of listings at each stage, showing where its share changed.
