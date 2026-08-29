import fs from "node:fs/promises";
import path from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { buildMonthlySignal, monthlyCloses } from "../src/lib/strategy/momentum";
import { initialEngineState, transitionDay } from "../src/lib/strategy/state-machine";
import { performanceStats } from "../src/lib/backtest";
import { nextUsTradingSession } from "../src/lib/trading-calendar";
import type { EquityPoint, MonthlySignal, PricePoint, UniverseMonth } from "../src/lib/types";

const sameSet=(a:string[],b:string[])=>[...a].sort().join(",")===[...b].sort().join(",");
const weightMap=(s:MonthlySignal)=>new Map(s.selectedSymbols.map((x,i)=>[x,s.targetWeights[i]]));
function exactSameWeights(state:any,s:MonthlySignal){if(!sameSet(state.currentPositions.map((p:any)=>p.symbol),s.selectedSymbols))return false;const wm=weightMap(s);return state.currentPositions.every((p:any)=>Math.abs((wm.get(p.symbol)??-9)-p.targetWeight)<1e-12)}
function forward3m(hist:PricePoint[],date:string){const m=monthlyCloses(hist).filter(p=>p.date>=date);if(m.length<4)return null;const a=m[0]?.close,b=m[3]?.close;return a&&b?b/a-1:null}
function slice(c:EquityPoint[],s:string,e:string){const x=c.filter(p=>p.date>=s&&p.date<=e);if(!x.length)return[];const b=x[0].equity;return x.map(p=>({...p,equity:p.equity/b}))}

function simulate(hist:Record<string,PricePoint[]>,universe:UniverseMonth[],exact:boolean){
 const qqq=[...(hist.QQQ??[])].sort((a,b)=>a.date.localeCompare(b.date));const dates=qqq.map(p=>p.date);const idx=new Map(dates.map((d,i)=>[d,i]));const pm=Object.fromEntries(Object.entries(hist).map(([s,ps])=>[s,new Map(ps.map(p=>[p.date,p]))]));const um=new Map(universe.map(u=>[u.asOf,u]));let st=initialEngineState(PRODUCTION_STRATEGY),skips=0,sales=0;const curve:EquityPoint[]=[];
 for(let i=0;i<dates.length;i++){const date=dates[i];if(date<PRODUCTION_STRATEGY.backtestStart)continue;const next=dates[i+1]??nextUsTradingSession(date);const u=um.get(date);const sig=u?buildMonthlySignal({universe:u,histories:hist,qqq,nextSessionDate:next,config:PRODUCTION_STRATEGY}):null;const sy=new Set(["QQQ",...st.currentPositions.map(p=>p.symbol),...(st.pendingSignal?.selectedSymbols??[]),...st.nextAction.symbols,...(sig?.selectedSymbols??[])]);const prices=Object.fromEntries([...sy].map(s=>[s,pm[s]?.get(date)]));
  if(exact&&st.nextAction.type==="MONTH_END_REBALANCE_NEXT_OPEN"&&st.nextAction.executionDate===date&&st.pendingSignal&&exactSameWeights(st,st.pendingSignal)){st.nextAction={type:"HOLD",executionDate:null,symbols:st.currentPositions.map(p=>p.symbol),targetWeights:st.currentPositions.map(p=>p.targetWeight),reason:"Research exact no-churn"};skips++;}
  const before=structuredClone(st);st=transitionDay(st,{date,prices,qqqHistoryThroughClose:qqq.slice(0,(idx.get(date)??i)+1),monthlySignal:sig,nextSessionDate:next},PRODUCTION_STRATEGY);if(before.currentPositions.length&&((before.nextAction.type==="SELL_ALL_NEXT_OPEN"||before.nextAction.type==="MONTH_END_REBALANCE_NEXT_OPEN")&&before.nextAction.executionDate===date))sales+=before.currentPositions.length;curve.push({date,equity:st.currentEquity,drawdown:st.drawdown});
 }
 return{curve,skips,sales};
}

async function main(){
 const market=JSON.parse(await fs.readFile(path.join(process.cwd(),"public/data/market-data.json"),"utf8")) as {histories:Record<string,PricePoint[]>};const uf=JSON.parse(await fs.readFile(path.join(process.cwd(),"data/universe-history.json"),"utf8")) as {history:UniverseMonth[]};const universe=[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf));const qqq=market.histories.QQQ??[];
 const prod=simulate(market.histories,universe,false),exact=simulate(market.histories,universe,true);const years=[2022,2023,2024,2025,2026];
 const noChurn={full:[{variant:"PRODUCTION",stats:performanceStats(prod.curve),sales:prod.sales},{variant:"EXACT_NO_CHURN",stats:performanceStats(exact.curve),sales:exact.sales,skips:exact.skips}],oos:years.map(y=>({year:y,production:performanceStats(slice(prod.curve,`${y}-01-01`,y===2026?"2026-08-25":`${y}-12-31`)),exactNoChurn:performanceStats(slice(exact.curve,`${y}-01-01`,y===2026?"2026-08-25":`${y}-12-31`))}))};
 const universeRows=[] as any[];for(const u of universe){if(u.asOf<PRODUCTION_STRATEGY.backtestStart)continue;const sig=buildMonthlySignal({universe:u,histories:market.histories,qqq,nextSessionDate:null,config:PRODUCTION_STRATEGY});const vals=u.symbols.map(m=>({symbol:m.symbol,universeRank:m.universeRank,r:forward3m(market.histories[m.symbol]??[],u.asOf)})).filter(x=>x.r!==null) as {symbol:string;universeRank:number;r:number}[];if(!vals.length)continue;vals.sort((a,b)=>b.r-a.r);const w=vals[0];const band=w.universeRank<=20?"1-20":w.universeRank<=40?"21-40":w.universeRank<=60?"41-60":"61-80";universeRows.push({date:u.asOf,winner:w.symbol,winnerUniverseRank:w.universeRank,winnerBand:band,winnerForward3m:w.r,selected:sig.selectedSymbols,selectedContainsWinner:sig.selectedSymbols.includes(w.symbol)});}
 const bandCounts=Object.fromEntries(["1-20","21-40","41-60","61-80"].map(b=>[b,universeRows.filter(r=>r.winnerBand===b).length]));
 const output={generatedAt:new Date().toISOString(),validity:{researchOnly:true,trueOOS:false,architectureHindsightRemains:true,noLeverage:true,warning:"Exact no-churn is a historical state-machine diagnostic. Universe winner-capture uses forward 3-month returns and is descriptive only, never a tradable signal."},noChurn,universeWinnerCapture:{months:universeRows.length,bandCounts,selectedContainsFutureWinner:universeRows.filter(r=>r.selectedContainsWinner).length,shareSelectedContainsFutureWinner:universeRows.length?universeRows.filter(r=>r.selectedContainsWinner).length/universeRows.length:null,rows:universeRows}};const dir=path.join(process.cwd(),"data/research/nonleveraged-next-screen");await fs.mkdir(dir,{recursive:true});await fs.writeFile(path.join(dir,"result.json"),JSON.stringify(output,null,2));console.log(JSON.stringify(output,null,2));
}
main().catch(e=>{console.error(e);process.exit(1)});