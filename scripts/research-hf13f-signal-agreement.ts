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
  sourceQuarter: string;
  mapped13fTop80: number;
  mappingCoverageTop80: number;
  intersection: number;
  overlapVsNport: number;
  jaccardOnMapped: number | null;
  "13fSymbols": string[];
  nportSymbols: string[];
};
type Pilot = {
  mappingDetails: Record<string, { permco: string | null }>;
  results: PilotMonth[];
};

async function main() {
  const root = resolve(import.meta.dirname, "..");
  const market = JSON.parse(await readFile(resolve(root, "public/data/market-data.json"), "utf8")) as MarketFile;
  const universe = JSON.parse(await readFile(resolve(root, "data/universe-history.json"), "utf8")) as UniverseFile;
  const pilot = JSON.parse(await readFile(resolve(root, "data/research/hf13f-nport-pilot.json"), "utf8")) as Pilot;
  const qqq = [...(market.histories.QQQ ?? [])].sort((a,b)=>a.date.localeCompare(b.date));
  const qqqDates = qqq.map(x=>x.date);
  const universeMap = new Map(universe.history.map(x=>[x.signalMonth,x]));

  const rows: any[] = [];
  let selectedTotal=0, mappedSelected=0, presentSelected=0, monthsAnySignal=0, monthsBothPresent=0, monthsAllMappedPresent=0;
  for (const p of pilot.results) {
    const u = universeMap.get(p.month);
    if (!u) continue;
    const i = qqqDates.findIndex(d=>d>u.asOf);
    const nextSessionDate = i>=0 ? qqqDates[i] : u.asOf;
    const signal = buildMonthlySignal({ universe:u, histories:market.histories, qqq, nextSessionDate, config:PRODUCTION_STRATEGY });
    const selected = signal?.selectedSymbols ?? [];
    if (selected.length) monthsAnySignal++;
    const details = selected.map(symbol=>{
      const mapped = Boolean(pilot.mappingDetails[symbol]?.permco);
      const present = p["13fSymbols"].includes(symbol);
      selectedTotal++; if (mapped) mappedSelected++; if (present) presentSelected++;
      return { symbol, mappedToPermco:mapped, presentIn13fTop80:present };
    });
    if (selected.length>=2 && details.slice(0,2).every(x=>x.presentIn13fTop80)) monthsBothPresent++;
    if (selected.length && details.every(x=>!x.mappedToPermco || x.presentIn13fTop80)) monthsAllMappedPresent++;
    rows.push({ month:p.month, asOf:u.asOf, selectedSymbols:selected, details, mapped13fTop80:p.mapped13fTop80, rawTop80Overlap:p.overlapVsNport });
  }
  const out = {
    method:"Production buildMonthlySignal selection evaluated against the free 13F proxy Top80 from the same pilot. This is a lower-bound signal-retention test because unmapped PERMCOs are never counted as present.",
    months:rows.length,
    monthsAnySignal,
    selectedTotal,
    mappedSelected,
    presentSelected,
    selectedMappingRate:selectedTotal?mappedSelected/selectedTotal:null,
    selectedRetentionLowerBound:selectedTotal?presentSelected/selectedTotal:null,
    selectedRetentionConditionalOnMapped:mappedSelected?presentSelected/mappedSelected:null,
    monthsBothTop2PresentLowerBound:monthsAnySignal?monthsBothPresent/monthsAnySignal:null,
    monthsAllMappedSelectionsPresent:monthsAnySignal?monthsAllMappedPresent/monthsAnySignal:null,
    rows,
    caveat:"A selected symbol that fails the PERMCO price-fingerprint map is classified as not present. Therefore lower-bound retention cannot distinguish identifier failure from true 13F-universe exclusion. Conditional-on-mapped retention addresses this separately."
  };
  console.log(JSON.stringify(out,null,2));
}

main().catch((error)=>{ console.error(error); process.exitCode=1; });
