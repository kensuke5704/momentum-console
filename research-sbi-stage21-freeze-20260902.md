# SBI-only Stage 21 rounded v1 freeze — 2026-09-02

Production Fixed60 remains unchanged. This document freezes a research-only candidate; it is not Production-approved.

## Objective
Build an SBI Securities-executable architecture targeting same-sample planning CAGR >= 40% and historical MaxDD near 15-17%, without borrowing, margin, or gross exposure above 100%.

Planning proxy remains:
`min(stress-median CAGR, rolling-36M median CAGR)`.

This is a same-sample robustness/planning proxy, NOT True Forward OOS evidence and NOT a statistical expected return.

## Why this candidate exists
The original Stage15 used DBMF and BTAL, which were not confirmed on SBI Securities' current overseas ETF list. SBI-only substitution research therefore replaced unavailable funded sleeves with SBI-buyable instruments and tested coarse structural alternatives rather than dense weight grids.

Key SBI-only path before the final candidate:
- GLDM + IEF + SH: planning 36.44%, MaxDD -16.33%.
- GLDM + SHY + SH: planning 37.22%, MaxDD -16.13%.
- GLDM + SHY + cash defense: planning 37.06%, MaxDD -15.94%.
- GLDM + SLV + cash defense: planning 38.82%, MaxDD -17.29%.
- all GLDM + cash defense: planning 38.86%, MaxDD -16.12%.
- all SLV + cash defense: planning 38.71%, MaxDD -19.90%.

Silver increased full-sample return but did not improve rolling-36M median and materially worsened drawdown. Precious-metals allocation search stopped at those structural endpoints.

## Frozen funded architecture — rounded v1
The prior G funded sleeve was structurally reassigned to Fixed60. G is not funded in this candidate.

### NORMAL
- Fixed60: **85.0%**
- GLDM: **15.0%**
- Cash: **0.0%**

### YELLOW — CFTC signal
- Fixed60: **55.5%**
- GLDM: **22.5%**
- Cash: **22.0%**

### DEEP — frozen M3 signal
- Fixed60: **25.5%**
- GLDM: **30.0%**
- Cash: **44.5%**

Weights sum to 100% in every state. No borrowing or margin is used.

The rounded weights replace the earlier mechanically generated fractional weights (for example 22.4375%). The rounded version was tested directly and is effectively performance-equivalent; the fractional precision is not required.

## Signals remain frozen
### CFTC Yellow
- CFTC Traders in Financial Futures, NASDAQ MINI contract code 209742.
- Asset Manager net = long - short.
- One-week publication lag.
- Yellow when latest eligible Asset Manager net is lower than four weekly reports earlier.
- No magnitude threshold.

### M3 Deep
The M3 trigger definition is unchanged from prior research, including its frozen 85% Fixed60 / 15% G **shadow core** used only for risk-state measurement.

Important: G is not a funded portfolio sleeve, but remains inside the pre-existing M3 shadow series. This distinction is intentional and must not be silently changed.

## Rebalancing and implementation
- Monthly rebalance.
- Immediate rebalance when NORMAL/YELLOW/DEEP state changes.
- Baseline one-way turnover cost: 10bp.
- Standard cost stress: 30bp.
- Existing +1 and +2 session signal/execution-lag stresses retained.
- Later-start tests retain historical state/signal context, then trim and rebase the portfolio equity curve.

## Rounded center same-sample result through 2026-08-25
- Historical CAGR: **49.3440%**
- Historical MaxDD: **-16.8860%**
- Annualized volatility: **25.4452%**
- Calmar: **2.9222**
- Final equity multiple: **14.3693x**

Standard stress CAGRs:
- 30bp cost: **47.8176%**
- +1 lag: **47.3586%**
- +2 lag: **47.6861%**
- start 2021: **44.2329%**
- stress median: **47.5224%**

Rolling 36M:
- median CAGR: **43.6573%**
- worst CAGR: **23.4205%**

Planning proxy:
- `min(47.5224%, 43.6573%) = **43.6573%**`

Research gate:
- planning proxy >= 40%: **PASS**
- historical MaxDD >= -17%: **PASS**
- combined gate: **PASS**

## Plateau / neighborhood robustness
After the first PASS, no fine grid was used. Seven coarse neighboring structures were tested only to determine whether the result lies on a broad plateau.

| Pattern | Structural perturbation | Historical CAGR | Planning proxy | MaxDD | Gate |
|---|---|---:|---:|---:|---|
| P0 | rounded center | 49.34% | 43.66% | -16.89% | PASS |
| P1 | NORMAL Fixed60 80% / GLDM 20% | 47.29% | 41.56% | -16.25% | PASS |
| P2 | NORMAL Fixed60 90% / GLDM 10% | 51.40% | 45.83% | -17.52% | FAIL DD |
| P3 | YELLOW/DEEP Fixed60 -1pt, Cash +1pt | 49.13% | 43.64% | -16.78% | PASS |
| P4 | YELLOW/DEEP Fixed60 +1pt, Cash -1pt | 49.56% | 43.74% | -16.99% | PASS |
| P5 | YELLOW/DEEP GLDM -1pt, Cash +1pt | 49.15% | 43.53% | -16.85% | PASS |
| P6 | YELLOW/DEEP GLDM +1pt, Cash -1pt | 49.54% | 43.85% | -16.92% | PASS |

Interpretation:
- **6 of 7** coarse neighbors pass both gates.
- All YELLOW/DEEP +/-1pt perturbations remain within a narrow band and pass.
- NORMAL 80/20 passes comfortably.
- NORMAL 90/10 raises return but crosses the DD boundary to -17.52%.
- The result is therefore not dependent on the original four-decimal weights.
- Evidence supports a broad local plateau on roughly the 80-85% Fixed60 side of NORMAL, with a historical DD boundary appearing as NORMAL exposure approaches 90% Fixed60.

This is robustness evidence, not permission to optimize inside the plateau.

## Extreme implementation stress
The rounded center was subjected to deliberately severe implementation perturbations.

### Higher transaction cost
- 50bp one-way turnover-cost stress CAGR: **46.3057%**.
- 100bp one-way turnover-cost stress CAGR: **42.5888%**.

Even the 100bp one-way stress remained above 40% CAGR in this historical sample. The portfolio is therefore not dependent on the baseline 10bp assumption.

### Longer signal / execution lag
- +3 session lag stress CAGR: **51.0362%**.
- +5 session lag stress CAGR: **52.1169%**.

These lagged variants happened to improve historical CAGR. This is NOT a reason to change the frozen execution rule. The relevant robustness conclusion is only that the architecture does not collapse when timing is displaced by several sessions and does not appear to depend on a one-day execution coincidence.

## Later-start period robustness
Using the full state/signal history and then trimming/rebasing portfolio equity:

| Period start | CAGR | MaxDD |
|---|---:|---:|
| 2021-01-01 | **44.23%** | **-16.68%** |
| 2022-01-01 | **43.06%** | **-13.90%** |
| 2023-01-01 | **57.69%** | **-13.90%** |
| 2024-01-01 | **50.30%** | **-13.90%** |

Interpretation:
- Historical low-DD behavior is not solely produced by the 2020 episode.
- 2021 onward still remains inside the 17% historical DD gate.
- 2022 onward historical MaxDD is about 13.9% in this sample.
- Shorter later-start windows are descriptive only and must not be treated as forecasts.

## Component ablation
Components were removed one at a time to diagnose what actually creates the Stage21 result. These are not alternative candidates to optimize.

| Variant | CAGR | Planning proxy | MaxDD | Interpretation |
|---|---:|---:|---:|---|
| Base rounded v1 | 49.34% | 43.66% | -16.89% | PASS |
| No CFTC Yellow; retain M3 Deep | 50.89% | 46.30% | -18.86% | CFTC sacrifices return but trims additional tail risk |
| No M3 Deep; retain CFTC Yellow | 53.90% | 43.21% | -22.50% | M3 is the primary deep-tail defense |
| No GLDM; substitute Cash | 43.88% | 40.39% | -17.07% | GLDM supplies return density and a small DD benefit |
| No CFTC and no M3 | 56.09% | 47.87% | -26.18% | Dynamic risk states are essential for the DD target |

Role attribution from ablation:
1. **M3 is the primary tail-defense engine.**
2. **CFTC is an anticipatory incremental tail trim.**
3. **GLDM is a return-preserving diversifier and also marginally improves DD versus cash.**
4. The simultaneous 40% planning / ~17% DD PASS comes from their combination, not from a single magic allocation number.

## Current robustness conclusion
The rounded Stage21 candidate now has four separate forms of same-sample evidence:
1. **Allocation plateau:** 6/7 coarse neighboring structures pass.
2. **Implementation robustness:** very high cost and multi-session lag do not destroy the return profile.
3. **Temporal robustness:** later-start periods retain high CAGR and low historical DD.
4. **Structural attribution:** removing M3, CFTC, or GLDM degrades a distinct part of the return/DD tradeoff in an economically coherent way.

This materially strengthens the same-sample case compared with the initial single PASS. It still does not convert the result into True Forward OOS evidence.

## Governance / final same-sample freeze
Same-sample strategy search stops here.

Do NOT now optimize:
- GLDM weight around 15%,
- Fixed60 weight inside the observed 80-90% neighborhood,
- YELLOW/DEEP weights,
- cash levels,
- CFTC 4-week lookback or participant class,
- CFTC magnitude thresholds,
- M3 trigger/recovery thresholds,
- G shadow-core weight,
- gold/silver mixtures,
- execution-delay definitions,
- transaction-cost assumptions to improve reported metrics.

Any such tuning after observing these results would increase same-sample overfitting risk.

## Forward OOS protocol
The next useful evidence is True Forward / paper OOS, not more historical optimization.

### Freeze
- Candidate identifier: **research-sbi-stage21-rounded-v1**.
- Strategy mechanics, state definitions, funded weights, data lags, and execution assumptions are frozen by this document.
- Production Fixed60 is not changed.

### What to record every eligible US session
- frozen Fixed60 output / portfolio return,
- GLDM close and execution price when rebalancing,
- latest eligible CFTC report date and Asset Manager net,
- CFTC Yellow status,
- frozen M3 Deep status,
- final NORMAL / YELLOW / DEEP state,
- target funded weights,
- actual intended trade date and execution price,
- realized turnover and estimated transaction cost,
- portfolio equity and drawdown,
- any data delay, missing observation, or parity discrepancy.

### Evaluation discipline
- First ~3 months: judge **parity, data timing, state correctness, and execution correctness**, not CAGR.
- Do not change rules because of a short favorable or unfavorable sequence.
- Track gross/pre-tax research OOS separately from Production Fixed60 OOS.
- At longer horizons compare realized drawdown, turnover, state behavior, and annualized return with the historical robustness envelope, but do not require reproduction of the 43.66% planning proxy.
- Any future rule change creates a new candidate/version and restarts its OOS clock; it must not be backfilled into this frozen candidate.

## What this result does and does not mean
It establishes a relatively broad, implementation-robust, SBI-executable same-sample candidate using funded Fixed60 underlying securities, GLDM, and cash, plus public CFTC data and the frozen M3 risk-state calculation.

It does **not** establish a 43-44% true expected CAGR. The **43.66%** figure is a historical robustness/planning proxy. True Forward OOS evidence is required before Production replacement or high confidence in future performance can be justified.

Production Fixed60 remains unchanged unless the user explicitly approves a Production change.
