import { readFile, mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { performanceStats, runStrategySimulation } from "../src/lib/backtest";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import { initialEngineState, transitionDay } from "../src/lib/strategy/state-machine";
import { nextUsTradingSession } from "../src/lib/trading-calendar";
import type { EquityPoint, MonthlySignal, PricePoint, UniverseMonth } from "../src/lib/types";

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

function noGateSignal(signal: MonthlySignal): MonthlySignal {
  const eligible = signal.candidates
    .filter((row) => row.eligible && row.score !== null)
    .sort((a, b) => (a.rank ?? 9999) - (b.rank ?? 9999));
  const selected = eligible.slice(0, PRODUCTION_STRATEGY.selection.topN);
  if (selected.length !== PRODUCTION_STRATEGY.selection.topN) {
    return { ...signal, marketRiskOn: true, selectedSymbols: [], targetWeights: [], zGap: null, allocationMode: "CASH" };
  }
  const scores = eligible.map((row) => row.score as number);
  const mean = scores.reduce((sum, value) => sum + value, 0) / scores.length;
  const dispersion = Math.sqrt(scores.reduce((sum, value) => sum + (value - mean) ** 2, 0) / scores.length);
  const zGap = dispersion > 0 ? ((selected[0].score as number) - (selected[1].score as number)) / dispersion : 0;
  const concentrated = zGap >= PRODUCTION_STRATEGY.allocation.concentrationZGap;
  const top1 = Math.min(
    PRODUCTION_STRATEGY.allocation.maxTop1Weight,
    concentrated ? PRODUCTION_STRATEGY.allocation.concentratedTop1Weight : PRODUCTION_STRATEGY.allocation.baseTop1Weight,
  );
  return {
    ...signal,
    marketRiskOn: true,
    selectedSymbols: selected.map((row) => row.symbol),
    targetWeights: [top1, 1 - top1],
    zGap,
    allocationMode: concentrated ? "70/30" : "50/50",
  };
}

function buildNoGate(histories: Record<string, PricePoint[]>, universeHistory: UniverseMonth[]) {
  const qqq = [...(histories.QQQ ?? [])].sort((a, b) => a.date.localeCompare(b.date));
  const tradingDates = qqq.map((p) => p.date).filter((date) => date >= START && date <= END);
  const qqqIndex = new Map(qqq.map((p, i) => [p.date, i]));
  const priceMaps = Object.fromEntries(Object.entries(histories).map(([symbol, points]) => [symbol, new Map(points.map((p) => [p.date, p]))]));
  const universeByDate = new Map(universeHistory.map((u) => [u.asOf, u]));
  let state = initialEngineState(PRODUCTION_STRATEGY);
  const curve: EquityPoint[] = [];

  for (let i = 0; i < tradingDates.length; i++) {
    const date = tradingDates[i];
    const nextSessionDate = tradingDates[i + 1] ?? nextUsTradingSession(date);
    const universe = universeByDate.get(date);
    const rawSignal = universe ? buildMonthlySignal({ universe, histories, qqq, nextSessionDate, config: PRODUCTION_STRATEGY }) : null;
    const signal = rawSignal ? noGateSignal(rawSignal) : null;
    const symbols = new Set([
      "QQQ",
      ...state.currentPositions.map((p) => p.symbol),
      ...(state.pendingSignal?.selectedSymbols ?? []),
      ...state.nextAction.symbols,
      ...(signal?.selectedSymbols ?? []),
    ]);
    const prices = Object.fromEntries([...symbols].map((symbol) => [symbol, priceMaps[symbol]?.get(date)]));
    const idx = qqqIndex.get(date) ?? 0;
    state = transitionDay(state, {
      date,
      prices,
      qqqHistoryThroughClose: qqq.slice(0, idx + 1),
      monthlySignal: signal,
      nextSessionDate,
    }, PRODUCTION_STRATEGY);
    curve.push({ date, equity: state.currentEquity, drawdown: state.drawdown });
  }
  return { curve, events: state.events as Event[], stats: performanceStats(curve) };
}

function summarize(label: "NO_GATE" | "10M", curve: EquityPoint[], events: Event[], stats: ReturnType<typeof performanceStats>) {
  const years = Array.from({ length: 7 }, (_, i) => 2020 + i);
  return {
    label,
    stats,
    yearly: years.map((year) => {
      const yearEvents = events.filter((e) => e.date.startsWith(`${year}-`));
      return {
        year,
        return: yearReturn(curve, year),
        exposure: annualExposure(curve, events, year),
        entries: yearEvents.filter((e) => e.type === "ENTRY_OPEN").length,
        exits: yearEvents.filter((e) => e.type === "EXIT_OPEN").length,
        stopExits: yearEvents.filter((e) => e.type === "EXIT_OPEN" && e.reason.includes("stop")).length,
        circuitExits: yearEvents.filter((e) => e.type === "EXIT_OPEN" && e.reason.includes("circuit")).length,
      };
    }),
  };
}

async function main() {
  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as MarketDataFile;
  const universe = JSON.parse(await readFile(resolve("data/universe-history.json"), "utf8")) as UniverseFile;
  const histories = Object.fromEntries(Object.entries(market.histories ?? {}).map(([s, pts]) => [s, pts.filter((p) => p.date <= END)]));
  const universeHistory = universe.history.filter((u) => u.asOf >= START && u.asOf <= END);

  const noGate = buildNoGate(histories, universeHistory);
  const prod = runStrategySimulation({ histories, universeHistory, config: PRODUCTION_STRATEGY });
  const output = {
    generatedAt: new Date().toISOString(),
    period: { start: START, end: END },
    results: [
      summarize("NO_GATE", noGate.curve, noGate.events, noGate.stats),
      summarize("10M", prod.backtest.equityCurve, prod.backtest.events as Event[], prod.backtest.stats),
    ],
  };
  const out = resolve("data/research/qqq-gate-yearly.json");
  await mkdir(dirname(out), { recursive: true });
  await writeFile(out, `${JSON.stringify(output, null, 2)}\n`);
  console.log(JSON.stringify(output, null, 2));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
