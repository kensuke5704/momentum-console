# Availability-aware Structural Monte Carlo — 2026-08-25

Strategy: `momentum-dynamic-2026-08-v1`

Method: 500 paths, 5-year horizon, 20-session common market blocks, 252-session warmup, seed 20260825. No QQQ proxy imputation. Non-available symbols are excluded; new blocks must preserve price availability for currently held names.

| Metric | Result |
|---|---:|
| CAGR p5 | -13.88% |
| CAGR p25 | -3.46% |
| CAGR median | 6.78% |
| CAGR p75 | 17.72% |
| CAGR p95 | 48.43% |
| P(CAGR >= 50%) | 4.60% |
| P(CAGR >= 80%) | 0.20% |
| P(CAGR < 0) | 33.00% |
| MaxDD adverse p5 | -68.22% |
| MaxDD p25 | -56.70% |
| MaxDD median | -45.97% |
| MaxDD p75 | -37.89% |
| MaxDD p95 | -30.59% |
| P(MaxDD <= -30%) | 95.60% |
| P(MaxDD <= -40%) | 69.20% |
| P(MaxDD <= -50%) | 39.00% |
| 5-year loss probability | 33.00% |
| Final wealth p5 | 0.47x |
| Final wealth median | 1.39x |
| Final wealth p95 | 7.24x |
| Median invested-month share | 42.62% |
| Median exits | 36 |
| Median stop exits | 4 |
| Median circuit exits | 7 |
| Median rejected blocks | 0 |

Comparison with prior structural MC (which used QQQ proxy imputation for missing symbol returns): prior CAGR median 7.55%, MaxDD median -47.66%, P(CAGR>=50%) 2.80%, 5-year loss probability 33.40%, P(MaxDD<=-40%) 73.60%. Removing proxy imputation did not materially restore performance.

Interpretation: the large degradation versus the simple return-block bootstrap is not primarily explained by missing-price proxy imputation. It emerges when synthetic cross-sectional stock paths are re-ranked and the Production Top2/risk state machine is rerun. This remains a robustness diagnostic, not a calibrated forecast: historical PIT universes are remapped to sampled source dates rather than synthetically regenerated from ETF holdings.