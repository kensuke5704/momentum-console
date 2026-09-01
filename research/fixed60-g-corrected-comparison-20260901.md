# Corrected Fixed60 × Candidate G comparison — 2026-09-01

This document supersedes the Fixed60-relative metrics and capital-sleeve table previously recorded in `research-independent-alpha-findings-20260901.md`.

## Reason for correction
The earlier Stage 5 comparison incorrectly read `public/data/backtest-frozen.json`, whose strategyId was the legacy `momentum-dynamic-2026-08-v1`. It was therefore not the Production Fixed60 equity series.

The corrected comparison generates Fixed60 directly with:
- `runStrategySimulation(...)`
- `config: PRODUCTION_STRATEGY`
- Production strategyId: `momentum-fixed60-2026-08-v1`

## Correct Production Fixed60 historical control
- Gross CAGR: **61.9981%**
- MaxDD: **-31.1272%**
- Annualized volatility: **34.5776%**
- Calmar: **1.9918**
- Final equity: **24.6686x**

This reproduces the approximately 60–62% gross CAGR shown by the current app / Production backtest.

## Candidate G unchanged
Candidate G standalone metrics are unaffected by the earlier reference error:
- CAGR: **23.3949%**
- MaxDD: **-27.5584%**
- Annualized volatility: **21.9670%**
- Calmar: **0.8489**
- Final equity: **4.0425x**

## Corrected independence metrics
Using the actual Fixed60 return series:
- Monthly return correlation: **0.3249**
- Fixed60 negative months: **17**
- G positive in those months: **8**
- Positive share in Fixed60 negative months: **47.06%**

The diversification conclusion remains materially intact. The previously quoted ~0.34 correlation / 50% positive-share figures should be replaced by the values above.

## Corrected fixed-weight daily capital sleeves
These figures are historical diagnostics only and must not be used to optimize a live sleeve weight on the same sample.

| Fixed60 | G | CAGR | MaxDD | Volatility | Calmar |
|---:|---:|---:|---:|---:|---:|
| 100% | 0% | **61.998%** | **-31.127%** | 34.578% | 1.992 |
| 90% | 10% | 58.412% | -28.828% | 32.028% | 2.026 |
| 80% | 20% | 54.739% | -26.471% | 29.628% | 2.068 |
| 70% | 30% | 50.990% | -24.055% | 27.419% | **2.120** |
| 60% | 40% | 47.173% | -23.109% | 25.449% | 2.041 |
| 50% | 50% | 43.299% | -22.218% | 23.778% | 1.949 |

## Interpretation
The corrected result strengthens, rather than weakens, the evidence that G is a diversifying return stream. G lowers historical CAGR because its standalone return is materially below Fixed60, but it reduces MaxDD and volatility enough to improve historical Calmar over a broad range of fixed sleeve weights.

No particular sleeve weight is selected from this table. Choosing the historically best 30% weight would be an additional in-sample optimization step and is therefore prohibited for the frozen Candidate G research protocol.

## Status
- Production Fixed60: unchanged.
- Candidate G `independent-top5-breakout-v1`: still **FROZEN PROMISING / FORWARD-OOS REQUIRED**.
- Candidate G standalone stress / LOO / rolling-window results: unchanged.
- Prior Fixed60-relative values from the legacy frozen backtest: withdrawn.
