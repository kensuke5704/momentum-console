# Momentum Quality Diagnostics — 2026-08-25

Production strategy was not modified.

## Design
- Strategy: `momentum-dynamic-2026-08-v1`
- Scope: actual chronological PIT Top-5 eligible candidates
- 78 signal months / 388 candidate-month observations
- Forward return: next-session open after signal month-end to next-session open after following month-end
- Features fixed ex ante:
  - 63d positive-day ratio (`consistency63`)
  - 126d trailing MaxDD (`smoothness126`, higher = less negative)
  - distance from 126d high (`highProximity126`, higher = closer to high)
  - 63d acceleration (`acceleration63` = recent 63d return - prior 63d return)
- Primary diagnostic: monthly cross-sectional Spearman IC within Top-5
- Bootstrap: 5,000 month resamples, seed 20260825

## Overall
| Signal | Mean IC | 95% bootstrap CI | Positive IC months | Mean Top-Bottom next-month return |
|---|---:|---:|---:|---:|
| Existing momentum rank | **0.1474** | **[0.0359, 0.2564]** | 57.7% | **+6.89%** |
| Consistency 63d | 0.0126 | [-0.1099, 0.1423] | 48.7% | -0.97% |
| Smoothness 126d | -0.0962 | [-0.2192, 0.0308] | 38.5% | -5.66% |
| High proximity 126d | -0.0682 | [-0.1723, 0.0364] | 46.2% | -5.05% |
| Acceleration 63d | 0.0538 | [-0.0756, 0.1782] | 51.3% | -1.00% |

## Mean IC by period
| Signal | 2020-22 | 2023-24 | 2025-26 |
|---|---:|---:|---:|
| Consistency 63d | +0.1034 | +0.0119 | -0.1680 |
| Smoothness 126d | +0.0361 | -0.1792 | -0.2500 |
| High proximity 126d | -0.0984 | +0.0087 | -0.1103 |
| Acceleration 63d | +0.0194 | +0.2083 | -0.0833 |

## Conclusion
None of the four quality features shows stable, standalone forward predictive power within the current Top-5 candidate set. Existing momentum rank remains the only tested signal with a positive overall mean IC whose 95% bootstrap interval excludes zero. The quality features also show substantial sign instability across subperiods. Do not add them to Production or tune thresholds from this result.
