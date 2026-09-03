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

Latest confirmed structural mapping on the same frozen 2006 N-Q PIT sample:
- eligible N-Q holdings: 487
- merged N-PX master: frozen 24-filing deterministic baseline plus independently pre-fixed broad-fund-family supplement
- unique mapping coverage by count: **42.71%**
- unique mapping coverage by eligible holding weight: **59.79%**
- XLE weight coverage: 94.41%
- XLG weight coverage: 93.54%
- XBI eligible-weight coverage: 100.00%
- no strategy-return data used

The broad-fund supplement materially improves mapping and is retained as structural evidence, but coverage remains insufficient to call the reconstructed universe Production-equivalent.

The next frozen structural design remains a 64-sample N-PX master using one deterministic representative per unique CIK and equal-quantile CIK sampling. Source-index transport from GitHub-hosted runners is currently blocked by SEC 403 / proxy 422 behavior; this is a data transport issue, not a strategy-performance result.

Do **not** run the 2006–2018 Stage21 performance backtest yet. First finish structural mapping/coverage validation, construct and validate the legacy universe bridge, and freeze those rules before exposing long-history strategy returns.

## New-session protocol

When only the repository URL is provided:
1. Read this file first.
2. Read `docs/research/momentum-handoff-current.md` from the branch listed above.
3. Read `docs/research/nq-npx-mapping-2006-20260903.md` from the same branch for the latest delta.
4. Continue from the current structural mapping/coverage gate.
5. Do not re-run rejected approaches without new evidence.
6. Do not change frozen Production parameters or use 2006–2018 returns to tune historical reconstruction rules.

Whenever the active research branch, canonical handoff location, or latest delta changes, update this root entry point on `main` in the same workstream.
