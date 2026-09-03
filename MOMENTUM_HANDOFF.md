# Momentum Research Handoff — Canonical Entry Point

This file is the stable handoff entry point for new ChatGPT sessions and other research agents.

## Read first

Current detailed research handoff:
- Branch: `research/nq-npx-mapping-2006-20260903`
- Path: `docs/research/momentum-handoff-current.md`

The detailed handoff above is the canonical source for ongoing Momentum research state, confirmed results, rejected paths, anti-overfitting constraints, and next actions.

## Current research objective

Reconstruct a point-in-time historical ETF-holdings universe for 2006 onward that is economically as close as possible to the frozen Production N-PORT universe, without modifying the frozen Production strategy.

Frozen strategy ID: `momentum-stage21-sbi-2026-09-v1`.

Current active gate: historical security mapping and coverage improvement for legacy N-Q holdings using N-PX issuer/ticker/security-ID data.

Do **not** run the 2006–2018 Stage21 performance backtest yet. First finish structural mapping/coverage validation, construct and validate the legacy universe bridge, and freeze those rules before exposing long-history strategy returns.

## New-session protocol

When only the repository URL is provided:
1. Read this file first.
2. Read `docs/research/momentum-handoff-current.md` from the branch listed above.
3. Continue from its `Current active gate` and `Planned validation sequence`.
4. Do not re-run rejected approaches without new evidence.
5. Do not change frozen Production parameters or use 2006–2018 returns to tune historical reconstruction rules.

Whenever the active research branch or canonical handoff location changes, update this root entry point on `main` in the same workstream.