import fs from 'node:fs/promises';
import path from 'node:path';
import {PRODUCTION_STRATEGY as C} from '../src/lib/config';
import {buildMonthlySignal} from '../src/lib/strategy/momentum';
import {initialEngineState,transitionDay} from '../src/lib/strategy/state-machine';
import {performanceStats} from '../src/lib/backtest';
import {nextUsTradingSession} from '../src/lib/trading-calendar';
import type {EquityPoint,PricePoint,UniverseMonth} from '../src/lib/types';

type Mode='BASE'|'BR50_STICKY'|'BR100_STICKY'|'BR50_ACTIVE'|'BR100_ACTIVE';
type Shadow={mode:Mode,equity:number,peak:number,curve:EquityPoint[],bridgeWeight:number,bridgeOn:boolean,scheduledEntry:boolean,scheduledExit:boolean,trades:number,bridgeDays:number};
const MODES:Mode[]=['BASE','BR50_STICKY','BR100_STICKY','BR50_ACTIVE','BR100_ACTIVE'];
const weight=(m:Mode)=>m.includes('100')?1:m.includes('50')?.5:0;
const activeOnly=(m:Mode)=>m.includes('ACTIVE');
function mark(s:Shadow,date:string){s.peak=Math.max(s.peak,s.equity);s.curve.push({date,equity:s.equity,drawdown:s.equity/s.peak-1});}
function baseFactor(prevEq:number,curEq:number){return prevEq>0?curEq/prevEq:1}
async function main(){
 const market=JSON.parse(await fs.readFile(path.join(process.cwd(),'public/data/market-data.json'),'utf8')) as {histories:Record<string,PricePoint[]>};
 const uf=JSON.parse(await fs.readFile(path.join(process.cwd(),'data/universe-history.json'),'utf8')) as {history:UniverseMonth[]};
 const h=market.histories,q=[...h.QQQ].sort((a,b)=>a.date.localeCompare(b.date)),dates=q.map(x=>x.date),di=new Map(dates.map((d,i)=>[d,i])),pm=Object.fromEntries(Object.entries(h).map(([s,p])=>[s,new Map(p.map(x=>[x.date,x]))])),um=new Map([...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf)).map(x=>[x.asOf,x]));
 let st=initialEngineState(C);let prevBaselineEq=1;let prevQClose:number|null=null;
 const ss=new Map<Mode,Shadow>(MODES.map(m=>[m,{mode:m,equity:1,peak:1,curve:[],bridgeWeight:weight(m),bridgeOn:false,scheduledEntry:false,scheduledExit:false,trades:0,bridgeDays:0}]));
 const episodes:any[]=[];let ep:any=null;
 for(let i=0;i<dates.length;i++){
   const d=dates[i];if(d<C.backtestStart){prevQClose=q[i].close;continue}
   const n=dates[i+1]??nextUsTradingSession(d),u=um.get(d),sig=u?buildMonthlySignal({universe:u,histories:h,qqq:q,nextSessionDate:n,config:C}):null;
   const sy=new Set(['QQQ',...st.currentPositions.map(p=>p.symbol),...(st.pendingSignal?.selectedSymbols??[]),...st.nextAction.symbols,...(sig?.selectedSymbols??[])]),prices=Object.fromEntries([...sy].map(s=>[s,pm[s]?.get(d)]));
   const before=structuredClone(st),beforeEq=st.currentEquity;
   st=transitionDay(st,{date:d,prices,qqqHistoryThroughClose:q.slice(0,(di.get(d)??i)+1),monthlySignal:sig,nextSessionDate:n},C);
   const qrow=pm.QQQ?.get(d),qo=qrow?.open??qrow?.close,qc=qrow?.close;
   const baselineInvestedAfter=st.currentPositions.length>0;
   const baselineWasInvested=before.currentPositions.length>0;
   const enteredTop2=!baselineWasInvested&&baselineInvestedAfter;
   const exitedTop2=baselineWasInvested&&!baselineInvestedAfter;
   if(exitedTop2&&!ep)ep={exitDate:d,reason:before.nextAction.reason,startRecovery:null,endDate:null,qqqOpen:qo,qqqExitOpen:null};
   if(ep&&st.state==='WAITING_RECOVERY'&&st.recoveryConsecutiveDays>0&&ep.startRecovery===null)ep.startRecovery=d;
   if(ep&&enteredTop2){ep.endDate=d;ep.qqqExitOpen=qo;episodes.push(ep);ep=null}
   for(const m of MODES){
     const s=ss.get(m)!;
     if(m==='BASE'){s.equity*=baseFactor(prevBaselineEq,st.currentEquity);mark(s,d);continue}
     // Execute scheduled bridge trades at today's open before close marking.
     if(s.scheduledExit&&s.bridgeOn&&qo&&prevQClose){
       const w=s.bridgeWeight,ret=qo/prevQClose;
       s.equity*=((1-w)+w*ret*(1-C.execution.transactionCost));s.bridgeOn=false;s.scheduledExit=false;s.trades++;
     }
     if(s.scheduledEntry&&!s.bridgeOn&&qo&&qc){
       const w=s.bridgeWeight;s.equity*=((1-w)+w*(1-C.execution.transactionCost)*(qc/qo));s.bridgeOn=true;s.scheduledEntry=false;s.trades++;s.bridgeDays++;
     } else if(s.bridgeOn&&qc&&prevQClose){
       const w=s.bridgeWeight;s.equity*=((1-w)+w*(qc/prevQClose));s.bridgeDays++;
     } else if(baselineWasInvested||baselineInvestedAfter){
       s.equity*=baseFactor(prevBaselineEq,st.currentEquity);
     }
     // Top2 entry supersedes bridge at same open. The bridge liquidation open move must be applied first, then baseline top2 day's return.
     if(enteredTop2){
       if(s.bridgeOn&&qo&&qc){
         // Undo today's close marking for bridge and replace with prev-close->open bridge + top2 open->close factor.
         const w=s.bridgeWeight,dayBridge=((1-w)+w*(qc/(prevQClose??qc)));
         if(dayBridge>0)s.equity/=dayBridge;
         s.equity*=((1-w)+w*(qo/(prevQClose??qo))*(1-C.execution.transactionCost));
         const top2Day=beforeEq>0?st.currentEquity/beforeEq:1;s.equity*=top2Day;s.bridgeOn=false;s.trades++;
       }
       s.scheduledEntry=false;s.scheduledExit=false;
     }
     // Close decisions for next open.
     if(!baselineInvestedAfter&&st.state==='WAITING_RECOVERY'&&st.recoveryConsecutiveDays===1&&!s.bridgeOn&&!s.scheduledEntry)s.scheduledEntry=true;
     if(activeOnly(m)&&s.bridgeOn&&st.state==='WAITING_RECOVERY'&&st.recoveryConsecutiveDays===0)s.scheduledExit=true;
     if(!st.marketRiskOn&&s.bridgeOn)s.scheduledExit=true;
     mark(s,d);
   }
   prevBaselineEq=st.currentEquity;prevQClose=qc??prevQClose;
 }
 const full=MODES.map(m=>{const s=ss.get(m)!;return{mode:m,stats:performanceStats(s.curve),trades:s.trades,bridgeDays:s.bridgeDays}});
 const years=[2020,2021,2022,2023,2024,2025,2026];
 function slice(c:EquityPoint[],y:number){const xs=c.filter(p=>p.date>=`${y}-01-01`&&p.date<=(y===2026?'2026-08-25':`${y}-12-31`));if(xs.length<2)return[];const b=xs[0].equity;return xs.map(p=>({...p,equity:p.equity/b}))}
 const annual=years.map(y=>({year:y,...Object.fromEntries(MODES.map(m=>[m,performanceStats(slice(ss.get(m)!.curve,y))]))}));
 const out={generatedAt:new Date().toISOString(),validity:{researchOnly:true,trueOOS:false,noLeverage:true,warning:'Shadow-return screening. Production state machine and triggers are unchanged. QQQ bridge is economic overlay only; entry is next open after first positive recovery close. STICKY holds until Top2 re-entry or RiskOff; ACTIVE exits next open if recovery counter resets. Includes 10bp bridge entry/exit cost. Requires exact-engine implementation before any adoption.'},full,annual,episodes};
 const dir=path.join(process.cwd(),'data/research/recovery-qqq-bridge-screen');await fs.mkdir(dir,{recursive:true});await fs.writeFile(path.join(dir,'result.json'),JSON.stringify(out,null,2));console.log(JSON.stringify(out,null,2));
}
main().catch(e=>{console.error(e);process.exit(1)});