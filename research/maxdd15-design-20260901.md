# MaxDD ~15% Portfolio Redesign — 2026-09-01

Production Fixed60 remains unchanged. This is a separate research portfolio design.

## Objective
Target historical MaxDD around 15% while preserving as much CAGR as practical.

## Governance
- No fine threshold search to force MaxDD to exactly 15%.
- Use round, preregistered risk budgets and simple trailing-volatility controls.
- Historical comparison ends 2026-08-25 to remain consistent with frozen G/U research.
- Fixed60, G, and U rules are not modified.

## Candidate families
A. Static risk-budget scaling: Fixed60 at 40/50/60% exposure, residual cash.
B. G/U equal basket at 50/60/70% exposure, residual cash.
C. Equal Fixed60/G/U ensemble at 50/60/70% exposure, residual cash.
D. Trailing-volatility targeting on Fixed60 and on the equal three-engine ensemble, using only prior realized returns. Targets: 12%, 15%, 18% annualized volatility; max exposure 100%.

The purpose is to identify a robust architecture near the 15% drawdown objective, not an optimized point estimate.