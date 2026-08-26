import { readFile, writeFile, mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { runStrategySimulation } from "../src/lib/backtest";
import { buildPointInTimeUniverse } from "../src/lib/universe/universe";
import type { PricePoint, UniverseMonth, StrategyConfig, NportFiling } from "../src/lib/types";

type Market = { histories: Record<string, PricePoint[]> };
type UF = { history: UniverseMonth[] };
type Filings = { filings: NportFiling[] };

function annualReturns(curve:{date:string;equity:number}[]){
  const years=[...new Set(curve.map(x=>x.date.slice(0,4)))];
  let prior=curve[0]?.equity ?? 1;
  return years.map(year=>{
    const rows=curve.filter(x=>x.date.startsWith(year));
    const end=rows.at(-1)?.equity ?? prior;
    const ret=prior>0?end/prior-1:0;
    prior=end;
    return {year,return:ret,startDate:rows[0]?.date,endDate:rows.at(-1)?.date};
  });
}

async function main(){
  const market=JSON.parse(await readFile(resolve("public/data/market-data.json"),"utf8")) as Market;
  const uf=JSON.parse(await readFile(resolve("data/universe-history.json"),"utf8")) as UF;
  const filingsFile=JSON.parse(await readFile(resolve("data/sec-nport/filings.json"),"utf8")) as Filings;
  const costs=[0.001,0.0025,0.005,0.01];
  const variants=costs.map(transactionCost=>{
    const config={...PRODUCTION_STRATEGY,execution:{...PRODUCTION_STRATEGY.execution,transactionCost}} as StrategyConfig;
    const sim=runStrategySimulation({histories:market.histories,universeHistory:uf.history,config});
    const entries=sim.backtest.events.filter(e=>e.type==="ENTRY_OPEN").length;
    const exits=sim.backtest.events.filter(e=>e.type==="EXIT_OPEN").length;
    return {transactionCost,stats:sim.backtest.stats,annual:annualReturns(sim.backtest.equityCurve),entries,exits};
  });

  const strictHistory:UniverseMonth[]=[];
  let previous:UniverseMonth|null=null;
  for(const u of uf.history){
    const eligible=filingsFile.filings.filter(f=>f.filingDate<u.asOf);
    const rebuilt=buildPointInTimeUniverse(eligible,u.signalMonth,u.asOf,previous);
    strictHistory.push(rebuilt); previous=rebuilt;
  }
  const strictSim=runStrategySimulation({histories:market.histories,universeHistory:strictHistory,config:PRODUCTION_STRATEGY});
  const strictPit={stats:strictSim.backtest.stats,annual:annualReturns(strictSim.backtest.equityCurve),entries:strictSim.backtest.events.filter(e=>e.type==="ENTRY_OPEN").length,exits:strictSim.backtest.events.filter(e=>e.type==="EXIT_OPEN").length};

  const sameDayFilings=uf.history.map(u=>({signalMonth:u.signalMonth,asOf:u.asOf,count:u.sourceFilings.filter(f=>f.filingDate===u.asOf).length,series:u.sourceFilings.filter(f=>f.filingDate===u.asOf).map(f=>f.seriesName)})).filter(x=>x.count>0);
  const out={generatedAt:new Date().toISOString(),strategyId:PRODUCTION_STRATEGY.strategyId,variants,strictPit,sameDayFilings,notes:{execution:"Signals and close-based risk triggers execute at the next session open.",cost:"transactionCost is applied on both buys and sells as a proportional haircut.",pit:"Baseline Universe accepts filingDate <= signal date. strictPit rebuilds every monthly Universe after excluding all filings with filingDate equal to the signal date."}};
  await mkdir(resolve("data/research/execution-feasibility"),{recursive:true});
  await writeFile(resolve("data/research/execution-feasibility/result.json"),JSON.stringify(out,null,2));
  console.log("FEASIBILITY_JSON="+JSON.stringify(out));
}
main().catch(e=>{console.error(e);process.exit(1)});
