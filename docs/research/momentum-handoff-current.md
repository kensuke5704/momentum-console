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

This deterministic structural mapping rule is the active research rule. Do not broaden it with fuzzy/edit-distance auto-matching merely to improve coverage.

## 9. 2006 PIT issuer-country bridge — materially resolved within mapped population

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

### Superseded pre-correction state

Before the corrected submission-header route:
- baseline mapped holdings resolved: **59.17% count / 62.68% weight**
- all 936 EC holdings resolved: **42.95% count / 50.97% weight**
- structural-new identities: US 7 / NON_US 2 / UNKNOWN 18
- approximate combined all-EC resolved-weight coverage: **52.35%**

The old generic complete-submission `.txt` pilot resolved 0/30 because it did not first establish the correct historical issuer identity and filing path. Do not interpret that pilot as evidence that complete-submission headers are unusable.

### Corrected deterministic flat-header route

The accepted country evidence route now is:
1. official historical SEC master index, issuer-bearing forms only, filing date `<=` legacy report date;
2. exact normalized historical issuer name must resolve to one CIK; current ticker metadata is exact-name CIK fallback only;
3. fetch the correct complete-submission filing;
4. parse the 2005/2006 flat `COMPANY DATA:` SEC header;
5. require matching historical company name, the same CIK, and `STATE OF INCORPORATION` in the same block;
6. classify only from that filing-time code.

Top-10 high-weight UNKNOWN pilot resolved **9/10 identities**, representing **93.67%** of sample weight.

Full baseline-mapped UNKNOWN expansion:
- commit `03dd6dfe7c26b37b1639b9fe28fdd93bf0097132`
- run `33892546597`
- artifact `9944538015`
- prior mapped UNKNOWN identities: 180
- newly resolved: **160**
- newly resolved US 159 / NON_US 1
- remaining mapped UNKNOWN identities: 20
- baseline mapped holdings country resolved: **95.41% count / 96.23% weight**
- all 936 EC before structural +37 integration: **68.27% count / 77.43% weight**

The one newly resolved NON_US identity was Tyco International Ltd., supported by the same historical CIK/name block and filing-time state code `D0` in its 2005 10-K.

### Structural-new identity refresh

The 27 unique identities introduced by the accepted structural mapping were then re-audited. Existing US/NON_US classifications were frozen; only the 18 old UNKNOWN identities could be promoted.

Issuer-name reconciliation reused only the already accepted trailing N-Q footnote/share-class/jurisdiction cleanup. It did **not** add fuzzy/edit-distance matching. Every promotion still required exact historical issuer-form name -> unique CIK and same-name/same-CIK filing-time state evidence.

Result:
- commit `a50e89046f01f20173659d6e9b0d47ee2fb50b96`
- run `33893452312`
- artifact `9944797581`
- 18 prior structural UNKNOWN -> **16 promoted**
- promoted holding occurrences: 21
- promoted aggregate weight: **38.22**
- structural identity total: **US 23 / NON_US 2 / UNKNOWN 2**
- structural resolved aggregate weight: **65.75**
- remaining structural-new UNKNOWN identities: News Corp. and E.W. Scripps

### Final 936-holding merge

Final conservative holding-level merge:
- commit `99ffda186350b3d07f8f04ae986dbede9a1872d4`
- run `33893804443`
- artifact `9944902929`
- denominator: **936 EC holdings**, unchanged
- total weight: **1992.55834288257**, unchanged
- classification conflicts: **0**
- US 641 / NON_US 33 / UNKNOWN 262
- all-EC resolved: **674/936 = 72.01% count**
- all-EC resolved weight: **80.85%**
- deterministic unique mapped holdings: 691
- mapped holdings with resolved country: **658/691 = 95.22% count**
- mapped-holding resolved weight: **96.14%**

Interpretation:
- country evidence is no longer the principal blocker **inside the deterministic mapped population**;
- residual full-EC unresolved weight is now dominated by unmapped/ambiguous identity rows rather than lack of country evidence on mapped identities;
- keep residual UNKNOWN conservative; do not revive a default-US rule.

## 10. 2006 source-series discovery — corrected and materially improved

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

SEC daily form indexes can be acquired with bounded HTTP Range reads instead of blocked full quarterly downloads. Source-discovery transport pilot:
- commit `2be4218a5753b5ca5e5eae682e7aa31dd8272c43`
- run `33878671009`
- workflow `Research SEC Daily Index N-Q Pilot 2006`
- conclusion: success

Interpretation:
- series identity within a known historical filing is reproducibly discoverable without holdings content or Production ranks;
- market-wide historical N-Q filing inventory has a viable SEC daily-index transport path;
- the remaining major source blocker is combining those pieces into a **market-wide, Production-independent registrant/filing discovery process**. The fixed three source submissions were inherited from the original pilot and are not sufficient.

## 11. Reproduction gate status

### Passed / strong
- Gate A mechanics: PASS
- corrected 2006 schedule→series segmentation: strong
- legacy EC bridge: accepted
- transition source parser retention: strong
- 2020-01 direct aggregate shadow: exceeds practical overlap/rank/Top2 thresholds
- transition CORP redundancy after EC+US: 226/226
- filing-index series extraction within fixed 2006 source submissions: 20/20 corrected PIT series covered
- PIT country attribution within deterministic mapped 2006 holdings: **95.22% count / 96.14% weight**

### Not yet passed
- deterministic security mapping itself covers only **73.90% count / 82.49% weight** of all EC holdings; do not fill the remainder with fuzzy matching
- market-wide Production-independent historical source-filing/registrant discovery
- full historical aggregate Universe reconstruction from independently discovered sources

Therefore **Universe reconstruction is not yet confirmed**.

## 12. Current active gate and next actions

The active gate has shifted away from country resolution. Proceed in this order:
1. freeze the corrected PIT submission-header country rule and keep residual mapped UNKNOWN conservative;
2. preserve the current deterministic structural identity rules; do not tune identity coverage from strategy outcomes;
3. build a scalable market-wide historical fund-filing discovery route using SEC daily form indexes plus filing-index Series/Class metadata;
4. identify active historical series/tickers from independently discovered filings without holdings-content or Production-rank seeding;
5. construct a full legacy aggregate Universe from those independently discovered sources;
6. explicitly quantify sensitivity to residual unmapped/UNKNOWN holdings without changing reconstruction rules from return outcomes;
7. rerun Gate B Top-K/Top80 overlap, common-name rank correlation and Production Top2 retention;
8. only after Gate B passes explicitly state `Universe reconstruction is confirmed` and implement the historical builder;
9. still do not immediately run broad 2006–2018 Stage21 performance; first freeze the bridge and expose older history in staged windows.

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
- current-ticker + historical-name validation route after 0/50 pilot, when used without the corrected historical-master identity route
- old generic complete-submission `.txt` probe after 0/30, when used without first fixing the historical issuer CIK and filing path

## 14. Key artifacts / runs

- corrected 2006 PIT: run `33714482859`
- EC per-holding: run `33714785802`, artifact `9878123068`
- EC-filtered PIT: run `33715016882`, artifact `9878189715`
- EC-filtered baseline mapping: run `33715050446`, artifact `9878201336`
- frozen N-PX master: artifact `9876020712`
- current-ticker PIT country sample: run `33731427179`, artifact `9884212384`
- unresolved country audit: run `33733665015`
- corrected filing-index series parser: run `33842315528`, artifact `9925317298`
- SEC daily N-Q index Range transport: run `33878671009`, commit `2be4218a5753b5ca5e5eae682e7aa31dd8272c43`
- full submission-header mapped-UNKNOWN country run: run `33892546597`, artifact `9944538015`, commit `03dd6dfe7c26b37b1639b9fe28fdd93bf0097132`
- structural-new submission-header country refresh: run `33893452312`, artifact `9944797581`, commit `a50e89046f01f20173659d6e9b0d47ee2fb50b96`
- final 936-holding country merge: run `33893804443`, artifact `9944902929`, commit `99ffda186350b3d07f8f04ae986dbede9a1872d4`

When resuming, update this file after any material gate change.
