# Frozen 2006 Structural Inputs

These inputs are frozen for apples-to-apples N-Q ↔ N-PX mapping-rule evaluation. They contain structural holdings/security-mapping data only; no strategy-return data is used.

## Frozen merged N-PX master

- source workflow run: `33708273986`
- source artifact: `9876020712`
- file: `npx-security-master-2006.json`
- raw bytes: `1,357,515`
- SHA-256: `279364138ff0476e3b91411de1de63e64fcacf5077cbc605fc6205fe7961cacd`
- paired records: `2,925`
- unique normalized issuers: `2,687`
- composition: deterministic 24-filing baseline + independently pre-fixed broad-fund-family supplement

## Frozen N-Q PIT holdings

- source workflow run: `33650184550`
- source artifact: `9854510485`
- file: `nq-pit-holdings-2006.json`
- raw bytes: `101,536`
- SHA-256: `24381f6bc2422fd71fa26272657bcc66ad9af534175cb5ad15d7b28428fa51bb`
- retained PIT series records: `9`
- eligible holdings used by mapping: `487`

## Current stable mapping result

- frozen-master workflow run: `33708713690`
- result artifact: `9876161889`
- count coverage: `43.53%`
- eligible-weight coverage: `60.67%`
- ambiguous holdings: `3`
- unmapped holdings: `272`

## Reproducibility rule

Mapping-rule changes must be evaluated against these exact frozen inputs, verified by SHA-256, unless a new master version is explicitly frozen and documented. Live filing-fetch runs are source-acquisition experiments and are not valid apples-to-apples mapping-rule comparisons when the fetched source set differs.
