import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { performanceStats, runStrategySimulation } from "../src/lib/backtest";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import { initialEngineState, transitionDay } from "../src/lib/strategy/state-machine";
import type { EquityPoint, MonthlySignal, NportFiling, PricePoint, UniverseMonth } from "../src/lib/types";
import { buildPointInTimeUniverse } from "../src/lib/universe/universe";
import { fetchHistories, fetchYahooHistory } from "../src/lib/yahoo";

const START = "2020-04-01";
const DELAYS = [1, 3, 5, 10] as const;

function previousQuarterEnd(date: string): string {
  const year = Number(date.slice(0, 4));
  const month = Number(date.slice(5, 7));
  const q = Math.floor((month - 1) / 3) + 1;
  if (q === 1) return `${year - 1}-12-31`;
  const endMonth = (q - 1) * 3;
  const lastDay = new Date(Date.UTC(year, endMonth, 0)).getUTCDate();
  return `${year}-${String(endMonth).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`;
}

function isQuarterEndMonth(month: string): boolean {
  return [3, 6, 9, 12].includes(Number(month.slice(5, 7)));
}

function buildFallbackHistory(filings: NportFiling[], months: Array<[string, string]>): UniverseMonth[] {
  const out: UniverseMonth[] = [];
  let previous: UniverseMonth | null = null;
  for (const [signalMonth, asOf] of months) {
    const cutoff = previousQuarterEnd(asOf);
    const available = filings.filter((f) => f.filingDate <= cutoff);
    const current = buildPointInTimeUniverse(available, signalMonth, asOf, previous);
    out.push(current);
    previous = current;
  }
  return out;
}

function countEvents(events: Array<{ type?: string }>) {
  const entries = events.filter((e) => e.type === "ENTRY").length;
  const exits = events.filter((e) => e.type === "EXIT").length;
  return { entries, exits, rebalanceEvents: entries };
}

function simulateWithFixedMonthEndExtra(args: {
  histories: Record<string, PricePoint[]>;
  fallbackHistory: UniverseMonth[];
  filings: NportFiling[];
  months: Array<[string, string]>;
  delaySessions: number;
}) {
  const qqq = [...(args.histories.QQQ ?? [])].sort((a, b) => a.date.localeCompare(b.date));
  const tradingDates = qqq.map((p) => p.date);
  const dateIndex = new Map(tradingDates.map((d, i) => [d, i]));
  const priceMaps = Object.fromEntries(Object.entries(args.histories).map(([symbol, points]) => [symbol, new Map(points.map((p) => [p.date, p]))]));
  const regularByDate = new Map(args.fallbackHistory.map((m) => [m.asOf, m]));
  const extras = new Map<string, MonthlySignal>();

  for (const [signalMonth, monthEnd] of args.months) {
    if (!isQuarterEndMonth(signalMonth)) continue;
    const idx = dateIndex.get(monthEnd);
    if (idx === undefined) continue;
    const receiptDate = tradingDates[idx + args.delaySessions];
    const executionDate = tradingDates[idx + args.delaySessions + 1];
    if (!receiptDate || !executionDate) continue;
    const available = args.filings.filter((f) => f.filingDate <= monthEnd);
    const newUniverse = buildPointInTimeUniverse(available, signalMonth, monthEnd, null);
    const signal = buildMonthlySignal({
      universe: newUniverse,
      histories: args.histories,
      qqq,
      nextSessionDate: executionDate,
      config: PRODUCTION_STRATEGY,
    });
    extras.set(receiptDate, signal);
  }

  let state = initialEngineState(PRODUCTION_STRATEGY);
  const curve: EquityPoint[] = [];
  for (let index = 0; index < tradingDates.length; index++) {
    const date = tradingDates[index];
    if (date < START) continue;
    const nextSessionDate = tradingDates[index + 1] ?? null;
    const regularUniverse = regularByDate.get(date);
    const regularSignal = regularUniverse ? buildMonthlySignal({ universe: regularUniverse, histories: args.histories, qqq, nextSessionDate, config: PRODUCTION_STRATEGY }) : null;
    const signal = extras.get(date) ?? regularSignal;
    const symbols = new Set([
      "QQQ",
      ...state.currentPositions.map((p) => p.symbol),
      ...(state.pendingSignal?.selectedSymbols ?? []),
      ...state.nextAction.symbols,
      ...(signal?.selectedSymbols ?? []),
    ]);
    const prices = Object.fromEntries([...symbols].map((symbol) => [symbol, priceMaps[symbol]?.get(date)]));
    state = transitionDay(state, {
      date,
      prices,
      qqqHistoryThroughClose: qqq.slice(0, (dateIndex.get(date) ?? index) + 1),
      monthlySignal: signal,
      nextSessionDate,
    }, PRODUCTION_STRATEGY);
    curve.push({ date, equity: state.currentEquity, drawdown: state.drawdown });
  }
  return { stats: performanceStats(curve), eventCounts: countEvents(state.events), signalEvents: args.fallbackHistory.length + extras.size };
}

async function main() {
  const quarterly = JSON.parse(await readFile(resolve("data/sec-nport/filings.json"), "utf8")) as { filings: NportFiling[] };
  const published = JSON.parse(await readFile(resolve("public/data/universe-history.json"), "utf8")) as { history: UniverseMonth[] };
  const qqq = await fetchYahooHistory("QQQ");
  const monthEnds = new Map<string, string>();
  for (const point of qqq) monthEnds.set(point.date.slice(0, 7), point.date);
  const lastMonth = published.history.at(-1)?.signalMonth ?? "9999-12";
  const months = [...monthEnds].filter(([m]) => m >= "2020-04" && m <= lastMonth).sort(([a], [b]) => a.localeCompare(b)) as Array<[string, string]>;
  const fallbackHistory = buildFallbackHistory(quarterly.filings, months);

  const symbols = [...new Set([
    "QQQ", "TQQQ",
    ...published.history.flatMap((m) => m.symbols.map((x) => x.symbol)),
    ...fallbackHistory.flatMap((m) => m.symbols.map((x) => x.symbol)),
    ...quarterly.filings.flatMap((f) => f.holdings.map((h) => h.symbol)),
  ])];
  console.log(`Fetching histories for ${symbols.length} symbols`);
  const histories = await fetchHistories(symbols, 8);

  const baseline = runStrategySimulation({ histories, universeHistory: published.history, config: { ...PRODUCTION_STRATEGY, backtestStart: START } }).backtest;
  const fallback = runStrategySimulation({ histories, universeHistory: fallbackHistory, config: { ...PRODUCTION_STRATEGY, backtestStart: START } }).backtest;
  const scenarios = Object.fromEntries(DELAYS.map((delay) => [String(delay), simulateWithFixedMonthEndExtra({ histories, fallbackHistory, filings: quarterly.filings, months, delaySessions: delay })]));

  const result = {
    generatedAt: new Date().toISOString(),
    start: START,
    assumptions: {
      fallback: "At every regular month-end, if the new quarterly ZIP is unavailable, use the prior-quarter Universe and execute the normal next-session-open rebalance.",
      receipt: "When the ZIP arrives after N trading-session closes, replace only the Universe. Recompute Top2 using the NEW Universe but keep all momentum returns and the QQQ monthly gate anchored to the original quarter-end close. Execute any changed allocation at the next session open.",
      delaysTestedTradingSessions: DELAYS,
      transactionCostPerSide: PRODUCTION_STRATEGY.execution.transactionCost,
      caveat: "Historical exact user upload times do not exist. Delays are scenario tests. Filing inclusion uses filingDate <= calendar quarter-end from the audited quarterly dataset.",
    },
    baselinePublished: { stats: baseline.stats, eventCounts: countEvents(baseline.events) },
    fallbackOnly: { stats: fallback.stats, eventCounts: countEvents(fallback.events) },
    fixedMonthEndExtraRebalance: scenarios,
  };
  await mkdir(resolve("data/research/live-nport-ingestion"), { recursive: true });
  await writeFile(resolve("data/research/live-nport-ingestion/nport-delayed-fixed-monthend.json"), `${JSON.stringify(result, null, 2)}\n`);
  console.log("NPORT_DELAYED_FIXED_MONTHEND=" + JSON.stringify(result));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
