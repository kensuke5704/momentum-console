import fs from 'node:fs/promises';
import path from 'node:path';
import {PRODUCTION_STRATEGY as P} from '../src/lib/config';
import {buildMonthlySignal} from '../src/lib/strategy/momentum';
import {initialEngineState,transitionDay} from '../src/lib/strategy/state-machine';
import {performanceStats} from '../src/lib/backtest';
import {nextUsTradingSession} from '../src/lib/trading-calendar';
import type {EquityPoint,PricePoint,StrategyConfig,UniverseMonth} from '../src/lib/types';

type V={id:string;top1:number;bridge:number;k:number};
const VS:V[]=[
 {id:'PROD',top1:-1,bridge:0,k:99},
 {id:'P_B50_K1',top1:-1,bridge:.5,k:1},
 {id:'P_B50_K3',top1:-1,bridge:.5,k:3},
 {id:'P_B50_K5',top1:-1,bridge:.5,k:5},
 {id:'F60',top1:.6,bridge:0,k:99},
 {id:'F60_B50_K1',top1:.6,bridge:.5,k:1},
 {id:'F60_B50_K3',top1:.6,bridge:.5,k:3},
 {id:'F60_B50_K5',top1:.6,bridge:.5,k:5},
 {id:'W70',top1:.7,bridge:0,k:99},
 {id:'W70_B50_K1',top1:.7,bridge:.5,k:1},
 {id:'W70_B50_K3',top1:.7,bridge:.5,k:3},
 {id:'W70_B50_K5',top1:.7,bridge:.5,k:5},
];
function cfg(v:V):StrategyConfig{return v.top1<0?P:{...P,allocation:{...P.allocation,baseTop1Weight:v.top1,concentratedTop1Weight:v.top1,maxTop1Weight:v.top1}} as StrategyConfig}
function slice(c:EquityPoint[],s:string,e:string){const xs=c.filter(p=>p.date>=s&&p.date<=e);if(xs.length<2)return[];const prev=[...c].reverse().find(p=>p.date<s),z=prev?[prev,...xs]:xs,b=z[0].equity;return z.map(p=>({...p,equity:p.equity/b}))}
function sim(hist:Record<string,PricePoint[]>,universe:UniverseMonth[],v:V){
 const c=cfg(v),q=[...hist.QQQ].sort((a,b)=>a.date.localeCompare(b.date)),dates=q.map(x=>x.date),di=new Map(dates.map((d,i)=>[d,i])),pm=Object.fromEntries(Object.entries(hist).map(([s,p])=>[s,new Map(p.map(x=>[x.date,x]))])),um=new Map(universe.map(x=>[x.asOf,x]));
 let st=initialEngineState(c),prevBase=1,prevQClose:number|null=null,equity=1,peak=1,bridgeOn=false,enterNext=false,exitNext=false,trades=0,bridgeDays=0;const curve:EquityPoint[]=[],tradeLog:any[]=[];
 for(let i=0;i<dates.length;i++){
  const date=dates[i];if(date<c.backtestStart){prevQClose=q[i].close;continue}
  const next=dates[i+1]??nextUsTradingSession(date),u=um.get(date);let sig=u?buildMonthlySignal({universe:u,histories:hist,qqq:q,nextSessionDate:next,config:c}):null;
  const sy=new Set(['QQQ',...st.currentPositions.map(p=>p.symbol),...(st.pendingSignal?.selectedSymbols??[]),...st.nextAction.symbols,...(sig?.selectedSymbols??[])]),prices=Object.fromEntries([...sy].map(s=>[s,pm[s]?.get(date)]));
  const before=structuredClone(st),beforeEq=st.currentEquity,wasInvested=before.currentPositions.length>0;
  st=transitionDay(st,{date,prices,qqqHistoryThroughClose:q.slice(0,(di.get(date)??i)+1),monthlySignal:sig,nextSessionDate:next},c);
  const nowInvested=st.currentPositions.length>0,enteredTop2=!wasInvested&&nowInvested,qr=pm.QQQ?.get(date),qo=qr?.open??qr?.close,qc=qr?.close,bf=prevBase>0?st.currentEquity/prevBase:1;
  if(v.bridge===0){equity*=bf;}
  else {
   if(exitNext&&bridgeOn&&qo&&prevQClose){const w=v.bridge;equity*=((1-w)+w*(qo/prevQClose)*(1-c.execution.transactionCost));bridgeOn=false;exitNext=false;trades++;tradeLog.push({date,type:'BRIDGE_EXIT_OPEN',reason:'RISK_OFF',weight:w});}
   if(enterNext&&!bridgeOn&&qo&&qc&&!nowInvested){const w=v.bridge;equity*=((1-w)+w*(1-c.execution.transactionCost)*(qc/qo));bridgeOn=true;enterNext=false;trades++;bridgeDays++;tradeLog.push({date,type:'BRIDGE_ENTRY_OPEN',weight:w,k:v.k});}
   else if(bridgeOn&&qc&&prevQClose){const w=v.bridge;equity*=((1-w)+w*(qc/prevQClose));bridgeDays++;}
   else if(wasInvested||nowInvested){equity*=bf;}
   if(enteredTop2&&bridgeOn&&qo&&qc){const w=v.bridge,bridgeDay=((1-w)+w*(qc/(prevQClose??qc)));if(bridgeDay>0)equity/=bridgeDay;equity*=((1-w)+w*(qo/(prevQClose??qo))*(1-c.execution.transactionCost));const top2Day=beforeEq>0?st.currentEquity/beforeEq:1;equity*=top2Day;bridgeOn=false;exitNext=false;enterNext=false;trades++;tradeLog.push({date,type:'BRIDGE_EXIT_OPEN',reason:'TOP2_REENTRY',weight:w});}
   if(bridgeOn&&sig&&sig.marketRiskOn===false)exitNext=true;
   if(!bridgeOn&&!enterNext&&!nowInvested&&!exitNext&&st.state==='WAITING_RECOVERY'&&st.marketRiskOn&&st.recoveryConsecutiveDays===v.k)enterNext=true;
   if(nowInvested){enterNext=false;exitNext=false;}
  }
  peak=Math.max(peak,equity);curve.push({date,equity,drawdown:equity/peak-1});prevBase=st.currentEquity;prevQClose=qc??prevQClose;
 }
 return{curve,trades,bridgeDays,tradeLog};
}
async function main(){
 const market=JSON.parse(await fs.readFile(path.join(process.cwd(),'public/data/market-data.json'),'utf8')) as {histories:Record<string,PricePoint[]>},uf=JSON.parse(await fs.readFile(path.join(process.cwd(),'data/universe-history.json'),'utf8')) as {history:UniverseMonth[]},u=[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf)),runs=new Map<string,ReturnType<typeof sim>>();
 for(const v of VS)runs.set(v.id,sim(market.histories,u,v));
 const full=VS.map(v=>{const r=runs.get(v.id)!;return{id:v.id,stats:performanceStats(r.curve),trades:r.trades,bridgeDays:r.bridgeDays}}),years=[2020,2021,2022,2023,2024,2025,2026],annual=years.map(y=>({year:y,...Object.fromEntries(VS.map(v=>[v.id,performanceStats(slice(runs.get(v.id)!.curve,`${y}-01-01`,y===2026?'2026-08-25':`${y}-12-31`))]))})),confirmation=VS.map(v=>({id:v.id,stats:performanceStats(slice(runs.get(v.id)!.curve,'2023-01-01','2026-08-25'))}));
 const out={generatedAt:new Date().toISOString(),validity:{researchOnly:true,trueOOS:false,noLeverage:true,warning:'Exact bridge lifecycle relative to the authoritative Production/fixed-allocation state machine: bridge entry is next open after K qualifying recovery closes; bridge exits next open after monthly RiskOff or at the same open as Top2 re-entry. 10bp each bridge side. Bridge equity does not feed back into Stop/Circuit state, intentionally preserving Production risk logic.'},full,annual,confirmation,tradeLogs:Object.fromEntries(VS.filter(v=>v.bridge>0).map(v=>[v.id,runs.get(v.id)!.tradeLog]))};
 const d=path.join(process.cwd(),'data/research/recovery-bridge-exact-lifecycle');await fs.mkdir(d,{recursive:true});await fs.writeFile(path.join(d,'result.json'),JSON.stringify(out,null,2));console.log(JSON.stringify({...out,tradeLogs:undefined},null,2));
}
main().catch(e=>{console.error(e);process.exit(1)});