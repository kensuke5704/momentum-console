import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { z } from "zod";
import { FROZEN_STRATEGY_ID } from "../src/lib/frozen-strategy";
import type { BacktestRow } from "../src/lib/types";

const selectionStateSchema = z.enum([
  "selected",
  "below-qqq",
  "surge-excluded",
  "genre-limit",
  "frontier-limit",
  "not-enough-history",
  "other-ineligible",
  "eligible-not-selected",
  "cash-market",
]);

const tickerSchema = z.object({
  symbol: z.string().min(1),
  genre: z.string().min(1),
  score: z.number().finite().nullable(),
  rank: z.number().int().positive().nullable(),
  eligible: z.boolean(),
  selected: z.boolean(),
  reason: z.string().min(1),
  oneMonth: z.number().finite().nullable(),
  threeMonth: z.number().finite().nullable(),
  sixMonth: z.number().finite().nullable(),
  holdingReturn: z.number().finite().nullable(),
  selectionState: selectionStateSchema,
});

const monthSchema = z.object({
  signalMonth: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  entryDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).nullable(),
  exitDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).nullable(),
  market: z.enum(["RiskOn", "Cash", "Unknown", "Not enough candidates"]),
  completed: z.boolean(),
  strategyReturn: z.number().finite().nullable(),
  universeSymbols: z.array(z.string().min(1)),
  selectedSymbols: z.array(z.string().min(1)),
  tickers: z.array(tickerSchema),
});

const summarySchema = z.object({
  genre: z.string().min(1),
  observedMonths: z.number().int().nonnegative(),
  eligibleMonths: z.number().int().nonnegative(),
  selectedMonths: z.number().int().nonnegative(),
  selectionRate: z.number().min(0).max(1),
  selectedWins: z.number().int().nonnegative(),
  selectedLosses: z.number().int().nonnegative(),
  averageSelectedHoldingReturn: z.number().finite().nullable(),
  cumulativeSelectedHoldingReturn: z.number().finite().nullable(),
  averageAllHoldingReturn: z.number().finite().nullable(),
  latestRank: z.number().int().positive().nullable(),
  latestScore: z.number().finite().nullable(),
  lastSelectedSignalMonth: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).nullable(),
  surgeExcludedMonths: z.number().int().nonnegative(),
  belowQqqMonths: z.number().int().nonnegative(),
  genreLimitedMonths: z.number().int().nonnegative(),
  frontierLimitedMonths: z.number().int().nonnegative(),
});

const monitoringSchema = z.object({
  version: z.literal(1),
  strategyId: z.string().min(1),
  monitoringStart: z.string().regex(/^\d{4}-\d{2}$/),
  updatedAt: z.string().datetime(),
  latestCompletedSignalMonth: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).nullable(),
  months: z.array(monthSchema),
  summary: z.record(z.string(), summarySchema),
});

type Monitoring = z.infer<typeof monitoringSchema>;
type Month = z.infer<typeof monthSchema>;
type Summary = z.infer<typeof summarySchema>;

type OosFile = {
  frozen: { id: string };
  rows: BacktestRow[];
};

function mean(values: number[]) {
  return values.length
    ? values.reduce((sum, value) => sum + value, 0) / values.length
    : null;
}

function recalculateSummary(months: Month[]) {
  const output: Record<string, Summary> = {};
  const symbols = new Set(months.flatMap((month) => month.universeSymbols));

  for (const symbol of symbols) {
    const observations = months
      .flatMap((month) =>
        month.tickers
          .filter((ticker) => ticker.symbol === symbol)
          .map((ticker) => ({ month, ticker })),
      )
      .sort((a, b) => a.month.signalMonth.localeCompare(b.month.signalMonth));
    if (!observations.length) continue;

    const completed = observations.filter(({ month }) => month.completed);
    const selectedReturns = completed
      .filter(({ ticker }) => ticker.selected && ticker.holdingReturn !== null)
      .map(({ ticker }) => ticker.holdingReturn as number);
    const allReturns = completed
      .filter(({ ticker }) => ticker.holdingReturn !== null)
      .map(({ ticker }) => ticker.holdingReturn as number);
    const selected = observations.filter(({ ticker }) => ticker.selected);
    const latest = observations.at(-1)!;

    output[symbol] = {
      genre: latest.ticker.genre,
      observedMonths: observations.length,
      eligibleMonths: observations.filter(({ ticker }) => ticker.eligible).length,
      selectedMonths: selected.length,
      selectionRate: selected.length / observations.length,
      selectedWins: selectedReturns.filter((value) => value > 0).length,
      selectedLosses: selectedReturns.filter((value) => value < 0).length,
      averageSelectedHoldingReturn: mean(selectedReturns),
      cumulativeSelectedHoldingReturn: selectedReturns.length
        ? selectedReturns.reduce((equity, value) => equity * (1 + value), 1) - 1
        : null,
      averageAllHoldingReturn: mean(allReturns),
      latestRank: latest.ticker.rank,
      latestScore: latest.ticker.score,
      lastSelectedSignalMonth: selected.at(-1)?.month.signalMonth ?? null,
      surgeExcludedMonths: observations.filter(
        ({ ticker }) => ticker.selectionState === "surge-excluded",
      ).length,
      belowQqqMonths: observations.filter(
        ({ ticker }) => ticker.selectionState === "below-qqq",
      ).length,
      genreLimitedMonths: observations.filter(
        ({ ticker }) => ticker.selectionState === "genre-limit",
      ).length,
      frontierLimitedMonths: observations.filter(
        ({ ticker }) => ticker.selectionState === "frontier-limit",
      ).length,
    };
  }

  return output;
}

function sameNumber(a: number | null, b: number | null) {
  if (a === null || b === null) return a === b;
  return Math.abs(a - b) <= 1e-12;
}

function assertSummaryEqual(actual: Monitoring["summary"], expected: Record<string, Summary>) {
  const actualSymbols = Object.keys(actual).sort();
  const expectedSymbols = Object.keys(expected).sort();
  if (JSON.stringify(actualSymbols) !== JSON.stringify(expectedSymbols)) {
    throw new Error("summary symbol set does not match raw observations");
  }

  for (const symbol of expectedSymbols) {
    const a = actual[symbol];
    const e = expected[symbol];
    for (const key of Object.keys(e) as Array<keyof Summary>) {
      const av = a[key];
      const ev = e[key];
      if (typeof av === "number" || typeof ev === "number") {
        if (!sameNumber(av as number | null, ev as number | null)) {
          throw new Error(`${symbol}: summary.${key} does not match raw observations`);
        }
      } else if (av !== ev) {
        throw new Error(`${symbol}: summary.${key} does not match raw observations`);
      }
    }
  }
}

async function main() {
  const monitoring = monitoringSchema.parse(
    JSON.parse(await readFile(resolve("data/universe-monitoring.json"), "utf8")),
  );
  const oos = JSON.parse(
    await readFile(resolve("public/data/oos-performance.json"), "utf8"),
  ) as OosFile;

  if (monitoring.strategyId !== FROZEN_STRATEGY_ID) {
    throw new Error(`strategyId=${monitoring.strategyId} does not match ${FROZEN_STRATEGY_ID}`);
  }
  if (oos.frozen.id !== FROZEN_STRATEGY_ID) {
    throw new Error(`OOS strategyId=${oos.frozen.id} does not match ${FROZEN_STRATEGY_ID}`);
  }

  const signalMonths = new Set<string>();
  const oosBySignalMonth = new Map(oos.rows.map((row) => [row.signalMonth, row]));

  for (const month of monitoring.months) {
    if (signalMonths.has(month.signalMonth)) {
      throw new Error(`Duplicate signalMonth: ${month.signalMonth}`);
    }
    signalMonths.add(month.signalMonth);

    const tickerSymbols = month.tickers.map((ticker) => ticker.symbol);
    if (new Set(tickerSymbols).size !== tickerSymbols.length) {
      throw new Error(`${month.signalMonth}: duplicate ticker symbol`);
    }
    if (new Set(month.universeSymbols).size !== month.universeSymbols.length) {
      throw new Error(`${month.signalMonth}: duplicate universe symbol`);
    }
    if (
      JSON.stringify([...tickerSymbols].sort()) !==
      JSON.stringify([...month.universeSymbols].sort())
    ) {
      throw new Error(`${month.signalMonth}: universeSymbols do not match ticker symbols`);
    }

    const selectedFromTickers = month.tickers
      .filter((ticker) => ticker.selected)
      .map((ticker) => ticker.symbol)
      .sort();
    if (
      JSON.stringify(selectedFromTickers) !==
      JSON.stringify([...month.selectedSymbols].sort())
    ) {
      throw new Error(`${month.signalMonth}: selectedSymbols do not match ticker.selected`);
    }
    for (const ticker of month.tickers) {
      if (ticker.selected && !month.selectedSymbols.includes(ticker.symbol)) {
        throw new Error(`${month.signalMonth}/${ticker.symbol}: selected symbol mismatch`);
      }
      if (!month.completed && ticker.holdingReturn !== null) {
        throw new Error(`${month.signalMonth}/${ticker.symbol}: provisional holdingReturn must be null`);
      }
    }

    const oosRow = oosBySignalMonth.get(month.signalMonth);
    if (!oosRow) throw new Error(`${month.signalMonth}: missing corresponding OOS row`);
    const oosCompleted = !oosRow.provisional && typeof oosRow.monthlyReturn === "number";
    if (month.completed !== oosCompleted) {
      throw new Error(`${month.signalMonth}: completed flag does not match OOS`);
    }
    if (month.entryDate !== oosRow.entryDate || month.exitDate !== oosRow.exitDate) {
      throw new Error(`${month.signalMonth}: entryDate/exitDate do not match OOS`);
    }
    if (month.market !== oosRow.market) {
      throw new Error(`${month.signalMonth}: market does not match OOS`);
    }
    if (
      JSON.stringify([...month.selectedSymbols].sort()) !==
      JSON.stringify([...oosRow.picks].sort())
    ) {
      throw new Error(`${month.signalMonth}: selectedSymbols do not match OOS picks`);
    }
    if (!sameNumber(month.strategyReturn, oosCompleted ? oosRow.monthlyReturn : null)) {
      throw new Error(`${month.signalMonth}: strategyReturn does not match OOS`);
    }
  }

  const latestCompleted = monitoring.months
    .filter((month) => month.completed)
    .map((month) => month.signalMonth)
    .sort()
    .at(-1) ?? null;
  if (monitoring.latestCompletedSignalMonth !== latestCompleted) {
    throw new Error("latestCompletedSignalMonth is incorrect");
  }

  assertSummaryEqual(monitoring.summary, recalculateSummary(monitoring.months));
  console.log(
    `Universe monitoring valid: ${monitoring.months.length} months, ${Object.keys(monitoring.summary).length} tickers`,
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
