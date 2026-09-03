# Gate B progress — 2026-09-04 JST

Structural/data-quality validation only. No Stage21 returns, CAGR, MaxDD, Calmar, trades, or 2006–2018 strategy outcomes were used to select any rule below.

## Transition aggregate evidence

2020-01 Production Universe source series were identified as LRGE, GFIN, and PPTY. Their latest complete pre-Production holdings sources are all within the preregistered <=184-day primary adjacency window.

Verified source-fidelity results:
- ClearBridge LRGE: 92.9% constituent retention / 95.9% retained weight
- Goldman GFIN: 94.2% / 97.4%
- PPTY: 93.9% / 98.0%

Using the same Production breadth-score mechanics and fixed identity semantics, the three-source legacy aggregate shadow reproduced 2020-01 Production with:
- 8 / 9 symbols common = 88.9%
- common-name Spearman = 0.842
- Production Top2 retained = 2 / 2

This clears the practical Gate A thresholds for this direct transition month, but is not by itself permission to implement the historical builder because legacy source discovery and 2006 US/CORP semantics must also be defensible.

## CORP transition evidence

Raw first-Production N-PORT filings for LRGE, GFIN, and PPTY were inspected individually. Among holdings satisfying EC+US:
- LRGE: 42 / 42 issuerCat=CORP
- GFIN: 69 / 69 CORP
- PPTY: 115 / 115 CORP
- total: 226 / 226 = 100%

Thus CORP was redundant conditional on EC+US in this direct transition cohort. This is transition evidence, not a universal historical identity claim.

## 2006 EC and mapping

Accepted EC bridge remains explicit COMMON_EQUITY only.

Frozen baseline mapping artifact `9878201336`:
- 935 eligible EC holdings
- 654 unique mapped
- 69.95% count coverage
- 78.98% weight coverage

Return-independent structural mapping sensitivity added only:
1. trailing share-class / jurisdiction presentation suffix cleanup followed by exact issuer match;
2. unique long-prefix reconciliation when the common prefix is at least 20 characters and the candidate identity union is exactly one.

No edit-distance or fuzzy match is auto-accepted.

Run `33773774767`, artifact `9900708609`:
- unique mapped holdings: 691
- count coverage: 73.90%
- weight coverage: 82.49%
- new structural matches: 37
- new structural weight: 70.36

Examples recovered structurally include UPS Class B, Comcast Class A, Broadcom Class A, Viacom Class B, Lennar Class A, Nike Class B, and Genworth Class A.

## 2006 country attribution

Country hierarchy remains conservative:
- alphabetic CINS prefix => NON_US
- explicit ADR/GDR => NON_US
- otherwise filing-time historical SEC state/country after deterministic CIK resolution
- current SEC ticker metadata may only seed a CIK; current state is never country evidence
- unresolved => UNKNOWN

Initial 12-shard full mapped-identity pass, run `33769611572`:
- identity population: 439
- US 195 / NON_US 11 / UNKNOWN 233
- mapped holding resolved rate: 48.6% count / 55.2% weight
- all 936 EC resolved rate after explicit unmapped ADR/GDR: 35.7% count / 45.2% weight

UNKNOWN-only retry using 10-K-scoped historical searches and broader historical incorporation-header patterns resolved 53 additional identities. Merge run `33778934003`, artifact `9902743513`:
- identity population: US 248 / NON_US 11 / UNKNOWN 180
- mapped holdings: US 374 / NON_US 13 / UNKNOWN 267
- mapped resolved rate: 59.17% count / 62.68% weight
- all 936 EC: US 374 / NON_US 28 / UNKNOWN 534
- all-EC resolved rate: 42.95% count / 50.97% weight

This is materially improved but still insufficient to freeze the historical US bridge.

## Rejected / failed discovery route

A Production-independent 2006 source-discovery pilot successfully enumerated 13,224 N-Q/N-CSR/N-CSRS filings from official SEC quarterly master indexes, but 16 deterministic sample filings exposed zero registered-series/ticker metadata in their legacy SGML headers. Do not rely on N-Q/N-CSR SGML registered-series headers for legacy ETF-series discovery.

The quarterly SEC master indexes themselves are valid but transport from GitHub runners is intermittent. Treat 403/fetch failure as transport only, not data evidence.

## Active work at this snapshot

Two country-coverage tests are running:
1. residual UNKNOWN top-weight identities: current ticker -> candidate CIK only, accepted only when a historical filing available by the legacy report date contains a matching historical COMPANY CONFORMED NAME and filing-time state/country;
2. country attribution for the 37 newly recovered structural mapping holdings.

Do not implement the historical Universe builder until these results are merged and the remaining 2006 country uncertainty is judged sufficiently small for aggregate ranking parity. Do not run broad 2006–2018 Stage21 performance.
