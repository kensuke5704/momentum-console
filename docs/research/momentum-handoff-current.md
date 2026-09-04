# Momentum Research Handoff — Current

Last updated: 2026-09-04 JST  
Branch: `research/nq-npx-mapping-2006-20260903`  
Repository: `kensuke5704/momentum-console`

This is the canonical handoff for ongoing Momentum historical-Universe research.

## 1. Hard constraint

Do **not** implement the historical/legacy Universe builder yet. First confirm that the historical Universe can be reproduced with sufficient structural fidelity.

Do **not** run broad 2006–2018 Stage21 performance yet. Historical reconstruction rules must be frozen using source/data-quality evidence before older returns are opened.

Do not tune any parser, identity, country, eligibility, ranking, or threshold rule from Stage21 returns, CAGR, MaxDD, Calmar, trades, or 2006–2018 strategy outcomes.

## 2. Frozen Production strategy — do not modify

Frozen identifier: `momentum-stage21-sbi-2026-09-v1`  
True Forward start: 2026-09-02

- NORMAL: Fixed60 85%, GLDM 15%
- YELLOW: Fixed60 55.5%, GLDM 22.5%, Cash 22%
- DEEP: Fixed60 25.5%, GLDM 30%, Cash 44.5%
- state priority: M3 > CFTC > NORMAL
- monthly rebalance + immediate state-change rebalance
- transaction cost: 10 bps one-way

Frozen 2020-01-01 through 2026-08-25 reference:
- CAGR 48.61%
- MaxDD -16.89%
- Calmar 2.879
- final equity 13.905x

Architecture-selection bias remains material. Longer history is for validation, not refitting.

## 3. Production Universe target

Relevant code:
- `src/lib/universe/universe.ts`
- `src/lib/universe/sec-nport.ts`
- `src/lib/universe/nport-quarterly.ts`

Breadth score:
`3*log1p(etfCount) + 0.5*log1p(aggregateWeight) + 0.5*log1p(recencyWeight)`

Production raw N-PORT filters:
- `ASSET_CAT=EC`
- `INVESTMENT_COUNTRY=US`
- `ISSUER_TYPE=CORP`

Aggregate/filter semantics:
- `etfCount >= 2 || maxWeight >= 4`
- sort by Production breadth score
- Top80 before downstream eligibility/ranking use

SEC N-PORT C.5 primary country means issuer organization country. Legacy `US` must not be replaced by listing venue.

## 4. Gate A — PASS

Production adapter / PIT identity / canonical scoring mechanics reproduce the first 12 Production Universe months strongly:
- median Top-K overlap: **93.75%**
- minimum overlap: **92.5%**
- median Spearman: **0.9996**
- Production Top2 individual retention: **100%**
- both Top2 retained: **100%**

Gate A validates mechanics, not legacy source fidelity.

## 5. Gate B transition evidence — strong

The actual three series behind the 2020-01 Production Universe were traced to their nearest complete pre-Production holdings reports without using returns:
- ClearBridge / LRGE: 182-day gap, legacy→N-PORT retention **92.9% count / 95.9% weight**
- Goldman GFIN: 90-day gap, **94.2% / 97.4%**
- PPTY: 183-day gap, **93.9% / 98.0%**

All satisfy the preregistered primary adjacency rule `report gap <= 184 days`.

Three-series 2020-01 aggregate legacy shadow using Production scoring semantics:
- Production Universe size: 9
- common names: **8/9 = 88.9%**
- Spearman: **0.842**
- Production Top2 retained: **2/2**

This is strong direct transition evidence, but it does **not** by itself authorize implementation because the three source series were known from Production when that aggregate shadow was built.

## 6. CORP bridge — transition evidence resolved

The first Production raw N-PORT filings for LRGE, GFIN and PPTY were individually parsed. Among holdings satisfying `EC+US`:
- LRGE: 42/42 `issuerCat=CORP`
- GFIN: 69/69 CORP
- PPTY: 115/115 CORP

Combined: **226/226 = 100% CORP**.

For this transition cohort, CORP is empirically redundant after EC+US. Do not generalize this as a universal historical fact, but CORP is no longer the principal implementation blocker.

## 7. Corrected 2006 PIT and EC bridge

Old nine-series PIT artifact `9854510485` is invalid and superseded. The old continuation-page segmentation used holdings-word overlap and could assign continuation pages to unrelated series.

Corrected segmentation rule:
1. assign schedule pages from exact filing-time registered series title;
2. never use holdings/industry words for series identity;
3. continuation pages inherit the explicit series;
4. concatenate pages per series before parsing;
5. trim final schedule at first explicit `NET ASSETS ... 100%` boundary;
6. apply eligibility after grouped parse.

Corrected PIT:
- run `33714482859`
- retained PIT series: **20**
- median holdings: **41**

Accepted legacy EC rule is explicit `COMMON_EQUITY` section attribution only.

Per-holding EC diagnostic:
- 964 parsed holdings
- known section 962/964 = 99.79%
- known-section weight 99.97%
- `COMMON_EQUITY`: **936 holdings = 97.10% count**
- `COMMON_EQUITY`: **99.63% portfolio weight**

Active EC-filtered PIT artifact: `9878189715`.

## 8. N-PX security mapping

Frozen N-PX master artifact: `9876020712`.

Baseline EC-filtered mapping:
- EC holdings: 936
- mapped: 654
- count coverage: **69.95%**
- weight coverage: **78.98%**

Return-independent structural mapping sensitivity adds only:
- trailing share-class / jurisdiction cleanup
- long issuer-name prefix match only when the candidate identity set is exactly one
- no edit-distance/fuzzy auto-match

Structural result:
- mapped holdings: **691**
- count coverage: **73.90%**
- weight coverage: **82.49%**
- new structural matches: 37
- added mapped weight: 70.36

Examples include Comcast Class A, UPS Class B, Broadcom Class A, Viacom Class B and Lennar Class A.

This structural mapping rule is promising but should remain a research rule until the historical bridge is frozen.

## 9. 2006 PIT issuer-country bridge — main blocker

Conservative hierarchy remains:
- alphabetic CINS prefix => NON_US
- explicit ADR/GDR => NON_US
- historical SEC filing-time state/country from deterministically resolved CIK => US/NON_US
- current SEC ticker metadata may seed a CIK only; current state is never country evidence
- UNKNOWN remains UNKNOWN

Never infer US from:
- US listing venue
- numeric CUSIP
- absence of ADR/GDR
- legacy country headings unless source semantics explicitly define issuer domicile/organization

Full 12-shard deterministic country run over the 439 baseline mapped identities completed successfully. UNKNOWN-only historical 10-K retry resolved **53 additional identities**.

After retry, baseline-mapping country coverage:
- mapped holdings resolved: **59.17% count / 62.68% weight**
- all 936 EC holdings, including conservative explicit ADR/GDR on unmapped rows: **42.95% count / 50.97% weight**

Country attribution on newly recovered structural mapping identities:
- 27 unique new identities
- US 7 / NON_US 2 / UNKNOWN 18
- resolved added weight: **27.53**

Combined all-EC resolved-weight coverage is approximately **52.35%**. This remains insufficient for implementation.

Rejected/low-value country routes:
- current-ticker CIK seed + historical `COMPANY CONFORMED NAME` validation on top 50 UNKNOWN: **0/50 resolved**
- deterministic complete-submission `.txt` pilot on top 30 UNKNOWN: **0/30 resolved**, sample weight 288.74

Important new lead: historical SEC **filing index pages** can expose `State of Incorp.` directly (e.g. Intel 2005 10-K). A filing-index-based PIT country resolver is the next route to validate. It must still use historical filing-time metadata and keep current ticker data seed-only.

## 10. 2006 source-series discovery — major correction and progress

Earlier wording that r.jina omitted historical Series/Class metadata was incorrect.

Actual SEC/r.jina filing-index grammar was diagnosed and parser-fixed. Historical N-Q filing index pages expose:
- Series ID
- Class/Contract ID
- class/fund title
- ticker when assigned

Fixed three 2006 N-Q source submissions:
- Select Sector SPDR accession `0000950135-06-001225`
- Rydex ETF Trust accession `0000950135-06-001815`
- streetTRACKS accession `0000950135-06-003650`

Corrected filing-index parser run `33842315528`, artifact `9925317298` extracted:
- **49 unique historical Series IDs**
- 33 distinct parsed ticker tokens before treating placeholder `ETF` as missing

Examples recovered directly from filing-index metadata:
- Select Sector: XLY, XLP, XLE, XLF, XLV, XLI, XLB, XLK, XLU
- Rydex: XLG, RSP
- streetTRACKS/SPDR: TMW, DGT, RWR, MTK, XBI, XHB, XSD and additional registered series

Direct comparison against the corrected 20-series PIT set confirms **20/20 = 100% source-series coverage** within these fixed source submissions.

Interpretation:
- series identity within a known historical filing is now reproducibly discoverable without holdings content or Production ranks;
- prior zero-series runs were parser defects, not data absence or transport absence;
- this materially strengthens the historical source-discovery bridge.

Remaining source-discovery caveat: the three source submissions/registrants were themselves fixed from the existing 2006 pilot. A scalable market-wide process still needs to discover the relevant historical fund filings/registrants without starting from a Production-known list.

## 11. Reproduction gate status

### Passed / strong
- Gate A mechanics: PASS
- corrected 2006 schedule→series segmentation: strong
- legacy EC bridge: accepted
- transition source parser retention: strong
- 2020-01 direct aggregate shadow: exceeds practical overlap/rank/Top2 thresholds
- transition CORP redundancy after EC+US: 226/226
- filing-index series extraction within fixed 2006 source submissions: 20/20 corrected PIT series covered

### Not yet passed
- conservative 2006 issuer-country resolved-weight coverage: only ~52.35%
- market-wide Production-independent historical source-filing discovery
- full historical aggregate Universe reconstruction from independently discovered sources

Therefore **Universe reconstruction is not yet confirmed**.

## 12. Current next actions

Proceed in this order:
1. validate a filing-index-based historical `State of Incorp.` resolver on remaining high-weight UNKNOWN issuers;
2. if effective, shard it across the remaining mapped UNKNOWN population and recompute count/weight coverage;
3. incorporate structural mapping additions only under deterministic unique-identity rules;
4. design a scalable historical fund-filing discovery route using SEC filing-index Series/Class metadata rather than holdings-content matching;
5. construct a full legacy aggregate Universe from independently discovered historical sources;
6. rerun Gate B Top-K/Top80 overlap, common-name rank correlation and Production Top2 retention;
7. only after Gate B passes explicitly state `Universe reconstruction is confirmed` and implement the historical builder;
8. still do not immediately run broad 2006–2018 Stage21 performance; first freeze the bridge and expose older history in staged windows.

## 13. Rejected paths — do not revive without new evidence

- old nine-series PIT sample / continuation-page token assignment
- 13F as direct Production Universe substitute
- BeanCounter generic CUSIP frequency
- fuzzy issuer auto-matching
- automatic country missing => US
- numeric CUSIP => US
- absence of ADR/GDR => US
- country heading => N-PORT C.5 US without explicit domicile semantics
- current SEC state as PIT country evidence
- accession first ten digits as issuer CIK
- raw quarterly N-PORT ZIP transport failure as semantic evidence
- current-ticker + historical-name validation route after 0/50 pilot
- complete-submission `.txt` country route after 0/30 pilot

## 14. Key artifacts / runs

- corrected 2006 PIT: run `33714482859`
- EC per-holding: run `33714785802`, artifact `9878123068`
- EC-filtered PIT: run `33715016882`, artifact `9878189715`
- EC-filtered baseline mapping: run `33715050446`, artifact `9878201336`
- frozen N-PX master: artifact `9876020712`
- current-ticker PIT country sample: run `33731427179`, artifact `9884212384`
- unresolved country audit: run `33733665015`
- corrected filing-index series parser: run `33842315528`, artifact `9925317298`

When resuming, update this file after any material gate change.