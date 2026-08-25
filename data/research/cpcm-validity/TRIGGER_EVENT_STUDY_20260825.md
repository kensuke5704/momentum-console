# CPCM Trigger-Conditioned Event Study — 2026-08-25

Run: `32859509863` (success)

Design:
- 5-year evaluation window.
- Production state machine unchanged: individual stop -17.5%, portfolio circuit -15%, Recovery10.
- CPCM baseline generator: BLOCK20 / RADIUS126 / actual-target conditioning / seed 20260825.
- 200 CPCM paths.
- Identify endogenous Production Stop and Circuit trigger dates.
- Compare QQQ and the two-stock basket held at the trigger over event windows.
- Basket uses the trigger-time Top2 symbols and target weights, held hypothetically after trigger for attribution only.

## Event counts

Historical:
- Stop: 5 events.
- Circuit: 6 events.

CPCM path event-count medians:
- Stop: 4 events (p05 2, p95 8).
- Circuit: 7 events (p05 3, p95 ~10.05).

Event frequency is therefore not grossly inconsistent. Historical sample sizes are small, so event-window level estimates must be interpreted cautiously.

## Stop events

### QQQ

| Window | Historical mean | CPCM median path mean |
|---|---:|---:|
| -20d to trigger | +1.31% | -0.97% |
| -5d to trigger | -0.47% | -2.44% |
| +1 to +5d | +0.20% | +0.60% |
| +6 to +10d | +0.76% | +0.36% |
| +11 to +20d | +1.11% | +0.64% |
| +1 to +10d | +0.89% | +0.86% |
| +1 to +20d | +2.03% | +1.43% |

QQQ post-Stop behavior is broadly similar. CPCM does not show an extreme market-level rebound relative to Historical.

### Trigger-time Top2 basket

| Window | Historical mean | CPCM median path mean |
|---|---:|---:|
| +1 to +5d | **-2.16%** | **+2.81%** |
| +6 to +10d | +0.13% | +1.57% |
| +11 to +20d | **+5.56%** | +1.55% |
| +1 to +10d | **-2.77%** | **+4.07%** |
| +1 to +20d | +2.24% | +5.87% |

The main Stop discrepancy is cross-sectional / selected-basket timing: Historical losers continued to underperform through the first 10 days and rebounded mainly in days 11-20, while CPCM gives the triggered Top2 basket an early rebound.

## Circuit events

### QQQ

| Window | Historical mean | CPCM median path mean |
|---|---:|---:|
| -20d to trigger | -2.12% | -1.24% |
| -5d to trigger | -2.60% | -2.84% |
| +1 to +5d | -0.02% | +0.57% |
| +6 to +10d | -0.25% | +0.40% |
| +11 to +20d | +0.39% | +0.90% |
| +1 to +10d | -0.28% | +0.99% |
| +1 to +20d | +0.12% | +2.00% |

There is some market-level early-rebound difference after Circuit, but the magnitude remains much smaller than the selected-basket discrepancy.

### Trigger-time Top2 basket

| Window | Historical mean | CPCM median path mean |
|---|---:|---:|
| +1 to +5d | **-3.04%** | **+1.77%** |
| +6 to +10d | **-2.15%** | **+2.24%** |
| +11 to +20d | **+4.63%** | +3.05% |
| +1 to +10d | **-5.19%** | **+3.96%** |
| +1 to +20d | +0.06% | +7.62% |

Historical Circuit-triggered baskets typically experienced continued weakness during the first 10 days, followed by later rebound. CPCM moves much more of the rebound into the first 10 days.

## Interpretation

1. The Recovery5-vs-Recovery10 disagreement is not mainly explained by QQQ unconditional statistics or donor-block boundaries.
2. The strongest mismatch is the conditional cross-sectional path of stocks that *endogenously caused* Stop/Circuit events.
3. Historical trigger-time Top2 baskets show short-term continuation of weakness for roughly 5-10 trading days, then later rebound.
4. Baseline CPCM tends to give those trigger-time baskets positive returns immediately after the trigger.
5. This mechanically favors faster Recovery5 and explains why CPCM gives Recovery5 positive paired value while Historical does not.
6. Current CPCM conditioning uses QQQ trend/vol and a common donor block, but does not explicitly condition on the selected basket's own recent drawdown / trigger state. It therefore does not preserve the conditional continuation/reversal structure of endogenous losers.

## Validity consequence

Current CPCM should **not** be used as primary evidence for parameters whose value depends on post-trigger path shape, including Recovery confirmation length, individual Stop thresholds, and portfolio Circuit thresholds.

It remains usable for broader paired tests where the intervention does not materially alter exposure specifically around endogenous Stop/Circuit states, but such use should be screened for trigger interaction.

## Next audit / model candidate

Test one coarse event-aware CPCM variant without tuning:
- preserve chronology and baseline QQQ trend/vol conditioning;
- when target state is within a Stop/Circuit event window, add a coarse selected-basket state condition (e.g. recent 5-20d relative return / drawdown sign or trigger-like donor eligibility);
- compare event-window posterior predictive fit first;
- only if event-window fit improves without breaking unconditional market statistics should strategy comparisons be repeated.

Do not optimize thresholds. Pre-specify only a small number of coarse event-state definitions.

Status: **VALID DIAGNOSTIC RESULT; CPCM TRIGGER-CONDITIONAL MODEL RISK CONFIRMED.**