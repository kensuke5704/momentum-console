import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { initialEngineState, transitionDay } from "../src/lib/strategy/state-machine";
import type { MonthlySignal, PricePoint, UniverseMonth } from "../src/lib/types";

type Market = { histories: Record<string, PricePoint[]> };
type UF = { history: UniverseMonth[] };
type Cause = "INVESTED"|"MARKET"|"STOP"|"CIRCUIT"|"TOP2_SHORTAGE"|"READY"|"OTHER_CASH";
const PATHS=1000, H=5*252, WARM=252, BLOCK=20, RADIUS=126, SEED=20260825;
const avg=(x:number[])=>x.length?x.reduce((a,b)=>a+b,0)/x.length:0;
const sd=(x:number[])=>{const m=avg(x);return x.length?Math.sqrt(avg(x.map(v=>(v-m)**2))):0};
const pct=(x:number[],p:number)=>{const a=[...x].sort((u,v)=>u-v),q=(a.length-1)*p,l=Math.floor(q),h=Math.ceil(q),w=q-l;return a[l]*(1-w)+a[h]*w};
function rng32(seed:number){let a=seed>>>0;return()=>{a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
function latestU(us:UniverseMonth[],d:string){let a=us[0];for(const u of us){if(u.asOf<=d)a=u;else break}return a}
const score=(r3:number,r6:number)=>.2*r3+.8*r6;
function makeSignal(date:string,next:string|null,u:UniverseMonth,monthly:Map<string,number[]>):MonthlySignal{
  const q=monthly.get("QQQ")??[],ret=(x:number[],n:number)=>x.length>n?x.at(-1)!/x.at(-(n+1))!-1:null;
  const q1=ret(q,1),q3=ret(q,3),q6=ret(q,6),qs=q1==null||q3==null||q6==null?null:score(q3,q6),ma=q.slice(-10),risk=ma.length===10&&q.at(-1)!>avg(ma),c:any[]=[];
  for(const m of u.symbols){const x=monthly.get(m.symbol)??[],r1=ret(x,1),r3=ret(x,3),r6=ret(x,6);if(r1==null||r3==null||r6==null||qs==null){c.push({symbol:m.symbol,oneMonth:r1,threeMonth:r3,sixMonth:r6,score:null,qqqScore:qs,scoreSpread:null,eligible:false,exclusionReason:"INSUFFICIENT_PRICE_HISTORY",rank:null});continue}const s=score(r3,r6),reason=r1>=.8?"ONE_MONTH_SURGE":s<=qs?"NOT_ABOVE_QQQ":null;c.push({symbol:m.symbol,oneMonth:r1,threeMonth:r3,sixMonth:r6,score:s,qqqScore:qs,scoreSpread:s-qs,eligible:!reason,exclusionReason:reason,rank:null})}
  const e=c.filter(x=>x.eligible&&x.score!=null).sort((a,b)=>b.score-a.score||a.symbol.localeCompare(b.symbol));e.forEach((x,i)=>x.rank=i+1);const chosen=e.slice(0,2),valid=chosen.length===2,d=sd(e.map(x=>x.score)),zg=valid&&d>0?(chosen[0].score-chosen[1].score)/d:valid?0:null,conc=zg!=null&&zg>=.25,w=conc?.7:.5;
  return {strategyId:PRODUCTION_STRATEGY.strategyId,signalMonth:date.slice(0,7),signalDate:date,executionDate:next,marketRiskOn:risk,qqqClose:q.at(-1)??null,qqqMonthlyMa:ma.length===10?avg(ma):null,qqqScore:qs,universe:u.symbols.map(x=>x.symbol),candidates:c,selectedSymbols:valid?chosen.map(x=>x.symbol):[],targetWeights:valid?[w,1-w]:[],zGap:zg,allocationMode:!valid?"CASH":conc?"70/30":"50/50"} as MonthlySignal;
}
function inferTrigger(s:string|null):Cause|null{if(!s)return null;const z=s.toLowerCase();if(z.includes("10m ma")||z.includes("riskoff"))return "MARKET";if(z.includes("stop"))return "STOP";if(z.includes("circuit"))return "CIRCUIT";return null}
function updateCause(prev:Cause,st:any,sig:MonthlySignal|null):Cause{
  if(st.currentPositions.length>0)return "INVESTED";
  if(st.state==="READY_NEXT_OPEN")return "READY";
  const t=inferTrigger(st.lastTrigger); if(st.state==="LOCKED_MARKET"||st.state==="LOCKED_STOP"||st.state==="LOCKED_CIRCUIT"||st.state==="WAITING_RECOVERY") return t??(prev==="INVESTED"?"OTHER_CASH":prev);
  if(sig){if(!sig.marketRiskOn)return "MARKET";if(sig.selectedSymbols.length<2)return "TOP2_SHORTAGE";}
  if(prev!=="INVESTED"&&prev!=="READY")return prev;
  return "OTHER_CASH";
}
function summarizeCauseShares(rows:Record<Cause,number>[],den:number){const out:any={};for(const k of ["INVESTED","MARKET","STOP","CIRCUIT","TOP2_SHORTAGE","READY","OTHER_CASH"] as Cause[]){const xs=rows.map(r=>r[k]/den);out[k]={p05:pct(xs,.05),median:pct(xs,.5),p95:pct(xs,.95)}}return out}
function stats(curve:number[]){let peak=curve[0]??1,dd=0;for(const v of curve){peak=Math.max(peak,v);dd=Math.min(dd,v/peak-1)}return{cagr:(curve.at(-1)!/(curve[0]||1))**(1/5)-1,dd}}
function actualRun(hist:Record<string,PricePoint[]>,us:UniverseMonth[]){
  const dates=(hist.QQQ??[]).map(p=>p.date),symbols=[...new Set(["QQQ",...us.flatMap(u=>u.symbols.map(x=>x.symbol))])],maps=new Map(symbols.map(s=>[s,new Map((hist[s]??[]).map(p=>[p.date,p]))])),monthly=new Map<string,number[]>(symbols.map(s=>[s,[]])),signals:Record<string,MonthlySignal>={};
  for(let i=0;i<dates.length;i++){const d=dates[i],next=dates[i+1]??null,me=!next||next.slice(0,7)!==d.slice(0,7);if(me){for(const s of symbols){const p=maps.get(s)?.get(d);if(p)monthly.get(s)!.push(p.close)}if(d>=us[0].asOf)signals[d]=makeSignal(d,next,latestU(us,d),monthly)}}
  let st=initialEngineState(PRODUCTION_STRATEGY),cause:Cause="OTHER_CASH";const qh:PricePoint[]=[],counts=Object.fromEntries(["INVESTED","MARKET","STOP","CIRCUIT","TOP2_SHORTAGE","READY","OTHER_CASH"].map(k=>[k,0])) as Record<Cause,number>;const curve:number[]=[];let n=0;
  for(let i=0;i<dates.length;i++){const d=dates[i],next=dates[i+1]??null,pq=maps.get("QQQ")?.get(d);if(pq)qh.push(pq);if(d<PRODUCTION_STRATEGY.backtestStart)continue;const prices:Record<string,PricePoint|undefined>={};for(const s of symbols){const p=maps.get(s)?.get(d);if(p)prices[s]=p}const sig=signals[d]??null;st=transitionDay(st,{date:d,prices,qqqHistoryThroughClose:qh,monthlySignal:sig,nextSessionDate:next},PRODUCTION_STRATEGY);cause=updateCause(cause,st,sig);counts[cause]++;curve.push(st.currentEquity);n++}
  return {days:n,shares:Object.fromEntries(Object.entries(counts).map(([k,v])=>[k,v/n])),...stats(curve)};
}
async function main(){
  const market=JSON.parse(await readFile(resolve("public/data/market-data.json"),"utf8")) as Market,uf=JSON.parse(await readFile(resolve("data/universe-history.json"),"utf8")) as UF,us=[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf)),hist=market.histories;
  const actual=actualRun(hist,us);
  const dates=(hist.QQQ??[]).filter(p=>p.date>=us[0].asOf).map(p=>p.date),target=dates.slice(-(WARM+H)),symbols=[...new Set(["QQQ",...us.flatMap(u=>u.symbols.map(x=>x.symbol))])],maps=new Map(symbols.map(s=>[s,new Map((hist[s]??[]).map(p=>[p.date,p]))])),dateIndex=new Map(dates.map((d,i)=>[d,i]));
  const q=(hist.QQQ??[]).filter(p=>dateIndex.has(p.date)),qMap=new Map(q.map(p=>[p.date,p]));
  const feature=(i:number)=>{const d=dates[i],p=qMap.get(d);if(!p||i<60)return null;const closes=dates.slice(i-60,i+1).map(x=>qMap.get(x)?.close).filter((x):x is number=>x!=null),r20=[] as number[];for(let j=i-19;j<=i;j++){const a=qMap.get(dates[j])?.close,b=qMap.get(dates[j-1])?.close;if(a&&b)r20.push(a/b-1)}if(closes.length<61||r20.length<20)return null;return{trend:closes.at(-1)!/closes[0]-1,vol:sd(r20)}};
  const feats=dates.map((_,i)=>feature(i)),r=rng32(SEED),causeRows:Record<Cause,number>[]=[],cagrs:number[]=[],dds:number[]=[];let totalFallback=0,totalObs=0;
  for(let pathNo=0;pathNo<PATHS;pathNo++){
    const syn=new Map(symbols.map(s=>[s,100])),monthly=new Map<string,number[]>(symbols.map(s=>[s,[]])),prices:Record<string,Record<string,PricePoint>>={},signals:Record<string,MonthlySignal>={};
    for(let ti=0;ti<target.length;){const td=target[ti],baseIdx=dateIndex.get(td)!,f=feats[baseIdx];let donor=baseIdx;if(f){const cand:number[]=[];for(let k=Math.max(61,baseIdx-RADIUS);k<=Math.min(dates.length-BLOCK-1,baseIdx+RADIUS);k++){const g=feats[k];if(!g)continue;if(Math.sign(g.trend)!==Math.sign(f.trend)&&Math.abs(f.trend)>.03)continue;const dist=Math.abs(g.trend-f.trend)/.10+Math.abs(g.vol-f.vol)/.01;cand.push(k+dist*1e-6)}cand.sort((a,b)=>(a-Math.floor(a))-(b-Math.floor(b)));const pool=cand.slice(0,Math.min(20,cand.length)).map(x=>Math.floor(x));if(pool.length)donor=pool[Math.floor(r()*pool.length)]}
      for(let j=0;j<BLOCK&&ti<target.length;j++,ti++){const d=target[ti],next=target[ti+1]??null,src=dates[Math.min(donor+j,dates.length-1)],srcPrev=dates[Math.max(0,Math.min(donor+j-1,dates.length-1))],targetPrev=ti>0?target[ti-1]:null,day:Record<string,PricePoint>={};for(const s of symbols){let a=maps.get(s)?.get(src),b=maps.get(s)?.get(srcPrev);if(!a||!b||a.open<=0||b.close<=0){const ta=maps.get(s)?.get(d),tb=targetPrev?maps.get(s)?.get(targetPrev):undefined;if(ta&&tb&&ta.open>0&&tb.close>0){a=ta;b=tb;totalFallback++}else continue}totalObs++;const pc=syn.get(s)!,o=pc*(a.open/b.close),c=o*(a.close/a.open);syn.set(s,c);day[s]={date:d,open:o,high:Math.max(o,c),low:Math.min(o,c),close:c}}prices[d]=day;const me=!next||next.slice(0,7)!==d.slice(0,7);if(me){for(const s of symbols)if(day[s])monthly.get(s)!.push(syn.get(s)!);signals[d]=makeSignal(d,next,latestU(us,d),monthly)}}}
    let st=initialEngineState(PRODUCTION_STRATEGY),cause:Cause="OTHER_CASH";const qh:PricePoint[]=[],counts=Object.fromEntries(["INVESTED","MARKET","STOP","CIRCUIT","TOP2_SHORTAGE","READY","OTHER_CASH"].map(k=>[k,0])) as Record<Cause,number>,curve:number[]=[];
    for(let i=0;i<target.length;i++){const d=target[i],next=target[i+1]??null,pp=prices[d]??{};if(pp.QQQ)qh.push(pp.QQQ);if(i===WARM){st=initialEngineState(PRODUCTION_STRATEGY);cause="OTHER_CASH"}if(i>=WARM){const sig=signals[d]??null;st=transitionDay(st,{date:d,prices:pp,qqqHistoryThroughClose:qh,monthlySignal:sig,nextSessionDate:next},PRODUCTION_STRATEGY);cause=updateCause(cause,st,sig);counts[cause]++;curve.push(st.currentEquity)}}
    causeRows.push(counts);const z=stats(curve);cagrs.push(z.cagr);dds.push(z.dd);if((pathNo+1)%50===0)console.log(`completed ${pathNo+1}/${PATHS}`)
  }
  const out={generatedAt:new Date().toISOString(),strategyId:PRODUCTION_STRATEGY.strategyId,method:{name:"cash-state decomposition on Production chronology and CPCM",causeTracking:"cash cause persists until entry; recovery attributed to originating Market/Stop/Circuit trigger",cpcm:"same 20d block / +/-126d conditional donor model as audited CPCM baseline",fallbackRate:totalFallback/Math.max(1,totalObs)},actual,mc:{paths:PATHS,seed:SEED,cagr:{median:pct(cagrs,.5),p05:pct(cagrs,.05)},maxDrawdown:{median:pct(dds,.5)},shares:summarizeCauseShares(causeRows,H)}};
  await mkdir(resolve("data/research/cash-state"),{recursive:true});await writeFile(resolve("data/research/cash-state/decomposition.json"),JSON.stringify(out,null,2));console.log("RESULT_JSON="+JSON.stringify(out));
}
main().catch(e=>{console.error(e);process.exit(1)});
