import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { emptyForwardOos, OOS_START_DATE, updateForwardOos } from "../src/lib/oos";
import type { BacktestResult, EquityPoint } from "../src/lib/types";

const backtest = (equityCurve: EquityPoint[]): BacktestResult => ({
  strategyId: "momentum-dynamic-2026-08-v1",
  equityCurve,
  stats: { cagr: 0, maxDrawdown: 0, annualizedVolatility: 0, calmar: null, finalEquity: equityCurve.at(-1)?.equity ?? 1 },
  benchmark: null,
  events: [],
});

test("Forward OOS starts on the frozen production date", () => {
  const empty = emptyForwardOos("momentum-dynamic-2026-08-v1");
  assert.equal(empty.startedAt, OOS_START_DATE);
  assert.deepEqual(empty.equityCurve, [{ date: OOS_START_DATE, equity: 1, drawdown: 0 }]);
});

test("Forward OOS uses actual post-start equity and appends without rewriting confirmed dates", () => {
  const first = updateForwardOos(backtest([
    { date: "2026-08-24", equity: 18, drawdown: 0 },
    { date: "2026-08-25", equity: 20, drawdown: 0 },
    { date: "2026-08-26", equity: 22, drawdown: 0 },
  ]));
  assert.equal(first.baselineBacktestEquity, 20);
  assert.deepEqual(first.equityCurve.map((point) => [point.date, point.equity]), [["2026-08-25", 1], ["2026-08-26", 1.1]]);

  const appended = updateForwardOos(backtest([
    { date: "2026-08-25", equity: 20, drawdown: 0 },
    { date: "2026-08-26", equity: 99, drawdown: 0 },
    { date: "2026-08-27", equity: 24, drawdown: 0 },
  ]), first);
  assert.equal(appended.equityCurve.find((point) => point.date === "2026-08-26")?.equity, 1.1);
  assert.equal(appended.equityCurve.find((point) => point.date === "2026-08-27")?.equity, 1.2);
  assert.equal(appended.asOf, "2026-08-27");
});

test("committed backtest snapshot is frozen on the OOS start date", async () => {
  const frozen = JSON.parse(await readFile("public/data/backtest-frozen.json", "utf8")) as { frozenAt: string; backtest?: BacktestResult };
  assert.equal(frozen.frozenAt, OOS_START_DATE);
  assert.ok(frozen.backtest?.equityCurve.length);
});
