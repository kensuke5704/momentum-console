# Legacy Universe Data-Quality Gates

Last updated: 2026-09-03 JST
Branch: `research/cagr40-new-alpha-20260901`

These gates use filing/data-quality evidence only. Strategy returns must not be used to pass, relax, or redefine them.

## Gate A — point-in-time integrity

- Every source filing used for an as-of date must have `filingDate <= asOf`.
- Select the latest public record per SEC `seriesId`; ties use accession ordering only.
- `reportDate` never makes data public before `filingDate`.
- No constituent is selected because of future listing survival or future price availability.

PASS: zero known look-ahead violations in deterministic audits.

## Gate B — schedule-to-series integrity

- Use filing-time SGML series/class metadata plus local schedule-heading context.
- Prefer exact filing-time series names.
- Reject ties and near-ties rather than forcing assignment.
- Fixed semantic anchors must show known holdings attached to the intended series.

PASS: all fixed semantic anchors pass and no known cross-series contamination remains in retained records.

## Gate C — security identity coverage

Automatic identities:
- Tier A: unique conservative issuer-name match to exactly one N-PX `(ticker, securityId)` identity.
- Tier B: only when no Tier A exists; unique issuer match to exactly one structurally valid 2–5 character ticker and securityId is absent.
- Fuzzy matches remain diagnostic-only.
- Ambiguous ADR/share-class/security identities are unresolved.
- Parser/header tokens and one-character ticker-only evidence are rejected.

PASS before historical universe construction:
- aggregate Tier A+B eligible-weight coverage >= **85%**
- median retained-series Tier A+B weight coverage >= **85%**
- semantic schedule audit has zero failures
- no fuzzy/header-token identity is promoted automatically

Current corrected 2006 pilot: aggregate Tier A+B eligible-weight coverage **91.37%**.

## Gate D — legacy proxy for N-PORT US/CORP/EC

Use explicit structure only:
- ADR/GDR/depositary receipt -> `NON_US_PROXY`
- debt/preferred/options/warrants/rights -> `NON_EC_PROXY`
- LP/limited partnership/LLC -> `NON_CORP_PROXY`
- accepted identity with no explicit exclusion -> `LEGACY_EQUITY_CANDIDATE`

Do not infer domicile from issuer spelling, ticker, price availability or performance.

## Gate E — ETF structural eligibility

Mirror Production economics:
- frozen Production-style series-name exclusions
- 10 <= holdings <= 120
- total positive normalized weight >= 50
- top-10 weight >= 25

Do not loosen thresholds merely to force more historical coverage.

## Gate F — universe scoring parity

Legacy scoring is frozen to Production:

`3*log1p(etfCount) + 0.5*log1p(aggregateWeight) + 0.5*log1p(recencyWeight)`

with:
- latest public filing per series
- `recencyFactor = exp(-ageDays / 120)`
- security eligibility `etfCount >= 2 OR maxWeight >= 4`
- sort score desc, ETF count desc, aggregate weight desc, ticker asc
- Top80, or fewer when fewer securities qualify

No future constituents may be backfilled.

## Gate G — direct 2020 reproducibility

The source of truth is `scripts/research-legacy-universe-reproducibility-2020.py`.

### G1 — shared-series fidelity

Hold the SEC series set fixed and compare legacy N-CSR/N-CSRS reconstruction with nearest same-series N-PORT holdings.

PASS requires:
- paired series >= **10**
- median legacy symbol-weight coverage >= **80%**
- Top80 overlap >= **80%**
- common-Top80 rank correlation >= **0.80**
- N-PORT Top2 retention >= **90%**

### G2 — missing-series impact

Compare full N-PORT against N-PORT restricted to series structurally reconstructable by the legacy pipeline. Both sides use N-PORT holdings, isolating series-coverage loss.

PASS requires:
- Top80 overlap >= **80%**
- common-Top80 rank correlation >= **0.80**
- N-PORT Top2 retention >= **90%**

Only G1 + G2 PASS permits the legacy bridge to be described as structurally equivalent to the Production universe.

Current status: **not yet evaluated successfully**. Fast run `33660812007` failed before metrics because GitHub runner access to SEC `master.idx` returned HTTP 403. This is a transport failure, not a fidelity failure. Validation must move to a deterministic frozen 2020 fixture.

## Gate H — historical data staging

Structural/data-quality diagnostics may use all 2006–2018 filing data.

Strategy performance opens sequentially under `legacy-history-evaluation-protocol.md`:
1. DEVELOPMENT 2006–2010
2. VALIDATION 2011–2014
3. SEALED_HOLDOUT 2015–2018

Default code permits DEVELOPMENT only. Later phases require explicit environment gates in `scripts/research-legacy-history-periods.py`.

Performance from a later phase may not be inspected to repair or select earlier reconstruction rules.

## Gate I — documentation freshness

`docs/research/momentum-handoff-current.md` is the canonical current state. Material changes to research scripts, research workflows, research validation docs, assumptions, conclusions or next actions must update the canonical handoff in the same change set whenever possible.

A dedicated freshness CI check must flag material research changes that leave the canonical handoff unchanged.