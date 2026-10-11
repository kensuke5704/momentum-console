import assert from "node:assert/strict";
import test from "node:test";
import { validateImportedExecutionHistory, validateImportedOosIdentity } from "../src/lib/manual-nport-validation";
import { PRODUCTION_PORTFOLIO } from "../src/lib/portfolio-config";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import type { BacktestResult } from "../src/lib/types";

test("manual import validates OOS against Stage21, not its Fixed60 inner engine", () => {
  assert.notEqual(PRODUCTION_PORTFOLIO.strategyId, PRODUCTION_STRATEGY.strategyId);
  assert.doesNotThrow(() => validateImportedOosIdentity(PRODUCTION_PORTFOLIO.strategyId, PRODUCTION_PORTFOLIO.strategyId));
});

test("delayed Universe activation cannot rewrite pre-execution OOS holdings", () => {
  const backtest = (symbol: string, date = "2026-10-01") => ({ events: [{ date, type: "PORTFOLIO_REBALANCE_OPEN", symbols: [symbol], reason: "test" }] }) as BacktestResult;
  assert.throws(() => validateImportedExecutionHistory(backtest("AMD"), backtest("DELL"), "2026-10-12"), /already-executed OOS/);
  assert.doesNotThrow(() => validateImportedExecutionHistory(backtest("AMD"), backtest("AMD"), "2026-10-12"));
  assert.doesNotThrow(() => validateImportedExecutionHistory(backtest("AMD", "2026-10-12"), backtest("DELL", "2026-10-12"), "2026-10-12"));
});

test("legacy or mismatched OOS remains fail-closed after regeneration", () => {
  assert.throws(() => validateImportedOosIdentity(PRODUCTION_PORTFOLIO.strategyId, PRODUCTION_STRATEGY.strategyId), /portfolio strategy IDs/);
  assert.throws(() => validateImportedOosIdentity(PRODUCTION_STRATEGY.strategyId, PRODUCTION_STRATEGY.strategyId), /portfolio strategy IDs/);
});
