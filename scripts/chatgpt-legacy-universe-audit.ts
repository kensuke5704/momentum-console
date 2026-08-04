import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { TICKERS } from "../src/lib/config";
import { FROZEN_STRATEGY } from "../src/lib/frozen-strategy";
import { buildDashboard } from "../src/lib/momentum";
import type { BacktestRow, PricePoint } from "../src/lib/types";
import { fetchHistories } from "../src/lib/yahoo";

const AUDIT_START = "2020-01-01";
const AUDIT_END = "2022-12-31";
const OUTPUT = resolve("artifacts/legacy-universe-audit.json");

type AuditClass = "A" | "B" | "C" | "D" | "BENCHMARK";

type SelectionObservation = {
  signalMonth: string;
  entryDate: string;
  exitDate: string;
  holdingReturn: number;
};

function monthKey(date: string) {
  return date.slice(0, 7);
}

function monthlyMap(points: PricePoint[]) {
  const map = new Map<string, number>();
  for (const point of points) map.set(monthKey(point.date), point.close);
  return map;
}

function monthlyKeys(points: PricePoint[]) {
  const set = new Set<string>();
  for (const point of points) set.add(monthKey(point.date));
  return [...set].sort();
}

function addDays(date: string, days: number) {
  const value = new Date(`${date}T00:00:00Z`);
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
}

function nextMonthEnd(signalMonth: string) {
  const [year, month] = signalMonth.slice(0, 7).split("-").map(Number);
  return new Date(Date.UTC(year, month + 1, 0)).toISOString().slice(0, 10);
}

function priceOnOrAfter(points: PricePoint[], date: string) {
  return points.find((point) => point.date >= date) ?? null;
}

function mean(values: number[]) {
  if (!values.length) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function stdev(values: number[]) {
  if (values.length <= 1) return 0;
  const avg = values.reduce((sum, value) => sum + value, 0) / values.length;
  return Math.sqrt(
    values.reduce((sum, value) => sum + (value - avg) ** 2, 0) /
      (values.length - 1),
  );
}

function periodStats(rows: BacktestRow[]) {
  const completed = rows.filter(
    (row) => typeof row.monthlyReturn === "number" && !row.provisional,
  );
  const returns = completed.map((row) => row.monthlyReturn as number);
  let equity = 1;
  let peak = 1;
  let maxDrawdown = 0;
  for (const value of returns) {
    equity *= 1 + value;
    peak = Math.max(peak, equity);
    maxDrawdown = Math.min(maxDrawdown, equity / peak - 1);
  }

  const annualReturns: Record<string, number> = {};
  for (const row of completed) {
    const year = row.signalMonth.slice(0, 4);
    annualReturns[year] =
      (1 + (annualReturns[year] ?? 0)) * (1 + (row.monthlyReturn as number)) - 1;
  }

  return {
    completedMonths: returns.length,
    finalEquity: equity,
    cumulativeReturn: equity - 1,
    cagr: returns.length ? equity ** (12 / returns.length) - 1 : null,
    averageMonthlyReturn: mean(returns),
    annualizedVolatility: stdev(returns) * Math.sqrt(12),
    maxDrawdown,
    annualReturns,
  };
}

function qqqBenchmark(rows: BacktestRow[], qqq: PricePoint[]) {
  const benchmarkRows: BacktestRow[] = [];
  let equity = 1;
  for (const row of rows) {
    const entry = priceOnOrAfter(qqq, addDays(row.signalMonth, 1));
    const exit = priceOnOrAfter(qqq, addDays(nextMonthEnd(row.signalMonth), 1));
    if (!entry || !exit) continue;
    const monthlyReturn = exit.close / entry.close - 1;
    equity *= 1 + monthlyReturn;
    benchmarkRows.push({
      signalMonth: row.signalMonth,
      entryDate: entry.date,
      exitDate: exit.date,
      market: "RiskOn",
      picks: ["QQQ"],
      monthlyReturn,
      equity,
    });
  }
  return periodStats(benchmarkRows);
}

function selectionObservation(
  row: BacktestRow,
  history: PricePoint[],
): SelectionObservation | null {
  if (!row.entryDate || !row.exitDate) return null;
  const entry = priceOnOrAfter(history, row.entryDate);
  const exit = priceOnOrAfter(history, row.exitDate);
  if (!entry || !exit) return null;
  return {
    signalMonth: row.signalMonth,
    entryDate: entry.date,
    exitDate: exit.date,
    holdingReturn: exit.close / entry.close - 1,
  };
}

async function main() {
  const symbols = [...new Set(TICKERS.map((ticker) => ticker.symbol))];
  const histories = await fetchHistories(symbols);
  const auditStrategy = { ...FROZEN_STRATEGY, backtestStart: AUDIT_START };
  const dashboard = buildDashboard(histories, TICKERS, auditStrategy);
  const auditRows = dashboard.backtest.rows.filter(
    (row) => row.signalMonth >= AUDIT_START && row.signalMonth <= AUDIT_END,
  );

  const qqqKeys = monthlyKeys(histories.QQQ ?? []);
  const qqqIndex = new Map(qqqKeys.map((key, index) => [key, index]));
  const signalKeys = auditRows.map((row) => monthKey(row.signalMonth));

  const tickerResults = TICKERS.map((ticker) => {
    if (ticker.symbol === "QQQ") {
      return {
        symbol: ticker.symbol,
        genre: ticker.genre,
        classification: "BENCHMARK" as AuditClass,
        rationale: "QQQ is the benchmark / risk filter and is not an investable candidate.",
      };
    }

    const history = histories[ticker.symbol] ?? [];
    const map = monthlyMap(history);
    const testableSignalMonths = signalKeys.filter((key) => {
      const index = qqqIndex.get(key);
      if (index === undefined || index < 6) return false;
      return [index, index - 1, index - 3, index - 6].every((position) => {
        const qqqKey = qqqKeys[position];
        return qqqKey ? map.has(qqqKey) : false;
      });
    });

    const selectedRows = auditRows.filter((row) => row.picks.includes(ticker.symbol));
    const observations = selectedRows
      .map((row) => selectionObservation(row, history))
      .filter((value): value is SelectionObservation => value !== null);
    const holdingReturns = observations.map((item) => item.holdingReturn);
    const avg = mean(holdingReturns);
    const wins = holdingReturns.filter((value) => value > 0).length;
    const winRate = holdingReturns.length ? wins / holdingReturns.length : null;

    let classification: AuditClass;
    let rationale: string;
    if (!testableSignalMonths.length) {
      classification = "C";
      rationale = "Insufficient usable pre-2023 history for the required 1M/3M/6M lookbacks.";
    } else if (
      observations.length >= 3 &&
      avg !== null && avg > 0 &&
      winRate !== null && winRate >= 0.5
    ) {
      classification = "A";
      rationale = "Selected at least 3 times with positive average selected-month return and win rate >= 50%.";
    } else if (
      observations.length >= 3 &&
      avg !== null && avg < 0 &&
      winRate !== null && winRate < 0.5
    ) {
      classification = "D";
      rationale = "Selected at least 3 times with negative average selected-month return and win rate < 50%; review only, no automatic removal.";
    } else {
      classification = "B";
      rationale = observations.length < 3
        ? "Usable pre-2023 history exists, but fewer than 3 completed selections provide limited evidence."
        : "Usable pre-2023 history exists, but selected-month outcomes are mixed and meet neither A nor D.";
    }

    return {
      symbol: ticker.symbol,
      genre: ticker.genre,
      classification,
      rationale,
      firstPriceDate: history.at(0)?.date ?? null,
      lastPre2023PriceDate:
        [...history].reverse().find((point) => point.date <= AUDIT_END)?.date ?? null,
      testableSignalMonths: testableSignalMonths.length,
      selectedMonths: observations.length,
      wins,
      losses: holdingReturns.length - wins,
      winRate,
      averageSelectedHoldingReturn: avg,
      cumulativeSelectedReturn: holdingReturns.reduce(
        (equityValue, value) => equityValue * (1 + value),
        1,
      ) - 1,
      observations,
    };
  });

  const classificationCounts = tickerResults.reduce<Record<string, number>>(
    (counts, item) => {
      counts[item.classification] = (counts[item.classification] ?? 0) + 1;
      return counts;
    },
    {},
  );

  const genreSummary = [...new Set(TICKERS.map((ticker) => ticker.genre))]
    .map((genre) => {
      const members = tickerResults.filter(
        (item) => item.genre === genre && item.classification !== "BENCHMARK",
      );
      return {
        genre,
        tickers: members.map((item) => item.symbol),
        classifications: members.reduce<Record<string, number>>((acc, item) => {
          acc[item.classification] = (acc[item.classification] ?? 0) + 1;
          return acc;
        }, {}),
        totalSelectedMonths: members.reduce(
          (sum, item) => sum + ("selectedMonths" in item ? item.selectedMonths : 0),
          0,
        ),
      };
    })
    .filter((item) => item.tickers.length > 0);

  const result = {
    generatedAt: new Date().toISOString(),
    purpose:
      "Diagnostic legacy Universe audit only. Do not optimize removals or strategy parameters on this sample.",
    policy: {
      A: "At least 3 completed pre-2023 selections, positive average selected-month holding return, win rate >= 50%.",
      B: "Usable pre-2023 history exists but evidence is limited or mixed; meets neither A nor D.",
      C: "Insufficient usable pre-2023 history for required momentum lookbacks.",
      D: "At least 3 completed pre-2023 selections, negative average selected-month holding return, win rate < 50%. Review only; no automatic removal.",
      note: "No classification triggers automatic removal.",
    },
    methodology: {
      dataSource: "src/lib/yahoo.ts via fetchHistories",
      strategyEngine: "src/lib/momentum.ts via buildDashboard",
      frozenStrategy: FROZEN_STRATEGY,
      auditStrategy,
      requestedWindow: { start: AUDIT_START, end: AUDIT_END },
      effectiveFirstSignal: auditRows.at(0)?.signalMonth ?? null,
      effectiveLastSignal: auditRows.at(-1)?.signalMonth ?? null,
      note: "Yahoo history begins 2020-01-01 and the strategy requires MA/lookback warm-up, so early 2020 cannot generate a valid signal.",
    },
    portfolioAudit: periodStats(auditRows),
    qqqBenchmark: qqqBenchmark(auditRows, histories.QQQ ?? []),
    rowCounts: {
      totalAuditRows: auditRows.length,
      riskOnInvestedMonths: auditRows.filter((row) => row.market === "RiskOn").length,
      cashMarketMonths: auditRows.filter((row) => row.market === "Cash").length,
      insufficientCandidateMonths: auditRows.filter(
        (row) => row.market === "Not enough candidates",
      ).length,
    },
    classificationCounts,
    tickerResults,
    genreSummary,
  };

  await mkdir(resolve("artifacts"), { recursive: true });
  await writeFile(OUTPUT, JSON.stringify(result, null, 2), "utf8");

  console.log("LEGACY AUDIT SUMMARY", JSON.stringify({
    effectiveFirstSignal: result.methodology.effectiveFirstSignal,
    effectiveLastSignal: result.methodology.effectiveLastSignal,
    portfolioAudit: result.portfolioAudit,
    qqqBenchmark: result.qqqBenchmark,
    rowCounts: result.rowCounts,
    classificationCounts,
  }));

  for (const item of tickerResults) {
    if (item.classification === "BENCHMARK") continue;
    console.log(
      "TICKER",
      item.symbol,
      item.genre,
      item.classification,
      "selectedMonths" in item ? item.selectedMonths : null,
      "winRate" in item ? item.winRate : null,
      "averageSelectedHoldingReturn" in item
        ? item.averageSelectedHoldingReturn
        : null,
    );
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
