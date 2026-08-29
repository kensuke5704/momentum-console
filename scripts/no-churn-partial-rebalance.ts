import fs from "node:fs/promises";
import path from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import { initialEngineState, transitionDay, type EngineState } from "../src/lib/strategy/state-machine";
import { nextUsTradingSession } from "../src/lib/trading-calendar";
import { performanceStats } from "../src/lib/backtest";
import type { EquityPoint, MonthlySignal, PositionState, PricePoint, UniverseMonth } from "../src/lib/types";

const TAX=0.20315;
type Variant={id:string; drift:number|null};
const VARIANTS:Variant[]=[
  {id:"PRODUCTION",drift:null},
  {id:"NO_CHURN",drift:Infinity},
  {id:"PR5",drift:0.05},
  {id:"PR10",drift:0.10},
  {id:"PR15",drift:0.15},
];

type TaxLedger={gain:Record<string,number>;loss:Record<string,number>;taxes:number;sales:number;partialSales:number;turnover:number};

type Sim={variant:string;curve:EquityPoint[];afterTaxCurve:EquityPoint[];tax:TaxLedger;fullRebalances:number;partialRebalances:number;skippedSameSet:number};

const clone=<T>(x:T):T=>structuredClone(x);
const sameSet=(a:string[],b:string[])=>[...a].sort().join(",")===[...b].sort().join(",");

function targetWeight(signal:MonthlySignal,symbol:string){const i=signal.selectedSymbols.indexOf(symbol);return i>=0?signal.targetWeights[i]:null}

function annualTax(curve:EquityPoint[],l:TaxLedger){
  if(!curve.length)return[];
  const years=[...new Set(curve.map(p=>p.date.slice(0,4)))];const ty:Record<string,number>={};let carry:{y:number,a:number}[]=[];
  for(const ys of years){const y=+ys;carry=carry.filter(x=>y-x.y<=3);let net=(l.gain[ys]??0)-(l.loss[ys]??0);if(net>0){for(const x of carry){const u=Math.min(net,x.a);net-=u;x.a-=u;if(net<=0)break}carry=carry.filter(x=>x.a>1e-12);ty[ys]=net*TAX}else if(net<0)carry.push({y,a:-net})}
  l.taxes=Object.values(ty).reduce((a,b)=>a+b,0);
  let e=curve[0].equity,pg=curve[0].equity,peak=e;const out:EquityPoint[]=[];
  for(let i=0;i<curve.length;i++){const p=curve[i];if(i)e*=p.equity/pg;pg=p.equity;const n=curve[i+1];if((!n||n.date.slice(0,4)!==p.date.slice(0,4))&&(ty[p.date.slice(0,4)]??0)>0)e=Math.max(0,e-(ty[p.date.slice(0,4)]??0)*(e/Math.max(p.equity,1e-12)));peak=Math.max(peak,e);out.push({date:p.date,equity:e,drawdown:e/peak-1})}
  return out;
}

function recordSale(l:TaxLedger,p:PositionState,shares:number,px:number,date:string,partial=false){
  if(shares<=0)return;const proceeds=shares*px*(1-PRODUCTION_STRATEGY.execution.transactionCost);const basis=shares*p.entryPrice;const pnl=proceeds-basis;const y=date.slice(0,4);if(pnl>=0)l.gain[y]=(l.gain[y]??0)+pnl;else l.loss[y]=(l.loss[y]??0)-pnl;l.sales++;if(partial)l.partialSales++;l.turnover+=proceeds;
}

function maybePartialRebalance(state:EngineState,input:{date:string;prices:Record<string,PricePoint|undefined>},signal:MonthlySignal,drift:number,ledger:TaxLedger):boolean{
  if(state.state!=="INVESTED"||state.currentPositions.length!==2||signal.selectedSymbols.length!==2||!sameSet(state.currentPositions.map(p=>p.symbol),signal.selectedSymbols))return false;
  const vals=state.currentPositions.map(p=>p.shares*(input.prices[p.symbol]?.open??p.currentPrice??p.entryPrice));const total=vals.reduce((a,b)=>a+b,0)+state.cash;if(total<=0)return true;
  const weights=state.currentPositions.map((p,i)=>vals[i]/total);let maxDrift=0;for(let i=0;i<state.currentPositions.length;i++){const tw=targetWeight(signal,state.currentPositions[i].symbol)??weights[i];maxDrift=Math.max(maxDrift,Math.abs(weights[i]-tw))}
  if(maxDrift<=drift)return true;
  const opens=state.currentPositions.map(p=>input.prices[p.symbol]?.open??p.currentPrice??p.entryPrice);
  const desired=state.currentPositions.map(p=>total*(targetWeight(signal,p.symbol)??0.5));
  // sell overweight positions first
  for(let i=0;i<state.currentPositions.length;i++){
    const p=state.currentPositions[i],px=opens[i];const cur=p.shares*px;if(cur>desired[i]+1e-12){const grossSell=cur-desired[i];const shares=grossSell/px;recordSale(ledger,p,shares,px,input.date,true);p.shares-=shares;state.cash+=grossSell*(1-PRODUCTION_STRATEGY.execution.transactionCost);}
  }
  // buy underweight using available cash
  for(let i=0;i<state.currentPositions.length;i++){
    const p=state.currentPositions[i],px=opens[i];const cur=p.shares*px;if(cur<desired[i]-1e-12&&state.cash>0){const grossBuy=Math.min(desired[i]-cur,state.cash);const invested=grossBuy*(1-PRODUCTION_STRATEGY.execution.transactionCost);p.shares+=invested/px;state.cash-=grossBuy;}
  }
  for(const p of state.currentPositions){const px=input.prices[p.symbol]?.open??p.currentPrice??p.entryPrice;p.currentPrice=px;}
  state.currentEquity=state.cash+state.currentPositions.reduce((s,p)=>s+p.shares*(p.currentPrice??p.entryPrice),0);
  return true;
}

function simulate(hist:Record<string,PricePoint[]>,universe:UniverseMonth[],v:Variant):Sim{
  const qqq=[...(hist.QQQ??[])].sort((a,b)=>a.date.localeCompare(b.date));const dates=qqq.map(p=>p.date),idx=new Map(dates.map((d,i)=>[d,i]));const pm=Object.fromEntries(Object.entries(hist).map(([s,ps])=>[s,new Map(ps.map(p=>[p.date,p]))]));const um=new Map(universe.map(u=>[u.asOf,u]));let state=initialEngineState(PRODUCTION_STRATEGY);const curve:EquityPoint[]=[];const tax:TaxLedger={gain:{},loss:{},taxes:0,sales:0,partialSales:0,turnover:0};let fullRebalances=0,partialRebalances=0,skippedSameSet=0;
  for(let i=0;i<dates.length;i++){
    const date=dates[i];if(date<PRODUCTION_STRATEGY.backtestStart)continue;const next=dates[i+1]??nextUsTradingSession(date);const u=um.get(date);const sig=u?buildMonthlySignal({universe:u,histories:hist,qqq,nextSessionDate:next,config:PRODUCTION_STRATEGY}):null;
    const sy=new Set(["QQQ",...state.currentPositions.map(p=>p.symbol),...(state.pendingSignal?.selectedSymbols??[]),...state.nextAction.symbols,...(sig?.selectedSymbols??[])]);const prices=Object.fromEntries([...sy].map(s=>[s,pm[s]?.get(date)]));
    // intercept same-set month-end execution for research variants
    if(v.id!=="PRODUCTION"&&state.nextAction.type==="MONTH_END_REBALANCE_NEXT_OPEN"&&state.nextAction.executionDate===date&&state.pendingSignal&&sameSet(state.currentPositions.map(p=>p.symbol),state.pendingSignal.selectedSymbols)){
      const before=clone(state.currentPositions);const handled=v.drift===Infinity?true:maybePartialRebalance(state,{date,prices},state.pendingSignal,v.drift??0,tax);if(handled){if(v.drift===Infinity)skippedSameSet++;else{const changed=before.some((p,j)=>Math.abs(p.shares-state.currentPositions[j].shares)>1e-12);if(changed)partialRebalances++;else skippedSameSet++;}state.nextAction={type:"HOLD",executionDate:null,symbols:state.currentPositions.map(p=>p.symbol),targetWeights:state.currentPositions.map(p=>p.targetWeight),reason:"Research no-churn/partial rebalance"};}
    }
    const before=clone(state);
    state=transitionDay(state,{date,prices,qqqHistoryThroughClose:qqq.slice(0,(idx.get(date)??i)+1),monthlySignal:sig,nextSessionDate:next},PRODUCTION_STRATEGY);
    // record full-position exits, including same-symbol full rebalance cases in Production
    const hadExit=before.currentPositions.length>0&&before.nextAction.type==="SELL_ALL_NEXT_OPEN"&&before.nextAction.executionDate===date;
    const hadRebal=before.currentPositions.length>0&&before.nextAction.type==="MONTH_END_REBALANCE_NEXT_OPEN"&&before.nextAction.executionDate===date;
    if(hadExit||hadRebal){for(const p of before.currentPositions){const px=prices[p.symbol]?.open??prices[p.symbol]?.close??p.currentPrice??p.entryPrice;recordSale(tax,p,p.shares,px,date,false)}if(hadRebal)fullRebalances++;}
    curve.push({date,equity:state.currentEquity,drawdown:state.drawdown});
  }
  return{variant:v.id,curve,afterTaxCurve:annualTax(curve,tax),tax,fullRebalances,partialRebalances,skippedSameSet};
}

function slice(c:EquityPoint[],s:string,e:string){const x=c.filter(p=>p.date>=s&&p.date<=e);if(!x.length)return[];const b=x[0].equity;return x.map(p=>({...p,equity:p.equity/b}))}

async function main(){
  const market=JSON.parse(await fs.readFile(path.join(process.cwd(),"public/data/market-data.json"),"utf8")) as {histories:Record<string,PricePoint[]>};const uf=JSON.parse(await fs.readFile(path.join(process.cwd(),"data/universe-history.json"),"utf8")) as {history:UniverseMonth[]};const universe=[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf));const sims=VARIANTS.map(v=>simulate(market.histories,universe,v));const years=[2022,2023,2024,2025,2026];
  const full=sims.map(s=>({variant:s.variant,gross:performanceStats(s.curve),afterTax:performanceStats(s.afterTaxCurve),taxPaidApprox:s.tax.taxes,sales:s.tax.sales,partialSales:s.tax.partialSales,turnover:s.tax.turnover,fullRebalances:s.fullRebalances,partialRebalances:s.partialRebalances,skippedSameSet:s.skippedSameSet}));
  const oos=years.map(y=>({year:y,rows:sims.map(s=>{const end=y===2026?"2026-08-25":`${y}-12-31`;return{variant:s.variant,gross:performanceStats(slice(s.curve,`${y}-01-01`,end)),afterTax:performanceStats(slice(s.afterTaxCurve,`${y}-01-01`,end))}})}));
  const output={generatedAt:new Date().toISOString(),validity:{researchOnly:true,trueOOS:false,architectureHindsightRemains:true,variantsPredeclared:["NO_CHURN","PR5","PR10","PR15"],warning:"Historical comparative diagnostic. Annual realized-P&L tax approximation with 3-year loss carryforward; partial-sale basis assumes original entry price and does not model exact Japanese tax-lot/withholding timing."},rules:{NO_CHURN:"same selected pair -> no month-end trade",PR5:"same pair -> partial rebalance only if max absolute weight drift from target exceeds 5 percentage points",PR10:"same with 10 points",PR15:"same with 15 points",unchanged:"signal, universe, Top2, market gate, stop, circuit, recovery, transaction cost"},full,oos};
  const dir=path.join(process.cwd(),"data/research/no-churn-partial-rebalance");await fs.mkdir(dir,{recursive:true});await fs.writeFile(path.join(dir,"result.json"),JSON.stringify(output,null,2));console.log(JSON.stringify(output,null,2));
}
main().catch(e=>{console.error(e);process.exit(1)});
