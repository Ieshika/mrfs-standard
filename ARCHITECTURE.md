# Architecture

## Repository layout

| Path | Contents |
|---|---|
| `docs/MRFS-Overview.pdf`, `docs/MRFS-Technical-Standard.pdf`, `docs/MRFS-Validation-Report.pdf` | The three published documents |
| `docs/publication/` | Markdown sources of the three documents, the LaTeX style, `make_publication_docs.py` (generates the worked example and the Validation Report from committed results) and `build_publication.py` (builds the PDFs) |
| `docs/References.md` | The consolidated bibliography |
| `src/metrics.py` | Reference implementation (version 2) |
| `src/test_metrics.py` | Tests with hand-worked expected values |
| `src/generate_synthetic_audit.py` | Deterministic synthetic marketplace |
| `src/run_validation.py`, `src/run_validation_review.py` | Synthetic validation; results in `src/validation_results/` |
| `src/generate_sample_audit_report.py` | Produces the worked example; output in `src/sample_audit_report/` |
| `tools/make_release.py` | Assembles the curated release folder from an explicit file list |

## Documents

1. **MRFS Overview** (informative): purpose, approach, the three core measures, the two kinds of assessment, how an audit works, and the limits of a result.
2. **MRFS Technical Standard** (normative): metrics and decision rules (E1–E3, O1–O3, S1–S2, Q1–Q3, statuses, thresholds, uncertainty); audit procedure; reference governance charter; data specification; limitations. Appendices: worked example (generated), changes from v1.x, reference implementation, design choices and their sources.
3. **MRFS Validation Report** (informative): behaviour of the reference implementation on synthetic data (generated).

## Generated content

The worked example and the Validation Report contain no hand-copied figures. `make_publication_docs.py` reads the committed results in `src/sample_audit_report/` and `src/validation_results/`. To change a figure, change the code or the seed, rerun the script that produces the results, regenerate and rebuild.

## Key design choices

The Technical Standard states each choice MRFS makes and whether it is externally sourced. In summary:

- E1 compares a cohort's top-K positions with the number expected from its share of listings in a declared comparison population (the candidate set at a named stage, or results retrieved to a stated depth).
- Statuses are decided from 95% event-level bootstrap intervals; statuses apply only to candidate-set populations and only to the declared stage.
- 0.80 is an MRFS normative threshold adopted by analogy to the four-fifths rule; 0.85 and the drift thresholds are MRFS defaults that may be changed if pre-specified.
- There are no fixed minimum event counts and no universal data-quality thresholds.

## Non-goals

- No certification or badging programme.
- No expansion into a general AI evaluation standard.
- No additional normative documents; the reference implementation stays in `src/` as code.
