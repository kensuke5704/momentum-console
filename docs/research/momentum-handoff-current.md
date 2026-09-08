# Momentum Research Handoff — Current

Last updated: 2026-09-08 JST  
Branch: `research/strict-series-source-h2-2007-20260908`  
Repository: `kensuke5704/momentum-console`

This is the canonical handoff for the historical-Universe reconstruction.

## 1. Hard constraints

- Production Stage21 remains frozen. Do not modify `main` or Production while historical validation continues.
- Production identifier: `momentum-stage21-sbi-2026-09-v1`; True Forward start: 2026-09-02.
- Do not use Stage21 returns, ranks, CAGR, MaxDD, Calmar, trades, portfolio outcomes, or strategy outcomes to tune historical source/parsing/identity/mapping/country/eligibility rules.
- Broad 2006–2018 Stage21 performance remains prohibited until a separate post-builder validation is explicitly defined and passed.
- Historical reconstruction must remain PIT. Country filing evidence must satisfy `evidenceDateFiled <= signal date`.
- No fuzzy/edit-distance ticker repair, current-country backfill, or future Series/Class backfill.
- UNKNOWN country remains UNKNOWN in primary.
- Do not invent a new gate (for example “Gate C”) unless its definition is committed before results are observed.

## 2. Frozen Production historical-Universe semantics

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

## 3. Closed validation gates

### Gate A — PASS
Production-mechanics shadow parity over the first 12 Production months passed the pre-defined overlap/rank/Top2 thresholds.

### Gate B — PASS
Formal checkpoint: `docs/research/gate-b-pass-2026-09-07.md`.

Important authoritative H1 2006 lineage:
- raw holdings run `34089965073`, artifact `10006530879`
- structural mapping run `34090287022`, artifact `10006580498`
- strict PIT country run `34104858455`, artifact `10012280475`
- N-PX master artifact `9876020712`
- static country evidence artifacts `9944538015` and `9944797581`
- frozen historical builder run `34126348051`, artifact `10020226749`
- frozen builder blob `1357402f34dfea1c1dbdcaac7de5078b680eb5c3`.

Frozen H1 country implementation blob:
- `scripts/research-nq-hybrid-pit-country-gate-b-h1-2006.py`
- blob `7b830b0e851b0d5349a5c6049e8889f171b791e0`.

Frozen H1 holdings/parser blobs:
- `research-nq-pit-holdings-hybrid-h1-2006.py` = `e391aa5175d1c06dced0ee45ce45eb26b6362690`
- `research-nq-series-segmentation-2006.py` = `47a2ac4fe713f9f43171aa2b38a7707c386c009e`
- `research-nq-pit-holdings-2006-corrected.py` = `866e328e8237afb49855499e88e49e5d9d2fa914`
- `research-nq-per-holding-ec-2006.py` = `79d2fc427efd67f784c98d2d6d9519aea99c3927`
- `research-sec-complete-portfolio-title-diagnostic-h2-2005.py` = `7006a968a32994772ecaa373aeebe750c8b493bc`.

Frozen mapping blobs:
- `research-nq-catalog-structural-mapping-h1-2006.py` = `690479017fc82dce2480ded5d1ffafbb76721722`
- `research-nq-npx-mapping-2006.py` = `972c1e8ebf2c829abb3b8b400dffa613c368e100`
- `research-nq-npx-structural-mapping-2006.py` = `d79b077887cf11784b8620220929fa936a822601`.

## 4. 2006 H2 — CLOSED / PASS

Strict Series source:
- run `34178968784`
- artifact `10038284691`
- 251 positive Series, 836 source occurrences
- conflicts/errors/no-schedule = 0/0/0
- Jul–Dec source counts = 199 / 221 / 242 / 242 / 245 / 251.

Source period-extension validation:
- run `34179259819`
- artifact `10038307519`
- PASS.

Holdings:
- run `34179821383`
- artifact `10038557328`.

Parser invariance vs H1:
- run `34181393477`
- artifact `10039022796`
- 120 overlapping filings, semantic mismatch 0, PASS.

Mapping:
- run `34180122700`
- artifact `10038597826`.

Country:
- run `34181593177`
- artifact `10039353878`
- strict PIT/no-lookahead PASS.

Downstream exact parity:
- run `34183463904`
- artifact `10039694610`
- 6/6 exact frozen-builder parity, PASS.

2006 full-year stitch:
- run `34183543393`
- artifact `10039721939` (`historical-universe-builder-2006`)
- Jan–Dec exact validated concatenation, PASS.

## 5. 2007 H1 — CLOSED / PASS

### 5.1 Upstream source extension

Cumulative N-Q inventory:
- run `34183793920`
- artifact `10039805856`
- exact 2006 replay: 6,564 rows / 2,879 registrants.

Cumulative complete-portfolio inventory:
- run `34183826632`
- artifact `10039815625`
- exact 2006 replay: 13,610 rows / 2,928 registrants.

Recall-preserved candidate prefilter:
- shard run `34183876207` (12/12 SUCCESS)
- merge run `34184039449`
- artifact `10039881783`
- all prior 79 H2 candidates retained at candidate layer only.

Source validation definition was committed before results:
- `docs/research/h1-2007-source-period-extension-validation-definition.md`.

Strict Series source:
- run `34184083615`
- artifact `10040000632`
- source catalog SHA256 `fcf8bd62ff1182f2d8a9dc99c2f6fd30bcf3b3a2974d04786d1a943f1c9fa21b`
- candidate registrants 122
- positive Series 433
- source occurrences 1,719
- conflicts/prospectus errors/source errors = 0/0/0
- audit-only `sourceNoSchedule = 1`, not admitted to source occurrences
- Jan–Jun source counts = 303 / 303 / 417 / 417 / 432 / 433
- prior H2 2006 251 Series identity/binding retained exactly
- Jul–Dec 2006 source snapshots replayed exactly.

### 5.2 Downstream extension

Downstream validation definition was committed before downstream results:
- `docs/research/h1-2007-downstream-period-extension-validation-definition.md`.

Holdings wrapper:
- run `34184472191`
- artifact `10040053724`
- 56/56 unique source filings fetched
- 13,867 unique parsed holdings
- COMMON_EQUITY 12,417
- missing parsed Series 0.

Parser invariance H2 2006 -> H1 2007:
- run `34184619228`
- artifact `10040069230`
- 154 overlapping source filings
- exact full record matches 154
- semantic mismatch 0
- PASS.

Structural mapping:
- run `34184639119`
- artifact `10040076231`
- frozen 2006 N-PX master retained because it is the latest annual proxy-voting master available before all H1 2007 signal dates.

Strict PIT country:
- run `34184751511`
- artifact `10040374627`
- all 8 shards + merge SUCCESS
- UNKNOWN preserved and CORP materiality invariant preserved
- no-lookahead PASS.

Downstream frozen-builder exact-parity validation:
- run `34186786093`
- artifact `10040774126`
- PASS, exact parity 6/6 months
- eligibleSourceSeriesCount = 22 / 23 / 20 / 20 / 19 / 18
- Universe size = 80 / 80 / 80 / 80 / 80 / 80
- no Stage21 strategy outcome was read.

Validated historical-Universe stitch through H1 2007:
- run `34186850426`
- artifact `10040792563` (`historical-universe-builder-through-h1-2007`)
- 18 exact months `2006-01` through `2007-06`, PASS.

## 6. 2007 H2 — CLOSED / PASS

### 6.1 Source extension

Authoritative corrected strict-Series source:
- run `34188233028`
- artifact `10041257985`
- source SHA256 `9ffed81a42044f7388221a60450a24967ea61f108eb63f66464699ada1849631`
- Jul–Dec source counts = 465 / 469 / 499 / 518 / 531 / 533
- closed Jan–Jun 2007 replay exact.

The closed-history candidate-discovery boundary correction was defined before the corrected result:
- `docs/research/h2-2007-closed-history-candidate-discovery-boundary-correction.md`.

### 6.2 Downstream extension

Downstream definition was committed before downstream results:
- `docs/research/h2-2007-downstream-period-extension-validation-definition.md`.

Holdings:
- run `34188353154`
- artifact `10041300366`
- 72/72 source filings fetched, 0 errors
- 10,375 parsed holdings; 10,057 COMMON_EQUITY
- missing parsed Series = 0.

Parser invariance:
- authoritative corrected run `34188697692`
- artifact `10041408799`
- expected/actual overlap 258 / 258
- exact full-record matches 258
- semantic mismatch 0
- PASS.
- audit-set correction: `docs/research/h2-2007-parser-invariance-audit-set-correction.md`.

PIT N-PX master:
- validation definition `docs/research/h2-2007-npx-pit-master-validation-definition.md`
- authoritative run `34190105652`
- artifact `10041975282`
- 205/205 fixed selected source fetches succeeded
- fetch errors 0; PIT violations 0
- later annual identity data not leaked backward.
- transport-only corrections are documented in `docs/research/h2-2007-npx-pit-master-transport-correction.md` and `docs/research/h2-2007-npx-filing-transport-correction.md`.

Structural mapping:
- validation definition `docs/research/h2-2007-structural-mapping-validation-definition.md`
- run `34190421577`
- artifact `10042002365`
- only frozen mapping methods accepted; fuzzy mapping not used.

Strict PIT country:
- validation definition `docs/research/h2-2007-country-pit-issuer-variant-validation-definition.md`
- run `34190587649`
- artifact `10042478228`
- all 8 shards + merge PASS
- country evidence no-lookahead PASS
- H2 N-PX issuer variants are visible only when both source filing and admission are public by signal date
- master-index years exactly `[2005, 2006, 2007]`
- UNKNOWN preserved; CORP positive non-CORP-name count 0.

Downstream frozen-builder exact parity:
- validator `scripts/research-h2-2007-downstream-period-extension-validation.py`
- validator blob `72ae7532458d35e09b4b98bf221fbd566970aa07`
- initial run `34192565485` failed before builder execution because of artifact-download transport only; correction documented in `docs/research/h2-2007-downstream-artifact-download-transport-correction.md`
- authoritative corrected run `34192853738`
- artifact `10042811090`
- PASS, exact parity 6/6 months
- eligible source counts Jul–Dec = 17 / 19 / 21 / 21 / 34 / 32
- Universe size = 80 each month
- country no-lookahead PASS
- CORP invariant PASS
- no Stage21 outcome was read.

### 6.3 Validated historical-Universe stitch through H2 2007

Validation definition:
- `docs/research/h2-2007-24-month-stitch-validation-definition.md`.

Workflow:
- `.github/workflows/research-historical-universe-stitch-through-h2-2007.yml`.

Stitch implementation:
- `scripts/research-historical-universe-stitch-through-h2-2007.py`
- blob `5d6c98817919277454bdf9dea76281aae6c378c0`.

Authoritative result:
- run `34193003030`
- artifact `10042873354` (`historical-universe-builder-through-h2-2007`)
- artifact digest `sha256:a8d1955fd406121e214af7dec4cf69058895573e0ad055b2e8a54d4101103f87`
- PASS.

The stitch preserves artifact `10040792563` exactly as the closed first 18 months and appends only the six validated H2 builder snapshots from artifact `10042811090`. No reconstruction step is rerun.

Coverage:
- 24 exact signal months, `2006-01` through `2007-12`
- eligible source counts = 10 / 19 / 26 / 26 / 29 / 28 / 18 / 23 / 23 / 23 / 23 / 22 / 22 / 23 / 20 / 20 / 19 / 18 / 17 / 19 / 21 / 21 / 34 / 32
- Universe sizes = 62 for 2006-01 and 80 for each remaining month.

## 7. Historical boundary/source rules that remain frozen

- Series/Class IDs became usable around 2006-02-06; do not require/backfill them before they were public.
- Pre-ID identity uses contemporaneously public document title/class evidence only.
- Post-ID identity may use contemporaneously public Series/Class metadata plus strict issuer-own operational ETF evidence.
- Legacy complete holdings include `N-Q`, `N-Q/A`, `N-CSR`, `N-CSR/A`, `N-CSRS`, `N-CSRS/A` where complete portfolio schedules are present.
- An amendment replaces a holdings source only if the amendment itself contains a complete portfolio schedule.
- Broad Creation-Unit/exchange language is candidate-prefilter evidence only. Final ETF evidence must describe the issuer's own Fund/Portfolio/Shares.
- Candidate positives may be carried forward for recall only; final strict Series acceptance must be independently re-established.
- Closed-history candidate discovery cannot retroactively admit newly discovered CIKs into an already closed prior period; newly discovered candidates begin contributing only in the open extension period unless the closed-history protocol is explicitly reopened before results.
- Do not restore trust-global sibling binding.
- Source eligibility is evaluated only after COMMON_EQUITY -> US -> CORP filtering.
- For each period extension, country evidence and N-PX issuer variants can use only information public by that month’s signal date.

## 8. Rejected paths — do not revive

- known-registry small samples as proof of global completeness
- Daily SEC HTTP Range pilot as a successful route
- N-Q-only complete-portfolio history
- trust/registrant name as Series identity
- fuzzy/edit-distance ticker repair
- current country/state as historical country evidence
- future Series/Class metadata backfill
- UNKNOWN -> US imputation in primary
- Stage21 performance-driven tuning of historical reconstruction.

## 9. Next task

Proceed to **2008 H1 period extension (Jan–Jun 2008)** from the closed 24-month H2-2007 state.

Required sequence:
1. create a new research branch from the current validated H2-2007 head;
2. extend cumulative N-Q and complete-portfolio inventories through the final H1-2008 signal date and require exact replay of all closed 2006-01 through 2007-12 inventory/history boundaries before using new rows;
3. rerun the recall-preserved operational candidate prefilter cumulatively, with the closed-history candidate-discovery boundary retained;
4. commit the H1-2008 source-period extension validation definition before observing strict-Series-source results;
5. extend strict Series source with unchanged semantics and require exact closed 2007 source identity/binding and snapshot replay;
6. only after source PASS, run frozen holdings/parser, parser invariance, PIT N-PX selected independently per signal date, frozen structural mapping, strict PIT country, and pre-defined downstream exact parity;
7. mechanically stitch validated H1-2008 output onto artifact `10042873354` without recomputing the closed 24-month prefix;
8. continue the same half-year extension protocol toward the historical end date; do not run broad Stage21 performance until a separate post-builder validation is explicitly defined and passed.
