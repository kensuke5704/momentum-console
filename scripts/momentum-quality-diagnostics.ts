import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import type { PricePoint, UniverseMonth } from "../src/lib/types";

type Market={histories:Record<string,PricePoint[]>};
type UF={history:UniverseMonth[]};
type Obs={signalDate:string,symbol:string,momentumRank:number,forwardReturn:number,features:Record<string,number>};

const TOPK=5;
const SEED=20260825;
const score=(r3:number,r6:number)=>PRODUCTION_STRATEGY.momentum.threeMonth*r3+PRODUCTION_STRATEGY.momentum.sixMonth*r6;
const avg=(x:number[])=>x.length?x.reduce((a,b)=>a+b,0)/x.length:NaN;
const pct=(x:number[],p:number)=>{const a=[...x].sort((u,v)=>u-v);if(!a.length)return NaN;const q=(a.length-1)*p,l=Math.floor(q),h=Math.ceil(q),w=q-l;return a[l]*(1-w)+a[h]*w};
function rng32(seed:number){let a=seed>>>0;return()=>{a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
function latestU(us:UniverseMonth[],d:string){let a=us[0];for(const u of us){if(u.asOf<=d)a=u;else break}return a}
function rank(v:number[]){const a=v.map((x,i)=>({x,i})).sort((p,q)=>p.x-q.x);const r=Array(v.length).fill(0);for(let i=0;i<a.length;){let j=i;while(j+1<a.length&&a[j+1].x===a[i].x)j++;const rr=(i+j)/2+1;for(let k=i;k<=j;k++)r[a[k].i]=rr;i=j+1}return r}
function corr(x:number[],y:number[]){if(x.length<3)return NaN;const mx=avg(x),my=avg(y);let a=0,b=0,c=0;for(let i=0;i<x.length;i++){const dx=x[i]-mx,dy=y[i]-my;a+=dx*dy;b+=dx*dx;c+=dy*dy}return b>0&&c>0?a/Math.sqrt(b*c):NaN}
const spearman=(x:number[],y:number[])=>corr(rank(x),rank(y));
function maxDD(xs:number[]){let p=xs[0],dd=0;for(const x of xs){p=Math.max(p,x);dd=Math.min(dd,x/p-1)}return dd}
function featureSet(hist:PricePoint[],idx:number){if(idx<127)return null;const close=(i:number)=>hist[i]?.close;const c=close(idx);if(!c||c<=0)return null;const r=[] as number[];for(let i=idx-62;i<=idx;i++){const a=close(i),b=close(i-1);if(!a||!b||b<=0)return null;r.push(a/b-1)}const win126=hist.slice(idx-125,idx+1).map(p=>p.close);if(win126.length<126||win126.some(x=>!x||x<=0))return null;const r63=c/close(idx-63)!-1,prev63=close(idx-63)!/close(idx-126)!-1;return {
  consistency63:r.filter(x=>x>0).length/r.length,
  smoothness126:maxDD(win126),
  highProximity126:c/Math.max(...win126)-1,
  acceleration63:r63-prev63,
};}
function bootstrapCI(vals:number[],seed:number){const clean=vals.filter(Number.isFinite);if(clean.length<3)return [NaN,NaN];const r=rng32(seed),means:number[]=[];for(let b=0;b<5000;b++){const s:number[]=[];for(let i=0;i<clean.length;i++)s.push(clean[Math.floor(r()*clean.length)]);means.push(avg(s))}return [pct(means,.025),pct(means,.975)]}
function summarize(obs:Obs[],feature:string,seedOffset:number){const byMonth=new Map<string,Obs[]>();for(const o of obs){if(!byMonth.has(o.signalDate))byMonth.set(o.signalDate,[]);byMonth.get(o.signalDate)!.push(o)}const ics:number[]=[],spreads:number[]=[];for(const [,rows] of byMonth){const valid=rows.filter(o=>Number.isFinite(o.features[feature])&&Number.isFinite(o.forwardReturn));if(valid.length<3)continue;const ic=spearman(valid.map(o=>o.features[feature]),valid.map(o=>o.forwardReturn));if(Number.isFinite(ic))ics.push(ic);const sorted=[...valid].sort((a,b)=>b.features[feature]-a.features[feature]);spreads.push(sorted[0].forwardReturn-sorted.at(-1)!.forwardReturn)}const ci=bootstrapCI(ics,SEED+seedOffset);return {months:ics.length,meanIC:avg(ics),medianIC:pct(ics,.5),positiveICRate:ics.filter(x=>x>0).length/Math.max(1,ics.length),meanTopMinusBottomForwardReturn:avg(spreads),meanICBootstrap95:[ci[0],ci[1]]};}

async function main(){
  const market=JSON.parse(await readFile(resolve("public/data/market-data.json"),"utf8")) as Market;
  const uf=JSON.parse(await readFile(resolve("data/universe-history.json"),"utf8")) as UF;
  const us=[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf));
  const q=market.histories.QQQ??[];
  const qDates=q.map(p=>p.date);
  const qIndex=new Map(qDates.map((d,i)=>[d,i]));
  const monthEnds:string[]=[];for(let i=0;i<qDates.length;i++){const d=qDates[i],n=qDates[i+1];if(!n||n.slice(0,7)!==d.slice(0,7))monthEnds.push(d)}
  const maps=new Map(Object.entries(market.histories).map(([s,h])=>[s,new Map(h.map((p,i)=>[p.date,i]))]));
  const obs:Obs[]=[];
  for(let mi=0;mi<monthEnds.length-1;mi++){
    const d=monthEnds[mi]; if(d<PRODUCTION_STRATEGY.backtestStart||d<us[0].asOf)continue;
    const nextSignal=monthEnds[mi+1]; const qi=qIndex.get(d); const qNextIdx=qIndex.get(nextSignal); if(qi==null||qNextIdx==null||qi<127)continue;
    const nextEntry=q[qi+1]?.date, nextExit=q[qNextIdx+1]?.date; if(!nextEntry||!nextExit)continue;
    const retM=(hist:PricePoint[],idx:number,n:number)=>idx>=n&&hist[idx-n]?.close>0?hist[idx].close/hist[idx-n].close-1:null;
    const q1=retM(q,qi,21),q3=retM(q,qi,63),q6=retM(q,qi,126);if(q1==null||q3==null||q6==null)continue;const qs=score(q3,q6);
    const u=latestU(us,d),c:any[]=[];
    for(const m of u.symbols){const h=market.histories[m.symbol]??[],idx=maps.get(m.symbol)?.get(d);if(idx==null)continue;const r1=retM(h,idx,21),r3=retM(h,idx,63),r6=retM(h,idx,126);if(r1==null||r3==null||r6==null)continue;const s=score(r3,r6);if(r1>=PRODUCTION_STRATEGY.momentum.surgeLimit||s<=qs)continue;c.push({symbol:m.symbol,score:s,idx,h})}
    c.sort((a,b)=>b.score-a.score||a.symbol.localeCompare(b.symbol));
    const top=c.slice(0,TOPK);
    for(let j=0;j<top.length;j++){const x=top[j],f=featureSet(x.h,x.idx);if(!f)continue;const ei=maps.get(x.symbol)?.get(nextEntry),xi=maps.get(x.symbol)?.get(nextExit);if(ei==null||xi==null)continue;const ep=x.h[ei]?.open,xp=x.h[xi]?.open;if(!ep||!xp||ep<=0||xp<=0)continue;obs.push({signalDate:d,symbol:x.symbol,momentumRank:j+1,forwardReturn:xp/ep-1,features:f})}
  }
  const features=["consistency63","smoothness126","highProximity126","acceleration63"];
  const periods=[
    {name:"2020-2022",from:"2020-01-01",to:"2022-12-31"},
    {name:"2023-2024",from:"2023-01-01",to:"2024-12-31"},
    {name:"2025-2026",from:"2025-01-01",to:"2026-12-31"},
  ];
  const overall=Object.fromEntries(features.map((f,i)=>[f,summarize(obs,f,i*100)]));
  const byPeriod=Object.fromEntries(periods.map((p,pi)=>[p.name,Object.fromEntries(features.map((f,i)=>[f,summarize(obs.filter(o=>o.signalDate>=p.from&&o.signalDate<=p.to),f,1000+pi*100+i)]))]));
  const momentumRankIC=summarize(obs.map(o=>({...o,features:{...o.features,momentumRankNegative:-o.momentumRank}})),"momentumRankNegative",9000);
  const out={generatedAt:new Date().toISOString(),strategyId:PRODUCTION_STRATEGY.strategyId,design:{scope:"actual chronological PIT top-5 eligible candidates",outcome:"next-session-open after signal month-end to next-session-open after following month-end",topK:TOPK,features:{consistency63:"fraction of positive daily returns over trailing 63 sessions; higher is smoother positive persistence",smoothness126:"trailing 126-session max drawdown; higher/less negative is smoother",highProximity126:"close / trailing 126-session high - 1; higher is closer to high",acceleration63:"recent 63-session return minus prior 63-session return; higher means acceleration"}},observations:obs.length,signalMonths:new Set(obs.map(o=>o.signalDate)).size,baselineMomentumRank:momentumRankIC,overall,byPeriod};
  await mkdir(resolve("data/research/momentum-quality"),{recursive:true});
  await writeFile(resolve("data/research/momentum-quality/diagnostics.json"),JSON.stringify(out,null,2));
  console.log("RESULT_JSON="+JSON.stringify(out));
}
main().catch(e=>{console.error(e);process.exit(1)});
