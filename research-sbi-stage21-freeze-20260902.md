# SBI-only Stage 21 candidate freeze — 2026-09-02

Production Fixed60 remains unchanged. This is research-only and is not Production-approved.

## Objective
SBI Securities executable architecture targeting same-sample forward-planning CAGR >= 40% and historical MaxDD near 15-17%, without borrowing and without allocation above 100% of portfolio capital.

Planning proxy remains:
`min(stress-median CAGR, rolling-36M median CAGR)`.
This is a same-sample robustness/planning proxy, NOT True Forward OOS evidence and NOT a statistical expected return.

## Why this candidate exists
The original Stage15 used DBMF and BTAL, which were not confirmed on SBI Securities' current overseas ETF list. SBI-only substitution research therefore replaced unavailable sleeves with products confirmed on SBI and tested only coarse structural alternatives rather than dense weight grids.

Key SBI-only path:
- GLDM + IEF + SH: planning 36.44%, MaxDD -16.33%.
- GLDM + SHY + SH: planning 37.22%, MaxDD -16.13%.
- GLDM + SHY + cash defense: planning 37.06%, MaxDD -15.94%.
- GLDM + SLV + cash defense: planning 38.82%, MaxDD -17.29%.
- all GLDM + cash defense: planning 38.86%, MaxDD -16.12%.
- all SLV + cash defense: planning 38.71%, MaxDD -19.90%.

Silver increased full-sample return but did not improve the rolling-36M median and materially worsened drawdown. Precious-metals weight exploration stops at these structural endpoints.

## Frozen Stage21 architecture
The final structural test reassigned the prior G capital sleeve to Fixed60 while keeping the existing CFTC and M3 signal definitions frozen.

### NORMAL
- Fixed60: 85.00%
- G held: 0.00%
- GLDM: 15.00%
- Cash: 0.00%

### YELLOW — CFTC signal
- Fixed60: 55.25%
- G held: 0.00%
- GLDM: 22.4375%
- Cash: 22.3125%

### DEEP — frozen M3 signal
- Fixed60: 25.50%
- G held: 0.00%
- GLDM: 29.875%
- Cash: 44.625%

Weights sum to 100% in every state. No borrowing or margin is used.

## Signals remain frozen
### CFTC Yellow
- CFTC Traders in Financial Futures, NASDAQ MINI contract code 209742.
- Asset Manager net = long - short.
- One-week publication lag.
- Yellow when latest eligible Asset Manager net is lower than four weekly reports earlier.
- No magnitude threshold.

### M3 Deep
The M3 trigger definition is unchanged from prior research, including its frozen 85% Fixed60 / 15% G **shadow core** used only for risk-state measurement.

Important: G is no longer a funded portfolio sleeve in Stage21, but remains part of the pre-existing frozen M3 shadow signal. This distinction is intentional and must not be silently changed in later evaluation.

## Rebalancing and implementation
- Monthly rebalance.
- Immediate rebalance when NORMAL/YELLOW/DEEP state changes.
- Baseline one-way turnover cost: 10bp.
- Cost stress: 30bp.
- Existing +1 and +2 session signal/execution lag stresses retained.
- Start-2021 stress retained.

## Stage21 same-sample result through 2026-08-25
- Historical CAGR: **49.3040%**
- Historical MaxDD: **-16.8727%**
- Annualized volatility: **25.4212%**
- Calmar: **2.9221**
- Final equity multiple: **14.3438x**

Stress CAGRs:
- 30bp cost: **47.7708%**
- +1 lag: **47.3133%**
- +2 lag: **47.6488%**
- start 2021: **44.1868%**
- stress median: **47.4810%**

Rolling 36M:
- median CAGR: **43.6434%**
- worst CAGR: **23.3988%**

Planning proxy:
- `min(47.4810%, 43.6434%) = **43.6434%**`

Research gate:
- planning proxy >= 40%: **PASS**
- historical MaxDD >= -17%: **PASS**
- combined gate: **PASS**

## Plateau / neighborhood robustness check
After the first PASS, no fine grid search was performed. Instead, a coarse preregistered neighborhood was tested to determine whether Stage21 sits on a broad plateau rather than at a single lucky allocation point.

Rounded center used for the neighborhood check:
- NORMAL: Fixed60 85.0%, GLDM 15.0%.
- YELLOW: Fixed60 55.5%, GLDM 22.5%, Cash 22.0%.
- DEEP: Fixed60 25.5%, GLDM 30.0%, Cash 44.5%.

Seven coarse perturbations were tested. The purpose was robustness diagnosis, not selecting the best performer.

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
- **6 of 7** coarse neighboring structures pass both gates.
- All YELLOW/DEEP +/-1 percentage-point perturbations remain within a narrow performance band and pass.
- NORMAL 80/20 also passes comfortably.
- NORMAL 90/10 raises return but crosses the DD gate to -17.52%.
- Therefore the PASS is not dependent on the original four-decimal weights such as 22.4375%.
- The evidence supports a broad plateau approximately on the 80-85% Fixed60 side of NORMAL and around the rounded YELLOW/DEEP allocations, with a risk boundary appearing as NORMAL exposure approaches 90% Fixed60.

The rounded center is operationally simpler and produces effectively the same result as the exact Stage21 weights. This robustness check is evidence for simplification, not a license to optimize further within the plateau.

## Governance / freeze
This is the first tested SBI-executable architecture to clear both research gates simultaneously, and the subsequent coarse neighborhood check shows that the result is not a single-point allocation artifact. Same-sample search stops here.

Do NOT now optimize:
- GLDM weight around 15%,
- Fixed60 weight within the observed 80-90% neighborhood,
- Yellow/Deep weights,
- cash levels,
- CFTC 4-week lookback or participant class,
- CFTC magnitude thresholds,
- M3 trigger/recovery thresholds,
- G weight between 0% and 12.75%,
- gold/silver mixtures,
- execution-delay definitions.

Any such tuning after observing this plateau would increase same-sample overfitting risk.

## What this result does and does not mean
It establishes a same-sample historical/robustness candidate that satisfies the research targets and uses SBI-buyable funded instruments (Fixed60 underlying US securities and GLDM; cash) plus public CFTC data for risk state. The plateau check strengthens the case that the allocation is not dependent on four-decimal precision. It does not establish a 43-44% true expected CAGR. True Forward OOS evidence is still required before Production replacement or confidence in future return can be justified.

Production Fixed60 remains unchanged unless the user explicitly approves a Production change.