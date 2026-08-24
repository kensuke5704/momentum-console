import assert from "node:assert/strict";
import test from "node:test";
import { runStrategySimulation } from "../src/lib/backtest";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import type { PricePoint, UniverseMonth } from "../src/lib/types";

const daily = (symbolBase: number, slope: number): PricePoint[] => Array.from({ length: 400 }, (_, index) => {
  const date = new Date(Date.UTC(2020, 0, 1 + index)).toISOString().slice(0, 10);
  const close = symbolBase * (1 + index * slope);
  return { date, open: close * .999, close };
});

test("a pending monthly/recovery order has prices available on its execution day", () => {
  const qqq = daily(100, .001), aaa = daily(100, .004), bbb = daily(90, .003);
  const signalPoint = qqq[350];
  const universe: UniverseMonth = { signalMonth: signalPoint.date.slice(0, 7), asOf: signalPoint.date, sourceFilings: [], added: ["AAA", "BBB"], removed: [], symbols: ["AAA", "BBB"].map((symbol, index) => ({ symbol, universeRank: index + 1, etfCount: 2, aggregateWeight: 10, maxWeight: 5, recencyWeight: 8, universeScore: 10 - index })) };
  const result = runStrategySimulation({ histories: { QQQ: qqq, TQQQ: qqq, AAA: aaa, BBB: bbb }, universeHistory: [universe], config: { ...PRODUCTION_STRATEGY, backtestStart: qqq[300].date } });
  assert.notEqual(result.state.nextAction.executionDate && result.state.nextAction.executionDate < result.state.asOf, true);
});
