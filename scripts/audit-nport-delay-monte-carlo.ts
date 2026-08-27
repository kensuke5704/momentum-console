import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { performanceStats, runStrategySimulation } from "../src/lib/backtest";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import { initialEngineState, transitionDay } from "../src/lib/strategy/state-machine";
import type { EquityPoint, MonthlySignal, NportFiling, PerformanceStats, PricePoint, UniverseMonth } from "../src/lib/types";
import { buildPointInTimeUniverse } from "../src/lib/universe/universe";
import { fetchHistories, fetchYahooHistory } from "../src/lib/yahoo";

const START = "2020-01-01";
const PATHS = 10_000;
const MAX_DELAY = 3;
const SEED = 20260827;

function rng(seed: number) {
  let value = seed >>> 0;
  return () => {
    value = (value + 0x6d2b79f5) >>> 0;
    let t = value;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function previousQuarterEnd(date: string): string {
  const year = Number(date.slice(0, 4));
  const month = Number(date.slice(5, 7));
  const q = Math.floor((month - 1) / 3) + 1;
  if (q === 1) return `${year - 1}-12-31`;
  const endMonth = (q - 1) * 3;
  const lastDay = new Date(Date.UTC(year, endMonth, 0)).getUTCDate();
  return `${year}-${String(endMonth).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`;
}

function isQuarterEndMonth(month: string): boolean {
  return [3, 6, 9, 12].includes(Number(month.slice(5, 7)));
}

function buildFallbackHistory(filings: NportFiling[], months: Array<[string, string]>): UniverseMonth[] {
  const out: UniverseMonth[] = [];
  let previous: UniverseMonth | null = null;
  for (const [signalMonth, asOf] of months) {
    const cutoff = previousQuarterEnd(asOf);
    const available = filings.filter((f) => f.filingDate <= cutoff);
    const current = buildPointInTimeUniverse(available, signalMonth, asOf, previous);
    out.push(current);
    previous = current;
  }
  return out;
}

function quantile(sorted: number[], p: number): number {
  if (!sorted.length) return 0;
  const position = (sorted.length - 1) * p;
  const lo = Math.floor(position), hi = Math.ceil(position);
  if (lo === hi) return sorted[lo];
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (position - lo);
}

function summarize(values: number[]) {
  const sorted = [...values].sort((a, b) => a - b);
  const mean = values.reduce((sum, value) => sum + value, 0) / Math.max(1, values.length);
  return { min: sorted[0] ?? 0, p05: quantile(sorted, 0.05), p25: quantile(sorted, 0.25), median: quantile(sorted, 0.5), mean, p75: quantile(sorted, 0.75), p95: quantile(sorted, 0.95), max: sorted.at(-1) ?? 0 };
}

function monthlyReturns(curve: EquityPoint[]): number[] {
  const monthEnd = new Map<string, number>();
  for (const point of curve) monthEnd.set(point.date.slice(0, 7), point.equity);
  let prior = 1;
  const returns: number[] = [];
  for (const [, equity] of [...monthEnd].sort(([a], [b]) => a.localeCompare(b))) {
    returns.push(equity / prior - 1);
    prior = equity;
  }
  return returns;
}

function histogram(values: number[], width = 0.05) {
  const minEdge = Math.floor(Math.min(...values) / width) * width;
  const maxEdge = Math.ceil(Math.max(...values) / width) * width;
  const bins: Array<{ from: number; to: number; label: string; count: number; probability: number }> = [];
  for (let from = minEdge; from < maxEdge - width / 10; from += width) {
    const to = from + width;
    bins.push({ from, to, label: `${(from * 100).toFixed(0)}%〜${(to * 100).toFixed(0)}%`, count: 0, probability: 0 });
  }
  for (const value of values) {
    const index = Math.min(bins.length - 1, Math.max(0, Math.floor((value - minEdge) / width + 1e-10)));
    bins[index].count += 1;
  }
  for (const bin of bins) bin.probability = bin.count / values.length;
  return bins;
}

async function main() {
  const quarterly = JSON.parse(await readFile(resolve("data/sec-nport/filings.json"), "utf8")) as { filings: NportFiling[] };
  const published = JSON.parse(await readFile(resolve("public/data/universe-history.json"), "utf8")) as { history: UniverseMonth[] };
  const qqq = await fetchYahooHistory("QQQ");
  const monthEnds = new Map<string, string>();
  for (const point of qqq) monthEnds.set(point.date.slice(0, 7), point.date);
  const lastMonth = published.history.at(-1)?.signalMonth ?? "9999-12";
  const months = [...monthEnds].filter(([month]) => month >= "2020-01" && month <= lastMonth).sort(([a], [b]) => a.localeCompare(b)) as Array<[string, string]>;
  const fallbackHistory = buildFallbackHistory(quarterly.filings, months);
  const quarterMonths = months.filter(([month]) => isQuarterEndMonth(month));
  const quarterUniverses = quarterMonths.map(([signalMonth, monthEnd]) => buildPointInTimeUniverse(quarterly.filings.filter((f) => f.filingDate <= monthEnd), signalMonth, monthEnd, null));
  const symbols = [...new Set(["QQQ", "TQQQ", ...published.history.flatMap((m) => m.symbols.map((x) => x.symbol)), ...fallbackHistory.flatMap((m) => m.symbols.map((x) => x.symbol)), ...quarterUniverses.flatMap((m) => m.symbols.map((x) => x.symbol))])];
  console.log(`Fetching histories for ${symbols.length} symbols`);
  const histories = await fetchHistories(symbols, 8);

  const sortedQqq = [...(histories.QQQ ?? [])].sort((a, b) => a.date.localeCompare(b.date));
  const tradingDates = sortedQqq.map((point) => point.date);
  const dateIndex = new Map(tradingDates.map((date, index) => [date, index]));
  const qqqPrefixes = tradingDates.map((_, index) => sortedQqq.slice(0, index + 1));
  const priceMaps = Object.fromEntries(Object.entries(histories).map(([symbol, points]) => [symbol, new Map(points.map((point) => [point.date, point]))]));
  const regularUniverseByDate = new Map(fallbackHistory.map((month) => [month.asOf, month]));
  const regularSignals = new Map<string, MonthlySignal>();
  for (const [date, universe] of regularUniverseByDate) {
    const idx = dateIndex.get(date);
    regularSignals.set(date, buildMonthlySignal({ universe, histories, qqq: sortedQqq, nextSessionDate: idx === undefined ? null : tradingDates[idx + 1] ?? null, config: PRODUCTION_STRATEGY }));
  }

  const extraSignalOptions = quarterMonths.map(([signalMonth, monthEnd]) => {
    const idx = dateIndex.get(monthEnd);
    if (idx === undefined) return null;
    const available = quarterly.filings.filter((f) => f.filingDate <= monthEnd);
    const newUniverse = buildPointInTimeUniverse(available, signalMonth, monthEnd, null);
    const options = Array.from({ length: MAX_DELAY + 1 }, (_, delay) => {
      const receiptDate = tradingDates[idx + delay];
      const executionDate = tradingDates[idx + delay + 1];
      if (!receiptDate || !executionDate) return null;
      const signal = buildMonthlySignal({ universe: newUniverse, histories, qqq: sortedQqq, nextSessionDate: executionDate, config: PRODUCTION_STRATEGY });
      return { delay, receiptDate, signal };
    });
    return { signalMonth, monthEnd, options };
  }).filter((value): value is NonNullable<typeof value> => Boolean(value));

  const baseline = runStrategySimulation({ histories, universeHistory: published.history, config: { ...PRODUCTION_STRATEGY, backtestStart: START } }).backtest;
  const random = rng(SEED);
  const cagrs: number[] = [], maxDrawdowns: number[] = [], vols: number[] = [], calmars: number[] = [], finalEquities: number[] = [], pooledMonthlyReturns: number[] = [];
  const pathDelayCounts = Array.from({ length: MAX_DELAY + 1 }, () => 0);

  for (let path = 0; path < PATHS; path++) {
    const extras = new Map<string, MonthlySignal>();
    for (const quarter of extraSignalOptions) {
      const delay = Math.floor(random() * (MAX_DELAY + 1));
      pathDelayCounts[delay] += 1;
      const option = quarter.options[delay];
      if (option) extras.set(option.receiptDate, option.signal);
    }
    let state = initialEngineState(PRODUCTION_STRATEGY);
    const curve: EquityPoint[] = [];
    for (let index = 0; index < tradingDates.length; index++) {
      const date = tradingDates[index];
      if (date < START) continue;
      const nextSessionDate = tradingDates[index + 1] ?? null;
      const signal = extras.get(date) ?? regularSignals.get(date) ?? null;
      const symbolsNeeded = new Set(["QQQ", ...state.currentPositions.map((position) => position.symbol), ...(state.pendingSignal?.selectedSymbols ?? []), ...state.nextAction.symbols, ...(signal?.selectedSymbols ?? [])]);
      const prices = Object.fromEntries([...symbolsNeeded].map((symbol) => [symbol, priceMaps[symbol]?.get(date)]));
      state = transitionDay(state, { date, prices, qqqHistoryThroughClose: qqqPrefixes[index], monthlySignal: signal, nextSessionDate }, PRODUCTION_STRATEGY);
      state.events = [];
      curve.push({ date, equity: state.currentEquity, drawdown: state.drawdown });
    }
    const stats: PerformanceStats = performanceStats(curve);
    cagrs.push(stats.cagr); maxDrawdowns.push(stats.maxDrawdown); vols.push(stats.annualizedVolatility); finalEquities.push(stats.finalEquity);
    if (stats.calmar !== null) calmars.push(stats.calmar);
    pooledMonthlyReturns.push(...monthlyReturns(curve));
    if ((path + 1) % 1000 === 0) console.log(`Completed ${path + 1}/${PATHS} paths`);
  }

  const monthlySummary = summarize(pooledMonthlyReturns);
  const result = {
    generatedAt: new Date().toISOString(), start: START, paths: PATHS, seed: SEED, maxDelayTradingSessions: MAX_DELAY,
    assumptions: {
      delayDistribution: "Independent discrete uniform delay of 0, 1, 2, or 3 US trading sessions for each quarter-end N-PORT refresh.",
      fallback: "If delayed, the regular month-start rebalance uses the prior valid Universe.",
      delayedActivation: "On receipt, only the Universe changes; Momentum and QQQ gate remain fixed to the prior official month-end close; changed Top2/weights execute next open.",
      transactionCostPerSide: PRODUCTION_STRATEGY.execution.transactionCost,
      caveat: "Historical user upload timestamps do not exist. This is a scenario Monte Carlo. The audited bootstrap starts in 2020 Q1, retaining the same Jan-Mar 2020 limitation as the Production-start comparison."
    },
    baseline: { stats: baseline.stats, monthlyReturns: summarize(monthlyReturns(baseline.equityCurve)) },
    monteCarlo: {
      cagr: summarize(cagrs), maxDrawdown: summarize(maxDrawdowns), annualizedVolatility: summarize(vols), calmar: summarize(calmars), finalEquity: summarize(finalEquities),
      probabilityCagrBelow50Pct: cagrs.filter((value) => value < 0.50).length / PATHS,
      probabilityCagrBelowBaseline: cagrs.filter((value) => value < baseline.stats.cagr).length / PATHS,
      delayCounts: pathDelayCounts,
      monthlyReturns: { summary: monthlySummary, positiveProbability: pooledMonthlyReturns.filter((value) => value > 0).length / pooledMonthlyReturns.length, negativeProbability: pooledMonthlyReturns.filter((value) => value < 0).length / pooledMonthlyReturns.length, zeroProbability: pooledMonthlyReturns.filter((value) => value === 0).length / pooledMonthlyReturns.length, histogram5Pct: histogram(pooledMonthlyReturns, 0.05) }
    }
  };
  await mkdir(resolve("data/research"), { recursive: true });
  await writeFile(resolve("data/research/nport-delay-monte-carlo.json"), `${JSON.stringify(result, null, 2)}\n`);
  console.log("NPORT_DELAY_MONTE_CARLO=" + JSON.stringify(result));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
