# Fixed60 Research Candidate Specification — 2026-08-30

## Status

- Research candidate only. This document does not change Production/main.
- Frozen on 2026-08-30 after a coarse, predeclared allocation comparison among Fixed60 / Fixed65 / Fixed70 and subsequent robustness checks.
- Historical and pseudo-OOS results before this freeze are not true ex-ante OOS for Fixed60.
- Fixed60-specific True Forward OOS begins only after this freeze.

## Core rule

Fixed60 changes only Top2 capital allocation relative to the existing Production architecture:

- Rank 1: 60%
- Rank 2: 40%
- No concentration override; both normal and concentrated states use 60/40.
- No leverage. Gross exposure remains 0–100%.
- All other Production selection, universe, market gate, Stop/Circuit, Recovery, transaction-cost and next-session-open execution rules remain unchanged unless separately frozen in another research specification.
- Historical transaction-cost assumption: 10 bp per side, inherited from the existing strategy configuration.

## Anti-mining constraint

- Do not refine the allocation around 60% after observing these historical results.
- In particular, do not search 55%, 57.5%, 62.5%, or other nearby weights to maximize backtest CAGR.
- Fixed60 is retained because it was one of the coarse predeclared comparison points and showed better robustness than W70, not because 60% is asserted to be a smooth mathematical optimum.

## Historical evidence available at freeze

Historical evidence is diagnostic only and contains architecture/selection hindsight.

- Gross CAGR: approximately 62.0%.
- Gross MaxDD: approximately -31.1%.
- Simplified after-tax CAGR: approximately 50.65%.
- Simplified after-tax MaxDD: approximately -37.37%.
- Simplified after-tax terminal equity: approximately 15.22x.
- Early 2020–2023 gross CAGR: approximately 64.79%.
- Late 2024–2026 gross CAGR: approximately 57.89%.

Leave-one-selected-ticker-out, after-tax historical counterfactual:

- Median CAGR: approximately 50.33%.
- p25 CAGR: approximately 47.65%.
- p10 CAGR: approximately 44.86%.
- Below 40%: 2 of 29 cases.
- Worst notable cases: MU approximately 36.82%, NVDA approximately 38.76%, HOOD approximately 42.98%.

Theme stress remains a material weakness:

- Removing semiconductor/hardware names post hoc reduced gross CAGR to approximately 37.31%.
- This diagnostic must not be used to invent a semiconductor-specific timing or exclusion rule after the fact.

## Structural edge-retention stress

The predeclared descriptive stress reduces the historical mean return earned on days classified as a favorable QQQ regime while preserving the residual historical return path. It is a sensitivity test, not a calibrated probability model and not a state-machine rerun.

Observed Fixed60 gross CAGR under favorable-regime edge retention:

- 100%: 62.03%
- 90%: 54.51%
- 85%: 50.88%
- 80%: 47.33%
- 75%: 43.87%
- 70%: 40.49%

Therefore the coarse stress grid stays above 40% gross through 70% edge retention. This does not imply 70% is a forecast or that after-tax CAGR would remain above 40% at the same point.

## Tax interpretation

The historical simplified after-tax CAGR is approximately 50.65%. A simple CAGR-ratio heuristic implies that 40% after tax would require about 79.0% retention of the historical after-tax CAGR. This ratio is not an exact tax stress and must not be presented as one.

The tax model currently approximates Japanese taxable-account drag using 20.315% annual realized stock P&L taxation with three-year loss carry. It does not reproduce exact broker tax lots, withholding timing, NISA treatment, foreign withholding, or every account-specific mechanic.

## Recovery QQQ50 bridge

- The Recovery QQQ50 K1 bridge is not part of the Fixed60 core planning estimate.
- Historical Fixed60 exact-lifecycle gross results were approximately: base 62.00%, K1 64.64%, K3 61.01%, K5 59.96%.
- Because K1 improves while K3/K5 deteriorate, timing fragility remains material.
- Do not add the K1 historical uplift to the central Forward CAGR estimate.
- If the bridge is pursued with Fixed60, freeze a separate Fixed60 bridge specification before counting any subsequent observations as Fixed60+bridge True Forward OOS.

## Forward evaluation rule

Fixed60 is a candidate for the user's 40% Forward CAGR objective, not a confirmed 40% strategy.

Forward assessment must use ranges and retention/stress evidence rather than the historical 50.65% after-tax CAGR as a point forecast. The central case must exclude unproven alpha overlays and the K1 bridge uplift.

Promotion to Production requires separate approval after sufficient Fixed60-specific True Forward OOS evidence and operational review. Until then Production/main remains unchanged.
