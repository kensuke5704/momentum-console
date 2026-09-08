# Momentum Research Handoff — Current

Last updated: 2026-09-08 JST  
Branch: `research/strict-series-source-h2-2006-20260908`  
Repository: `kensuke5704/momentum-console`

This is the canonical handoff for the historical-Universe reconstruction.

## 1. Hard constraints

- Production Stage21 remains frozen. Do not modify `main` or Production while historical validation continues.
- Production identifier: `momentum-stage21-sbi-2026-09-v1`; True Forward start: 2026-09-02.
- Do not use Stage21 returns, ranks, CAGR, MaxDD, Calmar, trades, or strategy outcomes to choose/tune source discovery, parsing, identity, country, eligibility, or reconstruction rules.
- Broad 2006–2018 Stage21 performance is still prohibited until a separate post-builder validation is explicitly defined and passed.
- Historical reconstruction must remain point-in-time. Country filing evidence must satisfy `evidenceDateFiled <= signal date`.
- No fuzzy/edit-distance ticker repair, current-country backfill, or future Series/Class backfill.
- UNKNOWN country is not imputed US in the primary reconstruction.

## 2. Production Universe semantics frozen for history

Order matters:
1. ingest public filing holdings;
2. retain `COMMON_EQUITY` analogue, conservative PIT `US`, `CORP` bridge, positive weight, usable symbol;
3. use latest public filing per source Series;
4. source eligibility only after holding filtering:
   - source-name exclusions;
   - 10–120 retained holdings;
   - retained total weight >= 50;
   - retained top-10 weight >= 25;
5. aggregate across eligible source Series;
6. retain `etfCount >= 2 || maxWeight >= 4`;
7. score `3*log1p(etfCount)+0.5*log1p(aggregateWeight)+0.5*log1p(recencyWeight)`;
8. Top80.

Production source-name exclusions remain frozen and must not be relaxed during historical extension.

## 3. Gate A — PASS

Production mechanics shadow parity over the first 12 Production months:
- median TopK overlap 93.75%
- minimum 92.5%
- median Spearman 0.9996
- Top2 individual retention 100%
- both Top2 retained 100%.

## 4. Gate B — PASS

Formal checkpoint: `docs/research/gate-b-pass-2026-09-07.md`.

Gate B uses the same practical thresholds as Gate A:
- median overlap >= 0.80
- minimum monthly overlap >= 0.70
- median Spearman >= 0.75
- Top2 individual retention >= 0.80
- both Top2 retained in >= 0.70 of evaluated months.

The obsolete early hybrid “4/6” criterion is non-authoritative and must not be reused.

### Direct transition source fidelity
- LRGE: 92.9% constituent / 95.9% weight
- GFIN: 94.2% / 97.4%
- PPTY: 93.9% / 98.0%
- 2020-01 aggregate: 8/9 common, Spearman 0.842, Top2 2/2.

### Authoritative H1 2006 source lineage
- pre-Series-ID source artifact: `9972690542`
- post-Series-ID source artifact: `9963958301`
- post-ID v3 exact run lineage: run `33948054540`
- hybrid catalog SHA256: `e2405277fe03a4208e163a43d724fd7364e139ad229caa70251b151f1d53b801`
- legacy positive identities 192
- post-ID positive Series 198
- exact same-CIK + exact-normalized-name unique bridges 111
- ambiguous bridges 0
- monthly source counts Jan–Jun: 192 / 204 / 267 / 270 / 273 / 279.

Bridge rule is frozen: same CIK + exact normalized Series/Fund name + uniqueness on both sides. No ticker inference, fuzzy rename, holdings/rank/return/outcome inference, or trust-global sibling binding.

### Raw holdings
Run `34089965073`, artifact `10006530879`:
- unique source filings 50
- fetch success 50/50
- unique parsed holdings **17,353**
- explicit `COMMON_EQUITY` 11,339
- missing parsed Series 0 each month.

### Structural mapping
Run `34090287022`, artifact `10006580498`.

Allowed primary mapping only:
- exact normalized issuer
- unique ADR-base identity
- accepted trailing share-class/jurisdiction/footnote cleanup followed by exact match
- unique long prefix >=20 only when candidate identity union is exactly one.

Raw mapping uncertainty remains visible; ambiguity is nonzero. Monthly mapped COMMON_EQUITY weight rates are approximately 65.01%, 69.21%, 79.10%, 79.10%, 76.59%, 74.83%.

Do not repeat older incorrect 93–95% raw mapping-weight coverage claims.

### Country
Strict PIT country run `34104858455`, artifact `10012280475`.

Rules:
- explicit historical country section where present
- alphabetic CINS / explicit ADR-GDR-ADS-depositary-receipt => NON_US
- frozen historical SEC filing-time state/country only when `evidenceDateFiled <= signal date`
- current ticker metadata may seed CIK only
- current state/country is never historical evidence
- unresolved => UNKNOWN in primary.

Canonical Actions-run country UNKNOWN-as-US upper-bound sensitivity:
- median overlap 0.8855357143
- minimum 0.8695652174
- median Spearman 0.9564368674
- Top2 individual retention 0.9166666667
- both Top2 monthly retention 0.8333333333
- PASS.

A locally downloaded copy was once observed with slightly different month/aggregate values. Do not mix that stale/local state with the accepted checkpoint; if metrics are externally reported, prefer the committed Gate B checkpoint and Actions run, or redownload the artifact fresh.

### CORP bridge
- transition EC+US cohort: 226/226 CORP
- old 2006 COMMON_EQUITY materiality sample: zero explicit non-CORP-name hits
- authoritative hybrid COMMON_EQUITY materiality audit: zero explicit non-CORP-name hits.

This is structural/materiality evidence; do not silently redefine every historical equity as CORP outside the frozen bridge.

### Mapping residual extreme sensitivity
Run `34125899895`, artifact `10020057970`.

Deliberately pessimistic assignment-free test: every unresolved positive COMMON_EQUITY row is assumed US/CORP for eligibility and each exact-normalized unresolved issuer group is treated as an entirely new anonymous security competing in Top80.

Both raw-normalized-exact and accepted-cleaned-exact variants:
- median TopK overlap 0.825
- minimum 0.7258064516
- median Spearman 0.9523245110
- Top2 individual retention 1.0
- both Top2 monthly retention 1.0
- PASS.

Therefore: **Gate B = PASS. Universe reconstruction is confirmed at the structural/source-fidelity gate level.**

## 5. Frozen historical Universe builder core — implemented and exact parity passed

Files:
- `scripts/research-historical-universe-builder.py`
- `.github/workflows/research-historical-universe-builder-parity-h1-2006.yml`

Parity run `34126348051`: SUCCESS.  
Artifact `10020226749`: `historical-universe-builder-parity-h1-2006`.

The builder consumes already-resolved historical filing snapshots only. It does not discover sources, repair identities, resolve country, use fuzzy mapping, or inspect strategy outcomes.

H1-2006 parity requirement was exact, not threshold-based:
- 6/6 signal months
- exact signal month / as-of alignment
- exact eligible source Series count
- exact full primary Universe rows including rank, score, and symbol-level metrics.

All comparisons passed. The downstream historical Universe builder core is therefore frozen against the accepted H1 Gate B output.

## 6. 2006 H2 strict post-ID source catalog — COMPLETE / VALIDATED

The H2 source-catalog extension is now closed. The H1 strict Series-source implementation was preserved and extended by period only, with one explicit recall-preservation rule at the **candidate prefilter** layer.

### 6.1 Exact lineage and upstream extension

H1 authoritative post-ID generator lineage was identified as:
- workflow: `.github/workflows/research-sec-id-era-strict-series-source-h1-2006-v3.yml`
- shard: `scripts/research-sec-id-era-strict-series-source-shard-h1-2006-v3.py`
- merge: `scripts/research-sec-id-era-strict-series-source-merge-h1-2006.py`
- run `33948054540`
- artifact `9963958301`.

The H1 upstream artifacts were confirmed to stop at `2006-06-30`, so strict Series-source alone could not be extended safely. H2 therefore rebuilt the upstream chain cumulatively through the final 2006 signal date.

Cumulative market-wide N-Q inventory:
- run `34139849908`
- artifact `10025455602`
- 6,564 filings
- 2,879 registrants.

Cumulative complete-portfolio inventory:
- run `34139895747`
- artifact `10025472099`
- 13,610 filings
- 2,928 registrants.

The cumulative complete-portfolio inventory restricted to `<= 2006-06-30` was checked against H1 artifact `9963841667`: **6,966 / 6,966 rows exact match**.

### 6.2 Operational prefilter recall preservation

The H1 operational prefilter is a candidate screen only; it is not final ETF evidence. A naive through-H2 rerun produced 74 current positive candidate registrants but dropped 5 registrants that had already been PIT-valid candidates in H1 because the prefilter selects newer prospectus evidence as time advances.

That recall loss was rejected. The H2 merge now carries forward the authoritative H1 positive candidate CIKs and unions them with newly positive H2 candidates. Final strict Series acceptance is **not** inherited from the carry-forward set and remains independently revalidated using issuer-own evidence and Series-level structural binding.

H2 prefilter shard run:
- run `34140039496`
- 12/12 shards SUCCESS.

Superseded naive merge:
- run `34140530406`
- artifact `10025705554`
- 74 current positive candidate registrants
- do not use as the authoritative H2 prefilter input.

Authoritative recall-preserved merge:
- run `34178898113`
- artifact `10038188212`
- 74 current positives + 5 H1 carry-forward = **79 candidate registrants**
- all H1 47 candidate registrants retained.

Five carry-forward CIKs:
- `0000751200`
- `0000802716`
- `0000813900`
- `0000822977`
- `0001100663`.

This does **not** weaken final Series acceptance. Broad prefilter evidence remains candidate discovery only.

### 6.3 Authoritative H2 strict Series-source result

Run `34178968784`: SUCCESS.  
Artifact `10038284691`: `sec-id-era-strict-series-source-h2-2006-v3`.

Fixed input artifacts:
- cumulative complete-portfolio: `10025472099`
- recall-preserved operational prefilter: `10038188212`.

Result:
- candidate registrants: **79**
- positive Series: **251**
- source occurrences: **836**
- identity conflicts: **0**
- prospectus errors: **0**
- source errors: **0**
- source-no-schedule count: **0**.

Binding counts:
- `EXPLICIT_ETF_CLASS_METADATA`: 28
- `REGISTRANT_EXPLICIT_ETF_SEMANTIC`: 45
- `SERIES_TITLE_EXPLICIT_ETF_SEMANTIC`: 177
- `SINGLE_SERIES_FILING_WITH_ISSUER_OWN_EVIDENCE`: 1.

Source-form counts:
- `N-CSR`: 179
- `N-CSR/A`: 23
- `N-CSRS`: 147
- `N-Q`: 451
- `N-Q/A`: 36.

Strict post-ID Jul–Dec source-Series counts:
- 2006-07: **199**
- 2006-08: **221**
- 2006-09: **242**
- 2006-10: **242**
- 2006-11: **245**
- 2006-12: **251**.

Signal dates are fixed at:
- 2006-07-31
- 2006-08-31
- 2006-09-29
- 2006-10-31
- 2006-11-30
- 2006-12-29.

### 6.4 H2 period-extension validation — PASS

Validation run `34179259819`: SUCCESS.  
Artifact `10038307519`: `sec-id-era-strict-series-source-h2-2006-validation`.

`passed = true`.

Checks passed:
- H2 Series identity conflicts = 0
- H2 prospectus errors = 0
- H2 source errors = 0
- exact Jul–Dec signal-month schedule
- nondecreasing Jul–Dec source counts
- all H1 198 positive Series retained
- H1 Series identity + binding exact
- H1 Feb–Jun snapshots reproduced **exactly at sourceFilings level** from the cumulative H2 catalog
- newly accepted Vanguard Series do not come from trust-global sibling leakage.

The H1 strict post-ID source counts reproduced from the cumulative H2 catalog are exactly:
- Feb 20
- Mar 172
- Apr 183
- May 192
- Jun 198.

New Vanguard Series IDs observed in the H2 extension:
- `S000014011`
- `S000015871`.

Both are accepted through explicit ETF class metadata; the validation found no conventional Vanguard sibling false positive.

Therefore the **2006 H2 source catalog is validated and may now feed the frozen holdings parser**.

## 7. Historical boundary and source rules that remain frozen

- Series/Class IDs became usable around 2006-02-06; do not require/backfill them into earlier PIT snapshots.
- Pre-ID identity uses contemporaneously public document title/class evidence only.
- Post-ID identity may use contemporaneously public Series/Class metadata plus strict issuer-own operational ETF evidence.
- Complete holdings in the legacy era include `N-Q`, `N-Q/A`, `N-CSR`, `N-CSR/A`, `N-CSRS`, `N-CSRS/A`; later transition forms may also matter.
- An amendment replaces a holdings source only if the amendment itself contains a complete portfolio schedule.
- Broad Creation-Unit/exchange language is candidate prefilter only. Final ETF evidence must describe the issuer's own Fund/Portfolio/Shares.
- Candidate-prefilter positives are recall-oriented and may be carried forward once already PIT-valid; **final strict Series acceptance must always be independently re-established and cannot be inherited from the prefilter**.
- Do not restore trust-global sibling binding; it produced conventional Vanguard sibling false positives.
- Source-name exclusions must match Production.
- Source eligibility is evaluated only after COMMON_EQUITY -> US -> CORP filtering.
- For H2 2006 PIT country work, historical SEC evidence may use only filings available by each signal date; do not use 2007 evidence.

## 8. Rejected paths — do not revive

- known-registry 20-Series sample as proof of global completeness
- Daily SEC HTTP Range pilot `33878671009` as a successful route
- N-Q-only complete-portfolio history
- trust/registrant name as Series identity
- trust-global ETF operational evidence for all sibling Series
- future Series/Class metadata in pre-2006-02-06 snapshots
- fuzzy/edit-distance issuer mapping
- numeric CUSIP => US
- missing country => US in primary
- absence of ADR/GDR => US
- current company state/country as PIT evidence
- strategy performance/ranks as reconstruction tuning signals
- treating the superseded 74-candidate H2 prefilter artifact `10025705554` as authoritative
- weakening final strict Series binding to compensate for prefilter recall issues.

## 9. Current status

Completed and closed:
- Gate A
- transition fidelity
- authoritative H1-2006 market-wide source catalog
- H1 raw holdings extraction
- H1 deterministic structural mapping
- H1 strict PIT country
- CORP materiality bridge
- H1 source eligibility / breadth reconstruction
- country and mapping residual sensitivities
- Gate B PASS
- frozen historical Universe builder core with exact H1 parity
- **2006 H2 cumulative upstream source inventories**
- **2006 H2 recall-preserved operational prefilter**
- **2006 H2 strict Series-source catalog**
- **H2 strict source period-extension validation PASS**.

Not yet completed:
- H2 holdings extraction
- H2 structural mapping
- H2 strict PIT country
- H2 builder output / downstream period-extension validation
- any broad 2006–2018 Stage21 performance.

## 10. Active next task — H2 holdings extraction

This is the current resumption point.

1. Identify/reuse the exact frozen holdings-parser lineage that produced H1 authoritative hybrid holdings run `34089965073`, artifact `10006530879`.
2. Do **not** modify source discovery or strict Series acceptance. Use the validated H2 source catalog artifact `10038284691` as the authoritative post-ID source input for Jul–Dec.
3. Preserve the H1 complete-portfolio parsing semantics exactly:
   - same schedule/document selection
   - same amendment handling
   - same row parsing and security-type classification
   - no mapping/country/ticker repair inside the holdings parser
   - no ranks/returns/strategy outcomes.
4. Generate H2 raw holdings for all Jul–Dec snapshot source filings and audit:
   - unique source filings
   - fetch success/failure
   - parsed holdings count
   - explicit `COMMON_EQUITY` count
   - missing parsed Series by month
   - duplicate/source replacement behavior.
5. Require H1 parser invariance where the same historical source filing is encountered. If an H1-era filing parses differently under the H2 execution environment, stop and audit rather than silently accepting drift.
6. Only after H2 raw holdings validation, extend the frozen structural mapping rules.
7. Then extend strict PIT country using evidence available by each Jul–Dec signal date only; no 2007 evidence.
8. Feed the resolved H2 snapshots into `scripts/research-historical-universe-builder.py` without changing builder semantics.
9. Define/pass downstream period-extension validation before any broad 2006–2018 Stage21 performance.

Do not invent a new “Gate C” label unless it is explicitly defined and committed first.

## 11. Key artifacts / runs

H1 / frozen baseline:
- frozen N-PX master: `9876020712`
- repaired pre-ID: run `33977286028`, artifact `9972690542`
- post-ID v3: run `33948054540`, artifact `9963958301`
- authoritative hybrid holdings: run `34089965073`, artifact `10006530879`
- structural mapping: run `34090287022`, artifact `10006580498`
- strict PIT country / H1 Gate B: run `34104858455`, artifact `10012280475`
- mapping extreme sensitivity: run `34125899895`, artifact `10020057970`
- historical builder H1 exact parity: run `34126348051`, artifact `10020226749`.

H2 source extension:
- cumulative N-Q inventory: run `34139849908`, artifact `10025455602`
- cumulative complete-portfolio inventory: run `34139895747`, artifact `10025472099`
- operational prefilter shards: run `34140039496`
- superseded naive prefilter merge: run `34140530406`, artifact `10025705554`
- authoritative recall-preserved prefilter merge: run `34178898113`, artifact `10038188212`
- strict Series-source H2 v3: run `34178968784`, artifact `10038284691`
- H2 source period-extension validation: run `34179259819`, artifact `10038307519`.

## 12. Relevant commits

H1 / baseline:
- strict PIT country / Gate B pipeline: `c11a6064086ba26c1b785d0ac882070f6d473dc3`, `f49494f720366676d401f1173fae2fb5e2212088`
- mapping sensitivity implementation: `aee7e5b68e8526901856fc542ee68456aac8ded1`, `2463b1e10b75a5a49fbd4a8b811415e9532d9127`, `e86107604256d37388b76b4f03e71eebd871319a`
- Gate B formal PASS checkpoint: `84a75335ee82b0941f1d7a01a3393e962b6e6cdd`
- frozen historical builder core: `e51c38ac8925672bb300185937a8739f3ee33ac2`
- H1 exact-parity workflow: `30b5d55111dc4d19a27228d6e3e9fc05577c0891`
- prior canonical handoff refresh: `6d40ed089add9550a89818f666cdf9a08954400b`.

H2 source extension branch commits:
- `a6978bdcb042aeed852e348242296893af97cd9b`
- `bdf37bf6148a3345f69cfed07e3525c8972ac71e`
- `2fd75344c931f0cc8643c73609049402c60d855e`
- `1abf37dab975c0b58ccfbddcd0d4f22f810e754a`
- `7892dcc15b29a350fc4e7a894c8e20adccf57760`
- `10fd01ff0e7b9c7d1493f58dc5709a51eff45f61`
- `f6cf0d0058ef3d8a3d0870336e06736eb8b262c1`
- `11ed7549cb62a844e602f0edf10ef72467a02bf4`
- `9f645589a1c664e295d3b9d2f8ffd922597520f0`
- `76c950afa4f151ac7d8257573e848bccb9ff0765`.

Production/main remains frozen throughout this work.
