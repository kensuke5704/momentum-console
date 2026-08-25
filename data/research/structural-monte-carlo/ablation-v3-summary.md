# Structural Monte Carlo Ablation V3

Corrected execution: signal close -> next session open. 5-year horizon, 100 common synthetic paths.

| Stage | CAGR p5 | CAGR median | CAGR p95 | P(CAGR>=50%) | P(CAGR<0) | MaxDD median | adverse DD p5 | P(MaxDD<=-40%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A Fixed Top2 | -3.65% | 24.71% | 93.17% | 19% | 17% | -50.02% | -81.64% | 71% |
| B Dynamic Top2 | -17.07% | 21.24% | 78.99% | 20% | 21% | -58.45% | -81.91% | 94% |
| C + Market Gate | -20.31% | 17.59% | 66.15% | 15% | 23% | -55.45% | -79.03% | 96% |
| D + Individual Stop | -18.14% | 9.54% | 55.67% | 8% | 31% | -54.63% | -75.24% | 92% |
| E + Portfolio Circuit | -16.75% | 10.07% | 52.33% | 6% | 27% | -54.67% | -75.09% | 93% |
| F Full Production Recovery | -12.42% | 7.71% | 38.88% | 1% | 30% | -46.16% | -68.72% | 75% |

Notes:
- All six stages use the same 100 synthetic stock/QQQ paths.
- A-E use a simplified ablation engine with close confirmation and next-session-open execution, including 10 bp/side cost.
- F uses the actual Production `transitionDay` state machine, including persistent 10-day recovery logic.
- A is a rough fixed-selection diagnostic and should not be interpreted as a standalone investable strategy because fixed-name availability can vary across resampled history.
- Absolute results remain a structural robustness stress test rather than a forecast of expected CAGR.
