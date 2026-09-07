# Momentum Research Handoff — Current

Last updated: 2026-09-07 JST  
Branch: `research/momentum-v2-9-preid-fix-20260906`  
Repository: `kensuke5704/momentum-console`  
Branch head before this handoff refresh: `a76b00c93f07197d07781b0839b64cf2af1b41e4`

This is the canonical handoff for continuing the historical-Universe reconstruction in a new chat.

## 1. Current status in one paragraph

The H1 2006 historical ETF-Universe pipeline is structurally clean through source discovery, source/Series identity, complete-schedule parsing, explicit `COMMON_EQUITY`, deterministic N-PX mapping, Production-order ETF eligibility and Top80 construction. The authoritative source and holdings stages are PASS. The currently recorded Gate B decision is still **FAIL**, solely because conservative historical-country `UNKNOWN` sensitivity materially changes rank ordering in January and February 2006. Since that decision, additional point-in-time country evidence has been recovered. A complete eight-shard filing-detail evidence set now exists, but it is split across two workflow runs and has **not yet been merged and re-Gated successfully**. The immediate next task is therefore orchestration only: bind the final Gate workflow to those eight exact artifacts, merge them, rebuild the six monthly Universes, rerun the unchanged upper-bound sensitivity and Gate B v13, then record the actual PASS/FAIL.

`Universe reconstruction is confirmed` must **not** be stated yet.

## 2. Hard constraints

Do **not** modify Production Stage21 while Gate B is open.

Do **not** run broad 2006–2018 performance/backtests before Gate B PASS.

Do **not** use returns, ranks, CAGR, MaxDD, Calmar, trades or strategy outcomes to choose or tune source-discovery, parsing, identity, mapping, country, ETF eligibility or reconstruction rules.

Hard prohibitions:
- no future Series/Class IDs backfilled into pre-ID months;
- no fuzzy/edit-distance security matching;
- no ticker/name shortcuts to force mappings;
- no current-country defaults;
- no US default for unresolved country;
- no rank/outcome-selected country recovery rules;
- ambiguous mapping is excluded, never auto-assigned.

Production Stage21 remains frozen. `productionModified=false` and `stage21PerformanceConsulted=false` must remain true during this gate.

## 3. What is being reproduced

The target is not a modern list of companies projected backward. The goal is:

> For each historical month, reproduce the Top80 Universe that the current Production Universe generator would have produced using only information publicly available by that month.

Only after that Universe is structurally confirmed may the momentum strategy be applied historically.

Production-order semantics to preserve:
1. ingest filing holdings;
2. historical EC analogue = explicit `COMMON_EQUITY` only;
3. retain conservative US holdings only;
4. use the frozen transition CORP bridge only as explicitly documented;
5. select the latest public source filing per Series;
6. apply source-ETF eligibility **after** holding filtering:
   - source-name exclusions;
   - holdings count 10–120;
   - retained weight >= 50;
   - retained top-10 weight >= 25;
7. aggregate securities;
8. keep `etfCount >= 2 || maxWeight >= 4`;
9. apply Production breadth score;
10. Top80.

Do not apply ETF eligibility to raw holdings before COMMON_EQUITY + conservative country filtering.

## 4. Frozen accepted evidence

### Gate A — PASS

Production mechanics reproduction:
- median Top-K overlap: 93.75%
- minimum overlap: 92.5%
- median rank correlation: 0.9996
- Production Top2 individual retention: 100%
- both Top2 retained: 100%.

### Transition source fidelity

Nearest complete legacy holdings to first Production reports:
- LRGE: 92.9% count / 95.9% weight
- GFIN: 94.2% / 97.4%
- PPTY: 93.9% / 98.0%.

2020-01 aggregate shadow:
- 8/9 Production names
- rank correlation 0.842
- Top2 2/2.

### Explicit CORP bridge

Transition EC+US holdings were CORP:
- LRGE 42/42
- GFIN 69/69
- PPTY 115/115
- combined **226/226**.

This is a limited legacy semantic bridge, not permission to invent a general 2006 issuer-type classifier.

## 5. Authoritative lineage — use these inputs

| Stage | Status | Run | Artifact |
|---|---|---:|---:|
| Source v6 | PASS | `34024867963` | `9986725265` |
| Authoritative holdings v8 | PASS | `34025177693` | `9986815485` |
| Frozen N-PX master | frozen | — | `9876020712` |
| Mapping-only | PASS | — | `9987093683` |
| Original final Gate B execution | FAIL | `34027854106` | `9987700449` |

Do not revert to source v5 `9986077545`; source v6 supersedes it.

Do not use old failed holdings artifact `9984358291` as authority.

Do not use old country artifacts containing current-ticker fallback as final country authority.

## 6. Source v6 — PASS

Source v6 fixed the last source/holdings boundary mismatch: three iShares Series were registered in a 2006-06-08 N-CSR metadata set but did not actually have their portfolio schedules in that filing. Under the final grouping semantics they correctly fall back to the valid 2006-03-01 N-Q source.

Key state:
- post-ID qualified occurrences evaluated with the same final schedule grouping used downstream;
- exactly three stale occurrence choices removed;
- fetch errors 0;
- no identity/bridge conflict introduced.

Pre-ID/post-ID bridge remains strict:
- same CIK;
- exact normalized Series name;
- uniqueness on both sides;
- no fuzzy rename inference;
- no ticker guessing.

## 7. Authoritative holdings v8 — PASS

Run `34025177693`, artifact `9986815485`.

Structural audit:
- filings: **38/38 success**;
- catalog/output source keys: **1190/1190**;
- missing source keys: 0;
- extra source keys: 0;
- zero-holdings targets: 0;
- missing grouped schedules: 0;
- ambiguous source-marker assignment: 0;
- financial-statement text contamination: 0;
- temporal-label contamination: 0;
- summary-aggregate contamination: 0;
- unique parsed `COMMON_EQUITY` holdings: **147,854**.

The parser/source problem is no longer the Gate blocker.

## 8. Deterministic N-PX mapping

Frozen N-PX master: artifact `9876020712`.

Only these assigned methods are permitted:
- `BASELINE_EXACT`
- `BASELINE_ADR_BASE_UNIQUE`
- `STRUCTURAL_SUFFIX_EXACT`
- `UNIQUE_LONG_PREFIX`

Unexpected assigned method = conflict.

Ambiguous/unmapped rows may exist but must not receive a ticker/security ID automatically.

Mapping-only artifact used for the current Gate lineage: `9987093683`.

## 9. Correct Gate rank-correlation implementation

Do not revive the superseded closed-form Spearman calculation on original ranks with gaps.

For common symbols, use Pearson correlation of their original rank values (or equivalently rerank the common subset). The accepted implementation is conceptually:

```python
xs = [rank_a[s] for s in common]
ys = [rank_b[s] for s in common]
rho = corr(xs, ys)
```

The final Gate scripts were corrected accordingly.

## 10. Original Gate B decision — currently still authoritative

Decision file:
`docs/research/momentum-v2-9-gate-b-decision-h1-2006.md`

Original final Gate run: `34027854106`  
Artifact: `9987700449`

Decision: **Gate B FAIL**.

All structural checks passed; the sole conflict was:

`COUNTRY_UPPER_BOUND_MATERIAL`

Strict PIT country after explicit same-filing/CINS/depositary-receipt evidence:
- unresolved mapped identity/report-date queries entering historical resolution: 9,575
- US resolved: 6,216
- NON_US resolved: 33
- remaining UNKNOWN: **3,326**.

Primary vs UNKNOWN→US upper-bound sensitivity:

| Month | Top80 overlap | Rank correlation | Top2 retention |
|---|---:|---:|---:|
| 2006-01 | 77.5% | **0.5345** | 100% |
| 2006-02 | 81.25% | **0.6750** | 100% |
| 2006-03 | 77.5% | 0.8604 | 100% |
| 2006-04 | 73.75% | 0.8199 | 100% |
| 2006-05 | 73.75% | 0.8143 | 100% |
| 2006-06 | 77.5% | 0.8547 | 100% |

January and February fail the predefined 0.75 rank-correlation sensitivity threshold.

A 120-query SGML-header fallback diagnostic produced **0 SGML-only country resolutions**, so the blocker was not merely flat-vs-SGML header grammar.

## 11. Country evidence policy — frozen

Country evidence order remains:
1. same-filing explicit country;
2. deterministic NON_US CINS;
3. explicit ADR/GDR/depositary receipt;
4. historical exact issuer form/name -> exactly one CIK in pre-report-date SEC master;
5. pre-report-date SEC filing evidence binding that same historical entity/CIK to a state/country field;
6. otherwise UNKNOWN.

Current ticker metadata is forbidden for country discovery.

The new filing-detail recovery is valid only because it applies the same general, return-independent rule to the entire unresolved population. Do **not** select individual names because they move the Top80 ranks.

## 12. Additional index-headers recovery — completed

Workflow:
`.github/workflows/research-momentum-v2-9-country-index-headers-recovery-v29.yml`

Run: **`34029552893`**  
Status: **SUCCESS**  
Head: `122bbaee1aebd579d0eec02e1ff37fc7c2092809`

All 8 shards succeeded.

Artifacts:
- shard 0: `9988363468`
- shard 1: `9988349197`
- shard 2: `9988404099`
- shard 3: `9988338820`
- shard 4: `9988333329`
- shard 5: `9988356053`
- shard 6: `9988364713`
- shard 7: `9988328174`

These artifacts are also the candidate inputs used for the later filing-detail recovery.

## 13. Filing-detail recovery — complete evidence set now exists

The filing-detail rule promotes an original strict-country UNKNOWN only when:
- the exact `(ticker, securityId, reportDate)` key is present in the strict audit;
- historical exact issuer evidence identifies one CIK;
- an SEC filing dated no later than the report date binds the same historical entity and CIK to exactly one `State of Incorp.`/equivalent state code;
- `resolutionSource == PIT_FILING_DETAIL_ENTITY_STATE`.

No current metadata, fuzzy matching, US default, ranks, returns or performance are allowed.

### Main filing-detail run

Run `34084934273` ended **cancelled**, so it is **not** a complete run-level authority. However, five completed shard artifacts are valid exact evidence products and can be reused:
- shard 2: `10005459279`
- shard 3: `10005267895`
- shard 4: `10005356088`
- shard 5: `10005428298`
- shard 7: `10005351246`.

### Transport-only fast retry

Timed-out shards 0, 1 and 6 were rerun without changing the semantic evidence rule.

Workflow:
`.github/workflows/research-momentum-v2-9-country-filing-detail-fast-retry-v29.yml`

Run: **`34086972442`**  
Status: **SUCCESS**  
Head: `a76b00c93f07197d07781b0839b64cf2af1b41e4`

Artifacts:
- shard 0: `10005545021`
- shard 1: `10005550515`
- shard 6: `10005541171`.

The workflow policy is explicitly:
`HISTORICAL_EXACT_CIK_PLUS_PRE_REPORT_ACCESSION_DETAIL_STATE_ONLY`.

### Complete 8-shard set to use next

| Shard | Artifact | Source run |
|---:|---:|---:|
| 0 | `10005545021` | `34086972442` |
| 1 | `10005550515` | `34086972442` |
| 2 | `10005459279` | `34084934273` |
| 3 | `10005267895` | `34084934273` |
| 4 | `10005356088` | `34084934273` |
| 5 | `10005428298` | `34084934273` |
| 6 | `10005541171` | `34086972442` |
| 7 | `10005351246` | `34084934273` |

This mixed eight-artifact set is the **current recovery input** for the next Gate run.

## 14. Important orchestration failure — do not misinterpret it as Gate FAIL

Current final workflow:
`.github/workflows/research-momentum-v2-9-gate-b-filing-detail-final-h1-2006.yml`

It is currently stale because it still sets:

`DETAIL_RUN_ID="34084934273"`

and expects all eight recovery artifacts to be contained in that one run.

Gate workflow run `34085002133` therefore failed in the step:
`Wait for strict filing-detail recovery and download eight shards`.

The actual merge, Universe, upper-bound sensitivity and Gate calculation steps were **skipped**.

Therefore:

> `34085002133` is an orchestration failure, not a new methodological Gate B FAIL.

Do not cite it as evidence that the recovered-country Universe failed the Gate.

## 15. Exact next action

Do not redo source discovery, holdings parsing or N-PX mapping.

Update/rebind `.github/workflows/research-momentum-v2-9-gate-b-filing-detail-final-h1-2006.yml` so that it downloads the **eight exact filing-detail artifact IDs in Section 13**, rather than requiring one successful `DETAIL_RUN_ID`.

Then execute, in this exact order:

1. download original strict country artifact `9987700449`;
2. download authoritative holdings artifact `9986815485`;
3. download mapping artifact `9987093683`;
4. download the eight filing-detail artifacts listed above into `data/research/country-detail-recovery/`;
5. run `scripts/research-country-filing-detail-merge-v29.py`;
6. assert eight shard files, no duplicate keys, no country conflicts, only original UNKNOWN keys promoted;
7. run `scripts/research-nq-hybrid-universe-h1-2006.py`;
8. run `scripts/research-nq-hybrid-country-upper-bound-v29.py`;
9. run `scripts/research-momentum-v2-9-gate-b-v13-finalize.py`;
10. upload final country, Universe, upper-bound and Gate decision artifacts;
11. inspect the actual Gate metrics and record PASS/FAIL.

Do not change thresholds or evidence rules between steps 5 and 11.

## 16. Gate B thresholds / interpretation

Use the preregistered Gate semantics only. Do not tune them after viewing H1 2006 results.

Structural Gate targets include:
- median Top-K overlap >= 80%;
- minimum Top-K overlap >= 70%;
- median rank correlation >= 0.75;
- Top2 individual retention >= 85%;
- both Top2 retained >= 75%.

Country upper-bound sensitivity must remain immaterial under the already frozen per-month checks; do not weaken the January/February rank-correlation requirement simply to pass.

## 17. What to do after the next Gate

### If Gate B PASS

1. Update `docs/research/momentum-v2-9-gate-b-decision-h1-2006.md` with the new authoritative Gate run/artifact.
2. Only then state exactly:
   **`Universe reconstruction is confirmed`**
3. Run the research-only H1 2006 historical builder smoke test.
4. Output only research data, e.g. `data/research/universe-history-h1-2006-v29.json`.
5. Validate six monthly records and Production-schema compatibility.
6. Assert Production files are unchanged (`git diff --exit-code`).
7. Do not use broad performance as feedback to alter reconstruction rules.

### If Gate B FAIL

1. Keep the formal decision FAIL.
2. Do not tune source/mapping/country rules using the failed ranks.
3. Investigate only new **general**, PIT, return-independent evidence that applies to the unresolved population as a whole.
4. Do not rescue a hand-picked list of high-impact symbols selected from Top80 differences.

## 18. Research-only historical builder

A research-only builder/smoke-test path has already been prepared conceptually/code-wise with a Gate PASS assertion.

Required isolation:
- research output only;
- six H1 2006 months first;
- Production `data/universe-history.json` must not be written;
- Production Stage21 must not run;
- Production diff must remain zero.

Do not run this builder until the next successful Gate execution returns PASS.

## 19. Rejected / superseded paths — do not revive

- source v5 as final authority;
- old failed holdings cache as authority;
- fuzzy/edit-distance security mapping;
- ambiguous security auto-assignment;
- current ticker -> historical CIK/country fallback;
- US default for UNKNOWN;
- numeric CUSIP = US inference;
- absence of ADR/GDR = US inference;
- future Series/Class IDs backfilled before the 2006-02-06 regime boundary;
- N-Q-only source discovery;
- trust-global ETF evidence binding all sibling Series;
- summary Schedule of Investments treated as a complete portfolio;
- old rank-gap Spearman closed form;
- Gate run `34085002133` as a methodological result;
- broad 2006–2018 performance before Gate PASS.

## 20. Files most relevant on resume

- `docs/research/momentum-handoff-current.md` — this file, canonical entry point
- `docs/research/momentum-v2-9-gate-b-decision-h1-2006.md` — current formal FAIL decision
- `.github/workflows/research-momentum-v2-9-gate-b-filing-detail-final-h1-2006.yml` — **next file to fix**
- `.github/workflows/research-momentum-v2-9-country-filing-detail-fast-retry-v29.yml`
- `scripts/research-country-filing-detail-merge-v29.py`
- `scripts/research-nq-hybrid-universe-h1-2006.py`
- `scripts/research-nq-hybrid-country-upper-bound-v29.py`
- `scripts/research-momentum-v2-9-gate-b-v13-finalize.py`

## 21. Resume instruction for a new chat

Start by reading this file and the formal Gate decision. Then inspect the branch head and verify the eight artifact IDs in Section 13 still exist. Do **not** reopen already-settled source/parser/mapping methodology unless new evidence contradicts it. The next deliverable is a successful execution of the filing-detail merged Gate B, not another source rebuild.
