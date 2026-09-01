# Independent Alpha Engine Search 2 — 2026-09-01

Candidate G (`independent-top5-breakout-v1`) remains frozen and is not modified here.

This branch starts a new search from `main` to avoid contaminating G. No Production Fixed60 rule changes are allowed.

## Screening rule
Each candidate below is tested as one preregistered specification. No within-candidate parameter search before Pass/Reject.

Primary screen:
- gross CAGR >= 15%
- MaxDD > -40%
- monthly correlation with Production Fixed60 <= 0.60
- positive in at least 30% of Fixed60 negative months
- +1-session-delay CAGR remains >= 10%

## Results so far
- I Shock Continuation: rejected — CAGR 6.72%, +1 delay 5.03%.
- J Failed Gap Reversal: rejected — no trades under preregistered specification.
- K Range Expansion Continuation: rejected — CAGR 2.01%, +1 delay -1.33%.
- L Overnight Accumulation: rejected — CAGR 2.84%, MaxDD -42.63%.
- M Gap-Up Follow-Through: rejected — CAGR 0.71%.
- N Intraday Accumulation: rejected — CAGR -3.28%.
- O Volatility-Managed Nasdaq Trend: secondary — CAGR 28.24%, MaxDD -28.91%, +1 delay 27.59%, but Fixed60 correlation 0.638 > preregistered 0.60 ceiling.
- P Turn-of-Month TQQQ: rejected — CAGR 10.59%, +1 delay 1.82%.
- Q Abnormal Participation Continuation: rejected — CAGR 4.41%, +1 delay 0.46%.
- R Low-Participation Pullback: rejected — CAGR -1.73%, only one completed position cycle.
- S High-Participation Price Absorption: rejected — approximately flat, only two completed position cycles.
- T VIX-Gated Short-Volatility: rejected — CAGR 2.39%, MaxDD -39.55%, +1 delay 4.05% despite low Fixed60 correlation 0.287.

## Candidate U — Diversified Leveraged Trend Ensemble
Return source: four distinct equity risk-premium sleeves rather than individual-stock selection or a single Nasdaq trend.

Research-only Yahoo histories; Production data pipeline is unchanged.

Four fixed sleeves, each with maximum 25% portfolio target:
- Nasdaq: signal QQQ > QQQ 200-session SMA; instrument TQQQ
- US small caps: signal IWM > IWM 200-session SMA; instrument TNA
- US financials: signal XLF > XLF 200-session SMA; instrument FAS
- US energy: signal XLE > XLE 200-session SMA; instrument ERX

Rules:
- Each sleeve target is 25% when its underlying trend is on, otherwise 0%.
- Remaining capital stays in cash.
- Targets are calculated after the close and rebalanced at the next US open.
- Portfolio is rebalanced to the four fixed target weights whenever needed; transaction cost is 10bp on absolute traded notional.
- No additional stop/circuit, volatility target, ranking, or cross-sleeve selection.
- Historical comparison ends 2026-08-25.

### Initial screen result
- CAGR: 25.47%
- MaxDD: -36.26%
- +1-session delay CAGR: 25.76%
- +1-session delay MaxDD: -36.64%
- monthly correlation with Fixed60: 0.529
- positive in Fixed60 negative months: 8/17 = 47.1%
- all preregistered initial screens: PASS

### Preregistered robustness matrix
No parameters are selected from these results. Candidate U stays defined by the 200-session / four-sleeve baseline above.

Stress-only variants to run once:
1. transaction cost 30bp on traded notional
2. +2-session execution delay
3. backtest start 2021-01-01
4. 150-session trend length
5. 250-session trend length
6. remove Nasdaq sleeve, keep other sleeve caps at 25% and residual in cash
7. remove small-cap sleeve, same treatment
8. remove financial sleeve, same treatment
9. remove energy sleeve, same treatment

Additional diagnostics:
- yearly returns
- rolling 12M and rolling 36M annualized-return distributions
- stress CAGR median / p10 / worst
- worst sleeve-removal CAGR retention versus baseline

Candidate U is promoted to PROMISING only if the stress set remains economically positive without a single sleeve explaining most of the baseline and without execution/cost stress collapsing the result. No stress variant may replace the frozen baseline.
