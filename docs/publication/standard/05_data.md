# Data specification {#sec:data}

This section is the authoritative specification of the data an MRFS audit uses. It says what must be available at audit time, not how a platform stores it: event streams, batch exports and warehouses are all acceptable if the fields below can be produced.

## Data sources

| Source | Contents | Needed for |
|:--------------------|:----------------------------------------------------------|:------------------------------------|
| Ranking event log | One row per listing in the declared comparison population of each ranking event | All exposure and stability metrics |
| Seller records | One row per seller: cohort labels and the values they were derived from | Cohort assignment |
| Interaction log | Clicks and conversions on ranked listings | Outcome metrics and quality guardrails |
| Audit declaration | The choices fixed before results are examined | Every audit |

: Data sources.

## Ranking event log {#sec:eventlog}

One row per listing in the comparison population of each ranking event. In a platform audit this is every candidate listing at the declared stage, including candidates that were never placed in the ordered list. In an external assessment it is every result retrieved to the declared depth $N$.

| Field | Type | Description | Required |
|:-----------------------|:----------------|:--------------------------------------------------------|:------------------------|
| `event_id` | string | Identifier of the ranking event, shared by all its rows | Yes |
| `event_timestamp` | timestamp (UTC) | When the ranking was produced | Yes |
| `item_id` | string | Identifier of the listing | Yes |
| `seller_id` | string | Identifier of the listing's seller; may be pseudonymised consistently | Yes |
| `rank_position` | integer or empty | Position in the ordered list across all pages, 1 = top; empty for a candidate not placed in the ordered list | Yes (empty allowed in platform audits only) |
| `model_version` | string | Version of the ranking system that produced the list | Platform audits only |
| `query_context` | string | The query (may be hashed) or the recommendation surface | Recommended |
| `category_id` | string | Product category of the request, for optional stratification | Recommended |
| `inclusion_probability` | number | Probability that the event was sampled, where events were sampled with unequal probability | Only if sampling was unequal |

: Fields of the ranking event log.

::: requirement
- An event whose top positions are known to be incompletely logged, for example because of a logging gap, shall be excluded and counted. Where a list legitimately shows fewer than $K$ positions, the event is kept and the number of positions shown is used (Section 2.1). Events with no ranked position shall be excluded and counted.
- An event whose comparison population is known to be incompletely logged shall be excluded and counted. Missing candidate records shall never be treated as zero exposure.
- Ranking events may be sampled, but only whole events, never listings within an event. The sampling method and inclusion probabilities shall be documented.
:::

## Seller records {#sec:sellers}

One row per seller. Cohort labels are fixed at the audit start and apply for the whole audit window.

| Field | Type | Description | Required |
|:-----------------------|:-----------------|:-------------------------------------------------------|:------------------------------|
| `seller_id` | string | Matches the ranking event log | Yes |
| `seller_size` | Small, Medium, Large | Size cohort (Section 3.4) | Platform audits; external assessments where a size measure is publicly available |
| `seller_tenure` | New, Established | Tenure cohort (Section 3.4) | Platform audits; external assessments where a reference date is publicly available |
| `size_basis_value` | number | The value the size cohort was derived from: completed orders in the look-back period (platform audit) or active listing count (external assessment) | With `seller_size` |
| `tenure_reference_date` | date | The date tenure is measured from, from the declared source | With `seller_tenure` |
| `listing_count` | integer | Active listings at the audit start, for the sensitivity check | Platform audits |
| `cohort_effective_date` | date | The date the cohort labels were fixed (the audit start) | Yes |

: Fields of the seller records.

In a platform audit the seller records cover all sellers with at least one active listing at the audit start, taken from catalogue records. In an external assessment they cover the sellers observed in the retrieved results. A seller with no record, or with a missing label, is reported as Unassigned.

## Audit declaration record {#sec:declarationrecord}

One record per audit, fixed before results are examined (Section 3.2).

| Item | Content |
|:-----------------------|:--------------------------------------------------------------------|
| `audit_mode` | Platform audit or external assessment |
| `population_type` | Candidate set, or retrieved results |
| `population_detail` | The named candidate stage, or the retrieval depth $N$ |
| `upstream_not_captured` | Stages before the reference stage that are not logged; whether candidate generation is covered |
| `k`, `ordered_depth` | Number of top positions (default 10); the ordered depth used for E2 |
| `cohort_definitions` | For each dimension: measure, look-back period, cut-offs, tie rule, tenure reference date source and period |
| `thresholds` | Monitor line for E1 and O3 and drift lines for S1 (MRFS defaults unless stated); the Review line is 0.80 (Section 2.6) |
| `data_quality_criteria` | Acceptance criteria for the rates in Section 5.6 |
| `windows` | Audit window; for monitoring, window length and number of baseline windows |
| `resampling_unit`, `strata` | The resampling unit if not the ranking event; any stratification |
| `fixed_on` | The date these choices were fixed |

: Contents of the audit declaration record.

## Interaction log and joined analysis view {#sec:interactions}

| Field | Type | Description | Required |
|:-----------------------|:----------------|:--------------------------------------------------------|:---------|
| `event_id` | string | The ranking event that produced the impression | Yes |
| `item_id` | string | The listing that received the interaction | Yes |
| `interaction_type` | Click or Conversion | The kind of interaction | Yes |
| `interaction_timestamp` | timestamp (UTC) | When it happened; later than the event timestamp | Yes |

: Fields of the interaction log.

The metrics consume one **joined analysis view**: the ranking event log, with each row's seller cohort labels from the seller records, and `was_clicked` and `was_converted` (0 or 1) derived by joining the interaction log on `event_id` and `item_id`. A listing counts at most once as clicked and once as converted per event.

## Data quality reporting {#sec:dqreport}

MRFS sets no universal acceptance thresholds. The audit declaration states acceptance criteria, and the report gives the actual rates against them:

- the share of sellers, and of comparison-population rows, without a cohort label;
- events excluded for an incomplete top $K$, an incomplete comparison population, or a comparison population no larger than $K$;
- the share of interactions that join to a ranking event;
- timestamp violations, such as an interaction before its event;
- missing `model_version` values (platform audits);
- known differences between the logged order and the order shown to buyers.

Where missing data could materially change a conclusion, the affected result is Insufficient Data (Section 3.3).

## Minimum data for each kind of assessment

External assessments are not made impossible by requirements they cannot meet: each metric needs only the data listed for it.

| Metric | Platform audit | External assessment |
|:----------|:----------------------------------------------------------|:----------------------------------------------------------|
| E1, E2, E3 | Ranking event log with all candidates at the declared stage, and seller records | Retrieved results to depth $N$, and records for observed sellers (size proxy, tenure reference date) |
| O1 to O3 | Interaction log | Not available |
| S1 | Ranking event log across windows | Possible with repeated collection of the same query panel |
| S2 | `model_version`, or the separate logs of two versions | Not available |
| Q1, Q2 | Interaction log | Not available |
| Q3 | The platform's own relevance evaluation, documented | Not available |

: Minimum data for each kind of assessment.

## Windows and baselines

- **Audit window.** Declared in the audit declaration; Section 4.3 gives the recommended cadence.
- **Monitoring windows.** Whole weeks, with the length chosen for adequate precision (Section 3.7).
- **Baselines.** For S1, the declared number of preceding windows (default four) of the same length. For S2, the current version's results on the declared comparison design. A full audit may also be compared with the previous audit of the same design.

## Retention and privacy

**Retention.** The data and records needed to reproduce every reported result are retained: the ranking event log, the seller records with their effective dates, the interaction log, the audit declaration, and the software version and seeds. A year-on-year comparison needs logs covering twelve months plus the longest window being compared: thirteen months for monthly windows, fifteen for quarterly ones. Audit records are retained as the organisation's governance requires.

**Privacy.**

- Seller identifiers may be pseudonymised, consistently within and across audit windows.
- Query text may be hashed or omitted; no metric needs it.
- Aggregated results can still identify a seller when a cohort, category or window is small. Small cells are suppressed or combined before results are shared outside the audit team.
- Individual seller detail is used during investigations only under access control and with a documented reason.
