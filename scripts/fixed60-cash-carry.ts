import fs from 'node:fs/promises';
import path from 'node:path';
import { PRODUCTION_STRATEGY } from '../src/lib/config';
import { buildMonthlySignal } from '../src/lib/strategy/momentum';
import { initialEngineState, transitionDay } from '../src/lib/strategy/state-machine';
import { performanceStats } from '../src/lib/backtest';
import { nextUsTradingSession } from '../src/lib/trading-calendar';
import type { EquityPoint, PricePoint, StrategyConfig, UniverseMonth } from '../src/lib/types';

const cfg:StrategyConfig={...PRODUCTION_STRATEGY,allocation:{...PRODUCTION_STRATEGY.allocation,baseTop1Weight:.6,concentratedTop1Weight:.6,concentrationZGap:999,maxTop1Weight:.6}};
async function yh(s:string,start='2007-01-01'){
 const a=Math.floor(Date.parse(start+'T00:00:00Z')/1000),b=Math.floor(Date.parse('2026-09-01T00:00:00Z')/1000);
 const r=await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${s}?period1=${a}&period2=${b}&interval=1d&events=div%2Csplits&includeAdjustedClose=true`,{headers:{'User-Agent':'Mozilla/5.0'}});if(!r.ok)throw Error(`${s}:${r.status}`);
 const j:any=await r.json(),x=j.chart.result[0],q=x.indicators.quote[0],ad=x.indicators.adjclose[0].adjclose;
 return x.timestamp.map((t:number,i:number)=>q.close[i]!=null&&ad[i]!=null?{date:new Date(t*1000).toISOString().slice(0,10),open:q.open[i]??q.close[i],close:ad[i]} as PricePoint:null).filter(Boolean) as PricePoint[];
}
function sl(c:EquityPoint[],s:string,e:string){const x=c.filter(p=>p.date>=s&&p.date<=e);if(x.length<2)return[];const prev=[...c].reverse().find(p=>p.date<s);const rows=prev?[prev,...x]:x,b=rows[0].equity;return rows.map(p=>({...p,equity:p.equity/b}));}
function sim(hist:Record<string,PricePoint[]>,u:UniverseMonth[],bil:PricePoint[],carry:boolean){
 const q=[...hist.QQQ].sort((a,b)=>a.date.localeCompare(b.date)),dates=q.map(p=>p.date),ix=new Map(dates.map((d,i)=>[d,i])),pm=Object.fromEntries(Object.entries(hist).map(([s,p])=>[s,new Map(p.map(x=>[x.date,x]))])),um=new Map(u.map(x=>[x.asOf,x])),bm=new Map(bil.map(x=>[x.date,x.close]));let st=initialEngineState(cfg),peak=1,prevBil:number|null=null;const z:EquityPoint[]=[];
 for(let i=0;i<dates.length;i++){
  const d=dates[i];if(d<cfg.backtestStart)continue;
  const b=bm.get(d);if(carry&&b&&prevBil&&st.cash>0){st.cash*=b/prevBil;st.currentEquity=st.cash+st.currentPositions.reduce((sum,p)=>sum+p.shares*(p.currentPrice??p.entryPrice),0);}
  if(b)prevBil=b;
  const n=dates[i+1]??nextUsTradingSession(d),uu=um.get(d),sg=uu?buildMonthlySignal({universe:uu,histories:hist,qqq:q,nextSessionDate:n,config:cfg}):null;
  if(sg&&sg.selectedSymbols.length===2)sg.targetWeights=[.6,.4];
  const sy=new Set(['QQQ',...st.currentPositions.map(p=>p.symbol),...(st.pendingSignal?.selectedSymbols??[]),...st.nextAction.symbols,...(sg?.selectedSymbols??[])]),prices=Object.fromEntries([...sy].map(s=>[s,pm[s]?.get(d)]));
  st=transitionDay(st,{date:d,prices,qqqHistoryThroughClose:q.slice(0,(ix.get(d)??i)+1),monthlySignal:sg,nextSessionDate:n},cfg);peak=Math.max(peak,st.currentEquity);z.push({date:d,equity:st.currentEquity,drawdown:st.currentEquity/peak-1});
 }
 return z;
}
async function main(){const mk=JSON.parse(await fs.readFile(path.join(process.cwd(),'public/data/market-data.json'),'utf8')) as {histories:Record<string,PricePoint[]>},uf=JSON.parse(await fs.readFile(path.join(process.cwd(),'data/universe-history.json'),'utf8')) as {history:UniverseMonth[]},u=[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf)),bil=await yh('BIL'),base=sim(mk.histories,u,bil,false),carry=sim(mk.histories,u,bil,true),years=[2022,2023,2024,2025,2026];const fullBase=performanceStats(base),fullCarry=performanceStats(carry),annual=years.map(y=>{const e=y===2026?'2026-08-25':`${y}-12-31`,b=performanceStats(sl(base,`${y}-01-01`,e)),c=performanceStats(sl(carry,`${y}-01-01`,e));return{year:y,base:b,carry:c,cagrDelta:c.cagr-b.cagr};});const out={generatedAt:new Date().toISOString(),validity:{researchOnly:true,trueOOS:false,noRuleChange:true,noLeverage:true,pit:true,proxy:'BIL adjusted total return applied only to strategy cash balance; no asset-selection or timing parameter changed.',caveat:'Proxy for investable cash/MMF/T-bill carry; ignores broker-specific yield, taxes, spread and settlement details.'},base:fullBase,carry:fullCarry,cagrDelta:fullCarry.cagr-fullBase.cagr,maxDdDelta:fullCarry.maxDrawdown-fullBase.maxDrawdown,annual};const d=path.join(process.cwd(),'data/research/fixed60-cash-carry');await fs.mkdir(d,{recursive:true});await fs.writeFile(path.join(d,'result.json'),JSON.stringify(out,null,2));console.log(JSON.stringify(out,null,2));}
main().catch(e=>{console.error(e);process.exit(1)});
