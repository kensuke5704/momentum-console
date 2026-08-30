import fs from 'node:fs/promises';
import path from 'node:path';
import {PRODUCTION_STRATEGY} from '../src/lib/config';
import {buildMonthlySignal} from '../src/lib/strategy/momentum';
import {initialEngineState,transitionDay} from '../src/lib/strategy/state-machine';
import {performanceStats} from '../src/lib/backtest';
import {nextUsTradingSession} from '../src/lib/trading-calendar';
import type {EquityPoint,MonthlySignal,PricePoint,UniverseMonth,StrategyConfig} from '../src/lib/types';

type BaseId='PROD'|'W25';
type Variant={id:string;base:BaseId;cons:number|null};
const VARS:Variant[]=[
 {id:'PROD_BASE',base:'PROD',cons:null},
 {id:'PROD_C75',base:'PROD',cons:.75},
 {id:'PROD_C80',base:'PROD',cons:.80},
 {id:'W25_BASE',base:'W25',cons:null},
 {id:'W25_C75',base:'W25',cons:.75},
 {id:'W25_C80',base:'W25',cons:.80},
];
function cfg(base:BaseId):StrategyConfig{
 if(base==='PROD')return {...PRODUCTION_STRATEGY} as StrategyConfig;
 return {...PRODUCTION_STRATEGY,momentum:{...PRODUCTION_STRATEGY.momentum,oneMonth:0,threeMonth:.25,sixMonth:.75},allocation:{...PRODUCTION_STRATEGY.allocation,baseTop1Weight:.6,concentratedTop1Weight:.7}} as StrategyConfig;
}
function isConsensus(sig:MonthlySignal){const e=sig.candidates.filter(c=>c.eligible&&c.threeMonth!==null&&c.sixMonth!==null);if(e.length<2)return false;const r3=[...e].sort((a,b)=>(b.threeMonth??-9)-(a.threeMonth??-9)||a.symbol.localeCompare(b.symbol))[0]?.symbol;const r6=[...e].sort((a,b)=>(b.sixMonth??-9)-(a.sixMonth??-9)||a.symbol.localeCompare(b.symbol))[0]?.symbol;return !!r3&&r3===r6&&sig.selectedSymbols[0]===r3;}
function sim(h:Record<string,PricePoint[]>,u:UniverseMonth[],v:Variant,disableYear:number|null=null){const c=cfg(v.base),q=[...h.QQQ].sort((a,b)=>a.date.localeCompare(b.date)),ds=q.map(x=>x.date),ix=new Map(ds.map((d,i)=>[d,i])),pm=Object.fromEntries(Object.entries(h).map(([s,p])=>[s,new Map(p.map(x=>[x.date,x]))])),um=new Map(u.map(x=>[x.asOf,x]));let st=initialEngineState(c),hits=0;const hitMonths:string[]=[];const z:EquityPoint[]=[];for(let i=0;i<ds.length;i++){const d=ds[i];if(d<c.backtestStart)continue;const n=ds[i+1]??nextUsTradingSession(d),uu=um.get(d);let sg=uu?buildMonthlySignal({universe:uu,histories:h,qqq:q,nextSessionDate:n,config:c}):null;if(sg&&sg.selectedSymbols.length===2){let top=sg.zGap!==null&&sg.zGap>=c.allocation.concentrationZGap?c.allocation.concentratedTop1Weight:c.allocation.baseTop1Weight;const hit=v.cons!==null&&isConsensus(sg)&&Number(d.slice(0,4))!==disableYear;if(hit){top=v.cons!;hits++;hitMonths.push(d)}sg.targetWeights=[top,1-top];}const ss=new Set(['QQQ',...st.currentPositions.map(p=>p.symbol),...(st.pendingSignal?.selectedSymbols??[]),...st.nextAction.symbols,...(sg?.selectedSymbols??[])]),pr=Object.fromEntries([...ss].map(s=>[s,pm[s]?.get(d)]));st=transitionDay(st,{date:d,prices:pr,qqqHistoryThroughClose:q.slice(0,(ix.get(d)??i)+1),monthlySignal:sg,nextSessionDate:n},c);z.push({date:d,equity:st.currentEquity,drawdown:st.drawdown})}return{curve:z,hits,hitMonths}}
function sl(c:EquityPoint[],s:string,e:string){const x=c.filter(p=>p.date>=s&&p.date<=e);if(x.length<2)return[];const b=x[0].equity;return x.map(p=>({...p,equity:p.equity/b}))}
async function main(){const mk=JSON.parse(await fs.readFile(path.join(process.cwd(),'public/data/market-data.json'),'utf8')) as {histories:Record<string,PricePoint[]>},uf=JSON.parse(await fs.readFile(path.join(process.cwd(),'data/universe-history.json'),'utf8')) as {history:UniverseMonth[]},u=[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf));const runs=new Map<string,ReturnType<typeof sim>>();for(const v of VARS)runs.set(v.id,sim(mk.histories,u,v));const full=VARS.map(v=>({id:v.id,base:v.base,cons:v.cons,...performanceStats(runs.get(v.id)!.curve),hits:runs.get(v.id)!.hits}));const years=[2020,2021,2022,2023,2024,2025,2026];const annual=years.map(y=>({year:y,...Object.fromEntries(VARS.map(v=>[v.id,performanceStats(sl(runs.get(v.id)!.curve,`${y}-01-01`,y===2026?'2026-08-25':`${y}-12-31`))]))}));const confirmation=VARS.map(v=>({id:v.id,stats:performanceStats(sl(runs.get(v.id)!.curve,'2023-01-01','2026-08-25'))}));const leaveYear:any[]=[];for(const v of VARS.filter(x=>x.cons!==null)){const base=full.find(x=>x.id===`${v.base}_BASE`)!;const candidate=full.find(x=>x.id===v.id)!;for(const y of years){const r=sim(mk.histories,u,v,y);const st=performanceStats(r.curve);leaveYear.push({variant:v.id,disabledYear:y,cagr:st.cagr,fullDelta:candidate.cagr-base.cagr,deltaAfterDisable:st.cagr-base.cagr,lossOfEdge:candidate.cagr-st.cagr});}}
 const out={generatedAt:new Date().toISOString(),validity:{researchOnly:true,noLeverage:true,trueOOS:false,pit:true,nextOpen:true,warning:'Neighborhood/transfer validation only. Consensus definition fixed: selected Top1 must independently rank #1 on both 3M and 6M. Only 75/25 and 80/20 conditional weights tested.'},full,annual,confirmation,leaveYear,hitMonths:Object.fromEntries(VARS.filter(v=>v.cons!==null).map(v=>[v.id,runs.get(v.id)!.hitMonths]))};const d=path.join(process.cwd(),'data/research/consensus-robustness');await fs.mkdir(d,{recursive:true});await fs.writeFile(path.join(d,'result.json'),JSON.stringify(out,null,2));console.log(JSON.stringify(out,null,2));}
main().catch(e=>{console.error(e);process.exit(1)});