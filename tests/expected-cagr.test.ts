import assert from "node:assert/strict";
import test from "node:test";
import { buildExpectedCagrOverlay, EXPECTED_CAGR_MODEL } from "../src/lib/expected-cagr";

test("expected CAGR bands start from the same equity as the backtest", () => {
  const chart = buildExpectedCagrOverlay([
    { date: "2020-01-02", equity: 1, drawdown: 0 },
    { date: "2020-01-03", equity: 1.01, drawdown: 0 },
  ], EXPECTED_CAGR_MODEL);
  assert.deepEqual(chart[0].central50, [1, 1]);
  assert.deepEqual(chart[0].central90, [1, 1]);
  assert.equal(chart[0].expected, 1);
});

test("expected CAGR bands preserve the research quantile ordering", () => {
  const chart = buildExpectedCagrOverlay([
    { date: "2020-01-02", equity: 1, drawdown: 0 },
    { date: "2021-01-02", equity: 1.2, drawdown: 0 },
  ], EXPECTED_CAGR_MODEL);
  const last = chart.at(-1)!;
  assert.ok(last.central90[0] < last.central50[0]);
  assert.ok(last.central50[0] < last.expected);
  assert.ok(last.expected < last.central50[1]);
  assert.ok(last.central50[1] < last.central90[1]);
});
