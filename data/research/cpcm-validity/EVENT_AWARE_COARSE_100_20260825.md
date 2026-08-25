# CPCM Coarse Event-Aware Variants — 100 paths

Date: 2026-08-25
Run: `32860579628`
Paths: 100 per variant
Seed: 20260825

## Pre-specified variants

- baseline: current QQQ trend/vol CPCM.
- relative20: baseline donor distance plus distance in current selected Top2 20d return relative to QQQ.
- triggerLike: when synthetic portfolio DD <= -10% or any current position loss <= -12%, donor candidates must have the same Top2 basket 20d return <= -5%.

No threshold search or tuning was performed.

## Historical event targets

| Trigger | Basket +1..+5d | Basket +1..+10d | Basket +11..+20d |
|---|---:|---:|---:|
| Stop | -2.16% | -2.77% | +5.56% |
| Circuit | -3.04% | -5.19% | +4.63% |

## 100-path CPCM median event means

| Variant | Stop +1..+5d | Stop +1..+10d | Circuit +1..+5d | Circuit +1..+10d |
|---|---:|---:|---:|---:|
| baseline | +2.47% | +4.03% | +1.77% | +4.13% |
| relative20 | +2.60% | +3.49% | +1.29% | +2.35% |
| triggerLike | +1.88% | +4.26% | +2.11% | +4.51% |

relative20 improves Circuit early-path fit somewhat, but neither event-aware variant restores the negative first-10-day continuation seen in Historical. Stop remains opposite in sign for every variant.

## QQQ / market preservation

Historical QQQ:
- daily SD 1.445%
- 20d p05 -9.50%
- 20d median +1.56%
- 20d p95 +10.91%
- MaxDD -35.12%

Variant medians:

| Variant | daily SD | 20d p05 | 20d median | 20d p95 | MaxDD |
|---|---:|---:|---:|---:|---:|
| baseline | 1.414% | -8.44% | +1.56% | +10.26% | -28.94% |
| relative20 | 1.400% | -8.32% | +1.63% | +10.41% | -30.78% |
| triggerLike | 1.419% | -8.38% | +1.53% | +10.47% | -30.01% |

The added cross-sectional conditions do not grossly break QQQ return statistics, but they do not solve trigger-conditioned basket timing.

## Interpretation

The failure is structurally informative. Both variants choose donors only at ordinary 20-day block boundaries. A Stop/Circuit can occur in the middle of an already-selected block, so the immediate post-trigger +1..+5/+10 path is mostly predetermined before the trigger becomes known. This limits how much block-start state conditioning can repair endogenous post-trigger behavior.

## Next test

Test one adaptive event-aligned CPCM variant:
- use baseline CPCM normally;
- when Production Stop/Circuit occurs on a synthetic close, terminate the current donor block;
- at the next synthetic session, select a fresh donor whose *pre-block* QQQ trend/vol and same-Top2 recent weakness are close to the synthetic trigger state;
- then resume a contiguous block.

Evaluate event-window posterior predictive fit before any CAGR comparison.

Status: **COARSE EVENT-AWARE BLOCK-START CONDITIONING REJECTED AS INSUFFICIENT.**
