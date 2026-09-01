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

## Candidate I — Shock Continuation Basket
Return source: large positive daily price shock with persistent trend.
- PIT Dynamic Universe
- QQQ > 200DMA
- stock > 100DMA
- today's close-to-close return > +2.0 x trailing 20-session realized daily volatility
- rank by standardized shock size
- Top5 equal weight
- signal close -> enter next open
- hold 10 closes
- stop 12%, circuit 15%, 10bp/side

## Candidate J — Failed Gap Reversal
Return source: negative overnight news shock followed by intraday rejection/recovery.
- PIT Dynamic Universe
- QQQ > 200DMA
- stock > 100DMA before event
- open <= prior close * 0.95
- same-day close > open and close recovers at least half of the overnight gap
- rank by recovery strength
- Top5 equal weight
- signal close -> enter next open
- hold 5 closes
- stop 10%, circuit 12%, 10bp/side

## Candidate K — Range Expansion Continuation
Return source: abnormal intraday range expansion with close near high, independent of 20-day price breakout.
- PIT Dynamic Universe
- QQQ > 200DMA
- stock > 100DMA
- true range / prior close > 2.0 x median of prior 20-session true-range ratios
- close in top 20% of day's high-low range
- rank by normalized range expansion
- Top5 equal weight
- signal close -> enter next open
- hold 10 closes
- stop 12%, circuit 15%, 10bp/side

## Candidate L — Overnight Accumulation
Return source: persistent close-to-open accumulation rather than close-to-close momentum.
- PIT Dynamic Universe
- QQQ > 200DMA
- stock > 100DMA
- cumulative 20-session overnight log return > +5%
- cumulative overnight log return > cumulative intraday log return
- rank by overnight minus intraday log return
- Top5 equal weight
- signal close -> enter next open
- hold 20 closes
- stop 12%, circuit 15%, 10bp/side

## Candidate M — Gap-Up Follow-Through
Return source: discrete positive overnight information shock followed by same-day confirmation.
- PIT Dynamic Universe
- QQQ > 200DMA
- stock > 100DMA before event
- open >= prior close * 1.05
- same-day close > open
- close in upper half of daily range
- rank by gap size times intraday confirmation
- Top5 equal weight
- signal close -> enter next open
- hold 5 closes
- stop 10%, circuit 12%, 10bp/side

## Candidate N — Intraday Accumulation / Overnight Weakness
Return source: repeated regular-session demand masked by weak overnight pricing.
- PIT Dynamic Universe
- QQQ > 200DMA
- stock > 100DMA
- cumulative 20-session intraday log return > +8%
- cumulative 20-session overnight log return < 0%
- rank by intraday minus overnight log return
- Top5 equal weight
- signal close -> enter next open
- hold 10 closes
- stop 12%, circuit 15%, 10bp/side

## Candidate O — Volatility-Managed Nasdaq Trend
Return source: time-series trend plus volatility risk budgeting, with no individual-stock selection.
- instrument: TQQQ + cash only
- risk-on when QQQ close > QQQ 200DMA; otherwise cash
- estimate annualized TQQQ volatility from trailing 20 close-to-close returns
- target annualized portfolio volatility: 30%
- TQQQ weight = min(100%, 30% / trailing TQQQ volatility)
- signal/target weight fixed at close and executed next US open
- daily rebalance to the target weight
- transaction cost: 10bp on traded notional
- +1-session-delay version repeats the same target with one additional session lag
- no stop/circuit overlay; volatility scaling and QQQ trend gate are the complete risk engine
