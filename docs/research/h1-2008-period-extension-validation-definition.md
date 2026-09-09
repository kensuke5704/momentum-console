# H1 2008 Historical-Universe Period-Extension Validation Definition

Defined: 2026-09-09 JST, before observing any H1-2008 strict Series-source, holdings, structural-mapping, PIT-country, frozen-builder, or 30-month stitch result.

This is a period-extension validation, not a new named gate, and does not authorize Stage21 performance analysis.

## Scope

This checkpoint governs only the Jan-Jun 2008 extension of the already closed historical reconstruction. The closed prefix remains 2006-01 through 2007-12 and must not be recomputed, re-optimized, or rewritten.

Fixed H1-2008 signal dates:

- 2008-01-31
- 2008-02-29
- 2008-03-31
- 2008-04-30
- 2008-05-30
- 2008-06-30

## Fixed prior lineage

- closed H2-2007 strict Series source run: `34188233028`
- closed H2-2007 strict Series source artifact: `10041257985`
- H2-2007 source-catalog SHA256: `9ffed81a42044f7388221a60450a24967ea61f108eb63f66464699ada1849631`
- closed 24-month historical-Universe stitch run: `34193003030`
- closed 24-month historical-Universe stitch artifact: `10042873354`
- closed 24-month artifact digest: `sha256:a8d1955fd406121e214af7dec4cf69058895573e0ad055b2e8a54d4101103f87`
- exact closed coverage: `2006-01` through `2007-12`
- frozen historical builder blob: `1357402f34dfea1c1dbdcaac7de5078b680eb5c3`

## Frozen extension semantics

The H1-2008 extension must reuse the already validated H2-2007 implementation semantics. Only the open period may extend.

- Candidate-prefilter discovery remains recall-oriented only and is never final ETF evidence.
- A candidate CIK already known at the closed H2-2007 boundary may be carried forward only at the candidate layer.
- A CIK first discovered in H1-2008 must not be backfilled into any closed 2006-2007 snapshot merely because later evidence exists.
- Final positive Series acceptance must be independently established using contemporaneously public issuer-own operational ETF evidence and the frozen structural Series/Class binding rules.
- No trust-global sibling binding and no registrant/trust name may substitute for Series identity.
- No fuzzy/edit-distance identity repair, ticker inference, holdings/rank/return/outcome inference, or strategy-data inference is allowed.
- No future Series/Class, country, or issuer-variant backfill is allowed.
- Complete-portfolio forms and amendment-replacement semantics remain unchanged.
- Conventional mutual-fund siblings, including Vanguard siblings that do not independently satisfy the ETF evidence rule, remain excluded.

## Source-stage invariants

Before any H1-2008 strict Series-source result is accepted, a source-specific validation definition must bind the exact cumulative inventory and candidate-prefilter lineage used for the run.

PASS requires:

1. cumulative N-Q and complete-portfolio inventories replay the authoritative closed inventory prefix exactly;
2. closed candidate-discovery boundaries remain fixed, so newly discovered H1-2008 CIKs cannot alter 2006-2007 source snapshots;
3. every previously accepted H2-2007 positive Series retains its authoritative Series identity and binding when replayed under the same PIT evidence set;
4. all closed 2006-01 through 2007-12 source snapshots remain exact at the `sourceFilings` level;
5. H1-2008 consists of exactly the six fixed signal dates above;
6. every source occurrence and ETF operational evidence item used for a signal snapshot is public no later than that signal date;
7. Series identity conflicts, prospectus/source errors that would make the catalog incomplete, and unauthorized sibling admissions are stop conditions;
8. `sourceNoSchedule` remains audit-only and may not enter `sourceOccurrences`.

## Downstream invariants

Only after the strict source stage passes its pre-defined validation may downstream H1-2008 processing execute.

Before observing downstream H1-2008 results, a downstream validation definition must bind the authoritative H1-2008 source artifact and catalog digest.

The downstream path must preserve all frozen semantics:

- raw holdings use the frozen authoritative parser semantics with only mechanical schema adaptation where required;
- shared source filings must satisfy parser-semantic output invariance;
- structural mapping is limited to the already accepted frozen methods and uses no fuzzy or outcome-informed repair;
- any N-PX identity master is point-in-time for each signal date; later annual identity data may not be backfilled into earlier signals;
- PIT country evidence must satisfy `evidenceDateFiled <= asOf` for each signal month;
- UNKNOWN remains UNKNOWN in the primary path;
- CORP bridge materiality semantics remain unchanged;
- `scripts/research-historical-universe-builder.py` remains frozen at blob `1357402f34dfea1c1dbdcaac7de5078b680eb5c3`;
- Jan-Jun 2008 frozen-builder output must exactly match the independent primary-Universe rows produced by the validated downstream diagnostic path for all six months, including signal/as-of, eligible source count, full ranked rows, scores, and symbol-level metrics;
- the closed 24-month artifact `10042873354` must remain byte/row semantically exact for 2006-01 through 2007-12; a 30-month stitch may append only the validated six H1-2008 snapshots and may not rerun the closed prefix.

## Prohibited

Do not use Stage21 returns, ranks, CAGR, MaxDD, Calmar, trades, portfolio outcomes, or any other strategy performance to choose or revise source discovery, parsing, identity, mapping, country, eligibility, breadth, reconstruction, or validation rules.

Do not modify `main` or Production.

Broad 2006-2018 Stage21 performance remains prohibited.

## Failure handling

Any replay, PIT, identity, parser, mapping, country, builder-parity, lineage, or closed-prefix invariant failure is a stop condition. Audit the implementation or evidence lineage; do not relax or tune the frozen rules after observing the result.
