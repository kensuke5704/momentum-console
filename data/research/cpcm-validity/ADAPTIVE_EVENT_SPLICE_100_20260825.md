# CPCM Adaptive Trigger-Aligned Event Splice — 100 paths

Date: 2026-08-25
Run: `32861587330`
Paths: 100
Seed: 20260825

## Method

Baseline CPCM is used normally. When the synthetic Production state machine generates an endogenous Stop or Circuit at a close:

1. terminate the current donor block immediately;
2. on the next synthetic session choose a new donor block;
3. donor *pre-block* state is matched to the synthetic trigger state using:
   - QQQ 60d trend,
   - QQQ 20d volatility,
   - same trigger-time Top2 basket 20d return;
4. resume a contiguous block from the selected donor start.

No parameter search was performed. Event donor fallback rate was 0% across 1,091 event splices.

## Historical targets

| Trigger | Basket +1..+5d | Basket +1..+10d | Basket +11..+20d |
|---|---:|---:|---:|
| Stop | -2.16% | -2.77% | +5.56% |
| Circuit | -3.04% | -5.19% | +4.63% |

## Adaptive CPCM 100-path median event means

| Trigger | Basket +1..+5d | Basket +1..+10d | Basket +11..+20d |
|---|---:|---:|---:|
| Stop | +1.28% | +4.69% | +3.36% |
| Circuit | +1.79% | +3.84% | +3.34% |

For comparison, baseline CPCM 100-path medians from the coarse event-aware audit were:
- Stop +1..+5d +2.47%, +1..+10d +4.03%.
- Circuit +1..+5d +1.77%, +1..+10d +4.13%.

Adaptive alignment modestly improves Stop +1..+5d and Circuit +1..+10d, but does not restore the negative first-10-day continuation observed historically. Stop +1..+10d is actually worse than baseline.

## QQQ / market fit

Historical QQQ:
- daily SD 1.445%
- 20d p05 -9.50%
- 20d median +1.56%
- 20d p95 +10.91%
- MaxDD -35.12%

Adaptive CPCM median:
- daily SD **1.381%**
- 20d p05 **-8.94%**
- 20d median **+1.66%**
- 20d p95 **+10.37%**
- MaxDD **-33.51%**

The adaptive splice improves broad drawdown fit relative to the 100-path baseline MaxDD median (-28.94%) without materially breaking 20d QQQ return statistics.

## Interpretation

1. Ordinary block-boundary conditioning was insufficient.
2. Trigger-aligned block restarts also remain insufficient.
3. The mismatch therefore is not merely timing of donor selection.
4. Matching QQQ regime plus the same Top2's recent 20d loss does not reproduce the empirical short-term continuation of the endogenous losers that caused Historical Stop/Circuit events.
5. A more faithful trigger model would need richer cross-sectional/event dynamics (e.g. pre-trigger acceleration, idiosyncratic residual behavior, or analog events across other stocks), which materially increases model complexity and tuning/model-risk.

## Validity decision

Current evidence is sufficient to stop trying to make CPCM an all-purpose structural simulator through incremental conditioning.

CPCM should be treated as:
- **usable** for broad chronology-preserving local price-path robustness and selected paired comparisons that do not depend strongly on endogenous risk-trigger aftermath;
- **not validated** for expected-return estimation;
- **not valid as primary evidence** for Stop, Circuit, or Recovery parameters.

For risk-trigger mechanics, use separate historical/crisis/event-based validation rather than further tuning CPCM to the small Historical Stop/Circuit sample.

Status: **ADAPTIVE EVENT SPLICE REJECTED AS A TRIGGER-CONDITIONAL FIX. CPCM SCOPE SHOULD BE LIMITED RATHER THAN FURTHER TUNED.**
