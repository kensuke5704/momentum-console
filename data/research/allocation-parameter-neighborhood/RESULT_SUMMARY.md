# Allocation Parameter Neighborhood Audit — 2026-08-26

Run: `32910443656` (success)
Strategy: `momentum-dynamic-2026-08-v1`
Design: pre-specified one-factor-at-a-time coarse audit. No parameter is changed in Production from this result.

Current implementation computes `zGap = (Top1 score - Top2 score) / population SD of all eligible scores`; if `zGap >= 0.25`, Top1 receives 70% and Top2 30%, otherwise 50/50.

## zGap threshold neighborhood

| zGap threshold | CAGR | MaxDD | Calmar | Vol |
|---|---:|---:|---:|---:|
| 0.15 | **58.16%** | -21.93% | **2.65** | 35.86% |
| **0.25 Production** | 55.25% | -21.93% | 2.52 | 35.79% |
| 0.35 | 55.25% | -21.93% | 2.52 | 35.79% |

Production 0.25 is not a narrow historical optimum. 0.25 and 0.35 produce identical full-backtest metrics in this sample; 0.15 is somewhat higher-return historically. This by itself gives neighborhood non-fragility, but not a reason to prefer exactly 0.25.

## Concentrated Top1 weight neighborhood

| Concentrated Top1 weight | CAGR | MaxDD | Calmar | Vol |
|---|---:|---:|---:|---:|
| 60% | **60.07%** | **-19.80%** | **3.03** | 34.56% |
| **70% Production** | 55.25% | -21.93% | 2.52 | 35.79% |
| 80% | 56.14% | -21.37% | 2.63 | 36.40% |
| fixed 50/50 reference | 56.68% | -19.84% | 2.86 | **34.05%** |

Historical evidence does **not** identify 70/30 as superior. 60/40 and fixed 50/50 both have higher CAGR, lower drawdown, and higher Calmar than current 70/30 in this realized sample. Therefore 70/30 should not be justified as a historical optimum.

Prior CPCM allocation work also did not find a robust advantage for more concentration across seeds; equal allocation generally improved drawdown at a small return trade-off in that synthetic framework. Because allocation is not primarily a Stop/Circuit aftermath mechanism, CPCM remains useful as secondary paired evidence here, but it does not rescue a unique 70/30 rationale.

## Signal-level mechanism audit

62 RiskOn monthly Top2 signals with valid next-month open-to-open returns were available.

Association between current zGap and next-month `(Top1 return - Top2 return)`:
- Spearman: **-0.220**
- Pearson: **-0.134**

For Production threshold 0.25:
- `zGap >= 0.25`: 56/62 signals (**90.3%**) would be concentrated.
- Mean next-month Top1-Top2 spread: **+2.66%**.
- Top1 beat Top2 only **51.8%** of those months.
- `zGap < 0.25`: only 6 signals; mean spread **+14.42%**, Top1 win rate 100% (very small sample).

Threshold shares:
- 0.15 -> concentrated on 95.2% of valid signals.
- 0.25 -> 90.3%.
- 0.35 -> 87.1%.

Thus the present zGap scale is such that 0.25 is not a selective 'exceptional Top1 separation' threshold; it activates concentration in roughly nine out of ten valid RiskOn signals. The negative rank association also fails to support the intended monotonic mechanism that larger zGap should imply greater subsequent Top1 superiority.

The small low-zGap groups prevent a strong inverse conclusion, but the evidence is sufficient to say that the current zGap rule is **not empirically validated as a confidence signal**.

## Overall assessment

- **zGap concept:** economically interpretable as standardized Top1-vs-Top2 score separation, but the current empirical calibration does not show that larger zGap predicts stronger Top1 relative returns.
- **zGap 0.25:** non-fragile as a backtest threshold, but too permissive to act as a rare high-conviction regime; no unique parameter-level justification.
- **70/30:** no positive historical neighborhood justification; 60/40 and fixed 50/50 are historically better on CAGR/DD/Calmar in this sample.
- **Overfitting implication:** allocation rule is currently one of the weaker-justified Production components. Do not tune it to the best historical alternative after seeing these results.

Recommended research interpretation: retain Production unchanged for pure OOS integrity, but classify `zGap 0.25 -> 70/30` as **UNVALIDATED / FORWARD-OOS REQUIRED**, rather than claiming strong parameter-level support.
