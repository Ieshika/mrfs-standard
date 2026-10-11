# Introduction {#sec:intro}

## Purpose

The Marketplace Ranking Fairness Standard (MRFS) specifies how to audit the way a marketplace's ranking and recommendation systems distribute top-ranked positions across groups of sellers, and how an organisation governs what happens when an audit finds a potential disparity. It defines what to measure, how to measure it reproducibly with stated uncertainty, how to read the results, what data an audit needs, and how findings feed into an organisation's own decisions.

Rank position matters commercially as well as normatively. A field experiment on an online travel platform found that rank position causally affects which results consumers examine; conditional on a result being examined, its position did not affect purchase [10]. MRFS therefore treats the top-ranked positions as the point at which sellers gain or lose consideration by buyers.

MRFS draws on research that treats exposure in rankings as the quantity of interest [8] and on measures of group representation in ranked lists [7], the latter used in the TREC Fair Ranking Track [2]. General-purpose fairness toolkits [1][6][12] provide metrics and mitigation methods for machine-learning models; they do not set out an audit protocol for seller visibility in marketplace ranking. MRFS is intended to provide one. Its own design choices are identified as such throughout and summarised in Appendix D.

## Scope

**In scope.** Ranking and recommendation systems that determine which listings, and therefore which sellers, appear in the top positions of a marketplace's search results or recommendation slates.

**Seller cohorts.** By default, seller size (Small, Medium, Large) and seller tenure (New, Established), defined in Section 3.4. Further cohort dimensions may be added where the attribute is recorded lawfully and voluntarily, under the same rules.

**Out of scope.** Advertising and sponsored placements, pricing algorithms, and the adjudication of individual sellers' cases.

## Conventions

Normative statements use the following terms.

| Term | Meaning |
|:----------|:-------------------------------------------------------------|
| **shall** | A requirement. An audit that does not meet it is not an MRFS audit. |
| **should** | A recommendation. Departing from it is permitted and is stated in the report. |
| **may** | A permitted option. |

: Normative terms.

Statements are also marked visually:

::: requirement
Requirements are set in boxes like this one.
:::

::: recommendation
Recommendations are set in boxes like this one.
:::

::: example
Examples illustrate a rule. They are not normative.
:::

::: limitation
Limitations state what a result cannot show.
:::

Sample sizes are counted in ranking events throughout. Cross-references such as "Section 2.6" refer to sections of this document.

## Two kinds of assessment {#sec:assessments}

MRFS distinguishes two kinds of assessment.

| | Platform audit | External assessment |
|:------------------------|:--------------------------------------|:--------------------------------------|
| Conducted by | The marketplace operator, or an auditor with access to its logs | A third party using publicly retrievable results |
| Comparison population | The candidate listings considered by the ranking system at a named stage | The results retrieved to a stated depth |
| Statuses | Yes, scoped to the declared stage | No; ratios and intervals only |
| What a result can support | Exposure relative to candidates from the declared stage onward | Placement among the retrieved results only |

: The two kinds of assessment.

::: requirement
Every result shall state which kind of assessment produced it. Results from different kinds of assessment, or from different comparison populations, shall not be presented as comparable.
:::

## Terms and definitions {#sec:terms}

| Term | Definition |
|:----------------------|:----------------------------------------------------------------|
| Ranking event | One request (a search query or a recommendation request) that returns one ordered list. |
| Listing | One item offered by one seller. Positions and candidates are counted as listings. |
| Seller cohort | A group of sellers defined before results are examined. A listing belongs to its seller's cohort. |
| Comparison population | The listings against which a cohort's top positions are compared in each ranking event: the candidate set at a declared stage, or the results retrieved to a declared depth $N$. |
| Top $K$ | The first $K$ positions of the ordered list; $K = 10$ by default. |
| Audit declaration | The record of choices fixed before results are examined (Section 5.4). |
| Status | Pass, Monitor, Review Required or Insufficient Data, decided from a 95% confidence interval (Section 2.6). |
| Not Evaluated | The result reported for a metric whose data are unavailable. It is never counted as a pass. |
| Unassigned | The group of sellers without a cohort label. It is reported but never given a status. |
| Audit window | The period whose ranking events an audit uses. |
| Monitoring window | The period used for one round of routine monitoring. |

: Terms and definitions.

## Principles

- **MRFS identifies risks, quantifies uncertainty and requires accountability.** A status is evidence of a potential disparity that calls for investigation. It does not establish unfair treatment or its cause.
- **MRFS does not approve or block software releases.** Organisations decide through their own governance and document the decision (Section 4).
- **Declared before examined.** Cohort definitions, the comparison population, thresholds and data-quality criteria are fixed and recorded before results are seen.
- **Uncertainty is part of the result.** Every status is decided from a confidence interval. Insufficient Data is a legitimate result.
- **Scope is stated.** A result applies to the population and stage it was computed on, and no further.
- **MRFS choices are labelled.** Where MRFS adopts a threshold or default without external validation, this document says so (Appendix D).
- **Reproducible.** The reference implementation and the synthetic validation are published with fixed seeds (Appendix C).

## Status of this document

MRFS v2.0.0 is a published technical standard for evaluating seller exposure in marketplace ranking systems. Its reference implementation has been evaluated using synthetic data, as documented in the MRFS Validation Report. Validation against live marketplace internal data has not yet been conducted.
