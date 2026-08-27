import { readFile, mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { runStrategySimulation } from "../src/lib/backtest";
import type { PricePoint, UniverseMonth } from "../src/lib/types";

type MarketDataFile={histories?:Record<string,PricePoint[]>};
type UniverseFile={history:UniverseMonth[]};
const START="2020-01-01", END="2026-08-25", PATHS=50, SEED=20260828;

function rng(seed:number){let a=seed>>>0;return()=>{a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
function perturb(history:UniverseMonth[],dropFraction:number,seed:number){const r=rng(seed);return history.map(u=>{const rows=[...u.symbols];const k=Math.max(1,Math.round(rows.length*dropFraction));const idx=rows.map((_,i)=>i);for(let i=idx.length-1;i>0;i--){const j=Math.floor(r()*(i+1));[idx[i],idx[j]]=[idx[j],idx[i]];}const drop=new Set(idx.slice(0,k));return{...u,symbols:rows.filter((_,i)=>!drop.has(i))};});}
function quantile(xs:number[],q:number){const a=[...xs].sort((x,y)=>x-y);if(!a.length)return NaN;const p=(a.length-1)*q,lo=Math.floor(p),hi=Math.ceil(p);return a[lo]+(a[hi]-a[lo])*(p-lo);}
function summarize(xs:number[]){return{min:Math.min(...xs),p05:quantile(xs,.05),p25:quantile(xs,.25),median:quantile(xs,.5),mean:xs.reduce((s,x)=>s+x,0)/xs.length,p75:quantile(xs,.75),p95:quantile(xs,.95),max:Math.max(...xs)};}

async function main(){
 const market=JSON.parse(await readFile(resolve("public/data/market-data.json"),"utf8")) as MarketDataFile;
 const universe=JSON.parse(await readFile(resolve("data/universe-history.json"),"utf8")) as UniverseFile;
 const histories=Object.fromEntries(Object.entries(market.histories??{}).map(([s,pts])=>[s,pts.filter(p=>p.date<=END)]));
 const history=universe.history.filter(u=>u.asOf>=START&&u.asOf<=END);
 const baseline=runStrategySimulation({histories,universeHistory:history,config:PRODUCTION_STRATEGY}).backtest.stats;
 const scenarios=[] as any[];
 for(const [label,fraction,offset] of [["DROP_5PCT",.05,1000],["DROP_10PCT",.10,2000]] as const){
   const rows=[] as any[];
   for(let i=0;i<PATHS;i++){
     const h=perturb(history,fraction,SEED+offset+i);
     const stats=runStrategySimulation({histories,universeHistory:h,config:PRODUCTION_STRATEGY}).backtest.stats;
     rows.push({path:i+1,seed:SEED+offset+i,cagr:stats.cagr,maxDrawdown:stats.maxDrawdown,annualizedVolatility:stats.annualizedVolatility,calmar:stats.calmar,finalEquity:stats.finalEquity});
     if((i+1)%10===0) console.error(`${label}: ${i+1}/${PATHS}`);
   }
   scenarios.push({label,dropFraction:fraction,paths:PATHS,summary:{cagr:summarize(rows.map(r=>r.cagr)),maxDrawdown:summarize(rows.map(r=>r.maxDrawdown)),calmar:summarize(rows.map(r=>r.calmar)),finalEquity:summarize(rows.map(r=>r.finalEquity)),probabilityCagrBelow50:rows.filter(r=>r.cagr<.5).length/PATHS,probabilityCagrBelowBaseline:rows.filter(r=>r.cagr<baseline.cagr).length/PATHS},rows});
 }
 const output={generatedAt:new Date().toISOString(),period:{start:START,end:END},strategyId:PRODUCTION_STRATEGY.strategyId,seed:SEED,method:"Point-in-time Top80 missing-candidate perturbation Monte Carlo. For every Universe snapshot and every path, 5% or 10% of the stored Top80 members are randomly removed; no outside-Top80 replacement is available in universe-history.json. Production ranking, QQQ gate, stops, circuit, recovery, execution and costs are otherwise unchanged. This tests robustness to missing/misclassified eligible names, not Top80 boundary replacement noise.",baseline,scenarios};
 const out=resolve("data/research/universe-perturbation.json");await mkdir(dirname(out),{recursive:true});await writeFile(out,JSON.stringify(output,null,2)+"\n");console.log(JSON.stringify(output,null,2));
}
main().catch(e=>{console.error(e);process.exitCode=1;});