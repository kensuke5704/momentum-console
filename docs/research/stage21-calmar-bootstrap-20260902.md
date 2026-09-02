# Stage21 architecture-level Calmar robustness — 2026-09-02

## Scope

- Frozen candidate: `momentum-stage21-sbi-2026-09-v1`
- Sample: 2020-01-01 through 2026-08-25
- Common trading days: 1,669
- Captured performance calls: 492
- Full-period eligible calls: 408
- Unique full-period curves: 333
- Successfully reproduced scripts: 36 / 38
- Failed/non-reproduced: `cagr40-sec-fundamental-stage6` (error), `cagr40-putcall-stage17` (timeout)

## Observed Calmar ranking

Stage21:
- CAGR: 48.6072%
- MaxDD: -16.8860%
- Calmar: **2.8786**
- Rank among 333 unique full-period curves: **1 / 333**

Fixed60-like reference:
- CAGR: 61.9981%
- MaxDD: -31.1272%
- Calmar: **1.9918**

Next-highest observed Calmar values included:
- `cagr40-sbi-trend-stage20`: 2.5455
- `cagr40-sbi-stage18`: 2.5308
- `cagr40-tail-circuit-stage2`: 2.5189
- `cagr40-volatility-guard-stage12`: 2.4873

## Shared stationary-bootstrap paired comparison

5,000 replications per expected block length. The same bootstrap indices are used for Stage21 and the Fixed60-like reference.

| Expected block | Stage21 median Calmar | Stage21 95% interval | Fixed60 median Calmar | Fixed60 95% interval | Median Calmar difference | Difference 95% interval | P(Stage21 > Fixed60) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 2.0701 | [0.6848, 4.4763] | 1.7879 | [0.4914, 4.3422] | +0.2397 | [-0.7638, 1.2876] | 72.22% |
| 10 | 2.0885 | [0.7122, 4.6990] | 1.7591 | [0.4878, 4.3250] | +0.2764 | [-0.7117, 1.4839] | 74.42% |
| 20 | 2.1678 | [0.7227, 4.7971] | 1.7720 | [0.4738, 4.3710] | +0.3292 | [-0.7881, 1.7193] | 75.62% |
| 60 | 2.3418 | [0.8954, 4.6199] | 1.8325 | [0.6187, 3.9392] | +0.4568 | [-0.6767, 1.9842] | 78.88% |

## Interpretation

1. The observed historical risk/return trade-off is strong: Stage21 has the highest Calmar among all 333 captured full-period curves.
2. The advantage is directionally stable under stationary bootstrap. Stage21 beats the Fixed60-like reference in roughly 72% to 79% of resampled paths depending on block length.
3. The paired 95% interval for the Calmar difference crosses zero for every block length. Therefore the bootstrap does **not** establish a conventional 5% significance claim for Stage21 > Fixed60 on Calmar.
4. Longer blocks strengthen the median Stage21 advantage rather than weaken it, so the observed benefit is not obviously an artifact of very short-block resampling.
5. This is a Calmar robustness/rank-stability analysis, not a canonical Hansen SPA p-value. Calmar is nonlinear and path-dependent, so SPA-style daily loss differentials do not directly apply.
6. Architecture-selection bias remains relevant despite the rank result. The decisive independent evidence remains True Forward OOS.

## Reproduction

- Workflow: `.github/workflows/research-architecture-spa.yml`
- Calmar script: `scripts/architecture-calmar-bootstrap.mjs`
- Successful run: `33599739253`
- Commit: `71676c71f7ac45a677f744d0cc4aec7f6a608ed7`

Production and the frozen backtest were not modified.
