import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { DEFAULT_STRATEGY, TICKERS } from "../src/lib/config";
import {
  FROZEN_STRATEGY,
  FROZEN_STRATEGY_FIRST_HOLDING_MONTH,
  FROZEN_STRATEGY_FIRST_SIGNAL_MONTH,
  FROZEN_STRATEGY_FROZEN_AT,
  FROZEN_STRATEGY_ID,
} from "../src/lib/frozen-strategy";
import { buildDashboard } from "../src/lib/momentum";
import type { BacktestRow, StrategyConfig } from "../src/lib/types";
import { fetchHistories } from "../src/lib/yahoo";

function mean(values: number[]) {
  return values.length
    ? values.reduce((sum, value) => sum + value, 0) / values.length
    : 0;
}

function stdev(values: number[]) {
  if (values.length <= 1) return 0;
  const average = mean(values);
  const variance =
    values.reduce((sum, value) => sum + (value - average) ** 2, 0) /
    (values.length - 1);
  return Math.sqrt(variance);
}

function summarize(rows: BacktestRow[]) {
  const completed = rows.filter(
    (row) =>
      typeof row.monthlyReturn === "number" &&
      !row.provisional,
  );
  const returns = completed.map((row) => row.monthlyReturn as number);

  let equity = 1;
  let peak = 1;
  let maxDrawdown = 0;
  let wins = 0;
  let losses = 0;

  for (const value of returns) {
    equity *= 1 + value;
    peak = Math.max(peak, equity);
    maxDrawdown = Math.min(maxDrawdown, equity / peak - 1);
    if (value > 0) wins += 1;
    if (value < 0) losses += 1;
  }

  return {
    completedMonths: completed.length,
    pendingMonths: rows.length - completed.length,
    cumulativeReturn: completed.length ? equity - 1 : null,
    equity: completed.length ? equity : 1,
    cagr:
      completed.length && equity > 0
        ? equity ** (12 / completed.length) - 1
        : null,
    averageMonthlyReturn: completed.length ? mean(returns) : null,
    annualizedVolatility:
      completed.length > 1 ? stdev(returns) * Math.sqrt(12) : null,
    maxDrawdown: completed.length ? maxDrawdown : null,
    wins,
    losses,
  };
}

function strategyMismatches(
  current: StrategyConfig,
  frozen: StrategyConfig,
) {
  const mismatches: string[] = [];

  if (current.topN !== frozen.topN) {
    mismatches.push(`topN current=${current.topN} frozen=${frozen.topN}`);
  }
  if (current.weights.oneMonth !== frozen.weights.oneMonth) {
    mismatches.push(
      `weights.oneMonth current=${current.weights.oneMonth} frozen=${frozen.weights.oneMonth}`,
    );
  }
  if (current.weights.threeMonth !== frozen.weights.threeMonth) {
    mismatches.push(
      `weights.threeMonth current=${current.weights.threeMonth} frozen=${frozen.weights.threeMonth}`,
    );
  }
  if (current.weights.sixMonth !== frozen.weights.sixMonth) {
    mismatches.push(
      `weights.sixMonth current=${current.weights.sixMonth} frozen=${frozen.weights.sixMonth}`,
    );
  }
  if (current.surgeLimit !== frozen.surgeLimit) {
    mismatches.push(
      `surgeLimit current=${current.surgeLimit} frozen=${frozen.surgeLimit}`,
    );
  }
  if (current.qqqMaMonths !== frozen.qqqMaMonths) {
    mismatches.push(
      `qqqMaMonths current=${current.qqqMaMonths} frozen=${frozen.qqqMaMonths}`,
    );
  }
  if (current.genreMax !== frozen.genreMax) {
    mismatches.push(
      `genreMax current=${current.genreMax} frozen=${frozen.genreMax}`,
    );
  }
  if (current.frontierMax !== frozen.frontierMax) {
    mismatches.push(
      `frontierMax current=${current.frontierMax} frozen=${frozen.frontierMax}`,
    );
  }

  return mismatches;
}

async function main() {
  const symbols = [...new Set(TICKERS.map((ticker) => ticker.symbol))];
  console.log(`Fetching ${symbols.length} symbols for frozen OOS tracking...`);
  const histories = await fetchHistories(symbols);
  const dashboard = buildDashboard(histories, TICKERS, FROZEN_STRATEGY);

  const rows = dashboard.backtest.rows.filter((row) =>
    row.signalMonth.startsWith(FROZEN_STRATEGY_FIRST_SIGNAL_MONTH) ||
    row.signalMonth > FROZEN_STRATEGY_FIRST_SIGNAL_MONTH,
  );
  const mismatches = strategyMismatches(DEFAULT_STRATEGY, FROZEN_STRATEGY);
  const generatedAt = new Date().toISOString();
  const outputPath = resolve("public/data/oos-performance.json");

  const output = {
    generatedAt,
    frozen: {
      id: FROZEN_STRATEGY_ID,
      frozenAt: FROZEN_STRATEGY_FROZEN_AT,
      firstSignalMonth: FROZEN_STRATEGY_FIRST_SIGNAL_MONTH,
      firstHoldingMonth: FROZEN_STRATEGY_FIRST_HOLDING_MONTH,
      strategy: FROZEN_STRATEGY,
    },
    integrity: {
      defaultStrategyMatchesFrozen: mismatches.length === 0,
      mismatches,
    },
    summary: summarize(rows),
    rows,
  };

  await mkdir(dirname(outputPath), { recursive: true });
  await writeFile(outputPath, JSON.stringify(output, null, 2), "utf8");

  console.log(`Saved ${outputPath}`);
  console.log(`Frozen strategy: ${FROZEN_STRATEGY_ID}`);
  console.log(`Tracked rows: ${rows.length}`);
  console.log(`Completed OOS months: ${output.summary.completedMonths}`);
  if (mismatches.length) {
    console.warn("DEFAULT_STRATEGY differs from frozen strategy:");
    for (const mismatch of mismatches) console.warn(`- ${mismatch}`);
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
