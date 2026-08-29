import fs from "node:fs/promises";
import path from "node:path";
import { runBacktest } from "../src/lib/backtest";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import type { EquityPoint, PricePoint, StrategyConfig, UniverseMonth } from "../src/lib/types";

type MarketData = { histories?: Record<string, PricePoint[]>; [key: string]: unknown };
type Metrics = { start:string|null; end:string|null; days:number; totalReturn:number; cagr:number; maxDD:number; calmar:number|null };

function extractHistories(raw: MarketData): Record<string, PricePoint[]> {
  if (raw.histories && typeof raw.histories === "object") return raw.histories;
  const out: Record<string, PricePoint[]> = {};
  for (const [key,value] of Object.entries(raw)) if (Array.isArray(value) && value.length && typeof value[0] === "object" && "date" in value[0]) out[key]=value as PricePoint[];
  return out;
}
function metrics(curve: EquityPoint[], start:string, end:string): Metrics {
  const rows=curve.filter(p=>p.date>=start&&p.date<=end);
  if(rows.length<2)return{start:rows[0]?.date??null,end:rows.at(-1)?.date??null,days:rows.length,totalReturn:0,cagr:0,maxDD:0,calmar:null};
  const first=rows[0],last=rows.at(-1)!;
  const years=Math.max(1/365.25,(Date.parse(last.date)-Date.parse(first.date))/(365.25*86400000));
  const totalReturn=last.equity/first.equity-1,cagr=(last.equity/first.equity)**(1/years)-1;
  let peak=first.equity,maxDD=0; for(const r of rows){peak=Math.max(peak,r.equity);maxDD=Math.min(maxDD,r.equity/peak-1)}
  return{start:first.date,end:last.date,days:rows.length,totalReturn,cagr,maxDD,calmar:maxDD<-1e-12?cagr/Math.abs(maxDD):null};
}
function quantile(v:number[],q:number){const x=v.filter(Number.isFinite).sort((a,b)=>a-b);if(!x.length)return null;const p=(x.length-1)*q,l=Math.floor(p),h=Math.ceil(p);return l===h?x[l]:x[l]*(h-p)+x[h]*(p-l)}
function mean(v:number[]){const x=v.filter(Number.isFinite);return x.length?x.reduce((a,b)=>a+b,0)/x.length:null}
function rankPercentile(v:number[],value:number){const x=v.filter(Number.isFinite).sort((a,b)=>a-b);if(x.length<=1)return 1;let n=0;for(const a of x)if(a<=value)n++;return(n-1)/(x.length-1)}

async function main(){
  const momentumWeights=[
    {oneMonth:0,threeMonth:.50,sixMonth:.50,label:"0/50/50"},
    {oneMonth:0,threeMonth:.25,sixMonth:.75,label:"0/25/75"},
    {oneMonth:0,threeMonth:0,sixMonth:1,label:"0/0/100"},
    {oneMonth:.20,threeMonth:.30,sixMonth:.50,label:"20/30/50"},
  ];
  const universeSizes=[40,60,80],maMonths=[8,10,12],stops=[.15,.175,.20],circuits=[.125,.15,.175],recoveryDays=[5,10,15];
  const marketRaw=JSON.parse(await fs.readFile(path.join(process.cwd(),"public/data/market-data.json"),"utf8")) as MarketData;
  const histories=extractHistories(marketRaw);
  const universeFile=JSON.parse(await fs.readFile(path.join(process.cwd(),"data/universe-history.json"),"utf8")) as {history:UniverseMonth[]};
  const universeHistoryRaw=[...universeFile.history].sort((a,b)=>a.asOf.localeCompare(b.asOf));
  const configs:Array<{id:string;config:StrategyConfig;universeSize:number}>=[];
  for(const mw of momentumWeights)for(const universeSize of universeSizes)for(const ma of maMonths)for(const stop of stops)for(const circuit of circuits)for(const recovery of recoveryDays){
    const id=`mw${mw.label}-u${universeSize}-ma${ma}-s${stop}-c${circuit}-r${recovery}`;
    configs.push({id,universeSize,config:{...PRODUCTION_STRATEGY,strategyId:`wf-${id}`,universe:{...PRODUCTION_STRATEGY.universe,size:universeSize},momentum:{...PRODUCTION_STRATEGY.momentum,oneMonth:mw.oneMonth,threeMonth:mw.threeMonth,sixMonth:mw.sixMonth},market:{...PRODUCTION_STRATEGY.market,qqqMonthlyMaMonths:ma},risk:{individualStop:stop,portfolioCircuit:circuit},recovery:{...PRODUCTION_STRATEGY.recovery,confirmationDays:recovery}}});
  }
  const universeCache=new Map<number,UniverseMonth[]>();for(const size of universeSizes)universeCache.set(size,universeHistoryRaw.map(m=>({...m,symbols:m.symbols.slice(0,size)})));
  const simulations:Array<{id:string;config:StrategyConfig;universeSize:number;curve:EquityPoint[]}>=[];
  for(let i=0;i<configs.length;i++){const item=configs[i];const result=runBacktest({histories,universeHistory:universeCache.get(item.universeSize)!,config:item.config});simulations.push({...item,curve:result.equityCurve});if((i+1)%100===0)console.log(`simulated ${i+1}/${configs.length}`)}
  const splits=[
    {trainEnd:"2021-12-31",oosStart:"2022-01-01",oosEnd:"2022-12-31",label:"2022"},
    {trainEnd:"2022-12-31",oosStart:"2023-01-01",oosEnd:"2023-12-31",label:"2023"},
    {trainEnd:"2023-12-31",oosStart:"2024-01-01",oosEnd:"2024-12-31",label:"2024"},
    {trainEnd:"2024-12-31",oosStart:"2025-01-01",oosEnd:"2025-12-31",label:"2025"},
    {trainEnd:"2025-12-31",oosStart:"2026-01-01",oosEnd:"2026-08-25",label:"2026-YTD"},
  ];
  const splitResults=[];
  for(const split of splits){
    const rows=simulations.map(s=>{const train=metrics(s.curve,"2020-01-01",split.trainEnd),oos=metrics(s.curve,split.oosStart,split.oosEnd);const trainScore=train.calmar!==null&&Number.isFinite(train.calmar)?train.calmar:-Infinity;return{id:s.id,config:s.config,train,oos,trainScore}});
    const ranked=[...rows].sort((a,b)=>b.trainScore-a.trainScore||b.train.cagr-a.train.cagr||a.id.localeCompare(b.id));const topCount=Math.max(1,Math.ceil(ranked.length*.10)),top=ranked.slice(0,topCount),best=ranked[0];
    const allR=rows.map(r=>r.oos.totalReturn),topR=top.map(r=>r.oos.totalReturn),allD=rows.map(r=>r.oos.maxDD),topD=top.map(r=>r.oos.maxDD),allMedian=quantile(allR,.5);
    splitResults.push({...split,candidateCount:rows.length,topDecileCount:topCount,bestTrain:{id:best.id,config:best.config,train:best.train,oos:best.oos,oosReturnPercentileAmongAllCandidates:rankPercentile(allR,best.oos.totalReturn)},allCandidatesOOS:{returnMedian:allMedian,returnP10:quantile(allR,.1),returnP90:quantile(allR,.9),maxDDMedian:quantile(allD,.5),maxDDP10:quantile(allD,.1),maxDDP90:quantile(allD,.9)},topTrainDecileOOS:{returnMean:mean(topR),returnMedian:quantile(topR,.5),returnP10:quantile(topR,.1),returnP90:quantile(topR,.9),maxDDMedian:quantile(topD,.5),maxDDP10:quantile(topD,.1),maxDDP90:quantile(topD,.9),fractionPositive:topR.filter(x=>x>0).length/topR.length,fractionAboveAllMedian:topR.filter(x=>x>(allMedian??Infinity)).length/topR.length},top10Ids:top.slice(0,10).map(r=>({id:r.id,trainScore:r.trainScore,trainCagr:r.train.cagr,trainMaxDD:r.train.maxDD,oosReturn:r.oos.totalReturn,oosMaxDD:r.oos.maxDD}))});
  }
  const output={generatedAt:new Date().toISOString(),test:"nested pseudo-OOS parameter-transfer walk-forward",validity:{futureOosReturnsUsedForSelection:false,pointInTimeUniverseData:true,architectureFixedWithHindsight:true,candidateGridDefinedAfterFullHistoryWasKnown:true,thereforeTrueHistoricalOOS:false,primaryInference:"Does training-period parameter strength transfer to the next calendar year within the fixed strategy architecture?",warning:"This reduces parameter-selection leakage but cannot remove architecture/feature-selection hindsight. 2022 also has only two training years, so early splits have high estimator variance."},fixedArchitecture:{topN:2,surgeLimit:PRODUCTION_STRATEGY.momentum.surgeLimit,requireAboveQqqScore:PRODUCTION_STRATEGY.momentum.requireAboveQqqScore,allocation:PRODUCTION_STRATEGY.allocation,qqqDailySmaDays:PRODUCTION_STRATEGY.recovery.qqqDailySmaDays,qqqMomentumDays:PRODUCTION_STRATEGY.recovery.qqqMomentumDays,transactionCost:PRODUCTION_STRATEGY.execution.transactionCost},grid:{momentumWeights,universeSizes,maMonths,stops,circuits,recoveryDays,candidateCount:configs.length},selector:"Training Calmar; evaluate both single best and top training decile. Primary robustness result is top-decile transfer, not the single winner.",splits:splitResults};
  const outDir=path.join(process.cwd(),"data/research/walkforward-parameter-transfer");await fs.mkdir(outDir,{recursive:true});await fs.writeFile(path.join(outDir,"result.json"),JSON.stringify(output,null,2));
  console.log(JSON.stringify({candidateCount:configs.length,splits:splitResults.map(s=>({label:s.label,best:s.bestTrain.id,bestOos:s.bestTrain.oos.totalReturn,bestPct:s.bestTrain.oosReturnPercentileAmongAllCandidates,topMedian:s.topTrainDecileOOS.returnMedian,allMedian:s.allCandidatesOOS.returnMedian,topAboveAll:s.topTrainDecileOOS.fractionAboveAllMedian}))},null,2));
}
main().catch(e=>{console.error(e);process.exit(1)});
