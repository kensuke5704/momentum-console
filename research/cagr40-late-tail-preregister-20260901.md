# CAGR40 Late Tail Hedge — preregistration

This stage is diagnostic-driven but target-based, not optimized to a return peak. The portfolio DD budget is ~15%; therefore the defensive trigger is fixed at -12% shadow DD, leaving ~3 percentage points of historical loss budget for execution/slippage.

Normal core:
- Fixed60 85%
- frozen G 15%

Shadow signal is always the unhedged 85/15 core.

Enter defensive state when prior-close shadow DD <= -12%.
Exit defensive state when prior-close shadow DD > -8% AND shadow trailing-10-session return > 0.
Allocation changes apply next session.

Coarse defensive implementations:
- L1 Cash: Fixed60 15% / G 15% / Cash 70%.
- L2 BTAL: Fixed60 15% / G 15% / BTAL 70%.
- L3 Mixed: Fixed60 15% / G 15% / BTAL 35% / Cash 35%.

No margin; total allocation <=100%; BTAL purchased long.

Robustness:
- 30bp turnover cost,
- +1 session signal delay,
- +2 session delay,
- start 2021,
- rolling 36M.

Forward-planning CAGR proxy = min(stress CAGR median, rolling-36M CAGR median).
Pass = proxy >=40% AND historical MaxDD <=17%.

Do not alter the -12/-8 thresholds or test intermediate allocations after results.