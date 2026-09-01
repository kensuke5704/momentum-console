# Stage 7 — Return-Stacked Risk Budget Preregistration

Date: 2026-09-01
Historical research end: 2026-08-25

## Starting strategy
Use Stage-6 GOV3 unchanged:
- underlying architecture: 50% Fixed60 + 20% frozen G + 30% DBMF
- 60-session trailing volatility governor
- target 18% annualized vol
- exposure floor 35%, cap 100%
- first 60 observations at 70%
Observed historical result before this stage: CAGR 33.13%, MaxDD -12.99%.

## New hypothesis
The governor leaves material drawdown budget unused relative to the ~15% target. Use modest portfolio-level return stacking / leverage to consume that risk budget rather than changing any alpha-engine rule or defensive threshold.

## Locked risk budgets
Test gross multipliers 1.10x, 1.20x, and 1.30x applied to GOV3 daily portfolio returns. No additional timing rule. This corresponds to a modest capital-efficiency overlay, not a change to Fixed60/G/DBMF signals.

## Decision
Strong pass = CAGR >=35% and MaxDD <=17%.
Preferred architecture is the lowest preregistered multiplier that clears CAGR 35% while keeping MaxDD <=17%; this ordering is fixed before results to avoid selecting the highest in-sample CAGR.
No testing of intermediate multipliers such as 1.05/1.15/1.25 after observing results.
