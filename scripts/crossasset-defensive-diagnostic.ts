import fs from 'node:fs/promises';
import path from 'node:path';
import { PRODUCTION_STRATEGY } from '../src/lib/config';
import { buildMonthlySignal } from '../src/lib/strategy/momentum';
import { initialEngineState, transitionDay } from '../src/lib/strategy/state-machine';
import { performanceStats } from '../src/lib/backtest';
import { nextUsTradingSession } from '../src/lib/trading-calendar';
import type { EquityPoint, PricePoint, UniverseMonth, StrategyConfig } from '../src/lib/types';

// Predeclared once before observing results: one cross-asset Risk-Off rule only.
// GLD = gold, DBC = broad commodities, IEF = intermediate Treasuries, BIL = T-bills.
// At each monthly Risk-Off signal, hold the single asset with highest positive trailing 6M return;
// if none is positive, remain cash. No threshold/window/asset-set grid.
const ASSETS=['GLD','DBC','IEF','BIL'] as const;
const COST=.001;
const cfg:StrategyConfig={...PRODUCTION_STRATEGY,momentum:{...PRODUCTION_STRATEGY.momentum,oneMonth:0,threeMonth:.25,sixMonth:.75},allocation:{...PRODUCTION_STRATEGY.allocation,baseTop1Weight:.6,concentratedTop1Weight:.7}};

async function yh(s:string,start='2007-01-01'){
  const a=Math.floor(Date.parse(start+'T00:00:00Z')/1000),b=Math.floor(Date.parse('2026-09-01T00:00:00Z')/1000);
  const r=await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${s}?period1=${a}&period2=${b}&interval=1d&events=div%2Csplits&includeAdjustedClose=true`,{headers:{'User-Agent':'Mozilla/5.0'}});
  if(!r.ok)throw Error(`${s}:${r.status}`);
  const j:any=await r.json(),x=j.chart.result[0],q=x.indicators.quote[0],ad=x.indicators.adjclose[0].adjclose;
  return x.timestamp.map((t:number,i:number)=>{if(q.open[i]==null||q.close[i]==null||ad[i]==null)return null;const k=ad[i]/q.close[i];return{date:new Date(t*1000).toISOString().slice(0,10),open:q.open[i]*k,close:ad[i]}as PricePoint}).filter(Boolean)as PricePoint[];
}
function monthEnd(p:PricePoint[]){const m=new Map<string,PricePoint>();for(const x of p)m.set(x.date.slice(0,7),x);return[...m.values()].sort((a,b)=>a.date.localeCompare(b.date));}
function target(a:Record<string,PricePoint[]>,d:string){
  const rows=ASSETS.map(s=>{const x=a[s].filter(p=>p.date<=d);return x.length>126?{s,r:x.at(-1)!.close/x.at(-127)!.close-1}:null}).filter(Boolean)as{s:string,r:number}[];
  rows.sort((x,y)=>y.r-x.r);
  return rows[0]?.r>0?rows[0]:null;
}
function defensive(q:PricePoint[],a:Record<string,PricePoint[]>){
  const qm=monthEnd(q),pm=Object.fromEntries(Object.entries(a).map(([s,p])=>[s,new Map(p.map(x=>[x.date,x]))]));let cash=1,pos:{s:string,sh:number}|null=null,peak=1;const z:EquityPoint[]=[];
  for(let i=9;i<qm.length;i++){
    const sig=qm[i],ma=qm.slice(i-9,i+1).reduce((s,x)=>s+x.close,0)/10,riskOn=sig.close>ma,ex=nextUsTradingSession(sig.date);
    if(pos){const px=pm[pos.s]?.get(ex)?.open;if(px)cash+=pos.sh*px*(1-COST);pos=null;}
    if(!riskOn){const t=target(a,sig.date);if(t){const px=pm[t.s]?.get(ex)?.open;if(px){pos={s:t.s,sh:cash*(1-COST)/px};cash=0;}}}
    const end=qm[i+1]?.date??'2026-08-25';
    for(const d of q.filter(x=>x.date>=ex&&x.date<=end).map(x=>x.date)){let e=cash;if(pos){const px=pm[pos.s]?.get(d)?.close;if(px)e+=pos.sh*px;}peak=Math.max(peak,e);z.push({date:d,equity:e,drawdown:e/peak-1});}
  }
  return z;
}
function core(h:Record<string,PricePoint[]>,u:UniverseMonth[]){const q=[...h.QQQ].sort((a,b)=>a.date.localeCompare(b.date)),ds=q.map(x=>x.date),ix=new Map(ds.map((d,i)=>[d,i])),pm=Object.fromEntries(Object.entries(h).map(([s,p])=>[s,new Map(p.map(x=>[x.date,x]))])),um=new Map(u.map(x=>[x.asOf,x]));let st=initialEngineState(cfg);const z:EquityPoint[]=[];for(let i=0;i<ds.length;i++){const d=ds[i];if(d<cfg.backtestStart)continue;const n=ds[i+1]??nextUsTradingSession(d),uu=um.get(d),sg=uu?buildMonthlySignal({universe:uu,histories:h,qqq:q,nextSessionDate:n,config:cfg}):null;if(sg&&sg.selectedSymbols.length===2)sg.targetWeights=sg.zGap!==null&&sg.zGap>=.25?[.7,.3]:[.6,.4];const ss=new Set(['QQQ',...st.currentPositions.map(p=>p.symbol),...(st.pendingSignal?.selectedSymbols??[]),...st.nextAction.symbols,...(sg?.selectedSymbols??[])]),pr=Object.fromEntries([...ss].map(s=>[s,pm[s]?.get(d)]));st=transitionDay(st,{date:d,prices:pr,qqqHistoryThroughClose:q.slice(0,(ix.get(d)??i)+1),monthlySignal:sg,nextSessionDate:n},cfg);z.push({date:d,equity:st.currentEquity,drawdown:st.drawdown});}return z;}
function gate(h:Record<string,PricePoint[]>,u:UniverseMonth[]){const q=[...h.QQQ].sort((a,b)=>a.date.localeCompare(b.date)),m=new Map<string,boolean>();for(const um of u){if(um.asOf<cfg.backtestStart)continue;const ex=nextUsTradingSession(um.asOf),sg=buildMonthlySignal({universe:um,histories:h,qqq:q,nextSessionDate:ex,config:cfg});m.set(ex,sg.marketRiskOn);}let s=true;const out=new Map<string,boolean>();for(const p of q.filter(x=>x.date>=cfg.backtestStart)){if(m.has(p.date))s=m.get(p.date)!;out.set(p.date,s);}return out;}
function combine(c:EquityPoint[],d:EquityPoint[],g:Map<string,boolean>){const dm=new Map(d.map(x=>[x.date,x.equity]));let e=1,peak=1,pc=c[0]?.equity??1,pd=dm.get(c[0]?.date)??1,pg=g.get(c[0]?.date)??true;const z:EquityPoint[]=[];for(let i=0;i<c.length;i++){const x=dm.get(c[i].date);if(x==null)continue;const rc=i?c[i].equity/pc-1:0,rd=i?x/pd-1:0,cg=g.get(c[i].date)??pg;pc=c[i].equity;pd=x;let f=1;if(i)f=cg===pg?1+(cg?rc:rd):(1+rc)*(1+rd);e*=f;pg=cg;peak=Math.max(peak,e);z.push({date:c[i].date,equity:e,drawdown:e/peak-1});}return z;}
function sl(c:EquityPoint[],s:string,e:string){const x=c.filter(p=>p.date>=s&&p.date<=e);if(!x.length)return[];const b=x[0].equity;return x.map(p=>({...p,equity:p.equity/b}));}
async function main(){
  const mk=JSON.parse(await fs.readFile(path.join(process.cwd(),'public/data/market-data.json'),'utf8'))as{histories:Record<string,PricePoint[]>},uf=JSON.parse(await fs.readFile(path.join(process.cwd(),'data/universe-history.json'),'utf8'))as{history:UniverseMonth[]},u=[...uf.history].sort((x,y)=>x.asOf.localeCompare(y.asOf));
  const a:Record<string,PricePoint[]>={};for(const s of ASSETS)a[s]=await yh(s);const q=await yh('QQQ'),d=defensive(q,a),c=core(mk.histories,u),g=gate(mk.histories,u),recent=sl(d,'2020-01-01','2026-08-25'),comb=combine(c,recent,g);
  const longPeriods={p0812:performanceStats(sl(d,'2008-01-01','2012-12-31')),p1319:performanceStats(sl(d,'2013-01-01','2019-12-31')),p2026:performanceStats(recent),full:performanceStats(d)};
  const passLong=Object.values({p0812:longPeriods.p0812,p1319:longPeriods.p1319,p2026:longPeriods.p2026}).every(x=>x.cagr>0);
  const annual=[2022,2023,2024,2025,2026].map(y=>({y,candidate:performanceStats(sl(comb,`${y}-01-01`,y===2026?'2026-08-25':`${y}-12-31`)),core:performanceStats(sl(c,`${y}-01-01`,y===2026?'2026-08-25':`${y}-12-31`))}));
  const coreStats=performanceStats(c),combined=performanceStats(comb);const passIntegration=combined.cagr>coreStats.cagr&&combined.maxDrawdown>=coreStats.maxDrawdown-0.02;
  const o={generatedAt:new Date().toISOString(),validity:{researchOnly:true,trueOOS:false,noLeverage:true,pit:true,nextOpen:true,cost:COST,parameterSearch:false,rule:'During monthly QQQ 10M-MA Risk-Off, hold one of GLD/DBC/IEF/BIL with highest positive trailing 6M total return; otherwise cash.',passGate:'Positive defensive-sleeve CAGR in 2008-12, 2013-19, and 2020-26; integrated CAGR above Core without worsening MaxDD by more than 2pp.'},longPeriods,core:coreStats,combined2020:combined,annual,passLong,passIntegration,passGate:passLong&&passIntegration};
  const dir=path.join(process.cwd(),'data/research/crossasset-defensive-diagnostic');await fs.mkdir(dir,{recursive:true});await fs.writeFile(path.join(dir,'result.json'),JSON.stringify(o,null,2));console.log(JSON.stringify(o,null,2));
}
main().catch(e=>{console.error(e);process.exit(1)});
