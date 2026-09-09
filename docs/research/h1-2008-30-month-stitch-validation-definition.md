# H1 2008 30-Month Historical-Universe Stitch Validation Definition

Defined: 2026-09-09 JST after H1-2008 downstream frozen-builder exact parity passed and before any 30-month stitched result is produced.

This is a mechanical closure validation, not a strategy-performance gate, and it does not authorize Stage21 performance analysis.

## Fixed validated inputs

Closed 24-month prefix:
- run `34193003030`
- artifact `10042873354`
- artifact name `historical-universe-builder-through-h2-2007`
- artifact digest `sha256:a8d1955fd406121e214af7dec4cf69058895573e0ad055b2e8a54d4101103f87`
- coverage `2006-01` through `2007-12`
- status PASS.

Validated H1-2008 suffix:
- downstream exact-parity run `34354704856`
- artifact `10105210114`
- artifact name `h1-2008-downstream-period-extension-validation`
- artifact digest `sha256:b264b54551771cfcb3fb0832fa8f6ef293d435f15db98c0f3170b8848bdf6906`
- source catalog SHA256 `31ac8ca8df99093cbcf98b916e599969481a77fcfda7cea915b3f415f8c09fbc`
- frozen builder blob `1357402f34dfea1c1dbdcaac7de5078b680eb5c3`
- downstream validator blob `79529399552a9c4520b5e6ce205944038da1b370`
- exact frozen-builder parity PASS for all six Jan-Jun 2008 signal months.

## Mechanical stitch rule

1. Read the validated 24-month artifact as the closed prefix. Do not rebuild or mutate any of its `monthSnapshots`.
2. Read only `historical-universe-builder-h1-2008.json` from the validated H1-2008 downstream artifact as the six-month suffix.
3. Require suffix months exactly `2008-01` through `2008-06` in order.
4. Require frozen eligibility/order/breadth metadata on prefix and suffix to be identical.
5. Concatenate the 24 prefix snapshots and six suffix snapshots without re-running source discovery, parsing, mapping, country, source eligibility, breadth scoring, ranking, or any strategy computation.
6. The resulting 30 snapshots must be exactly `2006-01` through `2008-06`, unique and ordered.
7. Re-read the output and require its first 24 snapshots to be exactly equal to the closed prefix snapshots and its final six snapshots to be exactly equal to the validated H1-2008 builder snapshots.
8. Every snapshot must retain at most 80 Universe symbols and its `asOf` must belong to its `signalMonth`.
9. Record both fixed segment run/artifact IDs, source catalog SHA, and frozen builder blob in output provenance.
10. The closed 24-month prefix is immutable. Any prefix mismatch is a stop condition; no recomputation or repair is permitted.

## PASS condition

PASS requires exact closed-prefix preservation, exact validated-suffix preservation, exact 30-month coverage/order, metadata invariance, and fixed provenance. Any mismatch is a stop condition.

No Stage21 returns, ranks, CAGR, MaxDD, Calmar, trades, portfolio outcomes, or strategy outcomes may be read or used. `main` and Production remain untouched.
