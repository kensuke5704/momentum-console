import fs from "node:fs/promises";
import path from "node:path";
import { runBacktest } from "../src/lib/backtest";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import type { EquityPoint, UniverseMonth } from "../src/lib/types";

type Stats={start:string;end:string;totalReturn:number;maxDD:number};
function windowStats(curve:EquityPoint[],start:string,end:string):Stats|null{const r=curve.filter(x=>x.date>=start&&x.date<=end);if(r.length<2)return null;const a=r[0].equity,b=r.at(-1)!.equity;let peak=a,dd=0;for(const x of r){peak=Math.max(peak,x.equity);dd=Math.min(dd,x.equity/peak-1)}return{start:r[0].date,end:r.at(-1)!.date,totalReturn:b/a-1,maxDD:dd};}
function monthsAgo(date:string,n:number){const d=new Date(date+"T00:00:00Z");d.setUTCMonth(d.getUTCMonth()-n);return d.toISOString().slice(0,10)}
function years(curve:EquityPoint[]){const a=curve[0],b=curve.at(-1)!;return Math.max(1/365.25,(Date.parse(b.date)-Date.parse(a.date))/(365.25*86400000));}
function cagr(curve:EquityPoint[]){return (curve.at(-1)!.equity/curve[0].equity)**(1/years(curve))-1}
function maxDD(curve:EquityPoint[]){let p=curve[0].equity,d=0;for(const x of curve){p=Math.max(p,x.equity);d=Math.min(d,x.equity/p-1)}return d}
function rolling(curve:EquityPoint[],months:number){const out:{end:string;start:string;return:number}[]=[];for(let i=0;i<curve.length;i++){const end=curve[i].date,startTarget=monthsAgo(end,months);const j=curve.findIndex(x=>x.date>=startTarget);if(j>=0&&j<i&&Date.parse(end)-Date.parse(curve[j].date)>=months*27*86400000)out.push({end,start:curve[j].date,return:curve[i].equity/curve[j].equity-1});}return out;}
async function main(){
 const market=JSON.parse(await fs.readFile(path.join(process.cwd(),"public/data/market-data.json"),"utf8"));
 const uf=JSON.parse(await fs.readFile(path.join(process.cwd(),"data/universe-history.json"),"utf8")) as {history:UniverseMonth[]};
 const baseUniverse=[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf));
 const baseline=runBacktest({histories:market.histories,universeHistory:baseUniverse,config:PRODUCTION_STRATEGY});
 const selected=[...new Set(baseline.events.flatMap(e=>e.symbols).filter(s=>s&&s!=="QQQ"))].sort();
 const base12=rolling(baseline.equityCurve,12),base24=rolling(baseline.equityCurve,24);
 const tickerResults:any[]=[];
 for(const symbol of selected){
   const u=baseUniverse.map(m=>({...m,symbols:m.symbols.filter(x=>x.symbol!==symbol)}));
   const bt=runBacktest({histories:market.histories,universeHistory:u,config:PRODUCTION_STRATEGY});
   const r12=rolling(bt.equityCurve,12),r24=rolling(bt.equityCurve,24);
   const map12=new Map(r12.map(x=>[x.end,x])),map24=new Map(r24.map(x=>[x.end,x]));
   const del12=base12.filter(x=>map12.has(x.end)).map(x=>({end:x.end,start:x.start,delta:x.return-map12.get(x.end)!.return,baseReturn:x.return,counterfactualReturn:map12.get(x.end)!.return}));
   const del24=base24.filter(x=>map24.has(x.end)).map(x=>({end:x.end,start:x.start,delta:x.return-map24.get(x.end)!.return,baseReturn:x.return,counterfactualReturn:map24.get(x.end)!.return}));
   const sort=(a:{delta:number},b:{delta:number})=>b.delta-a.delta;
   tickerResults.push({symbol,full:{baselineCagr:cagr(baseline.equityCurve),counterfactualCagr:cagr(bt.equityCurve),cagrDelta:cagr(baseline.equityCurve)-cagr(bt.equityCurve),baselineMaxDD:maxDD(baseline.equityCurve),counterfactualMaxDD:maxDD(bt.equityCurve)},rolling12:{maxDependence:[...del12].sort(sort)[0]??null,minDependence:[...del12].sort((a,b)=>a.delta-b.delta)[0]??null,meanDelta:del12.reduce((s,x)=>s+x.delta,0)/(del12.length||1),positiveDeltaShare:del12.filter(x=>x.delta>0).length/(del12.length||1)},rolling24:{maxDependence:[...del24].sort(sort)[0]??null,minDependence:[...del24].sort((a,b)=>a.delta-b.delta)[0]??null,meanDelta:del24.reduce((s,x)=>s+x.delta,0)/(del24.length||1),positiveDeltaShare:del24.filter(x=>x.delta>0).length/(del24.length||1)}});
   console.log(`done ${symbol}`);
 }
 tickerResults.sort((a,b)=>b.full.cagrDelta-a.full.cagrDelta);
 const output={generatedAt:new Date().toISOString(),strategyId:PRODUCTION_STRATEGY.strategyId,method:"Counterfactual leave-one-out: remove one historically selected ticker from every PIT universe month, rerun the full Production ranking/state machine, and compare full-period plus rolling 12M/24M outcomes.",validity:{trueOOS:false,architectureHindsightRemains:true,reselectionAfterRemoval:true,pointInTimeUniversePreserved:true,warning:"This diagnoses historical dependence within the already-selected Production architecture. It is not a causal estimate of future alpha or the probability a ticker/theme disappears. Leave-one-out effects can be nonlinear because removal changes subsequent rankings, allocations, stops and recovery paths."},baseline:{cagr:cagr(baseline.equityCurve),maxDD:maxDD(baseline.equityCurve),selectedSymbols:selected,eventCount:baseline.events.length},tickerResults};
 const dir=path.join(process.cwd(),"data/research/rolling-winner-dependence");await fs.mkdir(dir,{recursive:true});await fs.writeFile(path.join(dir,"result.json"),JSON.stringify(output,null,2));console.log(JSON.stringify({baseline:output.baseline,top:tickerResults.slice(0,15).map(x=>({symbol:x.symbol,cagrDelta:x.full.cagrDelta,counterfactualCagr:x.full.counterfactualCagr,r12Max:x.rolling12.maxDependence,r24Max:x.rolling24.maxDependence}))},null,2));
}
main().catch(e=>{console.error(e);process.exit(1)});
