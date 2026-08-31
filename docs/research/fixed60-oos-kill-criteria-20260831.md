# Fixed60 True Forward OOS Kill Criteria

Frozen on 2026-08-31 before meaningful True Forward OOS observations accumulate.

## Purpose

Prevent post-hoc reinterpretation of Fixed60 True Forward OOS results. These criteria define in advance when the frozen Production strategy should be kept unchanged, placed under review, or rejected as a Forward candidate.

This document does not change Production strategy logic.

## Scope

- Strategy: `momentum-fixed60-2026-08-v1`
- Rule freeze: 2026-08-30
- First eligible signal close: 2026-08-31
- First eligible execution: next US open after that signal, if executable
- Evaluation basis: actual frozen Production signals and next-open execution contract
- Transaction-cost assumption for model comparison: 10 bp/side baseline; 30 bp/side stress remains a robustness reference
- Primary objective remains: after-tax Forward CAGR distribution median >= 40%, with MaxDD roughly <= 35-40%, but CAGR is not statistically interpretable from a short early OOS sample.

## Decision states

### GREEN — keep frozen, no tuning

Remain GREEN when all of the following hold:

1. Production implementation matches the frozen Fixed60 specification.
2. No material PIT violation, look-ahead, stale-data substitution, or execution-contract breach is detected.
3. Realized signal-to-fill slippage and transaction costs remain broadly compatible with the predeclared execution assumptions.
4. Drawdown remains within the historical/stress envelope and there is no structural failure pattern.
5. Short-horizon underperformance can still be explained by ordinary path variation rather than a rule/mechanics failure.

GREEN means do not tune parameters in response to recent P&L.

### AMBER — formal review, but do not optimize on OOS

Enter AMBER if any one of the following occurs:

1. Cumulative True Forward OOS drawdown reaches -30% from its OOS equity peak.
2. A single Production implementation or data-quality discrepancy is found that could have changed a trade, even if the realized P&L impact is small.
3. Average realized one-way implementation shortfall over at least 10 executed legs exceeds 30 bp relative to the next-open reference, excluding clearly documented exceptional market events.
4. At least 6 months of OOS have accumulated and the strategy is materially behind a predeclared simple benchmark while also exhibiting worse drawdown, such that the deficit cannot be attributed only to lower market exposure.
5. The observed concentration of returns becomes more extreme than the historical winner-removal stress suggests, for example if one symbol explains a majority of cumulative OOS gains after a sufficiently broad sample of trades.

AMBER action:

- freeze the Production rules unchanged;
- perform an implementation/data audit first;
- diagnose by attribution and stress tests only;
- do not retune TopN, momentum horizons, stop, circuit, recovery, or 60/40 weights using the accumulating OOS sample.

### RED — suspend/reject Fixed60 as the Forward candidate

Enter RED if any one of the following occurs:

1. True Forward OOS drawdown reaches -40% from its OOS equity peak.
2. A confirmed PIT/look-ahead/data-timing defect invalidates one or more live OOS decisions and cannot be corrected without changing the frozen historical information set.
3. A confirmed Production/backtest parity failure shows the live strategy is not the frozen strategy for a material period.
4. After at least 12 months of valid OOS, both conditions hold:
   - annualized OOS return is below 0%; and
   - MaxDD is worse than -30%.
5. After at least 24 months of valid OOS, annualized after-tax OOS CAGR is below 20% and the strategy fails to compensate with materially lower drawdown than the historical Fixed60 risk profile.
6. After at least 36 months of valid OOS, annualized after-tax OOS CAGR is below 30%. This is below the current planning center and would be strong evidence against the 40% Forward objective.
7. Any structural execution condition makes the strategy non-reproducible under the frozen close-to-next-open contract on a persistent basis.

RED action:

- suspend using Fixed60 as the primary Forward40 candidate;
- preserve the complete OOS record unchanged;
- do not rescue the strategy by post-hoc parameter tuning;
- if research continues, design a separately predeclared replacement/alpha engine and evaluate it independently.

## Horizon-specific interpretation

### 0-3 months

Do not judge CAGR. Evaluate only:

- signal correctness;
- PIT correctness;
- next-open execution reproducibility;
- transaction costs/slippage;
- stop/circuit/recovery state-machine parity;
- data freshness and universe construction.

### 3-12 months

Add:

- realized drawdown;
- turnover;
- return attribution by symbol and regime;
- benchmark-relative behavior;
- whether execution friction is materially worse than assumed.

Still do not treat annualized CAGR as a stable estimate.

### 12-24 months

Annualized return becomes a secondary diagnostic. Use RED criterion 4 only when both negative return and >30% drawdown are present.

### 24-36 months

Use the 20% after-tax CAGR floor as a formal failure threshold unless risk is materially lower than expected.

### 36+ months

Use the 30% after-tax CAGR threshold as the main Forward viability floor. A result below this level is inconsistent with the current 30% planning center and materially undermines the 40% target.

## What is explicitly not a kill criterion

The following alone do not justify a rule change or rejection:

- one bad month or quarter;
- one stop or circuit trigger;
- temporary underperformance versus QQQ;
- failure to match the historical 50.65% after-tax CAGR;
- failure to match the historical ~62% gross CAGR;
- a bootstrap percentile breach from historical resampling;
- a single losing symbol;
- missing the 40% objective over a short OOS window.

## Change-control rule

Any future modification to these criteria must be versioned with a new document and timestamp. The original 2026-08-31 criteria remain the reference for judging the first Fixed60 True Forward OOS record.
