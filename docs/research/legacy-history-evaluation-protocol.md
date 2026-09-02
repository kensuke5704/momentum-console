# Legacy History Evaluation Protocol

Last updated: 2026-09-03 JST
Branch: `research/cagr40-new-alpha-20260901`

## Purpose

Reconstruct the 2006–2018 historical ETF universe with point-in-time SEC filing data while preserving the information value of the historical return sample.

The universe-reconstruction layer and the strategy-performance layer are separate. Filing structure, report dates, filing dates, ETF series metadata, holdings descriptions, security identities, and structural eligibility may be inspected across the full 2006–2018 range. Strategy returns, CAGR, drawdown, Calmar, trade outcomes, and parameter comparisons may not be inspected across the full range at once.

## Frozen staged performance windows

### Phase 1 — DEVELOPMENT
- 2006-01-01 through 2010-12-31
- First historical performance window that may be opened.
- Used only after the legacy-universe conversion rules are frozen from structural evidence.
- Includes the 2008 crisis and 2009 recovery, which makes it useful for detecting catastrophic implementation errors early.

### Phase 2 — VALIDATION
- 2011-01-01 through 2014-12-31
- Must remain performance-sealed until Phase 1 has been evaluated and all permissible data-engineering fixes have been committed.
- No strategy parameter changes are permitted from Phase 1 or Phase 2 results.

### Phase 3 — SEALED_HOLDOUT
- 2015-01-01 through 2018-12-31
- Final historical holdout.
- Must not be opened for strategy performance until the legacy-universe reconstruction rules, data-quality gates, and evaluation metrics are frozen.
- Once opened, no parser/universe changes may be justified by strategy returns from this interval. Any post-open correction must be a documented objective data bug and must trigger a re-evaluation of the holdout interpretation.

## What may use 2006–2018 in full before performance testing

Allowed across the full range:
- SEC filing counts and filing availability
- filing/report dates
- SGML series and class-contract metadata
- ETF ticker metadata
- schedule-to-series structural mapping
- holdings parsing diagnostics
- issuer/security-id/ticker mapping coverage
- N-PX security-master coverage
- parser-artifact rates
- structural proxies for US/CORP/EC
- point-in-time staleness/recency diagnostics
- universe constituent counts and data-availability diagnostics that do not use future prices or returns

Not allowed across the full range before staged opening:
- strategy equity curves
- CAGR / annualized return
- MaxDD / Calmar / Sharpe / Sortino
- trade P&L
- hit rate or win/loss statistics
- Top2 realized returns
- parameter ranking based on returns
- choosing parser/universe rules because they improve Stage21 performance

## Anti-overfitting rule

Historical universe reconstruction may be changed only from structural/data-quality evidence. Stage21 production parameters remain frozen. The legacy bridge must not be tuned to improve historical returns.

## Required sequence

1. Build multi-year structural filing inventory for 2006–2018 without prices/returns.
2. Build PIT legacy ETF-series/holdings coverage across representative years.
3. Freeze issuer mapping and legacy US/CORP/EC proxy rules.
4. Freeze legacy universe scoring inputs and acceptance gates.
5. Generate 2006–2018 universe history without running strategy performance.
6. Open Phase 1 only: 2006–2010.
7. Record conclusions and freeze any objective data-engineering corrections.
8. Open Phase 2 only: 2011–2014.
9. Freeze final evaluation protocol and metrics.
10. Open Phase 3 only: 2015–2018.
11. Report all three historical phases separately from the frozen 2020–2026 production backtest and from True Forward OOS starting 2026-09-02.

## Enforcement

Research scripts that request a historical performance interval must pass through `scripts/research-legacy-history-periods.py`. By default, only Phase 1 is open. Phase 2 and Phase 3 require explicit environment gates and should not be enabled casually.
