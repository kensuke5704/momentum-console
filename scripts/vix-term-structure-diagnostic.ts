import fs from 'node:fs/promises';
import path from 'node:path';
import { PRODUCTION_STRATEGY } from '../src/lib/config';
import { buildMonthlySignal } from '../src/lib/strategy/momentum';
import { nextUsTradingSession } from '../src/lib/trading-calendar';
import type { PricePoint, UniverseMonth, StrategyConfig } from '../src/lib/types';

const cfg:StrategyConfig={...PRODUCTION_STRATEGY,allocation:{...PRODUCTION_STRATEGY.allocation,baseTop1Weight:.6,concentratedTop1Weight:.6,concentrationZGap:999,maxTop1Weight:.6}};
async function yh(s:string,start='2019-01-01'){
 const a=Math.floor(Date.parse(start+'T00:00:00Z')/1000),b=Math.floor(Date.parse('2026-09-01T00:00:00Z')/1000);
 const r=await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(s)}?period1=${a}&period2=${b}&interval=1d&events=div%2Csplits&includeAdjustedClose=true`,{headers:{'User-Agent':'Mozilla/5.0'}});if(!r.ok)throw Error(`${s}:${r.status}`);
 const j:any=await r.json(),x=j.chart.result?.[0];if(!x)throw Error(`${s}:no result`);const q=x.indicators.quote[0];return x.timestamp.map((t:number,i:number)=>q.close[i]!=null?{date:new Date(t*1000).toISOString().slice(0,10),open:q.open[i]??q.close[i],close:q.close[i]}as PricePoint:null).filter(Boolean)as PricePoint[];
}
function rank(a:number[]){const idx=a.map((v,i)=>({v,i})).sort((x,y)=>x.v-y.v),r=Array(a.length).fill(0);for(let i=0;i<idx.length;){let j=i;while(j+1<idx.length&&idx[j+1].v===idx[i].v)j++;const rr=(i+j)/2+1;for(let k=i;k<=j;k++)r[idx[k].i]=rr;i=j+1;}return r;}
function corr(x:number[],y:number[]){if(x.length<3)return null;const mx=x.reduce((a,b)=>a+b,0)/x.length,my=y.reduce((a,b)=>a+b,0)/y.length;let n=0,dx=0,dy=0;for(let i=0;i<x.length;i++){const a=x[i]-mx,b=y[i]-my;n+=a*b;dx+=a*a;dy+=b*b;}return dx>0&&dy>0?n/Math.sqrt(dx*dy):null;}
function spearman(x:number[],y:number[]){return corr(rank(x),rank(y));}
function mean(x:number[]){return x.length?x.reduce((a,b)=>a+b,0)/x.length:null;}
function median(x:number[]){if(!x.length)return null;const a=[...x].sort((p,q)=>p-q),m=Math.floor(a.length/2);return a.length%2?a[m]:(a[m-1]+a[m])/2;}
function next21(hist:Record<string,PricePoint[]>,symbol:string,d:string){const x=(hist[symbol]??[]).filter(p=>p.date>d&&p.open&&p.close);if(x.length<21)return null;return x[20].close/x[0].open-1;}
function port21(hist:Record<string,PricePoint[]>,symbols:string[],weights:number[],d:string){const rs=symbols.map(s=>next21(hist,s,d));if(rs.some(x=>x==null))return null;return rs.reduce((a,r,i)=>a+(r as number)*(weights[i]??0),0);}
async function main(){
 const market=JSON.parse(await fs.readFile(path.join(process.cwd(),'public/data/market-data.json'),'utf8'))as{histories:Record<string,PricePoint[]>},uf=JSON.parse(await fs.readFile(path.join(process.cwd(),'data/universe-history.json'),'utf8'))as{history:UniverseMonth[]},u=[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf));
 const vix=await yh('^VIX'),vix3m=await yh('^VIX3M'),vm=new Map(vix.map(x=>[x.date,x.close])),v3m=new Map(vix3m.map(x=>[x.date,x.close])),q=[...market.histories.QQQ].sort((a,b)=>a.date.localeCompare(b.date));
 const obs:any[]=[];
 for(const um of u){if(um.asOf<'2020-01-01'||um.asOf>'2026-08-25')continue;const sig=buildMonthlySignal({universe:um,histories:market.histories,qqq:q,nextSessionDate:nextUsTradingSession(um.asOf),config:cfg});if(!sig.marketRiskOn||sig.selectedSymbols.length!==2)continue;const a=vm.get(um.asOf),b=v3m.get(um.asOf);if(!a||!b||b<=0)continue;const weights=[.6,.4],r=port21(market.histories,sig.selectedSymbols,weights,um.asOf);if(r==null)continue;obs.push({date:um.asOf,ratio:a/b,backwardation:a>b,return21:r,symbols:sig.selectedSymbols});}
 function summary(start:string,end:string){const x=obs.filter(o=>o.date>=start&&o.date<=end),back=x.filter(o=>o.backwardation),normal=x.filter(o=>!o.backwardation);return{n:x.length,backwardationN:back.length,normalN:normal.length,spearmanRatioReturn21:spearman(x.map(o=>o.ratio),x.map(o=>o.return21)),backwardationMean21:mean(back.map(o=>o.return21)),normalMean21:mean(normal.map(o=>o.return21)),backwardationMedian21:median(back.map(o=>o.return21)),normalMedian21:median(normal.map(o=>o.return21)),meanSpreadBackwardationMinusNormal:(mean(back.map(o=>o.return21))??NaN)-(mean(normal.map(o=>o.return21))??NaN),medianSpreadBackwardationMinusNormal:(median(back.map(o=>o.return21))??NaN)-(median(normal.map(o=>o.return21))??NaN)};}
 const early=summary('2020-01-01','2023-12-31'),late=summary('2024-01-01','2026-08-25');
 const pass=early.n>=20&&late.n>=12&&early.backwardationN>=3&&late.backwardationN>=3&&(early.spearmanRatioReturn21??1)<0&&(late.spearmanRatioReturn21??1)<0&&early.meanSpreadBackwardationMinusNormal<0&&late.meanSpreadBackwardationMinusNormal<0&&early.medianSpreadBackwardationMinusNormal<=0&&late.medianSpreadBackwardationMinusNormal<=0;
 const out={generatedAt:new Date().toISOString(),validity:{researchOnly:true,trueOOS:false,parameterSearch:false,pit:true,hypothesis:'At monthly Production Risk-On signals, higher close-to-close VIX/VIX3M predicts lower next-21-session Fixed60 selected-portfolio returns.',fixedBoundary:'VIX > VIX3M (backwardation) only; no threshold search.',future:'First US session open strictly after signal close through the 21st session close.',weights:'Fixed60 60/40 for the two selected symbols.',passGate:'Negative Spearman IC in both 2020-23 and 2024-26; backwardation mean and median return spreads negative in both; at least 3 backwardation observations per period.'},coverage:{observations:obs.length},early2020_2023:early,late2024_2026:late,passGate:pass,observations:obs};
 const d=path.join(process.cwd(),'data/research/vix-term-structure-diagnostic');await fs.mkdir(d,{recursive:true});await fs.writeFile(path.join(d,'result.json'),JSON.stringify(out,null,2));console.log(JSON.stringify({...out,observations:undefined},null,2));
}
main().catch(e=>{console.error(e);process.exit(1)});
