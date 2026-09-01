# CAGR40 New Alpha Exploration — 2026-09-01

Production Fixed60 remains unchanged. Research branch: `research/cagr40-new-alpha-20260901`.

## Objective
Find a genuinely distinct return engine that can ultimately help a portfolio target forward-planning CAGR ~40% while keeping historical MaxDD near 15-17%, without borrowing and without gross exposure above 100%.

Planning proxy = min(stress-median CAGR, rolling-36M median CAGR). It is a same-sample robustness/planning proxy, not True Forward OOS evidence.

## Stages 1-7 summary
Rejected or blocked families already documented in prior commits:
- non-equity leveraged macro trend
- relative-value leveraged ETF pairs
- monthly bull/inverse rotation
- daily 200DMA bull/inverse switch
- PIT N-PORT flow acceleration
- SEC XBRL annual fundamentals (data-blocked / untested, not rejected)
- High-Yield OAS macro guard

None bridged the 40% planning / 15-17% DD objective.

## Stage 8 — static DBMF managed-futures sleeve
Preregistered DBMF weights 0/10/15/20%; all M3 weights proportionally scaled.
- 0%: CAGR 52.59%, MaxDD -23.30%, planning 47.79%.
- 10%: CAGR 48.03%, MaxDD -21.44%, planning 43.56%.
- 15%: CAGR 45.75%, MaxDD -20.50%, planning 41.47%.
- 20%: CAGR 43.47%, MaxDD -19.54%, planning 39.27%.

15% was the largest preregistered weight preserving planning >=40%. No intermediate grid was searched.

## Stage 9 — monthly rebalance verification of DBMF 15%
Monthly portfolio rebalance plus immediate rebalance on frozen M3 state changes; 10bp one-way turnover cost and 30bp stress.
- CAGR 45.98%
- MaxDD -20.19%
- stress median 44.43%
- rolling36 median 42.34%
- rolling36 worst 22.23%
- planning 42.34%

DBMF benefit survives a more operational rebalance model.

## Stage 10 — defensive BTAL/DBMF substitution
Keep static DBMF 15% and frozen M3 trigger. Replace defensive BTAL sleeve by DBMF at only three preregistered points: 0%, 50%, 100%.
- BASE: CAGR 45.98%, MaxDD -20.19%, planning 42.34%.
- HALF: CAGR 45.52%, MaxDD -18.92%, planning 41.63%.
- ALL: CAGR 45.01%, MaxDD -19.14%, planning 40.75%.

50/50 defensive BTAL/DBMF was superior to either endpoint for historical DD while retaining planning >40%. No finer BTAL/DBMF grid was searched.

## Stage 11 — deeper defensive Fixed60 cut
Preregistered before result. Normal state unchanged from Stage10 HALF:
- Fixed60 72.25%, G 12.75%, DBMF 15%.
Defensive state:
- Fixed60 12.75%, G 12.75%, BTAL 14.875%, DBMF 29.875%, cash 29.75%.
Frozen M3 trigger unchanged.

Result:
- CAGR 44.15%
- MaxDD -18.28%
- annualized vol 25.41%
- Calmar 2.415
- stress median CAGR 42.63%
- rolling36 median CAGR 41.03%
- rolling36 worst CAGR 20.66%
- planning 41.03%

This is the strongest same-sample frontier that preserves planning >=40% without adding a new external signal. It still fails the 17% objective. Do not fine-tune defensive weights further.

## Stage 12 — Cboe volatility guards on frozen Stage11
Official Cboe VIX and VIX9D daily histories, one-session lagged. Preregistered rules:
- AV: VIX9D / VIX >= 1.10
- AW: VIX 5-session increase >= 50%
- AX: AV OR AW

Results:
- AV: CAGR 41.67%, MaxDD -18.80%, stress median 38.51%, rolling36 median 39.03%, planning 38.51%. Reject.
- AW: CAGR 44.72%, MaxDD -18.28%, stress median 42.74%, rolling36 median 40.73%, planning 40.73%. Reject on DD; essentially no DD improvement over Stage11.
- AX: CAGR 41.06%, MaxDD -18.76%, planning 38.40%. Reject.

Conclusion: these option-implied volatility stress rules do not improve the Stage11 frontier. Do not tune VIX/VIX9D thresholds further on this sample.

## Stage 13 — STLFSI4 financial-stress guard
Official St. Louis Fed Financial Stress Index, weekly. To avoid release-timing look-ahead, only observations at least 7 calendar days old were eligible. Single natural rule: defensive when lagged STLFSI4 > 0.

Result:
- CAGR 39.12%
- MaxDD -18.42%
- stress median 38.64%
- rolling36 median 38.18%
- rolling36 worst 20.13%
- planning 38.18%

Reject. It slightly reduces return and does not solve DD.

## Stage 14 — CFTC Nasdaq Asset Manager positioning, full defensive
Independent PIT source: CFTC Traders in Financial Futures futures-only data for NASDAQ MINI (contract code 209742). API field validation found 1,055 weekly observations from 2006-06-13 through 2026-08-25.

Preregistered signal:
- Asset Manager net = long - short.
- One-week lag.
- Risk signal when latest net is lower than four weekly reports earlier.
- Signal sends portfolio directly to the frozen Stage11 Deep allocation; M3 unchanged.

Result:
- CAGR 39.10%
- MaxDD -17.15%
- annualized vol 20.72%
- stress median 36.80%
- rolling36 median 37.97%
- rolling36 worst 20.57%
- planning 36.80%

Conclusion: CFTC positioning contains meaningful anticipatory risk information because DD improved from -18.28% to -17.15%, but full Deep defense on every deterioration is too expensive in return. Do not tune the four-week lookback or introduce an optimized threshold.

## Stage 15 — CFTC Yellow midpoint state
To avoid a new weight parameter, Yellow was defined mechanically as the exact arithmetic midpoint of Stage11 Normal and Deep allocations.

States:
- Normal: Fixed60 72.25%, G 12.75%, DBMF 15%.
- Yellow: Fixed60 42.50%, G 12.75%, BTAL 7.4375%, DBMF 22.4375%, cash 14.875%.
- Deep: Fixed60 12.75%, G 12.75%, BTAL 14.875%, DBMF 29.875%, cash 29.75%.
- CFTC four-week deterioration -> Yellow; frozen M3 -> Deep and overrides Yellow.

Result:
- CAGR 41.86%
- MaxDD -16.98%
- annualized vol 22.33%
- stress median 39.88%
- rolling36 median 38.50%
- rolling36 worst 20.71%
- planning 38.50%

Conclusion: this is the first structure to achieve the historical ~17% MaxDD target with a still-high return profile, but planning proxy remains about 1.5 percentage points below 40%.

## Stage 16 — CFTC open-interest-normalized positioning
Preregistered before result. Same one-week lag, same four-week directional comparison, same Yellow/Deep states. Only the CFTC signal value was structurally normalized to Asset Manager net percent of open interest: `pct_of_oi_asset_mgr_long - pct_of_oi_asset_mgr_short`.

Result:
- CAGR 40.47%
- MaxDD -16.97%
- annualized vol 21.69%
- stress median 37.79%
- rolling36 median 36.53%
- rolling36 worst 22.13%
- planning 36.53%

Reject. OI normalization preserves the DD benefit but reduces rolling/planning return further. Do not tune the CFTC participant class, lookback, or Yellow weights on this sample.

## Stage 17 — Cboe Total Put/Call flow
Independent options-flow source. Cboe daily market-statistics pages were successfully retrieved for all 1,670 QQQ trading dates from 2020-01-01 through 2026-08-25 (100% coverage).

Preregistered rule:
- TOTAL PUT/CALL RATIO only.
- One-session lag.
- Yellow when latest 5-observation mean > latest 20-observation mean.
- M3 -> Deep and overrides Yellow.
- No absolute put/call threshold.

Result:
- CAGR 33.05%
- MaxDD -18.29%
- annualized vol 20.99%
- stress median 32.96%
- rolling36 median 31.42%
- rolling36 worst 19.37%
- planning 31.42%

Reject. This options-flow trend is too frequently defensive, severely reducing return without improving DD. Do not tune put/call thresholds or lookbacks on this sample.

## Current research conclusion
1. Historical architectures with planning proxy >40% are available, but their MaxDD remains about 18-23%.
2. Stage11 is the best current architecture that keeps planning >=40%: planning 41.03%, MaxDD -18.28%.
3. CFTC Asset Manager positioning is the only new external risk source tested so far that materially pushes DD to the target neighborhood: Stage15 reaches MaxDD -16.98%, but planning falls to 38.50%.
4. OI normalization, VIX/VIX9D, HY OAS, STLFSI4 and Total Put/Call do not bridge the remaining return/DD gap.
5. The empirical frontier is therefore now approximately:
   - preserve planning >=40% -> Stage11 around -18.3% MaxDD;
   - achieve ~17% historical MaxDD -> Stage15 around 38.5% planning.
6. The remaining gap is small numerically but should NOT be closed by denser threshold or allocation search on the same 2020-2026 sample. That would create another layer of overfitting.
7. Further same-source mining is prohibited: do not tune CFTC four-week lookback, participant category, magnitude threshold, Yellow weights, VIX, OAS, put/call, BTAL/DBMF ratio, or Fixed60/cash weights on this sample.
8. The next useful evidence must come from either a genuinely new independent return source with high return density or actual Forward OOS evidence. SEC annual fundamentals AO/AP/AQ remain untested only because companyfacts access was data-blocked in GitHub Actions.

Production Fixed60 remains unchanged. None of these same-sample research structures is Production-approved or True Forward OOS validated.