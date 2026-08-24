import assert from "node:assert/strict";
import test from "node:test";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { buildMonthlySignal, momentumScore } from "../src/lib/strategy/momentum";
import { initialEngineState, transitionDay, type EngineState } from "../src/lib/strategy/state-machine";
import type { MonthlySignal, NportFiling, PricePoint, UniverseMonth } from "../src/lib/types";
import { buildPointInTimeUniverse } from "../src/lib/universe/universe";

const point = (date: string, close: number, open = close): PricePoint => ({ date, open, close });
const holdings = (lead: string, weight = 5) => [{ symbol: lead, weight }, ...Array.from({ length: 9 }, (_, index) => ({ symbol: `X${index}`, weight: (100 - weight) / 9 }))];
const filing = (seriesId: string, filingDate: string, lead: string, weight = 5): NportFiling => ({ accession: `${seriesId}-${filingDate}`, seriesId, seriesName: `${seriesId} Innovation ETF`, reportDate: filingDate, filingDate, holdings: holdings(lead, weight) });

test("future N-PORT filings are never used", () => {
  const universe = buildPointInTimeUniverse([filing("S1", "2024-01-10", "OLD"), filing("S1", "2024-03-10", "FUTURE")], "2024-02", "2024-02-29");
  assert.ok(universe.symbols.some((row) => row.symbol === "OLD"));
  assert.ok(!universe.symbols.some((row) => row.symbol === "FUTURE"));
  assert.equal(universe.sourceFilings[0].filingDate, "2024-01-10");
});
test("latest public filing is selected per series", () => {
  const universe = buildPointInTimeUniverse([filing("S1", "2024-01-10", "OLD"), filing("S1", "2024-02-10", "NEW")], "2024-02", "2024-02-29");
  assert.ok(universe.symbols.some((row) => row.symbol === "NEW"));
  assert.ok(!universe.symbols.some((row) => row.symbol === "OLD"));
});
test("Universe is capped at 80", () => {
  const filings = Array.from({ length: 90 }, (_, index) => filing(`S${index}`, "2024-01-10", `T${index}`, 60));
  assert.equal(buildPointInTimeUniverse(filings, "2024-02", "2024-02-29").symbols.length, 80);
});
test("Universe score uses the specified breadth formula", () => {
  const universe = buildPointInTimeUniverse([filing("S1", "2024-02-29", "AAA", 5), filing("S2", "2024-02-29", "AAA", 5)], "2024-02", "2024-02-29");
  const row = universe.symbols.find((member) => member.symbol === "AAA")!;
  assert.ok(Math.abs(row.universeScore - (3 * Math.log1p(2) + .5 * Math.log1p(10) + .5 * Math.log1p(10))) < 1e-12);
});
test("Universe admission accepts etfCount>=2 or maxWeight>=4", () => {
  const universe = buildPointInTimeUniverse([filing("S1", "2024-01-10", "MAX", 4), filing("S2", "2024-01-10", "BREADTH", 2), filing("S3", "2024-01-10", "BREADTH", 2)], "2024-02", "2024-02-29");
  assert.ok(universe.symbols.some((row) => row.symbol === "MAX")); assert.ok(universe.symbols.some((row) => row.symbol === "BREADTH"));
});
test("production config contains no fixed TICKERS or genre controls", () => {
  assert.ok(!("tickers" in PRODUCTION_STRATEGY)); assert.ok(!("genreMax" in PRODUCTION_STRATEGY)); assert.ok(!("frontierMax" in PRODUCTION_STRATEGY));
});
test("Momentum score is exactly 0/20/80", () => assert.ok(Math.abs(momentumScore(9, .2, .5) - .44) < 1e-12));

function monthlyHistory(multiplier: number, lastMultiplier = multiplier): PricePoint[] {
  return Array.from({ length: 12 }, (_, index) => point(`2024-${String(index + 1).padStart(2, "0")}-28`, 100 * (1 + multiplier * index) * (index === 11 ? lastMultiplier / multiplier || 1 : 1)));
}
const universe = (symbols: string[]): UniverseMonth => ({ signalMonth: "2024-12", asOf: "2024-12-28", symbols: symbols.map((symbol, index) => ({ symbol, universeRank: index + 1, etfCount: 2, aggregateWeight: 10, maxWeight: 5, recencyWeight: 8, universeScore: 10 - index })), sourceFilings: [], added: symbols, removed: [] });
function signal(histories: Record<string, PricePoint[]>, symbols = Object.keys(histories)) {
  const qqq = Array.from({ length: 12 }, (_, index) => point(`2024-${String(index + 1).padStart(2, "0")}-28`, 100 + index));
  return buildMonthlySignal({ universe: universe(symbols), histories, qqq, nextSessionDate: "2025-01-02" });
}
test("1M return at +80% is excluded", () => {
  const history = Array.from({ length: 12 }, (_, index) => point(`2024-${String(index + 1).padStart(2, "0")}-28`, index === 11 ? 180 : 100));
  assert.equal(signal({ AAA: history }).candidates[0].exclusionReason, "ONE_MONTH_SURGE");
});
test("stock score at or below QQQ is excluded", () => assert.equal(signal({ AAA: Array.from({ length: 12 }, (_, index) => point(`2024-${String(index + 1).padStart(2, "0")}-28`, 100 + index)) }).candidates[0].exclusionReason, "NOT_ABOVE_QQQ"));
test("only Top2 are selected", () => assert.deepEqual(signal({ AAA: monthlyHistory(.08), BBB: monthlyHistory(.06), CCC: monthlyHistory(.04) }).selectedSymbols.length, 2));
test("zGap below .25 produces 50/50", () => {
  const result = signal({ AAA: monthlyHistory(.0500), BBB: monthlyHistory(.0499), CCC: monthlyHistory(.01) });
  assert.ok((result.zGap ?? 1) < .25); assert.deepEqual(result.targetWeights, [.5, .5]);
});
test("zGap at or above .25 produces 70/30", () => {
  const result = signal({ AAA: monthlyHistory(.20), BBB: monthlyHistory(.05), CCC: monthlyHistory(.049) });
  assert.ok((result.zGap ?? 0) >= .25); assert.deepEqual(result.targetWeights, [.7, .30000000000000004]);
});
test("Top1 weight never exceeds 70%", () => assert.ok(Math.max(...signal({ AAA: monthlyHistory(.5), BBB: monthlyHistory(.01), CCC: monthlyHistory(.009) }).targetWeights) <= .7));

const baseSignal: MonthlySignal = { strategyId: PRODUCTION_STRATEGY.strategyId, signalMonth: "2024-12", signalDate: "2024-12-31", executionDate: "2025-01-02", marketRiskOn: true, qqqClose: 120, qqqMonthlyMa: 110, qqqScore: .1, universe: ["AAA", "BBB"], candidates: [], selectedSymbols: ["AAA", "BBB"], targetWeights: [.5, .5], zGap: 0, allocationMode: "50/50" };
const qqqRecovery = Array.from({ length: 120 }, (_, index) => point(`2024-01-${String(index + 1).padStart(3, "0")}`, 100 + index));
function invested(): EngineState { const state = initialEngineState(); return { ...state, state: "INVESTED", marketRiskOn: true, cash: 0, currentPositions: [{ symbol: "AAA", shares: .005, entryPrice: 100, targetWeight: .5, currentPrice: 100, stopLevel: 82.5 }, { symbol: "BBB", shares: .005, entryPrice: 100, targetWeight: .5, currentPrice: 100, stopLevel: 82.5 }], portfolioPeak: 1, currentEquity: 1, nextAction: { type: "HOLD", executionDate: null, symbols: ["AAA", "BBB"], targetWeights: [.5, .5], reason: "hold" } }; }
test("month-end signal is not filled at the same close", () => {
  const out = transitionDay(initialEngineState(), { date: "2024-12-31", prices: {}, qqqHistoryThroughClose: qqqRecovery, monthlySignal: baseSignal, nextSessionDate: "2025-01-02" });
  assert.equal(out.currentPositions.length, 0); assert.equal(out.nextAction.type, "BUY_NEXT_OPEN");
});
test("individual stop schedules a next-open full exit", () => {
  const out = transitionDay(invested(), { date: "2025-01-03", prices: { AAA: point("2025-01-03", 80), BBB: point("2025-01-03", 100) }, qqqHistoryThroughClose: qqqRecovery, nextSessionDate: "2025-01-06" });
  assert.equal(out.currentPositions.length, 2); assert.equal(out.nextAction.executionDate, "2025-01-06"); assert.equal(out.state, "LOCKED_STOP");
});
test("stop exit uses next open and includes the overnight gap", () => {
  const triggered = transitionDay(invested(), { date: "2025-01-03", prices: { AAA: point("2025-01-03", 80), BBB: point("2025-01-03", 100) }, qqqHistoryThroughClose: qqqRecovery, nextSessionDate: "2025-01-06" });
  const exited = transitionDay(triggered, { date: "2025-01-06", prices: { AAA: point("2025-01-06", 70, 70), BBB: point("2025-01-06", 90, 90) }, qqqHistoryThroughClose: qqqRecovery, nextSessionDate: "2025-01-07" });
  assert.ok(exited.cash < .8); assert.equal(exited.currentPositions.length, 0);
});
test("portfolio -15% circuit schedules next-open exit", () => {
  const out = transitionDay(invested(), { date: "2025-01-03", prices: { AAA: point("2025-01-03", 84), BBB: point("2025-01-03", 84) }, qqqHistoryThroughClose: qqqRecovery, nextSessionDate: "2025-01-06" });
  assert.equal(out.state, "LOCKED_CIRCUIT"); assert.equal(out.nextAction.type, "SELL_ALL_NEXT_OPEN");
});
test("recovery does not re-enter after 9 closes", () => {
  let state: EngineState = { ...initialEngineState(), state: "WAITING_RECOVERY", marketRiskOn: true, pendingSignal: baseSignal };
  for (let day = 1; day <= 9; day++) state = transitionDay(state, { date: `2025-02-${String(day).padStart(2, "0")}`, prices: {}, qqqHistoryThroughClose: qqqRecovery, nextSessionDate: `2025-02-${String(day + 1).padStart(2, "0")}` });
  assert.equal(state.currentPositions.length, 0); assert.equal(state.state, "WAITING_RECOVERY");
});
test("10th recovery close schedules, but does not perform, entry", () => {
  let state: EngineState = { ...initialEngineState(), state: "WAITING_RECOVERY", marketRiskOn: true, pendingSignal: baseSignal };
  for (let day = 1; day <= 10; day++) state = transitionDay(state, { date: `2025-02-${String(day).padStart(2, "0")}`, prices: {}, qqqHistoryThroughClose: qqqRecovery, nextSessionDate: `2025-02-${String(day + 1).padStart(2, "0")}` });
  assert.equal(state.currentPositions.length, 0); assert.equal(state.state, "READY_NEXT_OPEN");
});
test("recovery enters at the next open and charges entry cost", () => {
  let state: EngineState = { ...initialEngineState(), state: "WAITING_RECOVERY", marketRiskOn: true, pendingSignal: baseSignal };
  for (let day = 1; day <= 10; day++) state = transitionDay(state, { date: `2025-02-${String(day).padStart(2, "0")}`, prices: {}, qqqHistoryThroughClose: qqqRecovery, nextSessionDate: `2025-02-${String(day + 1).padStart(2, "0")}` });
  state = transitionDay(state, { date: "2025-02-11", prices: { AAA: point("2025-02-11", 100, 100), BBB: point("2025-02-11", 100, 100) }, qqqHistoryThroughClose: qqqRecovery, nextSessionDate: "2025-02-12" });
  assert.equal(state.currentPositions.length, 2); assert.ok(state.currentEquity < 1);
});
test("QQQ monthly RiskOff creates a persistent market lock", () => {
  const off = { ...baseSignal, marketRiskOn: false, selectedSymbols: [], targetWeights: [], allocationMode: "CASH" as const };
  const out = transitionDay(invested(), { date: "2025-01-31", prices: { AAA: point("2025-01-31", 100), BBB: point("2025-01-31", 100) }, qqqHistoryThroughClose: qqqRecovery, monthlySignal: off, nextSessionDate: "2025-02-03" });
  assert.equal(out.state, "LOCKED_MARKET"); assert.equal(out.nextAction.type, "SELL_ALL_NEXT_OPEN");
});
