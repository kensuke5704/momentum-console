# Stage 14 — CFTC Nasdaq Asset Manager Positioning — 2026-09-01

Research branch only. Production Fixed60 unchanged. Historical same-sample research through 2026-08-25; not True Forward OOS evidence.

Preregistered signal:
- CFTC Traders in Financial Futures, futures-only, NASDAQ MINI code 209742.
- Asset Manager net position = long - short.
- One-week lag before use.
- Defensive when latest available net position is lower than four weekly reports earlier.
- Frozen Stage11 allocation and M3 trigger otherwise unchanged.
- 10bp one-way turnover cost; 30bp cost stress.

Data validation:
- CFTC API returned 1,055 weekly rows from 2006-06-13 through 2026-08-25 after correcting only the published API field names (`asset_mgr_positions_long`, `asset_mgr_positions_short`).

Results:
- CAGR: 39.10%
- MaxDD: -17.15%
- Annualized volatility: 20.72%
- Calmar: 2.280
- Stress median CAGR: 36.80%
- Rolling-36M median CAGR: 37.97%
- Rolling-36M worst CAGR: 20.57%
- Planning proxy: 36.80%

Conclusion:
CFTC Asset Manager positioning materially reduced MaxDD versus Stage11 (-18.28% -> -17.15%), indicating genuine anticipatory risk information. However, sending every CFTC deterioration directly to the full Stage11 defensive allocation is too costly in return and pushes the planning proxy below 40%.

Next structural test: retain the same CFTC signal and lag, but use it only for a mild Yellow state when M3 is not active; M3 continues to trigger the original Deep Defensive state. Do not tune the CFTC lookback or threshold on this sample.