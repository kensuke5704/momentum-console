# Fixed60 Forward Candidate Specification — 2026-08-30

## Status

Research candidate only. This document freezes the Fixed60 rule after the 2026-08-30 research screen. It does not change Production/main.

## Core rule

- Start from the existing Production strategy configuration and state machine.
- Momentum definition remains the Production 0/20/80 specification.
- Candidate ranking, universe construction, monthly market gate, Stop/Circuit/Recovery logic, transaction timing, and transaction-cost assumptions remain unchanged unless explicitly documented elsewhere.
- When two securities are held, allocate 60% to Top1 and 40% to Top2.
- `baseTop1Weight = 0.60`, `concentratedTop1Weight = 0.60`, and `maxTop1Weight = 0.60`.
- No leverage. Gross exposure remains 0–100%.
- No shorting, options, margin, or post-hoc theme override.

## Search freeze

The coarse allocation neighborhood 60/40, 65/35, and 70/30 was inspected. Fixed60 is frozen here. Do not continue searching 55/45, 57.5/42.5, 62.5/37.5, or other nearby weights using the same historical sample merely to improve CAGR.

## Historical evidence at freeze

Fixed60 historical gross CAGR was approximately 62.0%, versus approximately 59.0% for W70, with slightly better gross MaxDD. The annual realized-P&L tax approximation produced approximately 50.65% after-tax CAGR for Fixed60 versus approximately 48.18% for W70. These are historical/pseudo-OOS research results, not True Forward OOS.

Leave-one-symbol-out research showed materially reduced single-winner dependence versus W70, but dependence remains. MU and NVDA removals were the two strongest single-name stresses, and a post-hoc semiconductor/hardware group removal reduced Fixed60 gross CAGR below 40%. That group-removal test is descriptive stress only and must not be converted into a semiconductor-specific optimization rule.

## Structural edge-retention stress

A descriptive counterfactual was run on the 2020-01-03 through 2026-08-25 Fixed60 path. "Good regime" was defined before the haircut calculation as QQQ above its 200-day moving average with 20-day realized volatility below 30%. Approximately 74.1% of tested days met that condition.

The test removes a fixed fraction of the historical mean daily log return observed on those good-regime days while preserving the historical residual path. It is a sensitivity test only: it is not a calibrated probability model and does not rerun the state machine under altered prices.

- 100% edge retention: gross CAGR 62.03%, MaxDD -31.13%.
- 90% retention: gross CAGR 54.51%, MaxDD -32.35%.
- 85% retention: gross CAGR 50.88%, MaxDD -32.95%.
- 80% retention: gross CAGR 47.33%, MaxDD -33.55%.
- 75% retention: gross CAGR 43.87%, MaxDD -34.14%.
- 70% retention: gross CAGR 40.49%, MaxDD -34.72%.
- 50% retention: gross CAGR 27.75%.

Thus the tested gross historical path remains above 40% at 70% edge retention, but this must not be interpreted as a 70% probability of achieving 40%. The separate historical after-tax CAGR of approximately 50.65% implies that a simple proportional calculation would require roughly 79% retention to remain at 40% after tax; this proportional calculation is not an exact tax-under-decay simulation.

## Recovery bridge

The QQQ50 Recovery bridge remains an optional research overlay, not part of the Fixed60 core rule.

- K1 improved historical Fixed60 performance.
- K3 and K5 did not preserve that improvement.
- Therefore the bridge retains timing sensitivity and must not be used to justify a 40% Forward CAGR planning assumption.
- If monitored forward, use the already frozen QQQ50 K1 bridge lifecycle specification; bridge P&L must not feed the Production Stop/Circuit state machine.

## Forward clock

Fixed60 was identified using historical information on 2026-08-30. Therefore historical data before this freeze date cannot be called True Forward OOS for Fixed60.

- Fixed60-specific ex-ante clock begins after the 2026-08-30 freeze.
- The broader strategy's previously established True Forward OOS start date remains a separate record and must not be retroactively attributed to Fixed60.
- Forward observations must be logged without changing Fixed60 allocation or adding post-hoc filters because of early outcomes.

## Forward evaluation

Primary forward comparison:

1. Production rule as actually deployed at the time.
2. Frozen Fixed60 research shadow portfolio.
3. Optional Fixed60 + frozen QQQ50 K1 bridge shadow portfolio, reported separately.

Track at minimum cumulative return, annualized return when meaningful, MaxDD, realized volatility, turnover, transaction costs, tax-relevant realized gains/losses when available, exposure, monthly hit rate, and attribution by symbol/theme. Do not annualize very short samples as a decision metric.

## Candidate decision rule

Fixed60 remains a promising research candidate rather than a Production rule. Promotion requires evidence that the advantage over the prior allocation is not explained primarily by a small number of historical winners and does not disappear under reasonable edge-decay assumptions. True Forward OOS evidence should receive substantially more weight than additional historical tuning.

## 40% Forward target

The 40% Forward CAGR target is a planning objective, not a backtest acceptance threshold. Historical CAGR must not be translated directly into expected Forward CAGR. Edge-retention stress, tax drag, concentration dependence, theme dependence, execution costs, and future True Forward OOS observations must all be incorporated before stating a central Forward CAGR estimate.

At this freeze, the evidence supports describing Fixed60 as materially closer to a defensible 40% Forward target than W70, but does not support claiming a central Forward CAGR of 40% or higher. The key unresolved empirical requirement is Fixed60-specific True Forward OOS evidence after 2026-08-30.
