# Stage 5 — Orthogonal Hedge / Managed-Futures Preregistration

Date: 2026-09-01
Historical research end: 2026-08-25

## Objective
Seek CAGR >=35% with historical MaxDD <=17% by replacing cash with a sleeve that can earn positive return during equity stress.

## Candidate sleeves
H1 DBMF buy-and-hold: investable managed-futures proxy, continuously held.
H2 BTAL buy-and-hold: anti-beta market-neutral proxy, continuously held.
H3 PSQ risk-off hedge: hold PSQ only when QQQ close is below QQQ 200DMA; otherwise cash. Signal at close, effective next session.
H4 Defensive blend: equal 50/50 of DBMF and PSQ-risk-off sleeve.

## Locked portfolio architectures
A = 50% Fixed60 + 20% frozen G + 30% hedge sleeve.
B = 55% Fixed60 + 20% frozen G + 25% hedge sleeve.
C = 50% Fixed60 + 25% frozen G + 25% hedge sleeve.
No residual cash in these tests except inside a hedge sleeve when its rule is flat.

These are preregistered round architectures, not an allocation grid.

## Decision
Strong pass = CAGR >=35% AND MaxDD <=17%.
Reject a sleeve if all A/B/C fail the drawdown constraint or fail to improve the return/DD frontier versus Stage 4.
Do not tune QQQ trend length, hedge asset, or weights after results are observed.
