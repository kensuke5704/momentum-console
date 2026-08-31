# Fixed60 True Forward OOS evaluation protocol — frozen 2026-09-01

## Purpose
Evaluate the frozen Fixed60 strategy using genuinely post-freeze observations without adapting the rule to the realized OOS path. This document defines what is measured, when it is interpreted, and what can trigger review or rejection.

## OOS clock
- Rule freeze: 2026-08-30.
- First eligible signal close: 2026-08-31 US close.
- First eligible execution: next US open after that signal when executable.
- Pre-freeze observations are not admissible as True Forward OOS.

## Phase 0 — implementation validation: 0 to <3 months
Do not interpret CAGR as evidence of strategy quality.

Primary checks:
- exact PIT universe and signal date;
- displayed signal equals state-machine signal;
- next-open execution date is correct;
- realized entry/exit prices are traceable to the intended session;
- configured 10bp one-way cost is applied consistently in the recorded OOS equity;
- Stop 17.5%, Circuit 15%, and Recovery state transitions match the frozen rule;
- no confirmed OOS date is rewritten except an explicitly provisional Yahoo close row when the completed adjusted row arrives.

Any implementation mismatch is a blocking defect. Fix the implementation, preserve the raw audit trail, and do not classify the mismatch as investment performance.

## Phase 1 — descriptive OOS: 3 to <12 months
Still do not use CAGR alone to accept or reject the strategy.

Report at each monthly checkpoint:
- cumulative gross return;
- gross CAGR, clearly labelled as short-horizon descriptive only;
- MaxDD;
- annualized volatility;
- monthly return distribution;
- exposure share and Cash share;
- turnover / number of executions;
- realized execution slippage versus the intended next-open reference when available;
- Top1/Top2 contribution concentration and largest single-name contribution share.

No strategy parameter may be changed because of these diagnostics.

## Phase 2 — first performance checkpoint: 12 to <24 months
Interpret performance jointly with drawdown.

Predeclared hard rejection:
- RED if OOS gross CAGR < 0% **and** OOS MaxDD < -30%.
- RED at any horizon if OOS MaxDD <= -40%.

Review state:
- AMBER if OOS MaxDD <= -30% but the hard rejection condition above is not met.

A failure to match the historical 50%+ after-tax CAGR or roughly 62% gross CAGR is not itself a failure criterion.

## Phase 3 — tax-aware checkpoint: 24 to <36 months
The decision metric is after-tax CAGR, not gross CAGR.

Required before classification:
- compute OOS after-tax equity from realized OOS trades under the same documented Japanese tax approximation used for the authoritative Fixed60 historical after-tax study;
- keep gross OOS figures visible separately.

Predeclared decision:
- RED if after-tax CAGR < 20%.
- AMBER if an exact after-tax series is not yet available; do not substitute an inferred tax haircut.
- Otherwise continue unless another hard rejection rule is active.

## Phase 4 — strategy-objective checkpoint: >=36 months
Primary objective: after-tax Forward CAGR >= 40% with drawdown consistent with the Fixed60 risk envelope.

Predeclared classification:
- GREEN: after-tax CAGR >= 40% and MaxDD > -40%.
- AMBER: after-tax CAGR >= 30% and <40%, with MaxDD > -40%.
- RED: after-tax CAGR <30%, or MaxDD <= -40%.

The 40% threshold is a Forward objective. It is not backfilled from the historical sample and must not be relaxed after seeing OOS results.

## Robustness diagnostics at >=36 months
These diagnostics do not replace the primary OOS result:
- +10bp and +20bp additional one-way cost replay;
- +1 session execution-delay replay;
- winner-removal / contribution concentration analysis;
- rolling 12M and 24M subperiods;
- compare realized volatility and drawdown with the historical Fixed60 reference without treating historical bootstrap bands as calibrated future probabilities.

## Governance
- No momentum-weight, TopN, allocation, Stop, Circuit, Recovery, or universe-rule tuning is permitted on the accumulating Fixed60 OOS series.
- A replacement strategy must be researched on a separate branch/engine and must not overwrite Fixed60 OOS history.
- GREEN/AMBER/RED thresholds can only be changed prospectively for a newly frozen strategy version, never retroactively for `momentum-fixed60-2026-08-v1`.
