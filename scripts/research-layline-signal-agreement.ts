import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import type { PricePoint, UniverseMonth } from "../src/lib/types";

type MarketFile = { histories: Record<string, PricePoint[]> };
type UniverseFile = { history: UniverseMonth[] };
type PilotMonth = {
  month: string;
  asOf: string;
  mapped13fTopSymbols: string[];
  mappingCoverageTop80: number;
  overlapVsNport: number | null;
};
type Pilot = { results: PilotMonth[] };

type NportBootstrap = {
  snapshots?: Array<{ holdings?: Array<{ symbol?: string; issuerName?: string }> }>;
  filings?: Array<{ holdings?: Array<{ symbol?: string; issuerName?: string }> }>;
};
type Profiles = { profiles?: Record<string, { companyName?: string }> };

function normName(input: string): string {
  return (input || "")
    .toUpperCase()
    .replaceAll("&", " AND ")
    .replace(/\b(CLASS|CL)\s+[A-Z0-9]+\b/g, " ")
    .replace(/\b(COMMON STOCK|COM STK|COMMON|ORDINARY SHARES?|ORD SHS?)\b/g, " ")
    .replace(/\b(INCORPORATED|INCORPORATION|INC|CORPORATION|CORP|COMPANY|CO|LIMITED|LTD|PLC|HOLDINGS?|HLDGS?|GROUP)\b/g, " ")
    .replace(/[^A-Z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

async function buildMappableSymbols(root: string): Promise<Set<string>> {
  const byName = new Map<string, Set<string>>();
  const add = (name: string, symbol: string) => {
    const n = normName(name);
    const s = symbol.trim().toUpperCase();
    if (!n || !s) return;
    const set = byName.get(n) ?? new Set<string>();
    set.add(s);
    byName.set(n, set);
  };

  const zlib = await import("node:zlib");
  const { promisify } = await import("node:util");
  const gunzip = promisify(zlib.gunzip);
  const bootBuf = await readFile(resolve(root, "data/sec-nport/bootstrap.json.gz"));
  const boot = JSON.parse((await gunzip(bootBuf)).toString("utf8")) as NportBootstrap;
  for (const filing of boot.snapshots ?? boot.filings ?? []) {
    for (const h of filing.holdings ?? []) add(h.issuerName ?? "", h.symbol ?? "");
  }

  try {
    const profiles = JSON.parse(await readFile(resolve(root, "public/data/company-profiles.json"), "utf8")) as Profiles;
    for (const [symbol, p] of Object.entries(profiles.profiles ?? {})) add(p.companyName ?? "", symbol);
  } catch {
    // Optional enrichment only.
  }

  const out = new Set<string>();
  for (const syms of byName.values()) if (syms.size === 1) out.add([...syms][0]);
  return out;
}

async function main() {
  const root = resolve(import.meta.dirname, "..");
  const market = JSON.parse(await readFile(resolve(root, "public/data/market-data.json"), "utf8")) as MarketFile;
  const universe = JSON.parse(await readFile(resolve(root, "data/universe-history.json"), "utf8")) as UniverseFile;
  const pilot = JSON.parse(await readFile(resolve(root, "data/research/layline13f-nport-overlap-2020.json"), "utf8")) as Pilot;
  const mappableSymbols = await buildMappableSymbols(root);
  const qqq = [...(market.histories.QQQ ?? [])].sort((a, b) => a.date.localeCompare(b.date));
  const qqqDates = qqq.map(x => x.date);
  const universeMap = new Map(universe.history.map(x => [x.signalMonth, x]));

  const rows: any[] = [];
  let selectedTotal = 0;
  let mappableSelected = 0;
  let presentSelected = 0;
  let monthsAnySignal = 0;
  let monthsBothTop2Present = 0;
  let monthsAllMappableSelectionsPresent = 0;
  let monthsBothTop2Mappable = 0;

  for (const p of pilot.results) {
    const u = universeMap.get(p.month);
    if (!u) continue;
    const i = qqqDates.findIndex(d => d > u.asOf);
    const nextSessionDate = i >= 0 ? qqqDates[i] : u.asOf;
    const signal = buildMonthlySignal({ universe: u, histories: market.histories, qqq, nextSessionDate, config: PRODUCTION_STRATEGY });
    const selected = signal?.selectedSymbols ?? [];
    if (selected.length) monthsAnySignal++;

    const details = selected.map(symbol => {
      const mappable = mappableSymbols.has(symbol);
      const present = p.mapped13fTopSymbols.includes(symbol);
      selectedTotal++;
      if (mappable) mappableSelected++;
      if (present) presentSelected++;
      return { symbol, mappableByIssuerName: mappable, presentIn13fTop80: present };
    });

    const first2 = details.slice(0, 2);
    if (first2.length === 2 && first2.every(x => x.mappableByIssuerName)) monthsBothTop2Mappable++;
    if (first2.length === 2 && first2.every(x => x.presentIn13fTop80)) monthsBothTop2Present++;
    if (selected.length && details.every(x => !x.mappableByIssuerName || x.presentIn13fTop80)) monthsAllMappableSelectionsPresent++;

    rows.push({
      month: p.month,
      asOf: u.asOf,
      selectedSymbols: selected,
      details,
      mapped13fTop80: p.mapped13fTopSymbols.length,
      mappingCoverageTop80: p.mappingCoverageTop80,
      rawTop80Overlap: p.overlapVsNport,
    });
  }

  const out = {
    method: "Production buildMonthlySignal selections evaluated against the point-in-time Layline 13F Top80 proxy for 2020. Issuer-name mapping capability is separated from true Top80 exclusion.",
    months: rows.length,
    monthsAnySignal,
    selectedTotal,
    mappableSelected,
    presentSelected,
    selectedMappabilityRate: selectedTotal ? mappableSelected / selectedTotal : null,
    selectedRetentionLowerBound: selectedTotal ? presentSelected / selectedTotal : null,
    selectedRetentionConditionalOnMappable: mappableSelected ? presentSelected / mappableSelected : null,
    monthsBothTop2Mappable: monthsAnySignal ? monthsBothTop2Mappable / monthsAnySignal : null,
    monthsBothTop2PresentLowerBound: monthsAnySignal ? monthsBothTop2Present / monthsAnySignal : null,
    monthsAllMappableSelectionsPresent: monthsAnySignal ? monthsAllMappableSelectionsPresent / monthsAnySignal : null,
    rows,
    caveat: "Layline 13F and N-PORT cover different filer populations. This diagnostic tests whether production-selected names survive a free institutional-holdings proxy; it does not establish equivalence of the two universes.",
  };
  console.log(JSON.stringify(out, null, 2));
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
