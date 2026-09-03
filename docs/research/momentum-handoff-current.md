# Momentum Research Handoff — Current

Last updated: 2026-09-03 JST
Branch: `research/nq-npx-mapping-2006-20260903`
Repository: `kensuke5704/momentum-console`

> Canonical handoff for ongoing Momentum research. Update this file whenever the active baseline, validation result, rejected path, or next gate changes.

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

## 10. Legacy US bridge — active unresolved gate

Schedule-level diagnostic run `33714585732`, artifact `9878045597` showed explicit country allocations only in DGT among the examined portfolios. DGT reported United States 62.7% plus United Kingdom, Switzerland, Japan, France and others.

SEC Form N-PORT Item C.5 requires the country where the issuer is organized as the primary country field. Therefore:
- listing on a US exchange does **not** prove `US`;
- a numeric CUSIP does not by itself prove `US`;
- absence of ADR/GDR text does not prove `US`;
- ADR/GDR is useful foreign-security evidence but is not a complete country classifier;
- explicit N-Q country sections may be used where present;
- otherwise country remains UNKNOWN until an independent issuer-country source is established.

Next US work should seek a scalable historical issuer-organization-country source keyed by the mapped ticker/security ID/issuer. Do not introduce hand-curated winner-by-winner country labels.

## 11. CORP bridge — unresolved; failed redundancy shortcut rejected

A diagnostic attempted to infer whether `ISSUER_TYPE=CORP` is redundant after `EC+US` from `data/sec-nport/bootstrap.json.gz`.

Run: `33714843202`, artifact `9878130348`.

That attempt is **invalid for this question** because the Production bootstrap is already serialized as filtered `NportFiling[]`; `src/lib/universe/nport-quarterly.ts` discards raw N-PORT holdings unless they already satisfy `ASSET_CAT=EC`, `INVESTMENT_COUNTRY=US`, and `ISSUER_TYPE=CORP`. The raw issuer-type field is therefore not retained in the bootstrap and the 0-row diagnostic cannot measure redundancy.

Do not interpret that run as evidence about CORP. A valid CORP study requires raw quarterly N-PORT rows or a separate legacy structural rule.

## 12. 64-CIK N-PX master design and transport issue

Frozen expanded-master design:
- primary N-PX only;
- one deterministic representative per unique CIK;
- sort by CIK;
- sample 64 equal-quantile CIK positions;
- no N-Q target names, universe outcomes, momentum, or returns in source selection.

Transport status from GitHub-hosted runners:
- SEC quarterly `master.idx`: HTTP 403
- SEC `master.zip`: HTTP 403
- tested proxy `master.idx`: HTTP 422

This is a transport limitation, not evidence that the historical index is absent. Continue this path in parallel but do not block US/CORP work on it.

For mapping-rule comparisons, continue using frozen master artifact `9876020712` so live filing-fetch variance cannot contaminate results.

## 13. Current active gate

Do **not** run 2006–2018 Stage21 performance yet.

Proceed in this order:
1. treat EC-filtered PIT artifact `9878189715` as the active 2006 holdings input for subsequent parity work;
2. preserve EC-filtered mapping artifact `9878201336` as the active security-mapping baseline;
3. build a conservative, scalable per-holding `US` attribution hierarchy based on issuer organization country; explicit N-Q country sections are usable, unknown remains unknown;
4. investigate `CORP` parity independently using raw N-PORT or defensible legacy structural evidence;
5. continue deterministic 64-CIK source-index/master work in parallel;
6. only after US/CORP and security-identity coverage are sufficiently defensible, construct legacy scoring inputs: ETF count, aggregate weight, max weight, recency-weighted weight;
7. validate the bridge in an overlap period using Top80 overlap, rank correlation, and Production Top2 retention;
8. freeze the bridge before exposing older returns;
9. then use small staged historical windows before any broad 2006–2018 test.

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

Scripts:
- `scripts/research-nq-series-segmentation-2006.py`
- `scripts/research-nq-pit-holdings-2006-corrected.py`
- `scripts/research-nq-per-holding-ec-2006.py`
- `scripts/research-nq-pit-ec-filtered-2006.py`
- `scripts/research-nq-npx-mapping-2006.py`
- `scripts/research-nq-unmapped-diagnostics-2006.py`
- `scripts/research-nq-legacy-ec-us-diagnostic-2006.py`

Current artifacts:
- corrected PIT: `9878011119`
- per-holding EC diagnostic: `9878123068`
- EC-filtered PIT: `9878189715`
- EC-filtered mapping: `9878201336`
- frozen N-PX master: `9876020712`

## 16. Handoff maintenance

When research advances:
- update this canonical file;
- update `docs/research/nq-npx-mapping-2006-20260903.md` with the detailed delta;
- update main `MOMENTUM_HANDOFF.md` if the active baseline or gate changes;
- record decisive run IDs, artifact IDs, failures, rejected paths, and replacement rules;
- keep the next action explicit so a new chat can resume without relying on conversation history.
