# CAGR40 Core-Stress Detector — Stage 9 preregistration

Date: 2026-09-01

Context already known before this specification:
- The dominant 2024-12-24 -> 2025-02-26 drawdown occurs while QQQ stays above its 100DMA until after the trough.
- QQQ regime filters therefore miss the dominant portfolio-specific stress.
- DD-triggered circuits act too late and lose too much recovery return.

This stage tests three structurally different *early* detectors of core-specific stress. No parameters will be changed after results.

Normal allocation for every variant:
- Fixed60 85%
- frozen G 15%

Defensive allocation for every variant:
- Fixed60 30%
- G 15%
- BTAL 35%
- Cash 20%

No borrowing, no account-level shorting, total invested capital <=100%. BTAL is purchased long.

All signals use information through the prior close; allocation changes apply next session. Baseline turnover cost 10bp per changed notional.

## M1 — Core volatility shock
Signal portfolio: unhedged 85/15 core.
- Compute trailing 20-session annualized realized volatility of core daily returns.
- Compute the median of trailing 252-session values of the same 20-session realized-vol series.
- Enter defensive state when current 20-session vol >= 2.0x its trailing-252-session median.
- Exit when current 20-session vol < 1.25x trailing median for 5 consecutive sessions.

Rationale: standardized volatility shock; scale-free and not tied to the 2025 event level.

## M2 — PIT universe breadth deterioration
- Using the current PIT SEC N-PORT Dynamic Universe, compute share above 50DMA each session.
- Enter defensive state when breadth < 40%.
- Exit after breadth > 55% for 5 consecutive sessions.

Rationale: detects deterioration among the investable high-beta/theme opportunity set even while QQQ remains healthy.

## M3 — Core relative breakdown vs QQQ
- Compute trailing 20-session return of unhedged 85/15 core and QQQ.
- Enter defensive state when core 20-session return is at least 10 percentage points below QQQ 20-session return AND core 20-session return < 0.
- Exit when the 20-session relative gap improves to better than -3 percentage points for 5 consecutive sessions.

Rationale: detects strategy-specific failure rather than broad-market risk.

## Robustness
For each candidate:
- baseline 10bp turnover cost,
- 30bp turnover cost,
- signal delay +1 session,
- signal delay +2 sessions,
- start 2021,
- rolling 36M distribution.

Forward-planning CAGR proxy = min(stress CAGR median, rolling-36M CAGR median).
Pass = proxy >=40% AND historical MaxDD <=17%.

No threshold, confirmation-day, or defensive-allocation tuning after results.