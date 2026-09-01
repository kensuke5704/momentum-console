# MaxDD ~15% Return-Stack Findings — 2026-09-01

Production Fixed60 remains unchanged. All results are same-sample historical evidence through 2026-08-25, not Forward OOS.

## Search objective
CAGR >=35% with historical MaxDD <=17%, while avoiding fine-grained weight/threshold tuning.

## Prior frontier
- P2: 42% Fixed60 + 18% frozen G + 40% cash -> CAGR 29.20%, MaxDD -15.04%.
- Gold-trend cash replacement improved the frontier but did not pass 35%: best preregistered <=17% result was 42% Fixed60 + 18% G + 30% Gold trend + 10% cash -> CAGR 32.94%, MaxDD -16.93%.
- Multi-asset long/flat trend held DD near 15% but CAGR was only 31.59% at full cash replacement.
- DBMF architecture 50% Fixed60 + 20% G + 30% DBMF produced CAGR 38.11%, MaxDD -18.35%; return target passed but DD target failed.

## Portfolio governor
On the locked 50/20/30 Fixed60/G/DBMF architecture, GOV3 was preregistered as:
- 60-session realized portfolio volatility using prior returns only.
- 18% annualized vol target.
- exposure floor 35%, cap 100%.
- first 60 observations at 70% exposure.

GOV3 result before return stacking:
- CAGR 33.13%
- MaxDD -12.99%
- annualized volatility 16.70%
- Calmar 2.55

This left material unused DD budget.

## Return stacking
Preregistered multipliers were 1.10x, 1.20x, 1.30x applied to GOV3 daily portfolio returns. Selection rule was fixed before results: choose the lowest multiplier that clears CAGR 35% while MaxDD remains <=17%.

Results:
- 1.00x: CAGR 33.13%, MaxDD -12.99%, Calmar 2.55 — return target fails.
- **1.10x: CAGR 36.79%, MaxDD -14.23%, annualized vol 18.37%, Calmar 2.58 — STRONG PASS.**
- 1.20x: CAGR 40.50%, MaxDD -15.47%, Calmar 2.62 — passes but not selected by preregistered ordering.
- 1.30x: CAGR 44.28%, MaxDD -16.69%, Calmar 2.65 — passes but not selected by preregistered ordering.

## Current leading architecture
Research ID: maxdd15-returnstack-v1-candidate

Underlying sleeves:
- Fixed60 50%
- frozen G 20%
- DBMF buy-and-hold 30%

Risk layer:
- GOV3 60-session trailing-vol governor (18% target, 35%-100% base exposure, 70% first-60-session warm-up)
- portfolio-level 1.10x return-stack multiplier

Effective gross exposure range is approximately 38.5%-110% of the underlying 50/20/30 portfolio; warm-up exposure is 77%.

## Interpretation
This is the first preregistered architecture in the MaxDD~15 redesign to clear both historical targets. The mechanism is not a new equity alpha threshold: DBMF adds an orthogonal managed-futures return stream, the vol governor creates drawdown headroom, and modest return stacking uses that headroom.

## Governance / caveats
- This is NOT proof that future MaxDD will be capped at 15%.
- Multiple strategy families were searched on the same 2020-2026 sample; strategy-selection bias is material.
- 1.10x is selected because it was the lowest preregistered passing multiplier, not because it maximized historical CAGR.
- Do not test intermediate multipliers such as 1.05x/1.15x or tune the 18% vol target on this sample.
- Do not alter Fixed60 or frozen G mechanics.
- Before any production use, implementation/cost realism and Forward OOS are required.
