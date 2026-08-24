import { createInterface } from "node:readline";
import { spawn } from "node:child_process";
import { mkdir, readFile, rm, stat, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { tmpdir } from "node:os";
import type { NportFiling } from "../src/lib/types";

const CACHE = process.env.NPORT_CACHE_DIR ?? join(tmpdir(), "momentum-console-nport");
const START = process.env.NPORT_START_QUARTER ?? "2020q1";
const OUTPUT = resolve("data/sec-nport/filings.json");
const SEC_BASE = "https://www.sec.gov/files/dera/data/form-n-port-data-sets";
const USER_AGENT = process.env.SEC_USER_AGENT ?? "MomentumConsole/2.0 kensuke5704@users.noreply.github.com";

function latestAvailableQuarter(): string {
  const now = new Date();
  let year = now.getUTCFullYear();
  let quarter = Math.ceil((now.getUTCMonth() + 1) / 3) - 1;
  if (quarter === 0) { year -= 1; quarter = 4; }
  return `${year}q${quarter}`;
}
function quarters(start: string, end: string): string[] {
  const parse = (value: string) => ({ year: Number(value.slice(0, 4)), quarter: Number(value.at(-1)) });
  const a = parse(start), b = parse(end), output: string[] = [];
  for (let year = a.year; year <= b.year; year++) for (let quarter = 1; quarter <= 4; quarter++) {
    if (year === a.year && quarter < a.quarter) continue;
    if (year === b.year && quarter > b.quarter) continue;
    output.push(`${year}q${quarter}`);
  }
  return output;
}
async function exists(path: string) { try { await stat(path); return true; } catch { return false; } }
async function download(quarter: string, path: string) {
  if (await exists(path)) return;
  const response = await fetch(`${SEC_BASE}/${quarter}_nport.zip`, { headers: { "User-Agent": USER_AGENT, Accept: "application/zip" }, signal: AbortSignal.timeout(300_000) });
  if (!response.ok) throw new Error(`${quarter}: SEC returned HTTP ${response.status}`);
  await writeFile(path, Buffer.from(await response.arrayBuffer()));
}
async function eachTsv(path: string, table: string, visit: (row: string[], index: Record<string, number>) => void) {
  const child = spawn("unzip", ["-p", path, `${table}.tsv`], { stdio: ["ignore", "pipe", "inherit"] });
  const lines = createInterface({ input: child.stdout, crlfDelay: Infinity });
  let index: Record<string, number> | null = null;
  for await (const raw of lines) {
    const row = raw.replace(/\r$/, "").split("\t");
    if (!index) { index = Object.fromEntries(row.map((name, position) => [name, position])); continue; }
    visit(row, index);
  }
  const code = await new Promise<number | null>((resolveCode) => child.on("close", resolveCode));
  if (code !== 0) throw new Error(`Unable to extract ${table} from ${path}`);
}
const value = (row: string[], index: Record<string, number>, key: string) => row[index[key]] ?? "";
function parseDate(raw: string): string {
  const match = /^(\d{1,2})-([A-Z]{3})-(\d{4})$/i.exec(raw);
  if (!match) return raw.slice(0, 10);
  const months: Record<string, string> = { JAN: "01", FEB: "02", MAR: "03", APR: "04", MAY: "05", JUN: "06", JUL: "07", AUG: "08", SEP: "09", OCT: "10", NOV: "11", DEC: "12" };
  return `${match[3]}-${months[match[2].toUpperCase()]}-${match[1].padStart(2, "0")}`;
}

async function main() {
  await mkdir(CACHE, { recursive: true });
  let filings: NportFiling[] = [], processedQuarters: string[] = [];
  try {
    const existing = JSON.parse(await readFile(OUTPUT, "utf8")) as { filings?: NportFiling[]; quarters?: string[] };
    filings = existing.filings ?? []; processedQuarters = existing.quarters ?? [];
  } catch { /* first reproducible extraction */ }
  const requested = quarters(START, process.env.NPORT_END_QUARTER ?? latestAvailableQuarter());
  for (const quarter of requested) {
    if (processedQuarters.includes(quarter)) continue;
    const zip = join(CACHE, `${quarter}_nport.zip`);
    console.log(`SEC N-PORT ${quarter}`);
    await download(quarter, zip);
    const submissions = new Map<string, { reportDate: string; filingDate: string }>();
    await eachTsv(zip, "SUBMISSION", (row, index) => submissions.set(value(row, index, "ACCESSION_NUMBER"), { reportDate: parseDate(value(row, index, "REPORT_DATE")), filingDate: parseDate(value(row, index, "FILING_DATE")) }));
    const funds = new Map<string, NportFiling>();
    await eachTsv(zip, "FUND_REPORTED_INFO", (row, index) => {
      const accession = value(row, index, "ACCESSION_NUMBER");
      const submission = submissions.get(accession);
      const seriesName = value(row, index, "SERIES_NAME").trim();
      if (!submission || !/(^|\W)ETF($|\W)|EXCHANGE[ -]TRADED/i.test(seriesName)) return;
      funds.set(accession, { accession, seriesId: value(row, index, "SERIES_ID"), seriesName, reportDate: submission.reportDate, filingDate: submission.filingDate, holdings: [] });
    });
    const holdings = new Map<string, { fund: NportFiling; symbol?: string; issuerName: string; weight: number }>();
    await eachTsv(zip, "FUND_REPORTED_HOLDING", (row, index) => {
      const fund = funds.get(value(row, index, "ACCESSION_NUMBER"));
      if (!fund || value(row, index, "ASSET_CAT") !== "EC" || value(row, index, "INVESTMENT_COUNTRY") !== "US" || value(row, index, "ISSUER_TYPE") !== "CORP") return;
      holdings.set(value(row, index, "HOLDING_ID"), { fund, issuerName: value(row, index, "ISSUER_NAME"), weight: Number(value(row, index, "PERCENTAGE")) || 0 });
    });
    await eachTsv(zip, "IDENTIFIERS", (row, index) => {
      const holding = holdings.get(value(row, index, "HOLDING_ID"));
      const symbol = value(row, index, "IDENTIFIER_TICKER").trim().toUpperCase();
      if (holding && !holding.symbol && /^[A-Z][A-Z0-9.^=-]{0,14}$/.test(symbol)) holding.symbol = symbol;
    });
    for (const holding of holdings.values()) if (holding.symbol && holding.weight > 0) holding.fund.holdings.push({ symbol: holding.symbol, issuerName: holding.issuerName, weight: holding.weight });
    for (const fund of funds.values()) if (fund.holdings.length) filings.push({ ...fund, holdings: fund.holdings.sort((a, b) => b.weight - a.weight) });
    processedQuarters.push(quarter);
    if (process.env.KEEP_NPORT_ZIPS !== "1") await rm(zip, { force: true });
  }
  filings.sort((a, b) => a.filingDate.localeCompare(b.filingDate) || a.seriesId.localeCompare(b.seriesId));
  await mkdir(resolve("data/sec-nport"), { recursive: true });
  await writeFile(OUTPUT, `${JSON.stringify({ generatedAt: new Date().toISOString(), source: "SEC Form N-PORT quarterly public datasets", quarters: processedQuarters.sort(), filings })}\n`);
  console.log(`Saved ${filings.length} point-in-time filings to ${OUTPUT}`);
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
