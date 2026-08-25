# Expected CAGR Model — Initial Result

Date: 2026-08-26 JST
Run: `32863633662` (success)
Strategy: `momentum-dynamic-2026-08-v1`
Sample: 2020-01-02 through 2026-08-25, 1,670 trading days / 80 months.

## Purpose

Estimate long-run geometric growth from realized Production returns **without CPCM** and without an external expected-return prior.

This is an empirical expected-growth estimate, not a calibrated structural forecast.

## Main estimator

- Monthly portfolio log returns reconstructed using the current Production state machine.
- Center: Huber M-estimator of monthly log returns (`k=1.5`).
- Annualization: `exp(12 * robust monthly log mean) - 1`.
- Sampling uncertainty: 3-month moving-block bootstrap, 20,000 resamples.

### Result

- Robust empirical point estimate: **41.96% CAGR**.
- Central 50% bootstrap interval: **30.06% to 57.89%**.
- Central 90% bootstrap interval: **11.86% to 80.97%**.

The bootstrap interval is conditional on the observed 2020-2026 regime mix. It is **not** a full future-regime prediction interval.

## Cross-checks

- Realized annualized geometric growth from daily logs: **55.47%**.
- Realized annualized geometric growth from monthly logs: **55.02%**.
- 10% winsorized monthly-log estimate: **39.73%**.
- Leave-one-year-out robust estimates:
  - exclude 2020: 37.71%
  - exclude 2021: 46.28%
  - exclude 2022: 51.76%
  - exclude 2023: 31.70%
  - exclude 2024: 36.69%
  - exclude 2025: 45.23%
  - exclude 2026: 36.26%
- Leave-one-year-out median: **37.71%**; range: **31.70% to 51.76%**.

The robust monthly estimator, winsorized estimator, and leave-one-year-out median therefore cluster around roughly **38-42%** despite different treatments of winner concentration.

## Exposure decomposition

Exact realized daily-log identity:

`E[daily log growth] = exposure share × E[log return | exposed] + cash share × E[log return | cash]`

Current reconstruction:
- Exposure share: **51.53%**.
- Raw annualized return conditional on exposed days: **135.47%**.
- Huber-robust annualized conditional exposed-day return: **134.86%**.
- Cash-period return: 0% in the current backtest accounting.
- Raw factorized annualized growth: **55.47%**.
- Daily-Huber factorized annualized growth: **55.26%**.

Daily-level Huber barely changes the estimate because the realized right-tail dependence is not just a handful of isolated extreme daily observations; it is expressed through sustained multi-day/month winner episodes. Therefore monthly robustification is more informative for expected-growth shrinkage.

Risk controls, recovery behavior, execution costs, and transaction costs are already embedded in the Production equity path. They are not added as a separate forecast adjustment in v1.

## Interpretation / operating estimate

Use two numbers distinctly:

- **Model point estimate:** 41.96% expected geometric CAGR under the robust empirical estimator.
- **Working planning estimate:** approximately **40% CAGR**, reflecting the 41.96% Huber estimate, 39.73% winsorized estimate, and 37.71% leave-one-year-out median.

Do **not** describe 40-42% as a known true expected CAGR. The current sample is only 80 months and is strongly regime- and winner-dependent.

The old CPCM 26.04% median is not used in this estimate and should not be blended into it as a pseudo-prior.

## Forward OOS

`public/data/oos-performance.json` currently has no completed OOS return/equity history beyond the initial 2026-08-25 equity=1 state. Therefore OOS receives zero weight in this initial estimate. As completed OOS months accumulate, the expected-growth model should be updated to report Historical and OOS evidence separately before considering any combination.

## Status

**INITIAL EMPIRICAL EXPECTED CAGR MODEL ACCEPTED FOR MONITORING, NOT YET A CALIBRATED FORECAST MODEL.**

Production strategy/config remains unchanged.
