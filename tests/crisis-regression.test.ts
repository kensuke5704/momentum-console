import assert from "node:assert/strict";
import test from "node:test";
import { initialEngineState, transitionDay, type EngineState } from "../src/lib/strategy/state-machine";
import type { PricePoint } from "../src/lib/types";

const qqq = Array.from({ length: 120 }, (_, index): PricePoint => ({ date: `Q${index}`, open: 100 + index, close: 100 + index }));
const cases = [
  { name: "Dot-com style", closes: [92, 83.5, 79], gate: -.35 },
  { name: "GFC style", closes: [91, 83, 78], gate: -.35 },
  { name: "COVID", closes: [90, 83, 77], gate: -.30 },
  { name: "2022 Bear", closes: [94, 88, 82], gate: -.30 },
] as const;

for (const scenario of cases) test(`${scenario.name} structural drawdown stays inside the CI hard gate`, () => {
  let state: EngineState = { ...initialEngineState(), state: "INVESTED", marketRiskOn: true, cash: 0, currentPositions: [
    { symbol: "AAA", shares: .005, entryPrice: 100, targetWeight: .5, currentPrice: 100, stopLevel: 82.5 },
    { symbol: "BBB", shares: .005, entryPrice: 100, targetWeight: .5, currentPrice: 100, stopLevel: 82.5 },
  ], currentEquity: 1, portfolioPeak: 1, nextAction: { type: "HOLD", executionDate: null, symbols: ["AAA", "BBB"], targetWeights: [.5, .5], reason: "stress" } };
  let worst = 0;
  scenario.closes.forEach((close, index) => {
    const date = `D${index}`;
    state = transitionDay(state, { date, prices: { AAA: { date, open: index === 2 ? close - 3 : close, close }, BBB: { date, open: index === 2 ? close - 3 : close, close } }, qqqHistoryThroughClose: qqq, nextSessionDate: `D${index + 1}` });
    worst = Math.min(worst, state.drawdown);
  });
  assert.ok(worst > scenario.gate, `${scenario.name}: ${worst} breached ${scenario.gate}`);
});
