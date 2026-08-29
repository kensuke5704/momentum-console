import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import { initialEngineState, transitionDay } from "../src/lib/strategy/state-machine";
import type { PricePoint, UniverseMonth } from "../src/lib/types";

type Market={histories:Record<string,PricePoint[]>};
type UF={history:UniverseMonth[]};
type DailyRow={date:string;equity:number;logReturn:number};
type MonthlyRow={month:string;logReturn:number};
const BLOCK_MONTHS=3, SEED=20260826, SAMPLE_COUNT=100;
function quantile(x:number[],p:number){const a=[...x].sort((u,v)=>u-v),q=(a.length-1)*p,l=Math.floor(q),h=Math.ceil(q),w=q-l;return a[l]*(1-w)+a[h]*w}
const median=(x:number[])=>quantile(x,.5);
function mad(x:number[]){const m=median(x);return median(x.map(v=>Math.abs(v-m)))}
function huberLocation(x:number[],k=1.5){let mu=median(x);const s=Math.max(1e-9,1.4826*mad(x));for(let it=0;it<100;it++){let num=0,den=0;for(const v of x){const z=(v-mu)/s,w=Math.abs(z)<=k?1:k/Math.abs(z);num+=w*v;den+=w}const nmu=num/den;if(Math.abs(nmu-mu)<1e-12){mu=nmu;break}mu=nmu}return mu}
function rng32(seed:number){let a=seed>>>0;return()=>{a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
const annFromMonthlyLog=(m:number)=>Math.exp(12*m)-1;
function reconstruct(histories:Record<string,PricePoint[]>, universeHistory:UniverseMonth[]){
  const qqq=[...(histories.QQQ??[])].sort((a,b)=>a.date.localeCompare(b.date));
  const dates=qqq.map(p=>p.date),di=new Map(dates.map((d,i)=>[d,i]));
  const pm=Object.fromEntries(Object.entries(histories).map(([s,ps])=>[s,new Map(ps.map(p=>[p.date,p]))]));
  const ub=new Map(universeHistory.map(u=>[u.asOf,u])); let st=initialEngineState(PRODUCTION_STRATEGY),prev:number|null=null; const rows:DailyRow[]=[];
  for(let i=0;i<dates.length;i++){const date=dates[i];if(date<PRODUCTION_STRATEGY.backtestStart)continue;const next=dates[i+1]??null,u=ub.get(date)??null;
    const signal=u?buildMonthlySignal({universe:u,histories,qqq,nextSessionDate:next,config:PRODUCTION_STRATEGY}):null;
    const syms=new Set(["QQQ",...st.currentPositions.map(p=>p.symbol),...(st.pendingSignal?.selectedSymbols??[]),...st.nextAction.symbols,...(signal?.selectedSymbols??[])]);
    const prices=Object.fromEntries([...syms].map(s=>[s,pm[s]?.get(date)]));
    st=transitionDay(st,{date,prices,qqqHistoryThroughClose:qqq.slice(0,(di.get(date)??i)+1),monthlySignal:signal,nextSessionDate:next},PRODUCTION_STRATEGY);
    const eq=st.currentEquity,lr=prev&&prev>0?Math.log(eq/prev):0;rows.push({date,equity:eq,logReturn:lr});prev=eq;
  }return rows;
}
function monthly(rows:DailyRow[]):MonthlyRow[]{const by=new Map<string,DailyRow[]>();for(const r of rows){const m=r.date.slice(0,7),a=by.get(m)??[];a.push(r);by.set(m,a)}return [...by.entries()].sort((a,b)=>a[0].localeCompare(b[0])).map(([month,rs])=>({month,logReturn:rs.reduce((s,r)=>s+r.logReturn,0)}))}
async function main(){
  const market=JSON.parse(await readFile(resolve("public/data/market-data.json"),"utf8")) as Market;
  const uf=JSON.parse(await readFile(resolve("data/universe-history.json"),"utf8")) as UF;
  const ms=monthly(reconstruct(market.histories,[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf))));
  const rng=rng32(SEED),n=ms.length,samples=[];
  for(let b=0;b<SAMPLE_COUNT;b++){const picked:number[]=[];const blocks:{startIndex:number;months:string[]}[]=[];while(picked.length<n){const start=Math.floor(rng()*Math.max(1,n-BLOCK_MONTHS+1));const months:string[]=[];for(let j=0;j<BLOCK_MONTHS&&picked.length<n;j++){picked.push(ms[start+j].logReturn);months.push(ms[start+j].month)}blocks.push({startIndex:start,months})}samples.push({sample:b+1,cagr:annFromMonthlyLog(huberLocation(picked)),blocks});}
  const out={seed:SEED,blockMonths:BLOCK_MONTHS,sampleStart:ms[0]?.month,sampleEnd:ms.at(-1)?.month,months:ms.length,sampleCount:SAMPLE_COUNT,first100:samples};
  await mkdir(resolve("data/research/expected-cagr-replay"),{recursive:true});
  await writeFile(resolve("data/research/expected-cagr-replay/first100.json"),JSON.stringify(out,null,2));
  console.log(JSON.stringify(out));
}
main().catch(e=>{console.error(e);process.exit(1)});
