# Universe × Ranking Ablation — 2026-08-25

Run: `32844244531` (success)

Design: 2×2 factorial with all other Production rules unchanged.

- Universe: actual PIT Dynamic N-PORT breadth Universe vs the first PIT Universe (2020-01-31) frozen forward.
- Ranking: Production 0/20/80 Momentum ranking vs N-PORT `universeRank` breadth ranking.
- Breadth-ranking variants retain the same Momentum eligibility filters (surge exclusion and score > QQQ), changing only the ordering used to choose Top2.
- CPCM: 1,000 common 5-year paths, seed 20260825.

## Integrity checks

- Realized baseline reproduced official Production exactly: CAGR 55.3601%, MaxDD -21.9290%.
- CPCM baseline reproduced the audited 1,000-path result exactly: median CAGR 26.0447%, median MaxDD -41.3284%.
- Frozen Universe uses the first PIT snapshot from 2020-01-31 and is carried forward only; no future Universe is injected backward.

## Results

| Variant | Realized CAGR | Realized MaxDD | CPCM median CAGR | CPCM p05 CAGR | CPCM median DD | P(loss) | P(CAGR>=50%) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Dynamic + Momentum | 55.36% | -21.93% | 26.04% | -4.26% | -41.33% | 7.9% | 18.7% |
| Frozen-2020 + Momentum | 10.50% | -19.17% | 4.83% | -6.83% | -27.64% | 25.3% | 0.0% |
| Dynamic + Breadth | 15.85% | -21.22% | 14.63% | -3.40% | -33.89% | 11.1% | 2.0% |
| Frozen-2020 + Breadth | 12.92% | -15.49% | 4.97% | -5.96% | -26.37% | 23.9% | 0.0% |

## Factor effects

On the CPCM median:
- Dynamic Universe contribution under Momentum ranking: +21.21 percentage points.
- Momentum ranking contribution under Dynamic Universe: +11.42 percentage points.
- Large positive interaction: +11.56 percentage points.

On the realized path:
- Dynamic Universe contribution under Momentum ranking: +44.86 percentage points.
- Momentum ranking contribution under Dynamic Universe: +39.51 percentage points.
- Large positive interaction: +41.93 percentage points.

## Interpretation

The strategy's edge is not explained by either component alone. Dynamic Universe evolution and Momentum ranking are complementary. Momentum ranking is much more valuable when applied to the evolving PIT thematic Universe, and Dynamic Universe evolution is much more valuable when paired with Momentum ranking.

Do not interpret the factorial differences as additive independent alpha estimates; the interaction is large. This experiment supports keeping both the Dynamic Universe and the Momentum ranking as core Production components.
