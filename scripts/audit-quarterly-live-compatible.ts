import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { runBacktest } from "../src/lib/backtest";
import type { NportFiling, UniverseMonth } from "../src/lib/types";
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

async function main() {
  const quarterly = JSON.parse(await readFile(resolve("data/sec-nport/filings.json"), "utf8")) as { filings: NportFiling[] };
  const published = JSON.parse(await readFile(resolve("public/data/universe-history.json"), "utf8")) as { history: UniverseMonth[] };
  const qqq = await fetchYahooHistory("QQQ");
  const monthEnds = new Map<string, string>();
  for (const point of qqq) monthEnds.set(point.date.slice(0, 7), point.date);

  const conservative: UniverseMonth[] = [];
  let previous: UniverseMonth | null = null;
  for (const [signalMonth, asOf] of [...monthEnds].filter(([m]) => m >= "2020-01" && m <= (published.history.at(-1)?.signalMonth ?? "9999-12")).sort(([a], [b]) => a.localeCompare(b))) {
    const cutoff = previousQuarterEnd(asOf);
    const available = quarterly.filings.filter((f) => f.filingDate <= cutoff);
    const current = buildPointInTimeUniverse(available, signalMonth, asOf, previous);
    conservative.push(current);
    previous = current;
  }

  const symbols = [...new Set([
    "QQQ", "TQQQ",
    ...published.history.flatMap((m) => m.symbols.map((x) => x.symbol)),
    ...conservative.flatMap((m) => m.symbols.map((x) => x.symbol)),
  ])];
  console.log(`Fetching histories for ${symbols.length} symbols`);
  const histories = await fetchHistories(symbols, 8);
  const baseline = runBacktest({ histories, universeHistory: published.history });
  const liveCompatible = runBacktest({ histories, universeHistory: conservative });

  const monthDiffs = conservative.map((m) => {
    const truth = published.history.find((x) => x.signalMonth === m.signalMonth);
    if (!truth) return null;
    const a = new Set(m.symbols.map((x) => x.symbol));
    const b = new Set(truth.symbols.map((x) => x.symbol));
    const intersection = [...a].filter((x) => b.has(x)).length;
    const union = new Set([...a, ...b]).size;
    return { signalMonth: m.signalMonth, asOf: m.asOf, cutoff: previousQuarterEnd(m.asOf), jaccard: union ? intersection / union : 1, added: [...a].filter((x) => !b.has(x)), removed: [...b].filter((x) => !a.has(x)) };
  }).filter(Boolean);

  const result = {
    generatedAt: new Date().toISOString(),
    assumption: "At each signal date, only N-PORT filings from the prior completed calendar quarter or earlier are available.",
    baseline: baseline.stats,
    quarterlyLiveCompatible: liveCompatible.stats,
    delta: {
      cagr: liveCompatible.stats.cagr - baseline.stats.cagr,
      maxDrawdown: liveCompatible.stats.maxDrawdown - baseline.stats.maxDrawdown,
      finalEquity: liveCompatible.stats.finalEquity - baseline.stats.finalEquity,
    },
    months: monthDiffs,
  };
  await mkdir(resolve("data/research/live-nport-ingestion"), { recursive: true });
  await writeFile(resolve("data/research/live-nport-ingestion/quarterly-live-compatible.json"), `${JSON.stringify(result, null, 2)}\n`);
  console.log("QUARTERLY_LIVE_COMPATIBLE=" + JSON.stringify(result));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
