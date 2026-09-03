# Momentum Research Handoff — Current

Last updated: 2026-09-03 JST
Branch: `research/cagr40-new-alpha-20260901`
Repository: `kensuke5704/momentum-console`

> Canonical handoff for ongoing Momentum research. The exact live branch head must always be read from GitHub. Material research changes are required to update this file; a freshness CI gate enforces that policy.

## 1. Current objective

Reconstruct a point-in-time ETF-holdings universe for 2006–2018 that is structurally faithful to the frozen Production N-PORT universe, without changing the Production strategy and without consuming the historical return sample all at once.

The immediate question is **universe reproducibility**, not strategy performance: can legacy N-Q/N-CSR holdings, with N-PX identity support, reproduce the same economic universe that Production builds from N-PORT?

## 2. Frozen Production — do not modify

Frozen identifier: `momentum-stage21-sbi-2026-09-v1`
True Forward start: 2026-09-02

Stage21 allocations:
- NORMAL: Fixed60 85%, GLDM 15%
- YELLOW: Fixed60 55.5%, GLDM 22.5%, Cash 22%
- DEEP: Fixed60 25.5%, GLDM 30%, Cash 44.5%
- State priority: M3 > CFTC > NORMAL
- Monthly rebalance plus immediate state-change rebalance
- Transaction cost assumption: 10 bps one-way

Frozen Production/backtest logic remains untouched. Historical reconstruction is research-only.

## 3. Production universe rule that legacy history must reproduce

Production universe inputs per security:
- distinct ETF count (`etfCount`)
- aggregate holding weight
- maximum holding weight
- filing-recency-weighted holding weight

Production score:

`3*log1p(etfCount) + 0.5*log1p(aggregateWeight) + 0.5*log1p(recencyWeight)`

Security eligibility:

`etfCount >= 2 OR maxWeight >= 4`

Recency:

`exp(-ageDays / 120)`

ETF structural eligibility includes Production-style series-name exclusions, 10–120 holdings, total positive weight >=50, and top-10 concentration >=25. N-PORT additionally exposes explicit `ASSET_CAT=EC`, `INVESTMENT_COUNTRY=US`, and `ISSUER_TYPE=CORP`; legacy filings require a structural proxy for these fields.

Key Production files:
- `src/lib/universe/universe.ts`
- `src/lib/universe/sec-nport.ts`
- `src/lib/universe/nport-quarterly.ts`
- `scripts/build-universe.ts`

## 4. Legacy source architecture — frozen direction

Primary historical route:
- N-Q: main legacy portfolio-holdings source through 2006–2018
- N-CSR/N-CSRS: complementary holdings source and 2020 overlap-validation source
- N-PX: historical issuer ↔ ticker ↔ security-id support

Rejected as direct Production-universe substitutes:
- direct 13F universe: economic universe differs too much; 2020 Production Top2 retention was poor
- BeanCounter/CUSIP-frequency reconstruction: false-positive and fund-level CUSIP contamination

Do not revive rejected routes without new structural evidence.

## 5. Critical N-Q series-assignment correction

The first legacy parser sometimes attached a `Schedule of Investments` block to the neighboring ETF series because the actual series heading appeared before the generic schedule marker.

Current strict rule:
- inspect a tight pre/post schedule-heading context
- prefer exact filing-time series phrase
- reject exact ties and near ties
- use the same mapping rule in segmentation and PIT holdings construction
- run deterministic semantic anchors for known ETF series

Strict 2006 result:
- filings succeeded: 6/6
- retained PIT series: 13
- median holdings: 54
- weight normalization error: 0
- semantic audit: PASS

Known coherent retained series include XLY, XLE, XLI, XLB, XLK, ELR, ELG, ELV, DGT, KBE, KCE, KIE and OOO. Previously misassigned XBI/XHB/MTK schedules are no longer force-retained.

## 6. Historical security identity — latest confirmed 2006 result

N-PX master uses 96 deterministic equal-quantile filing positions; selection does not use performance.

Latest completed mapping workflow: `33653470171`

Identity tiers:
- Tier A: unique exact/conservative legal-name issuer match to exactly one `(ticker, securityId)`
- Tier B: no Tier A; unique issuer match to one structurally valid 2–5 character historical ticker with missing securityId
- Unresolved: multiple identities/tickers, parser/header token, one-character ticker-only evidence, fuzzy-only evidence, or no structural match

Corrected 13-series result:
- eligible holdings: 728
- Tier A count: 616 / 728 = 84.62%
- Tier A eligible-weight coverage: **91.21%**
- Tier B count: 3 / 728 = 0.41%
- Tier B eligible-weight coverage: **0.15%**
- Tier A+B eligible-weight coverage: **91.37%**
- ambiguous weight: ~1.83%
- unmapped count: 93

Selected per-series Tier A+B weight coverage:
- XLE 100.0%
- XLI 96.2%
- XLK 92.6%
- ELR 92.2%
- ELG 95.0%
- ELV 93.3%
- KBE 94.2%
- KCE 88.0%
- KIE 94.6%
- OOO 97.1%
- XLY 89.7%
- XLB 85.5%
- DGT 68.6%

Interpretation: 2006 identity mapping is structurally strong enough to continue, but this alone does **not** prove Production-universe parity.

## 7. Legacy proxy for N-PORT US/CORP/EC

Only explicit structural evidence is used:
- accepted Tier A/B identity required
- ADR/GDR/depositary receipt -> `NON_US_PROXY`
- debt/preferred/options/warrants/rights -> `NON_EC_PROXY`
- LP/limited partnership/LLC -> `NON_CORP_PROXY`
- otherwise -> `LEGACY_EQUITY_CANDIDATE`

Do not infer domicile from issuer spelling, ticker, price availability or performance.

2006 corrected 13-series aggregate:
- total parser-relative weight: 1300.0
- accepted identity weight: 1180.68 = 90.82%
- legacy equity candidate weight: 1175.52 = **90.42%**
- unresolved identity weight: 111.57
- parser artifact weight: 7.75
- explicit ADR/GDR exclusion weight: 5.16

## 8. Universe reproducibility gates — current source of truth

The current reproducibility implementation is `scripts/research-legacy-universe-reproducibility-2020.py`.

### Gate A — shared-series fidelity

Hold the SEC `seriesId` set fixed and compare legacy N-CSR/N-CSRS reconstruction against nearest same-series N-PORT holdings.

PASS requires:
- at least 10 paired series
- median legacy symbol-weight coverage >= **80%**
- Top80 overlap >= **80%**
- common-Top80 rank correlation >= **0.80**
- N-PORT Top2 retention >= **90%**

This isolates parser + issuer identity + scoring fidelity.

### Gate B — missing-series impact

Use N-PORT holdings on both sides:
- full eligible N-PORT series set
- N-PORT restricted to series that the legacy pipeline can reconstruct

PASS requires:
- Top80 overlap >= **80%**
- common-Top80 rank correlation >= **0.80**
- N-PORT Top2 retention >= **90%**

This isolates source-series coverage from parser/mapping error.

**Only Gate A + Gate B PASS allows the bridge to be called structurally equivalent to the Production universe.**

## 9. Current reproducibility status

Parity is **not yet established**.

Latest fast workflow attempt:
- workflow: `Research Legacy Universe Reproducibility Fast 2020`
- run: `33660812007`
- head at that run: `95c2f7be8fc56dc609c1c75e10dfe9ae1b6d35bf`
- conclusion: failure before metrics were produced
- cause: GitHub runner received HTTP 403 while fetching SEC quarterly `master.idx`

This is a transport failure, not a Gate A/B metric failure. Do not interpret it as evidence for or against universe parity.

Parser lessons already confirmed:
- SPDR legacy reports can be parsed correctly by the original parser path
- some iShares/modern shareholder reports need HTML fallback because the plain-text path can misread a year/header as a holding
- the current parser is composite: preserve the original result when structurally sane, invoke HTML fallback only for zero/obvious-artifact output

Next reproducibility task: remove SEC runner-network dependence by using a deterministic frozen 2020 filing/overlap fixture, then run Gate A/B on identical fixed inputs.

## 10. Historical-data preservation protocol

Structural filing data may be inspected across **all 2006–2018** years for parser, identity, PIT and universe reconstruction work. Performance data must not be consumed all at once.

Performance windows are frozen:
1. DEVELOPMENT: 2006-01-01 .. 2010-12-31
2. VALIDATION: 2011-01-01 .. 2014-12-31
3. SEALED_HOLDOUT: 2015-01-01 .. 2018-12-31

Default code permits DEVELOPMENT only. Later phases require explicit environment gates through `scripts/research-legacy-history-periods.py`.

Do not open any historical performance window until universe reproducibility/conversion rules are structurally frozen. Do not change parser/universe rules because of CAGR, MaxDD, Calmar, returns, trade outcomes or other performance quantities.

## 11. 2006–2018 filing availability

The structural inventory confirmed N-Q availability across the full 2006–2018 span. Therefore the preferred long-history architecture remains:

**N-Q throughout the legacy period + N-CSR/N-CSRS complement + N-PX identity support.**

Cross-year structural sampling must be deterministic. Samples may not be selected or replaced based on parser success or strategy outcomes.

## 12. Existing robustness context

Frozen Stage21 remains promising on the available 2020–2026 sample, but broad architecture correction does not establish conventional raw-return significance.

Architecture-wide results already recorded:
- 333 full-period curves
- global SPA vs QQQ p approximately 0.176 / 0.161 / 0.142 for block 5/10/20
- Stage21-family p approximately 0.346 / 0.323 / 0.313
- observed Stage21 Calmar rank 1/333
- paired stationary-bootstrap P(Stage21 Calmar > Fixed60) 72.22% / 74.42% / 75.62% / 78.88% for block 5/10/20/60
- all 95% Calmar-difference intervals cross zero

This is why the longer historical test is useful, but it must not be contaminated by reconstruction tuning.

## 13. Current active sequence

1. **DONE:** strict N-Q schedule→series correction and semantic audit.
2. **DONE:** 2006 N-PX identity mapping; Tier A+B weight coverage 91.37%.
3. **DONE:** structural legacy US/CORP/EC proxy definition; no performance tuning.
4. **DONE:** staged historical-performance guard; 2011–2018 remain sealed by default.
5. **IN PROGRESS:** freeze deterministic 2020 overlap fixture so validation no longer depends on SEC runner transport.
6. Run Gate A shared-series reproducibility on the fixed fixture.
7. Run Gate B missing-series impact on the same fixture.
8. If either gate fails, diagnose by filing/parser/series evidence only; thresholds must not be relaxed.
9. If both pass, freeze legacy conversion rules and build monthly PIT universe history for 2006–2018 without strategy returns.
10. Only then open DEVELOPMENT performance (2006–2010).
11. Keep VALIDATION (2011–2014) and SEALED_HOLDOUT (2015–2018) closed until their predeclared release conditions are met.

## 14. Important files

Canonical/current:
- `docs/research/momentum-handoff-current.md`
- `docs/research/nq-npx-mapping-2006-20260903.md`
- `docs/research/legacy-universe-data-gates.md`
- `docs/research/legacy-history-evaluation-protocol.md`

Legacy reconstruction:
- `scripts/research-nq-series-segmentation-2006.py`
- `scripts/research-nq-pit-holdings-2006.py`
- `scripts/research-npx-security-master-build-2006.py`
- `scripts/research-nq-npx-mapping-2006.py`
- `scripts/research-legacy-holdings-parser.py`
- `scripts/research-ncsr-nport-overlap-2020.py`
- `scripts/research-legacy-universe-reproducibility-2020.py`
- `scripts/research-legacy-universe-reproducibility-fast-2020.py`
- `scripts/research-legacy-history-periods.py`

## 15. Freshness protocol

At the start of every session:
1. Read this file.
2. Read the live branch head from GitHub; do not trust a SHA copied into conversation history as current.
3. Inspect any newer research workflow runs/artifacts relevant to the active sequence.
4. Treat this file and current code as authoritative over older chat summaries.

On every material research change:
- update this file in the same change set whenever possible
- record decisive metrics/run IDs and rejected paths
- remove or explicitly mark superseded conclusions
- never leave an older pilot result presented as the current result
- freshness CI must fail when material research code/docs/workflows change without this canonical handoff being updated

Production strategy remains frozen and separate.