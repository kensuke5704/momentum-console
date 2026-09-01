# MaxDD ~15% Redesign Findings — 2026-09-01

Production Fixed60 is unchanged. All results below are same-sample historical portfolio-design evidence through 2026-08-25, not Forward OOS.

## Baselines
- Fixed60: CAGR 61.998%, MaxDD -31.13%.
- 40% Fixed60 + 60% cash: CAGR 23.02%, MaxDD -13.57%.
- 45% Fixed60 + 55% cash: CAGR 26.08%, MaxDD -15.16%.
- 50% Fixed60 + 50% cash: CAGR 29.18%, MaxDD -16.72%.

## Diversification screens
- 60% exposure to equal Fixed60/G/U basket: CAGR 22.41%, MaxDD -14.28%; did not beat static Fixed60 scaling.
- 60% exposure to equal G/U basket: CAGR 15.64%, MaxDD -15.41%; rejected for insufficient return.

## Dynamic governors
- QQQ200 regime scaler (100% Fixed60 above QQQ 200DMA, 40% otherwise): effectively identical to Fixed60 because the overlay largely overlaps existing Fixed60 risk logic; MaxDD remained -31.13%.
- Shadow-DD scaler (100% / 50% / 25% exposure based on shadow Fixed60 DD bands -5%/-10%): CAGR 46.62%, MaxDD -23.92%; return remained strong but drawdown target failed.
- Initial 60-day volatility-target screen is not treated as valid evidence because the 2020 start lacked a pre-start strategy-return warm-up and the COVID drawdown occurred during the unscaled warm-up.

## Fixed60 + frozen G target-DD portfolios
- P1: 45% Fixed60 / 55% cash -> CAGR 26.08%, MaxDD -15.16%, Calmar 1.72.
- P2: 42% Fixed60 / 18% G / 40% cash -> CAGR 29.20%, MaxDD -15.04%, annualized vol 16.45%, Calmar 1.94.
- P3: 39% Fixed60 / 26% G / 35% cash -> CAGR 29.50%, MaxDD -15.56%, Calmar 1.90.
- P4: 35% Fixed60 / 35% G / 30% cash -> CAGR 29.40%, MaxDD -16.00%, Calmar 1.84.

## Current interpretation
P2 is the current leading historical architecture for a ~15% MaxDD objective. It improves historical CAGR by about 3.1 percentage points versus 45% Fixed60 alone while slightly reducing MaxDD. The economic rationale is diversification: frozen G has low historical monthly correlation with Fixed60 (~0.325).

P2 is NOT a production recommendation or statistically validated optimum. The allocation was studied after observing Fixed60/G history, so portfolio-weight selection bias exists. Do not fine-tune 42/18 to nearby weights on the same sample. The next useful work is robustness and Forward OOS governance, not weight optimization.