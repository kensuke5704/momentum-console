# Residual-Cash TQQQ Screen — Preregistered 2026-09-01

Goal: raise forward planning CAGR proxy toward 40% without margin borrowing and while keeping historical MaxDD around 15% (hard research tolerance -17%).

Base portfolio remains the previously tested 50% Fixed60 / 20% frozen G / 30% DBMF architecture.

Risk layer remains GOV3:
- 60-session trailing realized volatility of the base portfolio using prior returns only,
- 18% annualized vol target,
- base exposure floor 35%, cap 100%,
- first 60 sessions at 70% base exposure.

New implementation: instead of borrowing to lever GOV3, use only the cash left idle by GOV3. If GOV3 base exposure is x, residual cash is (1-x). When QQQ close > QQQ 200-session SMA, a fraction h of that residual cash is invested in TQQQ using a close signal and next-US-session-open execution. When the trend gate is off, residual capital stays cash.

Cash constraint: x + h*(1-x) <= 1 at all times. No margin or portfolio borrowing.

Preregistered h values:
- RC25: h=25%
- RC50: h=50%
- RC100: h=100%

Do not test intermediate h values after results.

Primary planning-CAGR definition and pass rules remain those in `research/predicted-cagr40-preregister-20260901.md`.
