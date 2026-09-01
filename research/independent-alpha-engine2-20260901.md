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
- +1-session-delay CAGR remains >= 10% if candidate passes baseline

## Results so far
- I Shock Continuation: rejected — CAGR 6.72%, +1 delay 5.03%.
- J Failed Gap Reversal: rejected — no trades under preregistered specification.
- K Range Expansion Continuation: rejected — CAGR 2.01%, +1 delay -1.33%.
- L Overnight Accumulation: rejected — CAGR 2.84%, MaxDD -42.63%.
- M Gap-Up Follow-Through: rejected — CAGR 0.71%.
- N Intraday Accumulation: rejected — CAGR -3.28%.
- O Volatility-Managed Nasdaq Trend: secondary — CAGR 28.24%, MaxDD -28.91%, +1 delay 27.59%, but Fixed60 correlation 0.638 > preregistered 0.60 ceiling.
- P Turn-of-Month TQQQ: rejected — CAGR 10.59%, +1 delay 1.82%.

## Candidate Q — Abnormal Participation Continuation
Return source: unusual market participation accompanying a positive price move.
- research-only Yahoo daily volume; Production market-data types remain unchanged
- PIT Dynamic Universe
- QQQ > 200DMA
- stock > 100DMA
- current close-to-close return > +1%
- current raw dollar turnover (Yahoo raw close × raw volume) > 2.5 × median prior-20-session raw dollar turnover
- current close in upper 50% of adjusted daily high-low range
- rank by dollar-turnover multiple × positive daily return
- Top5 equal weight
- close signal -> next-open entry
- hold 10 closes
- stop 12%, circuit 15%, cost 10bp/side

## Candidate R — Low-Participation Pullback Reversal
Return source: pullback inside an established trend without confirming heavy participation.
- research-only Yahoo daily volume
- PIT Dynamic Universe
- QQQ > 200DMA
- stock > 100DMA
- current close-to-close return <= -3%
- current raw dollar turnover < 0.70 × median prior-20-session raw dollar turnover
- rank by absolute negative return / dollar-turnover multiple
- Top5 equal weight
- close signal -> next-open entry
- hold 5 closes
- stop 10%, circuit 12%, cost 10bp/side

## Candidate S — High-Participation Price Absorption
Return source: unusually large participation with little net price movement and a strong close, interpreted as possible absorption rather than directional momentum.
- research-only Yahoo daily volume
- PIT Dynamic Universe
- QQQ > 200DMA
- stock > 100DMA
- current raw dollar turnover > 2.5 × median prior-20-session raw dollar turnover
- absolute close-to-close return < 1%
- current close in upper 25% of adjusted daily high-low range
- rank by dollar-turnover multiple × close-location value
- Top5 equal weight
- close signal -> next-open entry
- hold 10 closes
- stop 12%, circuit 15%, cost 10bp/side

### Volume-data integrity rule
The research loader obtains Yahoo raw close and raw volume solely to calculate raw dollar turnover = raw close × raw volume. This product is economically comparable across ordinary share splits because the raw price/share-count changes offset each other. Existing split-adjusted OHLC remains the sole price source for signals other than participation, portfolio marking, and execution. Production `PricePoint`, `sync:data`, and app data are not modified.
