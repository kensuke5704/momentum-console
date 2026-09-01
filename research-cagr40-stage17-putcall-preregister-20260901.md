# Stage 17 — Cboe Total Put/Call Flow — preregistration

Research branch only. Production Fixed60 unchanged.

Independent information source: Cboe daily Total Put/Call Ratio (actual options volume flow), not VIX levels and not price momentum.

Frozen before result:
- Download Cboe daily market-statistics pages for QQQ trading dates from 2020-01-01 through 2026-08-25.
- Use TOTAL PUT/CALL RATIO only.
- One trading-session lag before use.
- Flow stress when the mean of the latest 5 available put/call observations is greater than the mean of the latest 20 available observations.
- Flow stress alone -> the exact Stage15 Yellow midpoint allocation.
- Frozen M3 trigger -> original Stage11 Deep allocation and overrides Yellow.
- Normal/Yellow/Deep allocations otherwise unchanged.
- Monthly rebalance plus immediate state-change rebalance.
- 10bp one-way turnover cost; 30bp stress.
- Objective: planning proxy >=40% and historical MaxDD no worse than -17%.

No put/call absolute threshold, lookback, or Yellow weight will be tuned after the result.