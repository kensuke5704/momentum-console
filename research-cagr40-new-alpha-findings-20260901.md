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

## Research decision
Stop additional same-sample mining of price-only leveraged/inverse ETF architectures. Four structurally distinct families failed. The next useful research step must add genuinely new information rather than another OHLC-derived rule. Candidates should come from event/fundamental/positioning/flow data with point-in-time availability and an implementable daily signal path.

Do not modify Fixed60 Production mechanics based on this work.