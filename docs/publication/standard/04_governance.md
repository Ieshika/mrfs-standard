# Governance and adoption {#sec:governance}

## Using the reference charter

This section is a reference charter for an organisation that adopts MRFS. The roles and bodies named here do not exist until an adopting organisation designates them. The organisation may adapt the charter to its own governance, provided it documents its choices. Decisions belong to the adopting organisation and are documented; MRFS does not approve or block software releases.

The charter rests on five principles:

- **Accountability.** Each result that calls for a response has a named owner and a documented decision.
- **Evidence, not verdicts.** A status indicates a potential disparity that calls for investigation.
- **Stated uncertainty.** Insufficient Data is recorded as unresolved, never as a pass.
- **Proportionality.** Decisions weigh persistence, size and context, not a single window in isolation.
- **Privacy.** Aggregated and pseudonymised data are preferred; individual seller detail is used only where an investigation needs it, under access control.

## Roles

| Role | Responsibility | Authority |
|:------------------------|:----------------------------------------------------|:----------------------------------------|
| Fairness lead | Prepares audit declarations; runs audits and monitoring; reports results; leads investigations | Escalates findings; proposes mitigations |
| Ranking product owner | Owns the ranking system; provides logs and context; implements agreed mitigations | Decides on releases within the organisation's own process |
| Review body | A group the organisation designates, typically including ranking, policy, legal and seller-experience representatives | Records decisions on Review Required findings; approves mitigations and risk acceptance |
| Independent reviewer (optional) | Checks audits and monitoring against this standard | Issues findings, tracked to resolution |

: Roles in the reference charter.

## Recommended cadence

::: recommendation
The cadence below is recommended, not required. The organisation declares its actual cadence, and every result states its window dates.
:::

| Activity | Recommendation |
|:----------------------------------------------|:------------------------------------------------------------------|
| Routine monitoring (E1 status and S1 for each cohort) | Weekly, on whole-week windows; a longer window of whole weeks where a week routinely returns Insufficient Data (Section 3.7) |
| Full audit (Section 3) | Quarterly |
| Additional audit | After a material change to the ranking system, or after a Review Required result in monitoring |
| Review of audit results by the review body | After each full audit |
| Independent review | Annually |

: Recommended cadence.

Weekly, quarterly and annual intervals are practical recommendations, not derived values; whole-week windows avoid day-of-week effects. Response times, such as how soon an investigation starts, are set by the organisation's governance.

## Response to each result

::: requirement
Each result shall receive the response below.
:::

| Result | Response |
|:----------------------|:----------------------------------------------------------------------|
| Pass | Record. Continue monitoring. |
| Monitor | Record. Note the cohort for attention in the next audit. |
| Insufficient Data | Record as unresolved, never as a pass. State what the interval rules out and how further evidence will be obtained, for example with a longer window. |
| Review Required | Open a documented investigation (Section 4.7). The review body records a decision with its rationale. |
| S2 after a version change | Record the ratio and interval. S2 has no status; the fairness lead reports it to the decision-maker, and an interval wholly below 1 is weighed as evidence of deterioration. |
| Not Evaluated | Record the reason. |

: Response to each result.

## Records

For each audit the organisation keeps:

- the audit report (Section 3.10), including the audit declaration and the date it was fixed;
- supporting tables, and the software version and seeds used;
- for every Review Required or unresolved result, the decision record with its rationale and owner.

Records are kept long enough to reproduce every reported result and to support year-on-year comparison, and are available to auditors and, where applicable, regulators.

## Optional release-gate integration {#sec:releasegate}

An organisation may connect MRFS results to its release process. If it does, it declares that it does, and the following apply.

::: requirement
Where release-gate integration is declared:

- the inputs are the most recent audit or monitoring results for the cohorts concerned, S2 for the version being released, and the data-quality report;
- any Review Required status, and any Insufficient Data result on a metric the organisation has declared release-relevant, needs a decision recorded by the authority the organisation designates before the release proceeds. The decision may block the release, permit a conditional release, or authorise a time-limited exception, and a release made this way is recorded as such, never as a pass;
- S2 results for the version being released are part of the record and are considered in the decision;
- the absence of a decline is not a pass condition: an existing disparity is not acceptable merely because a new version did not worsen it;
- results apply to the declared stage of the ranking system only.
:::

Quality checks outside fairness mitigations remain with the platform's existing release process.

## Investigation and mitigation {#sec:mitigation}

### Investigation

Investigation begins with the data, then the ranking:

1. **Data quality.** Check the data-quality report, cohort label coverage and the Unassigned group.
2. **Location.** Stratify by category or query group to see whether the disparity is concentrated or broad. Use the stage breakdown (Section 2.8) where several stages are logged.
3. **Timing.** Compare across monitoring windows and ranking versions (S1, S2, `model_version`).
4. **Exposure findings (E1).** Check E2 for placement within the list and E3 for concentration within the cohort. Review ranking features that correlate with seller size or tenure.
5. **Outcome findings (O3).** Check exposure first, since outcome differences can follow from placement. Compare outcome rates within the same positions to separate placement from other causes. Review listing-quality signals by cohort.
6. **Drift findings (S1).** Check recent ranking changes, changes in the seller population, and seasonal patterns.
7. **Conclusion.** Record whether the disparity is attributable to the ranking system, to inventory or relevance differences, or remains undetermined.

### Mitigation options

| Option | Description | Typical use |
|:------------------------|:------------------------------------------------------|:------------------------------------------|
| Score calibration | Adjust scoring components that suppress a cohort without improving relevance | The investigation identifies a specific feature |
| Data and feature stability | Guard against volatile or shifted input features | A decline follows a data shift |
| Diversity constraints | Bound the share of top positions any few sellers hold, consistent with relevance | E3 shows strong concentration in a cohort with low E1 |
| Exposure controls | Re-rank to keep a cohort's top-$K$ presence within a set range | Persistent low E1 with quality guardrails within limits |
| Human review | Route specific categories or patterns for manual review | Automated options are unsuitable |
| Version rollback | Return to the previous ranking version | A specific release introduced the disparity |
| Risk acceptance | Accept a residual disparity with a written rationale recorded by the review body | The disparity is attributable to legitimate factors |

: Mitigation options, from least to most invasive.

### Evaluating a mitigation

::: requirement
Before adoption, a mitigation shall be compared with the current ranking on the fairness metric that triggered the investigation (E1, O3 or S1), with intervals, and on the quality guardrails Q1 to Q3 against declines pre-specified in the audit declaration. If a guardrail is breached, the mitigation is revised or withdrawn, or the trade-off is recorded as a decision by the review body.
:::

After adoption, monitoring continues until the next full audit confirms the result. If the triggering result recurs during monitoring, the review body is informed. The decision record documents the option chosen, its rationale, the before-and-after results with intervals, the guardrail results, and the close-out.

## Relationship to the NIST AI Risk Management Framework

The structure of this charter is informed by the four functions of the NIST AI Risk Management Framework [9]. The following mapping is the author's, offered for orientation.

| AI RMF function | Closest MRFS element |
|:-------------|:-------------------------------------------------------------------|
| Govern | Roles, decision records and documentation (Sections 4.2 to 4.5) |
| Map | Assessment scope, comparison population and cohort definitions (Sections 1.4, 3.2 and 3.4) |
| Measure | Metrics and audit procedure (Sections 2 and 3) |
| Manage | Responses to results and investigation and mitigation (Sections 4.4 and 4.7) |

: The author's mapping to the AI RMF functions.

Using MRFS does not by itself establish conformance with the AI RMF.
