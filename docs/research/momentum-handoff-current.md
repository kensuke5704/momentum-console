# Momentum Research Handoff — Current

Last updated: 2026-09-07 JST  
Branch: `research/nq-npx-mapping-2006-20260903`  
Repository: `kensuke5704/momentum-console`

This is the canonical handoff for the historical-Universe reconstruction.

## 1. Hard constraints

- Production Stage21 remains frozen. Do not modify `main` or Production while historical validation continues.
- Production identifier: `momentum-stage21-sbi-2026-09-v1`; True Forward start: 2026-09-02.
- Do not use Stage21 returns, ranks, CAGR, MaxDD, Calmar, trades, or strategy outcomes to choose/tune source discovery, parsing, identity, country, eligibility, or reconstruction rules.
- Broad 2006–2018 Stage21 performance is still prohibited until a separate post-builder validation is explicitly defined and passed.
- Historical reconstruction must remain point-in-time. Country filing evidence must satisfy `evidenceDateFiled <= signal date`.
- No fuzzy/edit-distance ticker repair, current-country backfill, or future Series/Class backfill.

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

### Direct transition source fidelity
- LRGE: 92.9% constituent / 95.9% weight
- GFIN: 94.2% / 97.4%
- PPTY: 93.9% / 98.0%
- 2020-01 aggregate: 8/9 common, Spearman 0.842, Top2 2/2.

### Authoritative H1 2006 source lineage
- pre-Series-ID source artifact: `9972690542`
- post-Series-ID source artifact: `9963958301`
- hybrid catalog SHA256: `e2405277fe03a4208e163a43d724fd7364e139ad229caa70251b151f1d53b801`
- legacy positive identities 192
- post-ID positive Series 198
- exact same-CIK + exact-normalized-name unique bridges 111
- ambiguous bridges 0
- monthly source counts Jan–Jun: 192 / 204 / 267 / 270 / 273 / 279.

Bridge rule is frozen: same CIK + exact normalized Series/Fund name + uniqueness on both sides. No ticker/fuzzy/outcome inference.

### Raw holdings
Run `34089965073`, artifact `10006530879`:
- source filings 50
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

### Country
Strict PIT country run `34104858455`, artifact `10012280475`.

Rules:
- explicit historical country section where present
- alphabetic CINS / explicit ADR-GDR => NON_US
- historical SEC filing-time state/country only when `evidenceDateFiled <= signal date`
- current ticker metadata may seed CIK only
- current state/country is never historical evidence
- unresolved => UNKNOWN in primary.

Country UNKNOWN-as-US upper-bound sensitivity:
- median overlap 0.8855357143
- minimum 0.8695652174
- median Spearman 0.9564368674
- Top2 individual retention 0.9166666667
- both Top2 monthly retention 0.8333333333
- PASS.

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

## 5. Frozen historical Universe builder core — implemented and parity passed

Files:
- `scripts/research-historical-universe-builder.py`
- `.github/workflows/research-historical-universe-builder-parity-h1-2006.yml`

Parity run `34126348051`: SUCCESS.

The builder consumes already-resolved historical filing snapshots only. It does not discover sources, repair identities, resolve country, use fuzzy mapping, or inspect strategy outcomes.

H1-2006 parity requirement was exact, not threshold-based:
- 6/6 signal months
- exact eligible source Series count
- exact full primary Universe rows including rank and score.

All comparisons passed.

## 6. Historical boundary and source rules that remain frozen

- Series/Class IDs became usable around 2006-02-06; do not require/backfill them into earlier PIT snapshots.
- Pre-ID identity uses contemporaneously public document title/class evidence only.
- Post-ID identity may use contemporaneously public Series/Class metadata plus strict issuer-own operational ETF evidence.
- Complete holdings in the legacy era include `N-Q`, `N-Q/A`, `N-CSR`, `N-CSR/A`, `N-CSRS`, `N-CSRS/A`; later transition forms may also matter.
- An amendment replaces a holdings source only if the amendment itself contains a complete portfolio schedule.
- Broad Creation-Unit/exchange language is candidate prefilter only. Final ETF evidence must describe the issuer's own Fund/Portfolio/Shares.
- Do not restore trust-global sibling binding; it produced conventional Vanguard false positives.

## 7. Rejected paths — do not revive

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
- strategy performance/ranks as reconstruction tuning signals.

## 8. Current status / next work

Completed:
- Gate A
- transition fidelity
- authoritative H1-2006 market-wide source catalog
- raw holdings extraction
- deterministic mapping
- strict PIT country
- CORP materiality bridge
- source eligibility / breadth reconstruction
- country and mapping residual sensitivities
- Gate B PASS
- frozen historical builder core with exact H1 parity.

Current next step is **source-bridge period extension**, beginning with 2006 H2, while reusing the frozen builder and all frozen identity/country/eligibility rules. This is data-lineage expansion, not strategy optimization.

Do not run broad 2006–2018 Stage21 performance yet. Before that, define and pass a separate post-builder validation covering period-extension causality/completeness and implementation invariants.

## 9. Key artifacts / runs

- frozen N-PX master: `9876020712`
- repaired pre-ID: run `33977286028`, artifact `9972690542`
- post-ID v3: artifact `9963958301`
- authoritative hybrid holdings: run `34089965073`, artifact `10006530879`
- structural mapping: run `34090287022`, artifact `10006580498`
- strict PIT country / H1 Gate B: run `34104858455`, artifact `10012280475`
- mapping extreme sensitivity: run `34125899895`, artifact `10020057970`
- historical builder H1 exact parity: run `34126348051`.
