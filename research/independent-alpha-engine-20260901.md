# Independent Alpha Engine — preregistration

Date: 2026-09-01
Branch: `research/independent-alpha-engine-20260901`
Status: research only. Do not merge into Production/main strategy logic.

## Objective
Build a standalone alpha engine whose return source is materially different from Production Fixed60. The purpose is diversification and independent evidence, not another Fixed60 ranking tweak.

Production Fixed60 remains frozen and unchanged.

## Candidate A: Trend-Conditioned Short-Term Reversal (TCSR)

### Economic idea
Fixed60 buys persistent medium-term relative winners at month-end. TCSR instead buys short-horizon losers only when their longer trend is still intact, seeking a 1-week rebound. It is intentionally counter-directional at the entry horizon and event-driven daily rather than monthly.

### Data contract
Use only information already available point-in-time in the repository:
- monthly PIT SEC N-PORT Dynamic Universe membership
- adjusted daily OHLC
- QQQ adjusted daily OHLC

No intraday quote may be used for signal generation or backtest.

### Frozen baseline specification
1. Universe: latest PIT Dynamic Universe membership effective for the trading day.
2. Market gate: QQQ close > QQQ 200-session simple moving average.
3. Stock trend gate: stock close > stock 100-session simple moving average.
4. Reversal signal: trailing 5-session close-to-close return.
5. Selection: among eligible names with negative 5-session return, rank ascending by 5-session return and select bottom 2.
6. Portfolio: equal weight 50/50.
7. Entry: signal confirmed at regular close; buy at next US session open.
8. Holding period: exactly 5 US trading sessions after entry, then exit at next session open.
9. Stop: if a held stock closes 12% or more below its entry price, liquidate the whole TCSR sleeve at next session open.
10. Portfolio circuit: if TCSR sleeve close-to-close equity drawdown from its post-entry peak reaches 12%, liquidate the whole sleeve at next session open.
11. Re-entry: no new entry while invested. After scheduled/stop/circuit exit, next valid close may generate a new entry.
12. Transaction cost: 10 bp per side.
13. Backtest start: 2020-01-01, subject to required lookback availability.

### Why these choices are frozen before looking at results
- 5 sessions is a one-week reversal horizon and a one-week holding period; symmetry reduces degrees of freedom.
- 100-session stock trend and 200-session market trend are conventional medium/long trend definitions and are not optimized here.
- Top2 matches a concentrated standalone sleeve while equal weighting avoids another allocation optimization problem.
- 12% stop/circuit are risk controls for a high-volatility short-horizon sleeve; they are not inherited from Fixed60's 17.5%/15% controls.

## Stage 1 evaluation — no parameter search
Run exactly the frozen baseline first.

Report:
- gross CAGR
- MaxDD
- annualized volatility
- Calmar
- final equity
- exposure share
- trades/year
- win rate
- median trade return
- p10 trade return
- worst trade
- year-by-year return
- rolling 12M and 36M return distribution
- monthly-return correlation with Production Fixed60
- fraction of months with opposite return sign versus Fixed60
- performance during Fixed60's worst 10 months
- symbol concentration / leave-one-symbol-out sensitivity

## Stage 1 decision rule
Do not promote based on CAGR alone.

Candidate A is worth further research only if all of the following are true:
1. Gross CAGR >= 15%.
2. MaxDD > -40%.
3. Monthly return correlation with Fixed60 <= 0.60.
4. At least 30% of Fixed60 negative months have positive TCSR return.
5. No single symbol removal destroys more than half of TCSR CAGR.
6. Results are not dominated by one calendar year.

If these fail, reject Candidate A rather than tuning thresholds on the same sample.

## Stage 2 only if Stage 1 passes
Only then test a very small structural neighborhood, one axis at a time:
- reversal/holding horizon: 3/3, 5/5, 10/10 sessions
- stock trend gate: 100 vs 200 sessions
- market gate: QQQ 200SMA vs no market gate

No arbitrary threshold search and no factor additions in Stage 2.

## Portfolio-combination test
If Candidate A survives Stage 2, test Fixed60 and TCSR as separate engines first; do not alter Fixed60 signals.
Evaluate static research-only blends: Fixed60/TCSR = 90/10, 80/20, 70/30.
Primary blend objective: improve worst rolling 36M return and/or MaxDD while retaining most of Fixed60 CAGR.

## OOS discipline
If a version is selected after historical research, freeze a new TCSR strategy ID and start a separate True Forward OOS series from the next eligible close after the freeze. Historical 2020-2026 results are research evidence, not True OOS.

## Explicit exclusions
Do not re-introduce previously rejected Fixed60 add-ons (quality, PEAD, insider, 13F, residual momentum, 52-week high, consensus, cross-asset defensive sleeves, etc.) into TCSR during Stage 1. This engine must remain structurally independent.
