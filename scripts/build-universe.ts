import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { buildPointInTimeUniverse, isCompletedSignalMonth } from "../src/lib/universe/universe";
import { fetchYahooHistory } from "../src/lib/yahoo";
import type { NportFiling, UniverseMonth } from "../src/lib/types";

async function optionalLiveFilings(): Promise<NportFiling[]> {
  try { return (JSON.parse(await readFile(resolve("data/sec-nport/live-filings.json"), "utf8")) as { filings?: NportFiling[] }).filings ?? []; }
  catch { return []; }
}

async function main() {
  const raw = JSON.parse(await readFile(resolve("data/sec-nport/filings.json"), "utf8")) as { filings: NportFiling[] };
  const live = await optionalLiveFilings();
  const merged = new Map<string, NportFiling>();
  for (const filing of raw.filings) merged.set(filing.accession, filing);
  for (const filing of live) merged.set(filing.accession, filing);
  const filings = [...merged.values()];
  const qqq = await fetchYahooHistory("QQQ");
  const monthEnds = new Map<string, string>();
  for (const point of qqq) monthEnds.set(point.date.slice(0, 7), point.date);
  const history: UniverseMonth[] = [];
  let previous: UniverseMonth | null = null;
  const currentCalendarMonth = new Date().toISOString().slice(0, 7);
  for (const [signalMonth, asOf] of [...monthEnds].filter(([month]) => month >= "2020-01" && isCompletedSignalMonth(month, currentCalendarMonth)).sort(([a], [b]) => a.localeCompare(b))) {
    const current = buildPointInTimeUniverse(filings, signalMonth, asOf, previous);
    history.push(current);
    previous = current;
  }
  const current = history.at(-1) ?? null;
  await mkdir(resolve("data"), { recursive: true });
  await mkdir(resolve("public/data"), { recursive: true });
  const payload = `${JSON.stringify({ generatedAt: new Date().toISOString(), strategyId: "momentum-dynamic-2026-08-v1", history })}\n`;
  await writeFile(resolve("data/universe-history.json"), payload);
  await writeFile(resolve("public/data/universe-history.json"), payload);
  await writeFile(resolve("public/data/universe-current.json"), `${JSON.stringify({ generatedAt: new Date().toISOString(), strategyId: "momentum-dynamic-2026-08-v1", current })}\n`);
  console.log(`Built ${history.length} point-in-time universes from ${raw.filings.length} quarterly + ${live.length} live filings; current size ${current?.symbols.length ?? 0}`);
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
