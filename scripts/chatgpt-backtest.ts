import { mkdir, writeFile } from "node:fs/promises";
import { buildDashboard } from "../src/lib/momentum";
import { TICKERS, DEFAULT_STRATEGY } from "../src/lib/config";
import { fetchHistories } from "../src/lib/yahoo";
import type { DashboardPayload, StrategyConfig, TickerConfig } from "../src/lib/types";

type ScenarioResult = {
  name: string;
  cagr: number;
  maxDrawdown: number;
  annualizedVolatility: number;
  finalEquity: number;
  averageMonthlyReturn: number;
  calmar: number;
  changedMonths: number;
  changes: Array<{
    month: string;
    baselinePicks: string[];
    scenarioPicks: string[];
    baselineReturn: number | null;
    scenarioReturn: number | null;
    returnDelta: number | null;
    removed: string[];
    added: string[];
  }>;
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

function rowsByMonth(dashboard: DashboardPayload) {
  return new Map(dashboard.backtest.rows.map((row) => [row.signalMonth, row]));
}

function summarizeScenario(
  name: string,
  dashboard: DashboardPayload,
  baseline: DashboardPayload,
): ScenarioResult {
  const stats = dashboard.backtest.stats;
  const baselineRows = rowsByMonth(baseline);
  const scenarioRows = rowsByMonth(dashboard);
  const months = [...new Set([...baselineRows.keys(), ...scenarioRows.keys()])].sort();
  const changes: ScenarioResult["changes"] = [];

  for (const month of months) {
    const a = baselineRows.get(month);
    const b = scenarioRows.get(month);
    const ap = a?.picks ?? [];
    const bp = b?.picks ?? [];
    const samePicks = ap.length === bp.length && ap.every((v, i) => v === bp[i]);
    const ar = typeof a?.monthlyReturn === "number" ? a.monthlyReturn : null;
    const br = typeof b?.monthlyReturn === "number" ? b.monthlyReturn : null;
    const sameReturn = ar === br;
    if (samePicks && sameReturn) continue;
    changes.push({
      month,
      baselinePicks: ap,
      scenarioPicks: bp,
      baselineReturn: ar,
      scenarioReturn: br,
      returnDelta: ar !== null && br !== null ? br - ar : null,
      removed: ap.filter((x) => !bp.includes(x)),
      added: bp.filter((x) => !ap.includes(x)),
    });
  }

  return {
    name,
    cagr: stats.cagr,
    maxDrawdown: stats.maxDrawdown,
    annualizedVolatility: stats.annualizedVolatility,
    finalEquity: stats.finalEquity,
    averageMonthlyReturn: stats.averageMonthlyReturn,
    calmar: stats.maxDrawdown < 0 ? stats.cagr / Math.abs(stats.maxDrawdown) : Number.POSITIVE_INFINITY,
    changedMonths: changes.length,
    changes,
  };
}

function selectionCounts(dashboard: DashboardPayload) {
  const counts: Record<string, number> = {};
  const months: Record<string, string[]> = {};
  for (const row of dashboard.backtest.rows) {
    for (const symbol of row.picks) {
      counts[symbol] = (counts[symbol] ?? 0) + 1;
      (months[symbol] ??= []).push(row.signalMonth);
    }
  }
  return { counts, months };
}

function combinations<T>(items: T[], minSize: number, maxSize: number): T[][] {
  const out: T[][] = [];
  const walk = (start: number, current: T[]) => {
    if (current.length >= minSize) out.push([...current]);
    if (current.length === maxSize) return;
    for (let i = start; i < items.length; i += 1) {
      current.push(items[i]);
      walk(i + 1, current);
      current.pop();
    }
  };
  walk(0, []);
  return out;
}

async function main() {
  const symbols = TICKERS.map((ticker) => ticker.symbol);
  const histories = await fetchHistories(symbols);
  const baselineStrategy = cloneStrategy();
  const baseline = buildDashboard(histories, TICKERS, baselineStrategy);
  const baselineSummary = summarizeScenario("Baseline", baseline, baseline);
  const selection = selectionCounts(baseline);

  const loo: Array<ScenarioResult & { removed: string; genre: string; selectionCount: number; selectionMonths: string[] }> = [];
  for (const ticker of TICKERS) {
    if (ticker.symbol === "QQQ") continue;
    const tickers = TICKERS.filter((item) => item.symbol !== ticker.symbol);
    const dashboard = buildDashboard(histories, tickers, cloneStrategy());
    loo.push({
      ...summarizeScenario(`Remove ${ticker.symbol}`, dashboard, baseline),
      removed: ticker.symbol,
      genre: ticker.genre,
      selectionCount: selection.counts[ticker.symbol] ?? 0,
      selectionMonths: selection.months[ticker.symbol] ?? [],
    });
  }
  loo.sort((a, b) => b.cagr - a.cagr);

  const genreNames = [...new Set(TICKERS.filter((t) => t.symbol !== "QQQ").map((t) => t.genre))].sort();
  const genreTests: Array<ScenarioResult & { genre: string; limit: number | "unlimited" }> = [];
  for (const genre of genreNames) {
    const count = TICKERS.filter((t) => t.genre === genre && t.symbol !== "QQQ").length;
    if (count < 2) continue;
    const limits = [...new Set([1, 2, 3, 4].filter((v) => v <= count))];
    for (const limit of limits) {
      const strategy = cloneStrategy();
      strategy.genreLimits[genre] = limit;
      const dashboard = buildDashboard(histories, TICKERS, strategy);
      genreTests.push({ ...summarizeScenario(`${genre} limit ${limit}`, dashboard, baseline), genre, limit });
    }
    const strategy = cloneStrategy();
    delete strategy.genreLimits[genre];
    const dashboard = buildDashboard(histories, TICKERS, strategy);
    genreTests.push({ ...summarizeScenario(`${genre} unlimited`, dashboard, baseline), genre, limit: "unlimited" });
  }

  const frontierTests: Array<ScenarioResult & { frontierMax: number }> = [];
  for (const frontierMax of [1, 2, 3, 4, 5]) {
    const strategy = cloneStrategy();
    strategy.frontierMax = frontierMax;
    const dashboard = buildDashboard(histories, TICKERS, strategy);
    frontierTests.push({ ...summarizeScenario(`Frontier max ${frontierMax}`, dashboard, baseline), frontierMax });
  }

  const positiveLoo = loo
    .filter((x) => x.cagr > baselineSummary.cagr)
    .sort((a, b) => b.cagr - a.cagr)
    .slice(0, 8)
    .map((x) => x.removed);
  const removalCombos: Array<ScenarioResult & { removed: string[] }> = [];
  for (const combo of combinations(positiveLoo, 2, Math.min(4, positiveLoo.length))) {
    const set = new Set(combo);
    const tickers = TICKERS.filter((item) => !set.has(item.symbol));
    const dashboard = buildDashboard(histories, tickers, cloneStrategy());
    removalCombos.push({ ...summarizeScenario(`Remove ${combo.join("+")}`, dashboard, baseline), removed: combo });
  }
  removalCombos.sort((a, b) => b.cagr - a.cagr);

  const result = {
    generatedAt: new Date().toISOString(),
    source: "Yahoo Finance via src/lib/yahoo.ts fetchHistories/fetchYahooHistory",
    strategy: baselineStrategy,
    tickers: TICKERS,
    historyRange: Object.fromEntries(Object.entries(histories).map(([symbol, points]) => [symbol, {
      first: points[0]?.date ?? null,
      last: points.at(-1)?.date ?? null,
      count: points.length,
    }])),
    baseline: baselineSummary,
    baselineSelection: selection,
    leaveOneOut: loo,
    genreTests,
    frontierTests,
    positiveLooCandidates: positiveLoo,
    removalCombos,
  };

  await mkdir("artifacts", { recursive: true });
  await writeFile("artifacts/backtest-results.json", JSON.stringify(result, null, 2));

  console.log("BASELINE", JSON.stringify(baselineSummary));
  console.log("TOP_LOO", JSON.stringify(loo.slice(0, 12).map((x) => ({ removed: x.removed, genre: x.genre, cagr: x.cagr, maxDrawdown: x.maxDrawdown, vol: x.annualizedVolatility, finalEquity: x.finalEquity, changedMonths: x.changedMonths }))));
  console.log("TOP_GENRE", JSON.stringify([...genreTests].sort((a, b) => b.cagr - a.cagr).slice(0, 12).map((x) => ({ genre: x.genre, limit: x.limit, cagr: x.cagr, maxDrawdown: x.maxDrawdown, vol: x.annualizedVolatility, finalEquity: x.finalEquity, changedMonths: x.changedMonths }))));
  console.log("FRONTIER", JSON.stringify(frontierTests.map((x) => ({ frontierMax: x.frontierMax, cagr: x.cagr, maxDrawdown: x.maxDrawdown, vol: x.annualizedVolatility, finalEquity: x.finalEquity, changedMonths: x.changedMonths }))));
  console.log("TOP_COMBOS", JSON.stringify(removalCombos.slice(0, 20).map((x) => ({ removed: x.removed, cagr: x.cagr, maxDrawdown: x.maxDrawdown, vol: x.annualizedVolatility, finalEquity: x.finalEquity, changedMonths: x.changedMonths }))));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
