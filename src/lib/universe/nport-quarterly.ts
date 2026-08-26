import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { basename } from "node:path";
import { createInterface } from "node:readline";
import type { NportFiling } from "../types";

const REQUIRED_HEADERS = {
  SUBMISSION: ["ACCESSION_NUMBER", "REPORT_DATE", "FILING_DATE"],
  FUND_REPORTED_INFO: ["ACCESSION_NUMBER", "SERIES_NAME", "SERIES_ID"],
  FUND_REPORTED_HOLDING: ["ACCESSION_NUMBER", "HOLDING_ID", "ASSET_CAT", "INVESTMENT_COUNTRY", "ISSUER_TYPE", "ISSUER_NAME", "PERCENTAGE"],
  IDENTIFIERS: ["HOLDING_ID", "IDENTIFIER_TICKER"],
} as const;

type RequiredTable = keyof typeof REQUIRED_HEADERS;

export type QuarterlyNportImport = {
  quarter: string;
  zipBytes: number;
  sha256: string;
  submissions: number;
  filings: NportFiling[];
};

export function quarterFromZipName(path: string): string {
  const match = /^(\d{4}q[1-4])_nport\.zip$/i.exec(basename(path));
  if (!match) throw new Error("ZIP filename must match the official SEC pattern YYYYqN_nport.zip");
  return match[1].toLowerCase();
}

export function validateRequiredHeaders(table: RequiredTable, headers: string[]): void {
  const present = new Set(headers);
  const missing = REQUIRED_HEADERS[table].filter((header) => !present.has(header));
  if (missing.length) throw new Error(`${table}.tsv is missing required headers: ${missing.join(", ")}`);
}

function runUnzip(args: string[]): Promise<void> {
  return new Promise((resolve, reject) => {
    const child = spawn("unzip", args, { stdio: ["ignore", "ignore", "pipe"] });
    let error = "";
    child.stderr.setEncoding("utf8");
    child.stderr.on("data", (chunk) => { error += chunk; });
    child.on("error", reject);
    child.on("close", (code) => code === 0 ? resolve() : reject(new Error(error.trim() || `unzip exited with ${code}`)));
  });
}

async function eachTsv(
  zipPath: string,
  table: RequiredTable,
  visit: (row: string[], index: Record<string, number>) => void,
): Promise<number> {
  const child = spawn("unzip", ["-p", zipPath, `${table}.tsv`], { stdio: ["ignore", "pipe", "pipe"] });
  const lines = createInterface({ input: child.stdout, crlfDelay: Infinity });
  let index: Record<string, number> | null = null;
  let rows = 0;
  let error = "";
  child.stderr.setEncoding("utf8");
  child.stderr.on("data", (chunk) => { error += chunk; });
  for await (const raw of lines) {
    const row = raw.replace(/\r$/, "").split("\t");
    if (!index) {
      validateRequiredHeaders(table, row);
      index = Object.fromEntries(row.map((name, position) => [name, position]));
      continue;
    }
    visit(row, index);
    rows++;
  }
  const code = await new Promise<number | null>((resolveCode, reject) => {
    child.on("error", reject);
    child.on("close", resolveCode);
  });
  if (code !== 0) throw new Error(error.trim() || `Unable to extract ${table}.tsv from ${zipPath}`);
  if (!index) throw new Error(`${table}.tsv is empty`);
  return rows;
}

const value = (row: string[], index: Record<string, number>, key: string) => row[index[key]] ?? "";

function parseDate(raw: string): string {
  const match = /^(\d{1,2})-([A-Z]{3})-(\d{4})$/i.exec(raw);
  if (!match) return raw.slice(0, 10);
  const months: Record<string, string> = { JAN: "01", FEB: "02", MAR: "03", APR: "04", MAY: "05", JUN: "06", JUL: "07", AUG: "08", SEP: "09", OCT: "10", NOV: "11", DEC: "12" };
  return `${match[3]}-${months[match[2].toUpperCase()]}-${match[1].padStart(2, "0")}`;
}

export function quarterForDate(date: string): string {
  const match = /^(\d{4})-(\d{2})-\d{2}$/.exec(date);
  if (!match) throw new Error(`Invalid filing date in N-PORT dataset: ${date}`);
  return `${match[1]}q${Math.floor((Number(match[2]) - 1) / 3) + 1}`;
}

export async function parseQuarterlyNportZip(zipPath: string): Promise<QuarterlyNportImport> {
  const quarter = quarterFromZipName(zipPath);
  const file = await stat(zipPath);
  if (!file.isFile() || file.size < 1) throw new Error("N-PORT ZIP is empty or not a regular file");
  const hash = createHash("sha256");
  for await (const chunk of createReadStream(zipPath)) hash.update(chunk);
  const sha256 = hash.digest("hex");
  await runUnzip(["-tq", zipPath]);

  const submissions = new Map<string, { reportDate: string; filingDate: string }>();
  const submissionRows = await eachTsv(zipPath, "SUBMISSION", (row, index) => {
    const accession = value(row, index, "ACCESSION_NUMBER");
    const reportDate = parseDate(value(row, index, "REPORT_DATE"));
    const filingDate = parseDate(value(row, index, "FILING_DATE"));
    if (!accession || !reportDate || !filingDate) throw new Error("SUBMISSION.tsv contains an incomplete required value");
    if (quarterForDate(filingDate) !== quarter) throw new Error(`${accession}: filing date ${filingDate} does not belong to ${quarter}`);
    submissions.set(accession, { reportDate, filingDate });
  });
  if (submissionRows < 1) throw new Error("SUBMISSION.tsv contains no data rows");

  const funds = new Map<string, NportFiling>();
  await eachTsv(zipPath, "FUND_REPORTED_INFO", (row, index) => {
    const accession = value(row, index, "ACCESSION_NUMBER");
    const submission = submissions.get(accession);
    const seriesName = value(row, index, "SERIES_NAME").trim();
    if (!submission || !/(^|\W)ETF($|\W)|EXCHANGE[ -]TRADED/i.test(seriesName)) return;
    funds.set(accession, { accession, seriesId: value(row, index, "SERIES_ID"), seriesName, reportDate: submission.reportDate, filingDate: submission.filingDate, holdings: [] });
  });

  const holdings = new Map<string, { fund: NportFiling; symbol?: string; issuerName: string; weight: number }>();
  await eachTsv(zipPath, "FUND_REPORTED_HOLDING", (row, index) => {
    const fund = funds.get(value(row, index, "ACCESSION_NUMBER"));
    if (!fund || value(row, index, "ASSET_CAT") !== "EC" || value(row, index, "INVESTMENT_COUNTRY") !== "US" || value(row, index, "ISSUER_TYPE") !== "CORP") return;
    holdings.set(value(row, index, "HOLDING_ID"), { fund, issuerName: value(row, index, "ISSUER_NAME"), weight: Number(value(row, index, "PERCENTAGE")) || 0 });
  });
  await eachTsv(zipPath, "IDENTIFIERS", (row, index) => {
    const holding = holdings.get(value(row, index, "HOLDING_ID"));
    const symbol = value(row, index, "IDENTIFIER_TICKER").trim().toUpperCase();
    if (holding && !holding.symbol && /^[A-Z][A-Z0-9.^=-]{0,14}$/.test(symbol)) holding.symbol = symbol;
  });
  for (const holding of holdings.values()) {
    if (holding.symbol && holding.weight > 0) holding.fund.holdings.push({ symbol: holding.symbol, issuerName: holding.issuerName, weight: holding.weight });
  }
  const filings = [...funds.values()]
    .filter((fund) => fund.seriesId && fund.holdings.length)
    .map((fund) => ({ ...fund, holdings: fund.holdings.sort((a, b) => b.weight - a.weight) }))
    .sort((a, b) => a.filingDate.localeCompare(b.filingDate) || a.seriesId.localeCompare(b.seriesId));
  if (!filings.length) throw new Error("No eligible ETF filings were parsed from the N-PORT ZIP");
  return { quarter, zipBytes: file.size, sha256, submissions: submissionRows, filings };
}
