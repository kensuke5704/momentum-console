import { readFile, mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { runStrategySimulation, performanceStats } from "../src/lib/backtest";
import type { EquityPoint, PricePoint, StrategyConfig, UniverseMonth } from "../src/lib/types";

type MarketDataFile = { histories?: Record<string, PricePoint[]> };
type UniverseFile = { history: UniverseMonth[] };
const END = "2026-08-25";
const DAYS = [8, 10, 12] as const;

function configFor(days: number): StrategyConfig {
  const config = JSON.parse(JSON.stringify(PRODUCTION_STRATEGY)) as StrategyConfig;
  config.recovery.confirmationDays = days;
  return config;
}

function sliceCurve(curve: EquityPoint[], start: string, end: string): EquityPoint[] {
  const rows = curve.filter((p) => p.date >= start && p.date <= end);
  if (rows.length < 2) return rows;
  const base = rows[0].equity;
  let peak = 1;
  return rows.map((p) => {
    const equity = p.equity / base;
    peak = Math.max(peak, equity);
    return { date: p.date, equity, drawdown: equity / peak - 1 };
  });
}

function addMonths(iso: string, months: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCMonth(d.getUTCMonth() + months);
  return d.toISOString().slice(0, 10);
}

function minDate(a: string, b: string) { return a < b ? a : b; }

async function main() {
  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as MarketDataFile;
  const universe = JSON.parse(await readFile(resolve("data/universe-history.json"), "utf8")) as UniverseFile;
  const histories = market.histories ?? {};
  const universeHistory = universe.history.filter((u) => u.asOf >= PRODUCTION_STRATEGY.backtestStart && u.asOf <= END);

  const simulations = Object.fromEntries(DAYS.map((days) => {
    const result = runStrategySimulation({ histories, universeHistory, config: configFor(days) });
    return [String(days), result];
  }));

  const fixedWindows = [
    { label: "EARLY_2020_2022", start: "2020-01-02", end: "2022-12-30" },
    { label: "MID_2023_2024", start: "2023-01-03", end: "2024-12-31" },
    { label: "RECENT_2025_2026", start: "2025-01-02", end: END },
  ];

  const rollingWindows: Array<{ label: string; start: string; end: string }> = [];
  for (let start = "2020-01-02"; start < "2025-01-01"; start = addMonths(start, 6)) {
    const end = minDate(addMonths(start, 24), END);
    if (end <= start) break;
    rollingWindows.push({ label: `ROLL24_${start}_${end}`, start, end });
  }

  function evaluateWindow(window: { label: string; start: string; end: string }) {
    const rows = DAYS.map((days) => {
      const curve = sliceCurve(simulations[String(days)].backtest.equityCurve, window.start, window.end);
      return { recoveryDays: days, stats: performanceStats(curve) };
    });
    const ranked = [...rows].sort((a, b) => b.stats.cagr - a.stats.cagr);
    return {
      ...window,
      rows,
      winner: ranked[0].recoveryDays,
      rank10: ranked.findIndex((r) => r.recoveryDays === 10) + 1,
      cagr10MinusBestAlternative: rows.find((r) => r.recoveryDays === 10)!.stats.cagr - Math.max(...rows.filter((r) => r.recoveryDays !== 10).map((r) => r.stats.cagr)),
    };
  }

  const fixed = fixedWindows.map(evaluateWindow);
  const rolling = rollingWindows.map(evaluateWindow);
  const rollingWins10 = rolling.filter((w) => w.winner === 10).length;
  const rollingRank1or2_10 = rolling.filter((w) => w.rank10 <= 2).length;
  const diffs = rolling.map((w) => w.cagr10MinusBestAlternative).sort((a, b) => a - b);
  const median = diffs.length ? diffs[Math.floor(diffs.length / 2)] : null;

  const output = {
    generatedAt: new Date().toISOString(),
    period: { start: PRODUCTION_STRATEGY.backtestStart, end: END },
    strategyId: PRODUCTION_STRATEGY.strategyId,
    method: "Temporal stability audit of fixed recovery confirmation values 8/10/12. No parameter is optimized or selected inside any window. Each configuration is simulated causally over the full history; performance is then measured on non-overlapping fixed eras and 24-month windows stepped every 6 months, preserving the state inherited from prior history.",
    caveat: "Because recovery=10 was already chosen using historical research, these are temporal/pseudo-OOS robustness checks, not a pristine untouched out-of-sample test.",
    fullPeriod: DAYS.map((days) => ({ recoveryDays: days, stats: simulations[String(days)].backtest.stats })),
    fixedWindows: fixed,
    rolling24MonthWindows: rolling,
    rollingSummary: {
      windows: rolling.length,
      recovery10Wins: rollingWins10,
      recovery10WinRate: rolling.length ? rollingWins10 / rolling.length : null,
      recovery10Rank1or2: rollingRank1or2_10,
      recovery10Rank1or2Rate: rolling.length ? rollingRank1or2_10 / rolling.length : null,
      medianCagr10MinusBestAlternative: median,
      worstCagr10MinusBestAlternative: diffs[0] ?? null,
      bestCagr10MinusBestAlternative: diffs.at(-1) ?? null,
    },
  };

  const out = resolve("data/research/recovery-temporal-stability.json");
  await mkdir(dirname(out), { recursive: true });
  await writeFile(out, JSON.stringify(output, null, 2) + "\n");
  console.log(JSON.stringify(output, null, 2));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
