# Momentum Research Handoff — Canonical Entry Point

This file is the stable handoff entry point for new ChatGPT sessions and other research agents.

## Read first

Current detailed research handoff:
- Branch: `research/nq-npx-mapping-2006-20260903`
- Path: `docs/research/momentum-handoff-current.md`

Latest same-branch research delta:
- Path: `docs/research/nq-npx-mapping-2006-20260903.md`

Read the detailed handoff first, then the latest delta note above before continuing. The detailed handoff remains the canonical long-form source; the delta records work completed after its last full refresh.

## Current research objective

Reconstruct a point-in-time historical ETF-holdings universe for 2006 onward that is economically as close as possible to the frozen Production N-PORT universe, without modifying the frozen Production strategy.

Frozen strategy ID: `momentum-stage21-sbi-2026-09-v1`.

## Critical current state

The prior nine-series N-Q PIT sample is superseded. An audit found that `SCHEDULE OF INVESTMENTS (CONTINUED)` pages had been treated as independent portfolios and sometimes assigned to the wrong ETF using holdings-word similarity.

The corrected segmentation now:
- assigns schedule pages only from exact filing-time registered series titles;
- groups continuation pages with the same explicit series;
- never uses holdings/industry words to determine series identity;
- trims the final schedule at an explicit `NET ASSETS ... 100%` boundary before parsing later filing tables.

Corrected fixed-source PIT holdings:
- workflow run: `33714482859`
- artifact: `9878011119`
- retained PIT series: **20**
- median holdings: **41**

The old **43.53% count / 60.67% weight** mapping result is retained only as mapping-engine history and is not valid evidence of historical-universe quality.

## Active security-mapping baseline

Use the same frozen merged N-PX master artifact `9876020712` for apples-to-apples evaluation.

Corrected mapping workflow:
- run: `33714515426`
- artifact: `9878021112`
- corrected PIT series: 20
- eligible holdings: **944**
- unique matches: **654**
- mapping coverage by count: **69.28%**
- mapping coverage by eligible holding weight: **78.92%**
- ambiguous holdings: 14
- unmapped holdings: 276
- fuzzy matching remains diagnostic only
- no strategy-return data used.

## Legacy N-PORT field bridge

Corrected structural diagnostic:
- workflow run: `33714585732`
- artifact: `9878045597`

`ASSET_CAT=EC`:
- 28 / 30 examined corrected schedules explicitly print `COMMON STOCK(S/SHARES) -- xx%`;
- most are approximately 99.5–100.0% common stocks;
- this is strong schedule-level EC evidence but is not yet a validated per-holding EC replacement.

`INVESTMENT_COUNTRY=US`:
- do not default missing country headings to US;
- DGT explicitly reports United States 62.7% plus multiple foreign-country allocations;
- ADR/GDR references identify useful foreign-security flags but do not by themselves reproduce N-PORT country classification.

`ISSUER_TYPE=CORP` remains a separate unresolved structural gate.

## 64-CIK master transport

The frozen 64-CIK design remains:
- one deterministic primary N-PX representative per unique CIK;
- sort by CIK;
- sample 64 equal-quantile positions;
- no N-Q target names, universe outcomes, momentum, or returns in selection.

Direct SEC `master.idx` and `master.zip` access from GitHub-hosted runners returns HTTP 403; the tested proxy index route returned HTTP 422. This is a source-transport issue, not a strategy-performance result.

Do not block the EC/US/CORP structural work on this transport issue.

## Current gate

Do **not** run the 2006–2018 Stage21 performance backtest yet.

Proceed in this order:
1. use corrected PIT artifact `9878011119` as the active N-Q holdings baseline;
2. validate per-holding legacy `EC` attribution from explicit schedule section state;
3. construct a conservative `US` attribution hierarchy; unknown remains unknown;
4. investigate `CORP` parity separately;
5. continue the reproducible 64-CIK source-index path in parallel;
6. only then construct legacy universe scoring inputs;
7. perform overlap-period universe validation before any long-history strategy-return test.

## New-session protocol

When only the repository URL is provided:
1. Read this file first.
2. Read `docs/research/momentum-handoff-current.md` from the branch listed above.
3. Read `docs/research/nq-npx-mapping-2006-20260903.md` from the same branch for the latest delta.
4. Treat the corrected 20-series PIT sample as active; do not revive the old nine-series sample.
5. Use frozen artifacts for apples-to-apples mapping-rule comparisons.
6. Do not re-run rejected approaches without new evidence.
7. Do not change frozen Production parameters or use 2006–2018 returns to tune historical reconstruction rules.

Whenever the active research branch, canonical handoff location, or latest delta changes, update this root entry point on `main` in the same workstream.
