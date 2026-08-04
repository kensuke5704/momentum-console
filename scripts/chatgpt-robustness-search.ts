import { mkdir, writeFile } from "node:fs/promises";
import { buildDashboard } from "../src/lib/momentum";
import { DEFAULT_STRATEGY, TICKERS } from "../src/lib/config";
import { fetchHistories } from "../src/lib/yahoo";
import type { BacktestRow, StrategyConfig } from "../src/lib/types";

type Stats = {
  finalEquity: number;
  cagr: number;
  averageMonthlyReturn: number;
  annualizedVolatility: number;
  maxDrawdown: number;
  calmar: number;
  months: number;
};

type Result = {
  name: string;
  params: {
    topN: number;
    qqqMaMonths: number;
    weights: StrategyConfig["weights"];
    surgeLimit: number;
    genreMax: number;
    frontierMax: number;
  };
  full: Stats;
  firstHalf: Stats;
  secondHalf: Stats;
  yearly: Record<string, Stats>;
  insufficientMonths: number;
  changedMonths: number;
};

function cloneStrategy(): StrategyConfig {
  return {
    ...DEFAULT_STRATEGY,
    weights: { ...DEFAULT_STRATEGY.weights },
    frontierGenres: [...DEFAULT_STRATEGY.frontierGenres],
    excludedTickers: [...DEFAULT_STRATEGY.excludedTickers],
  };
}

function mean(values: number[]) {
  return values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0;
}

function stdev(values: number[]) {
  if (values.length <= 1) return 0;
  const m = mean(values);
  return Math.sqrt(values.reduce((sum, value) => sum + (value - m) ** 2, 0) / (values.length - 1));
}

function statsFromRows(rows: BacktestRow[], predicate: (row: BacktestRow) => boolean = () => true): Stats {
  const returns = rows
    .filter(predicate)
    .filter((row) => typeof row.monthlyReturn === "number" && !row.provisional)
    .map((row) => row.monthlyReturn as number);
  if (!returns.length) {
    return { finalEquity: 1, cagr: 0, averageMonthlyReturn: 0, annualizedVolatility: 0, maxDrawdown: 0, calmar: 0, months: 0 };
  }
  let equity = 1;
  let peak = 1;
  let maxDrawdown = 0;
  for (const r of returns) {
    equity *= 1 + r;
    peak = Math.max(peak, equity);
    maxDrawdown = Math.min(maxDrawdown, equity / peak - 1);
  }
  const cagr = equity > 0 ? equity ** (12 / returns.length) - 1 : 0;
  return {
    finalEquity: equity,
    cagr,
    averageMonthlyReturn: mean(returns),
    annualizedVolatility: stdev(returns) * Math.sqrt(12),
    maxDrawdown,
    calmar: maxDrawdown < 0 ? cagr / Math.abs(maxDrawdown) : Number.POSITIVE_INFINITY,
    months: returns.length,
  };
}

function rowsMap(rows: BacktestRow[]) {
  return new Map(rows.map((row) => [row.signalMonth, row]));
}

function countChangedMonths(rows: BacktestRow[], baselineRows: BacktestRow[]) {
  const a = rowsMap(baselineRows);
  const b = rowsMap(rows);
  const months = new Set([...a.keys(), ...b.keys()]);
  let changed = 0;
  for (const month of months) {
    const x = a.get(month);
    const y = b.get(month);
    const xp = x?.picks ?? [];
    const yp = y?.picks ?? [];
    const xr = typeof x?.monthlyReturn === "number" ? x.monthlyReturn : null;
    const yr = typeof y?.monthlyReturn === "number" ? y.monthlyReturn : null;
    if (xp.join("|") !== yp.join("|") || xr !== yr) changed += 1;
  }
  return changed;
}

function summarize(name: string, strategy: StrategyConfig, rows: BacktestRow[], baselineRows: BacktestRow[]): Result {
  const yearly: Record<string, Stats> = {};
  for (const year of ["2023", "2024", "2025", "2026"]) {
    yearly[year] = statsFromRows(rows, (row) => row.signalMonth.startsWith(year));
  }
  return {
    name,
    params: {
      topN: strategy.topN,
      qqqMaMonths: strategy.qqqMaMonths,
      weights: { ...strategy.weights },
      surgeLimit: strategy.surgeLimit,
      genreMax: strategy.genreMax,
      frontierMax: strategy.frontierMax,
    },
    full: statsFromRows(rows),
    firstHalf: statsFromRows(rows, (row) => row.signalMonth < "2025-01-01"),
    secondHalf: statsFromRows(rows, (row) => row.signalMonth >= "2025-01-01"),
    yearly,
    insufficientMonths: rows.filter((row) => row.market === "Not enough candidates").length,
    changedMonths: countChangedMonths(rows, baselineRows),
  };
}

function makeStrategy(patch: Partial<StrategyConfig> & { weights?: StrategyConfig["weights"] }) {
  const s = cloneStrategy();
  Object.assign(s, patch);
  if (patch.weights) s.weights = { ...patch.weights };
  return s;
}

function withinYear(row: BacktestRow, year: string) {
  return row.signalMonth.startsWith(year);
}

function pct(v: number) { return Number((v * 100).toFixed(4)); }

async function main() {
  const symbols = TICKERS.map((ticker) => ticker.symbol);
  const histories = await fetchHistories(symbols);
  const baselineStrategy = cloneStrategy();
  const baselineDashboard = buildDashboard(histories, TICKERS, baselineStrategy);
  const baselineRows = baselineDashboard.backtest.rows;
  const baseline = summarize("Baseline current main", baselineStrategy, baselineRows, baselineRows);

  const perturbations: Result[] = [baseline];
  const runPerturbation = (name: string, strategy: StrategyConfig) => {
    const dashboard = buildDashboard(histories, TICKERS, strategy);
    perturbations.push(summarize(name, strategy, dashboard.backtest.rows, baselineRows));
  };

  for (const topN of [8, 9, 10, 11, 12]) {
    if (topN === baselineStrategy.topN) continue;
    runPerturbation(`TopN ${topN}`, makeStrategy({ topN }));
  }
  for (const qqqMaMonths of [8, 9, 10, 11, 12]) {
    if (qqqMaMonths === baselineStrategy.qqqMaMonths) continue;
    runPerturbation(`QQQ MA ${qqqMaMonths}`, makeStrategy({ qqqMaMonths }));
  }
  const weightVariants: Array<[string, StrategyConfig["weights"]]> = [
    ["W 10/40/50", { oneMonth: 0.1, threeMonth: 0.4, sixMonth: 0.5 }],
    ["W 20/30/50", { oneMonth: 0.2, threeMonth: 0.3, sixMonth: 0.5 }],
    ["W 20/40/40", { oneMonth: 0.2, threeMonth: 0.4, sixMonth: 0.4 }],
    ["W 20/50/30", { oneMonth: 0.2, threeMonth: 0.5, sixMonth: 0.3 }],
    ["W 30/30/40", { oneMonth: 0.3, threeMonth: 0.3, sixMonth: 0.4 }],
    ["W 30/40/30", { oneMonth: 0.3, threeMonth: 0.4, sixMonth: 0.3 }],
  ];
  for (const [name, weights] of weightVariants) {
    if (name === "W 20/40/40") continue;
    runPerturbation(name, makeStrategy({ weights }));
  }
  for (const surgeLimit of [0.6, 0.7, 0.8, 0.9, 1.0]) {
    if (surgeLimit === baselineStrategy.surgeLimit) continue;
    runPerturbation(`Surge ${Math.round(surgeLimit * 100)}%`, makeStrategy({ surgeLimit }));
  }
  for (const genreMax of [1, 2, 3]) {
    if (genreMax === baselineStrategy.genreMax) continue;
    runPerturbation(`GenreMax ${genreMax}`, makeStrategy({ genreMax }));
  }
  for (const frontierMax of [1, 2, 3]) {
    if (frontierMax === baselineStrategy.frontierMax) continue;
    runPerturbation(`FrontierMax ${frontierMax}`, makeStrategy({ frontierMax }));
  }

  // Prespecified narrow grid around current settings. Structural caps stay fixed at current main.
  const topNs = [9, 10, 11];
  const maMonths = [9, 10, 11];
  const gridWeights = weightVariants.map(([, weights]) => weights);
  const surgeLimits = [0.7, 0.8, 0.9];
  const grid: Result[] = [];
  for (const topN of topNs) {
    for (const qqqMaMonths of maMonths) {
      for (const weights of gridWeights) {
        for (const surgeLimit of surgeLimits) {
          const strategy = makeStrategy({ topN, qqqMaMonths, weights, surgeLimit, genreMax: 2, frontierMax: 2 });
          const dashboard = buildDashboard(histories, TICKERS, strategy);
          const name = `N${topN}-MA${qqqMaMonths}-W${Math.round(weights.oneMonth*10)}${Math.round(weights.threeMonth*10)}${Math.round(weights.sixMonth*10)}-S${Math.round(surgeLimit*100)}`;
          grid.push(summarize(name, strategy, dashboard.backtest.rows, baselineRows));
        }
      }
    }
  }

  const baselineTrain = baseline.firstHalf;
  const baselineTest = baseline.secondHalf;
  const eligibleTrain = grid.filter((r) => r.firstHalf.cagr >= baselineTrain.cagr * 0.95 && r.firstHalf.maxDrawdown >= baselineTrain.maxDrawdown - 0.03);
  const trainLeaders = [...eligibleTrain]
    .sort((a, b) => b.firstHalf.calmar - a.firstHalf.calmar || b.firstHalf.cagr - a.firstHalf.cagr)
    .slice(0, 20);

  const fullLeaders = [...grid]
    .filter((r) => r.full.cagr >= baseline.full.cagr * 0.95)
    .sort((a, b) => b.full.calmar - a.full.calmar || b.full.cagr - a.full.cagr)
    .slice(0, 20);

  const fullCagrLeaders = [...grid].sort((a, b) => b.full.cagr - a.full.cagr).slice(0, 20);

  // Leave-one-year-out: choose on other years, then report the untouched held-out year.
  const loyo: Array<{ holdoutYear: string; selected: string; train: Stats; holdout: Stats; baselineHoldout: Stats; holdoutDelta: number }> = [];
  for (const holdoutYear of ["2023", "2024", "2025", "2026"]) {
    const scored = grid.map((r) => {
      const strategy = makeStrategy({
        topN: r.params.topN,
        qqqMaMonths: r.params.qqqMaMonths,
        weights: r.params.weights,
        surgeLimit: r.params.surgeLimit,
        genreMax: 2,
        frontierMax: 2,
      });
      const dashboard = buildDashboard(histories, TICKERS, strategy);
      const rows = dashboard.backtest.rows;
      return {
        result: r,
        train: statsFromRows(rows, (row) => !withinYear(row, holdoutYear)),
        holdout: statsFromRows(rows, (row) => withinYear(row, holdoutYear)),
      };
    });
    const baselineTrainEx = statsFromRows(baselineRows, (row) => !withinYear(row, holdoutYear));
    const candidates = scored.filter((x) => x.train.cagr >= baselineTrainEx.cagr * 0.95 && x.train.maxDrawdown >= baselineTrainEx.maxDrawdown - 0.03);
    const best = [...candidates].sort((a, b) => b.train.calmar - a.train.calmar || b.train.cagr - a.train.cagr)[0];
    const baselineHoldout = statsFromRows(baselineRows, (row) => withinYear(row, holdoutYear));
    if (best) {
      loyo.push({
        holdoutYear,
        selected: best.result.name,
        train: best.train,
        holdout: best.holdout,
        baselineHoldout,
        holdoutDelta: best.holdout.finalEquity - baselineHoldout.finalEquity,
      });
    }
  }

  const result = {
    generatedAt: new Date().toISOString(),
    source: "Yahoo Finance via src/lib/yahoo.ts fetchHistories; strategy evaluation via src/lib/momentum.ts buildDashboard",
    currentMainStrategy: baselineStrategy,
    baseline,
    baselineTrain,
    baselineTest,
    perturbations,
    gridCount: grid.length,
    trainLeaders,
    fullLeaders,
    fullCagrLeaders,
    loyo,
    historyRange: Object.fromEntries(Object.entries(histories).map(([symbol, points]) => [symbol, { first: points[0]?.date ?? null, last: points.at(-1)?.date ?? null, count: points.length }])),
  };

  await mkdir("artifacts", { recursive: true });
  await writeFile("artifacts/robustness-search.json", JSON.stringify(result, null, 2));

  console.log("BASELINE", JSON.stringify({ cagr: pct(baseline.full.cagr), maxDD: pct(baseline.full.maxDrawdown), vol: pct(baseline.full.annualizedVolatility), calmar: baseline.full.calmar, insufficient: baseline.insufficientMonths, firstHalf: pct(baseline.firstHalf.cagr), secondHalf: pct(baseline.secondHalf.cagr) }));
  console.log("PERTURBATIONS", JSON.stringify(perturbations.map((r) => ({ name: r.name, cagr: pct(r.full.cagr), dd: pct(r.full.maxDrawdown), vol: pct(r.full.annualizedVolatility), calmar: Number(r.full.calmar.toFixed(3)), h1: pct(r.firstHalf.cagr), h2: pct(r.secondHalf.cagr), changed: r.changedMonths, insufficient: r.insufficientMonths }))));
  console.log("TRAIN_LEADERS", JSON.stringify(trainLeaders.slice(0, 10).map((r) => ({ name: r.name, trainCagr: pct(r.firstHalf.cagr), trainDD: pct(r.firstHalf.maxDrawdown), trainCalmar: Number(r.firstHalf.calmar.toFixed(3)), testCagr: pct(r.secondHalf.cagr), testDD: pct(r.secondHalf.maxDrawdown), testCalmar: Number(r.secondHalf.calmar.toFixed(3)), fullCagr: pct(r.full.cagr), fullDD: pct(r.full.maxDrawdown), fullCalmar: Number(r.full.calmar.toFixed(3)) }))));
  console.log("FULL_LEADERS", JSON.stringify(fullLeaders.slice(0, 10).map((r) => ({ name: r.name, cagr: pct(r.full.cagr), dd: pct(r.full.maxDrawdown), vol: pct(r.full.annualizedVolatility), calmar: Number(r.full.calmar.toFixed(3)), h1: pct(r.firstHalf.cagr), h2: pct(r.secondHalf.cagr) }))));
  console.log("LOYO", JSON.stringify(loyo.map((x) => ({ year: x.holdoutYear, selected: x.selected, trainCagr: pct(x.train.cagr), holdoutReturn: pct(x.holdout.finalEquity - 1), baselineHoldoutReturn: pct(x.baselineHoldout.finalEquity - 1), delta: pct(x.holdoutDelta) }))));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
