# CAGR40 / MaxDD17 Research Frontier — 2026-09-01

Production Fixed60 remains unchanged. All tests below are research-only on `research/cagr40-orthogonal-20260901`.

## Objective
- Forward-planning CAGR proxy >= 40%
- Historical MaxDD >= -17%
- No borrowing / no gross exposure above 100%

The forward-planning proxy used in these screens is the minimum of stress-median CAGR and rolling-36-month median CAGR. This is a research planning proxy, not True Forward OOS evidence.

## Current return frontier

- L2 late-tail: planning proxy 40.84%, MaxDD -23.70%
- M3 stress detector: planning proxy 47.79%, MaxDD -23.30%
- N2 fast shock: planning proxy 46.90%, MaxDD -23.66%
- N3 dual-speed: planning proxy 47.53%, MaxDD -23.30%
- 5-session shock quarantine: planning proxy 45.23%, MaxDD -23.91%
- Static BTAL 10%: planning proxy 41.64%, MaxDD -21.99%

These variants show that historical planning-return capacity above 40% exists, but the drawdown remains around 22-24%.

## Stage 16 — BTAL / conditional-TQQQ barbell

Preregistered structures:
- P1 normal: Fixed60 65%, G 15%, BTAL 10%, conditional TQQQ 10%
- P2 normal: Fixed60 60%, G 15%, BTAL 15%, conditional TQQQ 10%
- P3 normal: Fixed60 60%, G 15%, BTAL 10%, conditional TQQQ 15%
- TQQQ only when QQQ > 200DMA and shadow drawdown > -3%; otherwise its allocation is cash
- Existing M3 defensive state retained

Results:
- P1: CAGR 41.54%, MaxDD -20.40%, stress median 39.93%, rolling36 median 37.57%, planning proxy 37.57%
- P2: CAGR 38.29%, MaxDD -19.73%, stress median 36.79%, rolling36 median 34.48%, planning proxy 34.48%
- P3: CAGR 39.30%, MaxDD -19.59%, stress median 37.73%, rolling36 median 35.45%, planning proxy 35.45%

Conclusion: barbell construction improves MaxDD by roughly 3-4 points versus the high-return frontier, but does not preserve the 40% planning proxy. Rejected as a simultaneous 40% / 17% solution.

## Stage 17 — Volatility targeting

Architecture:
- Normal engine remains 85% Fixed60 / 15% G
- 20-session realized volatility of the shadow 85/15 portfolio determines exposure scale
- Scale = min(1, target volatility / realized volatility)
- No leverage; unused allocation is cash
- Existing M3 defensive state retained
- Only two round-number targets were screened: 20% and 25%

Results:
- V20: CAGR 31.77%, MaxDD -16.91%, annualized vol 17.53%, stress median CAGR 32.42%, rolling36 median CAGR 29.97%, rolling36 worst 18.86%, planning proxy 29.97%
- V25: CAGR 37.16%, MaxDD -18.16%, annualized vol 20.58%, stress median CAGR 37.61%, rolling36 median CAGR 35.51%, rolling36 worst 23.03%, planning proxy 35.51%

Conclusion:
- V20 is the first tested architecture to satisfy the -17% historical MaxDD objective.
- It does so by reducing the planning proxy from >40% to ~30%.
- V25 moves back toward the return objective but loses the drawdown objective.
- This establishes a clear empirical return/drawdown frontier for the current Fixed60 + G + BTAL risk-control family.

## Research decision

Stop additional same-sample tuning of:
- BTAL weights
- TQQQ weights
- drawdown thresholds
- fast-shock thresholds
- volatility targets between 20% and 25%

Interpolating or grid-searching these values would mainly optimize against the 2020-2026 sample and is unlikely to add independent evidence.

The next useful research step is not another risk-control threshold. It is a genuinely distinct, low-correlation return engine that can replace part of Fixed60 exposure while preserving return under a lower portfolio volatility budget.

Any new engine must be evaluated independently first, then blended with a frozen reference architecture. No Production strategy mechanics are approved by this document.