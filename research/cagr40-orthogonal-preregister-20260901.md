# CAGR40 Orthogonal Engine Search — preregistration

Date: 2026-09-01
Branch: research/cagr40-orthogonal-20260901

Production Fixed60 is unchanged. Frozen G is unchanged. No margin/credit borrowing. Cash-funded TQQQ is permitted.

## Ultimate portfolio objective
- Forward-planning CAGR proxy >= 40%.
- Historical portfolio MaxDD approximately 15%, hard research screen <= 17%.
- Forward-planning proxy is not full-sample backtest CAGR. It is `min(stress median CAGR, rolling-36M median CAGR)`.

## Stage 1 standalone screen
A new engine is worth portfolio integration only if it shows materially better robust return than the prior diversifiers. Initial screen:
- planning CAGR proxy >= 30%,
- monthly correlation with formal Fixed60 <= 0.40,
- full-sample MaxDD <= 40%,
- no single-session execution dependency under +1/+2 session stress.

No threshold tuning after results.

## Candidate V — Cross-Asset Leveraged Rotation
- Assets: TQQQ, GLD, DBMF, Cash.
- Signal: last US session of each calendar month.
- Score: 50% trailing 3-month return + 50% trailing 6-month return.
- Eligible only when 6-month return > 0.
- Hold the single highest-scoring eligible asset; otherwise Cash.
- Close signal -> next-session open execution.
- 10 bp/side baseline cost.
- Rationale: changes return source across leveraged equity, gold and managed futures rather than permanently carrying Nasdaq beta.

## Candidate W — Breadth-Thrust TQQQ
- PIT SEC N-PORT Dynamic Universe.
- Daily breadth = share of current universe above 50DMA.
- Arm when breadth was <= 40% at least once during the prior 10 sessions.
- Trigger when current breadth >= 60% and breadth has increased by >= 20 percentage points over 10 sessions.
- Require QQQ close > 100DMA.
- Buy TQQQ next open; hold exactly 20 closes, then exit next open.
- No overlapping positions.
- 10 bp/side.
- Rationale: event-driven recovery participation, not continuous equity trend.

## Candidate X — Risk-On Breakout TQQQ
- Require QQQ close > 200DMA.
- Require current QQQ close > prior 20-session closing high.
- Buy TQQQ next open.
- Hold until QQQ close < 50DMA or 20 closes elapsed, whichever comes first; exit next open.
- 10 bp/side.
- Rationale: sparse leveraged participation only during confirmed trend expansion.

## Stress set
For every candidate:
- baseline 10bp/side,
- cost 30bp/side,
- +1-session execution delay,
- +2-session execution delay,
- start 2021-01-01.

Candidate is rejected without tuning if Stage 1 fails.