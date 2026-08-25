# Cash-State Decomposition — Audited Summary

Workflow run: `32846251881` (success)

## Validation
- CPCM Production baseline median CAGR: **26.0447%**
- CPCM p05 CAGR: **-4.2594%**
- CPCM median MaxDD: **-41.3284%**
- These exactly reproduce the audited CPCM 1,000-path baseline.
- Synthetic-price fallback rate: **0.05929%**.

## State occupancy

### Realized 2020–2026 trading-day shares
- Invested: **50.6595%**
- Market-gate / market-origin recovery cash: **22.2422%**
- Individual-stop-origin recovery cash: **9.4125%**
- Portfolio-circuit-origin recovery cash: **15.5875%**
- Ready-next-open: **0.8993%**
- Other cash: **1.1990%**
- Top2 shortage: **0.0000%**

### CPCM 1,000 paths — marginal median share of trading days
- Invested: **41.9444%**
- Market-gate / market-origin recovery cash: **31.6667%**
- Individual-stop-origin recovery cash: **8.6508%**
- Portfolio-circuit-origin recovery cash: **14.7619%**
- Ready-next-open: **0.9524%**
- Other cash: **0.8730%**
- Top2 shortage: **0.0000%**

Note: marginal medians are computed separately by state and therefore need not sum exactly to 100%.

## Important correction
The first diagnostic artifact also printed an `actual.cagr` and `actual.dd` from a helper that hard-coded a five-year CAGR denominator and recomputed drawdown from the equity curve. Those two helper fields are **INVALIDATED and must not be used**. The state-occupancy counts above are unaffected. The authoritative realized Production statistics remain CAGR **55.3601%** and MaxDD **-21.9290%** from the official state-machine-aligned backtest.

## Interpretation
The dominant CPCM cash source is the Market Gate / market-origin recovery state (~31.7% of days), followed by Portfolio Circuit (~14.8%) and Individual Stop (~8.7%). Top2 scarcity contributes essentially nothing. Therefore the main source of cash drag is risk-state management rather than failure to find two eligible momentum candidates.
