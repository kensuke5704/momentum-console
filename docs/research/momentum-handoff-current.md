# Momentum Research Handoff — Current

Last updated: 2026-09-02 JST
Branch: `research/cagr40-new-alpha-20260901`
Repository: `kensuke5704/momentum-console`

> This file is the canonical handoff for ongoing Momentum strategy research. Update it whenever research code, validation results, assumptions, conclusions, or next actions change.

## 1. Current objective

Validate whether the frozen Stage21 momentum strategy has useful out-of-sample-like robustness beyond the currently available 2020–2026 backtest period, without modifying the frozen production strategy.

The current workstream is specifically trying to reconstruct a longer historical ETF-holdings-based universe for 2006 onward using only free sources.

## 2. Frozen production strategy — do not modify

Frozen identifier: `momentum-stage21-sbi-2026-09-v1`
Frozen date: 2026-09-02
True Forward start: 2026-09-02

Stage21 allocations:
- NORMAL: Fixed60 85%, GLDM 15%
- YELLOW: Fixed60 55.5%, GLDM 22.5%, Cash 22%
- DEEP: Fixed60 25.5%, GLDM 30%, Cash 44.5%
- State priority: M3 > CFTC > NORMAL
- Monthly rebalance plus immediate state-change rebalance
- Transaction cost assumption: 10 bps one-way

Frozen backtest period: 2020-01-01 through 2026-08-25
- CAGR: 48.61%
- MaxDD: -16.89%
- Calmar: 2.879
- Final equity: 13.905x

Primary downside-control interpretation:
- M3 is the main downside-control engine.
- GLDM materially improves the return/drawdown tradeoff.
- CFTC is a secondary overlay.

Production/frozen logic must remain unchanged. All extended-history work stays in research-only scripts/workflows.

## 3. Existing robustness results

### 3.1 Local Stage21 SPA family

32 nearby Stage21-family candidates were tested.

Stage21 vs QQQ family-wise SPA p-values were approximately:
- block 5: 0.034
- block 10: 0.041 range
- block 20: within the same ~0.03–0.04 range

Stage21 vs Fixed60 raw mean-return SPA p-value = 1.0 because Fixed60 is intentionally riskier and has higher raw mean return. This does not invalidate the drawdown-controlled objective.

### 3.2 Architecture-wide SPA

Historical `cagr40-*` scripts were instrumented in GitHub Actions to capture all full-period `performanceStats()` curves.

- 333 unique full-period curves
- common sample: 2020-01-01 through 2026-08-25
- 1,669 common trading days
- 36/38 scripts succeeded
- `cagr40-sec-fundamental-stage6`: rc=1
- `cagr40-putcall-stage17`: timeout 120s

Architecture SPA vs QQQ:
- block 5: global p = 0.176
- block 10: global p = 0.161
- block 20: global p = 0.142

Stage21 family-wise p-values under the broad architecture family:
- block 5: 0.346
- block 10: 0.323
- block 20: 0.313

Conclusion: raw-return alpha does not survive broad architecture correction. Architecture-selection bias remains material and is not ruled out.

### 3.3 Architecture Calmar bootstrap

Script: `scripts/architecture-calmar-bootstrap.mjs`

Observed Stage21 Calmar rank: 1 / 333
Fixed60-like Calmar: 1.992

Paired stationary-bootstrap probability that Stage21 Calmar > Fixed60:
- block 5: 72.22%
- block 10: 74.42%
- block 20: 75.62%
- block 60: 78.88%

All 95% Calmar-difference intervals cross zero. Therefore this is supportive but not conventionally significant.

Relevant docs:
- `docs/research/stage21-validation-summary-20260902.md`
- `docs/research/stage21-spa-20260902.md`
- `docs/research/stage21-architecture-spa-20260902.md`
- `docs/research/stage21-calmar-bootstrap-20260902.md`

## 4. Why a longer backtest is needed

The current 2020–2026 sample is only about 6.7 years and is dominated by a limited set of market regimes.

A 2006–2026 test would add:
- pre-GFC expansion
- 2008 financial crisis
- 2009 recovery
- 2011 euro-area stress
- 2015–2016 correction
- 2018 selloff
- 2020 COVID shock
- 2022 tightening regime

The goal is not to refit Stage21 to this history. The goal is to reconstruct the historical data inputs as faithfully as possible, freeze the reconstruction rules before seeing performance, then run the frozen Stage21 logic.

## 5. Main data limitation

The production universe uses SEC N-PORT-based ETF holdings breadth.

Current universe implementation:
- `src/lib/universe/universe.ts`
- `src/lib/universe/sec-nport.ts`
- `src/lib/universe/nport-quarterly.ts`

Current universe score:

`3 * log1p(etfCount) + 0.5 * log1p(aggregateWeight) + 0.5 * log1p(recencyWeight)`

Eligibility filter includes:
- at least 10 and at most 120 holdings
- total positive holding weight >= 50
- top-10 weight >= 25
- excludes structured/income/broad-benchmark funds by series-name rules

Production N-PORT parsing also restricts holdings to US corporate equities using the N-PORT fields `ASSET_CAT=EC`, `INVESTMENT_COUNTRY=US`, and `ISSUER_TYPE=CORP`.

N-PORT itself cannot be extended far enough backward, so the research is testing legacy SEC fund filings as a historical bridge.

## 6. Free-source alternatives tested

### 6.1 SEC 13F — rejected as direct N-PORT substitute

Layline 13F was tested as a free institutional-holdings proxy.

2020 overlap diagnostics:
- average Top80 ticker mapping coverage: ~65.0%
- median mapping coverage: ~70.0%
- average direct N-PORT Top80 overlap: ~40.56%
- median direct overlap: ~43.13%
- average conditional overlap among mapped 13F names: ~55.29%
- median conditional overlap: ~59.09%

More importantly, production Top2 retention in 2020 was poor:
- 6 / 22 selected names retained in 13F Top80 = 27.3%
- both Top2 retained in only 2 / 11 months = 18.2%

Conclusion: 13F changes the economic universe too much. Do not use it for the extended Stage21 backtest.

### 6.2 Legacy N-Q / N-CSR — current primary route

This is conceptually much closer to N-PORT because it is registered-fund portfolio holdings data.

2006 SEC index extraction succeeded using the public Notre Dame master-index archive.

2006 target filing counts:
- total target forms: 13,610
- N-Q: 6,489
- N-CSR: 3,668
- N-CSRS: 3,067
- N-CSR/A: 238
- N-Q/A: 84
- N-CSRS/A: 64

2006 holdings parser pilot:
- fetch success: 100% in the fixed sample
- >=20 holdings parsed: 50.0%
- median parsed holdings: 35
- positive market values in 83.3% of sampled filings

2019 bridge parser pilot:
- fetch success: 100% in the fixed sample
- >=20 holdings parsed: 52.8%
- median parsed holdings: 21

Interpretation: old filings are not inherently unusable; parser quality is the main issue.

## 7. 2006 ETF-series identification — latest confirmed result

Targeted metadata probe run:
- workflow: `Research NQ Series Metadata 2006`
- run id: `33635790761`
- commit: `aea69ecf30f677786771917ce75540dffe907105`

Targeted sample: 14 known ETF registrant / Vanguard ETF-share-class candidates.

Result:
- fetch success: 14/14 = 100%
- series metadata rate: 78.57%
- ticker metadata rate: 71.43%
- structured series rate: 78.57%

Successfully recovered filing-time ETF ticker sets including:
- Select Sector SPDR: XLY, XLP, XLE, XLF, XLV, XLI, XLB, XLK, XLU
- Rydex ETF Trust: XLG, RSP
- StreetTRACKS: FEU, FEZ
- PowerShares examples: PBE, PBJ, PBS, PPA, PHO, PGJ, etc.
- StreetTRACKS Series Trust examples: RWR, SDY, XBI, XHB, XSD, etc.

Important caveats:
- iShares samples returned no SGML series metadata through the current transport/parser.
- ProShares returned series metadata but no tickers in that sample.
- Vanguard often embeds ETF share classes inside broader mutual-fund series, so explicit `ETF` text alone is insufficient.

Conclusion: historical ETF identification is feasible, but classification must use the SGML hierarchy and class-level metadata rather than only fund/series names.

## 8. Historical issuer/ticker/security-id mapping — N-PX pilot

Current supporting route: SEC Form N-PX.

2006 N-PX index:
- 3,541 filings total
- N-PX: 3,429
- N-PX/A: 112

Pilot run:
- workflow run: `33638519487`
- N-PX job id: `100275380996`
- sample fetch success: 4/4
- filings with >=1 ticker/security-ID pair: 50%
- filings with >=50 pairs: 50%
- median paired records: 200

Examples recovered directly from filing text:
- ABBOTT LABORATORIES → ABT → 002824100
- REYNOLDS & REYNOLDS CO. → REY → 761695105
- SUPERVALU INC. → SVU → 868536103

Conclusion: N-PX can become a free historical issuer ↔ ticker ↔ security-id security master, especially for securities no longer listed today.

Script:
- `scripts/research-npx-security-master-2006.py`

## 9. BeanCounter path — rejected for holdings reconstruction

BeanCounter was investigated as a free bulk EDGAR text mirror.

The 2006 shard range was identified around shards 144–164.

CUSIP extraction from generic text was not reliable:
- naive 9-character matching produced obvious false positives such as `TRUSTEES1`
- check-digit validation still allowed textual false positives such as `OFFICERS3`
- real CUSIPs found in the body often referred to the filing fund/share class itself rather than portfolio holdings

Conclusion: do not use BeanCounter CUSIP-frequency counting as the historical universe source.

## 10. N-Q series-to-holdings and PIT representation — confirmed but coverage-limited

The original segmentation feasibility probe in run `33638519487` reported 94 / 99 ETF series as segmentable. That was a coarse heading/series assignment feasibility measure and should not be interpreted as 94 usable holdings records.

A stricter end-to-end rerun was completed after the handoff was created:
- workflow run: `33644227262`
- commit: `cb74de04e3f0184e34b2b038bf0ec12459df7e82`
- 6 deterministic ETF registrant filings fetched successfully
- 34 series actually mapped to parsed schedule blocks
- 30 mapped series passed the production-style name exclusions
- 18 passed the preliminary structural rule of 10–120 parsed holdings and positive market value

A point-in-time holdings representation script was then added:
- `scripts/research-nq-pit-holdings-2006.py`
- stores accession, CIK, filing date, report date, series ID/name, fund ticker metadata, mapping score, parser method, holdings descriptions, market values, and parser-relative series weights
- weights are normalized from positive parsed market values within each series; they are not yet validated against reported net assets
- no return/performance data is used

The production top-10 concentration rule was then added and rerun:
- workflow run: `33644613585`
- commit: `1531b8caf5d5d6bfac7c060f6f99c67023d6cf41`
- filings attempted/succeeded: 6 / 6
- final PIT series records passing production-style name exclusions, 10–120 holdings, and normalized top-10 weight >=25%: **9**
- median holdings per retained record: **49**
- weight normalization error: **0.0**

Examples of retained PIT records:
- XLE — report date 2005-12-31, filing date 2006-02-28, 30 holdings, top-10 weight ~63.75%
- XLG — report date 2006-01-31, filing date 2006-03-27, 52 holdings, top-10 weight ~43.24%
- MTK — report date 2006-03-31, filing date 2006-05-24, 49 holdings, top-10 weight ~38.37%
- XBI — report date 2006-03-31, filing date 2006-05-24, 14 holdings, top-10 weight ~97.54%
- XHB — report date 2006-03-31, filing date 2006-05-24, 41 holdings, top-10 weight ~26.72%

Interpretation:
- series-level PIT holdings reconstruction is technically feasible for legacy N-Q filings
- current coverage is not yet sufficient for a historical universe backtest
- the earlier 94/99 segmentation number was optimistic if treated as end-to-end usable coverage
- parser/mapping coverage, issuer ticker mapping, and the lack of direct legacy equivalents for N-PORT `US/CORP/EC` fields remain active limitations

## 11. Current active gate: historical security mapping and coverage improvement

Do not run 2006–2018 Stage21 performance yet.

The next technical gate is to turn the retained legacy holdings descriptions into stable point-in-time security identities and determine whether coverage can become sufficient for N-PORT-like breadth ranking without performance-driven tuning.

Proceed next with:
1. Expand the N-PX security master beyond the four-file feasibility pilot using a deterministic, non-performance-based sampling/build rule.
2. Normalize legacy N-Q issuer descriptions and join them to N-PX issuer ↔ ticker ↔ security-id records.
3. Measure mapping coverage by holdings count and by holdings weight for the retained N-Q PIT series.
4. Diagnose currently unmapped N-Q series/schedule blocks using parser/structure evidence only.
5. Investigate structural proxies for the missing N-PORT `US/CORP/EC` fields; do not choose rules based on strategy returns.
6. Only after mapping/coverage quality is acceptable, construct the legacy universe scoring inputs.

## 12. Planned validation sequence

Do not jump directly to a 2006–2026 performance backtest.

Proceed in this order:

1. N-Q series-to-holdings segmentation feasibility test. **Completed; feasible but coverage-limited.**
2. Point-in-time historical ETF-series holdings representation. **Pilot completed; 9 retained records under production-style structural constraints in the current six-filing sample.**
3. Build/extend historical issuer ↔ ticker/security-id mapping, using N-PX where needed. **Current step.**
4. Construct a legacy-N-Q universe using the same economic scoring inputs as the N-PORT universe where possible:
   - ETF count
   - aggregate weight
   - max weight
   - recency-weighted weight
5. Use an overlap period near the N-Q/N-PORT transition to measure:
   - Top80 overlap
   - rank correlation
   - production Top2 retention
6. Freeze the legacy-universe conversion rules before looking at 2006–2018 Stage21 performance.
7. If the bridge is sufficiently faithful, extend the universe backward and run frozen Stage21 research backtests.
8. Report the extended test separately from the frozen 2020–2026 production backtest.

## 13. Interpretation rules / anti-overfitting constraints

- Do not change Stage21 production parameters based on extended-history results.
- Do not tune legacy parser/universe rules against CAGR, MaxDD, Calmar, or trade outcomes.
- Parser and mapping quality may be improved using only structural/data-quality evidence.
- Define overlap/mapping acceptance rules before running long-history performance where practical.
- Label any proxy period clearly; do not call it true OOS.
- Keep True Forward OOS from 2026-09-02 conceptually separate from all historical reconstruction work.

## 14. Known research-code caveat

`stage21-spa.ts` has/had a GLDM→Cash spread-order issue in the research script. The relevant workflow patched it at runtime. Frozen production strategy is unaffected.

If touching SPA research code again, cleanly verify/fix source parity before using new results.

## 15. Important files

Production/universe logic:
- `src/lib/universe/universe.ts`
- `src/lib/universe/sec-nport.ts`
- `src/lib/universe/nport-quarterly.ts`
- `scripts/build-universe.ts`

Long-history research:
- `scripts/research-nq-index-extract.py`
- `scripts/research-nq-parser-pilot.py`
- `scripts/research-nq-bridge-2019.py`
- `scripts/research-nq-series-metadata-2006.py`
- `scripts/research-nq-series-segmentation-2006.py`
- `scripts/research-nq-pit-holdings-2006.py`
- `scripts/research-npx-security-master-2006.py`
- `.github/workflows/research-nq-index-extract.yml`
- `.github/workflows/research-nq-series-metadata-2006.yml`

Robustness research:
- `scripts/stage21-spa.ts`
- `scripts/architecture-spa-analyze.mjs`
- `scripts/architecture-calmar-bootstrap.mjs`

## 16. Handoff protocol

At the start of a new chat/session:

1. Read this file first.
2. Inspect the latest commit on `research/cagr40-new-alpha-20260901`.
3. Inspect any workflow run IDs listed in the current active gate.
4. Continue from the `Planned validation sequence` without re-running already rejected approaches unless there is new evidence.
5. Do not modify frozen Stage21 production/backtest logic.

When research is changed:

- Update this file in the same change set/commit whenever possible.
- Update `Last updated`.
- Move completed items out of `Current active gate` into confirmed results.
- Record decisive run IDs, commit SHAs, metrics, failures, and rejected paths.
- Keep the next action explicit so a new chat can resume without relying on conversation history.
