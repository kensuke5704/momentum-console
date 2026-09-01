# Stage 15 — Static Pre-funded Hedge

Frozen before execution on 2026-09-01.

## Rationale
Stages 11, 13, and 14 show that post-loss defensive triggers are structurally too late for the 2020-09 type drawdown. This stage removes signal timing from the tail hedge by pre-funding a small permanent anti-beta sleeve.

## Architecture
Candidate G remains 15%. The hedge is funded only from Fixed60.
- H5: 80% Fixed60 / 15% G / 5% BTAL.
- H10: 75% Fixed60 / 15% G / 10% BTAL.
- H15: 70% Fixed60 / 15% G / 15% BTAL.

Slow M3 remains unchanged. When M3 is active, all three variants use the existing defensive allocation: 30% Fixed60 / 15% G / 35% BTAL / 20% cash. Thus the only structural variable is the always-on hedge before a breakdown.

## Execution / costs
- No timing rule for the static hedge; daily sleeve accounting.
- M3 uses prior close and next-session allocation as before.
- Baseline 10bp/side proxy on M3 allocation transitions.
- Stresses: 30bp/side, +1 signal-session lag, +2 signal-session lag, start 2021.

## Pass gate
- Forward-planning CAGR proxy = min(stress CAGR median, rolling 36M CAGR median) >= 40%.
- MaxDD >= -17%.
- No interpolation or post-result hedge-weight optimization.
