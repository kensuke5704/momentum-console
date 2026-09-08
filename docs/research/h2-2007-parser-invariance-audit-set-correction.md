# H2 2007 Parser-Invariance Audit-Set Correction

Date: 2026-09-08 JST

## Status

This is an audit-definition correction after the first H1-vs-H2-2007 parser-invariance run failed. It does not change the holdings parser, source catalog, source evidence, mapping, country, eligibility, ranking, or any strategy rule.

## Initial audit

Run `34188489347` compared the H1-2007 and H2-2007 holdings artifacts and reported:

- H1 unique holdings filing records: 847
- H2 unique holdings filing records: 1,169
- actual holdings overlap: 258
- exact full-record matches on that overlap: **258 / 258**
- legacyIdentity-only differences: 0
- parser-semantic mismatches: **0**
- apparent source-only missing records: 589

The 589 apparent missing records were not parser failures. The audit constructed its expected source overlap from both `closedHistoryReplaySnapshots` and `monthSnapshots` in the H2 source catalog, while the H2 holdings run intentionally consumed only the H2 Jul-Dec `monthSnapshots`. Therefore the audit incorrectly required closed Jan-Jun replay source records to exist in an H2 holdings artifact that never received them as inputs.

## Correct expected-overlap set

For parser invariance, the expected source overlap must be the intersection of the **current-period source snapshots actually supplied to each holdings run**:

- H1 2007: H1 Jan-Jun `monthSnapshots`
- H2 2007: H2 Jul-Dec `monthSnapshots`

The parser-invariance script is corrected only so `unique_source_keys()` reads `monthSnapshots`. The holdings records, parser implementation, parser blobs, source catalogs, thresholds, and comparison semantics remain unchanged.

## Required result

The corrected audit must still require:

- a non-empty independently derived source overlap;
- exact equality between expected source overlap and actual holdings overlap;
- zero parser-semantic mismatches after excluding only the existing `legacyIdentity` schema metadata field.

No Stage21 returns, ranks, trades, CAGR, MaxDD, Calmar, portfolio outcomes, or strategy outcomes were inspected or used in this correction.
