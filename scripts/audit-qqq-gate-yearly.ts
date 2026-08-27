import { readFile, mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { runStrategySimulation } from "../src/lib/backtest";
import type { EquityPoint, PricePoint, StrategyConfig, UniverseMonth } from "../src/lib/types";

type MarketDataFile = { histories?: Record<string, PricePoint[]> };
type UniverseFile = { history: UniverseMonth[] };
type Event = { date: string; type: string; symbols: string[]; reason: string };

const START = "2020-01-01";
const END = "2026-08-25";

function yearReturn(curve: EquityPoint[], year: number) {
  const rows = curve.filter((p) => p.date.startsWith(`${year}-`));
  if (!rows.length) return null;
  const before = curve.filter((p) => p.date < `${year}-01-01`).at(-1)?.equity ?? 1;
  return rows.at(-1)!.equity / before - 1;
}

function annualExposure(curve: EquityPoint[], events: Event[], year: number) {
  const dates = curve.filter((p) => p.date.startsWith(`${year}-`)).map((p) => p.date);
  if (!dates.length) return null;
  const orderedEvents = [...events].sort((a, b) => a.date.localeCompare(b.date));
  let invested = false;
  let eventIndex = 0;
  while (eventIndex < orderedEvents.length && orderedEvents[eventIndex].date < `${year}-01-01`) {
    const e = orderedEvents[eventIndex++];
    if (e.type === "EXIT_OPEN") invested = false;
    if (e.type === "ENTRY_OPEN") invested = true;
  }
  let investedDays = 0;
  for (const date of dates) {
    while (eventIndex < orderedEvents.length && orderedEvents[eventIndex].date === date) {
      const e = orderedEvents[eventIndex++];
      if (e.type === "EXIT_OPEN") invested = false;
      if (e.type === "ENTRY_OPEN") invested = true;
    }
    if (invested) investedDays += 1;
  }
  return { tradingDays: dates.length, investedDays, exposure: investedDays / dates.length };
}

function summarize(histories: Record<string, PricePoint[]>, universeHistory: UniverseMonth[], label: "NO_GATE" | "10M") {
  let config: StrategyConfig = PRODUCTION_STRATEGY;
  if (label === "NO_GATE") {
    config = { ...PRODUCTION_STRATEGY, market: { ...PRODUCTION_STRATEGY.market, qqqMonthlyMaMonths: 1 } };
    const qqq = histories.QQQ ?? [];
    histories = { ...histories, QQQ: qqq.map((p, i) => ({ ...p, close: p.close + i * 1e-12 })) };
  }
  const simulation = runStrategySimulation({ histories, universeHistory, config });
  const events = simulation.backtest.events as Event[];
  const years = Array.from({ length: 7 }, (_, i) => 2020 + i);
  return {
    label,
    stats: simulation.backtest.stats,
    yearly: years.map((year) => {
      const yearEvents = events.filter((e) => e.date.startsWith(`${year}-`));
      return {
        year,
        return: yearReturn(simulation.backtest.equityCurve, year),
        exposure: annualExposure(simulation.backtest.equityCurve, events, year),
        entries: yearEvents.filter((e) => e.type === "ENTRY_OPEN").length,
        exits: yearEvents.filter((e) => e.type === "EXIT_OPEN").length,
        stopExits: yearEvents.filter((e) => e.type === "EXIT_OPEN" && e.reason.includes("stop")).length,
        circuitExits: yearEvents.filter((e) => e.type === "EXIT_OPEN" && e.reason.includes("circuit")).length,
        events: yearEvents,
      };
    }),
  };
}

async function main() {
  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as MarketDataFile;
  const universe = JSON.parse(await readFile(resolve("data/universe-history.json"), "utf8")) as UniverseFile;
  const histories = Object.fromEntries(Object.entries(market.histories ?? {}).map(([s, pts]) => [s, pts.filter((p) => p.date <= END)]));
  const universeHistory = universe.history.filter((u) => u.asOf >= START && u.asOf <= END);
  const output = {
    generatedAt: new Date().toISOString(),
    period: { start: START, end: END },
    note: "NO_GATE control uses a 1-month gate with an epsilon-increasing QQQ close so the monthly gate is always risk-on while preserving daily returns to numerical precision.",
    results: [summarize(histories, universeHistory, "NO_GATE"), summarize(histories, universeHistory, "10M")],
  };
  const out = resolve("data/research/qqq-gate-yearly.json");
  await mkdir(dirname(out), { recursive: true });
  await writeFile(out, `${JSON.stringify(output, null, 2)}\n`);
  console.log(JSON.stringify(output, null, 2));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
