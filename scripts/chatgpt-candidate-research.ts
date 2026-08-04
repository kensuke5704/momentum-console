import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { TICKERS } from "../src/lib/config";
import { FROZEN_STRATEGY } from "../src/lib/frozen-strategy";
import { buildDashboard } from "../src/lib/momentum";
import type { DashboardPayload, TickerConfig } from "../src/lib/types";
import { fetchHistories } from "../src/lib/yahoo";

const CANDIDATES: TickerConfig[] = [
  { symbol: "CRWV", genre: "AI Cloud" },
  { symbol: "NBIS", genre: "AI Cloud" },
  { symbol: "AUR", genre: "Autonomous Freight" },
  { symbol: "KDK", genre: "Autonomous Freight" },
  { symbol: "JOBY", genre: "Advanced Air Mobility" },
  { symbol: "ACHR", genre: "Advanced Air Mobility" },
  { symbol: "TEM", genre: "AI Healthcare" },
  { symbol: "RXRX", genre: "AI Healthcare" },
];

const THEMES = [
  { name: "AI Cloud", symbols: ["CRWV", "NBIS"] },
  { name: "Autonomous Freight", symbols: ["AUR", "KDK"] },
  { name: "Advanced Air Mobility", symbols: ["JOBY", "ACHR"] },
  { name: "AI Healthcare", symbols: ["TEM", "RXRX"] },
];

function annualReturns(dashboard: DashboardPayload) {
  const output: Record<string, number> = {};
  for (const row of dashboard.backtest.rows) {
    if (
      typeof row.monthlyReturn !== "number" ||
      row.provisional
    ) continue;
    const year = row.signalMonth.slice(0, 4);
    output[year] = (1 + (output[year] ?? 0)) * (1 + row.monthlyReturn) - 1;
  }
  return output;
}

function metrics(dashboard: DashboardPayload) {
  const stats = dashboard.backtest.stats;
  return {
    cagr: stats.cagr,
    maxDrawdown: stats.maxDrawdown,
    annualizedVolatility: stats.annualizedVolatility,
    finalEquity: stats.finalEquity,
    averageMonthlyReturn: stats.averageMonthlyReturn,
    calmar:
      stats.maxDrawdown < 0 ? stats.cagr / Math.abs(stats.maxDrawdown) : null,
    annualReturns: annualReturns(dashboard),
  };
}

function compareRows(
  baseline: DashboardPayload,
  variant: DashboardPayload,
  candidateSymbols: string[],
) {
  const baseByMonth = new Map(
    baseline.backtest.rows.map((row) => [row.signalMonth, row]),
  );
  const candidateSet = new Set(candidateSymbols);
  const selectedMonths: Array<{
    signalMonth: string;
    picks: string[];
    candidatePicks: string[];
    monthlyReturn: number | null;
    provisional: boolean;
  }> = [];
  const changedMonths: Array<{
    signalMonth: string;
    removed: string[];
    added: string[];
  }> = [];
  const displacedCounts = new Map<string, number>();

  for (const row of variant.backtest.rows) {
    const candidatePicks = row.picks.filter((symbol) => candidateSet.has(symbol));
    if (candidatePicks.length) {
      selectedMonths.push({
        signalMonth: row.signalMonth,
        picks: row.picks,
        candidatePicks,
        monthlyReturn: row.monthlyReturn,
        provisional: Boolean(row.provisional),
      });
    }

    const base = baseByMonth.get(row.signalMonth);
    if (!base) continue;
    const removed = base.picks.filter((symbol) => !row.picks.includes(symbol));
    const added = row.picks.filter((symbol) => !base.picks.includes(symbol));
    if (removed.length || added.length || base.market !== row.market) {
      changedMonths.push({ signalMonth: row.signalMonth, removed, added });
      for (const symbol of removed) {
        displacedCounts.set(symbol, (displacedCounts.get(symbol) ?? 0) + 1);
      }
    }
  }

  return {
    selectedMonthCount: selectedMonths.length,
    completedSelectedMonthCount: selectedMonths.filter((row) => !row.provisional).length,
    selectedMonths,
    changedMonthCount: changedMonths.length,
    changedMonths,
    mostDisplaced: [...displacedCounts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([symbol, count]) => ({ symbol, count })),
  };
}

async function main() {
  const allSymbols = [
    ...new Set([
      ...TICKERS.map((ticker) => ticker.symbol),
      ...CANDIDATES.map((ticker) => ticker.symbol),
    ]),
  ];
  console.log(`Fetching ${allSymbols.length} symbols...`);
  const histories = await fetchHistories(allSymbols);

  const baseline = buildDashboard(histories, TICKERS, FROZEN_STRATEGY);
  const cases: Array<{
    name: string;
    kind: "single" | "theme";
    symbols: string[];
    dashboard: DashboardPayload;
  }> = [];

  for (const candidate of CANDIDATES) {
    cases.push({
      name: `+${candidate.symbol}`,
      kind: "single",
      symbols: [candidate.symbol],
      dashboard: buildDashboard(
        histories,
        [...TICKERS, candidate],
        FROZEN_STRATEGY,
      ),
    });
  }

  for (const theme of THEMES) {
    const additions = CANDIDATES.filter((candidate) =>
      theme.symbols.includes(candidate.symbol),
    );
    cases.push({
      name: `+${theme.name}`,
      kind: "theme",
      symbols: theme.symbols,
      dashboard: buildDashboard(
        histories,
        [...TICKERS, ...additions],
        FROZEN_STRATEGY,
      ),
    });
  }

  const baselineMetrics = metrics(baseline);
  const results = cases.map((item) => {
    const variantMetrics = metrics(item.dashboard);
    return {
      name: item.name,
      kind: item.kind,
      symbols: item.symbols,
      metrics: variantMetrics,
      delta: {
        cagr: variantMetrics.cagr - baselineMetrics.cagr,
        maxDrawdown:
          variantMetrics.maxDrawdown - baselineMetrics.maxDrawdown,
        annualizedVolatility:
          variantMetrics.annualizedVolatility -
          baselineMetrics.annualizedVolatility,
        finalEquity:
          variantMetrics.finalEquity - baselineMetrics.finalEquity,
        calmar:
          variantMetrics.calmar !== null && baselineMetrics.calmar !== null
            ? variantMetrics.calmar - baselineMetrics.calmar
            : null,
      },
      selection: compareRows(baseline, item.dashboard, item.symbols),
    };
  });

  const output = {
    generatedAt: new Date().toISOString(),
    purpose:
      "Research-only historical fit check. Do not adopt candidates from this output alone.",
    frozenStrategy: FROZEN_STRATEGY,
    baseline: baselineMetrics,
    candidates: CANDIDATES,
    results,
  };

  const path = resolve("artifacts/candidate-research.json");
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, JSON.stringify(output, null, 2), "utf8");

  console.log("BASELINE", JSON.stringify(baselineMetrics));
  for (const result of results) {
    console.log(
      "CASE",
      result.name,
      JSON.stringify({
        cagr: result.metrics.cagr,
        dd: result.metrics.maxDrawdown,
        vol: result.metrics.annualizedVolatility,
        calmar: result.metrics.calmar,
        deltaCagr: result.delta.cagr,
        selectedMonths: result.selection.selectedMonthCount,
        changedMonths: result.selection.changedMonthCount,
      }),
    );
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
