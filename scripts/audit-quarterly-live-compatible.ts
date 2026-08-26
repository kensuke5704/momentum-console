import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { runBacktest } from "../src/lib/backtest";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import type { NportFiling, StrategyConfig, UniverseMonth } from "../src/lib/types";
import { buildPointInTimeUniverse } from "../src/lib/universe/universe";
import { fetchHistories, fetchYahooHistory } from "../src/lib/yahoo";

function previousQuarterEnd(date: string): string {
  const year = Number(date.slice(0, 4));
  const month = Number(date.slice(5, 7));
  const q = Math.floor((month - 1) / 3) + 1;
  if (q === 1) return `${year - 1}-12-31`;
  const endMonth = (q - 1) * 3;
  const lastDay = new Date(Date.UTC(year, endMonth, 0)).getUTCDate();
  return `${year}-${String(endMonth).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`;
}

function dayBefore(date: string): string {
  return new Date(Date.parse(`${date}T12:00:00Z`) - 86_400_000).toISOString().slice(0, 10);
}

function isQuarterEndSignal(asOf: string): boolean {
  return [3, 6, 9, 12].includes(Number(asOf.slice(5, 7)));
}

function cutoffFor(asOf: string, mode: "prior-quarter" | "strict-posting" | "inclusive-posting"): string {
  if (mode === "prior-quarter") return previousQuarterEnd(asOf);
  if (!isQuarterEndSignal(asOf)) return previousQuarterEnd(asOf);
  return mode === "strict-posting" ? dayBefore(asOf) : asOf;
}

function buildHistory(filings: NportFiling[], months: Array<[string, string]>, mode: "prior-quarter" | "strict-posting" | "inclusive-posting"): UniverseMonth[] {
  const out: UniverseMonth[] = [];
  let previous: UniverseMonth | null = null;
  for (const [signalMonth, asOf] of months) {
    const cutoff = cutoffFor(asOf, mode);
    const available = filings.filter((f) => f.filingDate <= cutoff);
    const current = buildPointInTimeUniverse(available, signalMonth, asOf, previous);
    out.push(current);
    previous = current;
  }
  return out;
}

function configFrom(start: string): StrategyConfig {
  return { ...PRODUCTION_STRATEGY, backtestStart: start } as StrategyConfig;
}

async function main() {
  const quarterly = JSON.parse(await readFile(resolve("data/sec-nport/filings.json"), "utf8")) as { filings: NportFiling[] };
  const published = JSON.parse(await readFile(resolve("public/data/universe-history.json"), "utf8")) as { history: UniverseMonth[] };
  const qqq = await fetchYahooHistory("QQQ");
  const monthEnds = new Map<string, string>();
  for (const point of qqq) monthEnds.set(point.date.slice(0, 7), point.date);
  const lastMonth = published.history.at(-1)?.signalMonth ?? "9999-12";
  const months = [...monthEnds]
    .filter(([m]) => m >= "2020-01" && m <= lastMonth)
    .sort(([a], [b]) => a.localeCompare(b)) as Array<[string, string]>;

  const priorQuarter = buildHistory(quarterly.filings, months, "prior-quarter");
  const strictPosting = buildHistory(quarterly.filings, months, "strict-posting");
  const inclusivePosting = buildHistory(quarterly.filings, months, "inclusive-posting");

  const symbols = [...new Set([
    "QQQ", "TQQQ",
    ...published.history.flatMap((m) => m.symbols.map((x) => x.symbol)),
    ...priorQuarter.flatMap((m) => m.symbols.map((x) => x.symbol)),
    ...strictPosting.flatMap((m) => m.symbols.map((x) => x.symbol)),
    ...inclusivePosting.flatMap((m) => m.symbols.map((x) => x.symbol)),
  ])];
  console.log(`Fetching histories for ${symbols.length} symbols`);
  const histories = await fetchHistories(symbols, 8);

  const run = (history: UniverseMonth[], start = PRODUCTION_STRATEGY.backtestStart) => runBacktest({ histories, universeHistory: history, config: configFrom(start) }).stats;
  const baseline = run(published.history);
  const prior = run(priorQuarter);
  const strict = run(strictPosting);
  const inclusive = run(inclusivePosting);
  const diagnosticStart = "2020-04-01";

  const monthDiffs = strictPosting.map((m) => {
    const truth = published.history.find((x) => x.signalMonth === m.signalMonth);
    if (!truth) return null;
    const a = new Set(m.symbols.map((x) => x.symbol));
    const b = new Set(truth.symbols.map((x) => x.symbol));
    const intersection = [...a].filter((x) => b.has(x)).length;
    const union = new Set([...a, ...b]).size;
    return {
      signalMonth: m.signalMonth,
      asOf: m.asOf,
      strictCutoff: cutoffFor(m.asOf, "strict-posting"),
      inclusiveCutoff: cutoffFor(m.asOf, "inclusive-posting"),
      quarterEndSignal: isQuarterEndSignal(m.asOf),
      jaccard: union ? intersection / union : 1,
      added: [...a].filter((x) => !b.has(x)),
      removed: [...b].filter((x) => !a.has(x)),
    };
  }).filter(Boolean);

  const result = {
    generatedAt: new Date().toISOString(),
    secPostingRule: "Quarterly posting is treated as available for the next session at quarter-end. Strict mode excludes filings dated on the final business day; inclusive mode includes them. Non-quarter-end months use only the prior completed quarter.",
    caveat: "The bootstrap begins at 2020 Q1, so 2020 Jan-Mar lack the already-available 2019 Q4 dataset. A 2020-04-01 diagnostic removes that initial-data bias.",
    baseline,
    priorQuarter: prior,
    strictPosting: strict,
    inclusivePosting: inclusive,
    diagnosticFrom2020Q2: {
      baseline: run(published.history, diagnosticStart),
      priorQuarter: run(priorQuarter, diagnosticStart),
      strictPosting: run(strictPosting, diagnosticStart),
      inclusivePosting: run(inclusivePosting, diagnosticStart),
    },
    deltasVsBaseline: {
      priorQuarterCagr: prior.cagr - baseline.cagr,
      strictPostingCagr: strict.cagr - baseline.cagr,
      inclusivePostingCagr: inclusive.cagr - baseline.cagr,
    },
    months: monthDiffs,
  };
  await mkdir(resolve("data/research/live-nport-ingestion"), { recursive: true });
  await writeFile(resolve("data/research/live-nport-ingestion/quarterly-live-compatible.json"), `${JSON.stringify(result, null, 2)}\n`);
  console.log("AVAILABILITY_AWARE=" + JSON.stringify(result));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
