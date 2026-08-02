import { mkdir, writeFile } from "node:fs/promises";
import { buildDashboard } from "../src/lib/momentum";
import { TICKERS, DEFAULT_STRATEGY } from "../src/lib/config";
import { fetchHistories } from "../src/lib/yahoo";
import type { DashboardPayload, StrategyConfig } from "../src/lib/types";

type ChangeRow = {
  month: string;
  baselinePicks: string[];
  scenarioPicks: string[];
  baselineReturn: number | null;
  scenarioReturn: number | null;
  returnDelta: number | null;
  removed: string[];
  added: string[];
};

type ScenarioResult = {
  name: string;
  rules: string[];
  cagr: number;
  maxDrawdown: number;
  annualizedVolatility: number;
  finalEquity: number;
  averageMonthlyReturn: number;
  calmar: number;
  changedMonths: number;
  annualReturns: Record<string, number>;
  changes: ChangeRow[];
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

function annualReturns(dashboard: DashboardPayload) {
  const byYear = new Map<string, number[]>();
  for (const row of dashboard.backtest.rows) {
    if (row.provisional || typeof row.monthlyReturn !== "number") continue;
    const year = row.signalMonth.slice(0, 4);
    (byYear.get(year) ?? byYear.set(year, []).get(year)!).push(row.monthlyReturn);
  }
  return Object.fromEntries(
    [...byYear.entries()].map(([year, returns]) => [
      year,
      returns.reduce((equity, value) => equity * (1 + value), 1) - 1,
    ]),
  );
}

function summarizeScenario(
  name: string,
  rules: string[],
  dashboard: DashboardPayload,
  baseline: DashboardPayload,
): ScenarioResult {
  const stats = dashboard.backtest.stats;
  const baselineRows = rowsByMonth(baseline);
  const scenarioRows = rowsByMonth(dashboard);
  const months = [...new Set([...baselineRows.keys(), ...scenarioRows.keys()])].sort();
  const changes: ChangeRow[] = [];

  for (const month of months) {
    const a = baselineRows.get(month);
    const b = scenarioRows.get(month);
    const ap = a?.picks ?? [];
    const bp = b?.picks ?? [];
    const samePicks = ap.length === bp.length && ap.every((v, i) => v === bp[i]);
    const ar = typeof a?.monthlyReturn === "number" ? a.monthlyReturn : null;
    const br = typeof b?.monthlyReturn === "number" ? b.monthlyReturn : null;
    if (samePicks && ar === br) continue;

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
    rules,
    cagr: stats.cagr,
    maxDrawdown: stats.maxDrawdown,
    annualizedVolatility: stats.annualizedVolatility,
    finalEquity: stats.finalEquity,
    averageMonthlyReturn: stats.averageMonthlyReturn,
    calmar:
      stats.maxDrawdown < 0
        ? stats.cagr / Math.abs(stats.maxDrawdown)
        : Number.POSITIVE_INFINITY,
    changedMonths: changes.length,
    annualReturns: annualReturns(dashboard),
    changes,
  };
}

function combinations<T>(items: T[]): T[][] {
  const out: T[][] = [];
  for (let mask = 1; mask < 1 << items.length; mask += 1) {
    const combo: T[] = [];
    for (let i = 0; i < items.length; i += 1) {
      if (mask & (1 << i)) combo.push(items[i]);
    }
    out.push(combo);
  }
  return out;
}

async function main() {
  const symbols = TICKERS.map((ticker) => ticker.symbol);
  const histories = await fetchHistories(symbols);
  const baselineStrategy = cloneStrategy();
  const baseline = buildDashboard(histories, TICKERS, baselineStrategy);
  const baselineSummary = summarizeScenario("Baseline", [], baseline, baseline);

  const capDefinitions = [
    {
      key: "Quantum limit 1",
      apply: (strategy: StrategyConfig) => {
        strategy.genreLimits.Quantum = 1;
      },
    },
    {
      key: "frontierMax 2",
      apply: (strategy: StrategyConfig) => {
        strategy.frontierMax = 2;
      },
    },
    {
      key: "Defense limit 1",
      apply: (strategy: StrategyConfig) => {
        strategy.genreLimits.Defense = 1;
      },
    },
    {
      key: "Optical Networking limit 1",
      apply: (strategy: StrategyConfig) => {
        strategy.genreLimits["Optical Networking"] = 1;
      },
    },
  ];

  const capScenarios: ScenarioResult[] = [];
  for (const combo of combinations(capDefinitions)) {
    const strategy = cloneStrategy();
    for (const rule of combo) rule.apply(strategy);
    const rules = combo.map((rule) => rule.key);
    const dashboard = buildDashboard(histories, TICKERS, strategy);
    capScenarios.push(
      summarizeScenario(rules.join(" + "), rules, dashboard, baseline),
    );
  }

  const removalScenarios: ScenarioResult[] = [];
  for (const symbol of ["AVAV", "IONQ", "FN"]) {
    const tickers = TICKERS.filter((ticker) => ticker.symbol !== symbol);
    const dashboard = buildDashboard(histories, tickers, cloneStrategy());
    removalScenarios.push(
      summarizeScenario(`Remove ${symbol}`, [`Remove ${symbol}`], dashboard, baseline),
    );
  }

  const allScenarios = [baselineSummary, ...capScenarios, ...removalScenarios];
  const rankedByCalmar = [...allScenarios].sort(
    (a, b) => b.calmar - a.calmar || b.cagr - a.cagr,
  );
  const rankedByCagr = [...allScenarios].sort((a, b) => b.cagr - a.cagr);

  const result = {
    generatedAt: new Date().toISOString(),
    mainSha: process.env.GITHUB_SHA ?? null,
    source: "Yahoo Finance via src/lib/yahoo.ts fetchHistories/fetchYahooHistory",
    historyRange: Object.fromEntries(
      Object.entries(histories).map(([symbol, points]) => [
        symbol,
        {
          first: points[0]?.date ?? null,
          last: points.at(-1)?.date ?? null,
          count: points.length,
        },
      ]),
    ),
    strategy: baselineStrategy,
    baseline: baselineSummary,
    capScenarios,
    removalScenarios,
    rankedByCalmar,
    rankedByCagr,
  };

  await mkdir("artifacts", { recursive: true });
  await writeFile(
    "artifacts/backtest-results.json",
    JSON.stringify(result, null, 2),
  );

  const compact = (scenario: ScenarioResult) => ({
    name: scenario.name,
    cagr: scenario.cagr,
    maxDrawdown: scenario.maxDrawdown,
    vol: scenario.annualizedVolatility,
    finalEquity: scenario.finalEquity,
    calmar: scenario.calmar,
    changedMonths: scenario.changedMonths,
    annualReturns: scenario.annualReturns,
  });

  console.log("BASELINE", JSON.stringify(compact(baselineSummary)));
  console.log(
    "RANKED_CALMAR",
    JSON.stringify(rankedByCalmar.map(compact)),
  );
  console.log("RANKED_CAGR", JSON.stringify(rankedByCagr.map(compact)));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
