# H2 2007 Structural Mapping Validation Definition

Defined: 2026-09-08 JST before any H2-2007 structural-mapping result is produced.

This is a downstream validation definition under `docs/research/h2-2007-downstream-period-extension-validation-definition.md`. It is not a new named gate and does not authorize Stage21 performance analysis.

## Fixed holdings lineage

- strict Series source run `34188233028`
- strict Series source artifact `10041257985`
- source catalog SHA256 `9ffed81a42044f7388221a60450a24967ea61f108eb63f66464699ada1849631`
- H2 holdings run `34188353154`
- H2 holdings artifact `10041300366`
- holdings input file `nq-pit-holdings-series-id-h2-2007.json`
- expected source-Series counts Jul-Dec: `465, 469, 499, 518, 531, 533`

## Frozen mapping semantics

The accepted mapping implementation is exactly:

- `scripts/research-nq-catalog-structural-mapping-h1-2006.py`
- git blob `690479017fc82dce2480ded5d1ffafbb76721722`

Its imported baseline/structural mapping implementations remain the frozen repository files. No match rule may be reimplemented, broadened, or adapted from H2 coverage.

Accepted methods remain only those already implemented by the frozen mapper: baseline exact normalized issuer, unique ADR base, accepted structural suffix exact, and unique >=20-character long prefix. Fuzzy/edit-distance candidates remain non-accepted.

## Required N-PX lineage

Mapping is prohibited until the separately pre-defined H2-2007 PIT N-PX validation in `docs/research/h2-2007-npx-pit-master-validation-definition.md` has a PASS artifact with six monthly masters.

The mapping workflow must pin that successful run/artifact by numeric ID and must consume exactly these monthly PIT masters:

- `2007-07` / `2007-07-31`
- `2007-08` / `2007-08-31`
- `2007-09` / `2007-09-28`
- `2007-10` / `2007-10-31`
- `2007-11` / `2007-11-30`
- `2007-12` / `2007-12-31`

For each month, the N-PX master `asOf` must equal that holdings signal date. The frozen pre-2007 master is closed evidence. Every incremental 2007 N-PX record/source must have `sourceFilingDate <= signal date` and `admittedAtSignal <= signal date`.

A later monthly master must never be substituted for an earlier month even if it improves mapping coverage.

## Mechanical execution rule

For each H2 month independently:

1. construct a temporary holdings JSON containing only that unchanged input `monthSnapshot`;
2. point the frozen mapper's `RAW` global at that temporary file;
3. point the frozen mapper's `NPX` global at the matching monthly PIT N-PX master;
4. point the frozen mapper's `OUT` global at a temporary output;
5. call the frozen mapper's `main()` exactly once;
6. collect the single resulting mapped snapshot without changing any mapping field.

After all six calls, mechanically combine the six mapped snapshots in chronological order and attach lineage metadata. No cross-month identity carry, current ticker map, current country, later N-PX identity, return, rank, or strategy outcome may be consulted.

## PASS assertions

PASS requires all of the following:

- frozen mapper blob assertion passes before execution;
- holdings artifact/source SHA lineage exactly matches the fixed values above;
- the H2 holdings input has exactly the six fixed signal months/dates and source-Series counts above;
- the pinned N-PX audit has status `PASS`, zero PIT violations, and zero selected-source fetch errors;
- each mapper call receives only the same month's holdings snapshot and same month's PIT N-PX master;
- each mapper output has exactly one month and the matching signal month/date/source-Series count;
- source filing identities and COMMON_EQUITY holding base fields are unchanged except for the mapping fields added by the frozen mapper;
- every `MATCHED_UNIQUE` row is produced by a frozen accepted match method; no fuzzy/edit-distance acceptance exists;
- six output snapshots are present in Jul-Dec chronological order;
- mapping coverage metrics may be reported for audit but may not cause any source, parser, identity, or mapping-rule change.

Any mismatch is a stop condition before country resolution.

## Prohibited

Do not use Stage21 returns, ranks, CAGR, MaxDD, Calmar, trades, portfolio outcomes, strategy outcomes, current-country backfill, future Series/Class evidence, or later N-PX filings to repair earlier months. Do not modify `main` or Production.
