import fs from "node:fs/promises";
import path from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import { initialEngineState, transitionDay, type EngineState } from "../src/lib/strategy/state-machine";
import { nextUsTradingSession } from "../src/lib/trading-calendar";
import { performanceStats } from "../src/lib/backtest";
import type { EquityPoint, MonthlySignal, PricePoint, UniverseMonth } from "../src/lib/types";

type Variant = { id:string; gainRank:number; lossRank:number };
const TAX=0.20315;
const VARIANTS:Variant[]=[
  {id:"PRODUCTION",gainRank:2,lossRank:2},
  {id:"H3",gainRank:3,lossRank:3},
  {id:"H4",gainRank:4,lossRank:4},
  {id:"TAX_H4",gainRank:4,lossRank:3},
  {id:"TAX_H5",gainRank:5,lossRank:3},
];

type TaxLedger={realizedGainByYear:Record<string,number>; realizedLossByYear:Record<string,number>; turnover:number; sales:number; taxes:number};
type SimResult={variant:string;curve:EquityPoint[];afterTaxCurve:EquityPoint[];tax:TaxLedger;events:number;monthlySwitches:number};
const clone=<T>(x:T):T=>structuredClone(x);

function rankOf(signal:MonthlySignal,symbol:string){return signal.candidates.find(c=>c.symbol===symbol)?.rank ?? null;}
function candidate(signal:MonthlySignal,symbol:string){return signal.candidates.find(c=>c.symbol===symbol);}
function normalizeSignal(base:MonthlySignal,state:EngineState,v:Variant):MonthlySignal{
  if(v.id==="PRODUCTION" || state.state!=="INVESTED" || state.currentPositions.length!==2 || !base.marketRiskOn || base.selectedSymbols.length!==2)return base;
  const retained:string[]=[];
  for(const p of state.currentPositions){
    const c=candidate(base,p.symbol); if(!c?.eligible || c.rank==null)continue;
    const gain=(p.currentPrice ?? p.entryPrice)/p.entryPrice-1;
    const maxRank=gain>0?v.gainRank:v.lossRank;
    if(c.rank<=maxRank)retained.push(p.symbol);
  }
  const chosen=[...retained];
  for(const c of base.candidates.filter(c=>c.eligible&&c.rank!=null).sort((a,b)=>(a.rank??999)-(b.rank??999))){
    if(chosen.length>=2)break; if(!chosen.includes(c.symbol))chosen.push(c.symbol);
  }
  if(chosen.length!==2)return base;
  if(chosen[0]===base.selectedSymbols[0]&&chosen[1]===base.selectedSymbols[1])return base;
  // Keep allocation rule conservative: only preserve original 70/30 when the same top symbol remains first; otherwise 50/50.
  const sameTop=chosen[0]===base.selectedSymbols[0];
  const targetWeights=sameTop&&base.targetWeights[0]>0.5?[base.targetWeights[0],1-base.targetWeights[0]]:[0.5,0.5];
  return {...base,selectedSymbols:chosen,targetWeights,allocationMode:targetWeights[0]>0.5?"70/30":"50/50"};
}

function maxDD(curve:EquityPoint[]){let peak=curve[0]?.equity??1,dd=0;for(const p of curve){peak=Math.max(peak,p.equity);dd=Math.min(dd,p.equity/peak-1)}return dd;}
function applyAnnualTaxes(curve:EquityPoint[],ledger:TaxLedger){
  if(!curve.length)return [];
  const taxesByYear:Record<string,number>={};
  const years=[...new Set(curve.map(p=>p.date.slice(0,4)))];
  let carry:{year:number,amount:number}[]=[];
  for(const ys of years){const y=Number(ys);carry=carry.filter(x=>y-x.year<=3);let net=(ledger.realizedGainByYear[ys]??0)-(ledger.realizedLossByYear[ys]??0);if(net>0){for(const lot of carry){const use=Math.min(net,lot.amount);net-=use;lot.amount-=use;if(net<=0)break;}carry=carry.filter(x=>x.amount>1e-12);taxesByYear[ys]=net*TAX;}else if(net<0)carry.push({year:y,amount:-net});}
  let taxEquity=curve[0].equity,prevGross=curve[0].equity,peak=taxEquity;const out:EquityPoint[]=[];
  for(let i=0;i<curve.length;i++){
    const p=curve[i];if(i>0){const grossRet=p.equity/prevGross-1;taxEquity*=1+grossRet;}prevGross=p.equity;
    const next=curve[i+1]; if((!next||next.date.slice(0,4)!==p.date.slice(0,4))&&(taxesByYear[p.date.slice(0,4)]??0)>0){const scale=taxEquity/Math.max(p.equity,1e-12);taxEquity=Math.max(0,taxEquity-(taxesByYear[p.date.slice(0,4)]??0)*scale);}
    peak=Math.max(peak,taxEquity);out.push({date:p.date,equity:taxEquity,drawdown:taxEquity/peak-1});
  }
  ledger.taxes=Object.values(taxesByYear).reduce((a,b)=>a+b,0);return out;
}

function simulate(histories:Record<string,PricePoint[]>,universe:UniverseMonth[],v:Variant):SimResult{
 const qqq=[...(histories.QQQ??[])].sort((a,b)=>a.date.localeCompare(b.date));const dates=qqq.map(p=>p.date);const idx=new Map(dates.map((d,i)=>[d,i]));const priceMaps=Object.fromEntries(Object.entries(histories).map(([s,ps])=>[s,new Map(ps.map(p=>[p.date,p]))]));const uni=new Map(universe.map(u=>[u.asOf,u]));let state=initialEngineState(PRODUCTION_STRATEGY);const curve:EquityPoint[]=[];const ledger:TaxLedger={realizedGainByYear:{},realizedLossByYear:{},turnover:0,sales:0,taxes:0};let monthlySwitches=0;
 for(let i=0;i<dates.length;i++){
  const date=dates[i];if(date<PRODUCTION_STRATEGY.backtestStart)continue;const nextDate=dates[i+1]??nextUsTradingSession(date);const u=uni.get(date);let sig=u?buildMonthlySignal({universe:u,histories,qqq,nextSessionDate:nextDate,config:PRODUCTION_STRATEGY}):null;if(sig)sig=normalizeSignal(sig,state,v);
  const before=clone(state);const symbols=new Set(["QQQ",...state.currentPositions.map(p=>p.symbol),...(state.pendingSignal?.selectedSymbols??[]),...state.nextAction.symbols,...(sig?.selectedSymbols??[])]);const prices=Object.fromEntries([...symbols].map(s=>[s,priceMaps[s]?.get(date)]));state=transitionDay(state,{date,prices,qqqHistoryThroughClose:qqq.slice(0,(idx.get(date)??i)+1),monthlySignal:sig,nextSessionDate:nextDate},PRODUCTION_STRATEGY);
  const beforeSyms=before.currentPositions.map(p=>p.symbol).sort().join(","),afterSyms=state.currentPositions.map(p=>p.symbol).sort().join(",");if(sig&&before.state==="INVESTED"&&beforeSyms!==afterSyms)monthlySwitches++;
  const afterSet=new Set(state.currentPositions.map(p=>p.symbol));for(const p of before.currentPositions){if(afterSet.has(p.symbol))continue;const px=prices[p.symbol]?.open??prices[p.symbol]?.close??p.currentPrice??p.entryPrice;const proceeds=p.shares*px*(1-PRODUCTION_STRATEGY.execution.transactionCost);const basis=p.shares*p.entryPrice;const pnl=proceeds-basis;const y=date.slice(0,4);if(pnl>=0)ledger.realizedGainByYear[y]=(ledger.realizedGainByYear[y]??0)+pnl;else ledger.realizedLossByYear[y]=(ledger.realizedLossByYear[y]??0)-pnl;ledger.turnover+=proceeds;ledger.sales++;}
  curve.push({date,equity:state.currentEquity,drawdown:state.drawdown});
 }
 const afterTaxCurve=applyAnnualTaxes(curve,ledger);return{variant:v.id,curve,afterTaxCurve,tax:ledger,events:state.events.length,monthlySwitches};
}
function sliceCurve(curve:EquityPoint[],start:string,end:string){const xs=curve.filter(p=>p.date>=start&&p.date<=end);if(!xs.length)return[];const b=xs[0].equity;return xs.map(p=>({...p,equity:p.equity/b}));}
async function main(){const market=JSON.parse(await fs.readFile(path.join(process.cwd(),"public/data/market-data.json"),"utf8")) as {histories:Record<string,PricePoint[]>};const uf=JSON.parse(await fs.readFile(path.join(process.cwd(),"data/universe-history.json"),"utf8")) as {history:UniverseMonth[]};const universe=[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf));const sims=VARIANTS.map(v=>simulate(market.histories,universe,v));const splits=[{trainEnd:"2021-12-31",oosStart:"2022-01-01",oosEnd:"2022-12-31"},{trainEnd:"2022-12-31",oosStart:"2023-01-01",oosEnd:"2023-12-31"},{trainEnd:"2023-12-31",oosStart:"2024-01-01",oosEnd:"2024-12-31"},{trainEnd:"2024-12-31",oosStart:"2025-01-01",oosEnd:"2025-12-31"},{trainEnd:"2025-12-31",oosStart:"2026-01-01",oosEnd:"2026-08-25"}];
 const full=sims.map(s=>({variant:s.variant,gross:performanceStats(s.curve),afterTax:performanceStats(s.afterTaxCurve),sales:s.tax.sales,turnover:s.tax.turnover,taxPaidApprox:s.tax.taxes,monthlySwitches:s.monthlySwitches}));
 const wf=splits.map(sp=>({split:`through ${sp.trainEnd} -> ${sp.oosStart.slice(0,4)}`,rows:sims.map(s=>{const g=sliceCurve(s.curve,sp.oosStart,sp.oosEnd),a=sliceCurve(s.afterTaxCurve,sp.oosStart,sp.oosEnd);return{variant:s.variant,gross:performanceStats(g),afterTax:performanceStats(a)}})}));
 const output={generatedAt:new Date().toISOString(),validity:{researchOnly:true,trueOOS:false,architectureHindsightRemains:true,variantsPredeclared:["H3","H4","TAX_H4","TAX_H5"],warning:"This is a comparative historical diagnostic. Tax ledger approximates realized gains from full-position exits/rebalances; exact Japanese tax-lot accounting and intra-year withholding timing are not modeled."},rules:{H3:"retain incumbent while eligible rank<=3",H4:"retain incumbent while eligible rank<=4",TAX_H4:"if incumbent unrealized gain>0 retain rank<=4, else rank<=3",TAX_H5:"if incumbent unrealized gain>0 retain rank<=5, else rank<=3",unchanged:"market gate, stop, circuit, recovery, momentum signal, universe, transaction cost"},full,wf};const dir=path.join(process.cwd(),"data/research/tax-aware-hysteresis");await fs.mkdir(dir,{recursive:true});await fs.writeFile(path.join(dir,"result.json"),JSON.stringify(output,null,2));console.log(JSON.stringify(output,null,2));}
main().catch(e=>{console.error(e);process.exit(1)});
