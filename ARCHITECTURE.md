# ARCHITECTURE.md

## Structure

Six volumes, deliberately not expanded beyond this for v1.0:

1. **Standard Overview** — purpose, positioning/gap statement, scope, architecture, document index
2. **Evaluation Metric Catalog** — 11 metrics across Exposure (E1–E3), Outcome (O1–O3), Stability (S1–S2), Quality Guardrails (Q1–Q3)
3. **Audit Protocol** — repeatable methodology: data requirements, cohort definitions, testing methodology, drift monitoring, mitigation workflow, standardized report structure
4. **Governance Charter & Release Gate Policy** — roles, decision rights, escalation procedure, NIST AI RMF alignment
5. **Marketplace Logging & Data Specification** — platform-neutral logging schemas, data retention, privacy considerations
6. **Sample Audit Report** — reference demonstration on synthetic data (currently a known-disparity dataset only — see `docs/Validation_Addendum_False_Positive_Test.md` for the companion null-case/false-positive test)

## Positioning statement (use verbatim across whitepaper, README, and related materials)

> Academic research has established methods for measuring exposure fairness in ranked retrieval — most notably the NIST TREC Fair Ranking Track and the Attention-Weighted Rank Fairness (AWRF) metric, which quantify whether visibility across ranked results matches a fair target distribution. Separately, NIST's AI Risk Management Framework provides general-purpose governance guidance for AI systems. Neither has been translated into an operational standard for commercial marketplace ranking: a deployable audit protocol, a cohort-based metric catalog suited to seller-visibility contexts, a platform-neutral logging specification enabling third-party audit without proprietary access, and governance gates that convert audit findings into concrete organizational action. MRFS closes that gap.

## Core metrics (from Volume 2 — full formulas there)

| ID | Metric | Category | Threshold (Pass / Monitor / Review) |
|---|---|---|---|
| E1 | ExposureShare@K | Exposure | ≥0.85 / 0.80–0.85 / <0.80 |
| E2 | Mean Rank Position (Δ) | Exposure | <5 pos / 5–10 pos / ≥10 pos |
| E3 | Exposure Gini | Exposure | Flag >0.60 within underexposed cohort |
| O1 | CTR Parity Ratio | Outcome | Evaluated via O3 |
| O2 | CVR Parity Ratio | Outcome | Evaluated via O3 |
| O3 | CTR/CVR Disparate Impact | Outcome | ≥0.85 / 0.80–0.85 / <0.80 (EEOC four-fifths analogy) |
| S1 | ExposureShare@K Drift | Stability | <10% / ≥10% / ≥20% or sustained >2wk |
| S2 | Model Regression Delta | Stability | Any metric crossing S1 triggers full audit |
| Q1–Q3 | Overall CTR/CVR/NDCG guardrails | Quality | ≤2% (CTR/CVR) / ≤5% (NDCG) relative decline |

Cohorts: Small/Large (listing-volume quartile), New/Established (12-month tenure threshold), optional protected-class cohorts (minority/women/veteran-owned, where flagged).

## Tech stack

- **Docs:** .docx, edited via unzip → `word/document.xml` → `merge_runs.py` → `str_replace` → rezip → `validate.py` (see `/mnt/skills/public/docx/SKILL.md` conventions if working in Claude environment; otherwise treat as any OOXML document)
- **Metrics implementation (planned, not yet built):** Python — numpy, pandas, scipy
- **Publication targets:** GitHub (this repo) → Zenodo (DOI via GitHub release) → arXiv/SSRN preprint → FAccT/AIES/RecSys workshop track (fast turnaround vs. full conference cycles)

## Explicit non-goals for v1.0 (do not add without a deliberate scope review)

- No certification/badging program
- No multi-module "AI Evaluation Standard" expansion (fairness + explainability + robustness + drift + hallucination, etc.)
- No Implementation Guide / Case Studies / Reference Implementation as *new volumes* — a reference implementation belongs in `src/` as code, not as a 7th documentation volume
- No eponymous naming
