import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import type { NportFiling } from "../src/lib/types";
import { dateRange, fetchDailyNportIndex, fetchLiveNportFiling } from "../src/lib/universe/edgar-live";

const OUTPUT = resolve("data/sec-nport/live-filings.json");
const BASELINE = resolve("data/sec-nport/filings.json");
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

function addDays(date: string, days: number): string {
  return new Date(Date.parse(`${date}T12:00:00Z`) + days * 86_400_000).toISOString().slice(0, 10);
}

async function main() {
  const baseline = JSON.parse(await readFile(BASELINE, "utf8")) as { filings: NportFiling[]; quarters?: string[] };
  const maxBaselineDate = baseline.filings.reduce((max, f) => f.filingDate > max ? f.filingDate : max, "2020-01-01");
  let prior: NportFiling[] = [];
  try { prior = (JSON.parse(await readFile(OUTPUT, "utf8")) as { filings?: NportFiling[] }).filings ?? []; } catch {}
  const start = process.env.NPORT_LIVE_START ?? addDays(maxBaselineDate, -3);
  const end = process.env.NPORT_LIVE_END ?? new Date().toISOString().slice(0, 10);
  const entries = [];
  for (const date of dateRange(start, end)) {
    const rows = await fetchDailyNportIndex(date);
    if (rows.length) console.log(`${date}: ${rows.length} NPORT-P filings`);
    entries.push(...rows);
    await sleep(120);
  }
  const byAccession = new Map(prior.map((f) => [f.accession, f]));
  const todo = entries.filter((e) => !byAccession.has(e.accession));
  let ok = 0, failed = 0, cursor = 0, done = 0;
  async function worker() {
    while (true) {
      const i = cursor++;
      if (i >= todo.length) return;
      const filing = await fetchLiveNportFiling(todo[i]);
      if (filing?.holdings.length) { byAccession.set(filing.accession, filing); ok++; }
      else failed++;
      done++;
      if (done % 25 === 0 || done === todo.length) console.log(`parsed ${done}/${todo.length}; ok=${ok}; failed=${failed}`);
      await sleep(650);
    }
  }
  await Promise.all(Array.from({ length: Math.min(4, Math.max(1, todo.length)) }, () => worker()));
  const filings = [...byAccession.values()].sort((a, b) => a.filingDate.localeCompare(b.filingDate) || a.accession.localeCompare(b.accession));
  await mkdir(resolve("data/sec-nport"), { recursive: true });
  await writeFile(OUTPUT, `${JSON.stringify({ generatedAt: new Date().toISOString(), source: "SEC EDGAR daily master index + individual NPORT-P primary XML", baselineMaxFilingDate: maxBaselineDate, scanStart: start, scanEnd: end, discovered: entries.length, parsedNew: ok, parseFailed: failed, filings })}\n`);
  console.log(`LIVE_NPORT_SUMMARY=${JSON.stringify({ baselineMaxFilingDate: maxBaselineDate, start, end, discovered: entries.length, prior: prior.length, parsedNew: ok, parseFailed: failed, totalLive: filings.length })}`);
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
