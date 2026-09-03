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

Current active gate: historical security mapping and coverage improvement for legacy N-Q holdings using N-PX issuer/ticker/security-ID data.

Latest stable structural mapping uses a **frozen merged 2006 N-PX master** so mapping-rule evaluation is not contaminated by live filing-fetch timeouts:
- frozen master source artifact: `9876020712`
- frozen-master workflow run: `33708713690`
- result artifact: `9876161889`
- eligible N-Q holdings: 487
- N-PX paired records: 2,925
- unique mapping coverage by count: **43.53%**
- unique mapping coverage by eligible holding weight: **60.67%**
- ambiguous holdings: 3
- unmapped holdings: 272
- conservative ADR-base resolution adds only two unique matches and is prohibited when the base issuer has multiple identities
- fuzzy matching remains diagnostic only
- no strategy-return data used

Remaining unmapped weight is dominated by weak/no-master candidates rather than a small set of obvious name aliases, so **master breadth remains the main active limitation**.

The next frozen structural design remains a 64-sample N-PX master using one deterministic representative per unique CIK and equal-quantile CIK sampling. Direct SEC `master.idx` and `master.zip` access from GitHub-hosted runners both return HTTP 403; proxy `master.idx` access returned HTTP 422. This is a data transport issue, not a strategy-performance result.

For mapping-rule experiments, use the frozen-master workflow. Do not compare total coverage across live broad-supplement runs when their fetched source sets differ.

Do **not** run the 2006–2018 Stage21 performance backtest yet. First finish structural mapping/coverage validation, construct and validate the legacy universe bridge, and freeze those rules before exposing long-history strategy returns.

## New-session protocol

When only the repository URL is provided:
1. Read this file first.
2. Read `docs/research/momentum-handoff-current.md` from the branch listed above.
3. Read `docs/research/nq-npx-mapping-2006-20260903.md` from the same branch for the latest delta.
4. Continue from the current structural mapping/coverage gate.
5. Use frozen artifacts for apples-to-apples mapping-rule comparisons.
6. Do not re-run rejected approaches without new evidence.
7. Do not change frozen Production parameters or use 2006–2018 returns to tune historical reconstruction rules.

Whenever the active research branch, canonical handoff location, or latest delta changes, update this root entry point on `main` in the same workstream.
