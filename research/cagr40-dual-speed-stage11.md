# Stage 11 — Dual-speed Core Stress Detector

Frozen before execution on 2026-09-01.

## Baseline architecture
- Normal sleeve: 85% Fixed60 / 15% Candidate G.
- Defensive sleeve: 30% Fixed60 / 15% G / 35% BTAL / 20% cash.
- Slow detector: retain M3 exactly as tested: 20-session core return < 0 and core minus QQQ 20-session return <= -10 percentage points.
- Recovery: retain M3 recovery: relative gap > -3 percentage points for 5 consecutive sessions.

## Structural change
Add one fast detector family to the unchanged M3 slow detector. These are not parameter-neighbor optimizations; they represent three distinct failure definitions.

- N1 Drawdown break: shadow core drawdown <= -10% and 5-session core return < 0.
- N2 Fast crash: 5-session core return <= -8%.
- N3 Strategy-specific break: 10-session core return <= -10% while QQQ 10-session return > -5%.

Any fast detector OR the unchanged slow M3 detector enters the same defensive sleeve. Exit remains governed by the unchanged M3 recovery condition, with a minimum 5-session defensive hold to avoid one-day churn.

## Execution / cost
- Signal uses prior close only; allocation change applies to next session return.
- 10bp/side baseline transaction cost proxy.
- Stresses: 30bp/side, +1 session signal lag, +2 session signal lag, start 2021.

## Pass gate
- Forward-planning CAGR proxy = min(stress CAGR median, rolling 36M CAGR median) >= 40%.
- MaxDD >= -17%.
- No post-result threshold tuning in this stage.
