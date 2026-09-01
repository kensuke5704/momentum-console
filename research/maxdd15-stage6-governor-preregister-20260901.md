# Stage 6 — Portfolio Governor Preregistration

Date: 2026-09-01
Historical research end: 2026-08-25

## Locked base architecture
50% Fixed60 + 20% frozen G + 30% DBMF buy-and-hold.
Observed Stage-5 baseline: CAGR 38.11%, MaxDD -18.35%.
Weights are now frozen for this stage. No nearby allocation search.

## Objective
Reduce tail drawdown to <=17% while retaining CAGR >=35%.

## Governors
GOV1 two-state shadow-DD governor:
- Use the ungoverned base portfolio as shadow NAV.
- Full exposure while shadow DD > -10%.
- Next session exposure = 35% when shadow DD <= -10%.
- Return to full exposure only when shadow DD > -5%.

GOV2 three-state shadow-DD governor:
- Full exposure when shadow DD > -8%.
- 60% exposure when shadow DD <= -8% but > -12%.
- 25% exposure when shadow DD <= -12%.
- Return to full only after shadow DD > -4%; transitions use prior-close information.

GOV3 trailing-vol governor:
- 60-session realized volatility of the locked base portfolio, using only prior returns.
- Target 18% annualized volatility, max exposure 100%, min exposure 35%.
- Before 60 observations, use 70% exposure (not 100%) to avoid an uncontrolled warm-up.

## Decision
Strong pass = CAGR >=35% and MaxDD <=17%.
Do not tune thresholds, target volatility, or base weights after results are observed.
