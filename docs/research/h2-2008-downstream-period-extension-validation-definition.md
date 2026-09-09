# H2 2008 Downstream Period-Extension Validation Definition

Defined: 2026-09-10 JST, before observing any H2-2008 downstream holdings, parser-invariance, N-PX, structural-mapping, PIT-country, frozen-builder, or stitch result.

This is a suffix-extension checkpoint only and does not authorize Stage21 performance analysis.

## Fixed closed historical-Universe prefix

- closed 30-month stitch run: `34354891519`
- closed 30-month artifact: `10105279657`
- coverage: `2006-01` through `2008-06`
- artifact digest: `sha256:98b33c37a2c25413d1d180b9b54d54d38fea1013e6b7c29af2f7cafea6d81d85`
- frozen historical-Universe builder git blob: `1357402f34dfea1c1dbdcaac7de5078b680eb5c3`

The 30 closed snapshots are immutable inputs. H2-2008 processing may not rebuild, rewrite, reorder, repair, or otherwise mutate them.

## Fixed H2-2008 signal dates

- `2008-07-31`
- `2008-08-29`
- `2008-09-30`
- `2008-10-31`
- `2008-11-28`
- `2008-12-31`

## Source binding rule

Downstream execution is prohibited until the H2-2008 strict source passes `docs/research/h2-2008-source-period-extension-validation-definition.md`.

Because the accepted H2 strict-source run/artifact/digest do not exist when this definition is frozen, the first downstream workflow commit must hard-bind the authoritative accepted H2 source run ID, artifact ID, source-catalog digest, and the source-validation PASS lineage **before** any downstream workflow is dispatched. That binding commit becomes part of this frozen definition. This document must not be revised to accommodate downstream results.

## Required downstream invariants

- Raw holdings reuse the authoritative frozen parser semantics with only mechanical Series-ID/schema adaptation required by the accepted H2 source catalog.
- Shared source filings already present in the validated H1 holdings artifact must reproduce parser-semantic output exactly; drift is a stop condition.
- Only complete public portfolio schedules from the accepted source catalog may enter holdings extraction. Amendment semantics remain frozen.
- Structural mapping is limited to: exact normalized issuer; unique ADR-base identity; accepted trailing share-class/jurisdiction/footnote cleanup followed by exact identity; unique long prefix of at least 20 characters only when candidate identity union is exactly one.
- No ticker inference, fuzzy/edit-distance matching, current-metadata repair, future identity backfill, rank/return/outcome inference, or strategy data may be used for structural mapping.
- N-PX identity data is point-in-time per signal. Future issuer variants must be blocked from earlier H2 months.
- PIT country reuses the frozen resolver semantics. Historical evidence used for a signal month must satisfy `evidenceDateFiled <= asOf`.
- Country primary evidence remains explicit historical country section where available; alphabetic CINS or explicit ADR/GDR/ADS/depositary-receipt evidence implies NON_US; SEC filing-time evidence only. Current ticker metadata may seed a CIK only and current state/country may not supply historical country.
- UNKNOWN remains UNKNOWN in the primary path.
- CORP bridge semantics remain frozen. Positive mapped COMMON_EQUITY rows may not silently redefine known non-CORP security names as CORP.
- Source eligibility remains frozen and is evaluated only after holding filtering: source-name exclusions; retained holdings 10-120; retained total weight >= 50; retained top-10 weight >= 25.
- Source-name exclusions must not be relaxed.
- Aggregation and breadth remain frozen: retain `etfCount >= 2 || maxWeight >= 4`; score `3*log1p(etfCount)+0.5*log1p(aggregateWeight)+0.5*log1p(recencyWeight)`; Top80.
- `scripts/research-historical-universe-builder.py` must remain exactly git blob `1357402f34dfea1c1dbdcaac7de5078b680eb5c3`.
- The independent diagnostic and frozen builder must have exact six-month primary eligible-source and full ranked-symbol parity for all H2 signal months, including as-of, source count, full ranked rows, scores, and symbol-level metrics.
- Top80 rank invariants must hold.
- The closed 30-month prefix must remain exact and provenance-bound; only six validated H2 snapshots may later be appended.

## Parser invariance

A dedicated parser-invariance comparison must cover every source filing shared between the authoritative H1-2008 holdings artifact and H2-2008 holdings extraction. Shared filings must have exact semantic holdings output under the frozen parser. Missing/extra overlap, semantic mismatch, or parser drift is a stop condition.

## N-PX binding

H2 N-PX must satisfy `docs/research/h2-2008-npx-pit-master-validation-definition.md` and extend the authoritative H1 N-PX run `34320224950` / artifact `10091573844` without mutating its validated `2008-06` base.

## PASS condition

PASS requires all source-lineage, parser, mapping, N-PX PIT, country PIT, CORP-bridge, eligibility, frozen-builder, no-lookahead, Top80-rank, no-strategy-leakage, and closed-prefix invariants above to hold exactly for all six H2-2008 signal months.

Any mismatch must be audited as an implementation/data-lineage failure rather than accommodated by changing frozen rules after results are known.

## Final stitch

Only after downstream exact-parity PASS may a separate 36-month stitch definition be created and frozen, and it must be created before observing the stitch result. The stitch may append the six validated H2 snapshots to run `34354891519` / artifact `10105279657` only. No historical recomputation is permitted.

## Prohibited

Do not use Stage21 returns, ranks, CAGR, MaxDD, Calmar, trades, portfolio outcomes, or any other strategy performance/output to choose or revise reconstruction rules. Do not run broad 2006-2018 Stage21 performance. Do not modify `main` or Production.
