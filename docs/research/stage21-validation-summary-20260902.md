# Stage21 Validation Summary — 2026-09-02

対象: `momentum-stage21-sbi-2026-09-v1` / Stage21 rounded v1

この文書は、Production採用までに行った主要なsame-sample検証と、2026-09-02に再計算した暦年リターンをまとめたものです。Production仕様そのものは `docs/production/stage21-sbi-2026-09-v1.md` を参照してください。

## Frozen funded states

| State | Fixed60 | GLDM | Cash |
|---|---:|---:|---:|
| NORMAL | 85.0% | 15.0% | 0.0% |
| YELLOW | 55.5% | 22.5% | 22.0% |
| DEEP | 25.5% | 30.0% | 44.5% |

Gはfunded sleeveではなく、M3 shadow-coreのsignal seriesとしてのみ使用します。

## Release-aware historical reference

2020-01-01〜2026-08-25:

- CAGR: **48.6072%**
- MaxDD: **-16.8860%**
- Annualized volatility: **25.1960%**
- Calmar: **2.8786**
- Final equity: **13.9048x**
- Planning proxy: **43.66%**
- Rolling 36M median CAGR: **43.66%**
- Rolling 36M P10 CAGR: **35.19%**
- Rolling 36M worst CAGR: **23.42%**

Planning proxyはTrue Forward expected CAGRではありません。

## Calendar-year returns — recomputed 2026-09-02

定義:
- 2020年: initial equity 1.0 → 2020年最終営業日equity
- 2021年以降: 前年最終営業日equity → 当年最終営業日equity
- 2026年は **2026-08-25までのYTD**
- release-aware CFTC timingを使用
- Stage21 rounded v1、10bp one-way baseline cost

| Year | Return |
|---|---:|
| 2020 | **+76.67%** |
| 2021 | **+55.10%** |
| 2022 | **-0.34%** |
| 2023 | **+86.94%** |
| 2024 | **+63.96%** |
| 2025 | **+45.15%** |
| 2026 YTD through 2026-08-25 | **+14.44%** |

Reproduction audit:
- research branch: `research/cagr40-new-alpha-20260901`
- workflow run: **33573510827**
- workflow result: success
- research commit: `3a2367a2565d43c05c8a7b7079b8578b5a9bc969`

The same run reproduced CAGR 48.6072% and MaxDD -16.8860%, matching the frozen release-aware reference.

## Profit Factor diagnostic

Stage21 is a continuously rebalanced portfolio rather than a simple one-position-per-trade system. For a reproducible portfolio-level diagnostic, daily PF is defined as:

`sum(positive daily equity P&L) / abs(sum(negative daily equity P&L))`

Result:
- **Daily Profit Factor: 1.3910**

This should not be compared mechanically with trade-level PF from a discrete-entry/discrete-exit strategy.

## Robustness evidence

### Parameter plateau
- 7 coarse neighboring allocation patterns tested
- 6 / 7 passed both planning >=40% and historical MaxDD >=-17%
- only Normal Fixed60 90% / GLDM 10% failed DD, at approximately -17.52%
- Yellow/Deep ±1pt perturbations remained near planning 43.5–43.9% and MaxDD -16.8 to -17.0%

Interpretation: performance is not concentrated at an exact decimal allocation point.

### Execution/cost stress
- 50bp one-way cost stress CAGR approximately 46.31%
- 100bp one-way cost stress CAGR approximately 42.59%
- +3 session lag CAGR approximately 51.04%
- +5 session lag CAGR approximately 52.12%

Interpretation: historical result is not dependent on one exact next-open timing point or unrealistically tiny costs.

### Subperiod checks
- 2021 onward: CAGR approximately 44.23%, MaxDD approximately -16.68%
- 2022 onward: CAGR approximately 43.06%, MaxDD approximately -13.90%
- 2023 onward: CAGR approximately 57.69%, MaxDD approximately -13.90%
- 2024 onward: CAGR approximately 50.30%, MaxDD approximately -13.90%

### Rolling joint robustness
| Window | CAGR>40% and DD<=17% pass share | CAGR median | CAGR P10 | Worst CAGR |
|---|---:|---:|---:|---:|
| 24M | 62.7% | 47.62% | 26.82% | 11.52% |
| 30M | 63.2% | 48.43% | 29.65% | 18.43% |
| 36M | 74.7% | 44.18% | 35.19% | 23.42% |
| 48M | 89.7% | 47.83% | 39.82% | 32.12% |

All tested rolling windows remained within the 17% DD research boundary, but CAGR 40% is not maintained in every 2–3 year period.

## Ablation

| Removed / replaced component | Planning | MaxDD | Interpretation |
|---|---:|---:|---|
| CFTC removed | ~46.30% | ~-18.86% | CFTC contributes additional tail reduction |
| M3 removed | ~43.21% | ~-22.50% | M3 is the main drawdown defense |
| GLDM -> Cash | ~40.39% | ~-17.07% | GLDM helps preserve return and slightly improve DD |
| CFTC + M3 removed | ~47.87% | ~-26.18% | dynamic defense is structurally important |

## CFTC PIT audit

The ordinary one-week lag was conservative in normal periods, but the 2025 US government shutdown created delayed CFTC releases. Historical simulation was corrected to actual release availability for the affected backlog.

Effect of the correction:
- Historical CAGR fell from about 49.34% to **48.61%**
- MaxDD remained **-16.89%**
- planning proxy remained about **43.66%**

The main research conclusion survived the PIT correction.

## Account realism

Integrated next-open + 10bp + whole-share simulations were tested for $10k, $25k, $50k, $100k and $250k accounts.

- all tested account sizes remained within 17% historical MaxDD
- at $10k, CAGR difference vs fractional-share simulation was approximately -0.36 percentage point
- larger accounts were closer to the fractional result

## Overfitting assessment

Current assessment:
- exact-parameter / local overfit risk: **low to medium**
- architecture-selection bias: **meaningful / medium**
- True Forward evidence: **not yet sufficient**

Reasons local overfit risk is reduced:
- coarse rather than dense parameter grids
- mechanically defined Yellow midpoint before rounding
- neighboring plateau tests
- cost and execution-delay stress
- ablation
- contiguous rolling-window tests
- PIT correction
- whole-share account realism

Remaining limitation:
Stage21 was selected after many architectures were evaluated on the same 2020–2026 historical sample. That selection effect cannot be removed by more same-sample tuning.

Therefore no further same-sample optimization of GLDM weight, Fixed60 weight, CFTC lookback/category/threshold, M3 thresholds, Yellow/Deep allocations, or G funded weight is permitted for this strategy ID.

## True Forward OOS

- start: **2026-09-02**
- separate from legacy Fixed60 OOS
- first ~3 months: no CAGR judgment; data/state/execution parity only
- MaxDD -17%: AMBER review
- MaxDD -25%: RED kill / stop new Stage21 buying, Cash next open
- 12M+: CAGR <0 and DD <=-17%: RED
- 24M+: gross CAGR <15%: RED
- 36M+: gross CAGR <25%: RED

Any rule change requires a new strategy ID and a new OOS clock.
