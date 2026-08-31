# Fixed60 Forward CAGR haircut framework — 2026-08-31

## Purpose

Estimate a conservative **after-tax Forward CAGR scenario range** for the frozen Fixed60 strategy without treating the 2020–2026 backtest CAGR as a direct forecast.

This is a scenario framework, not a statistically calibrated probability forecast. True Forward OOS remains the primary evidence source from the freeze date onward.

## Historical anchor

Authoritative Fixed60 historical after-tax CAGR through 2026-08-25: **50.65%**.

This value is retrospective and is not used directly as a Forward expectation.

## Empirical stress anchors already observed

- +1 execution session delay: **45.33%** after-tax CAGR
- 30 bp per side cost stress: **41.20%**
- Start at 2021-01 instead of 2020-01: **41.34%**
- Pair-removal stress p10 across C(29,2)=406 removals: **38.47%**
- Rolling 36-month after-tax CAGR p25: **38.40%**
- Rolling 36-month after-tax CAGR p10: **29.10%**

Median of these six empirical stress anchors: **39.84%**.
Mean: **38.97%**.

## Why the empirical stress center is still too high for a Forward point estimate

The stress tests are all generated from the same broad 2020–2026 research sample used during strategy development. They capture execution, concentration, start-date and rolling-window fragility, but they do **not** fully price in:

1. strategy-selection bias from repeated research on the same historical period;
2. regime dependence of the 2020–2026 sample;
3. uncertainty in whether the strongest historical winners and sector structure recur;
4. unknown future tax, slippage and market microstructure effects beyond the tested cases;
5. absence of accumulated True Forward OOS after the Fixed60 freeze.

Accordingly, a second-stage non-statistical selection/regime haircut is required.

## Forward scenario range

### Optimistic scenario: 40% after tax

Use the empirical stress-center cluster (~39–40%) with essentially no additional selection haircut.

Interpretation: historical edge transfers unusually well and future execution remains close to the tested environment.

### Base scenario: 30% after tax

Apply roughly a **10 percentage-point selection/regime haircut** to the empirical stress-center (~39.8%). Round to 30% rather than implying false precision.

Interpretation: substantial alpha survives, but roughly one quarter of the stress-adjusted historical CAGR is lost in Forward transfer.

### Conservative scenario: 20% after tax

Apply an additional ~10 percentage-point deterioration from the base case.

Interpretation: the strategy remains profitable but the 2020–2026 edge was materially regime- and winner-dependent.

## Current working range

**20% / 30% / 40% after-tax CAGR** = conservative / base / optimistic Forward scenarios.

The **30% base case is a planning center, not an estimate with calibrated confidence intervals**. The 40% figure remains the strategy objective, not the current central forecast.

## Updating rule

Do not change the scenario center because of one or two favorable/unfavorable trades. Update only when enough True Forward OOS evidence accumulates under the frozen rule and predeclared evaluation protocol.

The Forward range should eventually be replaced by an OOS-driven estimate rather than further mining of the 2020–2026 sample.
