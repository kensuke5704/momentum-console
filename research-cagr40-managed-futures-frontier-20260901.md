# Managed-Futures Frontier — 2026-09-01

Production Fixed60 remains unchanged. Research only on `research/cagr40-new-alpha-20260901`.

All figures below are historical same-sample research through 2026-08-25, not True Forward OOS evidence.

## Stage 8 — static DBMF sleeve
Frozen M3 trigger unchanged. DBMF weights were preregistered at 0/10/15/20%; all existing M3 weights were proportionally scaled by `(1-w)`.

| DBMF | CAGR | MaxDD | Planning proxy |
|---:|---:|---:|---:|
| 0% | 52.59% | -23.30% | 47.79% |
| 10% | 48.03% | -21.44% | 43.56% |
| 15% | 45.75% | -20.50% | 41.47% |
| 20% | 43.47% | -19.54% | 39.27% |

No intermediate DBMF weight was searched. 15% was the largest preregistered weight that retained planning >=40%.

## Stage 9 — monthly rebalance verification
15% DBMF was re-run with monthly portfolio rebalancing plus immediate rebalance only on frozen M3 state changes. Portfolio turnover was charged at 10bp one-way, with a 30bp stress.

- CAGR: 45.98%
- MaxDD: -20.19%
- annualized volatility: 25.55%
- stress median CAGR: 44.43%
- rolling-36M median CAGR: 42.34%
- rolling-36M worst CAGR: 22.23%
- planning proxy: 42.34%

The managed-futures benefit therefore survives a lower-frequency operational allocation model.

## Stage 10 — defensive BTAL/DBMF substitution
Normal state stayed fixed at Fixed60 72.25%, G 12.75%, DBMF 15%. The frozen M3 trigger remained unchanged. In the defensive state, the existing BTAL sleeve was replaced by DBMF at only three structural points: 0%, 50%, and 100%.

| Defensive substitution | CAGR | MaxDD | Planning proxy |
|---|---:|---:|---:|
| 0% (BASE) | 45.98% | -20.19% | 42.34% |
| 50% (HALF) | 45.52% | **-18.92%** | **41.63%** |
| 100% (ALL) | 45.01% | -19.14% | 40.75% |

The 50/50 BTAL/DBMF defensive mix dominates the full DBMF substitution on drawdown while keeping a higher planning proxy. No 25/75 or other grid was searched.

## Current frontier
Best observed structure under the fixed research gate is currently:
- Normal: Fixed60 72.25%, G 12.75%, DBMF 15%
- Defensive: Fixed60 25.5%, G 12.75%, BTAL 14.875%, DBMF 29.875%, cash 17%
- Frozen M3 state trigger unchanged
- Monthly rebalance plus immediate state-change rebalance

Historical research metrics:
- CAGR ~45.52%
- MaxDD ~-18.92%
- planning proxy ~41.63%

This is materially closer to the 40% / 15-17% objective, but it still fails the MaxDD gate and is not production-approved.

## Next structural test
Do not optimize BTAL/DBMF ratios further. Test one preregistered deeper-defensive variant only: keep the normal state unchanged, keep the Stage10 50/50 BTAL/DBMF defensive mix, halve the defensive Fixed60 sleeve from 25.5% to 12.75%, and move the released 12.75% to cash. No trigger threshold changes.
