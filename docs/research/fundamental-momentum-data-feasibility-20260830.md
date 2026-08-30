# Fundamental Momentum data feasibility — 2026-08-30

## Objective
Evaluate whether EPS / revenue estimate revisions can be added to Hybrid 60→70 without look-ahead bias, using point-in-time (PIT) data from 2020 onward.

## Hard validity requirement
For every strategy signal close `t`, any analyst-estimate observation used by the ranking must have an effective / observation timestamp `<= t`. A current consensus value attached to an old fiscal period is not sufficient. Historical actual-vs-estimate earnings surprise data is also not a substitute for revision history.

## Sources checked

### Zacks historical consensus / revisions
- Zacks states that it maintains historical consensus estimates: annual EPS back to 1979, quarterly EPS from 1982, and sales estimates from 2000.
- Delivery is available via API / bulk files / partner DaaS; individual-investor access is offered through Nasdaq Data Link and Intrinio.
- Nasdaq Data Link lists Zacks Earnings Estimates (ZEE) as Premium.
- Intrinio exposes Zacks EPS Estimates with `start_date` / `end_date`, making date-scoped historical retrieval structurally suitable.

Assessment: **Suitable for strict PIT research, but not presently accessible in this repository without a subscription/API entitlement.**

### S&P Capital IQ Estimates Snapshot
- Explicitly offers point-in-time estimate history and effective-date fields, with history since 2016.

Assessment: **Suitable for strict PIT research, commercial data.**

### Alpha Vantage EARNINGS_ESTIMATES
- Documentation says it returns annual/quarterly EPS and revenue estimates, analyst count and revision history.
- Public documentation does not establish that the endpoint exposes a complete historical sequence of timestamped consensus snapshots sufficient to reconstruct every 2020–2026 signal date.
- Endpoint requires an API key; no Alpha Vantage integration/key is present in this repository.

Assessment: **Do not use for the historical walk-forward unless timestamped PIT coverage is independently verified.**

### Other free/current APIs
Several free/current estimate endpoints expose current forward consensus, EPS trend, or recent revisions. These are useful live indicators but do not by themselves reconstruct what the market knew at historical signal dates.

Assessment: **Not valid for the requested 2020–2026 historical walk-forward.**

## Result
A rigorous Fundamental Momentum validation is **data-access blocked, not empirically rejected**. No backtest should be run by retroactively applying today's analyst estimates to past dates.

## Proposed predeclared factor once PIT data is available
Keep Production eligibility / QQQ gate / risk engine / execution unchanged and Hybrid allocation 60/40→70/30 unchanged.

For each eligible symbol at each monthly signal close:
1. Select the latest forward FY1 and/or NTM consensus snapshot available at or before the signal close.
2. Compare with the latest snapshot at least 20 trading days earlier (prefer 30 calendar days where source timestamps permit).
3. Compute:
   - `EPS_REV = (EPS_now - EPS_prev) / max(abs(EPS_prev), floor)` with sign-safe handling around zero;
   - `REV_REV = (Revenue_now - Revenue_prev) / abs(Revenue_prev)`;
   - optionally revision breadth = upgrades / total revisions where source supplies analyst-level revision counts.
4. Cross-sectionally winsorize only using information available on that signal date, then z-score within the eligible universe.
5. Test only predeclared blends:
   - `FUND25 = z(price momentum) + 0.25 * z(fundamental revision)`
   - `FUND50 = z(price momentum) + 0.50 * z(fundamental revision)`
6. Anchored selection: train-only Calmar through prior year; evaluate next calendar year 2022, 2023, 2024, 2025, and 2026 YTD through 2026-08-25.

## Acceptance criteria
Do not adopt because full-period CAGR improves alone. Require:
- positive next-year CAGR delta versus Hybrid baseline in multiple informative OOS-ish years;
- no material MaxDD degradation;
- performance not driven by one year/theme;
- result stable between 25% and 50% factor weight or otherwise supported by a broad neighborhood;
- later True Forward OOS confirmation before Production change.

## Repository status
Research branch only. Production/main unchanged.
