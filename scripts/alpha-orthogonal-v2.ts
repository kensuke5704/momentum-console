// research rerun: 2026-08-30 current-data transferability screen
import fs from "node:fs/promises";
import path from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import { initialEngineState, transitionDay } from "../src/lib/strategy/state-machine";
import { nextUsTradingSession } from "../src/lib/trading-calendar";
import { performanceStats } from "../src/lib/backtest";
import type { EquityPoint, MonthlySignal, PricePoint, UniverseMonth } from "../src/lib/types";

type Variant={id:string;kind:"PROD"|"PATH"|"ACCEL"|"BREADTH"|"HVCASH"|"HVVOL"};
const VARIANTS:Variant[]=[
 {id:"PRODUCTION",kind:"PROD"},
 {id:"PATH25",kind:"PATH"},
 {id:"ACCEL25",kind:"ACCEL"},
 {id:"BREADTH_STRICT",kind:"BREADTH"},
 {id:"HV_CASH30",kind:"HVCASH"},
 {id:"HV_VOL50",kind:"HVVOL"},
];
const mean=(x:number[])=>x.length?x.reduce((a,b)=>a+b,0)/x.length:0;
const sd=(x:number[])=>{if(x.length<2)return 0;const m=mean(x);return Math.sqrt(x.reduce((s,v)=>s+(v-m)**2,0)/(x.length-1))};
const z=(v:number,m:number,s:number)=>s>0?(v-m)/s:0;
function through(ps:PricePoint[],date:string){return ps.filter(p=>p.date<=date)}
function dlog(ps:PricePoint[],date:string,days:number){const x=through(ps,date).slice(-(days+1));if(x.length<days+1)return null;return Math.log(x.at(-1)!.close/x[0].close)}
function rv(ps:PricePoint[],date:string,days:number){const x=through(ps,date).slice(-(days+1));if(x.length<days+1)return null;const r=x.slice(1).map((p,i)=>Math.log(p.close/x[i].close));return sd(r)*Math.sqrt(252)}
function efficiency(ps:PricePoint[],date:string,days=126){const x=through(ps,date).slice(-(days+1));if(x.length<days+1)return null;const net=Math.abs(Math.log(x.at(-1)!.close/x[0].close));let travel=0;for(let i=1;i<x.length;i++)travel+=Math.abs(Math.log(x[i].close/x[i-1].close));return travel>0?net/travel:0}
function accel(ps:PricePoint[],date:string){const x=through(ps,date);if(x.length<127)return null;const a=x.slice(-64);const b=x.slice(-127,-63);if(a.length<64||b.length<64)return null;return Math.log(a.at(-1)!.close/a[0].close)-Math.log(b.at(-1)!.close/b[0].close)}
function qVol(qqq:PricePoint[],date:string){return rv(qqq,date,20)}
function breadth(hist:Record<string,PricePoint[]>,base:MonthlySignal){const vals=base.universe.map(s=>dlog(hist[s]??[],base.signalDate,126)).filter((x):x is number=>x!=null);return vals.length?vals.filter(x=>x>0).length/vals.length:0}
function rerank(base:MonthlySignal,hist:Record<string,PricePoint[]>,qqq:PricePoint[],v:Variant):MonthlySignal{
 if(v.kind==="PROD"||!base.marketRiskOn)return base;
 const qv=qVol(qqq,base.signalDate);
 if(v.kind==="HVCASH"&&qv!=null&&qv>=0.30)return {...base,selectedSymbols:[],targetWeights:[],allocationMode:"CASH",zGap:null};
 let rows=base.candidates.filter(c=>c.eligible&&c.score!=null);
 if(v.kind==="BREADTH"&&breadth(hist,base)<0.50){rows=rows.filter(c=>(c.scoreSpread??-Infinity)>=0.05);if(rows.length<2)return {...base,selectedSymbols:[],targetWeights:[],allocationMode:"CASH",zGap:null};}
 if(rows.length<2)return base;
 const moms=rows.map(c=>c.score as number),mm=mean(moms),ms=sd(moms);
 const aux=rows.map(c=>{
   if(v.kind==="PATH")return efficiency(hist[c.symbol]??[],base.signalDate);
   if(v.kind==="ACCEL")return accel(hist[c.symbol]??[],base.signalDate);
   if(v.kind==="HVVOL"&&qv!=null&&qv>=0.30)return rv(hist[c.symbol]??[],base.signalDate,60);
   return 0;
 });
 const av=aux.filter((x):x is number=>x!=null),am=mean(av),as=sd(av);
 const scored=rows.map((c,i)=>{let a=z(c.score as number,mm,ms);const x=aux[i];if(v.kind==="PATH"&&x!=null)a+=0.25*z(x,am,as);if(v.kind==="ACCEL"&&x!=null)a+=0.25*z(x,am,as);if(v.kind==="HVVOL"&&qv!=null&&qv>=0.30&&x!=null)a-=0.50*z(x,am,as);return{c,a}}).sort((a,b)=>b.a-a.a||a.c.symbol.localeCompare(b.c.symbol));
 const pick=scored.slice(0,2).map(x=>x.c);const raw=base.candidates.filter(c=>c.eligible&&c.score!=null).map(c=>c.score as number);const disp=sd(raw);const zg=disp>0?((pick[0].score as number)-(pick[1].score as number))/disp:0;const conc=zg>=PRODUCTION_STRATEGY.allocation.concentrationZGap;const w1=Math.min(PRODUCTION_STRATEGY.allocation.maxTop1Weight,conc?PRODUCTION_STRATEGY.allocation.concentratedTop1Weight:PRODUCTION_STRATEGY.allocation.baseTop1Weight);
 return {...base,selectedSymbols:pick.map(c=>c.symbol),targetWeights:[w1,1-w1],zGap:zg,allocationMode:conc?"70/30":"50/50"};
}
function sim(hist:Record<string,PricePoint[]>,universe:UniverseMonth[],v:Variant){const qqq=[...(hist.QQQ??[])].sort((a,b)=>a.date.localeCompare(b.date));const dates=qqq.map(p=>p.date),idx=new Map(dates.map((d,i)=>[d,i]));const pm=Object.fromEntries(Object.entries(hist).map(([s,ps])=>[s,new Map(ps.map(p=>[p.date,p]))]));const um=new Map(universe.map(u=>[u.asOf,u]));let state=initialEngineState(PRODUCTION_STRATEGY);const curve:EquityPoint[]=[];for(let i=0;i<dates.length;i++){const date=dates[i];if(date<PRODUCTION_STRATEGY.backtestStart)continue;const next=dates[i+1]??nextUsTradingSession(date),u=um.get(date);let sig=u?buildMonthlySignal({universe:u,histories:hist,qqq,nextSessionDate:next,config:PRODUCTION_STRATEGY}):null;if(sig)sig=rerank(sig,hist,qqq,v);const sy=new Set(["QQQ",...state.currentPositions.map(p=>p.symbol),...(state.pendingSignal?.selectedSymbols??[]),...state.nextAction.symbols,...(sig?.selectedSymbols??[])]);const prices=Object.fromEntries([...sy].map(s=>[s,pm[s]?.get(date)]));state=transitionDay(state,{date,prices,qqqHistoryThroughClose:qqq.slice(0,(idx.get(date)??i)+1),monthlySignal:sig,nextSessionDate:next},PRODUCTION_STRATEGY);curve.push({date,equity:state.currentEquity,drawdown:state.drawdown})}return{variant:v.id,curve}}
function slice(c:EquityPoint[],s:string,e:string){const x=c.filter(p=>p.date>=s&&p.date<=e);if(!x.length)return[];const b=x[0].equity;return x.map(p=>({...p,equity:p.equity/b}))}
async function main(){const market=JSON.parse(await fs.readFile(path.join(process.cwd(),"public/data/market-data.json"),"utf8")) as {histories:Record<string,PricePoint[]>};const uf=JSON.parse(await fs.readFile(path.join(process.cwd(),"data/universe-history.json"),"utf8")) as {history:UniverseMonth[]};const universe=[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf));const sims=VARIANTS.map(v=>sim(market.histories,universe,v));const years=[2022,2023,2024,2025,2026];const full=sims.map(s=>({variant:s.variant,stats:performanceStats(s.curve)}));const oos=years.map(y=>({year:y,rows:sims.map(s=>({variant:s.variant,stats:performanceStats(slice(s.curve,`${y}-01-01`,y===2026?"2026-08-25":`${y}-12-31`))}))}));const prod=full.find(x=>x.variant==="PRODUCTION")!;const summary=full.filter(x=>x.variant!=="PRODUCTION").map(x=>({variant:x.variant,cagrDelta:x.stats.cagr-prod.stats.cagr,maxDdDelta:x.stats.maxDrawdown-prod.stats.maxDrawdown,oosWins:oos.filter(y=>y.rows.find(r=>r.variant===x.variant)!.stats.cagr>y.rows.find(r=>r.variant==="PRODUCTION")!.stats.cagr+1e-12).length,oosLosses:oos.filter(y=>y.rows.find(r=>r.variant===x.variant)!.stats.cagr<y.rows.find(r=>r.variant==="PRODUCTION")!.stats.cagr-1e-12).length}));const output={generatedAt:new Date().toISOString(),validity:{researchOnly:true,trueOOS:false,architectureHindsightRemains:true,variantsPredeclared:["PATH25","ACCEL25","BREADTH_STRICT","HV_CASH30","HV_VOL50"],warning:"Sparse economically motivated historical diagnostics; no threshold grid search. Same 2020-2026 architecture-visible sample, so results are not independent True OOS evidence."},rules:{PATH25:"z(momentum)+0.25*z(126D path efficiency ratio)",ACCEL25:"z(momentum)+0.25*z(recent 3M log return minus prior 3M log return)",BREADTH_STRICT:"when universe positive-6M breadth<50%, require score to exceed QQQ by >=5 percentage points; otherwise Production",HV_CASH30:"when QQQ 20D realized vol>=30%, no new monthly Risk-On selection",HV_VOL50:"when QQQ 20D realized vol>=30%, rank by z(momentum)-0.50*z(60D realized vol); otherwise Production",unchanged:"PIT universe, market gate, Top2 architecture, allocation rule, stop, circuit, recovery, execution cost"},full,oos,summary};const dir=path.join(process.cwd(),"data/research/alpha-orthogonal-v2");await fs.mkdir(dir,{recursive:true});await fs.writeFile(path.join(dir,"result.json"),JSON.stringify(output,null,2));console.log(JSON.stringify(output,null,2))}
main().catch(e=>{console.error(e);process.exit(1)});
