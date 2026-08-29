import fs from "node:fs/promises";
import path from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import { initialEngineState, transitionDay } from "../src/lib/strategy/state-machine";
import { nextUsTradingSession } from "../src/lib/trading-calendar";
import { performanceStats } from "../src/lib/backtest";
import type { EquityPoint, MonthlySignal, PricePoint, UniverseMonth } from "../src/lib/types";

type Variant={id:string; volPenalty:number; requirePositive1m:boolean};
const VARIANTS:Variant[]=[
 {id:"PRODUCTION",volPenalty:0,requirePositive1m:false},
 {id:"VOL25",volPenalty:0.25,requirePositive1m:false},
 {id:"VOL50",volPenalty:0.50,requirePositive1m:false},
 {id:"POS1M",volPenalty:0,requirePositive1m:true},
];
const mean=(x:number[])=>x.length?x.reduce((a,b)=>a+b,0)/x.length:0;
const sd=(x:number[])=>{if(x.length<2)return 0;const m=mean(x);return Math.sqrt(x.reduce((s,v)=>s+(v-m)**2,0)/(x.length-1))};
function realizedVol(points:PricePoint[],date:string,days=60){const xs=points.filter(p=>p.date<=date).slice(-(days+1));if(xs.length<days+1)return null;const r=xs.slice(1).map((p,i)=>Math.log(p.close/xs[i].close));return sd(r)*Math.sqrt(252)}
function adjust(base:MonthlySignal,hist:Record<string,PricePoint[]>,v:Variant):MonthlySignal{
 if(v.id==="PRODUCTION"||!base.marketRiskOn)return base;
 let rows=base.candidates.filter(c=>c.eligible&&c.score!=null);
 if(v.requirePositive1m)rows=rows.filter(c=>(c.oneMonth??-Infinity)>0);
 if(rows.length<2)return {...base,selectedSymbols:[],targetWeights:[],allocationMode:"CASH",zGap:null};
 const moms=rows.map(c=>c.score as number),vols=rows.map(c=>realizedVol(hist[c.symbol]??[],base.signalDate)).filter((x):x is number=>x!=null);
 const mm=mean(moms),ms=sd(moms),vm=mean(vols),vs=sd(vols);
 const scored=rows.map(c=>{const rv=realizedVol(hist[c.symbol]??[],base.signalDate);const mz=ms>0?((c.score as number)-mm)/ms:0;const vz=rv!=null&&vs>0?(rv-vm)/vs:0;return{c,adj:mz-v.volPenalty*vz}}).sort((a,b)=>b.adj-a.adj||a.c.symbol.localeCompare(b.c.symbol));
 const pick=scored.slice(0,2).map(x=>x.c);const allRaw=base.candidates.filter(c=>c.eligible&&c.score!=null).map(c=>c.score as number);const disp=sd(allRaw);const zg=disp>0?((pick[0].score as number)-(pick[1].score as number))/disp:0;const conc=zg>=PRODUCTION_STRATEGY.allocation.concentrationZGap;const w1=Math.min(PRODUCTION_STRATEGY.allocation.maxTop1Weight,conc?PRODUCTION_STRATEGY.allocation.concentratedTop1Weight:PRODUCTION_STRATEGY.allocation.baseTop1Weight);
 return {...base,selectedSymbols:pick.map(c=>c.symbol),targetWeights:[w1,1-w1],zGap:zg,allocationMode:conc?"70/30":"50/50"};
}
function sim(hist:Record<string,PricePoint[]>,universe:UniverseMonth[],v:Variant){const qqq=[...(hist.QQQ??[])].sort((a,b)=>a.date.localeCompare(b.date));const dates=qqq.map(p=>p.date),idx=new Map(dates.map((d,i)=>[d,i]));const pm=Object.fromEntries(Object.entries(hist).map(([s,ps])=>[s,new Map(ps.map(p=>[p.date,p]))]));const um=new Map(universe.map(u=>[u.asOf,u]));let state=initialEngineState(PRODUCTION_STRATEGY);const curve:EquityPoint[]=[];for(let i=0;i<dates.length;i++){const date=dates[i];if(date<PRODUCTION_STRATEGY.backtestStart)continue;const next=dates[i+1]??nextUsTradingSession(date),u=um.get(date);let sig=u?buildMonthlySignal({universe:u,histories:hist,qqq,nextSessionDate:next,config:PRODUCTION_STRATEGY}):null;if(sig)sig=adjust(sig,hist,v);const sy=new Set(["QQQ",...state.currentPositions.map(p=>p.symbol),...(state.pendingSignal?.selectedSymbols??[]),...state.nextAction.symbols,...(sig?.selectedSymbols??[])]);const prices=Object.fromEntries([...sy].map(s=>[s,pm[s]?.get(date)]));state=transitionDay(state,{date,prices,qqqHistoryThroughClose:qqq.slice(0,(idx.get(date)??i)+1),monthlySignal:sig,nextSessionDate:next},PRODUCTION_STRATEGY);curve.push({date,equity:state.currentEquity,drawdown:state.drawdown})}return{variant:v.id,curve}}
function slice(c:EquityPoint[],s:string,e:string){const x=c.filter(p=>p.date>=s&&p.date<=e);if(!x.length)return[];const b=x[0].equity;return x.map(p=>({...p,equity:p.equity/b}))}
async function main(){const market=JSON.parse(await fs.readFile(path.join(process.cwd(),"public/data/market-data.json"),"utf8")) as {histories:Record<string,PricePoint[]>};const uf=JSON.parse(await fs.readFile(path.join(process.cwd(),"data/universe-history.json"),"utf8")) as {history:UniverseMonth[]};const universe=[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf));const sims=VARIANTS.map(v=>sim(market.histories,universe,v));const years=[2022,2023,2024,2025,2026];const full=sims.map(s=>({variant:s.variant,stats:performanceStats(s.curve)}));const oos=years.map(y=>({year:y,rows:sims.map(s=>({variant:s.variant,stats:performanceStats(slice(s.curve,`${y}-01-01`,y===2026?"2026-08-25":`${y}-12-31`))}))}));const output={generatedAt:new Date().toISOString(),validity:{researchOnly:true,trueOOS:false,architectureHindsightRemains:true,variantsPredeclared:["VOL25","VOL50","POS1M"],warning:"Historical comparative diagnostic. The variants are deliberately sparse and economically motivated; no parameter grid search is used."},rules:{VOL25:"cross-sectional z(momentum) - 0.25*z(60D realized vol)",VOL50:"cross-sectional z(momentum) - 0.50*z(60D realized vol)",POS1M:"Production ranking but candidate must also have positive 1-month return",unchanged:"dynamic universe, QQQ gate, Top2, allocation architecture, stop, circuit, recovery, execution cost"},full,oos};const dir=path.join(process.cwd(),"data/research/orthogonal-signal-quality");await fs.mkdir(dir,{recursive:true});await fs.writeFile(path.join(dir,"result.json"),JSON.stringify(output,null,2));console.log(JSON.stringify(output,null,2))}
main().catch(e=>{console.error(e);process.exit(1)});
