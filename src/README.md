# src/ -- MRFS Reference Implementation

This directory is the reference implementation referenced by Volume 2
(Evaluation Metric Catalog) and Volume 3 (Audit Protocol). It is
deliberately code living in `src/`, not a 7th documentation volume.

## Files

- **metrics.py** -- Core metric implementations: E1 (ExposureShare@K), E2
  (Mean Rank Position/Delta), E3 (Exposure Gini), O1/O2/O3 (CTR/CVR parity
  and Disparate Impact), S1 (drift), and `evaluate_thresholds()` (Volume 2
  Section 6 pass/monitor/review bands). E1, E2, and O1-O3 each return a 95%
  bootstrap confidence interval alongside their point estimate (event-level
  resampling -- see the module docstring for why), and `evaluate_thresholds()`
  uses the interval, not just the point estimate, to decide status --
  including a fourth status, INSUFFICIENT_DATA, for when the interval
  straddles a threshold line. `classify_ci()` is the reusable classification
  function behind this. Validated against a known-disparity synthetic dataset
  (Volume 6), a genuinely-fair synthetic dataset
  (`docs/Validation_Addendum_False_Positive_Test.md`), and a small-sample
  false-positive test that found and fixed a real gap
  (`docs/Validation_Addendum_Confidence_Intervals.md`).
  S1 has its own CI-returning variant, `es_at_k_drift_ci()`, and a dedicated
  classifier, `classify_s1_ci()` (NOT `classify_ci()` -- the boundary
  convention at exactly -10%/-20% differs; see that function's docstring).
  The original point-estimate `es_at_k_drift()` is unchanged and still
  available. Closes a 92.5% floor-scale false-alert rate found in the
  point-estimate-only version, with a real floor-scale detection-power
  tradeoff explicitly flagged for governance sign-off, not resolved by the
  fix itself -- see `docs/Validation_Addendum_S1_Confidence_Intervals.md`.
- **generate_fair_dataset.py** -- Synthetic "null case" dataset generator
  used for the false-positive counter-test.
- **run_false_positive_test.py** -- Runs the null-case dataset through
  `metrics.py` and reports pass/fail.
- **run_small_sample_false_positive_test.py** -- Repeats the null-case test
  across many seeds at multiple event-log scales (10,000 up to 250,000) and
  reports the empirical false-positive rate at each. See
  `docs/Validation_Addendum_Confidence_Intervals.md`.
- **generate_drift_scenario_dataset.py** -- Builds two synthetic 16-week
  datasets: `drift_scenario` (a real rank-position regression against Small
  sellers is injected starting week 8) and `stable_scenario` (a model-version
  label changes at the same week, but nothing behavioral does -- a null
  control). Used for the S1/S2 scenario test.
- **run_drift_regression_test.py** -- Runs both scenarios through
  `es_at_k_drift_ci()`/`classify_s1_ci()` (S1, with its 95% CI) and a
  directly-computed pre/post average delta (S2), plus a corroborating
  absolute-E1 check, and reports pass/fail on both the true-positive and
  true-negative direction. See
  `docs/Validation_Addendum_Drift_Regression_Test.md` for the original
  write-up, including a caveat about S1's trailing-window behavior this test
  surfaced, and `docs/Validation_Addendum_S1_Confidence_Intervals.md` for the
  CI fix.
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

## Running the S1/S2 drift and regression scenario test

```
python3 generate_drift_scenario_dataset.py
python3 run_drift_regression_test.py
```

No external API or key required -- fully synthetic, seeded for reproducibility.

## Running the small-sample false-positive test

```
python3 run_small_sample_false_positive_test.py
```

Takes a few minutes (repeats dataset generation and metric computation across
many seeds and scales). No external API or key required.

## Running the Etsy pilot

Requires an approved Etsy Open API v3 key (`etsy.com/developers`, Personal
App path).

```
pip install pandas numpy requests
export ETSY_API_KEY="your_keystring_here"
export ETSY_SHARED_SECRET="your_shared_secret_here"
python3 etsy_pilot_collector.py
python3 run_etsy_pilot.py
```

Both values come from the same "Your Apps" page in the Etsy Developer portal.
Etsy's Open API v3 requires the x-api-key header to be
`<keystring>:<shared_secret>` on every request, including public read-only
endpoints -- see the `ETSY_SHARED_SECRET` note in `etsy_pilot_collector.py`'s
module docstring.

This produces a markdown report under `reports/`. Read the report's
Limitations section before citing any number from it -- this pilot is
explicitly scoped as a feasibility study (E1-E3 only, single-run,
median-split cohorts), not a statistically powered claim.
