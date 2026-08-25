# Production Monte Carlo — 5y / 50,000 paths

Strategy: **momentum-dynamic-2026-08-v1**  
Source curve: **2020-01-02 → 2026-08-21** (1668 daily points)  
Reported CAGR: **55.36%** / recomputed from curve: **55.36%**  
Reported MaxDD: **-21.93%**

Method: 20-trading-day moving-block bootstrap, 5 years (1,260 sessions), 50,000 paths, seed 20260825.

| Scenario | CAGR p5 | CAGR median | CAGR p95 | P(CAGR≥50%) | P(CAGR≥80%) | MaxDD median | adverse DD p5 | P(DD≤-30%) | P(DD≤-40%) | Final wealth median |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 20-day moving-block bootstrap | 17.20% | 55.73% | 110.53% | 58.16% | 21.05% | -35.85% | -54.80% | 75.93% | 33.46% | 9.16x |
| Base + one forced -30% Top1 single-name gap per 5 years (70% sleeve => -21% portfolio shock) | 11.70% | 48.61% | 101.05% | 48.08% | 14.74% | -40.02% | -59.83% | 88.88% | 50.10% | 7.25x |
| Base + one forced -50% Top1 single-name gap per 5 years (70% sleeve => -35% portfolio shock) | 7.45% | 42.97% | 93.04% | 39.28% | 10.23% | -47.71% | -65.86% | 99.98% | 82.76% | 5.97x |

Additional base probabilities:
- P(CAGR < 0): 0.46%
- P(MaxDD <= -50%): 9.90%
- P(final wealth < 1.0x after 5 years): 0.46%

Forced -30% single-name gap scenario:
- P(CAGR < 0): 1.06%
- P(MaxDD <= -50%): 18.90%
- P(final wealth < 1.0x): 1.06%

Forced -50% single-name gap scenario:
- P(CAGR < 0): 1.94%
- P(MaxDD <= -50%): 40.73%
- P(final wealth < 1.0x): 1.94%

## Interpretation guardrails

- Base bootstrap preserves roughly one month of serial dependence but does not create new market regimes absent from 2020-present data.
- Forced gap scenarios are deliberately conservative severity overlays: every simulated 5-year path receives exactly one such shock. They are not estimates of event frequency.
- The simulation resamples realized Production strategy returns; it does not rerun synthetic stock prices through the state machine, so it is a distributional robustness test rather than a structural market model.
