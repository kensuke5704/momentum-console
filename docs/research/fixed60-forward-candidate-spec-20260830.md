# Fixed60 Forward Candidate Specification — 2026-08-30

## Status

Research candidate frozen on 2026-08-30 after the predeclared robustness-planning rule crossed the 40% Forward planning threshold. This freeze applies to the research specification only. It does not change Production/main.

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

The subsequent robustness test deliberately perturbed execution timing, signal date, transaction cost, Stop/Circuit/Recovery parameters, momentum weights, and universe membership. Those perturbations were falsification tests, not candidate searches. Apparent winners such as Stop 15.75%, Recovery 9 days, or momentum 0/15/85 must not be adopted from this sample after observing their results.

## Historical evidence at freeze

Fixed60 historical gross CAGR was approximately 62.0%, versus approximately 59.0% for W70, with slightly better gross MaxDD. The annual realized-P&L tax approximation produced approximately 50.65% after-tax CAGR for Fixed60 versus approximately 48.18% for W70. These are historical/pseudo-OOS research results, not True Forward OOS.

Leave-one-symbol-out research showed materially reduced single-winner dependence versus W70, but dependence remains. MU and NVDA removals were the two strongest single-name stresses, and a post-hoc semiconductor/hardware group removal reduced Fixed60 gross CAGR below 40%. That group-removal test is descriptive stress only and must not be converted into a semiconductor-specific optimization rule.

## Allocation-only anchored walk-forward falsification

A pre-existing allocation walk-forward was rerun without expanding its fixed grid `[0.5, 0.6, 0.7, 0.8, 0.9, 1.0]`. At each split, the highest training-only Calmar weight is selected and then observed in the following calendar year. This remains historical pseudo-OOS because architecture hindsight remains; it is not True Forward OOS and is used only as a falsification/stability check for the already-frozen 60/40 rule.

- Training through 2021 selected 50/50 for 2022; all tested rules were flat in the reported 2022 OOS slice.
- Training through 2022 selected 50/50 for 2023. Fixed60 produced 100.40% reported OOS CAGR versus 102.95% for 50/50, a small underperformance.
- Training through 2023 selected Fixed60 for 2024. Fixed60 produced 77.99% versus 66.85% for 50/50.
- Training through 2024 selected Fixed60 for 2025. Fixed60 produced 27.56% versus 21.88% for 50/50.
- Training through 2025 selected Fixed60 for the 2026 partial-year OOS slice. Fixed60 produced 82.07% annualized versus 58.09% for 50/50; this short partial-year annualization is descriptive only.

Thus Fixed60 was the training-Calmar choice in the three latest expanding windows, and its following-period result beat 50/50 in each of those three slices. The earlier 2023 slice slightly favored 50/50. This does not prove 60/40 is optimal, but it fails to falsify the frozen Fixed60 candidate and argues against the result being solely a full-sample allocation artifact. The weight grid must not now be refined on the basis of these outcomes.

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

The same stress was rerun on W70 using the identical regime definition and sample. W70 baseline gross CAGR was 59.00%; 80% retention produced 45.15%, 75% retention produced 41.88%, and the next tested point, 50%, produced 26.60%. On the fixed grid, W70 therefore required 75% retention to remain above 40%, versus 70% for Fixed60. This relative comparison supports greater structural margin for Fixed60, but both series remain descriptive counterfactuals rather than calibrated Forward forecasts.

## Predeclared robustness stress and planning proxy

After the user-defined decision rule was set — freeze the specification if the predicted/Forward planning CAGR exceeds 40%, otherwise continue condition research — a robustness test was specified before its results were read. Fixed60 remained 60/40 in every scenario. The test varied execution delay, signal date, transaction costs, risk thresholds, Recovery confirmation, momentum weights, and deterministic 10% universe dropout. The best scenario is not used as a new strategy.

Research run: `33303244408`.

Across 23 non-baseline perturbations:

- Baseline Fixed60 gross CAGR: 61.998%.
- Minimum stressed gross CAGR: 34.336%.
- 25th-percentile stressed gross CAGR: 51.464%.
- Median stressed gross CAGR: 57.639%.
- 75th percentile: 59.611%.
- 95.65% of scenarios remained above 40% gross CAGR.
- 82.61% remained above 50% gross CAGR.

Important fragilities remain:

- One-session execution delay: 55.29% full-sample gross CAGR, but only 38.11% in the 2024–2026 slice.
- Two-session execution delay: 46.28% full-sample gross CAGR and only 16.55% in the 2024–2026 slice.
- Moving the signal two sessions earlier: 40.37% full-sample gross CAGR and 29.85% in the 2024–2026 slice.
- A deterministic 10% universe-dropout realization produced 34.33% CAGR in the 2024–2026 slice despite 54.80% over the full sample.
- 100 bp per-side transaction cost reduced full-sample gross CAGR to 34.34%; 50 bp per side still produced 45.96%.

Before reading these results, the Forward planning center was fixed as:

`25th-percentile robustness Gross CAGR × historical Fixed60 after-tax/Gross CAGR ratio`.

Using 51.464% for the robustness 25th percentile, approximately 50.65% historical after-tax CAGR, and 61.998% historical gross CAGR gives an after-tax/Gross ratio of approximately 81.70% and a Forward planning center of approximately **42.04% CAGR**.

This 42.04% value is a conservative planning proxy, not a statistically calibrated expected return, confidence bound, or True Forward OOS estimate. The robustness scenarios are not a probability distribution and receive equal weight only to construct the precommitted sensitivity proxy. The margin above the 40% target is approximately 2.0 percentage points, so the target should be treated as met narrowly rather than with a large safety margin.

Because this precommitted planning proxy exceeds 40%, historical condition search is closed. The frozen research specification remains the original Fixed60 rule: Production 0/20/80 momentum, 60/40 Top1/Top2 allocation, Production Stop 17.5%, Circuit 15%, Recovery 10 days, standard next-session-open execution, and the existing transaction-cost convention. No post-hoc robustness winner is substituted.

## Recovery bridge

The QQQ50 Recovery bridge remains an optional research overlay, not part of the Fixed60 core rule.

- K1 improved historical Fixed60 performance.
- K3 and K5 did not preserve that improvement.
- Therefore the bridge retains timing sensitivity and is excluded from the 42.04% planning center.
- If monitored forward, use the already frozen QQQ50 K1 bridge lifecycle specification; bridge P&L must not feed the Production Stop/Circuit state machine.

## Forward clock

Fixed60 was identified using historical information on 2026-08-30. Therefore historical data before this freeze date cannot be called True Forward OOS for Fixed60.

- Rule freeze: 2026-08-30.
- First eligible US signal session after freeze: 2026-08-31 close.
- First eligible execution: 2026-09-01 next US-session open, if the frozen strategy generates an executable position.
- The Fixed60 shadow starts from a fresh state after freeze; no historical Fixed60 state is carried into the shadow series.
- The broader strategy's previously established True Forward OOS start date remains a separate record and must not be retroactively attributed to Fixed60.
- Forward observations must be logged without changing Fixed60 allocation or adding post-hoc filters because of early outcomes.

## Forward shadow implementation

Research-only implementation:

- `scripts/fixed60-forward-shadow.ts`
- `.github/workflows/fixed60-forward-shadow.yml`

The workflow rebuilds the PIT universe through completed signal months and refreshes Yahoo market data inside the ephemeral runner before evaluating the frozen Fixed60 rule. It uploads a research artifact and does not commit refreshed data or modify Production/main.

A verification run on 2026-08-30 refreshed market data through 2026-08-28 and found the latest completed PIT universe signal at 2026-07-31. The Fixed60 result correctly reported `oosClass=TRUE_FORWARD_ELIGIBLE`, `hasObservations=false`, `asOf=null`, and zero return observations. This is the correct temporal state before the 2026-08-31 close signal can exist; it is not a missing-data failure.

Before a post-freeze return exists, the result is labeled `TRUE_FORWARD_ELIGIBLE` with `hasObservations=false`; it must not be described as a True Forward OOS result. Once the first eligible next-open execution and subsequent market observation exist, only those post-freeze observations qualify as Fixed60-specific True Forward evidence.

## Forward evaluation

Primary forward comparison:

1. Production rule as actually deployed at the time.
2. Frozen Fixed60 research shadow portfolio.
3. Optional Fixed60 + frozen QQQ50 K1 bridge shadow portfolio, reported separately.

Track at minimum cumulative return, annualized return when meaningful, MaxDD, realized volatility, turnover, transaction costs, tax-relevant realized gains/losses when available, exposure, monthly hit rate, and attribution by symbol/theme. Do not annualize very short samples as a decision metric.

## Candidate decision rule

Fixed60 is now frozen as the current research target specification because the precommitted Forward planning proxy is approximately 42.04%, above the 40% target. This is not a Production promotion decision. Promotion to Production requires separate approval and should place substantially greater weight on accumulating True Forward OOS evidence than on any additional historical analysis.

## 40% Forward target

The current planning center is approximately **42.04% CAGR**, narrowly above the 40% planning objective. It should not be represented as a guaranteed return or a statistically estimated expectation. The downside stresses explicitly show plausible historical counterfactuals below 40%, especially under severe execution delay, high transaction costs, and adverse recent-period universe/signal perturbations.

Historical parameter tuning and condition search are now closed for Fixed60. The next source of decision-relevant evidence is Fixed60-specific True Forward OOS data after the 2026-08-30 rule freeze.
