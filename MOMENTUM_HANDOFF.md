# Momentum Research Handoff — Canonical Entry Point

This file is the stable handoff entry point for new ChatGPT sessions and other research agents.

## Read first

Current detailed research handoff:
- Branch: `research/nq-npx-mapping-2006-20260903`
- Path: `docs/research/momentum-handoff-current.md`

Latest same-branch delta:
- Path: `docs/research/nq-npx-mapping-2006-20260903.md`

The detailed handoff is canonical. Read it first, then the delta.

## Objective and hard stop

Reconstruct a point-in-time historical ETF-holdings universe for 2006 onward that is economically as close as possible to frozen Production N-PORT, without changing Production strategy `momentum-stage21-sbi-2026-09-v1`.

Do **not** implement the historical/legacy Universe builder until reproducibility is confirmed. Do **not** run broad 2006–2018 Stage21 performance yet.

## Current Gate state — 2026-09-04

### Gate A — PASS

Production mechanics reproduce strongly over the first 12 Production Universe months:
- median Top-K overlap 93.75%
- minimum 92.5%
- median Spearman 0.9996
- Production Top2 retention 100%.

### Gate B transition evidence — strong but not sufficient for implementation

For the actual three source series behind 2020-01 Production, nearest pre-Production complete holdings reports are within 90–183 days and retain later N-PORT holdings at:
- ClearBridge/LRGE: 92.9% count / 95.9% weight
- Goldman GFIN: 94.2% / 97.4%
- PPTY: 93.9% / 98.0%.

The three-series 2020-01 aggregate legacy shadow reproduces:
- 8/9 Production names = 88.9%
- Spearman 0.842
- Production Top2 2/2 retained.

This direct-month result is strong, but the run starts from the known Production source series, so independent historical source discovery is still required before implementation.

### CORP bridge

Valid raw N-PORT transition checks show that among `EC+US` holdings:
- LRGE 42/42 CORP
- GFIN 69/69 CORP
- PPTY 115/115 CORP
- combined **226/226 = 100% CORP**.

Thus CORP is empirically redundant after EC+US in this transition cohort and is no longer the principal blocker.

### 2006 EC / identity mapping

Accepted legacy EC rule remains explicit `COMMON_EQUITY` only:
- 936 EC holdings across 20 corrected PIT series
- 99.63% of portfolio weight.

Baseline EC-filtered N-PX mapping:
- 654 mapped holdings
- 69.95% count / 78.98% weight.

Deterministic structural mapping sensitivity, using only share-class/jurisdiction suffix cleanup and unique long-prefix identity reconciliation, improves this to:
- 691 mapped holdings
- **73.90% count / 82.49% weight**
- no fuzzy/edit-distance auto-match.

### 2006 PIT country bridge — still insufficient

Conservative hierarchy:
- alphabetic CINS prefix => NON_US
- explicit ADR/GDR => NON_US
- historical SEC filing-time state/country from a deterministically resolved CIK => US/NON_US
- current SEC ticker data may seed a CIK only; current state is never evidence
- UNKNOWN stays UNKNOWN.

Full 12-shard attribution plus UNKNOWN-only historical 10-K retry resolved 53 additional identities.

Baseline-mapping country coverage after retry:
- mapped holdings: 59.17% count / 62.68% weight resolved
- all 936 EC holdings: **42.95% count / 50.97% weight resolved**.

Country classification on newly recovered structural mapping identities adds resolved weight 27.53, raising all-EC resolved weight only to approximately **52.35%**.

A further current-ticker-CIK + historical-name-validation pilot on the 50 highest-weight remaining UNKNOWN identities resolved **0/50** and is rejected as an effective next route.

Country coverage is therefore still the main implementation blocker.

### Historical source-series discovery — transport blocker isolated

SEC native historical filing-index pages do expose `Series and Classes/Contracts Information`, including historical Series IDs, Class IDs and tickers. Example: accession `0000950135-06-001225` visibly contains Select Sector series/tickers.

However GitHub-hosted runners cannot retrieve the native index page and fall back to r.jina; the r.jina rendering omits the Series/Class table. Complete-submission SGML also does not provide an equivalent reliable replacement.

Therefore source discovery is currently blocked by **transport/acquisition**, not by absence of historical SEC series metadata.

## Current gate

Universe reconstruction is **not yet confirmed**. Continue in this order:
1. improve conservative 2006 issuer-country resolved-weight coverage materially above ~52.35% without coercing UNKNOWN;
2. establish a scalable, Production-independent acquisition route for historical SEC Series/Class/Ticker metadata;
3. build a full aggregate legacy Universe from independently discovered sources;
4. re-run Gate B overlap/rank/Top2 metrics;
5. only if Gate B passes, explicitly declare `Universe reconstruction is confirmed` and implement the historical builder;
6. keep broad 2006–2018 Stage21 performance unopened until bridge rules are frozen.

## New-session protocol

When only the repository URL is provided:
1. read this file;
2. read `docs/research/momentum-handoff-current.md` on `research/nq-npx-mapping-2006-20260903`;
3. read the same-branch delta;
4. do not revive the old nine-series sample or old country-heading assumptions;
5. preserve frozen artifacts for apples-to-apples structural comparisons;
6. do not change Production parameters or tune reconstruction rules against older strategy returns.
