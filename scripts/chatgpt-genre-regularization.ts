import { mkdir, writeFile } from "node:fs/promises";
import { buildDashboard } from "../src/lib/momentum";
import { DEFAULT_STRATEGY, TICKERS } from "../src/lib/config";
import { fetchHistories } from "../src/lib/yahoo";
import type { BacktestRow, DashboardPayload, StrategyConfig } from "../src/lib/types";

type Scenario = {
  name: string;
  family: string;
  complexity: number;
  genreRule: string;
  frontierMax: number;
  strategy: StrategyConfig;
};

type Stats = {
  finalEquity: number;
  cagr: number;
  maxDrawdown: number;
  annualizedVolatility: number;
  averageMonthlyReturn: number;
  calmar: number;
};

type Result = Stats & {
  name: string;
  family: string;
  complexity: number;
  genreRule: string;
  frontierMax: number;
  genreLimits: Record<string, number>;
  changedMonths: number;
  annualReturns: Record<string, number>;
  yearsBeatingCurrent: number;
  worstYearReturn: number;
  changes: Array<{
    month: string;
    currentPicks: string[];
    scenarioPicks: string[];
    currentReturn: number | null;
    scenarioReturn: number | null;
    returnDelta: number | null;
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

function genreCounts() {
  const counts: Record<string, number> = {};
  for (const ticker of TICKERS) {
    if (ticker.symbol === "QQQ") continue;
    counts[ticker.genre] = (counts[ticker.genre] ?? 0) + 1;
  }
  return counts;
}

const counts = genreCounts();
const genres = Object.keys(counts).sort();

function uniformLimits(limit: number) {
  return Object.fromEntries(genres.map((genre) => [genre, limit]));
}

function sizeFloorHalfLimits() {
  return Object.fromEntries(
    genres.map((genre) => [genre, Math.max(1, Math.floor(counts[genre] / 2))]),
  );
}

function sizeCeilHalfLimits() {
  return Object.fromEntries(
    genres.map((genre) => [genre, Math.max(1, Math.ceil(counts[genre] / 2))]),
  );
}

function strategyWith(genreLimits: Record<string, number>, frontierMax: number) {
  const strategy = cloneStrategy();
  strategy.genreLimits = { ...genreLimits };
  strategy.frontierMax = frontierMax;
  return strategy;
}

function rowsByMonth(dashboard: DashboardPayload) {
  return new Map(dashboard.backtest.rows.map((row) => [row.signalMonth, row]));
}

function annualReturns(rows: BacktestRow[]) {
  const byYear = new Map<string, number[]>();
  for (const row of rows) {
    if (typeof row.monthlyReturn !== "number" || row.provisional) continue;
    const year = row.signalMonth.slice(0, 4);
    const list = byYear.get(year) ?? [];
    list.push(row.monthlyReturn);
    byYear.set(year, list);
  }
  return Object.fromEntries(
    [...byYear.entries()].map(([year, values]) => [
      year,
      values.reduce((equity, value) => equity * (1 + value), 1) - 1,
    ]),
  );
}

function statsFromReturns(returns: number[]): Stats {
  if (!returns.length) {
    return {
      finalEquity: 1,
      cagr: 0,
      maxDrawdown: 0,
      annualizedVolatility: 0,
      averageMonthlyReturn: 0,
      calmar: 0,
    };
  }
  let equity = 1;
  let peak = 1;
  let maxDrawdown = 0;
  for (const value of returns) {
    equity *= 1 + value;
    peak = Math.max(peak, equity);
    maxDrawdown = Math.min(maxDrawdown, equity / peak - 1);
  }
  const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
  const variance =
    returns.length > 1
      ? returns.reduce((sum, value) => sum + (value - mean) ** 2, 0) /
        (returns.length - 1)
      : 0;
  const vol = Math.sqrt(variance) * Math.sqrt(12);
  const cagr = equity > 0 ? equity ** (12 / returns.length) - 1 : 0;
  return {
    finalEquity: equity,
    cagr,
    maxDrawdown,
    annualizedVolatility: vol,
    averageMonthlyReturn: mean,
    calmar: maxDrawdown < 0 ? cagr / Math.abs(maxDrawdown) : Number.POSITIVE_INFINITY,
  };
}

function completedReturns(rows: BacktestRow[], excludedYear?: string) {
  return rows
    .filter(
      (row) =>
        typeof row.monthlyReturn === "number" &&
        !row.provisional &&
        (!excludedYear || row.signalMonth.slice(0, 4) !== excludedYear),
    )
    .map((row) => row.monthlyReturn as number);
}

function summarize(
  scenario: Scenario,
  dashboard: DashboardPayload,
  current: DashboardPayload,
  currentAnnual: Record<string, number>,
): Result {
  const stats = dashboard.backtest.stats;
  const currentRows = rowsByMonth(current);
  const scenarioRows = rowsByMonth(dashboard);
  const months = [...new Set([...currentRows.keys(), ...scenarioRows.keys()])].sort();
  const changes: Result["changes"] = [];

  for (const month of months) {
    const a = currentRows.get(month);
    const b = scenarioRows.get(month);
    const ap = a?.picks ?? [];
    const bp = b?.picks ?? [];
    const ar = typeof a?.monthlyReturn === "number" ? a.monthlyReturn : null;
    const br = typeof b?.monthlyReturn === "number" ? b.monthlyReturn : null;
    const samePicks = ap.length === bp.length && ap.every((value, index) => value === bp[index]);
    if (samePicks && ar === br) continue;
    changes.push({
      month,
      currentPicks: ap,
      scenarioPicks: bp,
      currentReturn: ar,
      scenarioReturn: br,
      returnDelta: ar !== null && br !== null ? br - ar : null,
    });
  }

  const yearly = annualReturns(dashboard.backtest.rows);
  const commonYears = Object.keys(currentAnnual).filter((year) => yearly[year] !== undefined);
  const yearsBeatingCurrent = commonYears.filter(
    (year) => yearly[year] >= currentAnnual[year],
  ).length;
  const worstYearReturn = Math.min(...Object.values(yearly));

  return {
    name: scenario.name,
    family: scenario.family,
    complexity: scenario.complexity,
    genreRule: scenario.genreRule,
    frontierMax: scenario.frontierMax,
    genreLimits: scenario.strategy.genreLimits,
    finalEquity: stats.finalEquity,
    cagr: stats.cagr,
    maxDrawdown: stats.maxDrawdown,
    annualizedVolatility: stats.annualizedVolatility,
    averageMonthlyReturn: stats.averageMonthlyReturn,
    calmar: stats.maxDrawdown < 0 ? stats.cagr / Math.abs(stats.maxDrawdown) : Number.POSITIVE_INFINITY,
    changedMonths: changes.length,
    annualReturns: yearly,
    yearsBeatingCurrent,
    worstYearReturn,
    changes,
  };
}

function makeScenarios(): Scenario[] {
  const scenarios: Scenario[] = [];
  const frontierOptions = [2, 3, 10];
  const rules: Array<{
    family: string;
    complexity: number;
    description: string;
    limits: Record<string, number>;
  }> = [
    { family: "none", complexity: 0, description: "All genres unlimited", limits: {} },
    { family: "uniform1", complexity: 1, description: "All genres max 1", limits: uniformLimits(1) },
    { family: "uniform2", complexity: 1, description: "All genres max 2", limits: uniformLimits(2) },
    { family: "uniform3", complexity: 1, description: "All genres max 3", limits: uniformLimits(3) },
    { family: "sizeFloorHalf", complexity: 1, description: "Genre limit = max(1, floor(universe count / 2))", limits: sizeFloorHalfLimits() },
    { family: "sizeCeilHalf", complexity: 1, description: "Genre limit = max(1, ceil(universe count / 2))", limits: sizeCeilHalfLimits() },
  ];

  for (const rule of rules) {
    for (const frontierMax of frontierOptions) {
      const frontierLabel = frontierMax >= 10 ? "unlimited" : String(frontierMax);
      scenarios.push({
        name: `${rule.family} + frontier ${frontierLabel}`,
        family: rule.family,
        complexity: rule.complexity + (frontierMax >= 10 ? 0 : 1),
        genreRule: rule.description,
        frontierMax,
        strategy: strategyWith(rule.limits, frontierMax),
      });
    }
  }

  for (const frontierMax of frontierOptions) {
    const strategy = cloneStrategy();
    strategy.frontierMax = frontierMax;
    const frontierLabel = frontierMax >= 10 ? "unlimited" : String(frontierMax);
    scenarios.push({
      name: `current individual caps + frontier ${frontierLabel}`,
      family: "currentIndividual",
      complexity: Object.keys(strategy.genreLimits).length + (frontierMax >= 10 ? 0 : 1),
      genreRule: "Current per-genre caps",
      frontierMax,
      strategy,
    });
  }
  return scenarios;
}

async function main() {
  const symbols = TICKERS.map((ticker) => ticker.symbol);
  const histories = await fetchHistories(symbols);
  const current = buildDashboard(histories, TICKERS, cloneStrategy());
  const currentAnnual = annualReturns(current.backtest.rows);
  const currentScenario: Scenario = {
    name: "Current production",
    family: "currentIndividual",
    complexity: Object.keys(DEFAULT_STRATEGY.genreLimits).length + 1,
    genreRule: "Current per-genre caps",
    frontierMax: DEFAULT_STRATEGY.frontierMax,
    strategy: cloneStrategy(),
  };
  const currentResult = summarize(currentScenario, current, current, currentAnnual);

  const scenarioDefinitions = makeScenarios();
  const dashboards = new Map<string, DashboardPayload>();
  const results: Result[] = [];
  for (const scenario of scenarioDefinitions) {
    const dashboard = buildDashboard(histories, TICKERS, scenario.strategy);
    dashboards.set(scenario.name, dashboard);
    results.push(summarize(scenario, dashboard, current, currentAnnual));
  }

  const generalResults = results.filter((result) => result.family !== "currentIndividual");
  const years = Object.keys(currentAnnual).sort();
  const leaveOneYearOut = years.map((heldOutYear) => {
    const ranked = generalResults
      .map((result) => {
        const dashboard = dashboards.get(result.name)!;
        const trainStats = statsFromReturns(completedReturns(dashboard.backtest.rows, heldOutYear));
        return { result, trainStats };
      })
      .sort((a, b) =>
        b.trainStats.calmar - a.trainStats.calmar ||
        b.trainStats.cagr - a.trainStats.cagr ||
        a.result.complexity - b.result.complexity,
      );
    const winner = ranked[0];
    return {
      heldOutYear,
      selectedOnOtherYears: winner.result.name,
      trainingCagr: winner.trainStats.cagr,
      trainingMaxDrawdown: winner.trainStats.maxDrawdown,
      trainingCalmar: winner.trainStats.calmar,
      heldOutReturn: winner.result.annualReturns[heldOutYear] ?? null,
      currentHeldOutReturn: currentAnnual[heldOutYear] ?? null,
      heldOutDeltaVsCurrent:
        winner.result.annualReturns[heldOutYear] !== undefined && currentAnnual[heldOutYear] !== undefined
          ? winner.result.annualReturns[heldOutYear] - currentAnnual[heldOutYear]
          : null,
    };
  });

  const rankedByCalmar = [...results].sort((a, b) =>
    b.calmar - a.calmar || b.cagr - a.cagr || a.complexity - b.complexity,
  );
  const rankedByCagr = [...results].sort((a, b) =>
    b.cagr - a.cagr || b.calmar - a.calmar || a.complexity - b.complexity,
  );

  const output = {
    generatedAt: new Date().toISOString(),
    source: "Yahoo Finance via src/lib/yahoo.ts; portfolio/backtest via src/lib/momentum.ts buildDashboard()",
    historyRange: Object.fromEntries(
      Object.entries(histories).map(([symbol, points]) => [
        symbol,
        { first: points[0]?.date ?? null, last: points.at(-1)?.date ?? null, count: points.length },
      ]),
    ),
    genreCounts: counts,
    current: currentResult,
    results,
    topByCalmar: rankedByCalmar.slice(0, 12),
    topByCagr: rankedByCagr.slice(0, 12),
    leaveOneYearOut,
  };

  await mkdir("artifacts", { recursive: true });
  await writeFile("artifacts/genre-regularization-results.json", JSON.stringify(output, null, 2));

  const brief = (result: Result) => ({
    name: result.name,
    complexity: result.complexity,
    cagr: result.cagr,
    maxDD: result.maxDrawdown,
    vol: result.annualizedVolatility,
    calmar: result.calmar,
    finalEquity: result.finalEquity,
    changedMonths: result.changedMonths,
    yearsBeatingCurrent: result.yearsBeatingCurrent,
    worstYearReturn: result.worstYearReturn,
    annualReturns: result.annualReturns,
  });
  console.log("CURRENT", JSON.stringify(brief(currentResult)));
  console.log("TOP_CALMAR", JSON.stringify(rankedByCalmar.slice(0, 12).map(brief)));
  console.log("TOP_CAGR", JSON.stringify(rankedByCagr.slice(0, 12).map(brief)));
  console.log("LOYO", JSON.stringify(leaveOneYearOut));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
