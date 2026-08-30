import fs from "node:fs/promises";
import path from "node:path";
import { runBacktest } from "../src/lib/backtest";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import type { EquityPoint, StrategyConfig, UniverseMonth } from "../src/lib/types";

const W70:StrategyConfig={...PRODUCTION_STRATEGY,allocation:{...PRODUCTION_STRATEGY.allocation,baseTop1Weight:.7,concentratedTop1Weight:.7,maxTop1Weight:.7}};
function years(c:EquityPoint[]){const a=c[0],b=c.at(-1)!;return Math.max(1/365.25,(Date.parse(b.date)-Date.parse(a.date))/(365.25*86400000));}
function cagr(c:EquityPoint[]){return c.length>1?(c.at(-1)!.equity/c[0].equity)**(1/years(c))-1:0;}
function maxDD(c:EquityPoint[]){if(!c.length)return 0;let p=c[0].equity,d=0;for(const x of c){p=Math.max(p,x.equity);d=Math.min(d,x.equity/p-1)}return d;}
function slice(c:EquityPoint[],s:string,e:string){const x=c.filter(p=>p.date>=s&&p.date<=e);if(x.length<2)return[];const prev=[...c].reverse().find(p=>p.date<s),z=prev?[prev,...x]:x,b=z[0].equity;return z.map(p=>({...p,equity:p.equity/b}));}
function stats(c:EquityPoint[]){return{cagr:cagr(c),maxDD:maxDD(c)}}
async function main(){
 const market=JSON.parse(await fs.readFile(path.join(process.cwd(),"public/data/market-data.json"),"utf8"));
 const uf=JSON.parse(await fs.readFile(path.join(process.cwd(),"data/universe-history.json"),"utf8")) as {history:UniverseMonth[]};
 const u=[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf));
 const base=runBacktest({histories:market.histories,universeHistory:u,config:W70});
 const selected=[...new Set(base.events.flatMap(e=>e.symbols).filter(s=>s&&s!=="QQQ"))].sort();
 const rows:any[]=[];
 for(const symbol of selected){
  const uu=u.map(m=>({...m,symbols:m.symbols.filter(x=>x.symbol!==symbol)}));
  const bt=runBacktest({histories:market.histories,universeHistory:uu,config:W70});
  rows.push({symbol,full:{baseline:stats(base.equityCurve),counterfactual:stats(bt.equityCurve),cagrDelta:cagr(base.equityCurve)-cagr(bt.equityCurve)},early2020_2023:{baseline:stats(slice(base.equityCurve,'2020-01-01','2023-12-31')),counterfactual:stats(slice(bt.equityCurve,'2020-01-01','2023-12-31'))},late2024_2026:{baseline:stats(slice(base.equityCurve,'2024-01-01','2026-08-25')),counterfactual:stats(slice(bt.equityCurve,'2024-01-01','2026-08-25'))},annual:[2020,2021,2022,2023,2024,2025,2026].map(y=>({year:y,baseline:stats(slice(base.equityCurve,`${y}-01-01`,y===2026?'2026-08-25':`${y}-12-31`)),counterfactual:stats(slice(bt.equityCurve,`${y}-01-01`,y===2026?'2026-08-25':`${y}-12-31`))}))});
  console.log(`done ${symbol}`);
 }
 rows.sort((a,b)=>b.full.cagrDelta-a.full.cagrDelta);
 const top=rows.slice(0,10);
 const out={generatedAt:new Date().toISOString(),validity:{researchOnly:true,trueOOS:false,pitUniversePreserved:true,reselectionAfterRemoval:true,architectureHindsightRemains:true,parameterSearch:false,warning:'Leave-one-out diagnostic for the fixed W70 research candidate. Removing a historically selected ticker changes subsequent rankings and state paths; this measures historical dependence, not future causal alpha.'},baseline:{stats:stats(base.equityCurve),selectedSymbols:selected,eventCount:base.events.length},summary:{selectedCount:selected.length,maxSingleTickerCagrDelta:top[0]?.full.cagrDelta??0,top5:top.slice(0,5).map(x=>({symbol:x.symbol,cagrDelta:x.full.cagrDelta,counterfactualCagr:x.full.counterfactual.cagr,lateCounterfactualCagr:x.late2024_2026.counterfactual.cagr}))},rows};
 const d=path.join(process.cwd(),"data/research/w70-rolling-winner-dependence");await fs.mkdir(d,{recursive:true});await fs.writeFile(path.join(d,"result.json"),JSON.stringify(out,null,2));console.log(JSON.stringify({baseline:out.baseline,summary:out.summary},null,2));
}
main().catch(e=>{console.error(e);process.exit(1)});
