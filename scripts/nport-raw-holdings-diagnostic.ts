import { readFile, mkdir, writeFile } from "node:fs/promises";
import { gunzipSync } from "node:zlib";
import { resolve } from "node:path";
import type { NportFiling } from "../src/lib/types";

async function main() {
  const raw = gunzipSync(await readFile(resolve("data/sec-nport/bootstrap.json.gz"))).toString("utf8");
  const parsed = JSON.parse(raw) as { snapshots?: NportFiling[]; filings?: NportFiling[]; startQuarter?: string; endQuarter?: string };
  const filings = parsed.snapshots ?? parsed.filings ?? [];
  const holdingKeys = new Set<string>();
  const filingKeys = new Set<string>();
  const series = new Set<string>();
  const reportDates = new Set<string>();
  const filingDates = new Set<string>();
  let holdings = 0;
  let positiveWeight = 0;
  let duplicateSeriesReport = 0;
  const seenSeriesReport = new Set<string>();
  const sampleHoldings: unknown[] = [];
  for (const f of filings) {
    Object.keys(f as unknown as Record<string, unknown>).forEach(k => filingKeys.add(k));
    series.add(f.seriesId);
    reportDates.add(f.reportDate);
    filingDates.add(f.filingDate);
    const sr = `${f.seriesId}|${f.reportDate}`;
    if (seenSeriesReport.has(sr)) duplicateSeriesReport++; else seenSeriesReport.add(sr);
    for (const h of f.holdings ?? []) {
      holdings++;
      Object.keys(h as unknown as Record<string, unknown>).forEach(k => holdingKeys.add(k));
      if (Number(h.weight) > 0) positiveWeight++;
      if (sampleHoldings.length < 20) sampleHoldings.push(h);
    }
  }
  const reportSorted = [...reportDates].sort();
  const filingSorted = [...filingDates].sort();
  const out = {
    source: { startQuarter: parsed.startQuarter ?? null, endQuarter: parsed.endQuarter ?? null },
    counts: { filings: filings.length, series: series.size, holdings, positiveWeight, reportDates: reportDates.size, filingDates: filingDates.size, duplicateSeriesReport },
    dateRange: { reportMin: reportSorted[0] ?? null, reportMax: reportSorted.at(-1) ?? null, filingMin: filingSorted[0] ?? null, filingMax: filingSorted.at(-1) ?? null },
    filingKeys: [...filingKeys].sort(),
    holdingKeys: [...holdingKeys].sort(),
    canTrackWithinSeriesOverTime: seenSeriesReport.size > series.size,
    sampleHoldings,
  };
  await mkdir(resolve("data/research/nport-raw-holdings-diagnostic"), { recursive: true });
  await writeFile(resolve("data/research/nport-raw-holdings-diagnostic/result.json"), JSON.stringify(out, null, 2));
  console.log(JSON.stringify(out, null, 2));
}
main().catch(e => { console.error(e); process.exitCode = 1; });
