# Forward Planning CAGR 40% Objective — Preregistered 2026-09-01

Production Fixed60 remains unchanged.

## User constraints
- No margin / credit trading.
- Leveraged ETFs such as TQQQ are allowed when purchased with cash.
- Portfolio gross capital allocation must remain <=100% cash-funded.
- Risk objective: maintain approximately 15% MaxDD, with research tolerance to 17% historical MaxDD.
- Return objective: forward planning CAGR ~=40%, explicitly not merely backtest CAGR.

## Forward planning CAGR proxy
For each frozen candidate architecture, calculate:
1. full-sample base CAGR,
2. 30bp/side implementation-cost stress where applicable,
3. +1 US-session execution delay,
4. +2 US-session execution delay,
5. start-date stress beginning 2021-01-01,
6. one structural sleeve-removal stress for the highest-risk added sleeve,
7. rolling 36-month CAGR distribution.

Define `stressMedianCAGR` as the median CAGR across items 1-6.
Define `rolling36MedianCAGR` as median rolling 36-month CAGR.
Define `forwardPlanningCAGRProxy = min(stressMedianCAGR, rolling36MedianCAGR)`.

This is a planning proxy, not a statistical expected value or probability forecast. It is deliberately more conservative than selecting the full-sample backtest CAGR.

## Pass rule
A candidate is a research PASS only if:
- forwardPlanningCAGRProxy >= 40%, and
- full-sample historical MaxDD >= -17%, and
- no +1/+2 execution stress produces MaxDD worse than -20%, and
- no single added sleeve removal reduces full-sample CAGR by more than 50%.

## New return source
Because margin is prohibited but leveraged ETFs are permitted, the next engine family uses a cash-funded TQQQ tactical sleeve. It is not portfolio borrowing.

TQQQ trend sleeve specification:
- Signal asset: QQQ.
- QQQ close > 200-session SMA -> hold TQQQ.
- Else cash.
- Signal at close, trade next US-session open.
- 10bp per traded notional per side.
- No optimization of SMA length on this sample.

Candidate portfolio architectures will use round, preregistered weights only; no nearby weight search after results.
