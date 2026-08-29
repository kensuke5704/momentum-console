import { readFile } from "node:fs/promises";
import { gunzipSync } from "node:zlib";
import { resolve } from "node:path";
import { buildPointInTimeUniverse } from "../src/lib/universe/universe";
import type { NportFiling, UniverseMonth } from "../src/lib/types";

async function main() {
  const source = JSON.parse(gunzipSync(await readFile(resolve("data/sec-nport/bootstrap.json.gz"))).toString("utf8")) as {
    startQuarter?: string;
    endQuarter?: string;
    snapshots?: NportFiling[];
  };
  const filings = source.snapshots ?? [];
  const dates = filings.map((f) => f.filingDate).sort();
  console.log(JSON.stringify({
    startQuarter: source.startQuarter ?? null,
    endQuarter: source.endQuarter ?? null,
    filingCount: filings.length,
    minFilingDate: dates[0] ?? null,
    maxFilingDate: dates.at(-1) ?? null,
  }));

  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as { histories?: Record<string, Array<{date:string}>> };
  const qqq = market.histories?.QQQ ?? [];
  const monthEnds = new Map<string,string>();
  for (const p of qqq) if (p.date >= "2018-01-01" && p.date < "2020-01-01") monthEnds.set(p.date.slice(0,7), p.date);

  let previous: UniverseMonth | null = null;
  const results = [] as Array<Record<string, unknown>>;
  for (const [signalMonth, asOf] of [...monthEnds].sort(([a],[b]) => a.localeCompare(b))) {
    const u = buildPointInTimeUniverse(filings, signalMonth, asOf, previous);
    results.push({
      signalMonth,
      asOf,
      universeSize: u.symbols.length,
      sourceFilings: u.sourceFilings.length,
      oldestSourceFiling: u.sourceFilings.map((x) => x.filingDate).sort()[0] ?? null,
      newestSourceFiling: u.sourceFilings.map((x) => x.filingDate).sort().at(-1) ?? null,
      top5: u.symbols.slice(0,5).map((x) => x.symbol),
    });
    previous = u;
  }
  for (const row of results) console.log(JSON.stringify(row));
  const full = results.filter((r) => r.universeSize === 80);
  console.log(JSON.stringify({ earliestFullTop80: full[0] ?? null, pre2020FullMonths: full.length }));
}
main().catch((e) => { console.error(e); process.exitCode = 1; });
