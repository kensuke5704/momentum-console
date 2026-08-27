import { readFile, mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { runStrategySimulation } from "../src/lib/backtest";
import type { PricePoint, StrategyConfig, UniverseMonth, EquityPoint } from "../src/lib/types";

type MarketDataFile = { histories?: Record<string, PricePoint[]> };
type UniverseFile = { history: UniverseMonth[] };

const START = "2020-01-01";
const END = "2026-08-25";
const WINDOWS = [6, 8, 10, 12] as const;

function yearReturn(curve: EquityPoint[], year: number) {
  const rows = curve.filter((p) => p.date.startsWith(`${year}-`));
  if (!rows.length) return null;
  const before = curve.filter((p) => p.date < `${year}-01-01`).at(-1)?.equity ?? 1;
  return rows.at(-1)!.equity / before - 1;
}

function statsForWindow(histories: Record<string, PricePoint[]>, universeHistory: UniverseMonth[], months: number) {
  const config: StrategyConfig = {
    ...PRODUCTION_STRATEGY,
    market: { ...PRODUCTION_STRATEGY.market, qqqMonthlyMaMonths: months },
  };
  const filteredHistories = Object.fromEntries(Object.entries(histories).map(([s, pts]) => [s, pts.filter((p) => p.date <= END)]));
  const simulation = runStrategySimulation({ histories: filteredHistories, universeHistory, config });
  const events2022 = simulation.backtest.events.filter((e) => e.date.startsWith("2022-"));
  const entries2022 = events2022.filter((e) => e.type === "ENTRY_OPEN");
  const exits2022 = events2022.filter((e) => e.type === "EXIT_OPEN");
  const qqq = filteredHistories.QQQ ?? [];
  const monthly = universeHistory.filter((u) => u.asOf >= "2022-01-01" && u.asOf <= "2022-12-31").map((u) => {
    const points = qqq.filter((p) => p.date <= u.asOf);
    const byMonth = new Map<string, PricePoint>();
    for (const p of points) byMonth.set(p.date.slice(0, 7), p);
    const closes = [...byMonth.values()];
    const window = closes.slice(-months);
    const close = window.at(-1)?.close ?? null;
    const ma = window.length === months ? window.reduce((sum, p) => sum + p.close, 0) / months : null;
    return { date: u.asOf, close, ma, riskOn: close !== null && ma !== null && close > ma };
  });
  return {
    months,
    stats: simulation.backtest.stats,
    return2022: yearReturn(simulation.backtest.equityCurve, 2022),
    entries2022: entries2022.length,
    exits2022: exits2022.length,
    events2022,
    monthlyGate2022: monthly,
  };
}

async function main() {
  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as MarketDataFile;
  const universe = JSON.parse(await readFile(resolve("data/universe-history.json"), "utf8")) as UniverseFile;
  const histories = market.histories ?? {};
  const universeHistory = universe.history.filter((u) => u.asOf >= START && u.asOf <= END);
  const results = WINDOWS.map((months) => statsForWindow(histories, universeHistory, months));
  const output = {
    generatedAt: new Date().toISOString(),
    period: { start: START, end: END },
    frozenProductionWindow: PRODUCTION_STRATEGY.market.qqqMonthlyMaMonths,
    invariantParameters: {
      momentum: PRODUCTION_STRATEGY.momentum,
      selection: PRODUCTION_STRATEGY.selection,
      allocation: PRODUCTION_STRATEGY.allocation,
      risk: PRODUCTION_STRATEGY.risk,
      recovery: PRODUCTION_STRATEGY.recovery,
      execution: PRODUCTION_STRATEGY.execution,
    },
    results,
  };
  const out = resolve("data/research/qqq-ma-sensitivity.json");
  await mkdir(dirname(out), { recursive: true });
  await writeFile(out, `${JSON.stringify(output, null, 2)}\n`);
  console.log(JSON.stringify(output, null, 2));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
