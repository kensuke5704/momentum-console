import fs from "node:fs/promises";
import path from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import { initialEngineState, transitionDay } from "../src/lib/strategy/state-machine";
import { nextUsTradingSession } from "../src/lib/trading-calendar";
import { performanceStats } from "../src/lib/backtest";
import type { EquityPoint, PricePoint, UniverseMonth } from "../src/lib/types";

type Variant={id:string; exposure:(zGap:number|null)=>number};
const VARIANTS:Variant[]=[
 {id:"PRODUCTION",exposure:()=>1},
 {id:"WEAK75",exposure:z=>z!=null&&z<0.25?0.75:1},
 {id:"STRONG125",exposure:z=>z!=null&&z>=0.50?1.25:1},
 {id:"TIERED",exposure:z=>z==null?1:z<0.25?0.75:z>=0.50?1.25:1},
];

function baseSim(hist:Record<string,PricePoint[]>,universe:UniverseMonth[]){
 const qqq=[...(hist.QQQ??[])].sort((a,b)=>a.date.localeCompare(b.date));
 const dates=qqq.map(p=>p.date),idx=new Map(dates.map((d,i)=>[d,i]));
 const pm=Object.fromEntries(Object.entries(hist).map(([s,ps])=>[s,new Map(ps.map(p=>[p.date,p]))]));
 const um=new Map(universe.map(u=>[u.asOf,u]));
 let state=initialEngineState(PRODUCTION_STRATEGY); const curve:EquityPoint[]=[]; const zgapByDate=new Map<string,number|null>(); let activeZGap:number|null=null;
 for(let i=0;i<dates.length;i++){
  const date=dates[i]; if(date<PRODUCTION_STRATEGY.backtestStart) continue;
  const next=dates[i+1]??nextUsTradingSession(date),u=um.get(date);
  const sig=u?buildMonthlySignal({universe:u,histories:hist,qqq,nextSessionDate:next,config:PRODUCTION_STRATEGY}):null;
  if(sig&&sig.marketRiskOn&&sig.selectedSymbols.length===2) activeZGap=sig.zGap; else if(sig&&!sig.marketRiskOn) activeZGap=null;
  zgapByDate.set(date,activeZGap);
  const sy=new Set(["QQQ",...state.currentPositions.map(p=>p.symbol),...(state.pendingSignal?.selectedSymbols??[]),...state.nextAction.symbols,...(sig?.selectedSymbols??[])]);
  const prices=Object.fromEntries([...sy].map(s=>[s,pm[s]?.get(date)]));
  state=transitionDay(state,{date,prices,qqqHistoryThroughClose:qqq.slice(0,(idx.get(date)??i)+1),monthlySignal:sig,nextSessionDate:next},PRODUCTION_STRATEGY);
  curve.push({date,equity:state.currentEquity,drawdown:state.drawdown});
 }
 return {curve,zgapByDate};
}

function transform(base:EquityPoint[],zg:Map<string,number|null>,v:Variant){
 if(!base.length)return[]; let e=1,peak=1; const out:EquityPoint[]=[];
 for(let i=0;i<base.length;i++){
  if(i>0){const r=base[i].equity/base[i-1].equity-1; const x=v.exposure(zg.get(base[i-1].date)??null); e*=Math.max(0,1+x*r);}
  peak=Math.max(peak,e); out.push({date:base[i].date,equity:e,drawdown:e/peak-1});
 }
 return out;
}
function slice(c:EquityPoint[],s:string,e:string){const x=c.filter(p=>p.date>=s&&p.date<=e);if(!x.length)return[];const b=x[0].equity;return x.map(p=>({...p,equity:p.equity/b}))}

async function main(){
 const market=JSON.parse(await fs.readFile(path.join(process.cwd(),"public/data/market-data.json"),"utf8")) as {histories:Record<string,PricePoint[]>};
 const uf=JSON.parse(await fs.readFile(path.join(process.cwd(),"data/universe-history.json"),"utf8")) as {history:UniverseMonth[]};
 const universe=[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf)); const base=baseSim(market.histories,universe);
 const sims=VARIANTS.map(v=>({variant:v.id,curve:transform(base.curve,base.zgapByDate,v)}));
 const years=[2022,2023,2024,2025,2026];
 const full=sims.map(s=>({variant:s.variant,stats:performanceStats(s.curve)}));
 const oos=years.map(y=>({year:y,rows:sims.map(s=>({variant:s.variant,stats:performanceStats(slice(s.curve,`${y}-01-01`,y===2026?"2026-08-25":`${y}-12-31`))}))}));
 const output={generatedAt:new Date().toISOString(),validity:{researchOnly:true,trueOOS:false,stateMachineRerun:false,descriptiveCounterfactual:true,architectureHindsightRemains:true,variantsPredeclared:["WEAK75","STRONG125","TIERED"],warning:"Screening only. Daily Production returns are scaled by prior known monthly zGap exposure; stops/circuit, financing cost, taxes and execution are NOT rerun. Any promising variant requires a full state-machine rerun before consideration."},rules:{WEAK75:"75% exposure when zGap<0.25; otherwise 100%",STRONG125:"125% exposure when zGap>=0.50; otherwise 100%",TIERED:"75% when zGap<0.25, 100% when 0.25<=zGap<0.50, 125% when zGap>=0.50",timing:"exposure uses prior-known monthly signal zGap for subsequent daily return"},full,oos};
 const dir=path.join(process.cwd(),"data/research/dynamic-exposure-screen"); await fs.mkdir(dir,{recursive:true}); await fs.writeFile(path.join(dir,"result.json"),JSON.stringify(output,null,2)); console.log(JSON.stringify(output,null,2));
}
main().catch(e=>{console.error(e);process.exit(1)});
