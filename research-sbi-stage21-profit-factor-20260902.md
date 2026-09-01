# Stage21 rounded v1 — Profit Factor diagnostic (2026-09-02)

Research-only diagnostic. Production rules are unchanged.

Frozen architecture: Stage21 rounded v1, release-aware CFTC timing, 2020-01-01 through 2026-08-25.

Reference backtest rerun:
- CAGR: 48.6072%
- MaxDD: -16.8860%
- annualized volatility: 25.1960%
- Calmar: 2.8786
- final equity: 13.9048x

## Profit Factor definitions and results

Because Stage21 is a continuously rebalanced portfolio wrapper rather than a simple one-position-in/one-position-out trade system, there is no single canonical trade PF. Two diagnostics were computed from the exact same equity curve:

### Daily equity-P&L PF
Definition: sum of positive daily equity changes divided by absolute sum of negative daily equity changes.
- PF: **1.3910346965**
- gross positive equity P&L: 45.9064948827
- gross negative equity P&L: 33.0016893165
- positive days: 910
- negative days: 755
- flat days: 4

### Rebalance-interval equity-P&L PF
Definition: sum of positive equity changes between monthly/state rebalance dates divided by absolute sum of negative interval equity changes.
- PF: **2.7329912823**
- gross positive interval equity P&L: 20.3513551813
- gross negative interval equity P&L: 7.4465496151
- winning intervals: 105
- losing intervals: 72
- rebalance dates captured: 176
- measured intervals: 177

Interpretation: the rebalance-interval PF is the closer analogue to conventional trade PF for Stage21, but it is still a portfolio-interval metric rather than per-security closed-trade PF. The daily PF is useful as a path-quality diagnostic and should not be compared mechanically with conventional trade-system PF thresholds.
