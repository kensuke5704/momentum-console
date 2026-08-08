import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { TICKERS } from "../src/lib/config";
import {
  FROZEN_STRATEGY,
  FROZEN_STRATEGY_FIRST_HOLDING_MONTH,
  FROZEN_STRATEGY_FIRST_SIGNAL_MONTH,
  FROZEN_STRATEGY_ID,
} from "../src/lib/frozen-strategy";
import { buildDashboard } from "../src/lib/momentum";
import type { BacktestRow, MomentumRow, PricePoint } from "../src/lib/types";
import { fetchHistories } from "../src/lib/yahoo";

type SelectionState =
  | "selected"
  | "below-qqq"
  | "surge-excluded"
  | "genre-limit"
  | "frontier-limit"
  | "not-enough-history"
  | "other-ineligible"
  | "eligible-not-selected"
  | "cash-market";

type TickerObservation = {
  symbol: string;
  genre: string;
  score: number | null;
  rank: number | null;
  eligible: boolean;
  selected: boolean;
  reason: string;
  oneMonth: number | null;
  threeMonth: number | null;
  sixMonth: number | null;
  holdingReturn: number | null;
  selectionState: SelectionState;
};

type MonthObservation = {
  signalMonth: string;
  entryDate: string | null;
  exitDate: string | null;
  market: BacktestRow["market"];
  completed: boolean;
  strategyReturn: number | null;
  universeSymbols: string[];
  selectedSymbols: string[];
  tickers: TickerObservation[];
};

type TickerSummary = {
  genre: string;
  observedMonths: number;
  eligibleMonths: number;
  selectedMonths: number;
  selectionRate: number;
  selectedWins: number;
  selectedLosses: number;
  averageSelectedHoldingReturn: number | null;
  cumulativeSelectedHoldingReturn: number | null;
  averageAllHoldingReturn: number | null;
  latestRank: number | null;
  latestScore: number | null;
  lastSelectedSignalMonth: string | null;
  surgeExcludedMonths: number;
  belowQqqMonths: number;
  genreLimitedMonths: number;
  frontierLimitedMonths: number;
};

type MonitoringFile = {
  version: 1;
  strategyId: string;
  monitoringStart: string;
  updatedAt: string;
  latestCompletedSignalMonth: string | null;
  months: MonthObservation[];
  summary: Record<string, TickerSummary>;
};

type OosFile = {
  frozen: { id: string };
  rows: BacktestRow[];
};

const outputPath = resolve("data/universe-monitoring.json");
const oosPath = resolve("public/data/oos-performance.json");
const productionTickers = TICKERS.filter((ticker) => ticker.symbol !== "QQQ");

function mean(values: number[]) {
  return values.length
    ? values.reduce((sum, value) => sum + value, 0) / values.length
    : null;
}

function priceOnOrAfter(points: PricePoint[] | undefined, date: string | null) {
  if (!points || !date) return null;
  return points.find((point) => point.date >= date) ?? null;
}

function truncateHistories(
  histories: Record<string, PricePoint[]>,
  signalMonth: string,
) {
  return Object.fromEntries(
    Object.entries(histories).map(([symbol, points]) => [
      symbol,
      points.filter((point) => point.date <= signalMonth),
    ]),
  );
}

function normalizeSelectionState(
  row: MomentumRow,
  market: BacktestRow["market"],
  selectedRows: MomentumRow[],
): SelectionState {
  if (market === "Cash") return "cash-market";
  if (row.selected) return "selected";
  if (row.reason === "QQQスコア以下") return "below-qqq";
  if (row.reason === "1か月急騰を除外") return "surge-excluded";
  if (row.reason === "データ不足") return "not-enough-history";

  if (row.eligible) {
    const sameGenreSelected = selectedRows.filter(
      (selected) => selected.genre === row.genre,
    ).length;
    if (sameGenreSelected >= FROZEN_STRATEGY.genreMax) return "genre-limit";

    if (FROZEN_STRATEGY.frontierGenres.includes(row.genre)) {
      const selectedFrontier = selectedRows.filter((selected) =>
        FROZEN_STRATEGY.frontierGenres.includes(selected.genre),
      ).length;
      if (selectedFrontier >= FROZEN_STRATEGY.frontierMax) {
        return "frontier-limit";
      }
    }
    return "eligible-not-selected";
  }

  return "other-ineligible";
}

function holdingReturn(
  histories: Record<string, PricePoint[]>,
  symbol: string,
  row: BacktestRow,
) {
  if (row.provisional || row.monthlyReturn === null || !row.entryDate || !row.exitDate) {
    return null;
  }
  const entry = priceOnOrAfter(histories[symbol], row.entryDate);
  const exit = priceOnOrAfter(histories[symbol], row.exitDate);
  if (!entry || !exit || exit.date < entry.date) return null;
  return exit.close / entry.close - 1;
}

function buildObservation(
  row: BacktestRow,
  histories: Record<string, PricePoint[]>,
): MonthObservation {
  const dashboard = buildDashboard(
    truncateHistories(histories, row.signalMonth),
    TICKERS,
    FROZEN_STRATEGY,
  );
  const selectedSet = new Set(row.picks);
  const momentumBySymbol = new Map(
    dashboard.momentum.map((item) => [item.symbol, item]),
  );
  const selectedRows = dashboard.momentum.filter((item) => selectedSet.has(item.symbol));
  const completed = !row.provisional && typeof row.monthlyReturn === "number";

  const tickers = productionTickers.map((ticker) => {
    const momentum = momentumBySymbol.get(ticker.symbol);
    if (!momentum) {
      throw new Error(`${row.signalMonth}: missing momentum row for ${ticker.symbol}`);
    }
    const normalizedRow = { ...momentum, selected: selectedSet.has(ticker.symbol) };
    return {
      symbol: ticker.symbol,
      genre: ticker.genre,
      score: momentum.score,
      rank: momentum.rank,
      eligible: momentum.eligible,
      selected: normalizedRow.selected,
      reason: momentum.reason,
      oneMonth: momentum.oneMonth,
      threeMonth: momentum.threeMonth,
      sixMonth: momentum.sixMonth,
      holdingReturn: completed
        ? holdingReturn(histories, ticker.symbol, row)
        : null,
      selectionState: normalizeSelectionState(normalizedRow, row.market, selectedRows),
    };
  });

  return {
    signalMonth: row.signalMonth,
    entryDate: row.entryDate,
    exitDate: row.exitDate,
    market: row.market,
    completed,
    strategyReturn: completed ? row.monthlyReturn : null,
    universeSymbols: productionTickers.map((ticker) => ticker.symbol),
    selectedSymbols: [...row.picks],
    tickers,
  };
}

function summarize(months: MonthObservation[]) {
  const summary: Record<string, TickerSummary> = {};
  const allSymbols = new Set(months.flatMap((month) => month.universeSymbols));

  for (const symbol of allSymbols) {
    const observations = months
      .flatMap((month) =>
        month.tickers
          .filter((ticker) => ticker.symbol === symbol)
          .map((ticker) => ({ month, ticker })),
      )
      .sort((a, b) => a.month.signalMonth.localeCompare(b.month.signalMonth));
    if (!observations.length) continue;

    const completed = observations.filter(({ month }) => month.completed);
    const selectedCompletedReturns = completed
      .filter(({ ticker }) => ticker.selected && ticker.holdingReturn !== null)
      .map(({ ticker }) => ticker.holdingReturn as number);
    const allCompletedReturns = completed
      .filter(({ ticker }) => ticker.holdingReturn !== null)
      .map(({ ticker }) => ticker.holdingReturn as number);
    const selectedObservations = observations.filter(({ ticker }) => ticker.selected);
    const latest = observations.at(-1)!;

    summary[symbol] = {
      genre: latest.ticker.genre,
      observedMonths: observations.length,
      eligibleMonths: observations.filter(({ ticker }) => ticker.eligible).length,
      selectedMonths: selectedObservations.length,
      selectionRate: selectedObservations.length / observations.length,
      selectedWins: selectedCompletedReturns.filter((value) => value > 0).length,
      selectedLosses: selectedCompletedReturns.filter((value) => value < 0).length,
      averageSelectedHoldingReturn: mean(selectedCompletedReturns),
      cumulativeSelectedHoldingReturn: selectedCompletedReturns.length
        ? selectedCompletedReturns.reduce((equity, value) => equity * (1 + value), 1) - 1
        : null,
      averageAllHoldingReturn: mean(allCompletedReturns),
      latestRank: latest.ticker.rank,
      latestScore: latest.ticker.score,
      lastSelectedSignalMonth: selectedObservations.at(-1)?.month.signalMonth ?? null,
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

  return summary;
}

async function readMonitoring(): Promise<MonitoringFile | null> {
  try {
    return JSON.parse(await readFile(outputPath, "utf8")) as MonitoringFile;
  } catch {
    return null;
  }
}

async function main() {
  const oos = JSON.parse(await readFile(oosPath, "utf8")) as OosFile;
  if (oos.frozen.id !== FROZEN_STRATEGY_ID) {
    throw new Error(`OOS strategyId=${oos.frozen.id} does not match ${FROZEN_STRATEGY_ID}`);
  }

  const existing = await readMonitoring();
  if (existing && existing.strategyId !== FROZEN_STRATEGY_ID) {
    throw new Error(`Monitoring strategyId=${existing.strategyId} does not match ${FROZEN_STRATEGY_ID}`);
  }

  const oosRows = oos.rows.filter(
    (row) => row.signalMonth.slice(0, 7) >= FROZEN_STRATEGY_FIRST_SIGNAL_MONTH,
  );
  const symbols = [...new Set(TICKERS.map((ticker) => ticker.symbol))];
  console.log(`Fetching ${symbols.length} symbols for Universe monitoring...`);
  const histories = await fetchHistories(symbols);
  const existingBySignalMonth = new Map(
    (existing?.months ?? []).map((month) => [month.signalMonth, month]),
  );
  const months: MonthObservation[] = [];

  for (const row of oosRows) {
    const previous = existingBySignalMonth.get(row.signalMonth);
    if (previous?.completed) {
      months.push(previous);
      continue;
    }
    months.push(buildObservation(row, histories));
  }

  for (const previous of existing?.months ?? []) {
    if (!months.some((month) => month.signalMonth === previous.signalMonth)) {
      months.push(previous);
    }
  }

  months.sort((a, b) => a.signalMonth.localeCompare(b.signalMonth));
  const completedMonths = months.filter((month) => month.completed);
  const output: MonitoringFile = {
    version: 1,
    strategyId: FROZEN_STRATEGY_ID,
    monitoringStart: FROZEN_STRATEGY_FIRST_HOLDING_MONTH,
    updatedAt: new Date().toISOString(),
    latestCompletedSignalMonth: completedMonths.at(-1)?.signalMonth ?? null,
    months,
    summary: summarize(months),
  };

  await mkdir(dirname(outputPath), { recursive: true });
  await writeFile(outputPath, JSON.stringify(output, null, 2), "utf8");
  console.log(`Saved ${outputPath}`);
  console.log(`Tracked signal months: ${months.length}`);
  console.log(`Completed signal months: ${completedMonths.length}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
