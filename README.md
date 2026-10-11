# MRFS — Marketplace Ranking Fairness Standard

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22073259.svg)](https://doi.org/10.5281/zenodo.22073259)

A method for auditing how marketplace ranking and recommendation systems distribute visibility across groups of sellers, with stated uncertainty, and for governing what happens when an audit finds a potential disparity.

**Status.** Version 2.0.0, published 11 October 2026. Version compatibility: E1 results from MRFS 2.0.0 are not directly comparable with those from MRFS 1.0 or 1.1 (see [`CHANGELOG.md`](CHANGELOG.md) and the Technical Standard, Appendix B).

## What MRFS does and does not claim

- It measures whether seller cohorts (by default Small, Medium and Large sellers; New and Established sellers) hold the top-ranked positions in proportion to their share of the listings a ranking system had to choose from.
- Every result carries a 95% confidence interval. Statuses (Pass, Monitor, Review Required, Insufficient Data) are decided from the interval.
- A status is evidence of a potential disparity that calls for investigation. It does not establish unfair treatment or its cause.
- MRFS does not approve or block software releases. Organisations decide through their own governance.

## Documents

| Document | Contents | PDF |
|---|---|---|
| MRFS Overview | A short introduction for a general reader (4 pages) | [MRFS-Overview.pdf](docs/MRFS-Overview.pdf) |
| MRFS Technical Standard | Metrics and decision rules, audit procedure, governance template, data specification, limitations; worked example, changes from v1.x, reference implementation and design choices in appendices | [MRFS-Technical-Standard.pdf](docs/MRFS-Technical-Standard.pdf) |
| MRFS Validation Report | How the reference implementation behaves on synthetic data, and its limitations | [MRFS-Validation-Report.pdf](docs/MRFS-Validation-Report.pdf) |

The Technical Standard is the normative document; the Overview and the Validation Report are informative. References are in [`docs/References.md`](docs/References.md).

The PDFs are built from the sources in [`docs/publication/`](docs/publication/). The worked example (Technical Standard, Appendix A) and the Validation Report are generated from the committed results, so they contain no hand-copied figures. Building needs pandoc 3 and XeLaTeX (TeX Live, with the Latin Modern, TeX Gyre and DejaVu fonts):

```
python docs/publication/make_publication_docs.py .
python docs/publication/build_publication.py
```

## Reference implementation

`src/metrics.py` implements the metric catalogue. `src/test_metrics.py` checks it against hand-worked examples, `src/run_validation.py` reproduces the synthetic validation, and `src/generate_sample_audit_report.py` produces the worked example in Appendix A of the Technical Standard. Python 3 with numpy and pandas:

```
cd src
python test_metrics.py
python run_validation.py
python generate_sample_audit_report.py
```

See [`src/README.md`](src/README.md).

## Changes from v1.x

The primary exposure metric (E1) is redefined and its values are not comparable with v1.0 and v1.1; fixed minimum event counts and universal data-quality thresholds are withdrawn; the synthetic validation of v1.x counted log rows as ranking events and is replaced by the Validation Report. See [`CHANGELOG.md`](CHANGELOG.md) and the Technical Standard, Appendix B. Versions 1.0.0 and 1.1.0 remain available from the concept DOI below.

## Citation and licence

Cite using [`CITATION.cff`](CITATION.cff) or the concept DOI [10.5281/zenodo.22073259](https://doi.org/10.5281/zenodo.22073259). Documents in `docs/` are licensed under CC BY 4.0 ([`docs/LICENSE-CC-BY-4.0.md`](docs/LICENSE-CC-BY-4.0.md)); code in `src/`, `tools/` and the build scripts in `docs/publication/` under the MIT License ([`LICENSE`](LICENSE)).

References to the NIST AI Risk Management Framework and to the four-fifths rule of the U.S. Uniform Guidelines on Employee Selection Procedures describe how MRFS relates to those sources. MRFS is not affiliated with or endorsed by NIST or other referenced organizations.
