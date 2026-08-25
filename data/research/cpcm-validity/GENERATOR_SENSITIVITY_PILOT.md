# CPCM Generator Sensitivity — Pilot

Date: 2026-08-25
Run: 32854888340
Paths: 60 per generator
Seed: 20260825
Design: full Production state machine; same synthetic path used for Production and Recovery5 within each paired comparison.

## Production absolute results

| Generator | Median CAGR | Median MaxDD |
|---|---:|---:|
| BLOCK10 / R126 / actual-target | 34.93% | -41.54% |
| BLOCK20 / R126 / actual-target | 23.83% | -42.84% |
| BLOCK40 / R126 / actual-target | 22.29% | -40.82% |
| BLOCK20 / R63 / actual-target | 27.84% | -37.00% |
| BLOCK20 / R252 / actual-target | 13.92% | -43.30% |
| BLOCK20 / R126 / synthetic-state | 37.50% | -40.69% |
| BLOCK20 / R126 / unconditional-local | 36.72% | -38.03% |

Absolute CPCM median CAGR is materially generator-dependent in this pilot. The audited 26.0447% baseline should therefore be treated as a baseline-generator-specific local-counterfactual statistic, not a generator-robust expected CAGR estimate.

## Recovery5 paired comparison

| Generator | Median Recovery5 - Production CAGR | Recovery5 win rate |
|---|---:|---:|
| BLOCK10 / R126 | +5.99pt | 76.7% |
| BLOCK20 / R126 | +3.01pt | 63.3% |
| BLOCK40 / R126 | +4.99pt | 63.3% |
| BLOCK20 / R63 | +3.23pt | 61.7% |
| BLOCK20 / R252 | +3.57pt | 61.7% |
| Synthetic-state | +6.58pt | 71.7% |
| Unconditional-local | +7.44pt | 81.7% |

The paired CPCM direction is consistent across all tested generator variants: Recovery5 usually improves CAGR on the synthetic paths, while generally worsening median drawdown.

Historical realized path remains directionally opposite: Production 55.36% vs Recovery5 49.03% (about -6.33pt). Therefore generator sensitivity does not resolve the CPCM-vs-historical disagreement.

## Interim verdict

1. CPCM is useful as a local counterfactual / paired robustness engine.
2. The absolute median CAGR is not generator-robust enough to call an expected-return estimate.
3. A candidate should not be promoted solely because it wins CPCM paired comparisons when realized chronology and crisis/OOS evidence disagree.
4. Recovery5 remains rejected for Production despite CPCM robustness because historical evidence is directionally opposite.
5. The next validity question is why CPCM systematically favors faster recovery: likely candidates include block-boundary trend fragmentation, recovery-state duration distribution, and winner-capture timing.

Status: PILOT; 60 paths per generator. Do not treat percentile estimates as final precision estimates.
