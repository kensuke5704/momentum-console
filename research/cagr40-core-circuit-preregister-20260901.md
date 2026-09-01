# CAGR40 Core Tail Circuit — preregistration

Purpose: preserve the high-return core in normal conditions and cap incremental loss after a material core drawdown, without relying on QQQ regime recognition or an external hedge asset.

Shadow signal portfolio (always ungoverned):
- Fixed60 85%
- frozen G 15%

Actual portfolio is the same core times a portfolio exposure multiplier; unused capital is Cash. No borrowing and no leveraged return multiplier.

Coarse variants, fixed before execution:

## K1
- Trigger: prior-close shadow DD <= -8%.
- Actual core exposure becomes 50% for a fixed 20 sessions.
- At the end of 20 sessions, restore 100% if shadow DD > -8%; otherwise renew another 20-session defensive block.

## K2
- Trigger: prior-close shadow DD <= -10%.
- Actual core exposure becomes 25% for a fixed 20 sessions.
- At block end, restore if shadow DD > -10%; otherwise renew.

## K3
- Trigger: prior-close shadow DD <= -10%.
- Actual core exposure becomes 0% (Cash) for a fixed 20 sessions.
- At block end, restore if shadow DD > -10%; otherwise renew.

All exposure changes apply next session. Baseline turnover cost 10bp per changed notional.

Robustness:
- 30bp turnover cost,
- circuit signal +1 session delay,
- +2 session delay,
- start 2021,
- rolling 36M distribution.

Forward-planning CAGR proxy = min(stress CAGR median, rolling-36M CAGR median).
Pass = proxy >=40% and historical MaxDD <=17%.

No intermediate threshold/exposure/holding-period tuning after results.