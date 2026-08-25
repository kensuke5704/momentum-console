# Risk Parameter Neighborhood Audit — 2026-08-26

Run: `32909830473` (success)
Strategy: `momentum-dynamic-2026-08-v1`
Design: pre-specified one-factor-at-a-time coarse neighborhood audit. No grid search and no selection of a new Production value from the best historical CAGR.

Current Production backtest in this run: CAGR **55.25%**, MaxDD **-21.93%**, Calmar **2.52**, annualized vol **35.79%**.

## Individual Stop

| Stop | CAGR | MaxDD | Calmar | Vol | Stop exits | Circuit exits | Exposure |
|---|---:|---:|---:|---:|---:|---:|---:|
| 15.0% | **56.55%** | **-20.46%** | **2.76** | 35.47% | 8 | 7 | 50.18% |
| **17.5% Production** | **55.25%** | **-21.93%** | **2.52** | 35.79% | 6 | 9 | 50.60% |
| 20.0% | **53.04%** | **-26.90%** | **1.97** | 36.74% | 5 | 9 | 53.23% |

Interpretation:
- Production 17.5% is **not an isolated historical optimum**.
- Results change smoothly as the stop is loosened.
- The historical sample actually favors the tighter 15% stop on CAGR, DD and Calmar.
- Therefore the defensible conclusion is not that 17.5% is optimal. It is that approximately **15-17.5% is a historically stable/tolerable stop region**, while 20% is materially weaker in this sample.
- Because 15% was not pre-specified as a Production candidate before this audit and the goal is overfit diagnosis rather than re-optimization, this result is **not a reason to change Production to 15%**.

Status: **17.5% has neighborhood support as a non-fragile value, but no unique optimality evidence.**

## Portfolio Circuit

| Circuit | CAGR | MaxDD | Calmar | Vol | Circuit exits | Exposure |
|---|---:|---:|---:|---:|---:|---:|
| 12.5% | **52.74%** | **-19.17%** | **2.75** | 34.30% | 11 | 48.56% |
| **15.0% Production** | **55.25%** | **-21.93%** | **2.52** | 35.79% | 9 | 50.60% |
| 17.5% | **58.44%** | **-22.50%** | **2.60** | 36.88% | 7 | 52.40% |

Interpretation:
- Production 15% is **not an isolated peak**.
- There is a clean monotonic risk/return trade-off: tighter circuit reduces DD/vol/exposure and CAGR; looser circuit increases CAGR/exposure and risk.
- 15% sits directly between the two coarse alternatives and is therefore naturally interpretable as a **middle risk-budget choice**, not a return-maximizing fitted value.
- 12.5% has the best historical Calmar; 17.5% has the best CAGR. This is useful evidence against the claim that 15% was selected because it happened to maximize a single backtest metric.

Status: **15% has strong neighborhood justification as a middle risk/return compromise; no evidence of a narrow fitted optimum.**

## Recovery confirmation

| Recovery | CAGR | MaxDD | Calmar | Vol | Recovery entries | Stop exits | Circuit exits | Exposure |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 days | **48.63%** | **-21.93%** | **2.22** | 37.65% | 20 | 8 | 12 | 54.85% |
| **10 days Production** | **55.25%** | **-21.93%** | **2.52** | 35.79% | 14 | 6 | 9 | 50.60% |
| 15 days | **42.73%** | **-24.10%** | **1.77** | 35.15% | 14 | 6 | 9 | 46.53% |

Interpretation:
- Recovery10 is the best of the three coarse historical points on CAGR and Calmar.
- Recovery5 raises exposure and produces more re-entry / risk-trigger activity, consistent with premature re-entry.
- Recovery15 lowers exposure materially and loses return, consistent with excessive delay.
- This gives Recovery10 a plausible mechanism: a middle confirmation horizon between false re-entry risk and opportunity-cost risk.
- However, unlike Stop and Circuit, this neighborhood is **hump-shaped with Production at the top**. Historical Stop/Circuit event counts are small, so this can still be sample-specific.
- Prior trigger-event research found Historical early post-Stop/Circuit weakness but also showed CPCM cannot validly adjudicate Recovery timing. Therefore CPCM must not be used to certify Recovery10.

Status: **Recovery10 has meaningful historical/mechanistic support, but exact-10-day overfitting risk remains higher than for Stop17.5 or Circuit15. Forward OOS/event accumulation is the decisive validation.**

## Overall conclusion

- **Stop17.5:** supported as a non-fragile member of a roughly 15-17.5% region; not uniquely optimal.
- **Circuit15:** strongest parameter-level justification; clearly a middle risk/return compromise rather than a fitted peak.
- **Recovery10:** strongest historical performance among the three coarse points and mechanistically plausible, but also the parameter with the greatest remaining exact-value overfit concern because the response is peaked at 10 days.

No Production configuration was changed.
