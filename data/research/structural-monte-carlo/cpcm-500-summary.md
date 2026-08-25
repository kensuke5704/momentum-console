# Chronology-Preserving Conditional Monte Carlo — 500 paths

Generated from GitHub Actions run 32808176907 on 2026-08-25.

Method: actual target-date PIT universe with chronology fixed; 20-trading-day donor blocks sampled within +/-126 trading days, conditioned on QQQ 60-day trend sign/proximity and 20-day volatility proximity; signal at close and execution next session open.

| Metric | Result |
|---|---:|
| CAGR p05 | -4.43% |
| CAGR median | 26.37% |
| CAGR p95 | 72.66% |
| P(CAGR >= 50%) | 19.6% |
| P(CAGR < 0) | 8.2% |
| MaxDD median | -40.81% |
| MaxDD adverse p05 | -62.59% |
| P(MaxDD <= -30%) | 91.8% |
| P(MaxDD <= -40%) | 52.4% |
| Wealth p05 | 0.797x |
| Wealth median | 3.222x |
| Wealth p95 | 15.346x |
| Stop count median (5y) | 4 |
| Circuit count median (5y) | 7 |
| Cash rate median | 58.13% |
| Fallback rate | 0.0598% |

This is a robustness/counterfactual distribution, not a forecast of expected CAGR.
