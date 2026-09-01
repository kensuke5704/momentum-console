# CAGR40 Dynamic BTAL Capital Shift — preregistration

Motivation: Z2 achieved the 40% planning-return objective but not the DD objective. This stage tests a structural change, not a threshold change: keep capital in the high-return core during normal regimes and move a coarse block of capital to BTAL only during the already-frozen risk-off condition.

Risk-off condition remains unchanged from Z2:
- QQQ close < 100DMA, AND
- QQQ trailing-20-session return < 0.

Normal allocation for all variants:
- Fixed60 85%
- frozen G 15%
- BTAL 0%

Risk-off allocations:
- H20: Fixed60 65% / G 15% / BTAL 20%
- H30: Fixed60 55% / G 15% / BTAL 30%
- H40: Fixed60 45% / G 15% / BTAL 40%

Signals are prior-close only and allocation changes apply from the following session. Baseline turnover cost 10bp per traded notional. No borrowing, no shorting by the account, total allocation 100%.

Robustness:
- 30bp turnover cost,
- allocation-signal delay +1 session,
- delay +2 sessions,
- start 2021,
- rolling 36M distribution.

Forward-planning CAGR proxy = min(stress CAGR median, rolling-36M CAGR median).
Pass = proxy >=40% AND historical MaxDD <=17%.

Do not test intermediate 25/35% shifts after results.