import assert from "node:assert/strict";
import test from "node:test";
import { buildMonthlyReturnDistribution } from "../src/lib/monthly-returns";
import type { EquityPoint } from "../src/lib/types";

const point = (date: string, equity: number): EquityPoint => ({ date, equity, drawdown: 0 });

test("monthly return distribution uses the last observed equity in each month", () => {
  const result = buildMonthlyReturnDistribution([
    point("2026-01-02", 1),
    point("2026-01-30", 1.1),
    point("2026-02-10", 1.2),
    point("2026-02-27", 1.21),
    point("2026-03-31", 1.089),
  ]);
  assert.equal(result.months, 2);
  assert.ok(Math.abs(result.returns[0] - 0.1) < 1e-12);
  assert.ok(Math.abs(result.returns[1] + 0.1) < 1e-12);
  assert.equal(result.negativeProbability, 0.5);
  assert.equal(result.positiveProbability, 0.5);
  assert.equal(result.zeroProbability, 0);
  assert.ok(Math.abs(result.histogram5Pct.reduce((sum, bin) => sum + bin.probability, 0) - 1) < 1e-12);
});

test("exact zero monthly returns occupy one dedicated 0% bin", () => {
  const result = buildMonthlyReturnDistribution([
    point("2026-01-30", 1),
    point("2026-02-27", 1),
    point("2026-03-31", 1.04),
    point("2026-04-30", 0.988),
  ]);
  const zeroBins = result.histogram5Pct.filter((bin) => bin.label === "0%");
  assert.equal(zeroBins.length, 1);
  assert.equal(zeroBins[0].count, 1);
  assert.equal(result.zeroProbability, 1 / 3);
  assert.ok(result.histogram5Pct.some((bin) => bin.label === ">0%–5%"));
  assert.ok(result.histogram5Pct.some((bin) => bin.label === "-5%–<0%"));
  assert.equal(result.histogram5Pct.reduce((sum, bin) => sum + bin.count, 0), 3);
});

test("empty or single-month equity curves do not invent a monthly return", () => {
  assert.equal(buildMonthlyReturnDistribution([]).months, 0);
  assert.equal(buildMonthlyReturnDistribution([point("2026-01-30", 1)]).months, 0);
});
