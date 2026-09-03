# Momentum Research Handoff — Current

Last updated: 2026-09-04 JST
Branch: `research/nq-npx-mapping-2006-20260903`
Repository: `kensuke5704/momentum-console`

> Canonical handoff for ongoing Momentum research. Update this file whenever the active baseline, validation result, rejected path, or next gate changes.

## 0. Superseding update — 2026-09-04

This section supersedes older status wording later in this document where the research has advanced. Historical notes remain below for traceability.

### Hard constraint remains unchanged

Do **not** implement the historical/legacy Universe builder yet. First confirm that the historical Universe can be reproduced with sufficient structural fidelity. Do **not** run broad 2006–2018 Stage21 performance. Older return history is still unopened for broad strategy evaluation.

### Gate A — PASS

Production adapter / PIT identity / canonical scoring mechanics reproduce the first 12 Production Universe months strongly:
- median Top-K overlap: **93.75%**
- minimum overlap: **92.5%**
- median Spearman: **0.9996**
- Production Top2 individual retention: **100%**
- both Top2 retained: **100%**

Gate A establishes mechanics, not legacy source fidelity.

### Gate B transition source fidelity — strong

The actual three source series behind the 2020-01 Production Universe were identified and their nearest pre-Production complete holdings reports fixed without using returns:
- ClearBridge / LRGE: 182-day gap, legacy→N-PORT retention **92.9% count / 95.9% weight**
- Goldman GFIN: 90-day gap, **94.2% / 97.4%**
- PPTY: 183-day gap, **93.9% / 98.0%**

All three satisfy the preregistered primary adjacency rule of report gap <=184 days.

A three-series 2020-01 aggregate shadow, using legacy source holdings with Production scoring semantics, reproduced:
- Production Universe size: 9
- common names: **8/9 = 88.9%**
- Spearman: **0.842**
- Production Top2 retained: **2/2**

This exceeds the practical transition thresholds for this direct month, but is **not sufficient by itself for historical-builder implementation**, because the aggregate run starts from the known three Production source series rather than independently discovering the full historical ETF source population.

### CORP bridge — transition evidence now resolved

The first Production raw N-PORT filings for LRGE, GFIN and PPTY were individually parsed. Among holdings already satisfying `ASSET_CAT=EC` and `INVESTMENT_COUNTRY=US`:
- LRGE: 42/42 had `issuerCat=CORP`
- GFIN: 69/69 had `issuerCat=CORP`
- PPTY: 115/115 had `issuerCat=CORP`

Combined: **226/226 = 100% CORP**. For this transition cohort, `CORP` is empirically redundant after `EC+US`. This replaces the older invalid bootstrap-based CORP diagnostic below. Do not generalize beyond the evidence without further checks, but CORP is no longer the principal blocker.

### 2006 EC and mapping state

Accepted EC bridge remains explicit `COMMON_EQUITY` only:
- 936 EC holdings across 20 corrected PIT series
- EC is 99.63% of parsed portfolio weight

Baseline EC-filtered N-PX mapping:
- 654 unique mapped holdings
- **69.95% count / 78.98% weight**

Return-independent structural identity sensitivity added only:
- trailing share-class/jurisdiction cleanup
- unique long-prefix identity when candidate set is exactly one
- no edit-distance/fuzzy auto-match

Structural mapping result:
- 691 unique mapped holdings
- **73.90% count / 82.49% weight**
- 37 new structural matches
- added mapped weight: 70.36

Examples include Comcast Class A, UPS Class B, Broadcom Class A, Viacom Class B, Lennar Class A and similar source-format differences.

### 2006 PIT issuer-country bridge — improved but still insufficient

Country hierarchy remains conservative:
- alphabetic CINS prefix => NON_US
- explicit ADR/GDR => NON_US
- historical SEC filing-time state/country from a deterministically resolved CIK => US/NON_US
- current SEC ticker metadata may seed a CIK only; current state is never country evidence
- UNKNOWN stays UNKNOWN
- numeric CUSIP, US listing, absence of ADR/GDR, or country-heading convention are not positive US proof

Full 12-shard deterministic run over the 439 baseline mapped identities completed successfully. UNKNOWN-only 10-K historical-header retry then resolved **53 additional identities**.

After UNKNOWN retry, baseline-mapping country coverage was:
- mapped holdings resolved: **59.17% count / 62.68% weight**
- all 936 EC holdings including conservative explicit ADR/GDR treatment on unmapped rows: **42.95% count / 50.97% weight**

Structural mapping additions were then country-attributed separately:
- 27 unique new structural identities
- US 7 / NON_US 2 / UNKNOWN 18
- resolved added weight: **27.53**

Adding those structurally recovered and country-resolved weights raises the all-EC resolved-weight coverage only to approximately **52.35%**. This remains **insufficient for implementation**.

A further `current ticker CIK seed + historical filing COMPANY CONFORMED NAME validation` pilot on the 50 highest-weight remaining UNKNOWN identities resolved **0/50** and is rejected as an effective next coverage route.

### 2006 source-series discovery — current transport finding

Important correction: SEC native filing index pages do expose `Series and Classes/Contracts Information` for historical N-Q filings. For example, accession `0000950135-06-001225` visibly lists historical Series IDs, Class IDs and tickers such as `S000006408 / C000017594 / XLY` through the Select Sector series.

However:
- GitHub-hosted runners receive a block/failure on the native SEC filing-index request;
- `r.jina` fallback retrieves the filing page but drops the Series/Class table;
- therefore the GitHub workflow reports zero series despite the native SEC page containing the metadata.

This is a **transport mismatch, not data absence**. Complete-submission SGML is still not a valid substitute because it does not expose the same series table in these filings.

The source-discovery blocker is now to create a reproducible acquisition path for SEC filing-index Series/Class/Ticker metadata (or an equivalent official registry) that does not depend on the blocked GitHub-runner transport.

### Current implementation gate

Universe reconstruction is **not yet confirmed**. The remaining principal blockers are:
1. raise conservative 2006 issuer-country resolved-weight coverage materially above the current ~52.35%, without coercing UNKNOWN to US;
2. establish a scalable, Production-independent historical ETF-series discovery/acquisition route for 2006-era SEC Series/Class/Ticker metadata;
3. then construct a full legacy aggregate Universe shadow from independently discovered sources and re-run Gate B metrics;
4. only after that explicitly declare `Universe reconstruction is confirmed` and implement the historical builder;
5. still keep broad 2006–2018 Stage21 performance unopened until bridge rules are frozen.

## 1. Objective and hard constraints

Reconstruct a point-in-time historical ETF-holdings universe for 2006 onward that is economically as close as possible to the frozen Production N-PORT universe. This work is **data reconstruction and structural parity**, not strategy optimization.

Do **not** run a broad 2006–2018 Stage21 performance backtest yet. The user explicitly wants the older history preserved from repeated exploratory use. Reconstruction rules must be frozen using structural/data-quality evidence before older returns are opened.

## 2. Frozen Production strategy — do not modify

Frozen identifier: `momentum-stage21-sbi-2026-09-v1`
Frozen / True Forward start: 2026-09-02

Stage21 allocations:
- NORMAL: Fixed60 85%, GLDM 15%
- YELLOW: Fixed60 55.5%, GLDM 22.5%, Cash 22%
- DEEP: Fixed60 25.5%, GLDM 30%, Cash 44.5%
- state priority: M3 > CFTC > NORMAL
- monthly rebalance plus immediate state-change rebalance
- transaction cost assumption: 10 bps one-way

Frozen 2020-01-01 through 2026-08-25 reference:
- CAGR 48.61%
- MaxDD -16.89%
- Calmar 2.879
- final equity 13.905x

Architecture-selection bias remains material. Architecture-wide SPA over 333 curves did not eliminate it; the longer history is for validation, not refitting.

## 3. Production universe target

Relevant implementation:
- `src/lib/universe/universe.ts`
- `src/lib/universe/sec-nport.ts`
- `src/lib/universe/nport-quarterly.ts`

Production breadth score uses:
- ETF count
- aggregate weight
- max weight
- recency-weighted weight

Production N-PORT holdings are restricted using:
- `ASSET_CAT=EC`
- `INVESTMENT_COUNTRY=US`
- `ISSUER_TYPE=CORP`

SEC Form N-PORT Item C.5 defines the primary country field as the country where the issuer is organized; a second country may be reported when risk/economic exposure points elsewhere. Therefore a legacy `US` bridge must not substitute listing venue for issuer country.

## 4. Historical source decisions already made

### Rejected

- **13F as direct Production-universe substitute:** weak direct overlap and poor Production Top2 retention.
- **BeanCounter generic CUSIP-frequency extraction:** false CUSIP-like tokens and fund/share-class contamination.
- **Holdings-content token overlap for N-Q schedule→series assignment:** structurally invalid; superseded below.
- **Automatic fuzzy issuer mapping:** prohibited.
- **Country missing ⇒ US:** prohibited.

### Active

- **Legacy N-Q / N-CSR:** primary historical fund-holdings route.
- **N-PX:** support source for historical issuer ↔ ticker ↔ security-ID mapping, including delisted securities.

## 5. Critical correction: old nine-series PIT sample is invalid

The prior segmentation treated each `SCHEDULE OF INVESTMENTS (CONTINUED)` marker as a separate portfolio candidate and used holdings-token similarity to assign that page to an ETF series. Continuation-page industry words could therefore map to an unrelated ETF and displace the actual portfolio page.

Confirmed examples included a software continuation page being assigned to SPDR Biotech ETF. The old XBI holdings were consequently economically impossible.

Therefore:
- old PIT artifact `9854510485` is superseded;
- the old nine-series sample is invalid as universe-quality evidence;
- the former 43.53% count / 60.67% weight mapping result is mapping-engine history only, not an active baseline.

No strategy returns were inspected in discovering or correcting this issue.

## 6. Corrected schedule-to-series rule

Implemented in `scripts/research-nq-series-segmentation-2006.py`.

Active rule:
1. assign each schedule page using the nearest exact filing-time registered ETF series title around the schedule marker;
2. never use holdings or industry words to determine series identity;
3. continuation pages remain assigned to the same explicit series;
4. concatenate pages belonging to one series before holdings parsing;
5. stop the final schedule after the first explicit `NET ASSETS ... 100%` boundary so later filing tables cannot bleed into holdings;
6. apply structural eligibility after grouped parsing.

Supporting audits:
- schedule-assignment audit run `33714110948`, artifact `9877891675`
- explicit-series-boundary audit run `33714195904`, artifact `9877920529`

The old token-overlap helper is retained only for diagnostics/compatibility and must not construct PIT holdings.

## 7. Corrected 2006 PIT holdings

Workflow: `Research NQ PIT Holdings 2006 Corrected`
Run: `33714482859`
Artifact: `9878011119`

Source submissions are frozen to the same three N-Q filings as the old pilot; only the objective segmentation defect changed.

Result:
- retained PIT series: **20**
- median holdings per retained series: **41**

Selected corrected portfolios are economically coherent:
- XLE: Exxon Mobil, Chevron, ConocoPhillips, Burlington Resources, Halliburton...
- MTK: NVIDIA, Broadcom, Cisco, Jabil, Network Appliance, SAP ADR, HP, Qualcomm...
- XBI: Nektar, Amylin, Celgene, Affymetrix, Serologicals, United Therapeutics, PDL BioPharma, Techne...
- XHB: Sherwin-Williams, Lennar, Brookfield Homes, Toll Brothers, M/I Homes, Home Depot...
- XSD: NVIDIA, Rambus, Intersil, Texas Instruments, International Rectifier, Agere, Microchip, Altera...

## 8. Frozen N-PX master

Frozen best merged N-PX master artifact: `9876020712`.

Construction:
- deterministic 24-filing equal-quantile baseline;
- independently pre-fixed broad/large fund-family supplement;
- 2,925 paired records;
- 2,687 unique normalized issuers;
- no N-Q target-name selection and no return/performance selection.

Accepted conservative identity rules:
- reject placeholder/invalid ticker identities;
- require structurally valid security IDs;
- legal-suffix normalization;
- trailing N-Q footnote-marker removal;
- leading/trailing `THE` normalization;
- collision-tested `HLDGS` ↔ `HOLDINGS` and `PHARMACEUTICALS` ↔ `PHARMACEUTICAL`;
- ADR suffix removal only when the base issuer resolves to exactly one valid identity;
- ambiguous ADR bases remain unresolved;
- fuzzy candidates are diagnostic only.

## 9. Security mapping — corrected and EC-filtered baseline

Corrected mapping before explicit EC filtering:
- run `33714515426`
- artifact `9878021112`
- 20 PIT series
- 944 eligible holdings
- 654 unique matches
- count coverage **69.28%**
- weight coverage **78.92%**

### Per-holding legacy EC bridge — accepted structural rule

Workflow: `Research NQ Per-Holding EC 2006`
Run: `33714785802`
Artifact: `9878123068`

Rule:
- locate each already-parsed holding back in its corrected explicit-series schedule;
- inherit only the nearest preceding explicit `COMMON`, `PREFERRED`, `SHORT_TERM`, or `DEBT` section heading;
- if a source location or preceding heading is not explicit, retain `UNKNOWN`;
- no issuer-name inference and no returns.

Result on corrected 20-series PIT sample:
- holdings: 964
- known section: **962 / 964 = 99.79%**
- known-section weight: **99.97%**
- `COMMON_EQUITY`: **936 holdings = 97.10% of count**
- `COMMON_EQUITY`: **99.63% of portfolio weight**
- only two UNKNOWN rows, both tiny parser-fragment strings (`Corp. ... $`)

Examples:
- XLE: 29 common equities + 1 short-term holding; EC weight 99.61%
- XLG: 51 common equities + 2 short-term; EC weight 99.998%
- MTK: 34 common equities + 1 short-term; EC weight 99.96%
- XBI: 40 common equities + 1 short-term; EC weight 99.98%
- XSD: 21 common equities + 1 short-term; EC weight 99.96%

This is now the **accepted legacy analogue for `ASSET_CAT=EC`** for this research path: only holdings with explicit `COMMON_EQUITY` section attribution are EC; other/unknown sections are excluded.

### EC-filtered PIT input

Workflow: `Research NQ PIT EC Filtered 2006`
Run: `33715016882`
Artifact: `9878189715`

Rules:
- retain only explicit `COMMON_EQUITY` holdings;
- preserve their original parser-relative portfolio weights; **do not renormalize to 100 after EC filtering**;
- recompute structural eligibility using 10–120 EC holdings, total EC weight >=50, top-10 EC weight >=25.

Result:
- all **20 / 20** corrected PIT series remain structurally usable after EC filtering;
- EC weights are typically ~99–100%, so the filter removes short-term/debt/parser fragments without materially changing the equity portfolios.

### EC-filtered security mapping — active mapping baseline

Workflow: `Research NQ N-PX EC Filtered 2006`
Run: `33715050446`
Artifact: `9878201336`

Result on the same frozen N-PX master:
- PIT series: **20**
- EC holdings: 936
- mapping-eligible holdings after parser-artifact rejection: **935**
- unique matches: **654**
- count mapping coverage: **69.95%**
- weight mapping coverage: **78.98%**
- ambiguous holdings: 14
- unmapped holdings: 267

This supersedes 69.28% / 78.92% as the active mapping baseline because it now applies the accepted legacy EC bridge first.

## 10. Legacy US bridge — historical note

Schedule-level diagnostic run `33714585732`, artifact `9878045597` showed explicit country allocations only in DGT among the examined portfolios. DGT reported United States 62.7% plus United Kingdom, Switzerland, Japan, France and others.

SEC Form N-PORT Item C.5 requires the country where the issuer is organized as the primary country field. Therefore:
- listing on a US exchange does **not** prove `US`;
- a numeric CUSIP does not by itself prove `US`;
- absence of ADR/GDR text does not prove `US`;
- ADR/GDR is useful foreign-security evidence but is not a complete country classifier;
- otherwise country remains UNKNOWN until independent PIT issuer-country evidence exists.

See the superseding Section 0 for the current country-coverage results.

## 11. CORP bridge — historical note

The old bootstrap-based redundancy diagnostic was invalid because the serialized Production bootstrap had already filtered on EC+US+CORP. Do not use that old zero-row result.

See Section 0 for the later valid raw-filing transition check showing 226/226 EC+US holdings were CORP.

## 12. Transport issues

GitHub-hosted runners have repeatedly encountered SEC transport restrictions on several bulk/index routes. Transport failure is never evidence of data absence. Current examples include raw quarterly N-PORT ZIPs, full-index archives, and native filing-index pages.

For mapping-rule comparisons, continue using frozen artifacts where possible so live fetch variance cannot contaminate structural comparisons.

## 13. Current active gate

See Section 0. The concise rule is unchanged: **do not implement the historical builder until independent source discovery and conservative US attribution are sufficiently reproducible, then re-run aggregate Gate B.**

## 14. Anti-overfitting / data-preservation rules

- Never modify frozen Stage21 Production parameters based on reconstructed history.
- Never tune parser, mapping, US/CORP/EC, or universe rules against CAGR, MaxDD, Calmar, trades, or selected winners.
- Structural/data-quality evidence may fix objective parser/mapping defects.
- Keep unknown data unknown rather than forcing coverage.
- Define validation gates before opening broad historical return periods where practical.
- Reconstructed history is research, not True Forward OOS.
- Keep True Forward OOS from 2026-09-02 separate from all reconstruction work.

## 15. Key current files

Research delta:
- `docs/research/nq-npx-mapping-2006-20260903.md`
- `docs/research/gate-b-progress-2026-09-04.md`

Key scripts include:
- `scripts/research-nq-series-segmentation-2006.py`
- `scripts/research-nq-pit-holdings-2006-corrected.py`
- `scripts/research-nq-per-holding-ec-2006.py`
- `scripts/research-nq-pit-ec-filtered-2006.py`
- `scripts/research-nq-npx-structural-mapping-2006.py`
- `scripts/research-sec-us-attribution-full-shard-2006.py`
- `scripts/research-sec-us-attribution-unknown-retry-shard-2006.py`
- `scripts/research-country-unknown-retry-merge-2006.py`
- `scripts/research-structural-new-matches-country-2006.py`
- `scripts/research-legacy-filing-index-series-pilot-2006.py`

Key artifacts:
- corrected PIT: `9878011119`
- per-holding EC diagnostic: `9878123068`
- EC-filtered PIT: `9878189715`
- EC-filtered baseline mapping: `9878201336`
- frozen N-PX master: `9876020712`
- structural mapping: `9900708609`
- UNKNOWN-retry country merge: `9902743513`
- structural-new-matches country: `9903255442`

## 16. Handoff maintenance

When research advances:
- update this canonical file;
- update `docs/research/nq-npx-mapping-2006-20260903.md` with the detailed delta;
- update main `MOMENTUM_HANDOFF.md` if the active baseline or gate changes;
- record decisive run IDs, artifact IDs, failures, rejected paths, and replacement rules;
- keep the next action explicit so a new chat can resume without relying on conversation history.
