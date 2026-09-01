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

## Candidate T — VIX-Gated Short-Volatility Risk Premium
Return source: volatility risk premium rather than individual-stock momentum.
- research-only Yahoo histories for `SVXY` and `^VIX`; Production data pipeline remains unchanged
- instrument: SVXY + cash only
- risk-on signal at close when BOTH:
  - QQQ close > QQQ 200-session SMA
  - VIX close < 25
- otherwise target cash
- target is 100% SVXY or 100% cash; no partial exposure
- signal at close -> execute target change at next US open
- transaction cost: 10bp per side / target switch
- no stop, circuit, or additional volatility targeting; the two preregistered regime conditions are the complete risk rule
- +1-session-delay stress executes each target change one additional US session later
- historical comparison ends 2026-08-25

Candidate T is deliberately simple. The VIX threshold, QQQ trend length, and exposure must not be tuned after observing its result under this strategy definition.
