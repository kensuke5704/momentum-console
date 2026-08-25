import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { initialEngineState, transitionDay } from "../src/lib/strategy/state-machine";
import type { MonthlySignal, PricePoint, StrategyConfig, UniverseMonth } from "../src/lib/types";

type Market={histories:Record<string,PricePoint[]>}; type UF={history:UniverseMonth[]}; type Rng=()=>number;
const PATHS=Number(process.env.CPCM_SENS_PATHS??300), YEARS=5, H=YEARS*252, WARM=252, SEED=20260825;
const variants=[
 {label:"b10-r126",block:10,radius:126,mode:"actual-target"},
 {label:"b20-r126",block:20,radius:126,mode:"actual-target"},
 {label:"b40-r126",block:40,radius:126,mode:"actual-target"},
 {label:"b20-r63",block:20,radius:63,mode:"actual-target"},
 {label:"b20-r252",block:20,radius:252,mode:"actual-target"},
 {label:"b20-r126-synthetic",block:20,radius:126,mode:"synthetic-state"},
 {label:"b20-r126-unconditional",block:20,radius:126,mode:"unconditional-local"},
] as const;
const strategies=[
 {label:"production",cfg:PRODUCTION_STRATEGY as StrategyConfig},
 {label:"recovery5",cfg:{...PRODUCTION_STRATEGY,recovery:{...PRODUCTION_STRATEGY.recovery,confirmationDays:5}} as StrategyConfig},
];
const avg=(x:number[])=>x.length?x.reduce((a,b)=>a+b,0)/x.length:0;
const sd=(x:number[])=>{const m=avg(x);return x.length?Math.sqrt(avg(x.map(v=>(v-m)**2))):0};
const pct=(x:number[],p:number)=>{const a=[...x].sort((u,v)=>u-v),q=(a.length-1)*p,l=Math.floor(q),h=Math.ceil(q),w=q-l;return a[l]*(1-w)+a[h]*w};
function rng32(seed:number):Rng{let a=seed>>>0;return()=>{a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
function latestU(us:UniverseMonth[],d:string){let a=us[0];for(const u of us){if(u.asOf<=d)a=u;else break}return a}
const score=(r3:number,r6:number,cfg:StrategyConfig)=>cfg.momentum.threeMonth*r3+cfg.momentum.sixMonth*r6;
function makeSignal(date:string,next:string|null,u:UniverseMonth,monthly:Map<string,number[]>,cfg:StrategyConfig):MonthlySignal{
 const q=monthly.get("QQQ")??[],ret=(x:number[],n:number)=>x.length>n?x.at(-1)!/x.at(-(n+1))!-1:null,q1=ret(q,1),q3=ret(q,3),q6=ret(q,6),qs=q1==null||q3==null||q6==null?null:score(q3,q6,cfg),ma=q.slice(-cfg.market.qqqMonthlyMaMonths),risk=ma.length===cfg.market.qqqMonthlyMaMonths&&q.at(-1)!>avg(ma),c:any[]=[];
 for(const m of u.symbols){const x=monthly.get(m.symbol)??[],r1=ret(x,1),r3=ret(x,3),r6=ret(x,6);if(r1==null||r3==null||r6==null||qs==null){c.push({symbol:m.symbol,oneMonth:r1,threeMonth:r3,sixMonth:r6,score:null,qqqScore:qs,scoreSpread:null,eligible:false,exclusionReason:"INSUFFICIENT_PRICE_HISTORY",rank:null});continue}const s=score(r3,r6,cfg),reason=r1>=cfg.momentum.surgeLimit?"ONE_MONTH_SURGE":cfg.momentum.requireAboveQqqScore&&s<=qs?"NOT_ABOVE_QQQ":null;c.push({symbol:m.symbol,oneMonth:r1,threeMonth:r3,sixMonth:r6,score:s,qqqScore:qs,scoreSpread:s-qs,eligible:!reason,exclusionReason:reason,rank:null})}
 const e=c.filter(x=>x.eligible&&x.score!=null).sort((a,b)=>b.score-a.score||a.symbol.localeCompare(b.symbol));e.forEach((x,i)=>x.rank=i+1);const chosen=risk?e.slice(0,cfg.selection.topN):[],valid=chosen.length===cfg.selection.topN,d=sd(e.map(x=>x.score)),zg=valid&&d>0?(chosen[0].score-chosen[1].score)/d:valid?0:null,conc=zg!=null&&zg>=cfg.allocation.concentrationZGap,w=Math.min(cfg.allocation.maxTop1Weight,conc?cfg.allocation.concentratedTop1Weight:cfg.allocation.baseTop1Weight);
 return {strategyId:cfg.strategyId,signalMonth:date.slice(0,7),signalDate:date,executionDate:next,marketRiskOn:risk,qqqClose:q.at(-1)??null,qqqMonthlyMa:ma.length===cfg.market.qqqMonthlyMaMonths?avg(ma):null,qqqScore:qs,universe:u.symbols.map(x=>x.symbol),candidates:c,selectedSymbols:valid?chosen.map(x=>x.symbol):[],targetWeights:valid?[w,1-w]:[],zGap:zg,allocationMode:!valid?"CASH":conc?"70/30":"50/50"} as MonthlySignal;
}
function stateFeature(q:number[]){if(q.length<61)return null;const trend=q.at(-1)!/q.at(-61)!-1,r:number[]=[];for(let i=q.length-20;i<q.length;i++)r.push(q[i]/q[i-1]-1);return{trend,vol:sd(r)}}
function stats(curve:number[]){let peak=curve[0]??1,dd=0;for(const v of curve){peak=Math.max(peak,v);dd=Math.min(dd,v/peak-1)}return{cagr:(curve.at(-1)!/(curve[0]||1))**(1/YEARS)-1,dd,wealth:curve.at(-1)!/(curve[0]||1)}}
async function main(){
 const market=JSON.parse(await readFile(resolve("public/data/market-data.json"),"utf8")) as Market,uf=JSON.parse(await readFile(resolve("data/universe-history.json"),"utf8")) as UF,us=[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf)),hist=market.histories,dates=(hist.QQQ??[]).filter(p=>p.date>=us[0].asOf).map(p=>p.date),target=dates.slice(-(WARM+H)),symbols=[...new Set(["QQQ",...us.flatMap(u=>u.symbols.map(x=>x.symbol))])],maps=new Map(symbols.map(s=>[s,new Map((hist[s]??[]).map(p=>[p.date,p]))])),idx=new Map(dates.map((d,i)=>[d,i]));
 const qMap=new Map((hist.QQQ??[]).map(p=>[p.date,p])); const actualFeat=dates.map((_,i)=>{if(i<60)return null;const closes=dates.slice(i-60,i+1).map(d=>qMap.get(d)?.close).filter((x):x is number=>x!=null),rs:number[]=[];for(let j=i-19;j<=i;j++){const a=qMap.get(dates[j])?.close,b=qMap.get(dates[j-1])?.close;if(a&&b)rs.push(a/b-1)}return closes.length===61&&rs.length===20?{trend:closes.at(-1)!/closes[0]-1,vol:sd(rs)}:null});
 const output:any={generatedAt:new Date().toISOString(),paths:PATHS,years:YEARS,seed:SEED,variants:{}};
 for(let vi=0;vi<variants.length;vi++){
  const v=variants[vi],rng=rng32(SEED),rows:any[]=[];
  for(let p=0;p<PATHS;p++){
   const syn=new Map(symbols.map(s=>[s,100])),monthlyByStrat=new Map(strategies.map(s=>[s.label,new Map<string,number[]>(symbols.map(sym=>[sym,[]]))])),prices:Record<string,Record<string,PricePoint>>={},signalsByStrat=new Map(strategies.map(s=>[s.label,{} as Record<string,MonthlySignal>])),synQ:number[]=[];
   for(let ti=0;ti<target.length;){const td=target[ti],base=idx.get(td)!,baseF=actualFeat[base];let donor=base;
    if(v.mode==="unconditional-local"){const lo=Math.max(1,base-v.radius),hi=Math.min(dates.length-v.block-1,base+v.radius);donor=lo+Math.floor(rng()*(hi-lo+1));}
    else {const f=v.mode==="synthetic-state"?stateFeature(synQ):baseF;if(f){const cand:{k:number;dist:number}[]=[];for(let k=Math.max(61,base-v.radius);k<=Math.min(dates.length-v.block-1,base+v.radius);k++){const g=actualFeat[k];if(!g)continue;if(Math.sign(g.trend)!==Math.sign(f.trend)&&Math.abs(f.trend)>.03)continue;const dist=Math.abs(g.trend-f.trend)/.10+Math.abs(g.vol-f.vol)/.01;cand.push({k,dist})}cand.sort((a,b)=>a.dist-b.dist||a.k-b.k);const pool=cand.slice(0,20);if(pool.length)donor=pool[Math.floor(rng()*pool.length)].k;}}
    for(let j=0;j<v.block&&ti<target.length;j++,ti++){const d=target[ti],next=target[ti+1]??null,src=dates[Math.min(donor+j,dates.length-1)],srcPrev=dates[Math.max(0,Math.min(donor+j-1,dates.length-1))],targetPrev=ti>0?target[ti-1]:null,day:Record<string,PricePoint>={};for(const s of symbols){let a=maps.get(s)?.get(src),b=maps.get(s)?.get(srcPrev);if(!a||!b||a.open<=0||b.close<=0){const ta=maps.get(s)?.get(d),tb=targetPrev?maps.get(s)?.get(targetPrev):undefined;if(ta&&tb&&ta.open>0&&tb.close>0){a=ta;b=tb}else continue}const pc=syn.get(s)!,o=pc*(a.open/b.close),c=o*(a.close/a.open);syn.set(s,c);day[s]={date:d,open:o,high:Math.max(o,c),low:Math.min(o,c),close:c} as PricePoint}prices[d]=day;if(day.QQQ)synQ.push(day.QQQ.close);const me=!next||next.slice(0,7)!==d.slice(0,7);if(me){for(const st of strategies){const monthly=monthlyByStrat.get(st.label)!;for(const s of symbols)if(day[s])monthly.get(s)!.push(syn.get(s)!);signalsByStrat.get(st.label)![d]=makeSignal(d,next,latestU(us,d),monthly,st.cfg)}}}}
   const res:any={};for(const st of strategies){let state=initialEngineState(st.cfg),qh:PricePoint[]=[],curve:number[]=[];for(let i=0;i<target.length;i++){const d=target[i],next=target[i+1]??null,pp=prices[d]??{};if(pp.QQQ)qh.push(pp.QQQ);if(i===WARM)state=initialEngineState(st.cfg);if(i>=WARM){state=transitionDay(state,{date:d,prices:pp,qqqHistoryThroughClose:qh,monthlySignal:signalsByStrat.get(st.label)![d]??null,nextSessionDate:next},st.cfg);curve.push(state.currentEquity)}}res[st.label]=stats(curve)}rows.push(res);
  }
  const summarize=(label:string)=>{const x=rows.map(r=>r[label]);return{cagr:{p05:pct(x.map((z:any)=>z.cagr),.05),median:pct(x.map((z:any)=>z.cagr),.5),p95:pct(x.map((z:any)=>z.cagr),.95)},dd:{adverseP05:pct(x.map((z:any)=>z.dd),.05),median:pct(x.map((z:any)=>z.dd),.5)},pLoss:x.filter((z:any)=>z.cagr<0).length/PATHS,pGe50:x.filter((z:any)=>z.cagr>=.5).length/PATHS}};
  const diff=rows.map(r=>r.recovery5.cagr-r.production.cagr);output.variants[v.label]={block:v.block,radius:v.radius,mode:v.mode,production:summarize("production"),recovery5:summarize("recovery5"),pairedRecovery5MinusProduction:{median:pct(diff,.5),p05:pct(diff,.05),p95:pct(diff,.95),winRate:diff.filter(x=>x>0).length/PATHS}};console.log(v.label,JSON.stringify(output.variants[v.label]));
 }
 await mkdir(resolve("data/research/cpcm-validity"),{recursive:true});await writeFile(resolve("data/research/cpcm-validity/generator-sensitivity.json"),JSON.stringify(output,null,2));console.log("SENSITIVITY_JSON="+JSON.stringify(output));
}
main().catch(e=>{console.error(e);process.exit(1)});