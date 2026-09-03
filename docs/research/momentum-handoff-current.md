# Momentum Research Handoff — Current

Last updated: 2026-09-03 JST
Branch: `research/nq-npx-mapping-2006-20260903`
Repository: `kensuke5704/momentum-console`

> This file is the canonical handoff for ongoing Momentum strategy research. Update it whenever research code, validation results, assumptions, conclusions, or next actions change.

## 1. Current objective

Reconstruct a point-in-time historical ETF-holdings universe for 2006 onward that is economically as close as possible to the frozen Production N-PORT universe, then use it only for robustness research after the reconstruction rules are frozen.

The immediate work is **data reconstruction and structural parity**, not strategy optimization.

Do not run a broad 2006–2018 performance backtest yet. The user explicitly wants the older history preserved from repeated exploratory use.

## 2. Frozen Production strategy — do not modify

Frozen identifier: `momentum-stage21-sbi-2026-09-v1`
Frozen date / True Forward start: 2026-09-02

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

Production/frozen logic must remain unchanged. All extended-history work stays in research-only scripts/workflows.

## 3. Existing robustness context

Architecture-selection bias remains material.

Architecture-wide SPA over 333 full-period curves:
- global p vs QQQ: 0.176 / 0.161 / 0.142 for blocks 5 / 10 / 20
- Stage21 family-wise p under the broad architecture family: 0.346 / 0.323 / 0.313

Architecture Calmar bootstrap:
- observed Stage21 Calmar rank 1 / 333
- probability Stage21 Calmar > Fixed60 about 72%–79% depending on block length
- all 95% Calmar-difference intervals cross zero

Interpretation: current evidence is supportive on risk-adjusted performance but does not remove architecture-selection risk. Longer history is for validation, not refitting.

## 4. Production universe target

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

Historical N-Q / N-CSR does not expose these fields directly, so the legacy bridge must reproduce their economic meaning conservatively.

## 5. Alternative historical sources already evaluated

### 13F — rejected as direct substitute

2020 overlap work showed the 13F route changes the economic universe too much. Production Top2 retention was only 6/22 names, with both Top2 retained in only 2/11 months. Do not use 13F as the extended Production-universe source.

### BeanCounter generic CUSIP-frequency route — rejected

Generic filing text generated false CUSIP-like tokens and frequently captured the filing fund/share class rather than portfolio holdings. Do not revive this route without materially new evidence.

### Legacy N-Q / N-CSR — active primary route

Registered-fund portfolio filings are conceptually much closer to N-PORT. Historical filing parsing and filing-time ETF-series metadata recovery are feasible, but parser/series mapping/security identity and legacy US/CORP/EC parity must be validated first.

### N-PX — active security-master support route

Historical N-PX can expose issuer ↔ ticker ↔ security-ID relationships, including delisted securities. It is currently used as a historical security master for N-Q issuer descriptions.

## 6. Critical correction: prior nine-series PIT sample is invalidated

A structural audit on 2026-09-03 found that the earlier N-Q segmentation was wrong.

Old behavior:
- every `SCHEDULE OF INVESTMENTS (CONTINUED)` marker was treated as a separate portfolio candidate;
- each page was assigned to an ETF series using token overlap in the holdings body;
- the largest `(holding count, mapping score)` page could replace the actual portfolio page.

This caused false assignments. For example, a software continuation page was assigned to SPDR Biotech ETF because software/security text overlapped an ETF-series token context; the actual Biotech page was then displaced.

Therefore:
- old PIT artifact `9854510485` is superseded;
- the old nine-series sample is not a valid universe-quality input;
- the former 43.53% count / 60.67% weight frozen-master mapping number is retained only as mapping-engine history and must not be used as the active baseline.

No strategy returns were inspected in discovering or fixing this issue.

## 7. Corrected schedule-to-series segmentation

Implemented in `scripts/research-nq-series-segmentation-2006.py`.

Active structural rule:
1. identify each schedule page using the nearest exact filing-time registered ETF series title around the schedule marker;
2. do not use holdings or industry words to determine series identity;
3. continuation pages remain assigned to that explicit series;
4. concatenate all pages belonging to the same series before parsing holdings;
5. for the final schedule, stop after the first explicit `NET ASSETS ... 100%` boundary so later filing tables cannot bleed into holdings;
6. apply structural eligibility only after the complete grouped portfolio is parsed.

Supporting audits:
- schedule-assignment audit run `33714110948`, artifact `9877891675`
- explicit-series-boundary audit run `33714195904`, artifact `9877920529`

The old token-overlap helper remains only for compatibility/diagnostics and must not construct PIT holdings.

## 8. Corrected 2006 PIT holdings — active baseline

Workflow: `Research NQ PIT Holdings 2006 Corrected`
Run: `33714482859`
Artifact: `9878011119`

The source submissions are frozen to the same three N-Q filings used by the earlier pilot; only the structurally incorrect assignment method changed.

Result:
- retained PIT series: **20**
- median holdings per retained series: **41**

Selected corrected portfolios:
- XLE: 30 holdings; Exxon Mobil, Chevron, ConocoPhillips, Burlington Resources, Halliburton, etc.
- MTK: 35 holdings; NVIDIA, Broadcom, Cisco, Jabil, Network Appliance, SAP ADR, HP, Qualcomm, etc.
- XBI: 41 holdings; Nektar, Amylin, Celgene, Affymetrix, Serologicals, United Therapeutics, PDL BioPharma, Techne, etc.
- XHB: 22 holdings; Sherwin-Williams, Lennar, Brookfield Homes, Toll Brothers, M/I Homes, Home Depot, etc.
- XSD: 22 holdings after final-schedule trimming; NVIDIA, Rambus, Intersil, Texas Instruments, International Rectifier, Agere, Microchip, Altera, etc.

Treat artifact `9878011119` as the active 2006 N-Q PIT input until a broader corrected sample supersedes it.

## 9. Frozen N-PX master and corrected mapping baseline

Frozen best merged N-PX master artifact: `9876020712`.

Master construction:
- deterministic 24-filing equal-quantile baseline
- independently pre-fixed broad/large fund-family supplement
- 2,925 paired records
- 2,687 unique normalized issuers
- no N-Q target-name selection and no return/performance selection.

Accepted conservative mapping rules:
- reject placeholder/invalid ticker identities;
- require structurally valid security IDs;
- normalize common legal suffixes;
- strip trailing N-Q footnote markers;
- normalize leading/trailing `THE`;
- collision-tested `HLDGS` ↔ `HOLDINGS` and `PHARMACEUTICALS` ↔ `PHARMACEUTICAL`;
- remove ADR suffix only when the base issuer resolves to exactly one valid identity;
- ambiguous ADR bases remain unresolved;
- fuzzy candidates are diagnostic only and never accepted automatically.

Corrected mapping workflow:
- run `33714515426`
- artifact `9878021112`

Result:
- PIT series: 20
- total parsed holdings: 964
- parser artifacts: 20
- eligible holdings: **944**
- unique matched holdings: **654**
- count coverage: **69.28%**
- weight coverage: **78.92%**
- ambiguous holdings: 14
- unmapped holdings: 276

Selected eligible-weight coverage:
- XLE 94.41%
- XLG 93.54%
- XLV 97.56%
- XLP 88.85%
- XLF 85.26%
- XLI 86.04%
- XLK 88.11%
- MTK 81.15%
- XBI 72.42%
- XHB 52.61%
- XSD 66.67%

Remaining unmapped weight is distributed across weak/name-gap/no-master/security-class/ADR categories; no fuzzy auto-acceptance is permitted.

## 10. Legacy `EC` / `US` structural evidence

Workflow: `Research NQ Legacy EC US Diagnostic 2006`
Run: `33714585732`
Artifact: `9878045597`

Thirty corrected explicit-series schedules were examined.

### EC

28 / 30 series explicitly print `COMMON STOCK(S/SHARES) -- xx%`.

Examples:
- XLE 99.8%
- XBI 100.0%
- XSD 100.0%
- most examined sector/style portfolios 99.5%–100.0%

Short-term investments are generally printed separately.

Conclusion: legacy N-Q contains strong schedule-level evidence for an `ASSET_CAT=EC` analogue. However, a portfolio-level common-stock percentage is not yet a validated per-holding EC classification. The next step is to carry explicit section state down to individual holdings and measure attribution coverage on corrected portfolios.

### US

Do **not** default country-unknown holdings to US.

Only one examined series printed explicit country allocations: DGT, including:
- United States 62.7%
- United Kingdom 17.7%
- Switzerland 7.1%
- Japan 2.6%
- France 2.3%
- other smaller countries.

DGT has many ADR/GDR references. MTK also contains ADR references without explicit country-allocation headings.

Conclusion: explicit country sections are usable where present; ADR/GDR is a useful foreign-security flag, but neither absence of a country heading nor absence of ADR text proves `US`. `INVESTMENT_COUNTRY=US` parity remains unresolved.

### CORP

`ISSUER_TYPE=CORP` parity remains a separate gate. Do not silently equate “mapped listed security” or “common stock” with N-PORT `CORP` until structurally validated.

## 11. 64-CIK N-PX master design and transport issue

Frozen expanded-master design:
- primary N-PX only
- one deterministic representative per unique CIK
- sort representatives by CIK
- sample 64 equal-quantile CIK positions
- no N-Q target names, universe outcomes, momentum, or returns in source selection.

Transport status:
- SEC quarterly `master.idx` from GitHub-hosted runners: HTTP 403
- SEC `master.zip`: HTTP 403
- tested proxy `master.idx` path: HTTP 422

This is a data-transport limitation, not evidence that the historical SEC index is absent.

Do not block EC/US/CORP work on this issue. Continue the reproducible source-index path in parallel.

For mapping-rule experiments use frozen master artifact `9876020712`; do not compare live broad-supplement runs when their fetched source sets differ.

## 12. Current active gate

Do **not** run 2006–2018 Stage21 performance yet.

Proceed in this order:
1. keep corrected PIT artifact `9878011119` as the active 2006 N-Q baseline;
2. implement and validate per-holding `EC` attribution from explicit N-Q section state on corrected grouped portfolios;
3. develop a conservative `US` attribution hierarchy using explicit country sections and independently verifiable security evidence; unknown remains unknown;
4. investigate `CORP` parity separately;
5. continue the deterministic 64-CIK source-index/master path in parallel;
6. once security identity and US/CORP/EC rules are sufficiently defensible, construct legacy scoring inputs matching Production economics: ETF count, aggregate weight, max weight, recency-weighted weight;
7. validate the bridge in an overlap period using Top80 overlap, rank correlation, and Production Top2 retention;
8. freeze the bridge rules before exposing older return history;
9. only then use small staged historical windows before any broad 2006–2018 test.

## 13. Anti-overfitting / data-preservation rules

- Never modify frozen Stage21 Production parameters based on reconstructed history.
- Never tune parser, security mapping, US/CORP/EC rules, or universe conversion against CAGR, MaxDD, Calmar, trade outcomes, or selected winners.
- Structural/data-quality evidence may be used to fix objective parser/mapping errors.
- Keep unknown data unknown rather than forcing coverage.
- Define validation/gate criteria before opening broad historical return periods where practical.
- Treat all reconstructed historical tests as research, not true OOS.
- Keep True Forward OOS from 2026-09-02 separate from all historical reconstruction.

## 14. Rejected/replaced paths that should not be revived casually

- 13F as direct Production-universe substitute: rejected by weak overlap/Top2 retention.
- BeanCounter generic CUSIP-frequency extraction: rejected for false identities.
- holdings-content token overlap for N-Q schedule→series assignment: **rejected and superseded** after structural misassignment audit.
- automatic fuzzy issuer mapping: prohibited.
- assuming no country heading means US: prohibited.
- comparing mapping coverage across live broad-supplement runs with different fetch success: prohibited.
- broad 2006–2018 Stage21 performance before bridge freeze: prohibited.

## 15. Files to read next

Latest detailed delta:
- `docs/research/nq-npx-mapping-2006-20260903.md`

Key current scripts:
- `scripts/research-nq-series-segmentation-2006.py`
- `scripts/research-nq-pit-holdings-2006-corrected.py`
- `scripts/research-nq-npx-mapping-2006.py`
- `scripts/research-nq-unmapped-diagnostics-2006.py`
- `scripts/research-nq-legacy-ec-us-diagnostic-2006.py`

Key current workflows:
- `.github/workflows/research-nq-pit-holdings-2006-corrected.yml`
- `.github/workflows/research-nq-npx-corrected-pit-2006.yml`
- `.github/workflows/research-nq-legacy-ec-us-diagnostic-2006.yml`

## 16. Handoff maintenance

When research advances:
- update this canonical file;
- update `docs/research/nq-npx-mapping-2006-20260903.md` with the detailed delta;
- update main `MOMENTUM_HANDOFF.md` if the active branch, canonical location, active baseline, or gate changes;
- record decisive run IDs, artifact IDs, failures, rejected paths, and replacement rules;
- keep the next action explicit so a new chat can resume without relying on conversation history.
