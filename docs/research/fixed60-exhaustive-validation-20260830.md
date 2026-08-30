# Fixed60 Exhaustive Validation Report — 2026-08-30

## Scope and decision discipline

This report consolidates the validations that can be performed with the currently available PIT universe, stored market data, free research data routes, and the frozen Fixed60 candidate as of 2026-08-30.

Fixed60 remains fixed at Top1/Top2 = 60/40. The tests below are falsification/robustness tests only. Better-looking perturbations are not promoted into the strategy. Historical and pseudo-OOS results before the 2026-08-30 freeze are not Fixed60-specific True Forward OOS.

The simplified tax approximation used below is 20.315% annual realized stock P&L taxation with three-year loss carry. It is not exact Japanese broker withholding/tax-lot accounting and does not compute each taxable transaction in JPY.

## Baseline

- Historical gross CAGR: 61.9981%
- Historical gross MaxDD: -31.13%
- Simplified after-tax CAGR: 50.6469%
- Simplified after-tax MaxDD: -37.37%
- Simplified after-tax final equity: 15.22x

These are historical diagnostics, not Forward expected values.

## Data/PIT integrity audit

Current stored dataset:

- PIT universe months: 79
- First universe as-of: 2020-01-31
- Last universe as-of: 2026-07-31
- Market-data symbols: 249
- Monthly signals checked: 79

All audited counts were zero:

- future-dated source filings
- duplicate universe members
- invalid/duplicate universe ranks
- universe oversize
- non-monotone universe dates
- duplicate price dates
- non-monotone price dates
- selected symbols missing signal-close prices
- selected symbols missing next-session-open prices

No explicit stored-data lookahead or selected-price gap was detected by these checks.

Limitation: the current PIT universe begins in January 2020. A like-for-like 2010s test cannot be run from the current universe history without reconstructing an older PIT universe from additional historical source data.

## Structural edge-retention sensitivity

Descriptive gross CAGR after reducing the historical favorable-regime mean edge while preserving the residual path:

| Edge retention | Gross CAGR |
| ---: | ---: |
| 100% | 62.03% |
| 90% | 54.51% |
| 85% | 50.88% |
| 80% | 47.33% |
| 75% | 43.87% |
| 70% | 40.49% |
| 50% | 27.75% |

This is not a calibrated probability distribution and does not rerun the state machine on synthetic prices.

## Local parameter fragility, after tax

Predeclared local perturbations all remained above 40% simplified after-tax CAGR:

| Case | After-tax CAGR |
| --- | ---: |
| Baseline | 50.65% |
| Stop 15.75% | 51.54% |
| Stop 19.25% | 48.76% |
| Circuit 13.5% | 45.83% |
| Circuit 16.5% | 48.34% |
| Recovery 9 | 48.30% |
| Recovery 11 | 46.99% |
| Momentum 0/15/85 | 51.35% |
| Momentum 0/25/75 | 50.42% |
| Momentum 10/20/70 | 48.96% |

The better historical values are not adopted. This result supports local parameter stability but does not validate the parameters ex ante.

## Rolling after-tax CAGR

Rolling windows calculated from the historical simplified after-tax equity curve:

| Window | p10 | p25 | Median | Share >=40% | Minimum |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 year / 252 sessions | 4.70% | 28.66% | 52.47% | 67.0% | -23.72% |
| 2 years / 504 sessions | 24.19% | 36.34% | 44.83% | 68.3% | 6.37% |
| 3 years / 756 sessions | 32.69% | 38.40% | 45.44% | 69.8% | 24.03% |

This is a material caution: even three-year historical start windows did not consistently exceed 40% after tax.

Annual simplified after-tax returns were approximately:

- 2020: +100.31%
- 2021: +45.76%
- 2022: 0.00%
- 2023: +87.71%
- 2024: +75.39%
- 2025: +25.17%
- 2026 partial: +32.06%

## Regime dependence

Using the existing descriptive favorable regime (QQQ above 200DMA and 20-day realized volatility below 30%):

- Favorable-regime days: 74.1% of tested days; after-tax-path CAGR-equivalent approximately 72.44%.
- Other days: 25.9%; CAGR-equivalent approximately 2.84%.

This demonstrates strong regime dependence. The return source is not evenly distributed through time.

## Transaction-cost stress, after tax

| Cost per side | After-tax CAGR |
| ---: | ---: |
| 10 bp | 50.65% |
| 20 bp | 48.27% |
| 30 bp | 41.20% |
| 50 bp | 36.72% |
| 100 bp | 26.34% |

The historical 40% after-tax threshold survives through 30 bp/side but not 50 bp/side.

## Execution-delay stress, after tax

| Additional execution delay | After-tax CAGR |
| ---: | ---: |
| 0 sessions | 50.65% |
| +1 session | 45.33% |
| +2 sessions | 38.03% |

The edge is materially timing-sensitive. A two-session execution delay breaks the historical 40% after-tax threshold.

## Signal-date perturbation, after tax

This test shifts the monthly PIT universe/signal date as a robustness perturbation; it is diagnostic rather than a proposed alternate implementation.

| Signal shift | After-tax CAGR |
| ---: | ---: |
| -2 sessions | 32.73% |
| -1 session | 41.32% |
| baseline | 50.65% |
| +1 session | 44.54% |

Exact month-end timing matters. Two sessions earlier materially degrades the result.

## Start-date dependence, after tax

| Backtest start | After-tax CAGR |
| --- | ---: |
| 2020-01 | 50.65% |
| 2020-04 | 57.14% |
| 2020-07 | 48.63% |
| 2021-01 | 41.34% |

The tested starts remain above 40%, but the margin is small from a 2021 start.

## PIT-universe dropout stress, after tax

Each monthly PIT universe was randomly reduced using deterministic predeclared seeds, followed by full reselection.

- 5% dropout, 10 seeds: minimum 43.18%, p10 46.45%, p25 48.43%, median 50.75%; 10/10 above 40%.
- 10% dropout, 10 seeds: minimum 37.95%, p10 44.26%, p25 46.37%, median 49.57%; 9/10 above 40%.

Moderate constituent availability noise is generally tolerated, but 10% dropout can break 40% in a historical realization.

## Ranking-noise stress, after tax

A predeclared 5% or 10% probability of replacing rank 2 with rank 3 was applied using deterministic seeds.

- 5% noise, 10 seeds: minimum 45.35%, p10 48.15%, p25 49.96%, median 50.65%; 10/10 above 40%.
- 10% noise, 10 seeds: minimum 46.67%, p10 47.31%, p25 48.50%, median 50.18%; 10/10 above 40%.

Small rank-order errors are not a major historical fragility in this test.

## All two-selected-ticker removals, after tax

Every pair among the 29 historically selected non-QQQ symbols was removed from every PIT universe month, with full reselection. All 406 pairs were tested.

Distribution of simplified after-tax CAGR:

- minimum: 24.14%
- p10: 38.47%
- p25: 44.73%
- median: 48.40%
- p75: 51.19%
- pairs below 40%: 54 / 406
- share at or above 40%: 86.70%

Worst cases included:

- MU + NVDA: 24.14%
- FTNT + NVDA: 29.23%
- HOOD + MU: 31.20%
- NET + NVDA: 31.43%
- HOOD + NVDA: 31.70%
- MU + NET: 31.99%

This confirms material winner dependence, especially around MU/NVDA. Fixed60 is more robust than single-winner dependence alone would suggest, but 40% is not independent of the historical winner set.

## Moving-block bootstrap, after tax — secondary only

This preserves local return blocks but not full historical chronology/regime mechanics. It must not be interpreted as a calibrated probability forecast.

- 21-session blocks / 5-year paths: 69.1% of generated paths >=40%; p10 23.62%, p25 36.06%.
- 63-session blocks / 5-year paths: 72.7% >=40%; p10 25.00%, p25 38.56%.
- 21-session blocks / 10-year paths: 75.4% >=40%; p10 31.12%, p25 40.26%.
- 63-session blocks / 10-year paths: 81.7% >=40%; p10 33.60%, p25 43.75%.

These fractions are not probabilities that Fixed60 will achieve 40% Forward CAGR.

## Currency sensitivity

The stored strategy backtest is based on US asset-price returns and does not include an explicit USD/JPY process.

Historical normalized USD-to-JPY wealth conversion over the tested period changed the gross CAGR from about 62.0% in USD to about 71.6% in JPY because USD/JPY moved from approximately 108.7 to 159.2. JPY MaxDD was worse at about -38.3%.

This historical FX tailwind must not be extrapolated. Yen appreciation is a distinct downside risk for a JPY investor. Exact Japanese after-tax JPY accounting remains unresolved because taxable gains should be computed from transaction-level JPY values.

## Other completed falsification/alpha diagnostics

The following candidate overlays/factors have already failed their predeclared or stability gates and are not used to support Fixed60's expected return:

- Overnight Momentum
- Information Gap
- fixed regime-entry gate
- existing nonleveraged dynamic exposure
- N-PORT institutional persistence
- SEC sales acceleration rerank
- margin delta
- SEC filing post-event drift / PEAD-like signal
- insider cluster buying
- FINRA short-sale volume
- Schedule 13D event drift
- 424B5 dilution filter
- signed-volume imbalance

SEC 13F accumulation was not rejected as an economic signal; the available free mirror did not provide historically timely PIT holdings/filing dates for the required early sample, so that route was closed as unavailable for valid historical testing.

Cash/T-bill carry was historically positive but is not alpha and is not counted as evidence that the core strategy reaches 40%.

Recovery QQQ50 K1 remains an optional, separately specified timing-sensitive overlay and is excluded from the core Forward estimate.

## What cannot be validated now

The following are not currently resolvable from the available historical data/model and therefore remain open rather than silently approximated:

1. Fixed60-specific True Forward OOS: the rule was frozen on 2026-08-30, before the first post-freeze US market session.
2. Like-for-like pre-2020 PIT validation: current PIT universe history starts 2020-01-31.
3. Exact Japanese broker-level after-tax CAGR in JPY, including transaction-level FX conversion, precise tax lots/withholding timing and account-specific treatment.
4. Future realized slippage/liquidity for the actual account size.
5. Future regime frequency and whether the historically favorable regime edge retains its historical magnitude.
6. Future availability of historical winner-like opportunities; two-winner removal and theme stress show this is a material source of uncertainty.

## Overall assessment

The completed tests materially strengthen the case that Fixed60 contains a genuine historical edge and is not merely a razor-thin local-parameter optimum:

- PIT/data integrity checks passed.
- Local Stop/Circuit/Recovery/Momentum perturbations all remained above 40% simplified after tax.
- 5% universe dropout and 5–10% rank noise were generally well tolerated.
- Gross structural edge retention remained above 40% down to the 70% grid point.

However, the tests also identify several reasons not to state a high-confidence Forward after-tax CAGR above 40%:

- rolling one-, two-, and three-year historical windows exceeded 40% only about 67–70% of the time;
- 50 bp/side transaction cost reduced after-tax CAGR below 40%;
- a two-session execution delay reduced it below 40%;
- a two-session signal-date shift reduced it well below 40%;
- 54 of 406 two-winner-removal cases fell below 40%, with a 24.14% worst case;
- theme concentration remains material;
- historical JPY results benefited strongly from yen depreciation;
- there are zero Fixed60-specific True Forward observations at the freeze date.

Therefore the correct conclusion as of 2026-08-30 is:

**Fixed60 is the strongest frozen research candidate, and the historical evidence makes a 40% after-tax long-run Forward CAGR plausible, but the available evidence does not justify treating >40% as a high-confidence or established Forward central value.**

Further same-sample parameter optimization would reduce evidentiary quality. The highest-value next evidence is Fixed60-specific True Forward data after the freeze, or a genuinely older PIT universe reconstructed from independent historical source data without changing the frozen strategy.
