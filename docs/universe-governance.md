# Momentum Universe Governance

This document defines the rule for adding, monitoring, auditing, and removing tickers from the Momentum Universe. The purpose is to reduce ex-post universe selection, survivorship bias, and overfitting.

## Core principle

A historical backtest is a **sanity check**, not an optimizer for Universe membership.

Do not add a ticker because it increases historical CAGR. Do not remove a ticker merely because deleting it improves historical CAGR.

The production strategy parameters and the Universe are separate research decisions.

## New ticker workflow

### Stage 1 — Ex-ante candidate discovery

Identify a theme and candidate ticker from information available at the time of discovery. The reason for candidacy must be independent of historical backtest performance.

Record at minimum:

- discovery date
- proposed genre
- business/theme rationale
- ticker(s) considered

### Stage 2 — Backtest sanity check

Run the candidate through the current frozen strategy using the repository's existing Yahoo `fetchHistories` and `buildDashboard` logic.

The sanity check may inspect:

- number of months selected
- months where existing picks change
- selected-month holding returns
- MaxDD and volatility impact
- genre/frontier concentration
- whether the ticker can actually qualify under the strategy

Historical CAGR improvement is **not** an adoption criterion.

A candidate must not be selected from a large candidate pool by choosing whichever ticker maximizes historical CAGR.

### Stage 3 — Watchlist

A candidate that passes the sanity check enters a watchlist. It does not automatically enter the production Universe.

### Stage 4 — Forward evidence

Evaluate evidence generated after the candidate's discovery date. Prefer forward/out-of-sample observations over retrospective fit.

Adoption may be considered only after the candidate shows useful forward behavior under the frozen strategy and still has a valid business/theme rationale.

## Existing / legacy Universe audit

Legacy tickers are periodically audited against periods that predate the current optimization window when data permits. The audit is diagnostic; it is not a deletion optimizer.

For the initial legacy audit, use the frozen strategy parameters and evaluate pre-2023 history available from the repository's Yahoo data path. Because Yahoo history currently begins at 2020-01-01 and the strategy requires a 10-month QQQ moving-average warm-up, the effective tradable audit window begins only after sufficient history exists.

Classify each ticker as follows. Classification thresholds are fixed before viewing the audit result.

### A — Supported

All of the following are true in completed pre-2023 audit months:

- selected at least 3 times
- average selected-month holding return is greater than 0%
- selected-month win rate is at least 50%

### B — Limited or mixed evidence

Pre-2023 price history exists, but the ticker does not meet either the A or D definition. This includes tickers selected fewer than 3 times and tickers with mixed outcomes.

### C — Not testable pre-2023

There is insufficient pre-2023 history to form the required momentum lookbacks, or no usable pre-2023 price history exists.

### D — Adverse legacy evidence

All of the following are true in completed pre-2023 audit months:

- selected at least 3 times
- average selected-month holding return is below 0%
- selected-month win rate is below 50%

A D classification does **not** trigger automatic removal. It triggers review only.

## Removal rule

Do not remove a ticker solely because retrospective removal improves CAGR, MaxDD, Calmar, or any other aggregate backtest metric.

Removal should normally require one or more independent reasons such as:

- the original investment theme is no longer valid
- the ticker no longer represents its assigned genre
- liquidity/listing/instrument structure makes the ticker unsuitable
- persistent forward evidence shows the ticker is structurally incompatible with the strategy

Historical backtest evidence may support the decision but must not be the sole reason.

## Strategy changes and Universe changes

Avoid tuning strategy parameters and Universe membership on the same historical sample at the same time. If the strategy is frozen for forward validation, candidate research must not rewrite that frozen benchmark.

## Research reporting

Every Universe research report should distinguish:

- ex-ante rationale
- retrospective sanity-check evidence
- forward/out-of-sample evidence
- final action: reject, watch, adopt, or review

When evidence is insufficient, prefer `watch` over `adopt` or `remove`.
