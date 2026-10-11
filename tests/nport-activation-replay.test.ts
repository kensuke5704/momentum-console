import assert from "node:assert/strict";
import test from "node:test";
import { buildStage21Portfolio } from "../src/lib/portfolio/stage21";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import { applyExtraordinaryRebalance, defaultNportOperations, executionUniverseHistory } from "../src/lib/nport-operations";
import { nextUsTradingSession } from "../src/lib/trading-calendar";
import type { PricePoint, UniverseMonth } from "../src/lib/types";

const dates: string[] = [];
for (let date = "2019-01-02"; date <= "2026-10-13"; date = nextUsTradingSession(date)) dates.push(date);
const histories: Record<string, PricePoint[]> = Object.fromEntries(["QQQ", "GLDM", "AAA", "BBB", "CCC"].map((symbol) => [symbol, dates.map((date, index) => {
  const growth = { QQQ: .0002, GLDM: .0001, AAA: .001, BBB: .0009, CCC: .0008 }[symbol]!;
  const close = 100 * (1 + growth) ** index;
  return { date, open: close, close };
})]));
const universe = (symbols: string[]): UniverseMonth => ({ signalMonth: "2026-09", asOf: "2026-09-30", symbols: symbols.map((symbol, index) => ({ symbol, universeRank: index + 1, etfCount: 2, aggregateWeight: 10, maxWeight: 5, recencyWeight: 9, universeScore: 10 - index })), sourceFilings: [], added: [], removed: [] });
const oldUniverse = universe(["AAA", "BBB"]), newUniverse = universe(["CCC", "AAA"]);
const signal = buildMonthlySignal({ universe: newUniverse, histories, qqq: histories.QQQ, nextSessionDate: "2026-10-12" });
const activation = { receivedAt: "2026-10-11T11:00:00Z", executionDate: "2026-10-12", signal };
const through = (end: string) => Object.fromEntries(Object.entries(histories).map(([symbol, rows]) => [symbol, rows.filter(row => row.date <= end)]));

test("new Universe is visible for selection without replacing the recorded month-end Universe", () => {
  const operations = { ...defaultNportOperations("2026q3"), executionUniverseHistory: [oldUniverse] };
  assert.deepEqual(executionUniverseHistory([newUniverse], operations), [oldUniverse]);
  const future = { ...newUniverse, signalMonth: "2026-10", asOf: "2026-10-30" };
  assert.deepEqual(executionUniverseHistory([newUniverse, future], operations), [oldUniverse, future]);
});

test("delayed receipt keeps holdings and OOS intact until the execution open, then executes once", () => {
  const prior = buildStage21Portfolio(through("2026-10-09"), [oldUniverse], []);
  const scheduled = buildStage21Portfolio(through("2026-10-09"), [oldUniverse], [], [activation]);
  assert.deepEqual(scheduled.backtest.equityCurve, prior.backtest.equityCurve);
  assert.deepEqual(scheduled.backtest.events, prior.backtest.events);
  assert.deepEqual(scheduled.portfolioState.holdings, prior.portfolioState.holdings);
  assert.equal(scheduled.portfolioState.nextAction.executionDate, "2026-10-12");
  const after = buildStage21Portfolio(histories, [oldUniverse], [], [activation]);
  assert.deepEqual(after.innerState.currentPositions.map(position => position.symbol), signal.selectedSymbols);
  assert.deepEqual(after.portfolioState.holdings.filter(holding => holding.role === "FIXED60").map(holding => holding.symbol), signal.selectedSymbols);
  assert.equal(after.backtest.events.filter(event => event.type === "PORTFOLIO_REBALANCE_OPEN" && event.date === "2026-10-12").length, 1);
  assert.match(after.backtest.events.find(event => event.type === "ENTRY_OPEN" && event.date === "2026-10-12")!.reason, /Delayed N-PORT/);
  assert.notEqual(after.portfolioState.nextAction.executionDate, "2026-10-12");
});

test("a delayed selection never overrides Circuit/Stop recovery or a pending risk exit", () => {
  const base = buildStage21Portfolio(through("2026-10-09"), [oldUniverse], []);
  const operations = { ...defaultNportOperations("2026q3"), extraordinaryRebalance: { evaluatedAt: activation.receivedAt, priceAsOf: signal.signalDate, changed: true, executionDate: activation.executionDate, previousSymbols: ["AAA", "BBB"], previousWeights: [.6, .4], nextSymbols: signal.selectedSymbols, nextWeights: signal.targetWeights, signal } };
  for (const state of ["WAITING_RECOVERY", "LOCKED_CIRCUIT", "LOCKED_STOP"] as const) {
    const dashboard = { liveState: { ...base.innerState, state }, portfolioState: base.portfolioState };
    assert.equal(applyExtraordinaryRebalance(dashboard, operations), dashboard);
  }
  const dashboard = { liveState: { ...base.innerState, nextAction: { ...base.innerState.nextAction, type: "SELL_ALL_NEXT_OPEN" as const } }, portfolioState: base.portfolioState };
  assert.equal(applyExtraordinaryRebalance(dashboard, operations), dashboard);
  const expired = { liveState: { ...base.innerState, asOf: "2026-10-12" }, portfolioState: base.portfolioState };
  assert.equal(applyExtraordinaryRebalance(expired, operations), expired);
});

test("the shared replay engine retains the cash lock when delayed receipt occurs during recovery", () => {
  const shocked = Object.fromEntries(Object.entries(histories).map(([symbol, rows]) => [symbol, rows.map(row => row.date >= "2026-10-08" && symbol !== "GLDM" ? { ...row, open: row.open * .6, close: row.close * .6 } : row)]));
  const result = buildStage21Portfolio(shocked, [oldUniverse], [], [activation]);
  assert.equal(result.innerState.state, "WAITING_RECOVERY");
  assert.equal(result.innerState.currentPositions.length, 0);
  assert.ok(result.portfolioState.holdings.every(holding => holding.symbol === "GLDM"));
  assert.ok(!result.backtest.events.some(event => event.date === "2026-10-12" && event.type === "ENTRY_OPEN"));
});
