import { mkdir, writeFile } from "node:fs/promises";
import { buildDashboard } from "../src/lib/momentum";
import { TICKERS, DEFAULT_STRATEGY } from "../src/lib/config";
import { fetchHistories } from "../src/lib/yahoo";
import type { DashboardPayload, StrategyConfig } from "../src/lib/types";

type Weights = StrategyConfig["weights"];
type CapVariant = {
  key: string;
  apply: (s: StrategyConfig) => void;
};
type Spec = {
  key: string;
  topN: number;
  qqqMaMonths: number;
  surgeLimit: number;
  weights: Weights;
  capKey: string;
};
type Summary = Spec & {
  mode: "standard" | "fixed10";
  minPositions?: number;
  cagr: number;
  maxDrawdown: number;
  annualizedVolatility: number;
  finalEquity: number;
  averageMonthlyReturn: number;
  calmar: number;
  yearlyReturns: Record<string, number>;
  worstYearReturn: number;
  completedMonths: number;
  cashMonths: number;
  insufficientMonths: number;
  partialMonths?: number;
  fullInvestMonths?: number;
  avgInvestedFraction?: number;
};

function cloneStrategy(): StrategyConfig {
  return {
    ...DEFAULT_STRATEGY,
    weights: { ...DEFAULT_STRATEGY.weights },
    genreLimits: { ...DEFAULT_STRATEGY.genreLimits },
    frontierGenres: [...DEFAULT_STRATEGY.frontierGenres],
    excludedTickers: [...DEFAULT_STRATEGY.excludedTickers],
  };
}

const capVariants: CapVariant[] = [
  { key: "main", apply: () => {} },
  { key: "q1", apply: (s) => { s.genreLimits.Quantum = 1; } },
  { key: "d1", apply: (s) => { s.genreLimits.Defense = 1; } },
  { key: "d2", apply: (s) => { s.genreLimits.Defense = 2; } },
  { key: "o1", apply: (s) => { s.genreLimits["Optical Networking"] = 1; } },
  { key: "f2", apply: (s) => { s.frontierMax = 2; } },
  { key: "q1d1", apply: (s) => { s.genreLimits.Quantum = 1; s.genreLimits.Defense = 1; } },
  { key: "q1d2", apply: (s) => { s.genreLimits.Quantum = 1; s.genreLimits.Defense = 2; } },
  { key: "q1o1", apply: (s) => { s.genreLimits.Quantum = 1; s.genreLimits["Optical Networking"] = 1; } },
  { key: "d1o1", apply: (s) => { s.genreLimits.Defense = 1; s.genreLimits["Optical Networking"] = 1; } },
  { key: "q1d1o1", apply: (s) => { s.genreLimits.Quantum = 1; s.genreLimits.Defense = 1; s.genreLimits["Optical Networking"] = 1; } },
  { key: "q1f2", apply: (s) => { s.genreLimits.Quantum = 1; s.frontierMax = 2; } },
  { key: "d1f2", apply: (s) => { s.genreLimits.Defense = 1; s.frontierMax = 2; } },
  { key: "q1d1f2", apply: (s) => { s.genreLimits.Quantum = 1; s.genreLimits.Defense = 1; s.frontierMax = 2; } },
  { key: "q1d1o1f2", apply: (s) => { s.genreLimits.Quantum = 1; s.genreLimits.Defense = 1; s.genreLimits["Optical Networking"] = 1; s.frontierMax = 2; } },
];
const capMap = new Map(capVariants.map((x) => [x.key, x]));

function strategyFromSpec(spec: Spec): StrategyConfig {
  const s = cloneStrategy();
  s.topN = spec.topN;
  s.qqqMaMonths = spec.qqqMaMonths;
  s.surgeLimit = spec.surgeLimit;
  s.weights = { ...spec.weights };
  capMap.get(spec.capKey)?.apply(s);
  return s;
}

function yearlyReturnsFromRows(rows: DashboardPayload["backtest"]["rows"]) {
  const yearly: Record<string, number> = {};
  for (const row of rows) {
    if (typeof row.monthlyReturn !== "number" || row.provisional) continue;
    const year = row.signalMonth.slice(0, 4);
    yearly[year] = (yearly[year] ?? 1) * (1 + row.monthlyReturn);
  }
  return Object.fromEntries(Object.entries(yearly).map(([year, value]) => [year, value - 1]));
}

function summarizeStandard(spec: Spec, dashboard: DashboardPayload): Summary {
  const stats = dashboard.backtest.stats;
  const yearlyReturns = yearlyReturnsFromRows(dashboard.backtest.rows);
  const yearValues = Object.values(yearlyReturns);
  return {
    ...spec,
    mode: "standard",
    cagr: stats.cagr,
    maxDrawdown: stats.maxDrawdown,
    annualizedVolatility: stats.annualizedVolatility,
    finalEquity: stats.finalEquity,
    averageMonthlyReturn: stats.averageMonthlyReturn,
    calmar: stats.maxDrawdown < 0 ? stats.cagr / Math.abs(stats.maxDrawdown) : Number.POSITIVE_INFINITY,
    yearlyReturns,
    worstYearReturn: yearValues.length ? Math.min(...yearValues) : 0,
    completedMonths: dashboard.backtest.rows.filter((r) => typeof r.monthlyReturn === "number" && !r.provisional).length,
    cashMonths: dashboard.backtest.rows.filter((r) => r.market === "Cash").length,
    insufficientMonths: dashboard.backtest.rows.filter((r) => r.market === "Not enough candidates").length,
  };
}

function mean(values: number[]) {
  return values.reduce((a, b) => a + b, 0) / values.length;
}
function stdev(values: number[]) {
  if (values.length <= 1) return 0;
  const m = mean(values);
  return Math.sqrt(values.reduce((sum, v) => sum + (v - m) ** 2, 0) / (values.length - 1));
}

function statsFromReturns(returns: Array<{ month: string; value: number; invested: number }>) {
  let equity = 1;
  let peak = 1;
  let maxDrawdown = 0;
  const equities: number[] = [];
  const vals: number[] = [];
  const yearly: Record<string, number> = {};
  for (const row of returns) {
    vals.push(row.value);
    equity *= 1 + row.value;
    equities.push(equity);
    peak = Math.max(peak, equity);
    maxDrawdown = Math.min(maxDrawdown, equity / peak - 1);
    const year = row.month.slice(0, 4);
    yearly[year] = (yearly[year] ?? 1) * (1 + row.value);
  }
  const finalEquity = equities.at(-1) ?? 1;
  const cagr = vals.length && finalEquity > 0 ? finalEquity ** (12 / vals.length) - 1 : 0;
  return {
    finalEquity,
    cagr,
    averageMonthlyReturn: vals.length ? mean(vals) : 0,
    annualizedVolatility: stdev(vals) * Math.sqrt(12),
    maxDrawdown,
    yearlyReturns: Object.fromEntries(Object.entries(yearly).map(([year, value]) => [year, value - 1])),
  };
}

function buildFixed10Summaries(baseSpec: Spec, dashboards: Map<number, DashboardPayload>): Summary[] {
  const byK = new Map<number, Map<string, DashboardPayload["backtest"]["rows"][number]>>();
  for (const [k, dashboard] of dashboards) {
    byK.set(k, new Map(dashboard.backtest.rows.map((row) => [row.signalMonth, row])));
  }
  const months = [...(byK.get(1)?.keys() ?? [])].sort();
  const candidateSeries: Array<{ month: string; k: number; meanReturn: number; provisional: boolean }> = [];
  for (const month of months) {
    let foundK = 0;
    let foundReturn = 0;
    let provisional = false;
    for (let k = 10; k >= 1; k -= 1) {
      const row = byK.get(k)?.get(month);
      if (row?.provisional) provisional = true;
      if (row?.market === "RiskOn" && typeof row.monthlyReturn === "number" && !row.provisional) {
        foundK = k;
        foundReturn = row.monthlyReturn;
        break;
      }
    }
    candidateSeries.push({ month, k: foundK, meanReturn: foundReturn, provisional });
  }

  return [1, 3, 5, 7, 10].map((minPositions) => {
    const completed = candidateSeries
      .filter((x) => !x.provisional)
      .map((x) => {
        const invest = x.k >= minPositions ? x.k / 10 : 0;
        return { month: x.month, value: invest * x.meanReturn, invested: invest };
      });
    const stats = statsFromReturns(completed);
    const yearValues = Object.values(stats.yearlyReturns);
    return {
      ...baseSpec,
      topN: 10,
      mode: "fixed10" as const,
      minPositions,
      cagr: stats.cagr,
      maxDrawdown: stats.maxDrawdown,
      annualizedVolatility: stats.annualizedVolatility,
      finalEquity: stats.finalEquity,
      averageMonthlyReturn: stats.averageMonthlyReturn,
      calmar: stats.maxDrawdown < 0 ? stats.cagr / Math.abs(stats.maxDrawdown) : Number.POSITIVE_INFINITY,
      yearlyReturns: stats.yearlyReturns,
      worstYearReturn: yearValues.length ? Math.min(...yearValues) : 0,
      completedMonths: completed.length,
      cashMonths: completed.filter((x) => x.invested === 0).length,
      insufficientMonths: 0,
      partialMonths: completed.filter((x) => x.invested > 0 && x.invested < 1).length,
      fullInvestMonths: completed.filter((x) => x.invested === 1).length,
      avgInvestedFraction: completed.length ? mean(completed.map((x) => x.invested)) : 0,
    };
  });
}

function weightKey(w: Weights) {
  return `${w.oneMonth.toFixed(2)}-${w.threeMonth.toFixed(2)}-${w.sixMonth.toFixed(2)}`;
}
function specKey(spec: Omit<Spec, "key">) {
  return `n${spec.topN}-ma${spec.qqqMaMonths}-s${spec.surgeLimit}-${weightKey(spec.weights)}-${spec.capKey}`;
}
function makeSpec(input: Omit<Spec, "key">): Spec {
  return { ...input, key: specKey(input) };
}
function uniqBy<T>(items: T[], keyFn: (x: T) => string) {
  const out: T[] = [];
  const seen = new Set<string>();
  for (const item of items) {
    const key = keyFn(item);
    if (!seen.has(key)) { seen.add(key); out.push(item); }
  }
  return out;
}
function topDistinct<T>(items: T[], count: number, score: (x: T) => number, key: (x: T) => string) {
  return uniqBy([...items].sort((a, b) => score(b) - score(a)), key).slice(0, count);
}

async function main() {
  const symbols = TICKERS.map((t) => t.symbol);
  const histories = await fetchHistories(symbols);

  const mainSpec = makeSpec({ topN: DEFAULT_STRATEGY.topN, qqqMaMonths: DEFAULT_STRATEGY.qqqMaMonths, surgeLimit: DEFAULT_STRATEGY.surgeLimit, weights: { ...DEFAULT_STRATEGY.weights }, capKey: "main" });
  const q1d1Base = makeSpec({ topN: 10, qqqMaMonths: 10, surgeLimit: 0.8, weights: { oneMonth: 0.2, threeMonth: 0.4, sixMonth: 0.4 }, capKey: "q1d1" });

  const standardCache = new Map<string, { spec: Spec; dashboard: DashboardPayload; summary: Summary }>();
  const runStandard = (spec: Spec) => {
    const cached = standardCache.get(spec.key);
    if (cached) return cached;
    const dashboard = buildDashboard(histories, TICKERS, strategyFromSpec(spec));
    const summary = summarizeStandard(spec, dashboard);
    const entry = { spec, dashboard, summary };
    standardCache.set(spec.key, entry);
    return entry;
  };

  const mainBaseline = runStandard(mainSpec).summary;
  const q1d1Baseline = runStandard(q1d1Base).summary;

  const topNSweep = [5,6,7,8,9,10,11,12].map((topN) => runStandard(makeSpec({ ...q1d1Base, topN, key: undefined as never })).summary);
  const maSweep = [7,8,9,10,11,12,13].map((qqqMaMonths) => runStandard(makeSpec({ ...q1d1Base, qqqMaMonths, key: undefined as never })).summary);
  const surgeSweep = [0.5,0.6,0.7,0.8,0.9,1.0,1.2,10].map((surgeLimit) => runStandard(makeSpec({ ...q1d1Base, surgeLimit, key: undefined as never })).summary);

  const weightCandidates: Weights[] = [];
  for (let one = 0; one <= 5; one += 1) {
    for (let three = 1; three <= 7; three += 1) {
      const six = 10 - one - three;
      if (six < 1 || six > 8) continue;
      weightCandidates.push({ oneMonth: one / 10, threeMonth: three / 10, sixMonth: six / 10 });
    }
  }
  weightCandidates.push({ oneMonth: 0.2, threeMonth: 0.4, sixMonth: 0.4 });
  const weightSweep = uniqBy(weightCandidates, weightKey).map((weights) => runStandard(makeSpec({ ...q1d1Base, weights, key: undefined as never })).summary);
  const capSweep = capVariants.map((cap) => runStandard(makeSpec({ ...q1d1Base, capKey: cap.key, key: undefined as never })).summary);

  const chooseValues = <T>(items: Summary[], value: (s: Summary) => T, baseline: T, key: (v: T) => string, countEach = 1) => {
    const cagr = topDistinct(items, countEach, (x) => x.cagr, (x) => key(value(x))).map(value);
    const calmar = topDistinct(items, countEach, (x) => x.calmar, (x) => key(value(x))).map(value);
    return uniqBy([baseline, ...cagr, ...calmar], key);
  };

  const topNValues = chooseValues(topNSweep, (s) => s.topN, 10, String, 1);
  const maValues = chooseValues(maSweep, (s) => s.qqqMaMonths, 10, String, 1);
  const surgeValues = chooseValues(surgeSweep, (s) => s.surgeLimit, 0.8, String, 1);
  const weightValues = chooseValues(weightSweep, (s) => s.weights, q1d1Base.weights, weightKey, 2);
  const capValues = chooseValues(capSweep, (s) => s.capKey, "q1d1", String, 2);

  const comboSpecs: Spec[] = [];
  for (const topN of topNValues) for (const qqqMaMonths of maValues) for (const surgeLimit of surgeValues) for (const weights of weightValues) for (const capKey of capValues) {
    comboSpecs.push(makeSpec({ topN, qqqMaMonths, surgeLimit, weights, capKey }));
  }
  const comboSummaries = uniqBy(comboSpecs, (x) => x.key).map((spec) => runStandard(spec).summary);

  const standardAll = [...standardCache.values()].map((x) => x.summary);
  const standardFinalists = uniqBy([
    ...topDistinct(comboSummaries, 15, (x) => x.cagr, (x) => x.key),
    ...topDistinct(comboSummaries, 15, (x) => x.calmar, (x) => x.key),
    q1d1Baseline,
    mainBaseline,
  ], (x) => x.key);

  const partialBaseSpecs = uniqBy(standardFinalists.map((s) => makeSpec({
    topN: 10,
    qqqMaMonths: s.qqqMaMonths,
    surgeLimit: s.surgeLimit,
    weights: s.weights,
    capKey: s.capKey,
  })), (x) => x.key);

  const partialSummaries: Summary[] = [];
  for (const baseSpec of partialBaseSpecs) {
    const dashboards = new Map<number, DashboardPayload>();
    for (let k = 1; k <= 10; k += 1) {
      const spec = makeSpec({ ...baseSpec, topN: k, key: undefined as never });
      dashboards.set(k, runStandard(spec).dashboard);
    }
    partialSummaries.push(...buildFixed10Summaries(baseSpec, dashboards));
  }

  const topStandardByCagr = [...standardAll].sort((a,b) => b.cagr - a.cagr).slice(0, 30);
  const topStandardByCalmar = [...standardAll].sort((a,b) => b.calmar - a.calmar).slice(0, 30);
  const topPartialByCagr = [...partialSummaries].sort((a,b) => b.cagr - a.cagr).slice(0, 30);
  const topPartialByCalmar = [...partialSummaries].sort((a,b) => b.calmar - a.calmar).slice(0, 30);

  const result = {
    generatedAt: new Date().toISOString(),
    source: "Yahoo Finance via src/lib/yahoo.ts; standard scenarios use src/lib/momentum.ts buildDashboard directly. fixed10 scenarios reconstruct only portfolio weighting from buildDashboard top-k monthly returns.",
    historyRange: Object.fromEntries(Object.entries(histories).map(([symbol, points]) => [symbol, { first: points[0]?.date ?? null, last: points.at(-1)?.date ?? null, count: points.length }])),
    mainBaseline,
    q1d1Baseline,
    sweeps: { topN: topNSweep, ma: maSweep, surge: surgeSweep, weights: weightSweep, caps: capSweep },
    selectedForCombo: { topNValues, maValues, surgeValues, weightValues, capValues },
    comboCount: comboSummaries.length,
    comboSummaries,
    partialBaseCount: partialBaseSpecs.length,
    partialSummaries,
    topStandardByCagr,
    topStandardByCalmar,
    topPartialByCagr,
    topPartialByCalmar,
  };

  await mkdir("artifacts", { recursive: true });
  await writeFile("artifacts/parameter-search-results.json", JSON.stringify(result, null, 2));
  console.log("MAIN_BASELINE", JSON.stringify(mainBaseline));
  console.log("Q1D1_BASELINE", JSON.stringify(q1d1Baseline));
  console.log("SELECTED", JSON.stringify(result.selectedForCombo));
  console.log("TOP_STANDARD_CAGR", JSON.stringify(topStandardByCagr.slice(0, 10)));
  console.log("TOP_STANDARD_CALMAR", JSON.stringify(topStandardByCalmar.slice(0, 10)));
  console.log("TOP_PARTIAL_CAGR", JSON.stringify(topPartialByCagr.slice(0, 10)));
  console.log("TOP_PARTIAL_CALMAR", JSON.stringify(topPartialByCalmar.slice(0, 10)));
}

main().catch((error) => { console.error(error); process.exit(1); });
