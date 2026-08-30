# Fixed60 Forward Candidate Specification — 2026-08-30

## Status

Research allocation candidate only. This document corrects the earlier 2026-08-30 interpretation that a robustness-scenario proxy established a Forward CAGR above 40%. That interpretation is withdrawn. Production/main is unchanged.

## Core rule under evaluation

- Start from the existing Production strategy configuration and state machine.
- Momentum remains Production `0/20/80`.
- Top1 / Top2 allocation is fixed at `60/40` when two securities are held.
- Market gate, Stop 17.5%, Circuit 15%, Recovery 10 closes, eligibility rules, PIT universe construction, and next-session-open execution remain Production-aligned.
- No leverage; gross exposure 0–100%.
- No shorting, options, margin, or post-hoc theme override.

## Allocation search boundary

The historical allocation neighborhood has already been inspected. Do not continue refining 60/40 with nearby weights merely to improve the same-sample CAGR. Fixed60 remains the allocation candidate, but the 40% Forward target has **not** been met. Further research should seek economically independent alpha rather than reopen local allocation tuning.

## Historical evidence

Fixed60 historical gross CAGR is approximately 62.0%, versus Production approximately 55.25% and W70 approximately 59.0%. The annual realized-P&L tax approximation produced approximately 50.65% after-tax CAGR for Fixed60. Historical MaxDD was approximately -31.1% gross.

These are historical/pseudo-OOS research results, not a Forward expected CAGR and not Fixed60-specific True Forward OOS.

Leave-one-symbol-out research reduced but did not remove winner dependence. MU and NVDA remained important. A post-hoc semiconductor/hardware group exclusion reduced Fixed60 gross CAGR below 40%; that test is descriptive stress only and must not be converted into a semiconductor-specific optimization rule.

## Allocation-only anchored walk-forward falsification

The pre-existing fixed allocation grid `[0.5, 0.6, 0.7, 0.8, 0.9, 1.0]` was rerun without refining it. Fixed60 slightly underperformed 50/50 in the reported 2023 slice, then was the training-Calmar choice in the three latest expanding windows and beat 50/50 in the following 2024, 2025, and 2026-partial slices.

This supports allocation stability but remains historical pseudo-OOS because the broader architecture was developed with historical information. It does not establish an expected Forward return.

## Structural edge-retention stress

Descriptive Fixed60 counterfactual results:

- 100% edge retention: gross CAGR ~62.03%.
- 90%: ~54.51%.
- 85%: ~50.88%.
- 80%: ~47.33%.
- 75%: ~43.87%.
- 70%: ~40.49%.
- 50%: ~27.75%.

These are sensitivity points, not probabilities or a calibrated predictive model. The same test gave W70 ~41.88% at 75% retention. Fixed60 therefore has somewhat greater historical structural margin than W70, but this cannot be translated directly into a Forward center.

## Robustness perturbation test

Run `33303244408` evaluated 23 predeclared falsification/sensitivity perturbations while keeping Fixed60 as the candidate. Baseline gross CAGR was ~61.998%; stressed gross CAGR ranged from ~34.34% to ~63.95%, with p25 ~51.46% and median ~57.64%.

Important fragilities included two-session execution delay (~46.28% full sample but ~16.55% in 2024–2026), signal two sessions early (~40.37% full sample and ~29.85% late), and 100 bp/side transaction cost (~34.34%).

The scenarios are **not a probability distribution**. Therefore the previously used calculation `stress p25 × historical after-tax/Gross ratio = 42.04%` is not an accepted Forward estimator. The earlier claim that this crossed the 40% Forward threshold is withdrawn. Apparent stress winners such as Stop 15.75%, Recovery 9, or momentum 0/15/85 remain non-adoptable post-hoc observations.

## Authoritative Forward planning framework

The project handoff established Production's Forward planning center at approximately **25%**, based on a subjective Forward distribution informed by regime dependence, structural edge-decay, winner/theme dependence, and other robustness evidence. It explicitly states that historical CAGR must not be placed directly into Forward expectations; only incremental candidate edge should be evaluated, with transfer discounting.

On that same scale:

- Production historical gross CAGR: ~55.25%.
- Fixed60 historical gross CAGR: ~61.998%.
- Historical Fixed60 increment over Production: ~+6.75 percentage points.
- Even an intentionally generous 100% transfer of that historical increment to the 25% Production planning center gives only ~31.75% gross Forward planning CAGR before any transfer haircut.

The handoff further estimated that an after-tax Forward CAGR near 40% would require roughly **50% gross Forward CAGR**. Therefore Fixed60 allocation improvement alone does not justify the target.

No formal posterior has yet been fitted. The ~25% base and any updated planning center must be described as planning judgments rather than statistically calibrated expected returns.

## Recovery bridge

QQQ50 Recovery K1 remains an optional research overlay and is not used to claim the 40% Forward target. K1 improved historical results, while K3/K5 did not preserve the improvement, so timing sensitivity remains material.

## Forward clock

Fixed60 was identified using historical information on 2026-08-30.

- Rule identification/freeze for shadow tracking: 2026-08-30.
- First eligible signal after identification: 2026-08-31 close.
- First eligible execution: 2026-09-01 next US-session open, if executable.
- No historical Fixed60 state is carried into its shadow series.
- Before a post-freeze observation exists, use `TRUE_FORWARD_ELIGIBLE`, not 'True Forward result'.

Research-only shadow implementation:

- `scripts/fixed60-forward-shadow.ts`
- `.github/workflows/fixed60-forward-shadow.yml`

## Research decision

Fixed60 remains the preferred allocation candidate relative to Production/W70 on the historical evidence, but **the Forward 40% target is not met** under the authoritative planning framework. Local allocation/threshold tuning should not resume merely to force the target. The next research stage is an independent PIT alpha engine that can improve security selection and demonstrate stable early/late transfer before integration.

Production/main remains unchanged pending separate approval.
