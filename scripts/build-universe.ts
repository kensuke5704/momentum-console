import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { gunzipSync } from "node:zlib";
import { buildPointInTimeUniverse, isCompletedSignalMonth } from "../src/lib/universe/universe";
import { fetchYahooHistory } from "../src/lib/yahoo";
import type { NportFiling, UniverseMonth } from "../src/lib/types";

async function main() {
  let filings: NportFiling[];
  try {
    filings = (JSON.parse(await readFile(resolve("data/sec-nport/filings.json"), "utf8")) as { filings: NportFiling[] }).filings;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    filings = (JSON.parse(gunzipSync(await readFile(resolve("data/sec-nport/bootstrap.json.gz"))).toString("utf8")) as { snapshots: NportFiling[] }).snapshots;
  }
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
  console.log(`Built ${history.length} point-in-time universes; current size ${current?.symbols.length ?? 0}`);
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
