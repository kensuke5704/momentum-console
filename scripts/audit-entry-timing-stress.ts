import { readFile, mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import type { PricePoint } from "../src/lib/types";

type MarketDataFile = { histories?: Record<string, PricePoint[]> };
type Trade = { symbol:string; entryDate:string; exitDate:string; grossAllocation:number; exitReason:string };
type Attribution = { period:{start:string;end:string}; allTrades:Trade[] };

type RepricedTrade = Trade & { delayedEntryDate:string; delayedExitDate:string; delayedEntryOpen:number; delayedExitOpen:number; shares:number; netProceeds:number; returnOnAllocation:number };

const COST = PRODUCTION_STRATEGY.execution.transactionCost;

function yearsBetween(a:string,b:string){ return (Date.parse(`${b}T00:00:00Z`)-Date.parse(`${a}T00:00:00Z`))/86_400_000/365.25; }
function cagr(finalEquity:number,start:string,end:string){ return Math.pow(finalEquity,1/yearsBetween(start,end))-1; }

function statsFromEpisodeReturns(episodes:Array<{date:string;multiplier:number}>, start:string, end:string){
  let equity=1, peak=1, maxDrawdown=0;
  for(const ep of episodes){ equity*=ep.multiplier; peak=Math.max(peak,equity); maxDrawdown=Math.min(maxDrawdown,equity/peak-1); }
  return { finalEquity:equity, cagr:cagr(equity,start,end), episodeBoundaryMaxDrawdown:maxDrawdown };
}

async function main(){
  const attribution=JSON.parse(await readFile(resolve("data/research/trade-attribution.json"),"utf8")) as Attribution;
  const market=JSON.parse(await readFile(resolve("public/data/market-data.json"),"utf8")) as MarketDataFile;
  const histories=market.histories??{};
  const qqqDates=(histories.QQQ??[]).filter(p=>p.date<=attribution.period.end).map(p=>p.date).sort();
  const dateIndex=new Map(qqqDates.map((d,i)=>[d,i]));
  const maps=Object.fromEntries(Object.entries(histories).map(([s,pts])=>[s,new Map(pts.map(p=>[p.date,p]))]));

  const scenarios=[] as Array<Record<string,unknown>>;
  for(const extraSessions of [0,1,2]){
    const repriced:RepricedTrade[]=[];
    let skipped=0;
    for(const t of attribution.allTrades){
      const ei=dateIndex.get(t.entryDate), xi=dateIndex.get(t.exitDate);
      if(ei==null||xi==null){ skipped++; continue; }
      const delayedEntryDate=qqqDates[ei+extraSessions];
      const delayedExitDate=qqqDates[xi+extraSessions];
      if(!delayedEntryDate||!delayedExitDate||delayedExitDate>attribution.period.end){ skipped++; continue; }
      const entry=maps[t.symbol]?.get(delayedEntryDate) as PricePoint|undefined;
      const exit=maps[t.symbol]?.get(delayedExitDate) as PricePoint|undefined;
      const entryOpen=entry?.open, exitOpen=exit?.open;
      if(!(entryOpen&&exitOpen)){ skipped++; continue; }
      const shares=t.grossAllocation*(1-COST)/entryOpen;
      const netProceeds=shares*exitOpen*(1-COST);
      repriced.push({...t,delayedEntryDate,delayedExitDate,delayedEntryOpen:entryOpen,delayedExitOpen:exitOpen,shares,netProceeds,returnOnAllocation:netProceeds/t.grossAllocation-1});
    }
    const groups=new Map<string,RepricedTrade[]>();
    for(const t of repriced){ const key=`${t.entryDate}|${t.exitDate}`; const rows=groups.get(key)??[]; rows.push(t); groups.set(key,rows); }
    const episodes=[...groups.values()].map(rows=>({
      date:rows[0].delayedExitDate,
      multiplier: rows.reduce((s,t)=>s+t.netProceeds,0)/rows.reduce((s,t)=>s+t.grossAllocation,0)
    })).sort((a,b)=>a.date.localeCompare(b.date));
    const stats=statsFromEpisodeReturns(episodes,attribution.period.start,attribution.period.end);
    scenarios.push({
      extraSessions,
      description: extraSessions===0?"Production fixed-path open repricing":"Same baseline trade path; both entry and exit shifted by extra US trading sessions and executed at shifted session open.",
      tradeLots:repriced.length, skippedLots:skipped, ...stats,
      meanLotReturn:repriced.reduce((s,t)=>s+t.returnOnAllocation,0)/(repriced.length||1),
      medianLotReturn:[...repriced].sort((a,b)=>a.returnOnAllocation-b.returnOnAllocation)[Math.floor(repriced.length/2)]?.returnOnAllocation??null
    });
  }
  const baseline=scenarios[0] as any;
  for(const s of scenarios as any[]){ s.cagrDifferenceVsZero=s.cagr-baseline.cagr; s.finalEquityRatioVsZero=s.finalEquity/baseline.finalEquity; }
  const output={
    generatedAt:new Date().toISOString(), period:attribution.period, strategyId:PRODUCTION_STRATEGY.strategyId,
    method:"Fixed-path execution timing stress using audited daily OHLC only. Baseline symbols, signal dates, stops, circuit/recovery path, target allocations and exit reasons are held fixed. Entry and exit execution are both shifted by +0/+1/+2 US trading sessions and repriced at that session open with Production transaction costs. This isolates dependence on exact open timing; it is not a causal full state-machine counterfactual. Intraday +15m/+30m/VWAP is not tested because full-history intraday data is unavailable.",
    scenarios
  };
  const out=resolve("data/research/entry-timing-stress.json"); await mkdir(dirname(out),{recursive:true}); await writeFile(out,JSON.stringify(output,null,2)+"\n"); console.log(JSON.stringify(output,null,2));
}
main().catch(e=>{console.error(e);process.exitCode=1;});