# Legacy Universe Gate B checkpoint — 2026-09-04

Structural/data-quality validation only. No Stage21 returns, CAGR, MaxDD, Calmar, historical trades, or 2006–2018 strategy outcomes were used.

## Hard gate

Do not implement the historical Universe builder and do not run broad 2006–2018 Stage21 performance until historical Universe reproducibility is confirmed.

## Confirmed components

### Gate A

Production adapter/scoring parity remains PASS on the first 12 Production months of 2020:
- median Top-K overlap 93.75%
- minimum overlap 92.5%
- median Spearman 0.9996
- Production Top2 retention 100%

### Transition source fidelity

For the three series that actually generated the 2020-01 Production Universe:
- ClearBridge/LRGE: 92.9% count / 95.9% weight
- Goldman GFIN: 94.2% / 97.4%
- PPTY: 93.9% / 98.0%

All source gaps are <=184 days.

### Transition aggregate shadow

2020-01 legacy-source reconstruction versus Production:
- Top-K overlap 8/9 = 88.9%
- Spearman 0.842
- Production Top2 retained 2/2

This is strong direct transition evidence, but by itself did not prove independent source-series discovery.

### CORP transition audit

Individual raw N-PORT filings for LRGE, GFIN and PPTY were inspected. Among holdings satisfying EC+US:
- LRGE 42/42 CORP
- GFIN 69/69 CORP
- PPTY 115/115 CORP
- aggregate 226/226 = 100%

Thus CORP is redundant after EC+US in this transition sample.

### 2006 independent source-series discovery

SEC filing index pages expose historical Series/Class/Ticker metadata even though the complete-submission SGML route did not.

Filing-index discovery artifact: `9925317298`.
Formal coverage run: `33873358078`.
Formal coverage artifact: `9936820544`.

Result:
- corrected 2006 PIT series: 20
- filing-index discovered series: 49
- matched corrected PIT series: 20/20
- source-series coverage: **100%**
- missing series: none

The discovery uses filing metadata only; holdings names, Production ranks and returns are not used to select the 20 series.

### 2006 structural security mapping

Original EC-filtered baseline:
- count 69.95%
- weight 78.98%

Deterministic structural additions only (share-class display cleanup and unique long-prefix identity; no fuzzy/edit-distance auto-acceptance):
- count **73.90%**
- weight **82.49%**
- +37 holdings / +70.36 weight

### 2006 country coverage before new filing-index route

UNKNOWN-only historical SEC retries added 53 resolved identities.
Merged country artifact: `9902743513`.

On the original mapped population:
- mapped resolved count 59.17%
- mapped resolved weight 62.68%
- all-EC resolved count 42.95%
- all-EC resolved weight 50.97%

Country attribution of the new structural mapping identities resolved 7 US + 2 NON_US identities, 27.53 additional weight. Approximate all-EC resolved weight after those additions is ~52.35%.

### Conservative-US eligibility sensitivity

Run: `33873875011`.
Artifact: `9937026635`.

Using only already confirmed-US holdings and excluding every UNKNOWN:
- 9/20 series = 45% remain eligible under Production-style 10–120 holdings / total>=50 / top10>=25.

This is sensitivity evidence only and is not the final historical Universe rule. It shows that country UNKNOWN remains material and cannot simply be ignored at the current coverage level.

## Rejected country routes

- current ticker as country evidence: prohibited
- numeric CUSIP => US: prohibited
- absence of ADR/GDR => US: prohibited
- generic N-Q country heading => issuer domicile: prohibited
- ticker-seed + historical COMPANY CONFORMED NAME validation pilot: 0/50 resolved
- derived complete-submission `.txt` pilot: 0/30 resolved
- SEC full-index master.zip on GitHub runner: transport failure; not semantic evidence

## Active country route

Historical SEC filing **index pages** expose `State of Incorp.` metadata. This is preferable to primary-document SGML because the index retains filing metadata that can be absent from rendered filing documents.

Country evidence rule being tested:
1. Current ticker metadata may only seed a CIK when ticker + normalized issuer title match uniquely.
2. Country classification must come from a historical SEC filing index page.
3. Use filing-index `State of Incorp.` as the evidence.
4. UNKNOWN remains UNKNOWN if the historical index cannot be resolved.
5. No current incorporation state may be used as country evidence.

### PIT cutoff correction preregistered before results

For an external issuer-country source, the correct information cutoff is the legacy **fund filingDate**, not the earlier holdings reportDate. The fund holdings are not public until filingDate; issuer SEC metadata already public by that date is therefore available to a point-in-time Universe constructor and is not look-ahead.

For identities appearing in multiple contributing ETF series, use the earliest contributing fund filingDate as the country-evidence cutoff.

Active runs:
- reportDate filing-index pilot: `33873160913`
- filingDate filing-index pilot: `33873667126`
- 10-K-restricted fast equivalent: `33873798848`

## Remaining blocker

Source discovery, EC, CORP-transition evidence, transition parser fidelity, transition aggregate parity and 2006 series discovery are now strong. The main unresolved Gate B blocker is scalable historical issuer-country coverage in 2006.

Do not declare Universe reconstruction confirmed until that blocker is sufficiently closed and the final conservative aggregate ranking/Top2 validation is frozen.
