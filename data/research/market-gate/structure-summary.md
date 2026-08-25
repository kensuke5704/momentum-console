# Market Gate Structure Research — 2026-08-25

Production strategy: `momentum-dynamic-2026-08-v1`

## Design

Four pre-fixed variants:

1. `production` — current 10M monthly QQQ gate + current 10-day recovery
2. `no_gate` — monthly market gate disabled
3. `confirm_2m` — gate state flips only after two consecutive monthly closes on the opposite side of the 10M MA
4. `recovery_5d` — current gate with 5 recovery closes instead of 10

Evaluation layers:

- 2020-01-02 to 2026-08-21: full Production state machine + chronological PIT Dynamic Universe
- Dot-com / GFC / COVID / 2022: QQQ-only gate overlay, because pre-2020 PIT N-PORT universes do not exist
- 1,000 common synthetic 5-year QQQ paths: 20-session moving blocks, 252-session warmup

## Full strategy, actual chronology

| Variant | CAGR | MaxDD | Final wealth | Cash rate |
| --- | ---: | ---: | ---: | ---: |
| Production | 55.36% | -21.93% | 18.59x | 49.34% |
| No gate | 64.47% | -21.93% | 27.13x | 43.11% |
| Confirm 2M | 61.53% | -21.93% | 24.07x | 51.20% |
| Recovery 5D | 49.03% | -21.93% | 14.11x | 45.20% |

## Crisis diagnostic — QQQ-only gate overlay

### Max drawdown

| Crisis | Production | No gate | Confirm 2M | Recovery 5D |
| --- | ---: | ---: | ---: | ---: |
| Dot-com | -36.46% | -82.96% | -36.46% | -40.92% |
| GFC | -19.98% | -53.40% | -22.12% | -26.16% |
| COVID | -28.56% | -28.56% | -28.56% | -28.56% |
| 2022 | -15.46% | -34.58% | -18.36% | -15.46% |

## Structural gate diagnostic — 1,000 common QQQ paths

| Variant | CAGR median | CAGR p05 | DD median | DD adverse p05 | P(loss) | P(DD <= -40%) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Production | 5.21% | -7.95% | -30.36% | -49.68% | 27.1% | 18.3% |
| No gate | 11.43% | -8.23% | -36.29% | -61.62% | 17.1% | 39.3% |
| Confirm 2M | 5.47% | -7.88% | -31.95% | -51.07% | 28.9% | 22.5% |
| Recovery 5D | 5.52% | -7.74% | -31.20% | -49.86% | 27.6% | 21.0% |

## Interpretation

- Removing the gate materially improves observed 2020-2026 CAGR, but this is purchased with much worse long-bear and structural tail risk.
- Two-month confirmation captures much of the observed-period return improvement, but its structural improvement is minimal and its drawdown/loss probabilities are worse than Production.
- Five-day recovery is rejected: it worsens the actual full-strategy CAGR and does not improve structural drawdown enough to compensate.
- COVID is too fast for a monthly 10M gate; all gate variants experience essentially the same QQQ crash-phase drawdown. Individual stop / portfolio circuit remain the relevant fast-crash defenses.

## Research verdict

Do not change Production Market Gate from this test.

`confirm_2m` is the only variant worth retaining as a research candidate, not a Production candidate. It should require evidence from future Forward/OOS or a stronger multi-regime full-strategy test before reconsideration.

Do not adopt `no_gate` or `recovery_5d`.
