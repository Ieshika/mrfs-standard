# Audit procedure {#sec:audit}

This section sets out the steps of an MRFS audit. It applies to platform audits and to external assessments. The data an audit needs are specified in Section 5; what an organisation does with the results is governed by its own processes, for which Section 4 offers a reference charter.

::: requirement
An exercise is an MRFS audit only if this procedure is followed in full. No minimum number of ranking events defines an audit; whether the data suffice is decided by the confidence intervals (Section 2.6).
:::

## Overview of an audit

```{=latex}
\begin{figure}[h]
\centering
\begin{tikzpicture}[node distance=4mm and 4mm,
  box/.style={draw=mrfsnavy,line width=0.5pt,fill=reqbg,minimum height=13mm,text width=22mm,align=center,font=\sffamily\footnotesize},
  arr/.style={-{Stealth[length=2mm]},color=mrfsnavy,line width=0.6pt}]
\node[box] (a) {1. Fix the audit declaration};
\node[box,right=of a] (b) {2. Assemble data; report its quality};
\node[box,right=of b] (c) {3. Assign seller cohorts};
\node[box,right=of c] (d) {4. Compute metrics with intervals};
\node[box,below=8mm of d] (e) {5. Assign statuses; state what intervals rule out};
\node[box,left=of e] (f) {6. Run sensitivity checks};
\node[box,left=of f] (g) {7. Write the report};
\node[box,left=of g,fill=white,draw=mrfsgrey] (h) {Organisation decides (Section 4)};
\draw[arr] (a) -- (b); \draw[arr] (b) -- (c); \draw[arr] (c) -- (d);
\draw[arr] (d) -- (e); \draw[arr] (e) -- (f); \draw[arr] (f) -- (g); \draw[arr] (g) -- (h);
\end{tikzpicture}
\caption{The steps of an MRFS audit. Routine monitoring between audits and comparisons between ranking versions follow Sections 3.7 and 3.8.}
\end{figure}
```

## The audit declaration {#sec:declaration}

::: requirement
Before any result is examined, the auditor shall record the audit declaration (Section 5.4) and the date it was fixed. It shall state:

- the kind of assessment: platform audit or external assessment;
- the comparison population: the candidate set at a named stage, or the results retrieved to a stated depth $N$;
- known stages before the reference stage that are not captured, and whether candidate generation is covered;
- $K$, and the ordered depth used for E2;
- the cohort definitions (Section 3.4), including the size measure, look-back period, cut-offs, tie rule, tenure reference date source and tenure period;
- the thresholds, if any differ from the MRFS defaults;
- the data-quality acceptance criteria (Section 3.3);
- the audit window, and for monitoring the window length and number of baseline windows;
- any resampling unit other than the ranking event, and any stratification.
:::

A choice made after results were seen is reported as exploratory and does not produce a status.

::: requirement
A status from a candidate-set comparison population applies to ranking from the declared stage onward and shall never be presented as an overall verdict on the marketplace. If only a late stage is logged, the report shall say prominently that earlier exclusion is not covered.
:::

::: example
A marketplace logs only the final 50 candidates for each request. Its E1 statuses describe ranking from those 50 onward. Listings excluded before that stage are not covered, and the report says so on its first page.
:::

## Data quality {#sec:dataquality}

Before computing metrics, the auditor reports for the audit window:

- the number of ranking events, and how they were sampled if not all were used;
- the share of sellers, and of comparison-population listings, without a cohort label;
- the number of events excluded because the comparison population had no more than $K$ listings, and the number excluded for an incomplete top $K$ or an incomplete comparison population;
- for outcome metrics, the share of interactions that join to a ranking event;
- any known differences between the logged order and the order shown to buyers.

::: requirement
MRFS sets no universal acceptance thresholds for these rates. The auditor shall pre-specify acceptance criteria in the declaration and report the actual rates against them. Missing candidate records shall never be interpreted as zero exposure. Where missing data could materially change a conclusion, the affected result shall be Insufficient Data.
:::

Sellers without a cohort label are reported as an Unassigned group, with their size and exposure shown separately and a statement of how excluding them would change the other cohorts' results. Unassigned is a transparency device, not a seller group to interpret.

## Seller cohorts {#sec:cohorts}

MRFS sets procedural requirements and provides defaults. An audit may use a different rule only if it is defined and documented in the declaration before results are seen.

::: requirement
Any cohort rule shall meet the following conditions:

- cohorts are defined before results are examined;
- the measure behind a cohort is taken over a period that ends before the audit window, so that membership is not itself an outcome of the ranking being audited, and is fixed for the whole window;
- one named measure and one named population are used for each dimension;
- every seller is assigned to exactly one cohort per dimension, with a stated rule for ties;
- all cohorts are reported, with each cohort's share of sellers and of comparison-population listings.
:::

### Seller size (default)

| Assessment | Size measure | Label |
|:----------------------------------|:------------------------------------------------------|:--------------------------------|
| Platform audit | Completed orders in the 12 calendar months before the audit start | Seller size |
| Platform audit, sensitivity check | Active listing count at the audit start | Seller size (listing count) |
| External assessment | Active listing count, where publicly available | Seller size (listing-count proxy) |

: Default size measures.

Default split: **Small** at or below the lower quartile of the size measure; **Large** at or above the upper quartile; **Medium** between. All three are reported. Sellers tied at a cut-off value fall on the same side of it, so cohort shares can differ from 25/50/25 and are reported. If the lower and upper quartile values coincide, the default split cannot form cohorts and another size rule is declared (Section 3.4). In a platform audit, quartiles are taken over all sellers with at least one active listing at the audit start, from catalogue records rather than from ranking output; in an external assessment, over the sellers observed in the retrieved results (Section 3.9).

The quartile split is an MRFS default. A disparity confined to the smallest sellers can be hidden by a split at the median, which mixes those sellers with others. Completed orders are preferred to sales value because sales value is dominated by price.

::: limitation
Any measure of commercial scale partly reflects how a seller was ranked in the past. Measuring before the window makes membership predetermined, not independent of past ranking. Results are therefore descriptive associations, and the listing-count sensitivity check (Section 3.6) shows whether a conclusion depends on the measure chosen.
:::

### Seller tenure (default)

Tenure is the time from when the seller became able to sell on the marketplace to the audit start. The reference date is taken from one source for all sellers in an audit, in this order of preference:

1. the date the seller's account or shop was opened;
2. the date of the seller's first published listing;
3. the earliest reliable observed marketplace activity, such as a first sale or first review. This understates tenure, and sellers who were never exposed may have no such date.

**New**: the reference date is later than the date 12 calendar months before the audit start. **Established**: otherwise, including exactly 12 months. Calendar-month arithmetic is used, not 365 days: the same day of the month, or the last day of the month where that day does not exist. Twelve months is an MRFS default; an implementation may pre-specify a different period that reflects its marketplace.

### Other cohort dimensions

Further dimensions, such as ownership attributes, may be added only where the attribute is recorded lawfully and voluntarily, and under the same requirements.

## Computing and reading results {#sec:reading}

The Section 2 metrics are computed for every cohort of every dimension, over the declared comparison population:

- E1, E2 and E3 for every assessment;
- O1 to O3 where interaction data exist;
- S1 in monitoring (Section 3.7) and S2 for version comparisons (Section 3.8);
- Q1 to Q3 only when a mitigation is being evaluated (Section 4.7).

Stratification by product category or query group is optional. Where used, it is declared in advance, each stratum is reported with its own sample size, and cross-stratum results are labelled as such. Stratification multiplies the number of comparisons.

::: requirement
When reading results, the auditor shall:

- assign statuses only where Section 2 provides them, and only for a candidate-set comparison population;
- report every interval and, for an Insufficient Data result, state which statuses the interval rules out;
- state that a status indicates a potential disparity calling for investigation, not unfair treatment or its cause;
- state that no correction for multiple comparisons is applied, and how many comparisons the audit made.
:::

## Sensitivity checks {#sec:sensitivity}

::: requirement
In a platform audit, E1 for seller size shall be repeated using the listing-count measure, and the report shall state whether any status changes.
:::

::: recommendation
Repeat the analysis with the cohort cut-offs moved to the 20th and 80th, or 30th and 70th, percentiles, and with the tenure period shortened and lengthened by three months. Where ranking events cluster strongly by query or by day, repeat the intervals resampling those units. Report any changes; they do not replace the declared result.
:::

## Monitoring between audits {#sec:monitoring}

Routine monitoring computes, for each monitoring window and cohort:

- **E1 and its status**, which report the level;
- **S1** against the declared number of baseline windows, which reports the change;
- O3 where interaction data exist.

::: recommendation
Use weekly monitoring windows where weekly traffic gives enough ranking events for the smallest audited cohort. Where a week routinely returns Insufficient Data, use a longer window made of whole weeks, which avoids day-of-week effects, and state the smallest decline that window can confirm.
:::

Precision depends on a cohort's share of comparison-population listings, not on the calendar. A longer window helps only because it contains more ranking events, and it reports a change later.

**Planning precision.** For a cohort holding a share $p$ of comparison-population listings, with $n$ ranking events and $K$ top positions, the half-width of the 95% interval for E1 near 1 is approximately

$$
h \;\approx\; 1.96\,\sqrt{\frac{1-p}{K\,n\,p}} .
$$

::: limitation
This is an approximate planning calculation under independence assumptions, not a sample-size guarantee. Actual uncertainty is estimated from the audit data using the prescribed resampling unit, and clustered data need more events for the same precision. Confirming Monitor needs a half-width well below 0.025.
:::

::: example
For a cohort holding 4.2% of candidate listings with $K = 10$, the formula gives a half-width of about 0.09 at 1,000 ranking events and 0.03 at 10,000. The synthetic validation, for a cohort at parity, observed 0.086 and 0.0275 (MRFS Validation Report, Section 5).
:::

## Comparing ranking versions {#sec:versions}

When a ranking version changes, S2 is computed for each cohort on the same comparison population and stage, and reported with its interval. The comparison design is declared:

- **Same events.** Both versions rank the same requests, for example in a replay or shadow evaluation.
- **Concurrent split.** Versions serve different requests at the same time.
- **Before and after.** Versions are observed in different periods; the comparison is confounded with time and the report says so.

An interval wholly below 1 is evidence of deterioration and is reported for review. MRFS does not approve or block a release; the organisation decides through its own governance.

## External assessment {#sec:external}

An external assessment uses publicly retrievable results.

::: requirement
In an external assessment:

- the comparison population is the results retrieved to a fixed depth $N$ for a fixed, published set of requests (a query panel), and $N$ is part of every reported value;
- cohort measures are those publicly available (Section 3.4), labelled as proxies, with quartiles taken over the sellers observed in the retrieved results;
- no status is assigned; the report gives ratios, intervals, a comparison against a declared reference value, and stability over time;
- every result carries the statement: "Measures placement among listings retrieved to depth $N$. Sellers and listings not retrieved are unobserved.";
- the assessor complies with the data provider's terms of use.
:::

One ranking event is one request's result list. Precision depends mainly on the number of distinct requests; repeating the same requests over time measures stability, not additional independent evidence. Values computed at different depths $N$ are not comparable.

## Report contents {#sec:report}

| Section | Contents |
|:----------------------|:------------------------------------------------------------------|
| Summary | Results by cohort, with statuses where applicable, and the scope statement |
| Audit declaration | The full declaration and the date it was fixed |
| Data | Event counts, window, sampling, cohort shares of sellers and listings, data-quality rates against the declared criteria, Unassigned group |
| Exposure | E1 with intervals and statuses; E2; E3 |
| Outcomes | O1, O2 and O3 with intervals and statuses, or Not Evaluated |
| Stability | S1 by window with statuses; S2 where a version changed |
| Quality guardrails | Q1 to Q3 where a mitigation was evaluated, otherwise Not Evaluated |
| Sensitivity checks | Results of Section 3.6 |
| Limitations | Scope, uncovered stages, multiple comparisons, clustering, anything excluded |
| Appendix | Formulas used, software version, seeds |

: Contents of an audit report.

Each report carries an identifier and a version. A change to the procedure between audits is recorded in the report. Appendix A is a complete example.
