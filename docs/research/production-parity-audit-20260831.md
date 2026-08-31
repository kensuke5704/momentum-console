# Production / backtest parity audit — 2026-08-31

## Scope

Audit whether the Production console, live state, monthly signal, backtest engine, execution contract, and Forward OOS are driven by the same frozen Fixed60 rule and the same strategy clock.

## Confirmed parity

- `src/lib/config.ts` remains the Production rule source.
- Both displayed live state and backtest are produced by `runStrategySimulation` / `transitionDay`.
- Monthly signal construction uses `buildMonthlySignal` with the Production config.
- Entry and exit are executed by the same state machine at next-session open with the configured transaction cost.
- Forward OOS is rebuilt from the same Production backtest engine and confirmed OOS dates are immutable except for explicitly provisional close rows.
- Dashboard rejects stale frozen backtest/OOS artifacts from a different strategy id.

## Material mismatch found

Before this audit fix, `buildDashboardPayload` constructed `currentSignal` whenever a latest Universe existed, even if the exact Universe `asOf` date did not yet exist in the QQQ daily strategy clock.

At a month boundary this created a real timing risk:

1. the monthly Universe job could commit the new month-end Universe before Yahoo's exact month-end daily close had been activated;
2. the state machine correctly did **not** process that signal because its QQQ trading-date loop had not reached the Universe `asOf` date;
3. the dashboard could nevertheless call `buildMonthlySignal` for the new `asOf` date using the latest earlier monthly close;
4. the console could therefore display a new month-end signal that the live/backtest state machine had not actually confirmed.

This is a Production/display parity violation and a potential stale-close trading instruction.

## Correction

`currentSignal` is now fail-closed: it remains `null` unless the exact Universe `asOf` date is present in the QQQ strategy clock. Once that row is activated, the dashboard and state machine publish the same signal date.

Regression tests cover both sides of the boundary:

- no displayed signal before the exact signal-date QQQ close exists;
- displayed and state-machine pending signals both appear once that exact date exists.

## Result

After this correction, no material Production/backtest rule mismatch was found in the audited signal/state/execution path. The remaining differences are intentional presentation/persistence behavior (for example frozen historical backtest display versus current live state), not separate trading rules.
