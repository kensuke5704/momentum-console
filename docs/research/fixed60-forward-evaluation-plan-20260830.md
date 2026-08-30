# Fixed60 True Forward Evaluation Plan — frozen 2026-08-30

## Purpose

Evaluate whether the frozen Fixed60 research candidate can support a long-run after-tax Forward CAGR objective around 40% without using historical re-optimization after the freeze date.

This document defines evidence collection and decision rules. It does not change Production/main.

## Start of Fixed60-specific True Forward OOS

- Freeze date: 2026-08-30.
- Fixed60-specific True Forward observations begin on the first eligible US trading session after the freeze.
- Data before the freeze remain historical or pseudo-OOS for Fixed60 even if they were previously held out for older architectures.

## Frozen strategy under evaluation

Use `docs/research/fixed60-candidate-spec-20260830.md` as the authoritative Fixed60 definition.

Do not change:

- 60/40 Top2 weights,
- universe construction,
- momentum formula,
- market filter,
- Stop/Circuit/Recovery state-machine rules,
- next-session-open execution convention,
- transaction-cost assumption,
- leverage constraint,

without starting a new candidate and a new forward clock.

## Core Forward measurements

Record, at minimum:

- pre-tax equity and CAGR,
- simplified after-tax equity and CAGR when enough realized activity exists,
- MaxDD,
- annualized volatility,
- Calmar,
- exposure share,
- turnover and sale count,
- realized and unrealized P&L,
- worst rolling period,
- selected symbols and concentration by repeated winner/theme,
- state-machine events: Market RiskOff, Stop, Circuit, Recovery,
- deviations caused by missing prices, stale data, execution failure, or manual intervention.

## 40% interpretation

Historical Fixed60 simplified after-tax CAGR of about 50.65% is not the Forward point estimate.

Current sensitivity evidence implies:

- gross CAGR remains about 47.33% under 80% favorable-regime edge retention,
- gross CAGR remains about 50.88% under 85% retention,
- gross CAGR remains about 40.49% under 70% retention,
- historical simplified after-tax drag was material enough that gross 40% is not sufficient for after-tax 40%.

Therefore a Forward after-tax CAGR near 40% requires substantial retention of the historical edge. The existing evidence is consistent with 40% being plausible, but does not justify calling 40% the expected value yet.

## Evidence hierarchy

Use evidence in this order:

1. Fixed60-specific live/forward observations after the freeze.
2. Frozen-rule anchored or rolling historical diagnostics that were specified before observing the tested segment.
3. Leave-one-ticker-out and structural stress as robustness evidence.
4. Full-period historical CAGR only as background.
5. CPCM or chronology-destroying simulations only as secondary cautionary diagnostics, not as the central expected-return estimator.

## Promotion / rejection logic

Do not promote Fixed60 to Production because of one strong month, one strong year, or a higher historical CAGR.

Increase confidence only when forward observations are directionally consistent with the frozen mechanism and do not reveal materially worse drawdown, turnover, tax drag, execution slippage, or concentration dependence than the historical diagnostics imply.

Reduce confidence if any of the following occurs persistently:

- realized performance is materially below the range implied by historical robustness diagnostics,
- repeated dependence on one ticker or one narrow theme becomes stronger,
- MaxDD or volatility materially exceeds the historical stress envelope,
- operational execution differs from the frozen next-open rules,
- the candidate requires a rule change to explain or rescue poor forward results.

Any rule change creates a new candidate and resets the relevant True Forward clock.

## Bridge and cash carry

- Recovery QQQ50 K1 is an optional overlay and is excluded from Fixed60's central Forward estimate until separately frozen for Fixed60.
- Historical K1 uplift must not be added to the central estimate because K3/K5 deterioration shows timing fragility.
- Cash/T-bill carry may be tracked separately as an operational return source. Historical simplified after-tax uplift was positive, but future carry depends on prevailing rates and implementation. It is not alpha and should not be used to claim that the core strategy itself reaches 40%.

## Current decision at freeze

Fixed60 is retained as the leading research candidate. The 40% Forward CAGR objective remains unconfirmed. Production/main remains unchanged pending separate approval and sufficient Fixed60-specific True Forward evidence.
