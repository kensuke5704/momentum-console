# CAGR40 Tail-Circuit Portfolio Screen — preregistration

Purpose: preserve the high-return Fixed60 engine during normal periods and cut only portfolio tail risk. No parameter tuning after results.

Underlying cash-funded portfolio is fixed at:
- Fixed60 60%
- frozen G 15%
- DBMF 25%

No margin. No portfolio return multiplier. Total capital <=100%.

## Y1 — single shadow-DD circuit
- Compute drawdown on the ungoverned 60/15/25 shadow portfolio.
- If prior-close shadow DD <= -8%, next session exposure becomes 25%.
- Stay at 25% until prior-close shadow DD > -3% AND shadow 10-session return > 0; then return to 100%.

## Y2 — two-stage shadow-DD circuit
- Prior-close shadow DD > -5%: 100% exposure.
- DD <= -5%: 60% exposure.
- DD <= -10%: 25% exposure.
- Exposure can increase only when the prior-close shadow portfolio moves back above the corresponding threshold.

## Y3 — QQQ-confirmed tail circuit
- Normally 100% exposure.
- If prior-close shadow portfolio DD <= -8% AND QQQ close < QQQ 100DMA, next-session exposure becomes 25%.
- Return to 100% when either shadow DD > -3% OR QQQ close > QQQ 100DMA.

## Robustness
For each candidate:
- baseline,
- circuit signal delayed +1 session,
- delayed +2 sessions,
- start 2021,
- rolling 36M distribution.

Forward-planning proxy = min(stress CAGR median, rolling 36M CAGR median).
Ultimate pass requires planning proxy >=40% and historical MaxDD <=17%.