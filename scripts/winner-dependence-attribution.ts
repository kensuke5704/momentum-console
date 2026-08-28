import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import { initialEngineState, transitionDay } from "../src/lib/strategy/state-machine";
import type { PricePoint, UniverseMonth } from "../src/lib/types";

type Market = { histories: Record<string, PricePoint[]> };
type UniverseFile = { history: UniverseMonth[] };
type Attr = { contribution: number; transactionCost: number; marketPnl: number; holdingDays: number; entries: number };

const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as Market;
const uf = JSON.parse(await readFile(resolve("data/universe-history.json"), "utf8")) as UniverseFile;
const config = PRODUCTION_STRATEGY;
const qqq = [...(market.histories.QQQ ?? [])].sort((a,b)=>a.date.localeCompare(b.date));
const tradingDates = qqq.map(p=>p.date);
const dateIndex = new Map(tradingDates.map((d,i)=>[d,i]));
const priceMaps = Object.fromEntries(Object.entries(market.histories).map(([s,pts])=>[s,new Map(pts.map(p=>[p.date,p]))]));
const universeBySignalDate = new Map(uf.history.map(m=>[m.asOf,m]));
const attrs = new Map<string,Attr>();
const entrySignals:any[]=[];
const getAttr=(s:string)=>{let x=attrs.get(s);if(!x){x={contribution:0,transactionCost:0,marketPnl:0,holdingDays:0,entries:0};attrs.set(s,x)}return x};
const price=(s:string,d:string)=>priceMaps[s]?.get(d) as PricePoint|undefined;
const add=(s:string,marketPnl:number,cost=0)=>{const a=getAttr(s);a.marketPnl+=marketPnl;a.transactionCost+=cost;a.contribution+=marketPnl-cost};

let state=initialEngineState(config);
let priorEquity=1;
for(let index=0; index<tradingDates.length; index++){
  const date=tradingDates[index];
  if(date<config.backtestStart) continue;
  const nextSessionDate=tradingDates[index+1]??null;
  const universe=universeBySignalDate.get(date);
  const signal=universe?buildMonthlySignal({universe,histories:market.histories,qqq,nextSessionDate,config}):null;
  const symbols=new Set(["QQQ",...state.currentPositions.map(p=>p.symbol),...(state.pendingSignal?.selectedSymbols??[]),...state.nextAction.symbols,...(signal?.selectedSymbols??[])]);
  const prices=Object.fromEntries([...symbols].map(s=>[s,price(s,date)]));
  const before=structuredClone(state);
  const actionExec = before.nextAction.executionDate===date ? before.nextAction.type : null;

  // Overnight mark-to-open for positions carried from the prior close.
  for(const p of before.currentPositions){
    const pp=prices[p.symbol];
    if(!pp) continue;
    const prevClose=p.currentPrice??p.entryPrice;
    add(p.symbol,p.shares*(pp.open-prevClose));
  }

  // Sell-side cost when an exit or rebalance executes at the open.
  if(actionExec==="SELL_ALL_NEXT_OPEN" || actionExec==="MONTH_END_REBALANCE_NEXT_OPEN"){
    for(const p of before.currentPositions){
      const pp=prices[p.symbol]; if(!pp) continue;
      add(p.symbol,0,p.shares*pp.open*config.execution.transactionCost);
    }
  }

  state=transitionDay(state,{date,prices,qqqHistoryThroughClose:qqq.slice(0,(dateIndex.get(date)??index)+1),monthlySignal:signal,nextSessionDate},config);

  // Detect new open positions and assign buy-side transaction cost.
  if(actionExec==="BUY_NEXT_OPEN" || actionExec==="MONTH_END_REBALANCE_NEXT_OPEN"){
    for(const p of state.currentPositions){
      const pp=prices[p.symbol]; if(!pp) continue;
      const invested=p.shares*pp.open;
      const grossAllocation=invested/(1-config.execution.transactionCost);
      const cost=grossAllocation-invested;
      add(p.symbol,0,cost);
      const a=getAttr(p.symbol); a.entries++;
      const sig=before.pendingSignal;
      const c=sig?.candidates.find(x=>x.symbol===p.symbol);
      entrySignals.push({date,symbol:p.symbol,targetWeight:p.targetWeight,rank:c?.rank??null,oneMonth:c?.oneMonth??null,threeMonth:c?.threeMonth??null,sixMonth:c?.sixMonth??null,score:c?.score??null,scoreSpread:c?.scoreSpread??null});
    }
  }

  // Intraday open-to-close PnL for positions held after open execution.
  for(const p of state.currentPositions){
    const pp=prices[p.symbol]; if(!pp) continue;
    add(p.symbol,p.shares*(pp.close-pp.open));
    getAttr(p.symbol).holdingDays++;
  }
  priorEquity=state.currentEquity;
}

const rows=[...attrs.entries()].map(([symbol,a])=>({symbol,...a})).sort((a,b)=>b.contribution-a.contribution);
const finalEquity=state.currentEquity;
const totalNetProfit=finalEquity-1;
const attributed=rows.reduce((s,x)=>s+x.contribution,0);
for(const row of rows) (row as any).shareOfNetProfit=totalNetProfit!==0?row.contribution/totalNetProfit:null;
const positive=rows.filter(x=>x.contribution>0);
const positiveTotal=positive.reduce((s,x)=>s+x.contribution,0);
const concentration=(n:number)=>({n,netProfitShare:totalNetProfit!==0?rows.slice(0,n).reduce((s,x)=>s+x.contribution,0)/totalNetProfit:null,positiveProfitShare:positiveTotal!==0?rows.slice(0,n).filter(x=>x.contribution>0).reduce((s,x)=>s+x.contribution,0)/positiveTotal:null});
const result={generatedAt:new Date().toISOString(),strategyId:config.strategyId,period:{start:config.backtestStart,end:state.asOf},finalEquity,totalNetProfit,attributedContribution:attributed,reconciliationError:attributed-totalNetProfit,concentration:[1,3,5,10].map(concentration),contributors:rows,entrySignals};
await mkdir(resolve("data/research/winner-dependence"),{recursive:true});
await writeFile(resolve("data/research/winner-dependence/attribution.json"),JSON.stringify(result,null,2)+"\n");
const pct=(x:number|null)=>x==null?"n/a":`${(x*100).toFixed(2)}%`;
let md=`# Winner dependence attribution\n\nStrategy: **${config.strategyId}**  \nPeriod: **${config.backtestStart} → ${state.asOf}**  \nFinal equity: **${finalEquity.toFixed(4)}x**  \nNet profit: **${totalNetProfit.toFixed(4)}**  \nAttribution reconciliation error: **${(attributed-totalNetProfit).toExponential(3)}**\n\n`;
md+=`| Top contributors | Share of net strategy profit | Share of positive symbol profit |\n|---|---:|---:|\n`;
for(const c of result.concentration) md+=`| Top ${c.n} | ${pct(c.netProfitShare)} | ${pct(c.positiveProfitShare)} |\n`;
md+=`\n## Contributors\n\n| Rank | Symbol | Net contribution | Share of net profit | Market PnL | Costs | Holding days | Entries |\n|---:|---|---:|---:|---:|---:|---:|---:|\n`;
rows.forEach((r,i)=>{md+=`| ${i+1} | ${r.symbol} | ${r.contribution.toFixed(4)} | ${pct((r as any).shareOfNetProfit)} | ${r.marketPnl.toFixed(4)} | ${r.transactionCost.toFixed(4)} | ${r.holdingDays} | ${r.entries} |\n`});
md+=`\n## Method\n\n- Replays the frozen Production strategy with the actual PIT dynamic universe and Production state machine.\n- Symbol attribution includes overnight close-to-open PnL, open-to-close PnL, and buy/sell transaction costs allocated to the traded symbol.\n- The reconciliation error must be near zero before concentration ratios are accepted.\n- Concentration is diagnostic only; it does not alter or optimize the strategy.\n`;
await writeFile(resolve("data/research/winner-dependence/attribution.md"),md);
console.log(md);
console.log("RESULT_JSON="+JSON.stringify(result));
