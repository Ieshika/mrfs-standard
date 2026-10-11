# What MRFS is for

On a marketplace, the first few positions of a search result or recommendation slate decide which sellers buyers consider. Evidence from a field experiment on an online travel platform shows that rank position changes which results consumers examine [1]. If a ranking system consistently places some groups of sellers lower, for example small or new sellers, those sellers are seen less, whether or not anyone intended it.

The Marketplace Ranking Fairness Standard (MRFS) is a method for checking this. It specifies how to measure whether groups of sellers hold top-ranked positions in proportion to what the ranking system had to choose from, how sure that measurement is, and what an organisation should do when a measurement points to a possible problem.

# What makes the approach distinct

- **It compares like with like.** A group of sellers is compared with its share of the listings the ranking system actually considered, not with its share of seller accounts. A ranking system that ignores seller identity is expected to score close to parity, apart from chance variation, however unevenly inventory is spread across sellers.
- **Uncertainty is part of every result.** Each result carries a 95% confidence interval, and a status is assigned only when the interval clearly supports it. Otherwise the result is "Insufficient Data", which is a legitimate answer.
- **Choices are declared before results are seen.** Seller groups, what is compared with what, and the thresholds are fixed in advance and recorded.
- **It says what it cannot show.** A result is evidence that calls for investigation, not proof of unfair treatment, and MRFS does not approve or block software releases.

# Three core measures

| Measure | Question it answers | Reading the value |
|:-------------------------|:------------------------------------------------|:----------------------------------------------|
| **E1** Exposure ratio | Do a group's listings appear in the top 10 as often as their share of the candidates would suggest? | 1.0 = in proportion; below 1.0 = fewer top positions. Carries a status in platform audits. |
| **E2** Mean rank position | Where in the list do the group's listings sit? | 0.5 = middle of the list; lower is higher up. Reported, no status. |
| **E3** Exposure concentration | Are top positions spread across many sellers or held by a few? | 0 = evenly spread; near 1 = held by a few. Reported, no status. |

: The three core measures.

E1 is decided against two lines. Below 0.80 a group is flagged **Review Required**; between 0.80 and 0.85 it is flagged **Monitor**; at or above 0.85 it is **Pass**, each only when the whole confidence interval lies in that range. The 0.80 line is borrowed by analogy from the four-fifths rule used in U.S. employment selection; it has not been validated for ranking, and no agency has endorsed its use here. MRFS also defines outcome measures (clicks and conversions), drift between monitoring windows, and comparisons between versions of a ranking system.

# Two kinds of assessment

| | Platform audit | External assessment |
|:--------------------|:----------------------------------------------|:----------------------------------------------|
| Who | The marketplace, or an auditor with access to its logs | A researcher or other third party |
| Data | Every candidate listing the ranking system considered at a named stage | The public results for a fixed set of searches, to a stated depth |
| Results | Ratios, intervals and statuses, for the declared stage | Ratios and intervals only, about placement among the results retrieved |

: Platform audits and external assessments.

An external assessment cannot see sellers who never appear in the results, so it can only describe placement among those that do.

# How an audit works

```{=latex}
\begin{figure}[h]
\centering
\begin{tikzpicture}[node distance=3.5mm,
  box/.style={draw=mrfsnavy,line width=0.5pt,fill=reqbg,minimum height=14mm,text width=19mm,align=center,font=\sffamily\footnotesize},
  arr/.style={-{Stealth[length=2mm]},color=mrfsnavy,line width=0.6pt}]
\node[box] (a) {Declare choices in advance};
\node[box,right=of a] (b) {Collect data; report its quality};
\node[box,right=of b] (c) {Form seller groups};
\node[box,right=of c] (d) {Compute measures with intervals};
\node[box,right=of d] (e) {Assign statuses; report};
\node[box,right=of e,fill=white,draw=mrfsgrey] (f) {Organisation investigates and decides};
\draw[arr] (a) -- (b); \draw[arr] (b) -- (c); \draw[arr] (c) -- (d); \draw[arr] (d) -- (e); \draw[arr] (e) -- (f);
\end{tikzpicture}
\caption{The audit workflow.}
\end{figure}
```

Between full audits, organisations are recommended to monitor E1 and its week-to-week change, and to run an additional audit after a material change to the ranking system.

# Reading results, and their limits

- **A status is a signal, not a verdict.** Review Required means a possible disparity that should be investigated. Differences in relevance, inventory or buyer intent can explain it.
- **"Insufficient Data" is common for small groups.** A group that holds only a small share of the listings needs many searches before its interval is narrow enough for a status. The Monitor band is especially hard to confirm.
- **Scope is limited to what was observed.** A platform audit covers ranking from the declared stage onward; an external assessment covers only the results retrieved.
- **Testing so far is synthetic.** The reference implementation has been tested on simulated marketplaces with a known answer. It has not been validated on a live marketplace's internal data.

# Where to find more

| Resource | Contents |
|:------------------------------|:------------------------------------------------------------|
| MRFS Technical Standard | Definitions, decision rules, audit procedure, governance template, data specification, worked example |
| MRFS Validation Report | How the reference implementation behaves on synthetic data, and its limitations |
| Reference implementation | Python code with tests and the scripts that reproduce every published figure: <https://github.com/Ieshika/mrfs-standard> |
| Citation | Concept DOI, covering all versions: <https://doi.org/10.5281/zenodo.22073259> |

: Further resources.

# Reference {.unnumbered}

::: references
[1] Ursu, R. M. (2018). The power of rankings: Quantifying the effect of rankings on online consumer search and purchase decisions. *Marketing Science*, 37(4), 530–552. <https://doi.org/10.1287/mksc.2017.1072>
:::
