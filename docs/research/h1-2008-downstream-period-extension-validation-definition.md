# H1 2008 Downstream Period-Extension Validation Definition

Defined: 2026-09-09 JST after the H1-2008 strict Series source run passed its pre-defined source-period validation and before H1-2008 holdings, parser-invariance, structural mapping, PIT country, frozen-builder, or stitched historical-Universe results are evaluated.

This is not a new named gate and does not authorize Stage21 performance analysis.

## Fixed source lineage

- authoritative H1 2008 strict source run: `34311526482`
- authoritative H1 2008 strict source artifact: `10088832684`
- source catalog SHA256: `31ac8ca8df99093cbcf98b916e599969481a77fcfda7cea915b3f415f8c09fbc`
- source period-extension validation: PASS under `docs/research/h1-2008-source-period-extension-validation-definition.md`
- closed source history `2006-01` through `2007-12` reproduced exactly at `sourceFilings` level before the H1-2008 source artifact was accepted.

## Fixed closed historical-Universe prefix

- closed 24-month historical-Universe stitch run: `34193003030`
- closed 24-month artifact: `10042873354`
- coverage: `2006-01` through `2007-12`
- artifact digest: `sha256:a8d1955fd406121e214af7dec4cf69058895573e0ad055b2e8a54d4101103f87`
- frozen historical-Universe builder git blob: `1357402f34dfea1c1dbdcaac7de5078b680eb5c3`
- the closed 24 monthly snapshots are immutable inputs. H1-2008 downstream processing must not rebuild, rewrite, reorder, repair, or otherwise mutate them.

## H1 2008 signal months

The only new suffix signal dates are:

- `2008-01-31`
- `2008-02-29`
- `2008-03-31`
- `2008-04-30`
- `2008-05-30`
- `2008-06-30`

## Required downstream invariants

- Raw holdings must reuse the frozen authoritative parser semantics and only mechanical Series-ID/schema adaptation required by the accepted H1-2008 source catalog.
- Any source filing already present in a previously validated holdings artifact must reproduce the same parser-semantic holding output; drift is a stop condition.
- Only complete public portfolio schedules from the accepted source catalog may enter holdings extraction. Amendment treatment remains frozen: an amendment replaces a source only when the amendment itself contains the complete portfolio schedule.
- Structural mapping must reuse the frozen accepted mapping rules only: exact normalized issuer; unique ADR-base identity; accepted trailing share-class/jurisdiction/footnote cleanup followed by exact identity; and unique long prefix of at least 20 characters only when the candidate identity union is exactly one.
- Structural mapping must not use ticker inference, fuzzy/edit-distance matching, current metadata repair, future identity backfill, rank/return/outcome inference, or strategy data.
- Any proxy-voting / N-PX or other identity master used for structural mapping must be selected point-in-time from filings public by each H1-2008 signal date. A later master may not be backfilled into an earlier month merely because it is available by 2008-06-30.
- PIT country must reuse the frozen strict country resolver semantics. Historical country evidence used for a signal month must satisfy `evidenceDateFiled <= asOf`.
- Country primary evidence remains: explicit historical country section where available; alphabetic CINS or explicit ADR/GDR/ADS/depositary-receipt evidence implies NON_US; SEC filing-time evidence only. Current ticker metadata may seed a CIK but current state/country must not be used as historical evidence.
- UNKNOWN country remains UNKNOWN in the primary path.
- CORP bridge semantics remain frozen. Positive mapped COMMON_EQUITY rows must not silently redefine known non-CORP security names as CORP.
- Source eligibility remains frozen and is evaluated only after holding filtering: source-name exclusions; 10-120 retained holdings; retained total weight at least 50; retained top-10 weight at least 25.
- Source-name exclusions must not be relaxed.
- Aggregation and breadth remain frozen: retain `etfCount >= 2 || maxWeight >= 4`; score `3*log1p(etfCount)+0.5*log1p(aggregateWeight)+0.5*log1p(recencyWeight)`; Top80.
- `scripts/research-historical-universe-builder.py` must remain exactly git blob `1357402f34dfea1c1dbdcaac7de5078b680eb5c3`.
- Builder input catalog lineage must be fixed to source artifact `10088832684` and source catalog SHA256 `31ac8ca8df99093cbcf98b916e599969481a77fcfda7cea915b3f415f8c09fbc`.
- Jan-Jun 2008 frozen-builder output must match the independent primary Universe rows produced by the frozen downstream diagnostic path exactly for all six signal months, including as-of, eligible source count, full ranked rows, scores, and symbol-level metrics.
- The closed `2006-01` through `2007-12` 24-month historical-Universe artifact must remain exact and byte/provenance-bound as specified above. The new process may append only six H1-2008 snapshots after downstream validation passes.

## Prohibited

Do not use Stage21 returns, ranks, CAGR, MaxDD, Calmar, trades, portfolio outcomes, or any other strategy performance/output to choose or revise source discovery, parsing, mapping, country, source eligibility, breadth, scoring, ranking, or Universe reconstruction rules. Do not run broad Stage21 2006-2018 performance. Do not modify `main` or Production.

## PASS condition

PASS requires all fixed source, parser, structural-mapping, PIT-country, CORP-bridge, eligibility, frozen-builder, no-lookahead, no-strategy-leakage, and closed-prefix invariants above to hold exactly for all six H1-2008 signal months. Any mismatch must be audited as an implementation/data-lineage failure rather than accommodated by changing the frozen rules after results are known.
