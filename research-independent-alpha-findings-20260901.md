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

## Candidate D — TQQQ 200DMA Trend (rejected)
- CAGR: 40.44%
- +1-session delay CAGR: 42.76%
- MaxDD: -57.82%

Reason: drawdown is too large despite timing robustness.

## Candidate E — Breadth Trend TQQQ (secondary candidate)
- CAGR: 23.47%
- MaxDD: -38.98%
- Correlation: 0.44
- +1-session delay CAGR: 23.18%
- +1-session delay MaxDD: -38.32%

Reason for secondary status: structurally stable, but positive in only 16.7% of Fixed60 negative months (27.8% with +1 delay), below the predeclared 30% diversification screen.

## Candidate F — QQQ Dip / TQQQ (rejected)
- CAGR: 7.93%
- MaxDD: -62.66%

## Candidate G — Top5 Breakout Basket (FROZEN PROMISING CANDIDATE)

### Frozen identity
- strategyId: `independent-top5-breakout-v1`
- freeze date: 2026-09-01
- historical data end: 2026-08-25
- all observations after 2026-08-25 are reserved for forward OOS and must not be used to tune this strategyId

### Frozen specification
- Point-in-time SEC N-PORT Dynamic Universe
- QQQ close > 200-session SMA
- Stock close > 100-session SMA
- Stock close > maximum close of prior 20 sessions
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

### Time-series stability after freeze
Year returns from the frozen historical simulation:
- 2020: +0.81%
- 2021: +11.52%
- 2022: -21.98%
- 2023: +48.82%
- 2024: +10.29%
- 2025: +43.07%
- 2026 through 2026-08-25: +103.35%

Rolling 12M annualized returns:
- median: +11.56%
- p10: -15.05%
- worst: -22.74%
- positive windows: 72.0%

Rolling 36M annualized returns:
- median: +13.00%
- p10: +1.76%
- worst: -5.52%
- positive windows: 95.7%

Interpretation: the engine is not uniformly defensive; 2022 and some rolling 12M windows are materially negative. The stronger evidence is that multi-year return persistence remains positive in almost all rolling 36M windows.

### Fixed60 capital-sleeve combinations
These are fixed-weight daily blends; Fixed60 itself is not modified.

| Fixed60 | G | CAGR | MaxDD | Volatility | Calmar |
|---:|---:|---:|---:|---:|---:|
| 100% | 0% | 55.36% | -31.53% | 35.82% | 1.756 |
| 90% | 10% | 52.63% | -29.19% | 33.13% | 1.803 |
| 80% | 20% | 49.77% | -27.07% | 30.58% | 1.839 |
| 70% | 30% | 46.80% | -25.27% | 28.22% | 1.852 |
| 60% | 40% | 43.72% | -24.47% | 26.11% | 1.787 |
| 50% | 50% | 40.55% | -23.69% | 24.29% | 1.712 |

Historical interpretation: G lowers return because its standalone CAGR is below Fixed60, but it also lowers drawdown and volatility. The 20–30% sleeve region produces the strongest historical Calmar improvement, but this is **not an optimization result to adopt**; selecting 20% or 30% from this same sample would create a new layer of in-sample selection. Any live capital weight must be governed separately and not retroactively optimized from this table.

### PIT / execution parity audit
The research engine uses `data/universe-history.json`, selecting the latest universe whose `asOf <= signal date`. The universe builder constructs completed monthly snapshots and `latestPublicFilings()` explicitly excludes any filing with `filingDate > asOf`. This is consistent with point-in-time intent.

Signal/execution ordering in the frozen research engine:
- breakout high excludes the current close
- 100/200-session SMA includes current close, so the signal is only known after that close
- entry is the next available US trading-session open
- stop/circuit/hold conditions are evaluated at close and executed next open
- transaction cost is 10bp per side

Known remaining data/model limitations:
- corporate-action / adjusted-price integrity inherits the repository market-data pipeline
- PIT integrity ultimately depends on the completeness and correctness of imported SEC N-PORT history
- stop/circuit execution is close-triggered; no intraday stop fill is modeled

### Current judgment
Candidate G remains the first candidate in this search that is economically meaningful and robust across execution delay, higher costs, start-date change, nearby structural choices, symbol removal, and multi-year rolling windows. It is now frozen as **PROMISING / FORWARD-OOS REQUIRED**, not production-approved.

It still shares the PIT Dynamic Universe and a QQQ trend gate with Fixed60, so it is not statistically independent in a strict sense. Its alpha-generation mechanism is distinct: daily short-horizon breakout / Top5 basket versus Fixed60's month-end 0/20/80 relative momentum / Top2. Historical monthly return correlation remains approximately 0.34.

## Candidate H — Top5 Reversal Basket (rejected)
- CAGR: -1.18%
- MaxDD: -55.10%
- +1-session delay CAGR: 9.74%

## Research decision
1. Stop parameter exploration for Candidate G.
2. Preserve `independent-top5-breakout-v1` unchanged.
3. Do not merge G into Production/main from historical evidence alone.
4. Begin a separately identified forward-OOS ledger for observations after 2026-08-25.
5. Any signal-changing bug fix or rule change requires a new strategyId and restarts forward-OOS evaluation.
6. Keep Fixed60 forward/OOS evidence separate from G evidence.
