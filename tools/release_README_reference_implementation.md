# MRFS reference implementation

The reference implementation of the MRFS Technical Standard (Appendix C of the standard maps each section to its function). Python 3 with numpy and pandas (`pip install -r requirements.txt`).

| File | Purpose |
|---|---|
| `metrics.py` | E1 to E3, O1 to O3, S1, S2, the audit declaration, default cohort assignment and status classification. The module docstring states the definitions. |
| `test_metrics.py` | 21 tests with hand-worked expected values. |
| `generate_synthetic_audit.py` | Deterministic synthetic marketplace, sized in ranking events. |
| `run_validation.py` | Synthetic validation reported in the MRFS Validation Report, Sections 4 to 8. Results in `validation_results/`. |
| `run_validation_review.py` | Focused review reported in the MRFS Validation Report, Section 9. Partial run: the completed rows are in `validation_results/review_band_and_drift_partial.json` and the comparison with `metrics.py` in `validation_results/review_check.json`; rerunning `band` or `drift` regenerates the completed rows but also runs the configurations that were not run (many hours). |
| `generate_sample_audit_report.py` | Produces the worked example in Appendix A of the Technical Standard. Output in `sample_audit_report/`. |

```
python test_metrics.py
python run_validation.py
python generate_sample_audit_report.py
```

The published results were produced with Python 3.11, numpy 2.4.4 and pandas 3.0.2. numpy does not guarantee identical random streams across all versions, so other versions may give slightly different figures.

The code is licensed under the MIT License.
