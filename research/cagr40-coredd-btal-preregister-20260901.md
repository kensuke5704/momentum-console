# CAGR40 Core-Drawdown BTAL Hedge — preregistration

Diagnosis before this specification:
- H20/H30/H40 max DD window: 2024-12-24 peak -> 2025-02-26 trough, -27.33%.
- QQQ remained above its 100DMA throughout the decline until 2025-02-27, one session after the portfolio trough.
- Therefore QQQ-based market-risk triggers cannot hedge this dominant drawdown. The failure is an equity/high-beta sleeve drawdown while the broad Nasdaq trend remains intact.

This stage changes the trigger structurally: use the high-return core portfolio's own unhedged shadow NAV drawdown, not a QQQ threshold.

Normal allocation:
- Fixed60 85%
- frozen G 15%
- BTAL 0%

Shadow portfolio for the signal is always the unhedged 85/15 Fixed60/G portfolio and is never affected by hedge P&L.

Hedge state:
- Enter hedge when prior-close shadow DD <= -8%.
- Exit hedge only when prior-close shadow DD > -3% AND shadow trailing-10-session return > 0.
- Allocation changes take effect on the next session.

Coarse preregistered hedge shifts from Fixed60 to BTAL:
- C30: risk-off Fixed60 55% / G 15% / BTAL 30%.
- C50: risk-off Fixed60 35% / G 15% / BTAL 50%.
- C70: risk-off Fixed60 15% / G 15% / BTAL 70%.

No margin, no account-level shorting, total allocation 100%. BTAL is purchased long with cash.

Robustness:
- 30bp turnover cost,
- hedge signal delay +1 session,
- delay +2 sessions,
- start 2021,
- rolling 36M.

Forward-planning CAGR proxy = min(stress CAGR median, rolling-36M CAGR median).
Pass = proxy >=40% AND historical MaxDD <=17%.

Do not test intermediate hedge sizes or DD thresholds after results.