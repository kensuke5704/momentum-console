# Stage 16 — CFTC OI-Normalized Positioning — preregistration

Research branch only. Production Fixed60 unchanged.

Rationale: raw Asset Manager contract counts can change with total futures open interest. Use CFTC's own percent-of-open-interest fields instead of absolute contracts, without changing the lookback or portfolio states.

Frozen before result:
- CFTC NASDAQ MINI futures-only, code 209742.
- Signal value = `pct_of_oi_asset_mgr_long - pct_of_oi_asset_mgr_short`.
- One-week lag.
- Yellow when latest normalized net share is lower than four weekly reports earlier.
- Yellow allocation remains exactly the arithmetic midpoint of Stage11 Normal and Deep allocations.
- M3 trigger remains unchanged and overrides Yellow with the original Deep state.
- Monthly rebalance plus state-change rebalance; 10bp one-way turnover cost and 30bp stress.
- Objective remains planning proxy >=40% and historical MaxDD no worse than -17%.

No threshold or weight will be tuned after observing this result.