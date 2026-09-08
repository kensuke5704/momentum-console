# H1 2007 Downstream Period-Extension Validation Definition

Defined: 2026-09-08 JST before H1-2007 holdings, structural mapping, PIT country, or historical-Universe builder results are evaluated.

This is not a new named gate and does not authorize Stage21 performance analysis.

## Required invariants

- Raw holdings must use the exact authoritative H1 parser implementation and a mechanical Series-ID schema adapter only.
- Any source filing shared with the validated H2-2006 holdings artifact must have parser-semantic output invariance; drift is a stop condition.
- Structural mapping must reuse the frozen accepted mapping rules without ticker inference, fuzzy matching, current metadata repair, rank/return/outcome inference, or strategy data.
- PIT country must reuse the frozen strict country resolver semantics. Historical country evidence used for a signal month must satisfy `evidenceDateFiled <= asOf`; no evidence filed after 2007-06-29 may enter H1-2007 resolution.
- UNKNOWN country remains UNKNOWN in the primary path.
- CORP bridge materiality invariant remains explicit; positive mapped COMMON_EQUITY rows must not silently redefine known non-CORP security names as CORP.
- `scripts/research-historical-universe-builder.py` remains frozen at git blob `1357402f34dfea1c1dbdcaac7de5078b680eb5c3`.
- Builder input catalog lineage must be fixed to the accepted H1-2007 strict source catalog.
- Jan-Jun 2007 builder output must match the independent primary Universe rows produced by the frozen country diagnostic path exactly for all six signal months, including as-of, eligible source count, full ranked rows, scores, and symbol-level metrics.

## Prohibited

Do not use Stage21 returns, ranks, CAGR, MaxDD, Calmar, trades, portfolio outcomes, or other strategy performance to choose or revise parsing, mapping, country, source eligibility, breadth, or Universe reconstruction rules. Do not modify `main` or Production.

PASS requires all invariants above to hold exactly. Any parser, PIT, lineage, or builder-parity failure must be audited rather than accommodated by changing rules after results are known.
