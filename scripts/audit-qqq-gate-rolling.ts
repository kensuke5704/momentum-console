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

const START = "2020-01-01";
const END = "2025-12-31";

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

function noGateCurve(histories: Record<string, PricePoint[]>, universeHistory: UniverseMonth[]) {
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
    const symbols = new Set(["QQQ", ...state.currentPositions.map((p) => p.symbol), ...(state.pendingSignal?.selectedSymbols ?? []), ...state.nextAction.symbols, ...(signal?.selectedSymbols ?? [])]);
    const prices = Object.fromEntries([...symbols].map((symbol) => [symbol, priceMaps[symbol]?.get(date)]));
    const idx = qqqIndex.get(date) ?? 0;
    state = transitionDay(state, { date, prices, qqqHistoryThroughClose: qqq.slice(0, idx + 1), monthlySignal: signal, nextSessionDate }, PRODUCTION_STRATEGY);
    curve.push({ date, equity: state.currentEquity, drawdown: state.drawdown });
  }
  return curve;
}

function normalizedWindow(curve: EquityPoint[], startYear: number, years: number) {
  const start = `${startYear}-01-01`;
  const end = `${startYear + years - 1}-12-31`;
  const before = curve.filter((p) => p.date < start).at(-1)?.equity ?? 1;
  const rows = curve.filter((p) => p.date >= start && p.date <= end);
  const normalized = rows.map((p) => ({ date: p.date, equity: p.equity / before, drawdown: 0 }));
  let peak = 1;
  for (const p of normalized) {
    peak = Math.max(peak, p.equity);
    p.drawdown = p.equity / peak - 1;
  }
  return { start, end, stats: performanceStats(normalized) };
}

async function main() {
  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as MarketDataFile;
  const universe = JSON.parse(await readFile(resolve("data/universe-history.json"), "utf8")) as UniverseFile;
  const histories = Object.fromEntries(Object.entries(market.histories ?? {}).map(([s, pts]) => [s, pts.filter((p) => p.date <= END)]));
  const universeHistory = universe.history.filter((u) => u.asOf >= START && u.asOf <= END);
  const noGate = noGateCurve(histories, universeHistory);
  const tenM = runStrategySimulation({ histories, universeHistory, config: PRODUCTION_STRATEGY }).backtest.equityCurve.filter((p) => p.date <= END);
  const full = {
    NO_GATE: performanceStats(noGate),
    TEN_M: performanceStats(tenM),
  };
  const windows = [3, 4].flatMap((years) => {
    const out = [];
    for (let startYear = 2020; startYear + years - 1 <= 2025; startYear++) {
      const a = normalizedWindow(noGate, startYear, years);
      const b = normalizedWindow(tenM, startYear, years);
      out.push({ years, startYear, endYear: startYear + years - 1, noGate: a.stats, tenM: b.stats, cagrDifference: a.stats.cagr - b.stats.cagr });
    }
    return out;
  });
  const output = { generatedAt: new Date().toISOString(), period: { start: START, end: END }, full, windows };
  const out = resolve("data/research/qqq-gate-rolling.json");
  await mkdir(dirname(out), { recursive: true });
  await writeFile(out, `${JSON.stringify(output, null, 2)}\n`);
  console.log(JSON.stringify(output, null, 2));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
