# H2 2007 24-Month Historical-Universe Stitch Validation Definition

Defined: 2026-09-08 JST after H2-2007 downstream frozen-builder exact parity passed and before any 24-month stitched result is produced.

This is a mechanical closure validation, not a new named gate, and does not authorize Stage21 performance analysis.

## Fixed validated inputs

Closed 18-month prefix:
- run `34186850426`
- artifact `10040792563`
- artifact name `historical-universe-builder-through-h1-2007`
- coverage `2006-01` through `2007-06`
- status PASS.

Validated H2-2007 suffix:
- downstream exact-parity run `34192853738`
- artifact `10042811090`
- artifact name `h2-2007-downstream-period-extension-validation`
- frozen builder blob `1357402f34dfea1c1dbdcaac7de5078b680eb5c3`
- downstream validator blob `72ae7532458d35e09b4b98bf221fbd566970aa07`
- source catalog SHA256 `9ffed81a42044f7388221a60450a24967ea61f108eb63f66464699ada1849631`
- exact frozen-builder parity PASS for all six Jul-Dec 2007 signal months.

## Mechanical stitch rule

1. Read the validated 18-month artifact as the closed prefix. Do not rebuild or mutate any of its `monthSnapshots`.
2. Read only `historical-universe-builder-h2-2007.json` from the validated H2 artifact as the six-month suffix.
3. Require suffix months exactly `2007-07` through `2007-12` in order.
4. Require the frozen eligibility/order/breadth metadata on the prefix and suffix to be identical.
5. Concatenate the 18 prefix snapshots and six suffix snapshots without re-running source discovery, parsing, mapping, country, source eligibility, breadth scoring, ranking, or any strategy computation.
6. The resulting 24 snapshots must be exactly `2006-01` through `2007-12`, unique and ordered.
7. Re-read the output and require its first 18 snapshots to be exactly equal to the closed prefix snapshots and its final six snapshots to be exactly equal to the validated H2 builder snapshots.
8. Every snapshot must retain at most 80 Universe symbols and its `asOf` must belong to its `signalMonth`.
9. Record both fixed segment artifact IDs and the frozen builder blob in the output provenance.

## PASS condition

PASS requires exact closed-prefix preservation, exact validated-suffix preservation, exact 24-month coverage/order, metadata invariance, and fixed provenance. Any mismatch is a stop condition.

No Stage21 returns, ranks, CAGR, MaxDD, Calmar, trades, portfolio outcomes, or strategy outcomes may be read or used. `main` and Production remain untouched.