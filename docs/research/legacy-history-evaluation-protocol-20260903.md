# Legacy History Evaluation Protocol — 2026-09-03

## Objective
Reconstruct a point-in-time ETF holdings universe for 2006–2018 without consuming the historical return sample all at once.

## Separation of data uses
Structural SEC filing data may be inspected across 2006–2018 for parser, identity, filing-availability, and point-in-time universe reconstruction work. This does not include security returns, strategy returns, CAGR, drawdown, Calmar, trade outcomes, or any other performance-derived quantity.

Performance data is opened sequentially:

1. DEVELOPMENT: 2006-01-01 through 2010-12-31
2. VALIDATION: 2011-01-01 through 2014-12-31
3. SEALED_HOLDOUT: 2015-01-01 through 2018-12-31

The default code gate permits only DEVELOPMENT. VALIDATION and SEALED_HOLDOUT require separate explicit environment gates and must not be opened merely because earlier performance is disappointing.

## Allowed before performance testing
- SEC filing inventory across all years
- N-Q/N-CSR/N-CSRS series identification
- Schedule-to-series mapping
- Holdings parsing
- N-PX issuer/ticker/security-id mapping
- Structural US/CORP/EC proxy classification
- Filing-date PIT availability checks
- Universe-score parity tests using synthetic inputs
- Cross-year parser/mapping coverage metrics
- Data-quality regression tests

## Prohibited before the relevant phase is opened
- Price/return loading for that phase
- Stage21 or Fixed60 equity curves for that phase
- CAGR, MaxDD, Calmar, Sharpe, hit rate, turnover P&L, trade outcomes
- Changing parser/universe rules in response to performance
- Choosing which filings/years to parse based on strategy results

## Universe reconstruction rule
Use the production universe functional form unchanged where the legacy data can supply equivalent inputs:

`3*log1p(etfCount) + 0.5*log1p(aggregateWeight) + 0.5*log1p(recencyWeight)`

with production eligibility `etfCount >= 2 OR maxWeight >= 4`, latest-public-filing PIT selection, and `exp(-ageDays/120)` recency weighting.

Any legacy-only structural proxy must be frozen from filing/data-quality evidence before its associated performance phase is opened.

## Current sequence
1. Inventory legacy filing availability across 2006–2018. DONE.
2. Fix deterministic anchor-year structural samples. IN PROGRESS.
3. Measure parser/series/ticker coverage across anchor years without returns.
4. Freeze legacy holdings-to-universe conversion rules.
5. Build monthly PIT universe history structurally.
6. Run DEVELOPMENT performance only (2006–2010).
7. Decide whether the reconstruction is technically adequate; do not tune Stage21.
8. If predeclared gates are met, explicitly open VALIDATION (2011–2014).
9. Only after validation conclusions are frozen, explicitly open SEALED_HOLDOUT (2015–2018) once.

Production strategy remains untouched throughout.
