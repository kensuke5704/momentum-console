import {readFile} from "node:fs/promises";
import {resolve} from "node:path";
import {performanceStats} from "../src/lib/backtest";
import {PRODUCTION_STRATEGY} from "../src/lib/config";
import {buildMonthlySignal} from "../src/lib/strategy/momentum";
import {initialEngineState,transitionDay} from "../src/lib/strategy/state-machine";
import {nextUsTradingSession} from "../src/lib/trading-calendar";
import {fetchYahooHistory} from "../src/lib/yahoo";
import type {EquityPoint,PricePoint,UniverseMonth} from "../src/lib/types";

type MF={histories:Record<string,PricePoint[]>}; type UF={history:UniverseMonth[]};
type Cot={date:string;net:number}; type OuterState="NORMAL"|"YELLOW"|"DEEP";
type FixedTarget={symbols:string[];weights:number[]};
type FixedSnap={date:string;equity:number;target:FixedTarget};
type OuterRow={date:string;state:OuterState};
type Target={state:OuterState;fixed:FixedTarget;f:number;gold:number;cash:number};
const START="2020-01-01", END="2026-08-25", COST=.001;
const N={f:.85,gold:.15,cash:0},Y={f:.555,gold:.225,cash:.22},D={f:.255,gold:.30,cash:.445};
const mean=(x:number[])=>x.reduce((a,b)=>a+b,0)/(x.length||1);
function latest(us:UniverseMonth[],d:string){let x:UniverseMonth|null=null;for(const u of us){if(u.asOf<=d)x=u;else break}return x}
function fixedSnaps(h:Record<string,PricePoint[]>,us:UniverseMonth[]){
 const q=[...(h.QQQ??[])].sort((a,b)=>a.date.localeCompare(b.date)), dates=q.map(x=>x.date), idx=new Map(dates.map((d,i)=>[d,i]));
 const maps=Object.fromEntries(Object.entries(h).map(([s,a])=>[s,new Map(a.map(x=>[x.date,x]))]));
 const ub=new Map(us.map(u=>[u.asOf,u])); let state=initialEngineState(PRODUCTION_STRATEGY); const out:FixedSnap[]=[];
 for(let i=0;i<dates.length;i++){const date=dates[i];if(date<START||date>END)continue;const next=dates[i+1]??nextUsTradingSession(date),u=ub.get(date);
  const sig=u?buildMonthlySignal({universe:u,histories:h,qqq:q,nextSessionDate:next,config:PRODUCTION_STRATEGY}):null;
  const syms=new Set(["QQQ",...state.currentPositions.map(p=>p.symbol),...(state.pendingSignal?.selectedSymbols??[]),...state.nextAction.symbols,...(sig?.selectedSymbols??[])]);
  const prices=Object.fromEntries([...syms].map(s=>[s,maps[s]?.get(date)]));
  state=transitionDay(state,{date,prices,qqqHistoryThroughClose:q.slice(0,(idx.get(date)??i)+1),monthlySignal:sig,nextSessionDate:next},PRODUCTION_STRATEGY);
  let target:FixedTarget;
  if(state.nextAction.executionDate===next&&(state.nextAction.type==="BUY_NEXT_OPEN"||state.nextAction.type==="MONTH_END_REBALANCE_NEXT_OPEN")) target={symbols:[...state.nextAction.symbols],weights:[...state.nextAction.targetWeights]};
  else if(state.nextAction.executionDate===next&&state.nextAction.type==="SELL_ALL_NEXT_OPEN") target={symbols:[],weights:[]};
  else target={symbols:state.currentPositions.map(p=>p.symbol),weights:state.currentPositions.map(p=>p.targetWeight)};
  out.push({date,equity:state.currentEquity,target});
 }
 return out;
}
function runG(h:Record<string,PricePoint[]>,us:UniverseMonth[]){
 const q=[...(h.QQQ??[])].sort((a,b)=>a.date.localeCompare(b.date)),dates=q.map(x=>x.date).filter(d=>d>=START&&d<=END),rows=Object.fromEntries(Object.entries(h).map(([s,a])=>[s,[...a].sort((x,y)=>x.date.localeCompare(y.date))])),idx=Object.fromEntries(Object.entries(rows).map(([s,a])=>[s,new Map((a as PricePoint[]).map((x,i)=>[x.date,i]))])),maps=Object.fromEntries(Object.entries(rows).map(([s,a])=>[s,new Map((a as PricePoint[]).map(x=>[x.date,x]))]));
 let cash=1,pos:Array<{s:string;sh:number;e:number}>=[],pin:{d:string;ss:string[]}|null=null,pout:string|null=null,hold=0,peak=1;const curve:EquityPoint[]=[];const eq=(d:string,f:"open"|"close")=>cash+pos.reduce((z,x)=>z+x.sh*((maps[x.s] as Map<string,PricePoint>).get(d)?.[f]??x.e),0);
 for(let di=0;di<dates.length;di++){const d=dates[di],nd=dates[di+1]??null;if(pout===d&&pos.length){cash=pos.reduce((z,x)=>{const r=(maps[x.s] as Map<string,PricePoint>).get(d);return z+x.sh*(r?.open??r?.close??x.e)},0)*.999;pos=[];pout=null;hold=0;peak=cash}if(pin?.d===d&&!pos.length){const os=pin.ss.map(s=>(maps[s] as Map<string,PricePoint>).get(d)?.open);if(os.length===5&&os.every(x=>x&&x>0)){const per=cash/5;pos=pin.ss.map((s,i)=>({s,sh:per*.999/(os[i] as number),e:os[i] as number}));cash=0;peak=eq(d,"open");hold=0}pin=null}const e=eq(d,"close");peak=Math.max(peak,e);const dd=e/peak-1;curve.push({date:d,equity:e,drawdown:dd});if(pos.length&&!pout&&nd){hold++;const stop=pos.some(x=>((maps[x.s] as Map<string,PricePoint>).get(d)?.close??Infinity)<=x.e*.88);if(stop||dd<=-.15||hold>=20)pout=nd}if(!pos.length&&!pin&&nd){const qi=(idx.QQQ as Map<string,number>).get(d);if(qi==null||qi<199)continue;const qr=rows.QQQ as PricePoint[];if(qr[qi].close<=mean(qr.slice(qi-199,qi+1).map(x=>x.close)))continue;const u=latest(us,d);if(!u)continue;const ca:Array<{s:string;v:number}>=[];for(const m of u.symbols){const s=m.symbol,i=(idx[s] as Map<string,number>|undefined)?.get(d),r=rows[s] as PricePoint[]|undefined;if(i==null||!r||i<99||i<20)continue;const close=r[i].close;if(close<=mean(r.slice(i-99,i+1).map(x=>x.close)))continue;const hi=Math.max(...r.slice(i-20,i).map(x=>x.close));if(close>hi)ca.push({s,v:close/hi-1})}ca.sort((a,b)=>b.v-a.v||a.s.localeCompare(b.s));if(ca.length>=5)pin={d:nd,ss:ca.slice(0,5).map(x=>x.s)}}}
 return curve;
}
function rm(c:EquityPoint[]){const m=new Map<string,number>();for(let i=1;i<c.length;i++)m.set(c[i].date,c[i].equity/c[i-1].equity-1);return m}
function core(f:EquityPoint[],g:EquityPoint[]){const fm=rm(f),gm=rm(g),dates=f.slice(1).map(x=>x.date).filter(d=>gm.has(d));let e=1,p=1;const o:EquityPoint[]=[{date:f[0].date,equity:1,drawdown:0}];for(const d of dates){e*=1+.85*(fm.get(d)??0)+.15*(gm.get(d)??0);p=Math.max(p,e);o.push({date:d,equity:e,drawdown:e/p-1})}return o}
async function cot(){const url="https://publicreporting.cftc.gov/resource/gpe5-46if.json?$limit=5000&$where=cftc_contract_market_code='209742'&$order=report_date_as_yyyy_mm_dd";const r=await fetch(url,{headers:{"user-agent":"momentum-research/1.0"}});if(!r.ok)throw new Error(`CFTC ${r.status}`);const j:any[]=await r.json(),out:Cot[]=[];for(const x of j){const date=String(x.report_date_as_yyyy_mm_dd??"").slice(0,10),l=Number(x.asset_mgr_positions_long),s=Number(x.asset_mgr_positions_short);if(date&&Number.isFinite(l)&&Number.isFinite(s))out.push({date,net:l-s})}return out.sort((a,b)=>a.date.localeCompare(b.date))}
const OV:Record<string,string>={"2025-09-30":"2025-11-19","2025-10-07":"2025-11-21","2025-10-14":"2025-11-25","2025-10-21":"2025-12-02","2025-10-28":"2025-12-05","2025-11-04":"2025-12-09","2025-11-10":"2025-12-10","2025-11-18":"2025-12-12","2025-11-25":"2025-12-15","2025-12-02":"2025-12-17","2025-12-09":"2025-12-19","2025-12-16":"2025-12-23","2025-12-23":"2025-12-29"};
function cotStress(rows:Cot[],date:string){const cut=new Date(date+"T00:00:00Z");cut.setUTCDate(cut.getUTCDate()-7);const cutoff=cut.toISOString().slice(0,10),ds=rows.filter(x=>x.date<=cutoff&&(!OV[x.date]||OV[x.date]<=date));return ds.length>=5&&ds.at(-1)!.net<ds.at(-5)!.net}
function outerStates(f:EquityPoint[],g:EquityPoint[],qqq:PricePoint[],cr:Cot[]){const sh=core(f,g),sim=new Map(sh.map((x,i)=>[x.date,i])),q=[...qqq].sort((a,b)=>a.date.localeCompare(b.date)).filter(x=>x.date>=START&&x.date<=END),qm=new Map(q.map((x,i)=>[x.date,i]));let m3=false,confirm=0;const out:OuterRow[]=[];for(const x of sh){const ci=sim.get(x.date)!;const si=Math.max(0,ci-1);let enter=false,exit=false;if(si>=20){const qi=qm.get(sh[si].date);if(qi!=null&&qi>=20){const core20=sh[si].equity/sh[si-20].equity-1,qr=q[qi].close/q[qi-20].close-1,gap=core20-qr;enter=core20<0&&gap<=-.10;if(m3){if(gap>-.03)confirm++;else confirm=0;exit=confirm>=5}}}if(!m3&&enter){m3=true;confirm=0}else if(m3&&exit){m3=false;confirm=0}const cs=cotStress(cr,sh[si]?.date??x.date);out.push({date:x.date,state:m3?"DEEP":cs?"YELLOW":"NORMAL"})}return out}
const key=(t:FixedTarget)=>t.symbols.map((s,i)=>`${s}:${t.weights[i]?.toFixed(4)}`).join("|");
function outerWeights(s:OuterState){return s==="DEEP"?D:s==="YELLOW"?Y:N}
function accountSim(h:Record<string,PricePoint[]>,snaps:FixedSnap[],outer:OuterRow[],capital:number,integer:boolean){
 const maps=Object.fromEntries(Object.entries(h).map(([s,a])=>[s,new Map(a.map(x=>[x.date,x]))]));const sm=new Map(snaps.map(x=>[x.date,x])),om=new Map(outer.map(x=>[x.date,x.state])),dates=snaps.map(x=>x.date).filter(d=>om.has(d));
 let cash=capital,positions=new Map<string,number>(),pending:Target|null=null,lastMonth="",lastState:OuterState|null=null,lastFixed="",peak=capital,totalTurn=0,rebals=0;const curve:EquityPoint[]=[{date:dates[0],equity:1,drawdown:0}];
 const px=(s:string,d:string,f:"open"|"close")=>(maps[s] as Map<string,PricePoint>|undefined)?.get(d)?.[f];
 const equityAt=(d:string,f:"open"|"close")=>cash+[...positions].reduce((z,[s,sh])=>z+sh*(px(s,d,f)??px(s,d,"close")??0),0);
 for(let i=1;i<dates.length;i++){const d=dates[i];if(pending){const e0=equityAt(d,"open"),reserve=.0025,targetShares=new Map<string,number>();for(let j=0;j<pending.fixed.symbols.length;j++){const s=pending.fixed.symbols[j],p=px(s,d,"open"),w=pending.f*(pending.fixed.weights[j]??0);if(p&&w>0){const raw=e0*(1-reserve)*w/p;targetShares.set(s,integer?Math.floor(raw):raw)}}const gp=px("GLDM",d,"open");if(gp&&pending.gold>0){const raw=e0*(1-reserve)*pending.gold/gp;targetShares.set("GLDM",integer?Math.floor(raw):raw)}let trade=0;for(const s of new Set([...positions.keys(),...targetShares.keys()]))trade+=Math.abs((targetShares.get(s)??0)-(positions.get(s)??0))*(px(s,d,"open")??0);const targetValue=[...targetShares].reduce((z,[s,sh])=>z+sh*(px(s,d,"open")??0),0);cash=e0-targetValue-trade*COST;positions=targetShares;totalTurn+=trade/e0;rebals++;pending=null}
  const e=equityAt(d,"close"),norm=e/capital;peak=Math.max(peak,e);curve.push({date:d,equity:norm,drawdown:e/peak-1});const snap=sm.get(d)!;const state=om.get(d)!;const month=d.slice(0,7),fk=key(snap.target);if(month!==lastMonth||state!==lastState||fk!==lastFixed){const w=outerWeights(state);pending={state,fixed:snap.target,f:w.f,gold:w.gold,cash:w.cash};lastMonth=month;lastState=state;lastFixed=fk}}
 const st=performanceStats(curve);return{capital,integer,stats:st,totalTurnover:totalTurn,annualizedTurnover:totalTurn/((Date.parse(dates.at(-1)!)-Date.parse(dates[0]))/86400000/365.25),rebalanceCount:rebals,cashEnd:cash,positionsEnd:Object.fromEntries(positions)}
async function main(){const m=JSON.parse(await readFile(resolve("public/data/market-data.json"),"utf8"))as MF,u=JSON.parse(await readFile(resolve("data/universe-history.json"),"utf8"))as UF,us=[...u.history].sort((a,b)=>a.asOf.localeCompare(b.asOf));if(!m.histories.GLDM||m.histories.GLDM.length<200)m.histories.GLDM=await fetchYahooHistory("GLDM");const snaps=fixedSnaps(m.histories,us),f=snaps.map((x,i,a)=>{let p=1;for(let j=0;j<=i;j++)p=j===0?1:p*(a[j].equity/a[j-1].equity);return{date:x.date,equity:p,drawdown:0}}),g=runG(m.histories,us),cr=await cot(),outer=outerStates(f,g,m.histories.QQQ,cr);const frac=accountSim(m.histories,snaps,outer,100000,false),caps=[10000,25000,50000,100000,250000].map(c=>accountSim(m.histories,snaps,outer,c,true));console.log(JSON.stringify({definition:"rounded Stage21, release-aware CFTC, outer/fixed target changes execute next US open, 10bp one-way traded-notional cost, whole shares for SBI audit",fractional:frac,wholeShare:caps,delta:caps.map(x=>({capital:x.capital,cagrPct:(x.stats.cagr-frac.stats.cagr)*100,maxDDPct:(x.stats.maxDrawdown-frac.stats.maxDrawdown)*100}))},null,2))}
main().catch(e=>{console.error(e);process.exitCode=1});
