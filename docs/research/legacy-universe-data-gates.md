# Legacy Universe Data-Quality Gates

Last updated: 2026-09-03 JST

These gates are evaluated without using strategy returns. They must be satisfied before opening historical Stage21 performance windows.

## Gate A — point-in-time integrity

- Every source filing used for an as-of date must have `filingDate <= asOf`.
- Selection is the latest publicly filed record per SEC `seriesId`; ties use accession ordering only.
- `reportDate` is descriptive and may precede `filingDate`; report-date information must never be treated as public before filing date.
- No constituent ticker may be selected because of future listing survival or future price availability.

PASS requirement: zero known look-ahead violations in deterministic audits.

## Gate B — schedule-to-series integrity

- Series mapping uses filing-time SGML series/class metadata and local schedule-heading context.
- Ambiguous ties/near-ties are rejected rather than forced.
- A fixed semantic-anchor audit must show that known sector/fund holdings are attached to the intended series and not neighboring schedule blocks.

PASS requirement: all fixed semantic anchors pass and there is no known cross-series contamination in retained records.

## Gate C — security identity coverage

Accepted automatic identities:
- Tier A: unique exact normalized issuer match to one N-PX ticker + security-id identity.
- Tier B: only when no Tier A identity exists, normalized issuer maps to exactly one structurally valid ticker and security-id is missing.
- Fuzzy matches remain diagnostic-only.
- Ambiguous ADR/share-class/security identities are not automatically accepted.

PASS requirements before constructing performance history:
- aggregate accepted identity weight rate >= 80%
- median retained-series accepted identity weight rate >= 75%
- no parser/header token may be admitted as a ticker

A year that fails the gate may be structurally improved, but not by consulting strategy returns.

## Gate D — legacy equity proxy

The proxy for N-PORT `US/CORP/EC` uses only explicit structural evidence:
- explicit ADR/GDR/depositary receipt -> exclude non-US proxy
- explicit debt/preferred/options/warrants/rights -> exclude non-EC proxy
- explicit LP/limited partnership/LLC legal form -> exclude non-CORP proxy
- accepted identity with no explicit exclusion -> `LEGACY_EQUITY_CANDIDATE`

Do not infer country from issuer spelling, historical return behavior, or whether excluding a name improves performance.

## Gate E — ETF structural eligibility

Mirror production `isEligibleEtf` economics:
- exclude structured/income/broad-benchmark series by the frozen production-style name rules
- 10 <= holdings <= 120
- total positive normalized weight >= 50 (legacy normalized records normally sum to 100)
- top-10 weight >= 25

No thresholds may be changed to improve historical Stage21 results.

## Gate F — universe scoring parity

Legacy universe scoring is frozen to the production formula:

`3*log1p(etfCount) + 0.5*log1p(aggregateWeight) + 0.5*log1p(recencyWeight)`

with:
- latest public filing per series
- `recencyFactor = exp(-ageDays / 120)`
- eligibility at security level: `etfCount >= 2 OR maxWeight >= 4`
- sort by score desc, ETF count desc, aggregate weight desc, ticker asc
- take up to Top80

If fewer than 80 securities satisfy the frozen rules, retain the smaller universe and record its size. Do not backfill with future constituents or loosen rules merely to force 80 names.

## Gate G — historical data staging

Structural/data-quality diagnostics may use 2006–2018 filings in full.

Strategy-performance history is opened sequentially under `legacy-history-evaluation-protocol.md`:
1. DEVELOPMENT 2006–2010
2. VALIDATION 2011–2014
3. SEALED_HOLDOUT 2015–2018

Performance from a later phase may not be inspected to repair or select earlier reconstruction rules.
