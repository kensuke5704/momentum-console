import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import { initialEngineState, transitionDay } from "../src/lib/strategy/state-machine";
import type { EquityPoint, PricePoint, UniverseMonth } from "../src/lib/types";

type Market = { histories: Record<string, PricePoint[]> };
type UF = { history: UniverseMonth[] };

type DailyRow = { date:string; equity:number; logReturn:number; exposed:boolean };
type MonthlyRow = { month:string; logReturn:number; simpleReturn:number; exposureShare:number };

const BOOTSTRAPS = Number(process.env.EXPECTED_CAGR_BOOTSTRAPS ?? 20000);
const BLOCK_MONTHS = 3;
const SEED = 20260826;

const avg=(x:number[])=>x.length?x.reduce((a,b)=>a+b,0)/x.length:0;
const median=(x:number[])=>quantile(x,.5);
function quantile(x:number[],p:number){if(!x.length)return NaN;const a=[...x].sort((u,v)=>u-v),q=(a.length-1)*p,l=Math.floor(q),h=Math.ceil(q),w=q-l;return a[l]*(1-w)+a[h]*w}
function rng32(seed:number){let a=seed>>>0;return()=>{a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
function mad(x:number[]){const m=median(x);return median(x.map(v=>Math.abs(v-m)))}
function huberLocation(x:number[],k=1.5){if(!x.length)return NaN;let mu=median(x);const s=Math.max(1e-9,1.4826*mad(x));for(let it=0;it<100;it++){let num=0,den=0;for(const v of x){const z=(v-mu)/s,w=Math.abs(z)<=k?1:k/Math.abs(z);num+=w*v;den+=w}const nmu=num/Math.max(1e-12,den);if(Math.abs(nmu-mu)<1e-12){mu=nmu;break}mu=nmu}return mu}
function winsorMean(x:number[],tail=.10){if(!x.length)return NaN;const lo=quantile(x,tail),hi=quantile(x,1-tail);return avg(x.map(v=>Math.min(hi,Math.max(lo,v))))}
const annFromMonthlyLog=(m:number)=>Math.exp(12*m)-1;
const annFromDailyLog=(m:number)=>Math.exp(252*m)-1;

function latestU(us:UniverseMonth[],d:string){let out:UniverseMonth|null=null;for(const u of us){if(u.asOf<=d)out=u;else break}return out}

function reconstruct(histories:Record<string,PricePoint[]>, universeHistory:UniverseMonth[]){
  const qqq=[...(histories.QQQ??[])].sort((a,b)=>a.date.localeCompare(b.date));
  const dates=qqq.map(p=>p.date);
  const dateIndex=new Map(dates.map((d,i)=>[d,i]));
  const priceMaps=Object.fromEntries(Object.entries(histories).map(([s,ps])=>[s,new Map(ps.map(p=>[p.date,p]))]));
  const universeByDate=new Map(universeHistory.map(u=>[u.asOf,u]));
  let st=initialEngineState(PRODUCTION_STRATEGY);
  const rows:DailyRow[]=[];
  let prevEquity:number|null=null;
  for(let i=0;i<dates.length;i++){
    const date=dates[i]; if(date<PRODUCTION_STRATEGY.backtestStart) continue;
    const next=dates[i+1]??null;
    const u=universeByDate.get(date)??null;
    const signal=u?buildMonthlySignal({universe:u,histories,qqq,nextSessionDate:next,config:PRODUCTION_STRATEGY}):null;
    const symbols=new Set(["QQQ",...st.currentPositions.map(p=>p.symbol),...(st.pendingSignal?.selectedSymbols??[]),...st.nextAction.symbols,...(signal?.selectedSymbols??[])]);
    const prices=Object.fromEntries([...symbols].map(s=>[s,priceMaps[s]?.get(date)]));
    const wasExposed=st.currentPositions.length>0;
    st=transitionDay(st,{date,prices,qqqHistoryThroughClose:qqq.slice(0,(dateIndex.get(date)??i)+1),monthlySignal:signal,nextSessionDate:next},PRODUCTION_STRATEGY);
    const exposed=wasExposed||st.currentPositions.length>0;
    const eq=st.currentEquity;
    const lr=prevEquity&&prevEquity>0?Math.log(eq/prevEquity):0;
    rows.push({date,equity:eq,logReturn:lr,exposed});
    prevEquity=eq;
  }
  return rows;
}

function monthly(rows:DailyRow[]):MonthlyRow[]{
  const by=new Map<string,DailyRow[]>();
  for(const r of rows){const m=r.date.slice(0,7);const a=by.get(m)??[];a.push(r);by.set(m,a)}
  const out:MonthlyRow[]=[];
  for(const [month,rs] of [...by.entries()].sort((a,b)=>a[0].localeCompare(b[0]))){
    const logReturn=rs.reduce((s,r)=>s+r.logReturn,0);
    out.push({month,logReturn,simpleReturn:Math.exp(logReturn)-1,exposureShare:rs.filter(r=>r.exposed).length/rs.length});
  }
  return out;
}

function bootstrap(ms:MonthlyRow[]){
  const rng=rng32(SEED),n=ms.length,vals:number[]=[];
  for(let b=0;b<BOOTSTRAPS;b++){
    const sample:number[]=[];
    while(sample.length<n){const start=Math.floor(rng()*Math.max(1,n-BLOCK_MONTHS+1));for(let j=0;j<BLOCK_MONTHS&&sample.length<n;j++)sample.push(ms[start+j].logReturn)}
    vals.push(annFromMonthlyLog(huberLocation(sample)));
  }
  return {p05:quantile(vals,.05),p25:quantile(vals,.25),median:quantile(vals,.5),p75:quantile(vals,.75),p95:quantile(vals,.95)};
}

function leaveOneYearOut(ms:MonthlyRow[]){
  const years=[...new Set(ms.map(x=>x.month.slice(0,4)))];
  return years.map(year=>{const keep=ms.filter(x=>!x.month.startsWith(year));return {excludedYear:year,cagr:annFromMonthlyLog(huberLocation(keep.map(x=>x.logReturn)))}});
}

async function main(){
  const market=JSON.parse(await readFile(resolve("public/data/market-data.json"),"utf8")) as Market;
  const uf=JSON.parse(await readFile(resolve("data/universe-history.json"),"utf8")) as UF;
  const us=[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf));
  const daily=reconstruct(market.histories,us), ms=monthly(daily);
  if(ms.length<12)throw new Error("insufficient monthly history");
  const rawDaily=annFromDailyLog(avg(daily.slice(1).map(x=>x.logReturn)));
  const rawMonthly=annFromMonthlyLog(avg(ms.map(x=>x.logReturn)));
  const robust=annFromMonthlyLog(huberLocation(ms.map(x=>x.logReturn)));
  const winsor=annFromMonthlyLog(winsorMean(ms.map(x=>x.logReturn),.10));
  const exposureShare=avg(daily.map(x=>x.exposed?1:0));
  const exposedLogs=daily.slice(1).filter(x=>x.exposed).map(x=>x.logReturn);
  const cashLogs=daily.slice(1).filter(x=>!x.exposed).map(x=>x.logReturn);
  const exposedAnnualized=annFromDailyLog(avg(exposedLogs));
  const cashAnnualized=annFromDailyLog(avg(cashLogs));
  const byYear=[...new Set(ms.map(x=>x.month.slice(0,4)))].map(year=>{const x=ms.filter(m=>m.month.startsWith(year));return {year,months:x.length,rawCagr:annFromMonthlyLog(avg(x.map(v=>v.logReturn))),robustCagr:annFromMonthlyLog(huberLocation(x.map(v=>v.logReturn))),exposureShare:avg(x.map(v=>v.exposureShare))}});
  const loo=leaveOneYearOut(ms), boot=bootstrap(ms);
  const top=ms.slice().sort((a,b)=>b.simpleReturn-a.simpleReturn).slice(0,10).map(x=>({month:x.month,return:x.simpleReturn}));
  const estimate={point:robust,central50:[boot.p25,boot.p75],central90:[boot.p05,boot.p95]};
  const out={generatedAt:new Date().toISOString(),strategyId:PRODUCTION_STRATEGY.strategyId,mainMethod:{name:"robust empirical expected geometric growth",center:"Huber M-estimator of monthly log returns, k=1.5",uncertainty:`${BLOCK_MONTHS}-month moving-block bootstrap, ${BOOTSTRAPS} resamples`,purpose:"estimate long-run geometric growth from realized Production returns without CPCM or an external return prior"},sample:{start:daily[0]?.date,end:daily.at(-1)?.date,tradingDays:daily.length,months:ms.length},estimate,diagnostics:{realizedGeometricAnnualizedDaily:rawDaily,realizedGeometricAnnualizedMonthly:rawMonthly,winsor10Annualized:winsor,exposureShare,exposedAnnualized,cashAnnualized,yearly:byYear,leaveOneYearOut:loo,topMonths:top},caveats:["This is an empirical sampling estimate, not a structural forecast.","Bootstrap intervals quantify sampling/path uncertainty conditional on the observed regime mix; they do not include model/regime uncertainty outside the sample.","Huber robustness reduces influence of extreme winner months but does not prove that remaining alpha is repeatable.","Forward OOS should progressively replace historical-only evidence as observations accumulate."]};
  await mkdir(resolve("data/research/expected-cagr"),{recursive:true});
  await writeFile(resolve("data/research/expected-cagr/expected-cagr.json"),JSON.stringify(out,null,2));
  console.log("EXPECTED_CAGR_JSON="+JSON.stringify(out));
}
main().catch(e=>{console.error(e);process.exit(1)});
