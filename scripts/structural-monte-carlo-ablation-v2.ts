import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { initialEngineState, transitionDay } from "../src/lib/strategy/state-machine";
import type { MonthlySignal, PricePoint, UniverseMonth } from "../src/lib/types";

type Market={histories:Record<string,PricePoint[]>}; type UF={history:UniverseMonth[]};
type Path={dates:string[]; sourceDates:string[]; prices:Record<string,Record<string,PricePoint>>; monthlySignals:Record<string,MonthlySignal>};
type Out={cagr:number;dd:number};
const PATHS=Number(process.env.ABLATION_PATHS??100), YEARS=5, H=YEARS*252, WARM=252, BLOCK=20, SEED=20260825;
const cfg=PRODUCTION_STRATEGY;
function rng32(seed:number){let a=seed>>>0;return()=>{a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
const avg=(x:number[])=>x.length?x.reduce((a,b)=>a+b,0)/x.length:0; const sd=(x:number[])=>{const m=avg(x);return x.length?Math.sqrt(avg(x.map(v=>(v-m)**2))):0};
const pct=(x:number[],p:number)=>{x=[...x].sort((a,b)=>a-b);const q=(x.length-1)*p,l=Math.floor(q),h=Math.ceil(q),w=q-l;return x[l]*(1-w)+x[h]*w};
const score=(r3:number,r6:number)=>.2*r3+.8*r6;
function latestU(us:UniverseMonth[],d:string){let a=us[0];for(const u of us){if(u.asOf<=d)a=u;else break}return a}
function signal(date:string,next:string|null,u:UniverseMonth,monthly:Map<string,number[]>):MonthlySignal{
 const q=monthly.get("QQQ")??[],ret=(x:number[],n:number)=>x.length>n?x.at(-1)!/x.at(-(n+1))!-1:null,q1=ret(q,1),q3=ret(q,3),q6=ret(q,6),qs=q1==null||q3==null||q6==null?null:score(q3,q6),ma=q.slice(-10),risk=ma.length===10&&q.at(-1)!>avg(ma),c:any[]=[];
 for(const m of u.symbols){const x=monthly.get(m.symbol)??[],r1=ret(x,1),r3=ret(x,3),r6=ret(x,6);if(r1==null||r3==null||r6==null||qs==null){c.push({symbol:m.symbol,oneMonth:r1,threeMonth:r3,sixMonth:r6,score:null,qqqScore:qs,scoreSpread:null,eligible:false,exclusionReason:"INSUFFICIENT_PRICE_HISTORY",rank:null});continue}const s=score(r3,r6),reason=r1>=.8?"ONE_MONTH_SURGE":s<=qs?"NOT_ABOVE_QQQ":null;c.push({symbol:m.symbol,oneMonth:r1,threeMonth:r3,sixMonth:r6,score:s,qqqScore:qs,scoreSpread:s-qs,eligible:!reason,exclusionReason:reason,rank:null})}
 const e=c.filter(x=>x.eligible&&x.score!=null).sort((a,b)=>b.score-a.score||a.symbol.localeCompare(b.symbol));e.forEach((x,i)=>x.rank=i+1);const chosen=e.slice(0,2),valid=chosen.length===2,d=sd(e.map(x=>x.score)),zg=valid&&d>0?(chosen[0].score-chosen[1].score)/d:valid?0:null,conc=zg!=null&&zg>=.25,w=conc?.7:.5;
 return {strategyId:cfg.strategyId,signalMonth:date.slice(0,7),signalDate:date,executionDate:next,marketRiskOn:risk,qqqClose:q.at(-1)??null,qqqMonthlyMa:ma.length===10?avg(ma):null,qqqScore:qs,universe:u.symbols.map(x=>x.symbol),candidates:c,selectedSymbols:valid?chosen.map(x=>x.symbol):[],targetWeights:valid?[w,1-w]:[],zGap:zg,allocationMode:!valid?"CASH":conc?"70/30":"50/50"} as MonthlySignal;
}
function stats(curve:number[]):Out{let peak=curve[0]??1,dd=0;for(const v of curve){peak=Math.max(peak,v);dd=Math.min(dd,v/peak-1)}const years=YEARS,cagr=(curve.at(-1)!/curve[0])**(1/years)-1;return{cagr,dd}}
function simple(path:Path,opt:{fixed:boolean;gate:boolean;stop:boolean;circuit:boolean}):Out{
 let cash=1,positions:{s:string;sh:number;entry:number;stop:number}[]=[],peak=1,fixed:string[]|null=null,pendingSell=false;const curve:number[]=[];
 const equity=(d:string,field:"open"|"close")=>cash+positions.reduce((z,p)=>z+p.sh*(path.prices[d]?.[p.s]?.[field]??path.prices[d]?.[p.s]?.close??p.entry),0);
 for(let i=WARM;i<path.dates.length;i++){const d=path.dates[i],next=path.dates[i+1]??null,pp=path.prices[d]??{};
   if(pendingSell&&positions.length){cash=positions.reduce((z,p)=>z+p.sh*(pp[p.s]?.open??pp[p.s]?.close??p.entry),0)*(.999);positions=[];pendingSell=false}
   const sig=path.monthlySignals[d]; if(sig){let syms=sig.selectedSymbols;if(opt.fixed){if(!fixed&&syms.length===2)fixed=[...syms];syms=fixed??[]} const can=syms.length===2&&(!opt.gate||sig.marketRiskOn);
     if(positions.length){cash=positions.reduce((z,p)=>z+p.sh*(pp[p.s]?.open??pp[p.s]?.close??p.entry),0)*.999;positions=[]}
     if(can){const ws=sig.targetWeights.length===2?sig.targetWeights:[.5,.5];for(let k=0;k<2;k++){const px=pp[syms[k]]?.open??pp[syms[k]]?.close;if(px&&px>0){const alloc=cash*ws[k]*.999;positions.push({s:syms[k],sh:alloc/px,entry:px,stop:px*(1-.175)})}}cash=positions.length===2?0:cash}
   }
   const eq=equity(d,"close");peak=Math.max(peak,eq); if(positions.length&&!pendingSell){if(opt.stop&&positions.some(p=>(pp[p.s]?.close??Infinity)<=p.stop))pendingSell=true;else if(opt.circuit&&eq/peak-1<=-.15)pendingSell=true}curve.push(eq)
 }
 return stats(curve)
}
function full(path:Path):Out{let st=initialEngineState(cfg);const qh:PricePoint[]=[],curve:number[]=[];for(let i=0;i<path.dates.length;i++){const d=path.dates[i],next=path.dates[i+1]??null,pp=path.prices[d]??{};if(pp.QQQ)qh.push(pp.QQQ);if(i===WARM)st=initialEngineState(cfg);if(i>=WARM){st=transitionDay(st,{date:d,prices:pp,qqqHistoryThroughClose:qh,monthlySignal:path.monthlySignals[d]??null,nextSessionDate:next},cfg);curve.push(st.currentEquity)}}return stats(curve)}
async function main(){const market=JSON.parse(await readFile(resolve("public/data/market-data.json"),"utf8")) as Market,uf=JSON.parse(await readFile(resolve("data/universe-history.json"),"utf8")) as UF,us=[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf)),hist=market.histories,dates=(hist.QQQ??[]).filter(p=>p.date>=us[0].asOf).map(p=>p.date),target=dates.slice(-(WARM+H)),symbols=[...new Set(["QQQ",...us.flatMap(u=>u.symbols.map(x=>x.symbol))])],maps=new Map(symbols.map(s=>[s,new Map((hist[s]??[]).map(p=>[p.date,p]))])),starts=dates.map((_,i)=>i).filter(i=>i>=1&&i+BLOCK<dates.length),r=rng32(SEED);
 const names=["A Fixed Top2","B Dynamic Top2","C + Market Gate","D + Individual Stop","E + Portfolio Circuit","F Full Production Recovery"],res=Object.fromEntries(names.map(n=>[n,[] as Out[]]));
 for(let p=0;p<PATHS;p++){const idx:number[]=[];while(idx.length<target.length){const s=starts[Math.floor(r()*starts.length)];for(let j=0;j<BLOCK&&idx.length<target.length;j++)idx.push(s+j)}const syn=new Map(symbols.map(s=>[s,100])),monthly=new Map<string,number[]>(symbols.map(s=>[s,[]])),prices:Record<string,Record<string,PricePoint>>={},signals:Record<string,MonthlySignal>={};
   for(let ti=0;ti<target.length;ti++){const td=target[ti],next=target[ti+1]??null,si=idx[ti],src=dates[si],prev=dates[si-1],day:Record<string,PricePoint>={};for(const s of symbols){const a=maps.get(s)?.get(src),b=maps.get(s)?.get(prev);if(!a||!b||a.open<=0||b.close<=0)continue;const pc=syn.get(s)!,o=pc*(a.open/b.close),c=o*(a.close/a.open);syn.set(s,c);day[s]={date:td,open:o,high:Math.max(o,c),low:Math.min(o,c),close:c} as PricePoint}prices[td]=day;const me=!next||next.slice(0,7)!==td.slice(0,7);if(me){for(const s of symbols)if(day[s])monthly.get(s)!.push(syn.get(s)!);signals[td]=signal(td,next,latestU(us,src),monthly)}}
   const path={dates:target,sourceDates:idx.map(i=>dates[i]),prices,monthlySignals:signals};res[names[0]].push(simple(path,{fixed:true,gate:false,stop:false,circuit:false}));res[names[1]].push(simple(path,{fixed:false,gate:false,stop:false,circuit:false}));res[names[2]].push(simple(path,{fixed:false,gate:true,stop:false,circuit:false}));res[names[3]].push(simple(path,{fixed:false,gate:true,stop:true,circuit:false}));res[names[4]].push(simple(path,{fixed:false,gate:true,stop:true,circuit:true}));res[names[5]].push(full(path));if((p+1)%25===0)console.log(`completed ${p+1}/${PATHS}`)}
 const summary=Object.fromEntries(names.map(n=>{const o=res[n],c=o.map(x=>x.cagr),d=o.map(x=>x.dd);return[n,{cagr:{p05:pct(c,.05),median:pct(c,.5),p95:pct(c,.95)},maxDrawdown:{adverseP05:pct(d,.05),median:pct(d,.5)},probabilities:{cagrGe50:c.filter(x=>x>=.5).length/PATHS,cagrLt0:c.filter(x=>x<0).length/PATHS,ddLe40:d.filter(x=>x<=-.4).length/PATHS}}]}));await mkdir(resolve("data/research/structural-monte-carlo"),{recursive:true});await writeFile(resolve("data/research/structural-monte-carlo/ablation-v2.json"),JSON.stringify({paths:PATHS,summary},null,2));console.log("RESULT_JSON="+JSON.stringify({paths:PATHS,summary}))}
main().catch(e=>{console.error(e);process.exit(1)});
