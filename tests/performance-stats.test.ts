import assert from "node:assert/strict";
import test from "node:test";
import { performanceStats } from "../src/lib/backtest";
import type { EquityPoint } from "../src/lib/types";

test("performanceStats uses global equity peak rather than engine episode drawdown", () => {
  const curve: EquityPoint[] = [
    { date: "2026-01-01", equity: 1.0, drawdown: 0 },
    { date: "2026-01-02", equity: 1.5, drawdown: 0 },
    { date: "2026-01-03", equity: 1.2, drawdown: -0.2 },
    // Simulate a recovery reset: engine drawdown is reset even though equity has not regained its global peak.
    { date: "2026-01-04", equity: 1.25, drawdown: 0 },
    { date: "2026-01-05", equity: 1.1, drawdown: -0.12 },
  ];

  const stats = performanceStats(curve);
  assert.ok(Math.abs(stats.maxDrawdown - (1.1 / 1.5 - 1)) < 1e-12);
});
