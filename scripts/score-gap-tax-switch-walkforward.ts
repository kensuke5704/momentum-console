import fs from "node:fs/promises";
import path from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import { initialEngineState, transitionDay, type EngineState } from "../src/lib/strategy/state-machine";
import { nextUsTradingSession } from "../src/lib/trading-calendar";
import { performanceStats } from "../src/lib/backtest";
import type { EquityPoint, MonthlySignal, PricePoint, UniverseMonth } from "../src/lib/types";

const TAX=0.20315;
type Variant={id:string;baseGap:number;taxAware:boolean;skipUnchanged:boolean};
const VARIANTS:Variant[]=[
 {id:"PRODUCTION",baseGap:0,taxAware:false,skipUnchanged:false},
 {id:"NO_CHURN",baseGap:0,taxAware:false,skipUnchanged:true},
 {id:"SG5",baseGap:0.05,taxAware:false,skipUnchanged:true},
 {id:"SG10",baseGap:0.10,taxAware:false,skipUnchanged:true},
 {id:"TAX_SG",baseGap:0.05,taxAware:true,skipUnchanged:true},
];
type TaxLedger={gain:Record<string,number>;loss:Record<string,number>;sales:number;turnover:number;taxes:number;skipped:number;retentions:number};
type Sim={variant:string;curve:EquityPoint[];afterTaxCurve:EquityPoint[];tax:TaxLedger};
function cand(s:MonthlySignal,symbol:string){return s.candidates.find(c=>c.symbol===symbol)}
function taxFriction(gain:number){return gain>0?TAX*gain/(1+gain):0}
function sameSet(a:string[],b:string[]){return [...a].sort().join("|") === [...b].sort().join("|")}
function adjustSignal(base:MonthlySignal,state:EngineState,v:Variant,l:TaxLedger):MonthlySignal{
 if(v.id==="PRODUCTION"||v.id==="NO_CHURN"||state.state!=="INVESTED"||state.currentPositions.length!==2||!base.marketRiskOn||base.selectedSymbols.length!==2)return base;
 const selected=[...base.selectedSymbols]; const current=new Set(state.currentPositions.map(p=>p.symbol)); const chosen=[...selected];
 for(const p of state.currentPositions){
   if(chosen.includes(p.symbol))continue; const ic=cand(base,p.symbol); if(!ic?.eligible||ic.rank==null||ic.rank>5||ic.score==null)continue;
   const newcomerIdx=chosen.map((s,i)=>({s,i,c:cand(base,s)})).filter(x=>!current.has(x.s)&&x.c?.score!=null).sort((a,b)=>(a.c!.score!)-(b.c!.score!))[0]; if(!newcomerIdx)continue;
   const gain=(p.currentPrice??p.entryPrice)/p.entryPrice-1; const hurdle=v.baseGap+(v.taxAware?taxFriction(gain):0); const advantage=newcomerIdx.c!.score!-ic.score;
   if(advantage<hurdle){chosen[newcomerIdx.i]=p.symbol;l.retentions++;}
 }
 const unique=[...new Set(chosen)]; if(unique.length!==2)return base; unique.sort((a,b)=>(cand(base,a)?.rank??999)-(cand(base,b)?.rank??999));
 if(sameSet(unique,base.selectedSymbols))return base; const sameTop=unique[0]===base.selectedSymbols[0]; const w=sameTop&&base.targetWeights[0]>0.5?[base.targetWeights[0],1-base.targetWeights[0]]:[0.5,0.5];
 return {...base,selectedSymbols:unique,targetWeights:w,allocationMode:w[0]>0.5?"70/30":"50/50"};
}
function applyTaxes(curve:EquityPoint[],l:TaxLedger){if(!curve.length)return[];const years=[...new Set(curve.map(p=>p.date.slice(0,4)))];const ty:Record<string,number>={};let carry:{y:number,a:number}[]=[];for(const ys of years){const y=+ys;carry=carry.filter(x=>y-x.y<=3);let net=(l.gain[ys]??0)-(l.loss[ys]??0);if(net>0){for(const x of carry){const u=Math.min(net,x.a);net-=u;x.a-=u;if(net<=0)break}carry=carry.filter(x=>x.a>1e-12);ty[ys]=net*TAX}else if(net<0)carry.push({y,a:-net})}l.taxes=Object.values(ty).reduce((a,b)=>a+b,0);let e=curve[0].equity,pg=curve[0].equity,peak=e;const out:EquityPoint[]=[];for(let i=0;i<curve.length;i++){const p=curve[i];if(i)e*=p.equity/pg;pg=p.equity;const n=curve[i+1];if((!n||n.date.slice(0,4)!==p.date.slice(0,4))&&(ty[p.date.slice(0,4)]??0)>0)e=Math.max(0,e-(ty[p.date.slice(0,4)]??0)*(e/Math.max(p.equity,1e-12)));peak=Math.max(peak,e);out.push({date:p.date,equity:e,drawdown:e/peak-1})}return out}
function simulate(hist:Record<string,PricePoint[]>,universe:UniverseMonth[],v:Variant):Sim{const qqq=[...(hist.QQQ??[])].sort((a,b)=>a.date.localeCompare(b.date));const dates=qqq.map(p=>p.date),idx=new Map(dates.map((d,i)=>[d,i]));const pm=Object.fromEntries(Object.entries(hist).map(([s,ps])=>[s,new Map(ps.map(p=>[p.date,p]))]));const um=new Map(universe.map(u=>[u.asOf,u]));let state=initialEngineState(PRODUCTION_STRATEGY);const curve:EquityPoint[]=[];const tax:TaxLedger={gain:{},loss:{},sales:0,turnover:0,taxes:0,skipped:0,retentions:0};
 for(let i=0;i<dates.length;i++){const date=dates[i];if(date<PRODUCTION_STRATEGY.backtestStart)continue;const next=dates[i+1]??nextUsTradingSession(date),u=um.get(date);let sig=u?buildMonthlySignal({universe:u,histories:hist,qqq,nextSessionDate:next,config:PRODUCTION_STRATEGY}):null;if(sig)sig=adjustSignal(sig,state,v,tax);
   const execToday=state.nextAction.executionDate===date; const execType=state.nextAction.type; const before=structuredClone(state.currentPositions); const sy=new Set(["QQQ",...state.currentPositions.map(p=>p.symbol),...(state.pendingSignal?.selectedSymbols??[]),...state.nextAction.symbols,...(sig?.selectedSymbols??[])]);const prices=Object.fromEntries([...sy].map(s=>[s,pm[s]?.get(date)]));
   if(execToday&&(execType==="SELL_ALL_NEXT_OPEN"||execType==="MONTH_END_REBALANCE_NEXT_OPEN")){for(const p of before){const px=prices[p.symbol]?.open??prices[p.symbol]?.close??p.currentPrice??p.entryPrice;const proceeds=p.shares*px*(1-PRODUCTION_STRATEGY.execution.transactionCost),basis=p.shares*p.entryPrice,pnl=proceeds-basis,y=date.slice(0,4);if(pnl>=0)tax.gain[y]=(tax.gain[y]??0)+pnl;else tax.loss[y]=(tax.loss[y]??0)-pnl;tax.sales++;tax.turnover+=proceeds}}
   state=transitionDay(state,{date,prices,qqqHistoryThroughClose:qqq.slice(0,(idx.get(date)??i)+1),monthlySignal:sig,nextSessionDate:next},PRODUCTION_STRATEGY);
   if(v.skipUnchanged&&sig&&state.state==="INVESTED"&&state.nextAction.type==="MONTH_END_REBALANCE_NEXT_OPEN"&&sameSet(state.currentPositions.map(p=>p.symbol),sig.selectedSymbols)){state.nextAction={type:"HOLD",executionDate:null,symbols:state.currentPositions.map(p=>p.symbol),targetWeights:state.currentPositions.map(p=>p.targetWeight),reason:"Research no-churn: unchanged selected ticker set"};tax.skipped++;}
   curve.push({date,equity:state.currentEquity,drawdown:state.drawdown})}
 return{variant:v.id,curve,afterTaxCurve:applyTaxes(curve,tax),tax}}
function slice(c:EquityPoint[],s:string,e:string){const x=c.filter(p=>p.date>=s&&p.date<=e);if(!x.length)return[];const b=x[0].equity;return x.map(p=>({...p,equity:p.equity/b}))}
async function main(){const market=JSON.parse(await fs.readFile(path.join(process.cwd(),"public/data/market-data.json"),"utf8")) as {histories:Record<string,PricePoint[]>};const uf=JSON.parse(await fs.readFile(path.join(process.cwd(),"data/universe-history.json"),"utf8")) as {history:UniverseMonth[]};const universe=[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf));const sims=VARIANTS.map(v=>simulate(market.histories,universe,v));const years=[2022,2023,2024,2025,2026];const full=sims.map(s=>({variant:s.variant,gross:performanceStats(s.curve),afterTax:performanceStats(s.afterTaxCurve),sales:s.tax.sales,turnover:s.tax.turnover,taxPaidApprox:s.tax.taxes,skippedRebalances:s.tax.skipped,scoreGapRetentions:s.tax.retentions}));const oos=years.map(y=>({year:y,rows:sims.map(s=>{const end=y===2026?"2026-08-25":`${y}-12-31`;return{variant:s.variant,gross:performanceStats(slice(s.curve,`${y}-01-01`,end)),afterTax:performanceStats(slice(s.afterTaxCurve,`${y}-01-01`,end))}})}));const prod=full.find(x=>x.variant==="PRODUCTION")!;const summary=full.filter(x=>x.variant!=="PRODUCTION").map(x=>({variant:x.variant,fullGrossCagrDelta:x.gross.cagr-prod.gross.cagr,fullAfterTaxCagrDelta:x.afterTax.cagr-prod.afterTax.cagr,salesReduction:prod.sales-x.sales,oosAfterTaxWins:oos.filter(y=>(y.rows.find(r=>r.variant===x.variant)!.afterTax.cagr)>(y.rows.find(r=>r.variant==="PRODUCTION")!.afterTax.cagr)+1e-12).map(y=>y.year),oosAfterTaxLosses:oos.filter(y=>(y.rows.find(r=>r.variant===x.variant)!.afterTax.cagr)<(y.rows.find(r=>r.variant==="PRODUCTION")!.afterTax.cagr)-1e-12).map(y=>y.year)}));const output={generatedAt:new Date().toISOString(),validity:{researchOnly:true,trueOOS:false,architectureHindsightRemains:true,variantsPredeclared:["NO_CHURN","SG5","SG10","TAX_SG"],warning:"Historical comparative diagnostic. Thresholds are not evidence of unbiased forward performance. Tax accounting approximates annual realized P/L and 3-year loss carryforward; exact tax lots and withholding timing are omitted."},rules:{NO_CHURN:"Production Top2; skip monthly sell/rebuy when ticker set is unchanged.",SG5:"NO_CHURN + retain eligible incumbent rank<=5 if challenger momentum-score advantage <5 percentage points.",SG10:"same with 10 percentage points.",TAX_SG:"SG5 replacement hurdle + estimated tax friction on positive unrealized gain.",unchanged:"Universe, momentum weights, Top2 entry, market gate, stop, circuit, recovery, transaction cost."},full,oos,summary};const dir=path.join(process.cwd(),"data/research/score-gap-tax-switch");await fs.mkdir(dir,{recursive:true});await fs.writeFile(path.join(dir,"result.json"),JSON.stringify(output,null,2));console.log(JSON.stringify(output,null,2))}
main().catch(e=>{console.error(e);process.exit(1)});
