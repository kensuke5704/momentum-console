import { TICKERS } from "../src/lib/config";
import { FROZEN_STRATEGY, FROZEN_STRATEGY_ID } from "../src/lib/frozen-strategy";
import { buildDashboard } from "../src/lib/momentum";
import { fetchHistories } from "../src/lib/yahoo";
import type { TickerConfig } from "../src/lib/types";

function calmar(cagr: number, maxDrawdown: number) {
  return maxDrawdown < 0 ? cagr / Math.abs(maxDrawdown) : 0;
}

function parseCandidate(raw: string): TickerConfig {
  const separator = raw.indexOf(":");
  if (separator <= 0 || separator === raw.length - 1) {
    throw new Error(`Candidate must be SYMBOL:Genre, received ${raw}`);
  }
  return {
    symbol: raw.slice(0, separator).trim().toUpperCase(),
    genre: raw.slice(separator + 1).trim(),
  };
}

function samePicks(a: string[], b: string[]) {
  return [...a].sort().join("|") === [...b].sort().join("|");
}

async function main() {
  const rawCandidates = process.argv.slice(2);
  const candidates = rawCandidates.map(parseCandidate);
  const productionSymbols = new Set(TICKERS.map((ticker) => ticker.symbol));
  for (const candidate of candidates) {
    if (productionSymbols.has(candidate.symbol)) {
      throw new Error(`${candidate.symbol} already exists in Production Universe`);
    }
  }

  const symbols = [...new Set([...TICKERS.map((ticker) => ticker.symbol), ...candidates.map((candidate) => candidate.symbol)])];
  const histories = await fetchHistories(symbols);
  const baseline = buildDashboard(histories, TICKERS, FROZEN_STRATEGY);

  const baselineRows = new Map(baseline.backtest.rows.map((row) => [row.signalMonth, row]));
  const baselineStats = baseline.backtest.stats;

  const output = {
    strategyId: FROZEN_STRATEGY_ID,
    baseline: {
      cagr: baselineStats.cagr,
      maxDrawdown: baselineStats.maxDrawdown,
      annualizedVolatility: baselineStats.annualizedVolatility,
      calmar: calmar(baselineStats.cagr, baselineStats.maxDrawdown),
    },
    candidates: [] as unknown[],
  };

  for (const candidate of candidates) {
    const scenarioTickers = [...TICKERS, candidate];
    const scenario = buildDashboard(histories, scenarioTickers, FROZEN_STRATEGY);
    const stats = scenario.backtest.stats;
    const selectedRows = scenario.backtest.rows.filter((row) => row.picks.includes(candidate.symbol));
    const changedRows = scenario.backtest.rows.filter((row) => {
      const base = baselineRows.get(row.signalMonth);
      return base ? !samePicks(base.picks, row.picks) : false;
    });

    const displaced = new Map<string, number>();
    const selectedDetail = selectedRows.map((row) => {
      const base = baselineRows.get(row.signalMonth);
      const removed = base ? base.picks.filter((symbol) => !row.picks.includes(symbol)) : [];
      for (const symbol of removed) displaced.set(symbol, (displaced.get(symbol) ?? 0) + 1);
      return {
        signalMonth: row.signalMonth,
        market: row.market,
        entryDate: row.entryDate,
        exitDate: row.exitDate,
        portfolioReturn: row.monthlyReturn,
        displaced: removed,
      };
    });

    output.candidates.push({
      symbol: candidate.symbol,
      genre: candidate.genre,
      selectedMonths: selectedRows.length,
      changedMonths: changedRows.length,
      cagr: stats.cagr,
      deltaCagr: stats.cagr - baselineStats.cagr,
      maxDrawdown: stats.maxDrawdown,
      deltaMaxDrawdown: stats.maxDrawdown - baselineStats.maxDrawdown,
      annualizedVolatility: stats.annualizedVolatility,
      deltaAnnualizedVolatility: stats.annualizedVolatility - baselineStats.annualizedVolatility,
      calmar: calmar(stats.cagr, stats.maxDrawdown),
      deltaCalmar: calmar(stats.cagr, stats.maxDrawdown) - calmar(baselineStats.cagr, baselineStats.maxDrawdown),
      displacedTickers: [...displaced.entries()].sort((a, b) => b[1] - a[1]).map(([symbol, months]) => ({ symbol, months })),
      selectedDetail,
    });
  }

  console.log("CANDIDATE_SANITY_JSON_START");
  console.log(JSON.stringify(output, null, 2));
  console.log("CANDIDATE_SANITY_JSON_END");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
