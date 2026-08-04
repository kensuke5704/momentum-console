import { mkdir, writeFile } from "node:fs/promises";
import { buildDashboard } from "../src/lib/momentum";
import { DEFAULT_STRATEGY, TICKERS } from "../src/lib/config";
import { fetchHistories } from "../src/lib/yahoo";
import type { BacktestRow, StrategyConfig } from "../src/lib/types";

type Stats = { finalEquity:number; cagr:number; annualizedVolatility:number; maxDrawdown:number; calmar:number; months:number };

function cloneStrategy(): StrategyConfig {
  return { ...DEFAULT_STRATEGY, weights:{...DEFAULT_STRATEGY.weights}, frontierGenres:[...DEFAULT_STRATEGY.frontierGenres], excludedTickers:[...DEFAULT_STRATEGY.excludedTickers] };
}
function mean(v:number[]){return v.length?v.reduce((a,b)=>a+b,0)/v.length:0}
function stdev(v:number[]){if(v.length<=1)return 0;const m=mean(v);return Math.sqrt(v.reduce((s,x)=>s+(x-m)**2,0)/(v.length-1))}
function stats(returns:number[]):Stats{
  if(!returns.length)return{finalEquity:1,cagr:0,annualizedVolatility:0,maxDrawdown:0,calmar:0,months:0};
  let eq=1,peak=1,dd=0;for(const r of returns){eq*=1+r;peak=Math.max(peak,eq);dd=Math.min(dd,eq/peak-1)}
  const cagr=eq**(12/returns.length)-1;return{finalEquity:eq,cagr,annualizedVolatility:stdev(returns)*Math.sqrt(12),maxDrawdown:dd,calmar:dd<0?cagr/Math.abs(dd):Infinity,months:returns.length};
}
function completed(rows:BacktestRow[]){return rows.filter(r=>typeof r.monthlyReturn==="number"&&!r.provisional)}
function returns(rows:BacktestRow[],scale=1){return completed(rows).map(r=>(r.monthlyReturn as number)*scale)}
function yearStats(rows:BacktestRow[],scale=1){return Object.fromEntries(["2023","2024","2025","2026"].map(y=>[y,stats(completed(rows).filter(r=>r.signalMonth.startsWith(y)).map(r=>(r.monthlyReturn as number)*scale))]))}
function halfStats(rows:BacktestRow[],scale=1){return{first:stats(completed(rows).filter(r=>r.signalMonth<"2025-01-01").map(r=>(r.monthlyReturn as number)*scale)),second:stats(completed(rows).filter(r=>r.signalMonth>="2025-01-01").map(r=>(r.monthlyReturn as number)*scale))}}

function mulberry32(seed:number){return()=>{let t=seed+=0x6D2B79F5;t=Math.imul(t^t>>>15,t|1);t^=t+Math.imul(t^t>>>7,t|61);return((t^t>>>14)>>>0)/4294967296}}
function blockBootstrap(base:number[],alt:number[],iterations=10000,block=3){
  const diffs=alt.map((r,i)=>Math.log1p(r)-Math.log1p(base[i]));
  const n=diffs.length;const rng=mulberry32(20260804);const samples:number[]=[];
  for(let k=0;k<iterations;k++){
    let total=0,count=0;
    while(count<n){const start=Math.floor(rng()*n);for(let j=0;j<block&&count<n;j++,count++){total+=diffs[(start+j)%n]}}
    samples.push(total);
  }
  samples.sort((a,b)=>a-b);
  const q=(p:number)=>samples[Math.floor((samples.length-1)*p)];
  return{iterations,block,probabilityOutperform:samples.filter(x=>x>0).length/samples.length,logAdvantageP05:q(.05),logAdvantageMedian:q(.5),logAdvantageP95:q(.95),observedLogAdvantage:diffs.reduce((a,b)=>a+b,0)};
}
function compare(name:string,baseRows:BacktestRow[],altRows:BacktestRow[],scale=1){
  const b=completed(baseRows);const a=completed(altRows);const map=new Map(a.map(r=>[r.signalMonth,r]));
  const aligned=b.map(r=>({month:r.signalMonth,base:r.monthlyReturn as number,alt:((map.get(r.signalMonth)?.monthlyReturn as number)??0)*scale}));
  const logDeltas=aligned.map(x=>({...x,logDelta:Math.log1p(x.alt)-Math.log1p(x.base),delta:x.alt-x.base}));
  const sorted=[...logDeltas].sort((x,y)=>y.logDelta-x.logDelta);
  const total=logDeltas.reduce((s,x)=>s+x.logDelta,0);const positive=logDeltas.filter(x=>x.logDelta>0).sort((x,y)=>y.logDelta-x.logDelta);
  const top3=positive.slice(0,3).reduce((s,x)=>s+x.logDelta,0);
  let rollingWins=0,rollingTotal=0;
  for(let i=0;i+12<=aligned.length;i++){const w=aligned.slice(i,i+12);const be=w.reduce((e,x)=>e*(1+x.base),1);const ae=w.reduce((e,x)=>e*(1+x.alt),1);rollingTotal++;if(ae>be)rollingWins++}
  return{name,scale,stats:stats(aligned.map(x=>x.alt)),yearly:yearStats(altRows,scale),halves:halfStats(altRows,scale),monthly:{wins:logDeltas.filter(x=>x.logDelta>0).length,losses:logDeltas.filter(x=>x.logDelta<0).length,ties:logDeltas.filter(x=>x.logDelta===0).length,top5:sorted.slice(0,5),bottom5:sorted.slice(-5),top3PositiveShare:total>0?top3/total:null,rolling12Wins:rollingWins,rolling12Total:rollingTotal,rolling12WinRate:rollingTotal?rollingWins/rollingTotal:0},bootstrap:blockBootstrap(aligned.map(x=>x.base),aligned.map(x=>x.alt))};
}

async function main(){
  const histories=await fetchHistories(TICKERS.map(t=>t.symbol));
  const baselineStrategy=cloneStrategy();
  const baseline=buildDashboard(histories,TICKERS,baselineStrategy);
  const s9=cloneStrategy();s9.topN=9;const d9=buildDashboard(histories,TICKERS,s9);
  const w145=cloneStrategy();w145.topN=9;w145.weights={oneMonth:.1,threeMonth:.4,sixMonth:.5};const d145=buildDashboard(histories,TICKERS,w145);
  const w145s90=cloneStrategy();w145s90.topN=9;w145s90.weights={oneMonth:.1,threeMonth:.4,sixMonth:.5};w145s90.surgeLimit=.9;const d145s90=buildDashboard(histories,TICKERS,w145s90);
  const baselineSummary={stats:stats(returns(baseline.backtest.rows)),yearly:yearStats(baseline.backtest.rows),halves:halfStats(baseline.backtest.rows),insufficientMonths:baseline.backtest.rows.filter(r=>r.market==="Not enough candidates").length};
  const comparisons=[
    compare("TopN9 equal weight (11.11% each)",baseline.backtest.rows,d9.backtest.rows,1),
    compare("TopN9 fixed 10% each + 10% cash",baseline.backtest.rows,d9.backtest.rows,.9),
    compare("TopN9 W10/40/50 S80 equal weight",baseline.backtest.rows,d145.backtest.rows,1),
    compare("TopN9 W10/40/50 S80 fixed10 + cash",baseline.backtest.rows,d145.backtest.rows,.9),
    compare("TopN9 W10/40/50 S90 equal weight",baseline.backtest.rows,d145s90.backtest.rows,1),
    compare("TopN9 W10/40/50 S90 fixed10 + cash",baseline.backtest.rows,d145s90.backtest.rows,.9),
  ];
  const result={generatedAt:new Date().toISOString(),source:"Yahoo fetchHistories + buildDashboard; fixed10 mode only scales TopN9 portfolio return to 90% invested / 10% cash",baselineStrategy,baseline:baselineSummary,comparisons};
  await mkdir("artifacts",{recursive:true});await writeFile("artifacts/topn-robustness.json",JSON.stringify(result,null,2));
  console.log("TOPN_ROBUSTNESS",JSON.stringify(comparisons.map(c=>({name:c.name,cagr:c.stats.cagr,dd:c.stats.maxDrawdown,vol:c.stats.annualizedVolatility,calmar:c.stats.calmar,years:Object.fromEntries(Object.entries(c.yearly).map(([y,s])=>[y,s.finalEquity-1])),h1:c.halves.first.cagr,h2:c.halves.second.cagr,monthly:c.monthly,bootstrap:c.bootstrap}))));
}
main().catch(e=>{console.error(e);process.exit(1)});
