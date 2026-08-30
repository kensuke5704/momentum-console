# Production console specification audit — 2026-08-30

## Scope

Audit the deployed Momentum Console after promoting Fixed60 to Production. The audit covers strategy configuration, Point-in-Time Universe, Momentum ranking, target allocation, live state machine, execution timing/cost, Forward OOS, backtest metrics, CAGR bootstrap band, monthly return distribution, displayed labels, and scheduled data refresh workflows.

## Production rule frozen in code

- strategyId: `momentum-fixed60-2026-08-v1`
- Dynamic Universe: SEC N-PORT breadth, target 80
- Momentum: 0 / 20 / 80 for 1M / 3M / 6M; 1M is used for the +80% surge exclusion
- Stock score must be above QQQ score
- TopN: 2
- Allocation: fixed 60 / 40
- QQQ market gate: 10-month MA
- Individual stop: 17.5%
- Portfolio circuit: 15.0%
- Recovery: QQQ > 100DMA, QQQ 20D momentum > 0, 10 consecutive closes
- Entry/exit: next US session open
- Transaction cost: 10bp per side
- Backtest start: 2020-01-01
- Fixed60 Forward OOS start: 2026-08-31

## Audit results

### Correct and strategy-linked

- `src/lib/config.ts` is the Production single source of truth.
- Monthly signals and state-machine transitions receive the Production config.
- Backtest strategyId is inherited from the Production config.
- Dashboard rejects frozen backtest/OOS artifacts whose strategyId does not match Production.
- Forward OOS restarts at the Fixed60 freeze boundary instead of carrying the prior strategy series.
- Current Target Portfolio and live positions use 60/40.
- PIT Universe selection uses only filings public by each signal date.
- Daily market-data activation fails closed when required prices are incomplete.
- GitHub Pages refreshes market data after US close and retries before the next US open.
- The monthly Universe job runs after the prior US month-end close and before the next US open.
- CAGR band is rebuilt from the displayed strategy equity curve with the current strategyId.

### Inconsistencies found and corrected

1. The monthly-return chart imported `data/research/nport-delay-monte-carlo.json`, generated under the prior Production strategy. It was therefore not a current Fixed60 monthly-return distribution.
   - Corrected: monthly returns are now derived directly from the displayed Fixed60 backtest equity curve using consecutive month-end equity values.
   - The first partial month is excluded because no prior month-end equity exists.
   - Histogram bins remain 5 percentage points.

2. The Settings tab still stated `Top2・zGap・50/50または70/30`.
   - Corrected: it displays the allocation from `data.config` and therefore shows Fixed 60/40.

3. Several UI labels embedded strategy parameters as literal text (10M, 100DMA, 20D, 17.5%, 15%, 10 closes, 10bp).
   - Corrected: these values are now rendered from `data.config` so a future Production parameter change cannot leave stale labels.

4. Momentum table headers said `3M × 20%` and `6M × 80%` while the cells displayed raw 3M/6M returns.
   - Corrected: headers now state `3M return (20% weight)` and `6M return (80% weight)`.

5. The CAGR band was visually labelled `Expected CAGR` even though the model is explicitly a historical moving-block bootstrap diagnostic.
   - Corrected: display wording now says `Bootstrap CAGR median` and describes it as historical sensitivity, not a calibrated forecast.

6. Empty Fixed60 OOS previously appeared as a 1.00x/0% chart without an explicit no-observation warning.
   - Corrected: the OOS tab now states that Fixed60 Forward OOS begins 2026-08-31 and currently has no observations when `asOf` is null.

## Known non-errors / limitations

- `public/data/backtest-frozen.json` can still contain the previous strategy until a Fixed60 freeze snapshot is explicitly written. The dashboard intentionally ignores it when the strategyId differs, so it does not contaminate the displayed Fixed60 backtest.
- Historical PIT Universe currently starts in 2020; the site cannot display a same-specification pre-2020 backtest without new PIT data.
- Latest display-only quotes are separate from signal/backtest prices and are not used for strategy decisions.
- The CAGR bootstrap band and historical monthly-return histogram are diagnostics, not Forward-return forecasts.

## Acceptance checks

- No displayed monthly-return data may depend on the old N-PORT-delay Monte Carlo artifact.
- No visible allocation text may say 50/50 or 70/30 under Fixed60 Production.
- Strategy parameter labels should render from config wherever practical.
- Test/typecheck/lint/build must all pass before closing this audit.
