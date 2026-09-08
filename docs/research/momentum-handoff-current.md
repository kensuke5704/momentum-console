# Momentum Research Handoff — Current

Last updated: 2026-09-09 JST  
Branch: `research/strict-series-source-h1-2008-20260908`  
Repository: `kensuke5704/momentum-console`

This is the canonical handoff for the historical-Universe reconstruction.

## 1. Current status

Historical Universe reconstruction is **closed through 2007-12**. The active extension is **H1 2008 (2008-01 through 2008-06)**.

Closed authoritative state:

- H2 2007: CLOSED / PASS
- 24-month stitch run: `34193003030`
- 24-month stitch artifact: `10042873354`
- artifact name: `historical-universe-builder-through-h2-2007`
- artifact digest: `sha256:a8d1955fd406121e214af7dec4cf69058895573e0ad055b2e8a54d4101103f87`
- exact coverage: `2006-01` through `2007-12`
- Universe size: 62 for `2006-01`, 80 for each of the remaining 23 months

Active work:

- branch: `research/strict-series-source-h1-2008-20260908`
- H1-2008 status: STARTED / NOT CLOSED
- no authoritative H1-2008 source, downstream-parity, or 30-month stitch artifact exists yet

## 2. Hard constraints

- Production Stage21 remains frozen. Do not modify `main` or Production while historical validation continues.
- Production identifier: `momentum-stage21-sbi-2026-09-v1`; True Forward start: 2026-09-02.
- Do not use Stage21 returns, ranks, CAGR, MaxDD, Calmar, trades, portfolio outcomes, or strategy outcomes to tune historical source/parsing/identity/mapping/country/eligibility rules.
- Broad 2006–2018 Stage21 performance remains prohibited until a separate post-builder validation is explicitly preregistered and passed.
- Historical reconstruction must remain PIT. Country filing evidence must satisfy `evidenceDateFiled <= signal date`.
- No fuzzy/edit-distance ticker repair, current-country backfill, future Series/Class backfill, or future issuer-variant backfill.
- UNKNOWN country remains UNKNOWN in primary.
- Do not invent a new gate such as “Gate C” unless its definition is committed before relevant results are observed.

## 3. Frozen Production historical-Universe semantics

Order is fixed:

1. ingest public filing holdings;
2. retain `COMMON_EQUITY` analogue, conservative PIT `US`, `CORP` bridge, positive weight, usable symbol;
3. latest public filing per source Series;
4. source eligibility after holding filtering:
   - frozen Production source-name exclusions;
   - 10–120 retained holdings;
   - retained total weight >= 50;
   - retained top-10 weight >= 25;
5. aggregate eligible source Series;
6. retain `etfCount >= 2 || maxWeight >= 4`;
7. score `3*log1p(etfCount)+0.5*log1p(aggregateWeight)+0.5*log1p(recencyWeight)`;
8. Top80.

## 4. Frozen baseline lineage

### Gate A — PASS

Production-mechanics shadow parity passed the pre-defined overlap/rank/Top2 thresholds.

### Gate B — PASS

Formal checkpoint:

- `docs/research/gate-b-pass-2026-09-07.md`

Authoritative H1 2006 lineage:

- raw holdings run `34089965073`, artifact `10006530879`
- structural mapping run `34090287022`, artifact `10006580498`
- strict PIT country run `34104858455`, artifact `10012280475`
- N-PX master artifact `9876020712`
- static country evidence artifacts `9944538015` and `9944797581`
- frozen historical builder run `34126348051`, artifact `10020226749`
- frozen builder script `scripts/research-historical-universe-builder.py`
- frozen builder blob `1357402f34dfea1c1dbdcaac7de5078b680eb5c3`

Frozen H1 country implementation:

- `scripts/research-nq-hybrid-pit-country-gate-b-h1-2006.py`
- blob `7b830b0e851b0d5349a5c6049e8889f171b791e0`

Frozen H1 holdings/parser blobs:

- `scripts/research-nq-pit-holdings-hybrid-h1-2006.py` = `e391aa5175d1c06dced0ee45ce45eb26b6362690`
- `scripts/research-nq-series-segmentation-2006.py` = `47a2ac4fe713f9f43171aa2b38a7707c386c009e`
- `scripts/research-nq-pit-holdings-2006-corrected.py` = `866e328e8237afb49855499e88e49e5d9d2fa914`
- `scripts/research-nq-per-holding-ec-2006.py` = `79d2fc427efd67f784c98d2d6d9519aea99c3927`
- `scripts/research-sec-complete-portfolio-title-diagnostic-h2-2005.py` = `7006a968a32994772ecaa373aeebe750c8b493bc`

Frozen mapping blobs:

- `scripts/research-nq-catalog-structural-mapping-h1-2006.py` = `690479017fc82dce2480ded5d1ffafbb76721722`
- `scripts/research-nq-npx-mapping-2006.py` = `972c1e8ebf2c829abb3b8b400dffa613c368e100`
- `scripts/research-nq-npx-structural-mapping-2006.py` = `d79b077887cf11784b8620220929fa936a822601`

Frozen N-PX parser/normalizer:

- `scripts/research-npx-security-master-2006.py` = `bc2d44dda6bfae00ebba22a81ba867a18bbd7ba5`
- `scripts/research-npx-security-master-build-2006.py` = `ad977557eb7f48fc0c0d71a2c369b0d61f6c1239`

## 5. 2006 H2 — CLOSED / PASS

- source run `34178968784`, artifact `10038284691`
- source validation run `34179259819`, artifact `10038307519`, PASS
- holdings run `34179821383`, artifact `10038557328`
- parser invariance run `34181393477`, artifact `10039022796`, PASS
- mapping run `34180122700`, artifact `10038597826`
- country run `34181593177`, artifact `10039353878`, PASS
- downstream exact parity run `34183463904`, artifact `10039694610`, PASS
- 2006 stitch run `34183543393`, artifact `10039721939`, PASS

## 6. 2007 H1 — CLOSED / PASS

### Upstream

- cumulative N-Q inventory run `34183793920`, artifact `10039805856`
- cumulative complete-portfolio inventory run `34183826632`, artifact `10039815625`
- recall-preserved prefilter shard run `34183876207`
- prefilter merge run `34184039449`, artifact `10039881783`

Source validation definition:

- `docs/research/h1-2007-source-period-extension-validation-definition.md`

Strict Series source:

- run `34184083615`
- artifact `10040000632`
- source SHA256 `fcf8bd62ff1182f2d8a9dc99c2f6fd30bcf3b3a2974d04786d1a943f1c9fa21b`
- candidate registrants 122
- positive Series 433
- source occurrences 1,719
- conflicts/prospectus errors/source errors = 0/0/0
- `sourceNoSchedule = 1`, audit-only
- Jan–Jun source counts = 303 / 303 / 417 / 417 / 432 / 433
- prior H2 2006 Series identity/binding retained exactly
- Jul–Dec 2006 source snapshots replayed exactly

### Downstream

Definition:

- `docs/research/h1-2007-downstream-period-extension-validation-definition.md`

- holdings run `34184472191`, artifact `10040053724`
- parser invariance run `34184619228`, artifact `10040069230`, PASS
- structural mapping run `34184639119`, artifact `10040076231`
- strict PIT country run `34184751511`, artifact `10040374627`, PASS
- downstream exact parity run `34186786093`, artifact `10040774126`, PASS
- eligible source counts = 22 / 23 / 20 / 20 / 19 / 18
- Universe size = 80 for all six months
- 18-month stitch run `34186850426`, artifact `10040792563`, PASS

## 7. 2007 H2 — CLOSED / PASS

### 7.1 Closed-history candidate-discovery correction

Later candidate discovery initially introduced 14 old HealthShares Series from CIK `0001352853` into already closed H1 2007. The correction was preregistered before the corrected result:

- `docs/research/h2-2007-closed-history-candidate-discovery-boundary-correction.md`

Authoritative corrected source:

- run `34188233028`
- artifact `10041257985`
- source SHA256 `9ffed81a42044f7388221a60450a24967ea61f108eb63f66464699ada1849631`
- Jul–Dec source counts = 465 / 469 / 499 / 518 / 531 / 533
- closed Jan–Jun 2007 replay exact

Key implementation:

- `scripts/research-sec-id-era-strict-series-source-merge-h2-2007-v4.py`
- `.github/workflows/research-sec-id-era-strict-series-source-h2-2007-v4.yml`

Frozen boundary behavior:

- closed replay uses only the candidate-review CIK set that was PIT-discovered and authoritative for the prior closed period
- newly discovered CIKs contribute only in the open extension period
- final issuer-own evidence, Series binding, complete-portfolio, and no-lookahead semantics are unchanged

### 7.2 Holdings/parser

- holdings run `34188353154`, artifact `10041300366`, PASS
- 72/72 source filings fetched
- 0 errors
- 10,375 parsed holdings
- 10,057 COMMON_EQUITY
- missing parsed Series 0

Parser audit correction:

- `docs/research/h2-2007-parser-invariance-audit-set-correction.md`

Corrected parser invariance:

- run `34188697692`
- artifact `10041408799`
- expected/actual overlap = 258 / 258
- exact matches = 258
- semantic mismatch = 0
- PASS

### 7.3 PIT N-PX

Definition:

- `docs/research/h2-2007-npx-pit-master-validation-definition.md`

Frozen rules include:

- pre-2007 master artifact `9876020712` as base
- official SEC 2007 N-PX inventory
- primary N-PX only for admissions; N-PX/A audit-only
- `dateFiled <= signal date`
- earliest primary filing per CIK
- fixed 64-position equal-quantile CIK sample
- fixed broad-family CIKs `35348,826473,68138,745463,752737,81247,916403,814232,1039949,202385,1026708`
- monotone admissions
- frozen parser/normalizer
- no target names, mapping, country, or outcomes used

Transport-only corrections:

- `docs/research/h2-2007-npx-pit-master-transport-correction.md`
- `docs/research/h2-2007-npx-filing-transport-correction.md`

Authoritative N-PX:

- run `34190105652`
- artifact `10041975282`
- 205/205 fixed selected source fetches succeeded
- errors 0
- PIT violations 0
- PASS

### 7.4 Structural mapping

Definition:

- `docs/research/h2-2007-structural-mapping-validation-definition.md`

Authoritative mapping:

- run `34190421577`
- artifact `10042002365`
- PASS

Allowed mapping methods only:

- `BASELINE_EXACT`
- `BASELINE_ADR_BASE_UNIQUE`
- `STRUCTURAL_SUFFIX_EXACT`
- `UNIQUE_LONG_PREFIX`

No fuzzy mapping.

### 7.5 Strict PIT country

Definition:

- `docs/research/h2-2007-country-pit-issuer-variant-validation-definition.md`

Frozen H2 issuer-variant behavior:

- pre-2007 base variants are eligible throughout H2
- a 2007 N-PX issuer variant is eligible only if both `sourceFilingDate <= signal date` and `admittedAtSignal <= signal date`
- future issuer variants are blocked backward
- UNKNOWN and CORP semantics remain unchanged
- SEC master years exactly `[2005, 2006, 2007]`

Authoritative country:

- run `34190587649`
- artifact `10042478228`
- all 8 shards + merge PASS
- country evidence no-lookahead PASS
- issuer-variant PIT PASS
- UNKNOWN preserved
- CORP invariant PASS

### 7.6 Downstream frozen-builder exact parity

Definition:

- `docs/research/h2-2007-downstream-period-extension-validation-definition.md`

Validator:

- `scripts/research-h2-2007-downstream-period-extension-validation.py`
- blob `72ae7532458d35e09b4b98bf221fbd566970aa07`

Workflow:

- `.github/workflows/research-h2-2007-downstream-period-extension-validation.yml`

Initial run `34192565485` failed before builder execution because of artifact-download transport only. No Universe/parity result was observed. Correction:

- `docs/research/h2-2007-downstream-artifact-download-transport-correction.md`

Authoritative corrected result:

- run `34192853738`
- artifact `10042811090`
- digest `sha256:e64b49362048418d6e7d3aff9a47d0ee5d9055ddd8a9292072bfd68f0240bccd`
- PASS, exact parity 6/6 months
- eligible source counts Jul–Dec = 17 / 19 / 21 / 21 / 34 / 32
- Universe size = 80 each month
- country no-lookahead PASS
- CORP invariant PASS
- no Stage21 outcome was read

### 7.7 Validated 24-month stitch

Definition:

- `docs/research/h2-2007-24-month-stitch-validation-definition.md`

Implementation:

- `scripts/research-historical-universe-stitch-through-h2-2007.py`
- blob `5d6c98817919277454bdf9dea76281aae6c378c0`

Workflow:

- `.github/workflows/research-historical-universe-stitch-through-h2-2007.yml`

Authoritative result:

- run `34193003030`
- artifact `10042873354`
- artifact name `historical-universe-builder-through-h2-2007`
- digest `sha256:a8d1955fd406121e214af7dec4cf69058895573e0ad055b2e8a54d4101103f87`
- PASS

The stitch preserves artifact `10040792563` exactly as the first 18 closed months and appends only the six validated H2 builder snapshots from artifact `10042811090`. No reconstruction step is rerun.

Eligible source counts over the 24 months:

`10,19,26,26,29,28,18,23,23,23,23,22,22,23,20,20,19,18,17,19,21,21,34,32`

## 8. Historical boundary/source rules that remain frozen

- Series/Class IDs became usable around 2006-02-06; do not require/backfill them before they were public.
- Pre-ID identity uses contemporaneously public document title/class evidence only.
- Post-ID identity may use contemporaneously public Series/Class metadata plus strict issuer-own operational ETF evidence.
- Legacy complete holdings include `N-Q`, `N-Q/A`, `N-CSR`, `N-CSR/A`, `N-CSRS`, `N-CSRS/A` where complete portfolio schedules are present.
- An amendment replaces a holdings source only if the amendment itself contains a complete portfolio schedule.
- Broad Creation-Unit/exchange language is candidate-prefilter evidence only. Final ETF evidence must describe the issuer's own Fund/Portfolio/Shares.
- Candidate positives may be carried forward for recall only; final strict Series acceptance must be independently re-established.
- Closed-history candidate discovery cannot retroactively admit newly discovered CIKs into an already closed prior period. Newly discovered candidates begin contributing only in the open extension period unless the closed-history protocol is explicitly reopened before results.
- Do not restore trust-global sibling binding.
- Source eligibility is evaluated only after COMMON_EQUITY -> US -> CORP filtering.
- For every extension, country evidence and N-PX issuer variants may use only information public by that month’s signal date.

## 9. Rejected paths — do not revive

- known-registry small samples as proof of global completeness
- Daily SEC HTTP Range pilot as a successful route
- N-Q-only complete-portfolio history
- trust/registrant name as Series identity
- fuzzy/edit-distance ticker repair
- current country/state as historical country evidence
- future Series/Class metadata backfill
- UNKNOWN -> US imputation in primary
- Stage21 performance-driven tuning of historical reconstruction

## 10. H1 2008 — active extension

Status: **STARTED / NOT YET CLOSED**.

No authoritative H1-2008 source, downstream parity, or stitch artifact exists yet.

Current branch:

- `research/strict-series-source-h1-2008-20260908`

Confirmed reusable H2-2007 upstream/source files:

- `scripts/research-sec-marketwide-nq-inventory-through-h2-2007.py`
- `.github/workflows/research-sec-marketwide-nq-inventory-through-h2-2007.yml`
- `.github/workflows/research-sec-etf-registrant-operational-prefilter-through-h2-2007.yml`
- `scripts/research-sec-id-era-strict-series-source-merge-h2-2007-v4.py`
- `.github/workflows/research-sec-id-era-strict-series-source-h2-2007-v4.yml`

Confirmed strict-source V4 workflow inputs:

- fixed H2 strict-source shard run `34187436415`
- authoritative H1 source artifact `10040000632`
- authoritative H1 candidate-review artifact `10039881783`

Confirmed authoritative H2 upstream references for H1-2008 extension:

- cumulative H2 N-Q inventory artifact `10040860433`
- cumulative H2 complete-portfolio inventory artifact `10040863522`
- H2 prefilter shard run `34187156944`
- H2 corrected source run `34188233028`
- H2 corrected source artifact `10041257985`

The H1-2008 source validation definition is **not yet committed**. It must be committed before strict-source results are observed.

## 11. H1 2008 required execution sequence

Proceed without changing semantic rules.

### A. Upstream extension

1. fetch the exact H2-2007 implementations/workflows for:
   - cumulative N-Q inventory
   - cumulative complete-portfolio inventory
   - recall-preserved registrant prefilter shards and merge
   - strict Series source shard generation/merge
2. extend only the period/time boundary through 2008 Q2 and the final H1-2008 signal date
3. derive Jan–Jun 2008 signal dates using the existing month-end business-day code path; do not manually invent dates
4. require exact replay of authoritative closed inventory/history through 2007-12 before consuming new 2008 rows

### B. Candidate boundary

5. rerun cumulative candidate discovery through H1 2008
6. preserve the authoritative closed 2006–2007 candidate/source lineage for every closed replay snapshot
7. permit CIKs first discovered during H1 2008 to contribute only from 2008-01 through 2008-06
8. require zero retroactive admission into any 2006 or 2007 source snapshot

### C. Preregister source validation

9. create and commit `docs/research/h1-2008-source-period-extension-validation-definition.md`
10. this definition must be committed **before strict-source result inspection**

### D. Strict source

11. run the frozen strict Series-source procedure over the cumulative H1-2008 candidate set
12. require exact replay of closed identity/binding and source snapshots
13. require no retroactive admission from new H1-2008 candidates
14. if validation fails, preregister the minimal correction before consuming corrected results

### E. Downstream

After source PASS, continue in this fixed order:

15. holdings using the frozen parser
16. parser invariance
17. PIT N-PX master selected independently per signal date
18. frozen structural mapping
19. strict PIT country
20. predefined downstream exact frozen-builder parity
21. mechanical stitch onto closed artifact `10042873354`

Expected successful H1-2008 closed state:

- 30 exact months
- `2006-01` through `2008-06`

## 12. Half-year standardization

Starting with H1 2008, prefer a parameter-driven half-year extension template so H2 2008 through H2 2018 become mechanical and less error-prone.

The template may parameterize only period metadata such as:

- period label
- open-period start/end
- SEC master-index quarter endpoint
- authoritative prior closed artifact/run references
- prior candidate-review artifact
- expected closed replay range
- output artifact names

It must **not** parameterize or alter research semantics such as:

- source eligibility
- candidate evidence acceptance
- Series identity/binding rules
- holdings parser semantics
- mapping methods
- country rules
- Universe thresholds/scoring

Any template refactor must demonstrate exact replay of already closed history before becoming authoritative.

## 13. Long-range target

Continue the same half-year closure protocol through **2018-12**.

Reaching 2018-12 does not itself authorize Stage21 historical performance analysis. After the full historical Universe is closed:

1. separately preregister a post-builder validation;
2. run it without using Stage21 outcomes to alter the historical builder;
3. require PASS;
4. only then run/analyze broad historical Stage21 performance.

## 14. Immediate resume point

Resume on:

- `research/strict-series-source-h1-2008-20260908`

Immediate execution tasks:

1. finish locating/fetching the H2-2007 complete-portfolio and prefilter shard/merge implementations;
2. build H1-2008 cumulative N-Q / complete-portfolio / prefilter extensions with exact closed-prefix replay;
3. commit `docs/research/h1-2008-source-period-extension-validation-definition.md` before strict-source result inspection;
4. execute H1-2008 strict source;
5. after PASS, continue holdings -> parser invariance -> PIT N-PX -> mapping -> PIT country -> exact builder parity -> mechanical 30-month stitch.

Do not stop at status-only reporting when execution tooling is available. Report meaningful checkpoints while continuing the work.
