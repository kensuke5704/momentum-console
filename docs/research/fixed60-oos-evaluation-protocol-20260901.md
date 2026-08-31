# Fixed60 True Forward OOS evaluation protocol — 2026-09-01

## Purpose

Pre-register how Fixed60 True Forward OOS will be evaluated before meaningful OOS performance accumulates. This protocol is for evidence discipline; it does not change Production strategy rules.

## Frozen clock

- Rule freeze: 2026-08-30
- First eligible signal close: 2026-08-31
- First eligible execution: next US open
- Strategy: `momentum-fixed60-2026-08-v1`

## Evaluation hierarchy

### 0–3 months: implementation integrity only

Do not use CAGR as evidence for strategy quality. Review only:

- exact signal date / PIT Universe alignment
- displayed signal == state-machine-confirmed signal
- next-open execution timing
- transaction-cost application
- stop / circuit / recovery state transitions
- provisional vs confirmed market-data replacement
- missing/stale data fail-closed behavior
- realized slippage versus the model's next-open assumption, when actual execution records are available

Immediate risk gates remain active: OOS MaxDD <= -30% => AMBER review; <= -40% => RED.

### 3–12 months: descriptive performance, no acceptance claim

Track but do not optimize against:

- cumulative return
- gross CAGR, clearly labelled tax-before
- MaxDD
- annualized volatility
- Calmar
- monthly hit rate and return dispersion
- turnover / realized trading-cost gap

No strategy replacement or parameter tuning may be justified solely by this window unless a pre-registered RED kill criterion is hit.

### 12–24 months: first structural review

In addition to the above:

- compare observed path with historical stress envelopes only as diagnostics, not p-values
- inspect concentration by year, symbol, sector/theme, and risk episode
- inspect whether performance is dominated by one or two winners
- verify execution/slippage remains within the historical stress budget

RED criterion already frozen: at >=12 months, CAGR < 0 and MaxDD <= -30%.

### 24–36 months: after-tax gate becomes mandatory

The formal criterion is after-tax CAGR, not displayed gross CAGR.

- If gross CAGR < 20%, RED is certain because after-tax cannot exceed gross under the adopted tax model.
- Otherwise an exact after-tax OOS series must be calculated before final GREEN/RED classification.
- Until exact after-tax calculation exists, status remains AMBER rather than using an invented haircut.

Frozen RED criterion: after-tax CAGR < 20% at >=24 months.

### 36+ months: Forward40 evidence stage

Primary metrics:

- after-tax CAGR
- MaxDD
- rolling 12/24/36-month returns
- realized execution-cost and delay sensitivity
- winner-removal / concentration diagnostics using only data accumulated after freeze

Frozen RED criterion: after-tax CAGR < 30% at >=36 months.

The strategic objective remains a Forward after-tax CAGR distribution median >=40%; observed 36-month CAGR alone is not treated as a statistically calibrated distribution median.

## Anti-selection-bias rules

- Do not tune 0/20/80 weights, TopN, 60/40 allocation, stop, circuit, recovery, surge limit, or QQQ market gate from the same accumulating OOS sample.
- Do not redefine GREEN/AMBER/RED thresholds after observing outcomes.
- Any replacement strategy must be developed on evidence that is separated from the Fixed60 True Forward OOS sample as far as practicable.
- Historical 2020–2026 results remain retrospective diagnostics and must not be relabelled as Forward OOS.

## Current implementation implication

The live Action gate can fully enforce drawdown and gross-sufficient-to-fail criteria now. Before the 24-month checkpoint, an exact after-tax OOS accounting path should be implemented so the 24M/36M rules can resolve from AMBER to a definitive status without a tax proxy.
