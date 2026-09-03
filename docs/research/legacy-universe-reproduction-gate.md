# Legacy Universe Reproduction Gate

Status: preregistered before any legacy-universe builder implementation.

## Purpose

Do not implement or use a historical legacy Universe builder until the research pipeline demonstrates that the Production SEC N-PORT breadth Universe can be reproduced closely enough without strategy-return information.

## Gate A — adapter/scoring shadow parity

Use Production N-PORT filings as ground truth, but hide each holding's symbol from the candidate side. Resolve symbols only through a point-in-time cross-series issuer-name identity master built from other public ETF filings. Recompute the canonical breadth score with the same formula and eligibility semantics.

Evaluate the first 12 Production Universe months beginning 2020-01.

### Structural clarification made before observing shadow-parity results

The stored Production history begins before enough eligible public N-PORT filings existed to populate 80 names. For example, 2020-01 contains only 9 ranked names. Therefore overlap is measured against the actual stored Production size `K` for each month (`TopK`), with `K <= 80`; once `K=80` this is exactly Top80 overlap. The original overlap thresholds are unchanged. Canonical reconstruction from the same N-PORT inputs must first reproduce the stored Production list exactly for each evaluated month; otherwise the shadow test is invalid and stops.

Pass only if all of the following hold:

- median TopK/Top80 overlap >= 0.80;
- minimum monthly TopK/Top80 overlap >= 0.70;
- median Spearman rank correlation among common ranked names >= 0.75;
- Production Universe Top2 individual-name retention >= 0.80;
- both Production Universe Top2 names retained in >= 0.70 of evaluated months.

This gate tests adapter + identity mapping + scoring mechanics only. It does not establish legacy source fidelity.

## Gate B — actual legacy-source fidelity

After Gate A passes, validate reconstructed ETF series against the transition into Production N-PORT. No performance data may be used.

### Transition source-fidelity adjacency rule

Before judging source fidelity, define the comparison population without looking at holdings overlap. Series continuity must be exact by SEC `seriesId`.

For the pre-Production side, select the latest publicly filed **complete holdings report** for that exact series whose report date precedes the first Production N-PORT report date. During the 2019 transition, accepted complete-holdings forms may include `N-Q`, `N-CSR`, `N-CSRS`, or `NPORT-EX`; the form label itself is not a selection criterion. The source is selected only from filing metadata, exact series continuity, completeness as a holdings report, and report date. This clarification is structural because some funds migrated to N-PORT transition forms before others. It is fixed before observing aggregate Gate B overlap and does not change any pass threshold.

For the primary transition fidelity sample, the report-date gap should be at most 184 days where such an adjacent complete report exists. Longer-gap pairs may be reported as sensitivity diagnostics but do not determine whether a parser/source bridge is faithful, because real portfolio turnover is otherwise confounded with extraction error. Registrants and series are selected from filing metadata only; no holdings overlap, momentum, Universe rank, or strategy return may be used for inclusion.

This adjacency/source rule does not change the final Gate B practical thresholds below.

The final confirmation must include a direct or temporally adjacent Production comparison and must report:

- reconstructed ETF-series coverage;
- constituent/ticker mapping coverage by count and weight;
- TopK/Top80 overlap;
- common-name rank correlation;
- Production Universe Top2 retention.

A historical Universe builder is not considered implementable until the actual legacy-source comparison is strong enough to meet the same practical thresholds as Gate A, or a stricter preregistered replacement justified before observing strategy performance.

## Anti-overfitting rule

No threshold, parser rule, identity rule, country rule, or ranking rule may be changed based on Stage21 returns, CAGR, MaxDD, Calmar, trades, or 2006–2018 strategy outcomes.
