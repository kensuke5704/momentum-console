import assert from "node:assert/strict";
import test from "node:test";
import { buildExpectedCagrModel, buildExpectedCagrOverlay } from "../src/lib/expected-cagr";
import type { EquityPoint, ExpectedCagrModel } from "../src/lib/types";

const model: ExpectedCagrModel = {
  generatedAt: "2026-08-30T00:00:00.000Z",
  sourceRun: "test",
  strategyId: "fixed60-test",
  method: "test",
  sample: { start: "2020-01-02", end: "2021-01-02", tradingDays: 2, months: 13 },
  estimate: { point: 0.4, central50: [0.3, 0.5], central90: [0.1, 0.8] },
};

test("expected CAGR bands start from the same equity as the backtest", () => {
  const chart = buildExpectedCagrOverlay([
    { date: "2020-01-02", equity: 1, drawdown: 0 },
    { date: "2020-01-03", equity: 1.01, drawdown: 0 },
  ], model);
  assert.deepEqual(chart[0].central50, [1, 1]);
  assert.deepEqual(chart[0].central90, [1, 1]);
  assert.equal(chart[0].expected, 1);
});

test("expected CAGR bands preserve quantile ordering", () => {
  const chart = buildExpectedCagrOverlay([
    { date: "2020-01-02", equity: 1, drawdown: 0 },
    { date: "2021-01-02", equity: 1.2, drawdown: 0 },
  ], model);
  const last = chart.at(-1)!;
  assert.ok(last.central90[0] < last.central50[0]);
  assert.ok(last.central50[0] < last.expected);
  assert.ok(last.expected < last.central50[1]);
  assert.ok(last.central50[1] < last.central90[1]);
});

test("CAGR model is deterministically rebuilt from the displayed equity curve", () => {
  let equity = 1;
  const curve: EquityPoint[] = Array.from({ length: 180 }, (_, index) => {
    if (index > 0) equity *= 1 + ([0.012, -0.006, 0.004, 0.001, -0.002][index % 5]);
    const day = new Date(Date.UTC(2025, 0, 1 + index));
    return { date: day.toISOString().slice(0, 10), equity, drawdown: 0 };
  });
  const first = buildExpectedCagrModel(curve, "fixed60-test")!;
  const second = buildExpectedCagrModel(curve, "fixed60-test")!;
  assert.equal(first.strategyId, "fixed60-test");
  assert.deepEqual(first.estimate, second.estimate);
  assert.ok(first.estimate.central90[0] <= first.estimate.central50[0]);
  assert.ok(first.estimate.central50[0] <= first.estimate.point);
  assert.ok(first.estimate.point <= first.estimate.central50[1]);
  assert.ok(first.estimate.central50[1] <= first.estimate.central90[1]);
});
