# Momentum Research Handoff — Current

Last updated: 2026-09-06 JST  
Branch: `research/nq-npx-mapping-2006-20260903`  
Repository: `kensuke5704/momentum-console`

This is the canonical handoff for continuing the historical-Universe reconstruction in a new chat.

## 1. Hard constraints

Do **not** implement the broad historical/legacy Universe builder yet.

Do **not** run broad 2006–2018 Stage21 performance yet.

Do **not** use returns, ranks, CAGR, MaxDD, Calmar, trades, or strategy outcomes to choose or tune source-discovery, parsing, identity, country, eligibility, or reconstruction rules.

Production Stage21 is frozen:
- identifier: `momentum-stage21-sbi-2026-09-v1`
- True Forward start: 2026-09-02
- do not modify Production while this source-fidelity gate is open.

Only after the historical Universe is reproduced with sufficient structural fidelity may the bridge be frozen and the historical builder implemented.

## 2. Production Universe semantics to reproduce

Relevant code:
- `src/lib/universe/universe.ts`
- `src/lib/universe/sec-nport.ts`
- `src/lib/universe/nport-quarterly.ts`
- `scripts/build-universe.ts`

Production order matters:
1. ingest filing holdings;
2. retain holdings satisfying `ASSET_CAT=EC`, `INVESTMENT_COUNTRY=US`, `ISSUER_TYPE=CORP`, positive weight, usable symbol;
3. select latest public filing per source Series;
4. apply source-ETF eligibility **after that holding filtering**:
   - source-name exclusions;
   - holdings count 10–120;
   - retained total weight >= 50;
   - retained top-10 weight >= 25;
5. aggregate securities across eligible sources;
6. keep `etfCount >= 2 || maxWeight >= 4`;
7. score `3*log1p(etfCount) + 0.5*log1p(aggregateWeight) + 0.5*log1p(recencyWeight)`;
8. Top80.

Historical reconstruction must preserve this ordering. In particular, do not apply source eligibility to raw legacy holdings before COMMON_EQUITY + conservative country filtering.

## 3. Stable evidence already accepted

### Gate A — PASS

Production mechanics reproduce the first 12 Production Universe months strongly:
- median Top-K overlap: 93.75%
- minimum overlap: 92.5%
- median Spearman: 0.9996
- Production Top2 individual retention: 100%
- both Top2 retained: 100%.

Gate A validates mechanics, not legacy source completeness.

### Transition source fidelity — strong

Nearest complete legacy holdings to first Production reports:
- LRGE: 92.9% count / 95.9% weight
- GFIN: 94.2% / 97.4%
- PPTY: 93.9% / 98.0%.

2020-01 three-source aggregate shadow:
- 8/9 Production names
- Spearman 0.842
- Production Top2 2/2.

### CORP bridge

In the transition cohort, every holding already satisfying EC+US was CORP:
- LRGE 42/42
- GFIN 69/69
- PPTY 115/115
- combined 226/226.

This is strong transition evidence but is **not** a universal 2006 CORP rule. Do not silently generalize it.

## 4. Corrected old 2006 PIT sample — structural sample only

Active EC-filtered artifact: `9878189715`, run `33715016882`.

Old corrected sample:
- 20 source Series
- 936 explicit `COMMON_EQUITY` holdings.

Known 20 include Select Sector SPDR, Rydex XLG and streetTRACKS Series such as DGT/RWR/KBE/KCE/KIE/MTK/OOO/XBI/XHB/XSD.

Critical caveat: `scripts/research-nq-pit-holdings-2006.py` originally used a hardcoded registrant regex and selected known registrants. Therefore this 20-Series set is useful for schedule parsing, mapping, country and structural validation, but it is **not** evidence of a globally complete PIT ETF source population.

## 5. Legacy COMMON_EQUITY and deterministic N-PX mapping

Accepted legacy EC rule: only explicit `COMMON_EQUITY` section attribution passes.

Old 936-EC sample mapping against frozen N-PX master artifact `9876020712`:
- baseline: 654/936 = 69.95% count / 78.98% weight
- deterministic structural: 691/936 = 73.90% / 82.49%.

Allowed deterministic mapping rules only:
- baseline exact normalized issuer;
- unique ADR-base identity;
- accepted trailing share-class/jurisdiction/footnote cleanup;
- unique long prefix >=20 chars only when the union of candidate identities is exactly one.

Do **not** add fuzzy/edit-distance auto-matching to improve coverage.

## 6. Historical country bridge

Final conservative old-sample country merge:
- run `33893804443`
- artifact `9944902929`
- denominator 936 EC holdings
- US 641 / NON_US 33 / UNKNOWN 262
- all-EC resolved 72.01% count / 80.85% weight
- among 691 deterministic mapped holdings, country resolved 658/691 = 95.22%
- mapped-holding resolved weight 96.14%
- conflicts 0.

Accepted hierarchy:
1. alphabetic CINS prefix => NON_US;
2. explicit ADR/GDR => NON_US;
3. deterministic historical issuer identity -> historical SEC filing-time `COMPANY DATA` / `STATE OF INCORPORATION` evidence;
4. UNKNOWN remains UNKNOWN.

Never infer US from listing venue, numeric CUSIP, absence of ADR/GDR, or current-company country defaults.

Country is no longer the primary blocker **inside deterministically mapped identities**.

## 7. SEC market-wide source discovery corrections

### Daily Range pilot was a failure

Run `33878671009` must **not** be described as a successful daily-index transport route.

Artifact audit showed, for the tested dates, all 40 HTTP Range attempts failed and produced zero N-Q filings/CIKs. Any older wording saying this pilot succeeded is superseded.

### Official quarterly/H1 inventories succeeded

Q1 2006 official SEC inventory:
- run `33894478362`
- artifact `9945162305`
- 1,480 N-Q/N-Q-A filings
- 1,285 registrant CIKs.

H1 2006 N-Q inventory:
- run `33897359772`
- artifact `9946255797`
- 3,293 N-Q/N-Q-A filings
- 2,816 CIKs.

Known Select Sector, Rydex and streetTRACKS filings appeared naturally in these inventories; they were not source-selection seeds.

## 8. Broad ETF-registrant prefilter and strict operational evidence

A broad preregistered condition of Creation Unit language + exchange language is useful only as a candidate prefilter. It is too permissive because conventional mutual-fund prospectuses often discuss investing in ETFs.

H1 broad prefilter:
- run `33897558123`
- 2,816 registrants examined
- 47 candidate registrants.

Known false-positive-style candidates included ordinary fund complexes where ETF language described portfolio investments rather than issuer-owned ETF Shares.

Strict issuer-own pilot:
- run `33897878473`
- artifact `9946455266`
- 7/7 classification controls correct.

Strict rule: Creation/exchange language must describe the filing issuer's own Fund/Portfolio/Shares, not investments in third-party ETFs.

## 9. 2006-02-06 Series/Class regime boundary

This is a critical historical boundary.

SEC Series/Class identifiers became required around **2006-02-06**. Therefore:
- pre-2006-02-06 portfolio filings cannot be required to expose Series IDs;
- do not backfill future Series IDs into January PIT snapshots;
- post-boundary identity can use SEC Series/Class metadata;
- pre-boundary identity must be bound from contemporaneously public document titles/classes only.

Earlier attempts that treated missing 2005 Series/Class metadata as a parser defect are superseded.

## 10. Complete-portfolio forms: N-Q alone is insufficient

For 2005/2006, complete portfolio holdings are not limited to N-Q. N-CSR/N-CSRS also matter.

2005 H2 complete-portfolio inventory:
- 6,968 filings
- 2,928 CIKs
- actual relevant form labels observed: `N-Q`, `N-Q/A`, `N-CSR`, `N-CSR/A`, `N-CSRS`, `N-CSRS/A`.

2006 H1 complete-portfolio inventory:
- 6,966 filings
- 2,869 CIKs.

Among the 47 broad ETF candidate CIKs:
- 2005 H2: 143 complete-portfolio filings / 45 CIKs
- 2006 H1: 139 complete-portfolio filings.

Schedule grammar validation across the 143 H2 candidate filings:
- 143/143 fetched
- after adding historical `Statement of Net Assets`, 142/143 qualified as complete-portfolio sources
- the remaining `N-CSR/A` amendment contained no schedule and therefore correctly does **not** replace the underlying holdings source.

Rule: an amendment updates the holdings source only if the amendment itself contains a complete-portfolio schedule.

## 11. Post-ID source catalog

The older 267-Series complete catalog was too trust-global and admitted conventional Vanguard sibling funds. It is superseded.

The tightened post-ID v3 catalog separates:
- issuer-own operational ETF evidence from a public prospectus; and
- Series/Class identity from contemporaneously public post-2006-02-06 SEC metadata.

Result:
- run `33948054540` was the v3 execution used during development;
- artifact used downstream: `9963958301`
- 198 positive Series
- 333 source occurrences
- identity conflicts 0
- fetch errors 0
- monthly Series snapshots: Feb 20 / Mar 172 / Apr 183 / May 192 / Jun 198.

Posthoc controls showed Select Sector 9 Series and Rydex identities were recovered while conventional Vanguard siblings were removed.

Do not revert to trust-global proximity binding.

## 12. Pre-ID source catalog — latest state

Pre-ID identity is the main area that changed most recently.

Rejected/superseded defects encountered:
- registrant/trust names such as `STREETTRACKS SERIES TRUST` and `Rydex ETF Trust` being treated as Series;
- `THE SELECT SECTOR SPDR TRUST` bypassing registrant-name exclusion because of the leading `THE`;
- mixed Vanguard trusts where local ETF/VIPER language could incorrectly bind conventional sibling funds.

Accepted identity hygiene:
- normalized Series candidate must not equal registrant/company name;
- registrant equivalence ignores a leading `THE`;
- no fuzzy name reconciliation;
- mixed trusts require direct Series/class association rather than trust-global operational evidence.

Latest successful direct per-CIK base:
- run `33977213400`
- conclusion: success
- 47 per-CIK shard artifacts + merged artifact
- merged artifact: **`9972683860`** (`sec-legacy-etf-series-source-preid-direct-2006`).

Latest mixed-Vanguard replacement:
- commit `6f480b4940dae6a0bd69cfa638593265afcd8775`
- run **`33977286028`**
- conclusion: success
- replacement artifact: **`9972690542`** (`sec-legacy-etf-series-source-preid-direct-replaced-2006`).

Workflow intentionally re-resolved only mixed-trust shards `[0,1,4,12]` and replaced those rows in the prior clean merged base.

This **`9972690542` artifact is the current pre-ID source artifact to inspect/use next**, not cancelled run `33950337808`.

Important correction about `33950337808`:
- its latest attempt ended `cancelled`;
- only 45 artifacts were present in that attempt;
- it is superseded by the direct per-CIK + mixed-trust replacement runs above.

## 13. Hybrid source -> holdings status

Hybrid rules already implemented conceptually/code-wise:
- pre-ID and post-ID bridge only on same CIK + exact normalized Series name + uniqueness on both sides;
- no ticker guessing, fuzzy rename inference or outcome-based repair;
- unmatched pre-ID identities remain distinct;
- post-ID source replaces legacy source only when it is public and explicitly linked.

Raw holdings design:
- use the hybrid catalog as the **only** source selector;
- do not rediscover/add sources inside the holdings extractor;
- post-ID rows bind schedules by Series ID;
- pre-ID rows bind by exact normalized filing-time title/legacy identity;
- ambiguous or missing schedule binding stays missing and is audited;
- preserve raw holdings first;
- annotate explicit `COMMON_EQUITY`/other legacy sections;
- do not apply source eligibility until after COMMON_EQUITY + conservative US filtering.

Previous chained workflow run `33950735883` failed and must not be treated as a completed holdings result. It predated the latest direct/replacement pre-ID artifact.

**Next execution should start from artifact `9972690542` + post-ID artifact `9963958301` and regenerate the hybrid catalog, then raw holdings.**

## 14. Existing downstream code prepared

Relevant research scripts/workflows added during this work include versions for:
- complete H1/H2 portfolio inventories;
- broad ETF operational prefilter;
- strict Series source catalogs;
- pre-ID direct per-CIK resolver;
- mixed-Vanguard replacement merge;
- hybrid pre-ID/post-ID merge;
- hybrid holdings extraction;
- catalog structural mapping.

The structural mapping stage should use frozen N-PX master artifact `9876020712` and the already accepted deterministic rules only.

For country, reuse the accepted historical resolver hierarchy from the old 936-holding sample; do not invent new defaults.

## 15. Current gate status

### Strong / passed
- Gate A mechanics
- transition source fidelity
- transition CORP evidence
- corrected schedule parsing / COMMON_EQUITY attribution
- deterministic N-PX mapping semantics
- country evidence on deterministically mapped identities
- market-wide official complete-portfolio inventory construction
- strict issuer-own operational evidence
- post-ID Series/Class source identification
- pre-ID identity grammar and direct mixed-trust repair have successful source artifacts.

### Still not passed
- regenerate one authoritative hybrid Jan–Jun 2006 source catalog from `9972690542` + `9963958301`;
- parse raw holdings from that hybrid source population;
- measure COMMON_EQUITY parse coverage and schedule-binding misses;
- run deterministic N-PX mapping on the new full source population;
- reuse conservative country attribution on the newly mapped identities;
- apply Production-order source eligibility after COMMON_EQUITY + US filtering;
- aggregate monthly securities and quantify residual mapping/UNKNOWN sensitivity;
- only then assess Gate B reproduction of the aggregate Universe.

Therefore **`Universe reconstruction is confirmed` must NOT yet be stated**.

## 16. Exact next actions for a new chat

Proceed without re-opening earlier source-selection debates unless new evidence contradicts the frozen rules:

1. Download/inspect pre-ID artifact `9972690542` from run `33977286028`.
2. Confirm mixed Vanguard conventional siblings and registrant/trust-name identities are absent.
3. Merge it with post-ID artifact `9963958301` using same-CIK + exact-normalized-name unique bridge only.
4. Produce Jan–Jun monthly hybrid PIT source snapshots and record bridge/unmatched counts.
5. Run hybrid raw holdings extractor using the hybrid catalog as the sole source selector.
6. Audit fetch errors, exact schedule bindings, unresolved/ambiguous schedules, holdings counts and legacy section attribution.
7. Keep only explicit `COMMON_EQUITY` for the EC analogue.
8. Run existing deterministic structural mapping using frozen N-PX master `9876020712`.
9. Reuse conservative historical country evidence; leave unresolved identities UNKNOWN.
10. Apply source eligibility only after COMMON_EQUITY + conservative US filtering: name exclusions, 10–120 holdings, total weight >=50, top10 >=25.
11. Aggregate monthly with `etfCount >=2 || maxWeight >=4`, Production breadth score, Top80.
12. Quantify sensitivity to unresolved mapping/country rows without changing rules from Universe ranks or returns.
13. If structural reproduction is sufficient, explicitly record Gate B PASS and only then say `Universe reconstruction is confirmed`.
14. Only after that implement the historical builder. Still do not immediately run broad 2006–2018 Stage21 performance.

## 17. Rejected paths — do not revive

- known-registry seeded 20-Series sample as proof of global source completeness
- old nine-Series continuation-page token assignment
- Daily SEC HTTP Range pilot `33878671009` as a successful transport result
- broad `Creation Unit + exchange anywhere` as final ETF classification
- fund/trust name containing ETF as sufficient classification
- trust-global operational evidence binding every sibling Series
- future Series/Class metadata backfilled into pre-2006-02-06 PIT months
- N-Q-only complete-portfolio history
- amendment automatically supersedes source when it contains no portfolio schedule
- 13F as direct Production Universe substitute
- fuzzy/edit-distance issuer matching
- automatic country missing => US
- numeric CUSIP => US
- absence of ADR/GDR => US
- current company country/state as PIT country evidence
- strategy returns/ranks as reconstruction tuning signals.

## 18. Key artifacts / runs

- corrected old 2006 PIT: run `33714482859`
- EC-filtered old PIT: run `33715016882`, artifact `9878189715`
- frozen N-PX master: artifact `9876020712`
- final old-sample country merge: run `33893804443`, artifact `9944902929`
- Q1 official N-Q inventory: run `33894478362`, artifact `9945162305`
- H1 official N-Q inventory: run `33897359772`, artifact `9946255797`
- broad H1 ETF candidate prefilter: run `33897558123`
- strict issuer-own evidence pilot: run `33897878473`, artifact `9946455266`
- post-ID v3 source artifact: `9963958301`
- successful pre-ID direct base: run `33977213400`, artifact `9972683860`
- latest mixed-trust repaired pre-ID: run `33977286028`, artifact **`9972690542`**
- failed/superseded old hybrid holdings chain: run `33950735883`.
