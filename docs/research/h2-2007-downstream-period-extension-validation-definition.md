# H2 2007 Downstream Period-Extension Validation Definition

Defined: 2026-09-08 JST after strict source v4 passed its pre-defined source validation and before H2-2007 holdings, parser-invariance, structural mapping, PIT country, or historical-Universe builder results are evaluated.

This is not a new named gate and does not authorize Stage21 performance analysis.

## Fixed source lineage

- authoritative H2 2007 strict source run: `34188233028`
- authoritative H2 2007 strict source artifact: `10041257985`
- source catalog SHA256: `9ffed81a42044f7388221a60450a24967ea61f108eb63f66464699ada1849631`
- source period-extension validation: PASS under `docs/research/h2-2007-source-period-extension-validation-definition.md`
- closed-history candidate-discovery boundary: `docs/research/h2-2007-closed-history-candidate-discovery-boundary-correction.md`
- authoritative H1 2007 source artifact for closed-period comparison: `10040000632`

## Required invariants

- Raw holdings must use the exact authoritative H1 parser implementation and a mechanical Series-ID schema adapter only.
- Any source filing shared with the validated H1-2007 holdings artifact must have parser-semantic output invariance; drift is a stop condition.
- Structural mapping must reuse the frozen accepted mapping rules without ticker inference, fuzzy matching, current metadata repair, rank/return/outcome inference, or strategy data.
- Any proxy-voting / N-PX identity master used for mapping must itself be selected point-in-time from filings public by each H2 signal date. A later annual master must not be backfilled into earlier H2 months merely because it exists by period end.
- PIT country must reuse the frozen strict country resolver semantics. Historical country evidence used for a signal month must satisfy `evidenceDateFiled <= asOf`; no evidence filed after that month's signal date may enter resolution.
- UNKNOWN country remains UNKNOWN in the primary path.
- CORP bridge materiality invariant remains explicit; positive mapped COMMON_EQUITY rows must not silently redefine known non-CORP security names as CORP.
- `scripts/research-historical-universe-builder.py` remains frozen at git blob `1357402f34dfea1c1dbdcaac7de5078b680eb5c3`.
- Builder input catalog lineage must be fixed to source artifact `10041257985` and SHA256 `9ffed81a42044f7388221a60450a24967ea61f108eb63f66464699ada1849631`.
- Jul-Dec 2007 builder output must match the independent primary Universe rows produced by the frozen country diagnostic path exactly for all six signal months, including as-of, eligible source count, full ranked rows, scores, and symbol-level metrics.
- Closed Jan-Jun 2007 reconstruction must remain the already validated H1 result; H2 downstream processing must not rewrite the closed 18-month stitched artifact.

## Prohibited

Do not use Stage21 returns, ranks, CAGR, MaxDD, Calmar, trades, portfolio outcomes, or other strategy performance to choose or revise parsing, mapping, country, source eligibility, breadth, or Universe reconstruction rules. Do not modify `main` or Production.

PASS requires all invariants above to hold exactly. Any parser, PIT mapping, country, lineage, or builder-parity failure must be audited rather than accommodated by changing rules after results are known.
