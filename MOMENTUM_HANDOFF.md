# Momentum Research Handoff — Canonical Entry Point

This file is the stable handoff entry point for new ChatGPT sessions and other research agents.

## Read first

Current detailed research handoff:
- Branch: `research/nq-npx-mapping-2006-20260903`
- Path: `docs/research/momentum-handoff-current.md`

Latest same-branch delta:
- Path: `docs/research/nq-npx-mapping-2006-20260903.md`

The detailed handoff is canonical. Read it first, then the delta.

## Objective

Reconstruct a point-in-time historical ETF-holdings universe for 2006 onward that is economically as close as possible to frozen Production N-PORT, without changing Production strategy `momentum-stage21-sbi-2026-09-v1`.

Do **not** run a broad 2006–2018 Stage21 performance test yet.

## Critical correction

The old nine-series N-Q PIT sample is invalidated. `SCHEDULE OF INVESTMENTS (CONTINUED)` pages had been treated as independent portfolios and could be assigned to the wrong ETF by holdings-word similarity.

Corrected segmentation now uses only exact filing-time series titles, groups continuation pages, and trims the final series at `NET ASSETS ... 100%`.

Corrected PIT:
- run `33714482859`
- artifact `9878011119`
- 20 retained series
- median holdings 41.

The old 43.53% / 60.67% mapping number is mapping-engine history only.

## Accepted legacy EC bridge

Per-holding EC diagnostic:
- run `33714785802`
- artifact `9878123068`
- 964 holdings
- explicit asset-section attribution: **99.79% by count / 99.97% by weight**
- explicit `COMMON_EQUITY`: **936 holdings / 99.63% of weight**.

Accepted rule: a legacy holding is `EC` only when it inherits an explicit `COMMON STOCK(S/SHARES)` section. SHORT_TERM, DEBT, PREFERRED and UNKNOWN do not pass. Unknown is never coerced.

EC-filtered PIT:
- run `33715016882`
- artifact `9878189715`
- all 20 corrected series still pass structural eligibility
- original portfolio-relative weights are preserved; no post-EC renormalization.

## Active security-mapping baseline

Frozen merged N-PX master: artifact `9876020712`.

EC-filtered mapping:
- run `33715050446`
- artifact `9878201336`
- 20 series
- 935 mapping-eligible EC holdings
- 654 unique matches
- count coverage **69.95%**
- weight coverage **78.98%**
- ambiguous 14
- unmapped 267
- fuzzy mapping remains diagnostic only.

This supersedes the pre-EC 69.28% / 78.92% mapping result as the active baseline.

## US / CORP gates

`INVESTMENT_COUNTRY=US` remains unresolved. SEC Form N-PORT defines the primary country field as the country where the issuer is organized. Therefore US listing venue, numeric CUSIP, or absence of ADR/GDR is not enough. Explicit country sections are usable where present; otherwise unknown remains unknown until a scalable issuer-country source is established.

`ISSUER_TYPE=CORP` remains unresolved. A bootstrap-based redundancy test is rejected because Production bootstrap data has already been filtered on `EC+US+CORP` and no longer retains the raw issuer-type field.

## 64-CIK master transport

Frozen design remains:
- one deterministic primary N-PX representative per unique CIK
- sort by CIK
- 64 equal-quantile CIK positions
- no target-name, universe, momentum, or return selection.

GitHub-hosted runner transport currently gets SEC `master.idx` 403, `master.zip` 403, tested proxy 422. Continue this path in parallel but do not block US/CORP work on it.

## Current gate

Proceed in this order:
1. use EC-filtered PIT artifact `9878189715` as active 2006 holdings input;
2. use EC-filtered mapping artifact `9878201336` as active security-mapping baseline;
3. construct a scalable issuer-organization-country (`US`) bridge, keeping unresolved holdings UNKNOWN;
4. investigate `CORP` independently;
5. continue deterministic 64-CIK source-index/master work in parallel;
6. only then build legacy ETF-count / aggregate-weight / max-weight / recency-weight scoring inputs;
7. validate Top80 overlap, rank correlation, and Production Top2 retention in an overlap period;
8. freeze the bridge before opening older returns;
9. expose older history only in small staged windows, not 2006–2018 at once.

## New-session protocol

When only the repository URL is provided:
1. read this file;
2. read the canonical research handoff on the branch above;
3. read the same-branch delta;
4. do not revive the old nine-series sample;
5. preserve frozen artifact inputs for apples-to-apples structural comparisons;
6. do not change Production parameters or tune reconstruction rules against older strategy returns.
