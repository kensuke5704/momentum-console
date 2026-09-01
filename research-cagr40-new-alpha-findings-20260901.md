# CAGR40 New Alpha Exploration — 2026-09-01

Production Fixed60 remains unchanged. Research branch: `research/cagr40-new-alpha-20260901`.

## Objective
Find a genuinely distinct return engine that can ultimately help a portfolio target forward-planning CAGR ~40% while keeping historical MaxDD near 15-17%, without borrowing and without gross exposure above 100%.

Standalone screening gate for these exploratory engines used planning CAGR >=25%, MaxDD no worse than 35-40% depending on structure, and low monthly correlation to Fixed60. Planning proxy = min(stress-median CAGR, rolling-36M median CAGR). It is not True Forward OOS evidence.

## Stage 1 — non-equity leveraged macro trend
- AA: GLD/TLT/USO directional bull/inverse sleeves using 200DMA. CAGR -10.14%, MaxDD -71.28%, planning -17.99%, Fixed60 corr -0.323. Reject.
- AB: same assets long/flat. CAGR 0.30%, MaxDD -71.66%, planning -5.28%, corr -0.142. Reject.
- AC: 63d winner rotation among leveraged macro bulls. CAGR 15.42%, MaxDD -66.81%, planning -1.93%, corr 0.016. Reject.

Conclusion: independence was achievable, but return density and drawdown quality were unacceptable.

## Stage 2 — relative-value leveraged ETF pairs
- AD: semiconductors vs Nasdaq. CAGR 6.17%, MaxDD -40.74%, planning ~0%, corr 0.219. Reject.
- AE: small-cap vs Nasdaq. CAGR -11.56%, MaxDD -59.44%, planning -11.39%, corr 0.030. Reject.
- AF: financials vs Nasdaq. CAGR -17.21%, MaxDD -78.87%, planning -18.81%, corr 0.155. Reject.

Conclusion: market-neutralization reduced correlation but also removed the return source.

## Stage 3 — monthly leveraged bull/inverse directional rotation
- AG: equity leveraged bull/inverse Top2 by positive 63d momentum. CAGR 1.27%, MaxDD -76.13%, planning -12.82%, corr 0.322. Reject.
- AH: equity + macro leveraged bull/inverse Top2. CAGR -12.03%, MaxDD -83.05%, planning -25.41%, corr 0.185. Reject.

Conclusion: leveraged ETF decay plus slow monthly direction changes produced unacceptable drawdowns and weak rolling returns.

## Stage 4 — daily 200DMA bull/inverse switch
- AI: QQQ -> TQQQ/SQQQ. CAGR 17.54%, MaxDD -64.84%, planning 17.16%, corr 0.429. Reject.
- AJ: QQQ + SMH directional sleeves. CAGR 23.18%, MaxDD -74.24%, planning 9.06%, corr 0.376. Reject.
- AK: QQQ + SMH + IWM directional sleeves. CAGR 20.08%, MaxDD -69.31%, planning 3.10%, corr 0.391. Reject.

Conclusion: inverse ETF participation did not solve whipsaw or leveraged-decay risk.

## Stage 5 — PIT N-PORT flow acceleration
Monthly signal, Top5 equal weight, next-open, 10bp/side, no price ranking.

- AL Ownership Breadth Acceleration: CAGR 18.15%, MaxDD -44.50%, stress median 17.18%, rolling36 median 16.21%, planning 16.21%, Fixed60 corr 0.390. Reject.
- AM Aggregate Weight Acceleration: CAGR 23.16%, MaxDD -39.42%, stress median 19.83%, rolling36 median 16.30%, rolling36 worst +2.64%, planning 16.30%, Fixed60 corr 0.496. Reject.
- AN New Sponsorship: same realized ranking/result as AL in this dataset; planning 16.21%, corr 0.390. Reject.

Conclusion: N-PORT holding-flow changes provide some positive return but insufficient planning return and insufficient independence for the portfolio objective. Stop further N-PORT derivative mining on the same sample.

## Stage 6 — SEC XBRL fundamental acceleration
Preregistered, not evaluated:
- AO annual FCF acceleration
- AP diluted-share-count contraction
- AQ CFO/net-income quality improvement

All use only annual 10-K facts filed by the signal date, PIT N-PORT universe, Top5, next-open, and no price ranking.

Infrastructure result: GitHub Actions could not access SEC companyfacts. Official ticker mapping initially returned 403; after replacing only the ticker map with a pinned public GitHub mirror, `data.sec.gov` companyfacts still returned zero usable downloads (0/247 requested symbols, 230 attempted and failed). Therefore AO/AP/AQ are **data-blocked / untested**, not rejected. No strategy rule was changed in response to this access failure.

## Stage 7 — High-Yield credit-spread guard on frozen M3 core
Purpose: add a genuinely different credit-market state variable to the high-return M3 architecture rather than tuning its price thresholds.

Data:
- ICE BofA US High Yield OAS history, one-session lagged before use.
- FRED now exposes only about three recent years for this ICE series, so a public long-history representation was used only to restore 2020-2026 coverage. The strategy rules were fixed before results.

Frozen M3 allocation retained:
- normal: Fixed60 85%, G 15%
- defensive: Fixed60 30%, G 15%, BTAL 35%, cash 20%

Preregistered macro additions:
- AR: defensive when OAS >= 5%
- AS: defensive when 20-observation OAS increase >= 1 percentage point
- AT: AR OR AS
- return to normal only after both M3 and macro condition are clear for 5 sessions

Results:
- AR: CAGR 44.72%, MaxDD -22.77%, stress median 44.42%, rolling36 median 42.04%, rolling36 worst 22.32%, planning 42.04%. Reject on DD.
- AS: CAGR 51.71%, MaxDD -23.30%, stress median 49.82%, rolling36 median 46.38%, rolling36 worst 24.78%, planning 46.38%. Reject on DD.
- AT: CAGR 44.30%, MaxDD -22.77%, stress median 43.55%, rolling36 median 41.38%, rolling36 worst 22.14%, planning 41.38%. Reject on DD.

Conclusion: credit-market information can preserve a >40% planning-return proxy, but it does not solve the approximately 22-23% drawdown regime. Do not tune OAS thresholds further on this sample.

## Stage 8 — static DBMF managed-futures sleeve
Purpose: add an independent managed-futures return stream without changing the frozen M3 trigger. DBMF weights were preregistered at 0/10/15/20%; all original M3 weights were proportionally scaled by `(1-w)`.

Daily fixed-weight screen:
- 0% DBMF: CAGR 52.59%, MaxDD -23.30%, planning 47.79%.
- 10% DBMF: CAGR 48.03%, MaxDD -21.44%, planning 43.56%.
- 15% DBMF: CAGR 45.75%, MaxDD -20.50%, planning 41.47%.
- 20% DBMF: CAGR 43.47%, MaxDD -19.54%, planning 39.27%.

No weight between these preregistered points was searched. 15% is the largest tested allocation that preserved planning >=40%; 20% crossed below the planning-return gate.

Conclusion: managed futures materially improve the return/DD frontier, but static allocation alone still does not reach 15-17% MaxDD.

## Stage 9 — operational rebalance verification of 15% DBMF
The 15% sleeve was re-tested using monthly portfolio rebalancing plus immediate rebalance only when the frozen M3 state changes. Portfolio turnover was charged at 10bp one-way, with a 30bp stress.

Result:
- CAGR 45.98%
- MaxDD -20.19%
- annualized volatility 25.55%
- stress median CAGR 44.43%
- rolling36 median CAGR 42.34%
- rolling36 worst CAGR 22.23%
- planning proxy 42.34%

Conclusion: the DBMF benefit survives a substantially more operational allocation model and is not an artifact of daily fixed-weight rebalancing. It remains short of the 17% DD objective.

## Current research conclusion
Two constraints are now empirically distinct:
1. Historical architectures with a planning-return proxy above 40% are available.
2. Managed futures improve the best observed frontier to roughly 42% planning CAGR with ~20% MaxDD under monthly rebalance.
3. The 15-17% MaxDD objective is still not reached without reducing the planning proxy below 40%.

Price-only ETF architectures, N-PORT flow, a simple credit-spread overlay, and a static managed-futures sleeve have not bridged the full gap. SEC annual fundamentals remain untested only because the current GitHub Actions environment cannot retrieve SEC companyfacts reliably.

The next structural test is to keep the 15% normal-state DBMF sleeve fixed and replace 50% or 100% of the M3 defensive BTAL sleeve with DBMF, without modifying the M3 trigger or searching additional thresholds.

Do not grid-search existing price, BTAL, TQQQ, OAS, DBMF, or N-PORT thresholds on the 2020-2026 sample. Do not modify Fixed60 Production mechanics based on this work.