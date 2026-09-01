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

This is the best current same-sample frontier preserving planning >=40% while materially reducing DD. It still fails the 17% objective. Do not fine-tune defensive weights further.

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
Official St. Louis Fed Financial Stress Index, weekly. To avoid release-timing look-ahead, only observations at least 7 calendar days old were eligible. Single natural rule: defensive when lagged STLFSI4 > 0 (the index's published normal/stress boundary).

Result:
- CAGR 39.12%
- MaxDD -18.42%
- stress median 38.64%
- rolling36 median 38.18%
- rolling36 worst 20.13%
- planning 38.18%

Reject. It slightly reduces return and does not solve DD.

## Current research conclusion
1. The return side of the objective is feasible in historical robustness terms: multiple structures have planning proxies above 40%.
2. Managed futures materially improve diversification; Stage11 currently gives planning 41.03% with MaxDD -18.28%.
3. Credit spreads, VIX/VIX9D, and STLFSI4 do not push the same architecture to 17% DD.
4. Same-sample allocation or threshold grid search is now prohibited: no denser Fixed60/cash, BTAL/DBMF, VIX, OAS, or volatility-target tuning.
5. The next useful evidence must come from a genuinely different PIT return/positioning source.

Next preregistered research direction: CFTC Traders in Financial Futures positioning for Nasdaq-100 futures. Use weekly published positioning with an explicit release lag and a directional change signal rather than an optimized extreme threshold. This source is structurally distinct from price, volatility, credit, and N-PORT data.

Do not modify Fixed60 Production mechanics based on this work.