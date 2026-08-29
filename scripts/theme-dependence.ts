import fs from "node:fs/promises";
import path from "node:path";
import { runBacktest } from "../src/lib/backtest";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import type { EquityPoint, UniverseMonth } from "../src/lib/types";

const GROUPS:Record<string,string[]>={
  "SEMICONDUCTORS_HARDWARE":["AMAT","INTC","LRCX","MU","NVDA","QCOM","WDC"],
  "CYBER_CLOUD_NETWORK":["ANET","CRWD","FTNT","NET","TWLO","ZS"],
  "SOFTWARE_AI_ADTECH":["APP","MSFT","PLTR"],
  "FINTECH_CRYPTO_PAYMENTS":["COF","COIN","HOOD","MA"],
  "CONSUMER_INTERNET_MEDIA":["ETSY","META","NFLX","PINS","RBLX"],
  "HEALTHCARE":["GILD","LLY"],
  "INDUSTRIAL_ELECTRIFICATION":["GEV"],
  "EV_AUTO":["TSLA"]
};
function years(c:EquityPoint[]){return Math.max(1/365.25,(Date.parse(c.at(-1)!.date)-Date.parse(c[0].date))/(365.25*86400000))}
function cagr(c:EquityPoint[]){return(c.at(-1)!.equity/c[0].equity)**(1/years(c))-1}
function maxDD(c:EquityPoint[]){let p=c[0].equity,d=0;for(const x of c){p=Math.max(p,x.equity);d=Math.min(d,x.equity/p-1)}return d}
function monthsAgo(date:string,n:number){const d=new Date(date+"T00:00:00Z");d.setUTCMonth(d.getUTCMonth()-n);return d.toISOString().slice(0,10)}
function rolling(c:EquityPoint[],months:number){const out:{end:string;start:string;return:number}[]=[];let j=0;for(let i=0;i<c.length;i++){const target=monthsAgo(c[i].date,months);while(j+1<i&&c[j+1].date<target)j++;const k=(j+1<i&&c[j].date<target)?j+1:j;if(k<i&&Date.parse(c[i].date)-Date.parse(c[k].date)>=months*27*86400000)out.push({end:c[i].date,start:c[k].date,return:c[i].equity/c[k].equity-1})}return out}
async function main(){
 const market=JSON.parse(await fs.readFile(path.join(process.cwd(),"public/data/market-data.json"),"utf8"));
 const uf=JSON.parse(await fs.readFile(path.join(process.cwd(),"data/universe-history.json"),"utf8")) as {history:UniverseMonth[]};
 const u0=[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf));
 const base=runBacktest({histories:market.histories,universeHistory:u0,config:PRODUCTION_STRATEGY});
 const base12=rolling(base.equityCurve,12),base24=rolling(base.equityCurve,24);
 const eventMentions:Record<string,number>={};for(const e of base.events)for(const s of new Set(e.symbols)){if(s!=="QQQ")eventMentions[s]=(eventMentions[s]??0)+1}
 const results:any[]=[];
 for(const [theme,members] of Object.entries(GROUPS)){
   const remove=new Set(members);const u=u0.map(m=>({...m,symbols:m.symbols.filter(x=>!remove.has(x.symbol))}));
   const bt=runBacktest({histories:market.histories,universeHistory:u,config:PRODUCTION_STRATEGY});
   const cf12=new Map(rolling(bt.equityCurve,12).map(x=>[x.end,x])),cf24=new Map(rolling(bt.equityCurve,24).map(x=>[x.end,x]));
   const d12=base12.filter(x=>cf12.has(x.end)).map(x=>({start:x.start,end:x.end,delta:x.return-cf12.get(x.end)!.return,baseReturn:x.return,counterfactualReturn:cf12.get(x.end)!.return}));
   const d24=base24.filter(x=>cf24.has(x.end)).map(x=>({start:x.start,end:x.end,delta:x.return-cf24.get(x.end)!.return,baseReturn:x.return,counterfactualReturn:cf24.get(x.end)!.return}));
   const dep=(d:any[])=>({meanDelta:d.reduce((s,x)=>s+x.delta,0)/(d.length||1),positiveDeltaShare:d.filter(x=>x.delta>0).length/(d.length||1),maxDependence:[...d].sort((a,b)=>b.delta-a.delta)[0]??null,minDependence:[...d].sort((a,b)=>a.delta-b.delta)[0]??null});
   results.push({theme,members,selectedEventMentions:Object.fromEntries(members.map(s=>[s,eventMentions[s]??0])),full:{counterfactualCagr:cagr(bt.equityCurve),cagrDelta:cagr(base.equityCurve)-cagr(bt.equityCurve),counterfactualMaxDD:maxDD(bt.equityCurve)},rolling12:dep(d12),rolling24:dep(d24)});
 }
 results.sort((a,b)=>b.full.cagrDelta-a.full.cagrDelta);
 const selected=[...new Set(base.events.flatMap(e=>e.symbols).filter(s=>s&&s!=="QQQ"))].sort();const covered=new Set(Object.values(GROUPS).flat());
 const output={generatedAt:new Date().toISOString(),strategyId:PRODUCTION_STRATEGY.strategyId,method:"Leave-group-out counterfactual using fixed broad business/theme buckets. Remove all members of one group from every PIT universe month, rerun Production selection/state machine, compare full and rolling 12M/24M outcomes.",validity:{trueOOS:false,architectureHindsightRemains:true,groupDefinitionsSetAfterTickerScreen:true,reselectionAfterRemoval:true,warning:"Theme buckets were defined after observing which tickers had been historically selected, so theme-level results are descriptive diagnostics, not independent confirmation. Buckets are broad business categories, not optimized partitions."},coverage:{selectedSymbols:selected,uncoveredSelected:selected.filter(s=>!covered.has(s))},baseline:{cagr:cagr(base.equityCurve),maxDD:maxDD(base.equityCurve),eventMentions},groups:GROUPS,results};
 const dir=path.join(process.cwd(),"data/research/theme-dependence");await fs.mkdir(dir,{recursive:true});await fs.writeFile(path.join(dir,"result.json"),JSON.stringify(output,null,2));console.log(JSON.stringify({coverage:output.coverage,results:results.map(x=>({theme:x.theme,cagrDelta:x.full.cagrDelta,counterfactualCagr:x.full.counterfactualCagr,cfDD:x.full.counterfactualMaxDD,r12mean:x.rolling12.meanDelta,r12max:x.rolling12.maxDependence,r24mean:x.rolling24.meanDelta,r24max:x.rolling24.maxDependence}))},null,2));
}
main().catch(e=>{console.error(e);process.exit(1)});
