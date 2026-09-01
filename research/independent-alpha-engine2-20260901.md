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
- +1-session-delay stress applies the same target vector one additional session later.
- Historical comparison ends 2026-08-25.

The four sleeves and 200-session trend rule are frozen before observing Candidate U. No sleeve deletion, sector substitution, or trend-length tuning is permitted under Candidate U after results are known.
