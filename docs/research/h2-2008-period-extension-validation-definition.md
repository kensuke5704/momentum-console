# H2 2008 Historical-Universe Period-Extension Validation Definition

Defined: 2026-09-09 JST, before observing any H2-2008 strict Series-source, holdings, structural-mapping, PIT-country, frozen-builder, or 36-month stitch result.

This is a suffix period-extension validation only. It does not authorize Stage21 performance analysis or any Production change.

## Scope

This checkpoint governs only the Jul-Dec 2008 extension. The closed historical-Universe prefix is 2006-01 through 2008-06 and must remain exact and immutable.

Fixed H2-2008 signal dates:

- 2008-07-31
- 2008-08-29
- 2008-09-30
- 2008-10-31
- 2008-11-28
- 2008-12-31

## Fixed closed prefix

- closed 30-month historical-Universe stitch run: `34354891519`
- closed 30-month historical-Universe stitch artifact: `10105279657`
- closed 30-month artifact digest: `sha256:98b33c37a2c25413d1d180b9b54d54d38fea1013e6b7c29af2f7cafea6d81d85`
- exact closed coverage: `2006-01` through `2008-06`
- frozen historical builder blob: `1357402f34dfea1c1dbdcaac7de5078b680eb5c3`
- authoritative H1-2008 strict source run: `34311526482`
- authoritative H1-2008 strict source artifact: `10088832684`
- authoritative H1-2008 source SHA256: `31ac8ca8df99093cbcf98b916e599969481a77fcfda7cea915b3f415f8c09fbc`

## Frozen extension semantics

H2-2008 must reuse the already validated semantics without tuning. Only the open suffix may extend.

- Candidate discovery is recall-oriented only and never final ETF evidence.
- Candidate CIKs known at the H1-2008 boundary may carry forward only at the candidate layer.
- A CIK or Series first evidenced in H2-2008 must not be backfilled into any closed 2006-01 through 2008-06 snapshot.
- Series/Class IDs are usable only when contemporaneously public; no future identity backfill.
- Final positive Series acceptance requires contemporaneous issuer-own operational ETF evidence plus the frozen structural Series/Class binding rules.
- Registrant/trust name may not substitute for Series identity; trust-global sibling binding is prohibited.
- Broad creation-unit/exchange language is candidate-prefilter evidence only.
- Conventional mutual-fund siblings that do not independently satisfy the ETF evidence rule remain excluded.
- Complete-portfolio form coverage and amendment replacement semantics remain unchanged.
- No fuzzy/edit-distance repair, ticker inference, outcome inference, or strategy-data inference is permitted.

## Frozen historical-Universe builder semantics

The builder continues to apply, in order:

1. COMMON_EQUITY analogue;
2. conservative PIT US classification, with unresolved remaining UNKNOWN;
3. frozen CORP bridge;
4. positive weight and usable symbol;
5. latest public filing per source Series;
6. source-name exclusions;
7. retained holdings count 10-120;
8. retained total weight >= 50;
9. retained top-10 weight >= 25;
10. aggregate across eligible Series;
11. retain `etfCount >= 2 || maxWeight >= 4`;
12. score `3*log1p(etfCount)+0.5*log1p(aggregateWeight)+0.5*log1p(recencyWeight)`;
13. Top80.

Source-name exclusions must not be relaxed.

## Source-stage requirements

Before observing the H2-2008 strict Series-source result, a source-specific validation definition must bind the exact cumulative inventory, candidate-prefilter, and closed source-replay lineage used.

PASS requires:

1. authoritative closed source snapshots for 2006-01 through 2008-06 remain exact at `sourceFilings` level;
2. H2-2008 contains exactly the six fixed signal dates above;
3. newly discovered H2 evidence cannot alter a closed source snapshot;
4. every source occurrence and operational ETF evidence item is public by the applicable signal date;
5. only contemporaneously valid Series/Class identity evidence is used;
6. `sourceNoSchedule` remains audit-only and cannot enter `sourceOccurrences`;
7. identity conflict, unauthorized sibling admission, incomplete source replay, or prospectus/source error that makes the catalog incomplete is a stop condition.

## Downstream requirements

Only after source validation passes may holdings, N-PX, mapping, country, and frozen-builder execution proceed.

Before observing downstream H2-2008 results, freeze a downstream validation definition binding the accepted source artifact and digest.

- Holdings parser semantics remain frozen; mechanical schema adaptation only.
- Shared source filings must satisfy parser-output invariance.
- Structural mapping remains restricted to exact normalized issuer, unique ADR-base, accepted suffix cleanup then exact, and unique >=20-character long-prefix only when the candidate identity union is exactly one.
- N-PX identity data is point-in-time per signal; future issuer variants are blocked.
- Country evidence must satisfy `evidenceDateFiled <= signal date`.
- Alphabetic CINS and explicit ADR/GDR/ADS/depositary-receipt evidence remain NON_US.
- Current metadata may seed a CIK only and may not supply historical country.
- UNKNOWN remains UNKNOWN.
- CORP bridge semantics remain frozen.
- The builder remains blob `1357402f34dfea1c1dbdcaac7de5078b680eb5c3`.
- The independent diagnostic and frozen builder must have exact six-month primary eligible-source and full ranked-symbol parity.
- Top80 rank invariants must hold.

## Final stitch requirement

A 36-month stitch definition must be frozen only after H2-2008 downstream exact-parity PASS and before producing the stitch result.

The final stitch must:

- take run `34354891519` / artifact `10105279657` as the immutable 30-month prefix;
- verify the prefix artifact digest `sha256:98b33c37a2c25413d1d180b9b54d54d38fea1013e6b7c29af2f7cafea6d81d85`;
- append only the six validated H2-2008 frozen-builder snapshots;
- produce exactly 36 unique months from `2006-01` through `2008-12`;
- preserve the first 30 snapshots exactly and the six suffix snapshots exactly;
- perform no historical recomputation.

## Prohibited

Do not use Stage21 returns, ranks, CAGR, MaxDD, Calmar, trades, portfolio outcomes, or other strategy performance to choose or revise any reconstruction rule.

Do not run broad 2006-2018 Stage21 performance.

Do not modify `main` or Production.

## Failure handling

Any replay, PIT, identity, parser, mapping, country, builder-parity, lineage, or closed-prefix failure is a stop condition. Audit implementation or evidence lineage only; do not relax or tune the frozen methodology after seeing results.
