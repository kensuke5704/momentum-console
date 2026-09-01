# Stage 13 — Shock Quarantine

Frozen before execution on 2026-09-01.

## Purpose
Stage 11 showed that fast detection alone does not reduce MaxDD enough when it enters the same mild defensive sleeve as slow M3. This stage separates the jobs of the two detectors.

## Rules
- Normal: 85% Fixed60 / 15% Candidate G.
- Slow M3: unchanged from Stage 9: if 20-session core return < 0 and core minus QQQ 20-session return <= -10pp, use 30% Fixed60 / 15% G / 35% BTAL / 20% cash. Recovery remains relative gap > -3pp for 5 consecutive sessions.
- Fast shock: if prior-close shadow core 5-session return <= -8%, override all sleeves and hold 100% cash for exactly 5 sessions.
- After 5 sessions, if slow M3 remains active, fall back to the slow defensive sleeve; otherwise return to normal.
- A new fast shock can start a new 5-session quarantine only after the prior quarantine has ended.

## Execution / costs
- Prior close signal only; allocation applies to next session return.
- Baseline cost 10bp/side.
- Stresses: 30bp/side, +1 session signal lag, +2 session signal lag, start 2021.

## Pass gate
- Forward-planning CAGR proxy = min(stress CAGR median, rolling 36M CAGR median) >= 40%.
- MaxDD >= -17%.
- No duration or threshold tuning after observing this result.
