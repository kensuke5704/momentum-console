import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { gunzipSync } from "node:zlib";
import { buildPointInTimeUniverse, isCompletedSignalMonth } from "../src/lib/universe/universe";
import { defaultNportOperations, fallbackUniverse, latestCompletedNportQuarter, nextNportImportDeadline, requiresUniverseFallback } from "../src/lib/nport-operations";
import { fetchYahooHistory } from "../src/lib/yahoo";
import type { NportFiling, NportOperations, UniverseMonth } from "../src/lib/types";

async function readPreviousCurrent(): Promise<UniverseMonth | null> {
  try { return (JSON.parse(await readFile(resolve("public/data/universe-current.json"), "utf8")) as { current?: UniverseMonth }).current ?? null; } catch { return null; }
}

async function readOperations(activeQuarter: string | null): Promise<NportOperations> {
  try { return JSON.parse(await readFile(resolve("data/nport-operations.json"), "utf8")) as NportOperations; }
  catch { return defaultNportOperations(activeQuarter); }
}

async function main() {
  let filings: NportFiling[];
  let activeQuarter: string | null = null;
  try {
    const source = JSON.parse(await readFile(resolve("data/sec-nport/filings.json"), "utf8")) as { filings: NportFiling[]; quarters?: string[] };
    filings = source.filings;
    activeQuarter = source.quarters?.at(-1) ?? null;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    const source = JSON.parse(gunzipSync(await readFile(resolve("data/sec-nport/bootstrap.json.gz"))).toString("utf8")) as { snapshots: NportFiling[]; endQuarter?: string };
    filings = source.snapshots;
    activeQuarter = source.endQuarter ?? null;
  }
  const previousPublished = await readPreviousCurrent();
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
  let current = history.at(-1) ?? null;
  const fallback = Boolean(current && previousPublished && requiresUniverseFallback(current.signalMonth, activeQuarter));
  if (current && previousPublished && fallback) {
    current = fallbackUniverse(previousPublished, current.signalMonth, current.asOf);
    history[history.length - 1] = current;
  }
  const existingOperations = await readOperations(activeQuarter);
  const operations: NportOperations = {
    ...existingOperations,
    activeQuarter,
    nextImportDeadlineAt: nextNportImportDeadline(activeQuarter),
    universeMode: fallback ? "FALLBACK" : "CURRENT",
    fallbackReason: fallback ? `Quarter ${latestCompletedNportQuarter(current!.signalMonth)} is not imported; previous valid Top80 retained` : null,
  };
  await mkdir(resolve("data"), { recursive: true });
  await mkdir(resolve("public/data"), { recursive: true });
  const payload = `${JSON.stringify({ generatedAt: new Date().toISOString(), strategyId: "momentum-dynamic-2026-08-v1", history })}\n`;
  await writeFile(resolve("data/universe-history.json"), payload);
  await writeFile(resolve("public/data/universe-history.json"), payload);
  await writeFile(resolve("public/data/universe-current.json"), `${JSON.stringify({ generatedAt: new Date().toISOString(), strategyId: "momentum-dynamic-2026-08-v1", current })}\n`);
  await writeFile(resolve("data/nport-operations.json"), `${JSON.stringify(operations, null, 2)}\n`);
  console.log(`Built ${history.length} point-in-time universes; current size ${current?.symbols.length ?? 0}`);
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
