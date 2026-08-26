import type { NportFiling, UniverseHolding } from "../types";

const SEC = "https://www.sec.gov";
const UA = process.env.SEC_USER_AGENT ?? "MomentumConsole/2.0 kensuke5704@users.noreply.github.com";
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export type EdgarIndexEntry = {
  cik: string;
  companyName: string;
  formType: "NPORT-P" | "NPORT-P/A";
  filingDate: string;
  accession: string;
};

export type EdgarDailyIndexResult = {
  date: string;
  available: boolean;
  entries: EdgarIndexEntry[];
};

function quarterFor(date: string): number {
  return Math.floor(Number(date.slice(5, 7)) / 3) + (Number(date.slice(5, 7)) % 3 === 0 ? 0 : 1);
}

function ymd(date: string): string { return date.replaceAll("-", ""); }

async function secFetch(url: string, accept = "text/plain,*/*"): Promise<Response | null> {
  let lastStatus = 0;
  for (let attempt = 0; attempt < 4; attempt++) {
    const res = await fetch(url, { headers: { "User-Agent": UA, Accept: accept }, signal: AbortSignal.timeout(30_000) }).catch(() => null);
    if (res?.ok) return res;
    if (res?.status === 404) return null;
    lastStatus = res?.status ?? 0;
    if (res?.status === 403) {
      const body = await res.text().catch(() => "");
      if (/Undeclared Automated Tool|Request Rate Threshold/i.test(body)) {
        throw new Error(`SEC live EDGAR access blocked (${res.status}) for ${url}; refusing to continue with a stale Universe`);
      }
    }
    await sleep(450 * (attempt + 1));
  }
  throw new Error(`SEC live EDGAR request failed (${lastStatus || "network"}) for ${url}; refusing to continue with a stale Universe`);
}

export async function fetchDailyNportIndexResult(date: string): Promise<EdgarDailyIndexResult> {
  const year = date.slice(0, 4), q = quarterFor(date);
  const url = `${SEC}/Archives/edgar/daily-index/${year}/QTR${q}/master.${ymd(date)}.idx`;
  const res = await secFetch(url);
  if (!res) return { date, available: false, entries: [] };
  const text = await res.text();
  const rows: EdgarIndexEntry[] = [];
  for (const line of text.split(/\r?\n/)) {
    const parts = line.split("|");
    if (parts.length !== 5) continue;
    const [cik, companyName, formType, filingDate, filename] = parts;
    if (formType !== "NPORT-P" && formType !== "NPORT-P/A") continue;
    const m = /([0-9]{10}-[0-9]{2}-[0-9]{6})\.txt$/i.exec(filename);
    if (!m) continue;
    rows.push({ cik, companyName, formType, filingDate, accession: m[1] });
  }
  return { date, available: true, entries: rows };
}

export async function fetchDailyNportIndex(date: string): Promise<EdgarIndexEntry[]> {
  return (await fetchDailyNportIndexResult(date)).entries;
}

function decodeXml(value: string): string {
  return value.replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'").trim();
}
const tag = (xml: string, name: string) => {
  const m = new RegExp(`<${name}(?:\\s[^>]*)?>([\\s\\S]*?)<\\/${name}>`, "i").exec(xml);
  return m ? decodeXml(m[1].replace(/<[^>]+>/g, "")) : "";
};
const attr = (xml: string, name: string, attribute: string) => {
  const m = new RegExp(`<${name}\\b[^>]*\\b${attribute}=["']([^"']+)["'][^>]*\\/?\\s*>`, "i").exec(xml);
  return m ? decodeXml(m[1]) : "";
};

export function parseNportXml(xml: string, accession: string, filingDate: string): NportFiling | null {
  const seriesId = tag(xml, "seriesId");
  const seriesName = tag(xml, "seriesName");
  const reportDate = tag(xml, "repPdDate") || tag(xml, "repPdEnd");
  if (!seriesId || !seriesName || !reportDate) return null;
  const holdings: UniverseHolding[] = [];
  for (const match of xml.matchAll(/<invstOrSec\b[^>]*>([\s\S]*?)<\/invstOrSec>/gi)) {
    const block = match[1];
    if (tag(block, "assetCat") !== "EC" || tag(block, "issuerCat") !== "CORP" || tag(block, "invCountry") !== "US") continue;
    const symbol = attr(block, "ticker", "value").toUpperCase();
    const weight = Number(tag(block, "pctVal"));
    if (!/^[A-Z][A-Z0-9.^=-]{0,14}$/.test(symbol) || !(weight > 0)) continue;
    holdings.push({ symbol, issuerName: tag(block, "name") || undefined, weight });
  }
  return { accession, seriesId, seriesName, reportDate, filingDate, holdings };
}

async function discoverPrimaryXml(cik: string, accession: string): Promise<string | null> {
  const clean = accession.replaceAll("-", "");
  const base = `${SEC}/Archives/edgar/data/${Number(cik)}/${clean}`;
  const direct = await secFetch(`${base}/primary_doc.xml`, "application/xml,text/xml,*/*");
  if (direct) return direct.text();
  const idx = await secFetch(`${base}/index.json`, "application/json,*/*");
  if (!idx) return null;
  const body = await idx.json() as { directory?: { item?: Array<{ name?: string }> } };
  const names = body.directory?.item?.map((x) => x.name ?? "") ?? [];
  for (const name of names.filter((x) => /\.xml$/i.test(x))) {
    const res = await secFetch(`${base}/${name}`, "application/xml,text/xml,*/*");
    if (!res) continue;
    const text = await res.text();
    if (/<submissionType>NPORT-P(?:\/A)?<\/submissionType>/i.test(text)) return text;
  }
  return null;
}

export async function fetchLiveNportFiling(entry: EdgarIndexEntry): Promise<NportFiling | null> {
  const xml = await discoverPrimaryXml(entry.cik, entry.accession);
  if (!xml) return null;
  return parseNportXml(xml, entry.accession, entry.filingDate);
}

export function dateRange(start: string, end: string): string[] {
  const out: string[] = [];
  for (let t = Date.parse(`${start}T12:00:00Z`), last = Date.parse(`${end}T12:00:00Z`); t <= last; t += 86_400_000) out.push(new Date(t).toISOString().slice(0, 10));
  return out;
}
