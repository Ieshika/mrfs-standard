# src/ -- MRFS Reference Implementation

This directory is the reference implementation referenced by Volume 2
(Evaluation Metric Catalog) and Volume 3 (Audit Protocol). It is
deliberately code living in `src/`, not a 7th documentation volume.

## Files

- **metrics.py** -- Core metric implementations: E1 (ExposureShare@K), E2
  (Mean Rank Position/Delta), E3 (Exposure Gini), O1/O2/O3 (CTR/CVR parity
  and Disparate Impact), S1 (drift), and `evaluate_thresholds()` (Volume 2
  Section 6 pass/monitor/review bands). Validated against both a
  known-disparity synthetic dataset (Volume 6) and a genuinely-fair
  synthetic dataset (`docs/Validation_Addendum_False_Positive_Test.md`).
- **generate_fair_dataset.py** -- Synthetic "null case" dataset generator
  used for the false-positive counter-test.
- **run_false_positive_test.py** -- Runs the null-case dataset through
  `metrics.py` and reports pass/fail.
- **query_set.py** -- The fixed, versioned, published query list for the
  Etsy real-data pilot. Don't edit in place -- bump the version and log
  why if it needs to change.
- **etsy_pilot_collector.py** -- Collects real search-listing data from
  Etsy's public Open API v3 for every query in `query_set.py`, shapes it
  into `metrics.py`'s expected input contract, and saves it to
  `data/etsy_pilot_runs/<timestamp>/`.
- **run_etsy_pilot.py** -- Loads a saved Etsy pilot run and computes
  E1/E2/E3 against it using the real `metrics.py` functions.
- **generate_audit_report.py** -- Formats a pilot run's metric results into
  a standardized markdown report under `reports/`.

## Running the Etsy pilot

Requires an approved Etsy Open API v3 key (`etsy.com/developers`, Personal
App path).

```
pip install pandas numpy requests
export ETSY_API_KEY="your_keystring_here"
python3 etsy_pilot_collector.py
python3 run_etsy_pilot.py
```

This produces a markdown report under `reports/`. Read the report's
Limitations section before citing any number from it -- this pilot is
explicitly scoped as a feasibility study (E1-E3 only, single-run,
median-split cohorts), not a statistically powered claim.
