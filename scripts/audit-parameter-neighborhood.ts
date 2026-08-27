import { readFile, mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { runStrategySimulation } from "../src/lib/backtest";
import type { PricePoint, StrategyConfig, UniverseMonth } from "../src/lib/types";

type MarketDataFile={histories?:Record<string,PricePoint[]>};
type UniverseFile={history:UniverseMonth[]};
const START="2020-01-01",END="2026-08-25";
function clone():StrategyConfig{return JSON.parse(JSON.stringify(PRODUCTION_STRATEGY)) as StrategyConfig;}

async function main(){
 const market=JSON.parse(await readFile(resolve("public/data/market-data.json"),"utf8")) as MarketDataFile;
 const universe=JSON.parse(await readFile(resolve("data/universe-history.json"),"utf8")) as UniverseFile;
 const histories=Object.fromEntries(Object.entries(market.histories??{}).map(([s,pts])=>[s,pts.filter(p=>p.date<=END)]));
 const history=universe.history.filter(u=>u.asOf>=START&&u.asOf<=END);
 const cases:Array<{label:string;factor:string;value:string;config:StrategyConfig}>=[];
 const base=clone();cases.push({label:"BASELINE",factor:"baseline",value:"current",config:base});
 for(const [m3,m6] of [[.15,.85],[.25,.75]] as const){const c=clone();c.momentum.threeMonth=m3;c.momentum.sixMonth=m6;cases.push({label:`MOM_${Math.round(m3*100)}_${Math.round(m6*100)}`,factor:"momentum_3m_6m",value:`${m3}/${m6}`,config:c});}
 for(const v of [.15,.20] as const){const c=clone();c.risk.individualStop=v;cases.push({label:`STOP_${v}`,factor:"individualStop",value:String(v),config:c});}
 for(const v of [.125,.175] as const){const c=clone();c.risk.portfolioCircuit=v;cases.push({label:`CIRCUIT_${v}`,factor:"portfolioCircuit",value:String(v),config:c});}
 for(const v of [8,12] as const){const c=clone();c.recovery.confirmationDays=v;cases.push({label:`RECOVERY_${v}`,factor:"recoveryConfirmationDays",value:String(v),config:c});}
 const rows=cases.map(({label,factor,value,config})=>{const stats=runStrategySimulation({histories,universeHistory:history,config}).backtest.stats;return{label,factor,value,stats};});
 const baseline=rows[0].stats;
 const results=rows.map(r=>({...r,cagrDifferenceVsBaseline:r.stats.cagr-baseline.cagr,maxDrawdownDifferenceVsBaseline:r.stats.maxDrawdown-baseline.maxDrawdown,calmarDifferenceVsBaseline:r.stats.calmar-baseline.calmar}));
 const byFactor=Object.fromEntries([...new Set(results.filter(r=>r.factor!=="baseline").map(r=>r.factor))].map(f=>[f,results.filter(r=>r.factor===f)]));
 const output={generatedAt:new Date().toISOString(),period:{start:START,end:END},strategyId:PRODUCTION_STRATEGY.strategyId,method:"One-factor-at-a-time neighborhood robustness audit; no optimization. All Production parameters remain fixed except the named nearby value. Momentum alternatives preserve 3M+6M weight=1. QQQ 10M MA was already separately audited and is not repeated here.",baseline,results,byFactor};
 const out=resolve("data/research/parameter-neighborhood.json");await mkdir(dirname(out),{recursive:true});await writeFile(out,JSON.stringify(output,null,2)+"\n");console.log(JSON.stringify(output,null,2));
}
main().catch(e=>{console.error(e);process.exitCode=1;});