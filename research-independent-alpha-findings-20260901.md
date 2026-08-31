# Independent Alpha Engine Research — 2026-09-01

Production Fixed60 is unchanged. All work is isolated to `research/independent-alpha-engine-20260901`.

## Objective
Find a structurally distinct return engine rather than micro-tuning Fixed60 on the same 2020–2026 sample. A candidate is screened for standalone return, drawdown, low monthly correlation with Fixed60, behavior in Fixed60 negative months, execution robustness, neighborhood robustness, and symbol concentration.

## Candidate A — TCSR (rejected)
Trend-conditioned 5-day short-term reversal, Top2.

- CAGR: 4.50%
- MaxDD: -49.16%
- Monthly correlation with Fixed60: 0.35
- Positive in Fixed60 negative months: 38.9%
- Worst LOO: UNH removal produced negative CAGR

Reason for rejection: independent behavior existed, but return, drawdown, and LOO robustness failed.

## Candidate B — VCB (not selected)
Volatility-compression 20-day breakout, Top2.

- Baseline CAGR: 24.08%
- MaxDD: -33.20%
- Correlation: 0.33
- Positive in Fixed60 negative months: 50.0%
- Worst LOO retention: 55.6%

However:
- +1-session delay CAGR: 3.43%
- 10-day hold CAGR: 4.05%
- 30-day hold CAGR: 6.64%
- compression=0.60 CAGR: 4.32%
- stress median CAGR: 10.18%

Reason for not selecting: strong baseline but excessive timing / holding-period / threshold sensitivity.

## Candidate C — Crisis Rebound TQQQ (rejected)

- CAGR: -10.48%
- MaxDD: -52.07%

Reason: insufficient return and drawdown.

## Candidate D — TQQQ 200DMA Trend (rejected)

- CAGR: 40.44%
- +1-session delay CAGR: 42.76%
- MaxDD: -57.82%

Reason: drawdown is too large despite timing robustness.

## Candidate E — Breadth Trend TQQQ (secondary candidate)
PIT Dynamic-Universe breadth + QQQ trend.

- CAGR: 23.47%
- MaxDD: -38.98%
- Correlation: 0.44
- +1-session delay CAGR: 23.18%
- +1-session delay MaxDD: -38.32%

Reason for secondary status: structurally stable, but positive in only 16.7% of Fixed60 negative months (27.8% with +1 delay), below the predeclared 30% diversification screen.

## Candidate F — QQQ Dip / TQQQ (rejected)

- CAGR: 7.93%
- MaxDD: -62.66%

Reason: insufficient return and drawdown.

## Candidate G — Top5 Breakout Basket (PROMISING)

### Frozen baseline specification
- Point-in-time SEC N-PORT Dynamic Universe
- QQQ close > 200-day SMA
- Stock close > 100-day SMA
- Stock close > prior 20-session high
- Rank by breakout strength
- Select Top5, equal weight
- Signal at close; enter next US open
- Hold 20 closes, then exit next open
- Individual close stop: -12%
- Portfolio circuit: -15%
- Transaction cost: 10bp per side
- No intraday signal inputs

### Baseline
- CAGR: 23.39%
- MaxDD: -27.56%
- Annualized volatility: 21.97%
- Calmar: 0.85
- Final equity: 4.04x
- Trades: 73
- Monthly correlation with Fixed60: 0.342
- Positive in Fixed60 negative months: 50.0%

### Execution / stress robustness
- 30bp/side cost: CAGR 18.04%, MaxDD -33.94%
- +1-session execution delay: CAGR 21.66%, MaxDD -19.70%
- Start 2021: CAGR 30.37%, MaxDD -24.35%
- 15-day breakout: CAGR 30.02%, MaxDD -23.94%
- 30-day breakout: CAGR 15.50%, MaxDD -34.14%
- 10-day hold: CAGR 12.96%, MaxDD -26.66%
- 30-day hold: CAGR 22.75%, MaxDD -24.93%
- Top3: CAGR 20.03%, MaxDD -33.84%
- Top8: CAGR 16.10%, MaxDD -21.86%

Stress CAGR distribution across these nine variants:
- median: 20.03%
- p10: 14.99%
- worst: 12.96%

### Leave-one-symbol-out
- Worst: remove PANW -> CAGR 12.42%
- Worst CAGR retention vs baseline: 53.1%
- LOO p10: 22.82%
- LOO median: 23.39%

### Current judgment
Candidate G is the first candidate in this search that is both economically meaningful and reasonably robust to one-session execution delay, higher costs, start-date change, nearby structural choices, and symbol removal. It is therefore classified as **PROMISING**, not production-approved.

It still uses the same PIT Dynamic Universe and a QQQ trend gate as Fixed60, so it is not statistically independent in a strict sense. Its alpha-generation mechanism is distinct: daily short-horizon breakout / Top5 basket versus Fixed60's month-end 0/20/80 relative momentum / Top2. The observed monthly return correlation of ~0.34 supports material diversification in this historical sample.

## Candidate H — Top5 Reversal Basket (rejected)

- CAGR: -1.18%
- MaxDD: -55.10%
- +1-session delay CAGR: 9.74%

Reason: insufficient return and drawdown.

## Next evidence required before any production discussion
1. Freeze Candidate G as-is; do not optimize it further on 2020–2026.
2. Verify point-in-time and execution parity independently from Fixed60 code paths.
3. Examine rolling 12M / 36M behavior and year-by-year contribution.
4. Evaluate a capital-sleeve combination with Fixed60 without changing Fixed60 itself.
5. If pursued live, create a separate forward-OOS series and strategy ID. Do not contaminate Fixed60 OOS.
