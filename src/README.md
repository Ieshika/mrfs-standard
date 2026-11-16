# src/ -- MRFS Reference Implementation

The reference implementation of the MRFS Technical Standard. Appendix C of the Technical Standard maps each section of the standard to the function that implements it.

Requirements: Python 3 with numpy and pandas (see `requirements.txt` in the repository root).

## Version 2

| File | Purpose |
|---|---|
| `metrics.py` | E1 (exposure ratio at K against a declared comparison population), E2 (normalised mean rank), E3 (exposure concentration), O1 to O3, S1 (drift), S2 (model regression), the audit declaration, default cohort assignment and status classification. The module docstring states the definitions. |
| `test_metrics.py` | 22 tests with hand-worked expected values. |
| `generate_synthetic_audit.py` | Deterministic synthetic marketplace. Sizes are counted in ranking events; each event has its own candidate set. |
| `run_validation.py` | Synthetic validation: E1 status rates, precision and coverage at 250 to 10,000 ranking events; drift, version-comparison and outcome checks. Results in `validation_results/`. |
| `run_validation_review.py` | Focused review of the Monitor band and weekly drift (partial run; completed rows in `validation_results/review_band_and_drift_partial.json`, comparison with `metrics.py` in `validation_results/review_check.json`; see the MRFS Validation Report, Section 9). |
| `generate_sample_audit_report.py` | Produces the worked example (Technical Standard, Appendix A) and every figure in it. Output in `sample_audit_report/`. |

```
cd src
python test_metrics.py
python run_validation.py
python generate_sample_audit_report.py
```

The worked example and the MRFS Validation Report are regenerated from these results by `docs/publication/make_publication_docs.py`.

Two things to know:

- E1 values from v1.0 and v1.1 are not comparable with version 2. On a synthetic ranking system that ignores cohort, version 2 reports about 1.0 for every cohort, while the v1 formula reports about 0.17 for Small sellers who hold 25% of seller accounts and 4% of listings (`validation_results/structure.json`).
- A status is evidence of a potential disparity that calls for investigation. It does not establish unfair treatment or its cause.
