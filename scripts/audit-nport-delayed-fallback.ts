import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { runBacktest } from "../src/lib/backtest";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import type { NportFiling, UniverseMonth } from "../src/lib/types";
import { buildPointInTimeUniverse } from "../src/lib/universe/universe";
import { fetchHistories, fetchYahooHistory } from "../src/lib/yahoo";

const DELAYS = [1, 3, 5, 10] as const;
const START = "2020-04-01"; // avoids missing 2019Q4 bootstrap bias

function quarterEndForMonth(signalMonth: string): string | null {
  const year = Number(signalMonth.slice(0, 4));
  const month = Number(signalMonth.slice(5, 7));
  if (![3, 6, 9, 12].includes(month)) return null;
  const day = new Date(Date.UTC(year, month, 0)).getUTCDate();
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function previousQuarterEnd(signalMonth: string): string {
  const year = Number(signalMonth.slice(0, 4));
  const month = Number(signalMonth.slice(5, 7));
  const q = Math.floor((month - 1) / 3) + 1;
  if (q === 1) return `${year - 1}-12-31`;
  const endMonth = (q - 1) * 3;
  const day = new Date(Date.UTC(year, endMonth, 0)).getUTCDate();
  return `${year}-${String(endMonth).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function buildQuarterlyFallbackHistory(filings: NportFiling[], monthEnds: Array<[string, string]>): UniverseMonth[] {
  const out: UniverseMonth[] = [];
  let previous: UniverseMonth | null = null;
  for (const [signalMonth, asOf] of monthEnds) {
    const cutoff = previousQuarterEnd(signalMonth);
    const available = filings.filter((f) => f.filingDate <= cutoff);
    const current = buildPointInTimeUniverse(available, signalMonth, asOf, previous);
    out.push(current);
    previous = current;
  }
  return out;
}

function addQuarterlyReceiptEvents(args: {
  filings: NportFiling[];
  base: UniverseMonth[];
  tradingDates: string[];
  delaySessions: number;
}): UniverseMonth[] {
  const events = [...args.base];
  const sortedDates = args.tradingDates;
  for (const month of args.base) {
    const quarterEnd = quarterEndForMonth(month.signalMonth);
    if (!quarterEnd) continue;
    const firstAfter = sortedDates.findIndex((d) => d > month.asOf);
    if (firstAfter < 0) continue;
    // Delay 1 means ZIP is received after the first trading-session close following quarter-end,
    // producing an extraordinary rebalance at the next session open.
    const receiptIndex = firstAfter + args.delaySessions - 1;
    const receiptDate = sortedDates[receiptIndex];
    if (!receiptDate) continue;
    const available = args.filings.filter((f) => f.filingDate <= quarterEnd);
    const prior = events.filter((e) => e.asOf < receiptDate).sort((a, b) => a.asOf.localeCompare(b.asOf)).at(-1) ?? null;
    const extraordinary = buildPointInTimeUniverse(available, `${month.signalMonth}-NPORT`, receiptDate, prior);
    events.push(extraordinary);
  }
  return events.sort((a, b) => a.asOf.localeCompare(b.asOf));
}

function turnoverFromEvents(events: Array<{ type?: string; date?: string; symbols?: string[]; targetWeights?: number[] }>): { entries: number; exits: number; rebalanceEvents: number } {
  const entries = events.filter((e) => /ENTRY/i.test(String(e.type ?? ""))).length;
  const exits = events.filter((e) => /EXIT/i.test(String(e.type ?? ""))).length;
  const rebalanceEvents = events.filter((e) => /ENTRY|REBALANCE/i.test(String(e.type ?? ""))).length;
  return { entries, exits, rebalanceEvents };
}

async function main() {
  const quarterly = JSON.parse(await readFile(resolve("data/sec-nport/filings.json"), "utf8")) as { filings: NportFiling[] };
  const published = JSON.parse(await readFile(resolve("public/data/universe-history.json"), "utf8")) as { history: UniverseMonth[] };
  const qqq = await fetchYahooHistory("QQQ");
  const tradingDates = qqq.map((p) => p.date).sort();
  const monthEndsMap = new Map<string, string>();
  for (const point of qqq) monthEndsMap.set(point.date.slice(0, 7), point.date);
  const lastMonth = published.history.at(-1)?.signalMonth ?? "9999-12";
  const monthEnds = [...monthEndsMap]
    .filter(([m]) => m >= "2020-04" && m <= lastMonth)
    .sort(([a], [b]) => a.localeCompare(b)) as Array<[string, string]>;

  const fallbackBase = buildQuarterlyFallbackHistory(quarterly.filings, monthEnds);
  const variants = Object.fromEntries(DELAYS.map((delay) => [String(delay), addQuarterlyReceiptEvents({ filings: quarterly.filings, base: fallbackBase, tradingDates, delaySessions: delay })]));

  const symbols = [...new Set([
    "QQQ", "TQQQ",
    ...published.history.flatMap((m) => m.symbols.map((x) => x.symbol)),
    ...fallbackBase.flatMap((m) => m.symbols.map((x) => x.symbol)),
    ...Object.values(variants).flatMap((history) => history.flatMap((m) => m.symbols.map((x) => x.symbol))),
  ])];
  console.log(`Fetching histories for ${symbols.length} symbols`);
  const histories = await fetchHistories(symbols, 8);

  const run = (history: UniverseMonth[]) => runBacktest({ histories, universeHistory: history, config: { ...PRODUCTION_STRATEGY, backtestStart: START } });
  const baseline = run(published.history);
  const fallbackOnly = run(fallbackBase);
  const delayed = Object.fromEntries(DELAYS.map((delay) => {
    const bt = run(variants[String(delay)]);
    return [String(delay), {
      stats: bt.stats,
      eventCounts: turnoverFromEvents(bt.events as Array<{ type?: string; date?: string; symbols?: string[]; targetWeights?: number[] }>),
      signalEvents: variants[String(delay)].length,
    }];
  }));

  const result = {
    generatedAt: new Date().toISOString(),
    start: START,
    assumptions: {
      fallback: "At each regular month-end, if the new quarterly ZIP is not yet available, use the prior-quarter Universe and execute the normal next-session-open rebalance.",
      receipt: "When the quarterly ZIP is received after N trading-session closes, rebuild Universe using filings in that quarter, recompute Production 0/20/80 momentum using prices through that receipt-day close, and execute an extraordinary rebalance at the next session open.",
      delaysTestedTradingSessions: DELAYS,
      transactionCostPerSide: PRODUCTION_STRATEGY.execution.transactionCost,
      caveat: "Historical exact user upload times do not exist, so 1/3/5/10-session delays are scenario tests, not reconstructed actual upload history. Quarterly filing inclusion is modeled using filings with filingDate <= calendar quarter-end from the audited quarterly dataset.",
    },
    baselinePublished: { stats: baseline.stats, eventCounts: turnoverFromEvents(baseline.events as Array<{ type?: string }>) },
    fallbackOnly: { stats: fallbackOnly.stats, eventCounts: turnoverFromEvents(fallbackOnly.events as Array<{ type?: string }>) },
    delayedReceiptExtraRebalance: delayed,
  };
  await mkdir(resolve("data/research/live-nport-ingestion"), { recursive: true });
  await writeFile(resolve("data/research/live-nport-ingestion/nport-delayed-fallback.json"), `${JSON.stringify(result, null, 2)}\n`);
  console.log("NPORT_DELAYED_FALLBACK=" + JSON.stringify(result));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
