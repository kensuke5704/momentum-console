# Execution Feasibility Audit — 2026-08-26

Strategy: `momentum-dynamic-2026-08-v1`
Audit run: `32922160983` (success)
Sample through: 2026-08-25

## Baseline annual returns (10 bp per side)

- 2020: +67.35%
- 2021: +57.05%
- 2022: +0.00%
- 2023: +96.11%
- 2024: +85.32%
- 2025: +21.96%
- 2026 YTD through 2026-08-25: +59.59%

Full-sample baseline: CAGR 55.25%, MaxDD -21.93%, final equity 18.591x.
Transactions: 56 entries / 56 exits.

## Transaction-cost sensitivity

The configured `transactionCost` is applied proportionally on both buys and sells.

- 10 bp/side: CAGR 55.25%, MaxDD -21.93%, final equity 18.591x
- 25 bp/side: CAGR 52.26%, MaxDD -22.28%, final equity 16.337x
- 50 bp/side: CAGR 45.95%, MaxDD -22.86%, final equity 12.334x
- 100 bp/side: CAGR 36.54%, MaxDD -21.18%, final equity 7.921x

The strategy remains profitable and high-growth under materially larger all-in proportional trading costs, so the result is not dependent on exactly 10 bp/side.

## Execution timing audit

- Monthly Top2 signals are computed from information through the signal-date close and scheduled for the next US session open.
- Stop and portfolio circuit triggers are evaluated using the close, then liquidated at the next session open. Overnight gap risk is therefore represented by the next-open execution price.
- Recovery confirmation is based on completed QQQ closes and re-entry is scheduled for the next session open.
- Yahoo raw OHLC is adjusted with the same adjusted-close factor to avoid split-induced false stops and adjusted-close/unadjusted-open inconsistencies.

These timing rules do not use the next open before the decision is made and are operationally implementable in principle with overnight / market-on-open orders.

## Material feasibility gaps

### 1. SEC N-PORT same-day filing timing — unresolved PIT risk

Universe construction accepts source filings when `filingDate <= signalDate`, but the stored Universe metadata contains only the filing date, not the SEC acceptance timestamp. The audit found many signal months containing N-PORT filings whose `filingDate` equals the month-end signal date, including months with large numbers of same-day filings.

Therefore the current backtest cannot prove that every same-day filing was publicly available before that day's market close. Strict point-in-time feasibility is **not yet fully established**. A conservative fix is to require `filingDate < signalDate`, or retain SEC acceptance timestamps and use same-day filings only when accepted before the signal close.

### 2. Exact opening fill / slippage

The backtest uses Yahoo's official adjusted open plus a fixed proportional transaction cost. Real market-on-open fills can differ from the official open, especially in volatile/smaller names. Cost sensitivity partially stress-tests this, but it is not a direct historical slippage model.

### 3. Liquidity / market impact

No ADV, dollar-volume, spread, or participation-rate constraint is currently part of the Production universe or backtest. Therefore feasibility depends on portfolio capital. The current model cannot certify scalability to arbitrary capital sizes.

### 4. Fractional shares and simultaneous rebalance

The engine allocates fractional shares exactly. A broker/account that cannot execute fractional market-on-open orders would have rounding differences. Month-end rebalance also models sell-all and buy-new positions at the same session open with exact proceeds; operational implementation may require a margin account, unsettled-funds support, or a small cash buffer and approximate pre-open sizing.

### 5. Taxes, FX, broker-specific fees

The simulation is a USD strategy-equity simulation. It does not separately model Japanese taxation, NISA/taxable-account treatment, JPY/USD conversion costs, withholding effects, or broker-specific commissions/fees. The 10 bp/side parameter can represent generic transaction friction but does not prove all investor-specific costs are covered.

## Verdict

**Execution timing is broadly realistic and the strategy is robust to much larger proportional trading costs, but the simulation is not yet certified as fully realizable in every respect.**

The largest correctness issue is the unresolved same-day N-PORT filing timestamp/PIT question. Liquidity/market-impact and investor-specific tax/FX/broker costs are also outside the current model.

Production strategy/config was not changed by this audit.
