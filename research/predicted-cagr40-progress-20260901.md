# Forward Planning CAGR 40% Progress — 2026-09-01

Production Fixed60 remains unchanged. No margin/credit leverage is assumed. Leveraged ETFs such as TQQQ are permitted only when purchased with cash.

## Objective
- Approximate MaxDD target: ~15%, research tolerance to -17% historical MaxDD.
- Forward planning CAGR target: 40%.
- Planning proxy is not base backtest CAGR. It is defined as `min(stress median CAGR, rolling 36M median CAGR)` under the preregistered stress set.

## TQQQ fixed-allocation screen
Preregistered cash-funded portfolios T1/T2/T3 used 20%-30% TQQQ trend sleeves alongside Fixed60/G/DBMF and the same 18% portfolio-vol governor.

Results:
- T1 40/20/20/20: base CAGR 30.66%, MaxDD -20.86%, planning proxy 24.51%.
- T2 35/20/20/25: base CAGR 28.95%, MaxDD -21.72%, planning proxy 22.57%.
- T3 30/20/20/30: base CAGR 27.12%, MaxDD -22.21%, planning proxy 20.84%.

Conclusion: replacing high-efficiency Fixed60 capital with a simple QQQ>200DMA TQQQ sleeve reduced the planning return frontier and breached the DD target.

## Fixed60-only volatility governor
Preregistered 20-session, 18%-target governor on Fixed60 produced:
- base CAGR 26.90%, MaxDD -18.49%,
- planning proxy 25.31%.

Conclusion: direct volatility scaling of Fixed60 sacrifices too much return for the target.

## Residual-cash TQQQ implementation
Base portfolio: 50% Fixed60 / 20% frozen G / 30% DBMF, with the existing GOV3 60-session 18% vol governor. TQQQ was funded only from cash left unused by the governor, so total cash allocation never exceeded 100% and no borrowing was used.

Preregistered residual-cash fractions:
- RC25: base CAGR 34.30%, MaxDD -16.20%, planning proxy 29.05%.
- RC50: base CAGR 35.24%, MaxDD -20.91%, planning proxy 30.21%.
- RC100: base CAGR 36.58%, MaxDD -29.79%, planning proxy 32.75%.

Conclusion: residual-cash TQQQ can raise historical CAGR, but the added return is too correlated / volatile to preserve the ~15% DD objective. Increasing TQQQ exposure worsens DD faster than it improves the forward-planning proxy.

## Current boundary
Under the strategies tested so far, the best cash-funded ~15%-DD architecture remains below a 40% forward-planning CAGR. The earlier abstract return-stack achieved backtest figures above the target only by multiplying portfolio returns; that is not considered implementable because margin borrowing is prohibited.

The next research direction should not be more TQQQ weight tuning. To plausibly reach 40% planning CAGR at ~15% DD, a new return source is needed with both:
- materially higher robust standalone return than G/U/DBMF, and
- materially lower correlation to Fixed60 than a TQQQ trend sleeve.

Do not optimize RC25/RC50 intermediate fractions or TQQQ SMA thresholds on the same sample.
