# References

*Standalone citations document for the MRFS volumes in `docs/volumes/`. Entries below are merged into: Volume 1 (positioning statement — AWRF/TREC and NIST AI RMF citations), Volume 2 Section 6 (threshold citations — EEOC four-fifths rule), Volume 4 (NIST AI RMF alignment), and a closing "References" section in each volume that cites it.*

## Governance framework

Tabassi, E. (2023). *Artificial Intelligence Risk Management Framework (AI RMF 1.0)*. NIST AI 100-1. National Institute of Standards and Technology, Gaithersburg, MD. https://doi.org/10.6028/NIST.AI.100-1

- Cited in: Volume 1 (positioning statement), Volume 4 (Governance Charter — NIST AI RMF alignment claim).
- Use: MRFS's GOVERN/MAP/MEASURE/MANAGE-adjacent structure in Volume 4 should cite this directly rather than referencing "NIST AI RMF" generically.

## Ranking exposure-fairness metrics (AWRF / TREC Fair Ranking Track)

Sapiezynski, P., Zeng, W., Robertson, R. E., Mislove, A., & Wilson, C. (2019). Quantifying the Impact of User Attention on Fair Group Representation in Ranked Lists. *Companion Proceedings of the 2019 World Wide Web Conference (WWW '19)*, 553–562. https://doi.org/10.1145/3308560.3316824

- Origin of the underlying exposure-weighted fairness measurement approach later formalized as AWRF.

Biega, A. J., Diaz, F., Ekstrand, M. D., & Kohlmeier, S. (2023). Overview of the TREC 2021 Fair Ranking Track. *arXiv:2302.10856*. https://arxiv.org/abs/2302.10856

- Formal adoption and naming of AWRF (Attention-Weighted Rank Fairness) as the track's official metric: cumulated exposure per group vs. a target distribution, compared via Jensen–Shannon divergence.
- Cited in: Volume 1 positioning statement (already references "TREC Fair Ranking Track" and "AWRF" by name — this is the citation that statement needs), Volume 2 (E1–E3 exposure metrics, as prior art MRFS builds on and diverges from — MRFS uses simpler rank-position and share-based measures rather than JS-divergence).

Singh, A., & Joachims, T. (2018). Fairness of Exposure in Rankings. *Proceedings of the 24th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining (KDD '18)*, 2219–2228. https://doi.org/10.1145/3219819.3220088

- Foundational academic source for exposure-as-fairness-currency framing. Relevant to Volume 2's conceptual framing of E1–E3.

## Commercial impact of ranking position (marketplace-specific motivation)

Ursu, R. M. (2018). The Power of Rankings: Quantifying the Effect of Rankings on Online Consumer Search and Purchase Decisions. *Marketing Science*, 37(4), 530–552. https://doi.org/10.1287/mksc.2017.1072

- Field-experiment evidence (Expedia) that rank position causally affects purchase outcomes — supports Volume 1's motivation for why exposure fairness matters commercially, not just normatively.

Khenissi, S., & Nasraoui, O. (2020). Modeling and Counteracting Exposure Bias in Recommender Systems. *arXiv:2001.04832*. https://arxiv.org/abs/2001.04832

- Relevant to Volume 2/3 discussion of exposure-bias feedback loops and to the NDCG relevance-circularity caveat — click data used to derive relevance is itself shaped by prior exposure.

## Outcome-parity threshold (EEOC four-fifths rule)

Equal Employment Opportunity Commission, Civil Service Commission, Department of Labor, & Department of Justice. (1978). *Uniform Guidelines on Employee Selection Procedures*, 29 C.F.R. § 1607 (1978), specifically § 1607.4(D). https://www.ecfr.gov/current/title-29/subtitle-B/chapter-XIV/part-1607

- Origin of the "four-fifths" / 80% rule: "A selection rate for any race, sex, or ethnic group which is less than four-fifths (4/5) of the rate for the group with the highest rate will generally be regarded... as evidence of adverse impact."
- Cited in: Volume 2 Section 6 (O3 CTR/CVR Disparate Impact threshold, currently described only as "EEOC four-fifths analogy" with no citation). The note explicitly states that this threshold was derived for employment selection decisions, not ranking exposure, and is adopted by analogy pending empirical calibration.

## Related open-source fairness auditing toolkits

Bellamy, R. K. E., Dey, K., Hind, M., Hoffman, S. C., Houde, S., Kannan, K., Lohia, P., Martino, J., Mehta, S., Mojsilović, A., Nagar, S., Ramamurthy, K. N., Richards, J., Saha, D., Sattigeri, P., Singh, M., Varshney, K. R., & Zhang, Y. (2018). AI Fairness 360: An Extensible Toolkit for Detecting, Understanding, and Mitigating Unwanted Algorithmic Bias. *arXiv:1810.01943*. https://arxiv.org/abs/1810.01943

Saleiro, P., Kuester, B., Hinkson, L., London, J., Stevens, A., Anisfeld, A., Rodolfa, K. T., & Ghani, R. (2018). Aequitas: A Bias and Fairness Audit Toolkit. *arXiv:1811.05577*. https://arxiv.org/abs/1811.05577

Weerts, H., Dudík, M., Edgar, R., Jalali, A., Lutz, R., & Madaio, M. (2023). Fairlearn: Assessing and Improving Fairness of AI Systems. *Journal of Machine Learning Research*, 24(257), 1–8. https://arxiv.org/abs/2303.16626

- Cited in: Volume 1, as the adjacent-but-different landscape — these are general-purpose ML fairness *toolkits* (classification-focused bias metrics/mitigation), not ranking-specific audit standards. Useful to name explicitly so MRFS's positioning ("no operational standard for commercial marketplace ranking specifically") isn't read as ignoring the broader fairness-tooling ecosystem.

---

*Not yet covered: multiple-comparisons correction citation (Bonferroni/Benjamini-Hochberg) for the drift-monitoring methodology.*
