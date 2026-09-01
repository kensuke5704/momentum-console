# CAGR40 Cash-Funded Crisis Hedge — preregistration

Objective: keep a high Fixed60 allocation and replace reactive de-risking with a small sleeve that can earn positive returns during equity stress. No borrowing or shorting by the account; all positions are long ETFs purchased with cash.

Core allocation for all candidates:
- Fixed60 75%
- frozen G 10%
- tactical hedge/return sleeve 15%

When the tactical sleeve is in Cash, total invested capital is 85%. When active, total invested capital is 100%.

Signals use QQQ close and execute at the next US-session open. Baseline cost 10bp/side.

## Z1 — VIXY crisis-only sleeve
- Hold VIXY when QQQ close < 100DMA AND QQQ trailing-20-session return < 0.
- Otherwise Cash.

## Z2 — BTAL crisis-only sleeve
- Same risk-off condition as Z1.
- Hold BTAL during risk-off, otherwise Cash.

## Z3 — barbell TQQQ/VIXY sleeve
- Risk-on: QQQ close > 200DMA AND trailing-20-session return > 0 -> TQQQ.
- Risk-off: QQQ close < 100DMA AND trailing-20-session return < 0 -> VIXY.
- Otherwise Cash.

No thresholds will be changed after results.

## Robustness
- 30bp/side cost,
- +1 session execution delay,
- +2 session execution delay,
- start 2021,
- rolling 36M distribution.

Forward-planning CAGR proxy = min(stress CAGR median, rolling 36M CAGR median).
Pass = planning proxy >=40% AND historical MaxDD <=17%.