import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import type { NportFiling, UniverseMonth } from "../src/lib/types";
import { buildPointInTimeUniverse } from "../src/lib/universe/universe";

type FilingFile = { filings: NportFiling[] };
type UniverseFile = { history: UniverseMonth[] };

async function main() {
  const quarterly = JSON.parse(await readFile(resolve("data/sec-nport/filings.json"), "utf8")) as FilingFile;
  const live = JSON.parse(await readFile(resolve("data/sec-nport/live-filings.json"), "utf8")) as FilingFile;
  const published = JSON.parse(await readFile(resolve("public/data/universe-history.json"), "utf8")) as UniverseFile;
  const baseHistory = published.history;
  const latest = baseHistory.at(-1);
  if (!latest) throw new Error("published Universe history is empty");
  const merged = new Map<string, NportFiling>();
  for (const f of quarterly.filings) merged.set(f.accession, f);
  for (const f of live.filings) merged.set(f.accession, f);
  const previous = baseHistory.at(-2) ?? null;
  const rebuilt = buildPointInTimeUniverse([...merged.values()], latest.signalMonth, latest.asOf, previous);
  const oldSymbols = latest.symbols.map((x) => x.symbol), newSymbols = rebuilt.symbols.map((x) => x.symbol);
  const oldSet = new Set(oldSymbols), newSet = new Set(newSymbols);
  const added = newSymbols.filter((x) => !oldSet.has(x));
  const removed = oldSymbols.filter((x) => !newSet.has(x));
  const intersection = oldSymbols.filter((x) => newSet.has(x)).length;
  const union = new Set([...oldSymbols, ...newSymbols]).size;
  const oldRank = new Map(latest.symbols.map((x) => [x.symbol, x.universeRank]));
  const rankChanges = rebuilt.symbols.map((x) => ({ symbol: x.symbol, oldRank: oldRank.get(x.symbol) ?? null, newRank: x.universeRank, delta: oldRank.has(x.symbol) ? (oldRank.get(x.symbol)! - x.universeRank) : null })).filter((x) => x.oldRank !== x.newRank).sort((a,b) => Math.abs(b.delta ?? 999)-Math.abs(a.delta ?? 999));
  const result = {
    generatedAt: new Date().toISOString(), signalMonth: latest.signalMonth, asOf: latest.asOf,
    quarterlyFilings: quarterly.filings.length, liveOverlayFilings: live.filings.length, mergedFilings: merged.size,
    publishedSourceFilings: latest.sourceFilings.length, rebuiltSourceFilings: rebuilt.sourceFilings.length,
    publishedSize: oldSymbols.length, rebuiltSize: newSymbols.length,
    jaccard: union ? intersection / union : 1,
    added, removed, rankChanges: rankChanges.slice(0, 30),
    identicalTop80: added.length === 0 && removed.length === 0,
    rebuilt,
  };
  await mkdir(resolve("data/research/live-nport-ingestion"), { recursive: true });
  await writeFile(resolve("data/research/live-nport-ingestion/result.json"), `${JSON.stringify(result, null, 2)}\n`);
  console.log("LIVE_NPORT_AUDIT=" + JSON.stringify({ signalMonth: result.signalMonth, asOf: result.asOf, quarterlyFilings: result.quarterlyFilings, liveOverlayFilings: result.liveOverlayFilings, mergedFilings: result.mergedFilings, publishedSourceFilings: result.publishedSourceFilings, rebuiltSourceFilings: result.rebuiltSourceFilings, jaccard: result.jaccard, added, removed, identicalTop80: result.identicalTop80 }));
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
