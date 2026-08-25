# Exposure Quality Attribution — 2026-08-25

Workflow run: `32847827172` (success)

## Baseline integrity
- Production historical CAGR reproduced: **55.3601%**
- Production CPCM 1,000-path median CAGR reproduced: **26.0447%**

## Exposure quantity vs quality
- Realized exposed-day share: **51.5588%**
- CPCM median exposed-day share: **42.8571%**
- Realized annualized return conditional on exposed days: **132.0392%**
- CPCM median conditional annualized exposed return: **69.5512%**

Using a symmetric log-growth decomposition on these median/realized summary values, approximately **29%** of the realized-vs-CPCM log-growth gap is associated with exposure quantity and approximately **71%** with conditional return quality. This is an approximation because CPCM marginal medians need not come from the same path.

## Monthly right-tail
- Realized mean monthly return: **4.4757%**
- CPCM median of path-level mean monthly return: **2.5532%**
- Realized monthly p90: **18.6724%**
- CPCM median monthly p90: **16.6015%**
- Realized monthly p95: **28.6185%**
- CPCM median monthly p95: **23.9633%**
- Realized maximum month: **57.0114%**
- CPCM median maximum month: **43.3712%**

Top 10% winning months as share of positive monthly log gains:
- Realized: **47.35%**
- CPCM median: **59.04%**

So CPCM is actually more concentrated in a few winners by this normalized measure; the realized edge is not merely "more concentrated wins", but stronger conditional returns across the exposed periods plus several very strong realized months.

## Counterfactual: set largest winning months to zero
CAGR after setting the top winning portfolio months to 0% return, leaving all other months unchanged:

| Case | Realized | CPCM median |
|---|---:|---:|
| Original | 55.36% | 26.04% |
| Top 1 month = 0 | 45.56% | 17.00% |
| Top 3 months = 0 | 32.27% | 4.88% |
| Top 5 months = 0 | 22.40% | -3.09% |

The strategy is strongly convex/right-tail dependent in both realized history and CPCM. However, the realized path remains materially stronger after removing the same number of top months.

## Largest realized months
1. 2021-10: **+57.01%**
2. 2024-11: **+43.75%**
3. 2020-11: **+30.64%**
4. 2025-09: **+29.68%**
5. 2023-12: **+28.50%**
6. 2020-07: **+27.79%**
7. 2026-01: **+21.04%**
8. 2024-03: **+20.66%**
9. 2023-05: **+18.17%**
10. 2020-12: **+16.55%**

## Interpretation
The prior hypothesis that the CAGR gap is mainly explained by roughly 9 percentage points more time invested is rejected. Exposure time matters, but the larger component is the quality of returns earned while exposed. The realized 2020–2026 path had substantially stronger conditional return capture than the CPCM median.

This does not prove the realized conditional return is repeatable. It increases the evidence that the historical 55.36% CAGR includes favorable path realization beyond what the CPCM model treats as typical.
