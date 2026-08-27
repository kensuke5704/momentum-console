import { readFile, mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { performanceStats, runStrategySimulation } from "../src/lib/backtest";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import { initialEngineState, transitionDay } from "../src/lib/strategy/state-machine";
import { nextUsTradingSession } from "../src/lib/trading-calendar";
import type { EquityPoint, MonthlySignal, PricePoint, StrategyConfig, UniverseMonth } from "../src/lib/types";

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
    label: `${months}M`,
    months,
    stats: simulation.backtest.stats,
    return2022: yearReturn(simulation.backtest.equityCurve, 2022),
    entries2022: entries2022.length,
    exits2022: exits2022.length,
    events2022,
    monthlyGate2022: monthly,
  };
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

function statsNoGate(histories: Record<string, PricePoint[]>, universeHistory: UniverseMonth[]) {
  const filteredHistories = Object.fromEntries(Object.entries(histories).map(([s, pts]) => [s, pts.filter((p) => p.date <= END)]));
  const qqq = [...(filteredHistories.QQQ ?? [])].sort((a, b) => a.date.localeCompare(b.date));
  const tradingDates = qqq.map((p) => p.date).filter((date) => date >= START && date <= END);
  const qqqIndex = new Map(qqq.map((p, i) => [p.date, i]));
  const priceMaps = Object.fromEntries(Object.entries(filteredHistories).map(([symbol, points]) => [symbol, new Map(points.map((p) => [p.date, p]))]));
  const universeByDate = new Map(universeHistory.map((u) => [u.asOf, u]));
  let state = initialEngineState(PRODUCTION_STRATEGY);
  const curve: EquityPoint[] = [];

  for (let i = 0; i < tradingDates.length; i++) {
    const date = tradingDates[i];
    const nextSessionDate = tradingDates[i + 1] ?? nextUsTradingSession(date);
    const universe = universeByDate.get(date);
    const rawSignal = universe ? buildMonthlySignal({ universe, histories: filteredHistories, qqq, nextSessionDate, config: PRODUCTION_STRATEGY }) : null;
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

  const events2022 = state.events.filter((e) => e.date.startsWith("2022-"));
  return {
    label: "NO_GATE",
    months: null,
    stats: performanceStats(curve),
    return2022: yearReturn(curve, 2022),
    entries2022: events2022.filter((e) => e.type === "ENTRY_OPEN").length,
    exits2022: events2022.filter((e) => e.type === "EXIT_OPEN").length,
    events2022,
    monthlyGate2022: null,
  };
}

async function main() {
  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as MarketDataFile;
  const universe = JSON.parse(await readFile(resolve("data/universe-history.json"), "utf8")) as UniverseFile;
  const histories = market.histories ?? {};
  const universeHistory = universe.history.filter((u) => u.asOf >= START && u.asOf <= END);
  const results = [statsNoGate(histories, universeHistory), ...WINDOWS.map((months) => statsForWindow(histories, universeHistory, months))];
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
