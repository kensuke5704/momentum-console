import { readFile } from "node:fs/promises";
import { gunzipSync } from "node:zlib";
import { resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { runBacktest } from "../src/lib/backtest";
import { buildPointInTimeUniverse } from "../src/lib/universe/universe";
import { parseQuarterlyNportZip } from "../src/lib/universe/nport-quarterly";
import { fetchHistories } from "../src/lib/yahoo";
import type { NportFiling, PricePoint, UniverseMonth } from "../src/lib/types";

async function main() {
  const zipPath = process.argv[2];
  if (!zipPath) throw new Error("Usage: npx tsx scripts/research-pre2020-backtest.ts /path/2019q4_nport.zip");

  const parsed = await parseQuarterlyNportZip(resolve(zipPath));
  const bootstrap = JSON.parse(gunzipSync(await readFile(resolve("data/sec-nport/bootstrap.json.gz"))).toString("utf8")) as { snapshots?: NportFiling[] };
  const existingFilings = bootstrap.snapshots ?? [];
  const filingMap = new Map(existingFilings.map((f) => [f.accession, f]));
  for (const f of parsed.filings) filingMap.set(f.accession, f);
  const filings = [...filingMap.values()].sort((a,b) => a.filingDate.localeCompare(b.filingDate));

  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as { histories?: Record<string, PricePoint[]> };
  const histories: Record<string, PricePoint[]> = market.histories ?? {};
  const qqq = histories.QQQ ?? [];
  const monthEnds = new Map<string,string>();
  for (const p of qqq) if (p.date >= "2019-01-01" && p.date < "2020-01-01") monthEnds.set(p.date.slice(0,7), p.date);

  const pre2020: UniverseMonth[] = [];
  let previous: UniverseMonth | null = null;
  for (const [signalMonth, asOf] of [...monthEnds].sort(([a],[b]) => a.localeCompare(b))) {
    const u = buildPointInTimeUniverse(filings, signalMonth, asOf, previous);
    pre2020.push(u);
    previous = u;
  }

  console.log(JSON.stringify({
    parsedQuarter: parsed.quarter,
    parsedFilings: parsed.filings.length,
    parsedSubmissions: parsed.submissions,
    minFilingDate: parsed.filings.map(f => f.filingDate).sort()[0] ?? null,
    maxFilingDate: parsed.filings.map(f => f.filingDate).sort().at(-1) ?? null,
  }));
  for (const u of pre2020) console.log(JSON.stringify({ signalMonth:u.signalMonth, asOf:u.asOf, universeSize:u.symbols.length, sourceFilings:u.sourceFilings.length, top5:u.symbols.slice(0,5).map(x=>x.symbol) }));

  const full = pre2020.filter((u) => u.symbols.length === PRODUCTION_STRATEGY.universe.size);
  const earliest = full[0];
  if (!earliest) {
    console.log(JSON.stringify({ status:"NO_FULL_TOP80_PRE2020" }));
    return;
  }

  const currentUniverseFile = JSON.parse(await readFile(resolve("data/universe-history.json"), "utf8")) as { history: UniverseMonth[] };
  const extendedUniverse = [...full, ...currentUniverseFile.history].sort((a,b) => a.asOf.localeCompare(b.asOf));
  const neededSymbols = [...new Set(["QQQ","TQQQ", ...full.flatMap(u => u.symbols.map(x => x.symbol))])];
  const missing = neededSymbols.filter((s) => !(histories[s]?.length));
  if (missing.length) {
    const fetched = await fetchHistories(missing, 6);
    Object.assign(histories, fetched);
  }
  const missingAfterFetch = neededSymbols.filter((s) => !(histories[s]?.length));

  const extendedConfig = {
    ...PRODUCTION_STRATEGY,
    strategyId: "research-pre2020-q4-extension",
    backtestStart: earliest.asOf,
  };
  const extended = runBacktest({ histories, universeHistory: extendedUniverse, config: extendedConfig });
  const baseline = runBacktest({ histories, universeHistory: currentUniverseFile.history, config: PRODUCTION_STRATEGY });
  const equity2019 = extended.equityCurve.filter(p => p.date <= "2019-12-31").at(-1)?.equity ?? null;
  console.log(JSON.stringify({
    status:"OK",
    earliestFullSignalMonth: earliest.signalMonth,
    earliestFullAsOf: earliest.asOf,
    pre2020FullMonths: full.length,
    missingPriceSymbols: missingAfterFetch,
    extendedStats: extended.stats,
    baselineStats: baseline.stats,
    equityAt2019End: equity2019,
    extendedFinalDate: extended.equityCurve.at(-1)?.date ?? null,
  }));
}
main().catch((e) => { console.error(e); process.exitCode = 1; });
