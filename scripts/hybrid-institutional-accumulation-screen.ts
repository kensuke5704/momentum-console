import fs from "node:fs/promises";
import path from "node:path";
import { gunzipSync } from "node:zlib";
import { PRODUCTION_STRATEGY as BASE } from "../src/lib/config";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import { initialEngineState, transitionDay } from "../src/lib/strategy/state-machine";
import { nextUsTradingSession } from "../src/lib/trading-calendar";
import { performanceStats } from "../src/lib/backtest";
import type { EquityPoint, NportFiling, PricePoint, UniverseMonth } from "../src/lib/types";

const CONFIG:any={...BASE,strategyId:"momentum-hybrid-60-70-institutional-accumulation-screen",allocation:{...BASE.allocation,baseTop1Weight:.60,concentratedTop1Weight:.70,concentrationZGap:.25,maxTop1Weight:.70}};
type Factor="BASE"|"BUY_BREADTH"|"MEAN_WEIGHT_DELTA";
type Variant={id:string;factor:Factor;lambda:number};
const VARIANTS:Variant[]=[
 {id:"HYBRID_BASE",factor:"BASE",lambda:0},
 {id:"BUY_BREADTH_25",factor:"BUY_BREADTH",lambda:.25},{id:"BUY_BREADTH_50",factor:"BUY_BREADTH",lambda:.50},
 {id:"MEAN_WEIGHT_DELTA_25",factor:"MEAN_WEIGHT_DELTA",lambda:.25},{id:"MEAN_WEIGHT_DELTA_50",factor:"MEAN_WEIGHT_DELTA",lambda:.50},
];
const mean=(x:number[])=>x.length?x.reduce((a,b)=>a+b,0)/x.length:0;
const sd=(x:number[])=>{if(x.length<2)return 0;const m=mean(x);return Math.sqrt(x.reduce((s,v)=>s+(v-m)**2,0)/x.length)};
const z=(v:number,m:number,s:number)=>s>1e-12?(v-m)/s:0;

type ReportGroup={reportDate:string;versions:NportFiling[]};
type SeriesReports={seriesId:string;reports:ReportGroup[]};
type Accum={up:number;down:number;flat:number;sumDelta:number;comparable:number};
type FactorRow={buyBreadth:number;meanWeightDelta:number;comparableSeries:number};

function buildSeriesReports(filings:NportFiling[]):SeriesReports[]{
 const bySeries=new Map<string,Map<string,NportFiling[]>>();
 for(const f of filings){let byReport=bySeries.get(f.seriesId);if(!byReport){byReport=new Map();bySeries.set(f.seriesId,byReport);}let vs=byReport.get(f.reportDate);if(!vs){vs=[];byReport.set(f.reportDate,vs);}vs.push(f);}
 return [...bySeries.entries()].map(([seriesId,byReport])=>({seriesId,reports:[...byReport.entries()].map(([reportDate,versions])=>({reportDate,versions:versions.sort((a,b)=>a.filingDate.localeCompare(b.filingDate)||a.accession.localeCompare(b.accession))})).sort((a,b)=>a.reportDate.localeCompare(b.reportDate))}));
}
function latestVersion(g:ReportGroup,asOf:string){const eligible=g.versions.filter(f=>f.filingDate<=asOf);return eligible.at(-1)??null;}
function latestTwo(sr:SeriesReports,asOf:string):[NportFiling,NportFiling]|null{
 const eligible:{g:ReportGroup;f:NportFiling}[]=[];
 for(const g of sr.reports){if(g.reportDate>asOf)break;const f=latestVersion(g,asOf);if(f)eligible.push({g,f});}
 if(eligible.length<2)return null;return [eligible.at(-1)!.f,eligible.at(-2)!.f];
}
function relevantWeights(f:NportFiling,symbols:Set<string>){const m=new Map<string,number>();for(const h of f.holdings??[]){if(symbols.has(h.symbol))m.set(h.symbol,Number(h.weight)||0);}return m;}
function buildFactorMaps(universe:UniverseMonth[],filings:NportFiling[]){
 const series=buildSeriesReports(filings);const result=new Map<string,Map<string,FactorRow>>();
 for(const u of universe){const symbols=new Set(u.symbols.map(x=>x.symbol));const acc=new Map<string,Accum>();for(const s of symbols)acc.set(s,{up:0,down:0,flat:0,sumDelta:0,comparable:0});
  for(const sr of series){const pair=latestTwo(sr,u.asOf);if(!pair)continue;const [cur,prev]=pair;const cm=relevantWeights(cur,symbols),pm=relevantWeights(prev,symbols);const union=new Set([...cm.keys(),...pm.keys()]);for(const sym of union){const d=(cm.get(sym)??0)-(pm.get(sym)??0);const a=acc.get(sym)!;a.comparable++;a.sumDelta+=d;if(d>1e-9)a.up++;else if(d<-1e-9)a.down++;else a.flat++;}}
  const rows=new Map<string,FactorRow>();for(const [sym,a] of acc){rows.set(sym,{buyBreadth:a.comparable?(a.up-a.down)/a.comparable:0,meanWeightDelta:a.comparable?a.sumDelta/a.comparable:0,comparableSeries:a.comparable});}result.set(u.asOf,rows);
 }
 return result;
}
function customSignal(u:UniverseMonth,hist:Record<string,PricePoint[]>,qqq:PricePoint[],next:string,v:Variant,factors:Map<string,Map<string,FactorRow>>){
 const base:any=buildMonthlySignal({universe:u,histories:hist,qqq,nextSessionDate:next,config:CONFIG});if(v.factor==="BASE"||!base.marketRiskOn)return base;const eligible=base.candidates.filter((c:any)=>c.eligible&&c.score!==null);if(eligible.length<2)return base;const fm=factors.get(u.asOf);if(!fm)return base;
 const rows=eligible.map((c:any)=>{const r=fm.get(c.symbol);const fv=v.factor==="BUY_BREADTH"?r?.buyBreadth:r?.meanWeightDelta;return{c,fv,comparables:r?.comparableSeries??0};}).filter((x:any)=>x.fv!==undefined&&x.comparables>=2);if(rows.length<2)return base;
 const sm=mean(rows.map((x:any)=>x.c.score)),ss=sd(rows.map((x:any)=>x.c.score)),xm=mean(rows.map((x:any)=>x.fv)),xs=sd(rows.map((x:any)=>x.fv));if(xs<=1e-12)return base;const ranked=rows.map((x:any)=>({...x,combo:z(x.c.score,sm,ss)+v.lambda*z(x.fv,xm,xs)})).sort((a:any,b:any)=>b.combo-a.combo||a.c.symbol.localeCompare(b.c.symbol));const sel=ranked.slice(0,2);if(sel.length<2)return base;const combos=ranked.map((x:any)=>x.combo),disp=sd(combos),zg=disp>0?(sel[0].combo-sel[1].combo)/disp:0,conc=zg>=CONFIG.allocation.concentrationZGap,top1=conc?.70:.60;return{...base,selectedSymbols:sel.map((x:any)=>x.c.symbol),targetWeights:[top1,1-top1],zGap:zg,allocationMode:conc?"70/30":"60/40"};
}
function sim(hist:Record<string,PricePoint[]>,universe:UniverseMonth[],v:Variant,factors:Map<string,Map<string,FactorRow>>){const qqq=[...(hist.QQQ??[])].sort((a,b)=>a.date.localeCompare(b.date)),dates=qqq.map(p=>p.date),di=new Map(dates.map((d,i)=>[d,i])),pm=Object.fromEntries(Object.entries(hist).map(([s,ps])=>[s,new Map(ps.map(p=>[p.date,p]))])),um=new Map(universe.map(x=>[x.asOf,x]));let st=initialEngineState(CONFIG);const curve:EquityPoint[]=[];for(let i=0;i<dates.length;i++){const date=dates[i];if(date<CONFIG.backtestStart)continue;const next=dates[i+1]??nextUsTradingSession(date),u=um.get(date),sig=u?customSignal(u,hist,qqq,next,v,factors):null,sy=new Set(["QQQ",...st.currentPositions.map(p=>p.symbol),...(st.pendingSignal?.selectedSymbols??[]),...st.nextAction.symbols,...(sig?.selectedSymbols??[])]),prices=Object.fromEntries([...sy].map(s=>[s,pm[s]?.get(date)]));st=transitionDay(st,{date,prices,qqqHistoryThroughClose:qqq.slice(0,(di.get(date)??i)+1),monthlySignal:sig,nextSessionDate:next},CONFIG);curve.push({date,equity:st.currentEquity,drawdown:st.drawdown});}return curve;}
function normSlice(c:EquityPoint[],s:string,e:string){const x=c.filter(p=>p.date>=s&&p.date<=e);if(x.length<2)return[];const b=x[0].equity;return x.map(p=>({...p,equity:p.equity/b}));}
async function main(){
 const market=JSON.parse(await fs.readFile(path.join(process.cwd(),"public/data/market-data.json"),"utf8")) as {histories:Record<string,PricePoint[]>};const uf=JSON.parse(await fs.readFile(path.join(process.cwd(),"data/universe-history.json"),"utf8")) as {history:UniverseMonth[]};const universe=[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf));
 const raw=JSON.parse(gunzipSync(await fs.readFile(path.join(process.cwd(),"data/sec-nport/bootstrap.json.gz"))).toString("utf8")) as {snapshots:NportFiling[]};const filings=raw.snapshots;console.log("build factor maps",filings.length,universe.length);const factors=buildFactorMaps(universe,filings);
 const info=[...factors.entries()].map(([asOf,m])=>({asOf,covered:[...m.values()].filter(x=>x.comparableSeries>=2).length,maxComparable:Math.max(0,...[...m.values()].map(x=>x.comparableSeries))}));console.log("factor coverage",JSON.stringify({medianCovered:info.map(x=>x.covered).sort((a,b)=>a-b)[Math.floor(info.length/2)],minCovered:Math.min(...info.map(x=>x.covered)),maxCovered:Math.max(...info.map(x=>x.covered)),maxComparable:Math.max(...info.map(x=>x.maxComparable))}));
 const curves=new Map<string,EquityPoint[]>();for(const v of VARIANTS){console.log("run",v.id);curves.set(v.id,sim(market.histories,universe,v,factors));}
 const full=VARIANTS.map(v=>({variant:v,...performanceStats(curves.get(v.id)!)}));const splits=[] as any[];for(const y of [2022,2023,2024,2025,2026]){const trainEnd=`${y-1}-12-31`,oosEnd=y===2026?"2026-08-25":`${y}-12-31`;const train=VARIANTS.map(v=>({v,stats:performanceStats(normSlice(curves.get(v.id)!,"2020-01-01",trainEnd))})).sort((a,b)=>(b.stats.calmar??-Infinity)-(a.stats.calmar??-Infinity));const chosen=train[0].v;const base=performanceStats(normSlice(curves.get("HYBRID_BASE")!,`${y}-01-01`,oosEnd)),oos=performanceStats(normSlice(curves.get(chosen.id)!,`${y}-01-01`,oosEnd));splits.push({trainThrough:y-1,oosYear:y,chosen:chosen.id,trainCalmar:train[0].stats.calmar,oos,hybridBase:base,cagrDiff:oos.cagr-base.cagr});}
 const out={generatedAt:new Date().toISOString(),method:{baseline:"Hybrid 60/40; 70/30 when zGap>=0.25",pit:"For each signal close, only filings with filingDate<=asOf; within each series, latest filed version of latest two reportDates",factors:{BUY_BREADTH:"Among comparable series holding symbol in either latest or prior report: (count weight increased - count weight decreased)/comparable series",MEAN_WEIGHT_DELTA:"Mean percentage-point portfolio-weight change across comparable series"},blend:"cross-sectional z(Production momentum)+lambda*z(institutional factor)",lambdas:[.25,.50],minimumComparableSeries:2,selection:"training-only Calmar; next-calendar-year anchored pseudo-OOS"},validity:{trueOOS:false,architectureHindsightRemains:true,factorFamilyChosenAfterPriorDiagnostics:true,smallCandidateSet:true,rawNportSeriesLevel:true,warning:"Retrospective pseudo-OOS. N-PORT holdings weights are portfolio weights, not share-count flows; changes can reflect security price moves, subscriptions/redemptions, benchmark changes, and manager trades. The factor is an institutional-accumulation proxy, not direct net buying."},coverage:info,full,splits};const dir=path.join(process.cwd(),"data/research/hybrid-institutional-accumulation-screen");await fs.mkdir(dir,{recursive:true});await fs.writeFile(path.join(dir,"result.json"),JSON.stringify(out,null,2));console.log(JSON.stringify({full,splits},null,2));
}
main().catch(e=>{console.error(e);process.exit(1)});
