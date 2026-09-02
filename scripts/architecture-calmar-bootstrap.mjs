import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const START='2020-01-01', START_TOL='2020-01-10', END='2026-08-25', END_TOL='2026-08-20';
const B=3000, SEED=29092026;
const BLOCKS=[5,10,20,60];
const TARGET={cagr:.48607237745471776,maxDrawdown:-.16885951856003312};
const FIXED60_TARGET={cagr:.6199809387396764,maxDrawdown:-.31127223620169275};
const mean=x=>x.reduce((a,b)=>a+b,0)/(x.length||1);
const quantile=(xs,p)=>{const a=[...xs].sort((x,y)=>x-y);if(!a.length)return null;const z=(a.length-1)*p,i=Math.floor(z),f=z-i;return a[i+1]===undefined?a[i]:a[i]*(1-f)+a[i+1]*f};
function curveStats(curve){const first=curve[0],last=curve.at(-1),years=(Date.parse(last.date)-Date.parse(first.date))/(365.25*86400000);let peak=first.equity,dd=0;for(const x of curve){peak=Math.max(peak,x.equity);dd=Math.min(dd,x.equity/peak-1)}const cagr=(last.equity/first.equity)**(1/years)-1;return{cagr,maxDrawdown:dd,calmar:dd<0?cagr/Math.abs(dd):null,finalEquity:last.equity};}
function returns(curve){return curve.slice(1).map((p,i)=>({date:p.date,r:p.equity/curve[i].equity-1}));}
function calmarFromReturns(rs,years){let eq=1,peak=1,dd=0;for(const r of rs){eq*=1+r;peak=Math.max(peak,eq);dd=Math.min(dd,eq/peak-1)}const cagr=eq**(1/years)-1;return{cagr,maxDrawdown:dd,calmar:dd<0?cagr/Math.abs(dd):Infinity};}
function rng(seed){let s=seed>>>0;return()=>{s=(1664525*s+1013904223)>>>0;return s/4294967296};}
function stationaryIndices(n,block,rand){const out=new Int32Array(n),p=1/block;let idx=Math.floor(rand()*n);for(let j=0;j<n;j++){if(j===0||rand()<p)idx=Math.floor(rand()*n);else idx=(idx+1)%n;out[j]=idx}return out;}

const files=process.argv.slice(2);if(!files.length)throw new Error('capture files required');
const raw=[];for(const file of files){let text='';try{text=await readFile(file,'utf8')}catch{continue}for(const line of text.split(/\n+/)){if(!line.trim())continue;try{raw.push(JSON.parse(line))}catch{}}}
const eligible=raw.filter(x=>x?.curve?.length>=1500&&x.curve[0].date<=START_TOL&&x.curve.at(-1).date>=END_TOL&&String(x.script??'').length>0);
const unique=[];const seen=new Set();for(const x of eligible){const c=x.curve.filter(p=>p.date>=START&&p.date<=END);if(c.length<1500)continue;const sig=createHash('sha256').update(c.slice(1).map((p,i)=>`${p.date}:${(p.equity/c[i].equity-1).toFixed(10)}`).join('|')).digest('hex');if(seen.has(sig))continue;seen.add(sig);unique.push({script:x.script,curve:c,stats:curveStats(c),signature:sig});}
if(!unique.length)throw new Error(`no eligible curves: raw=${raw.length} eligible=${eligible.length}`);
let selectedIndex=0,selectedDist=Infinity,fixedIndex=0,fixedDist=Infinity;
unique.forEach((u,i)=>{const ds=Math.abs(u.stats.cagr-TARGET.cagr)+Math.abs(u.stats.maxDrawdown-TARGET.maxDrawdown);if(ds<selectedDist){selectedDist=ds;selectedIndex=i}const df=Math.abs(u.stats.cagr-FIXED60_TARGET.cagr)+Math.abs(u.stats.maxDrawdown-FIXED60_TARGET.maxDrawdown);if(df<fixedDist){fixedDist=df;fixedIndex=i}});
const observed=[...unique].map((u,i)=>({i,script:u.script,...u.stats})).sort((a,b)=>(b.calmar??-Infinity)-(a.calmar??-Infinity));
const observedRank=observed.findIndex(x=>x.i===selectedIndex)+1;
const observedPercentile=1-(observedRank-1)/(observed.length-1);
const commonDates=returns(unique[0].curve).map(x=>x.date);
const maps=unique.map(u=>new Map(returns(u.curve).map(x=>[x.date,x.r])));
const dates=commonDates.filter(d=>maps.every(m=>m.has(d)));
if(dates.length<1500)throw new Error(`common sample too short: ${dates.length}`);
const matrix=maps.map(m=>Float64Array.from(dates.map(d=>m.get(d))));
const years=(Date.parse(END)-Date.parse(START))/(365.25*86400000);
const bootstrap=[];
for(const block of BLOCKS){const rand=rng(SEED+block);const stageCal=[],stageRank=[],fixedCal=[],stageMinusFixed=[];let top1=0,top10=0,topQuartile=0,gtFixed=0;for(let b=0;b<B;b++){const idx=stationaryIndices(dates.length,block,rand);const vals=new Float64Array(unique.length);for(let i=0;i<unique.length;i++){const rs=Array.from(idx,j=>matrix[i][j]);vals[i]=calmarFromReturns(rs,years).calmar}const s=vals[selectedIndex],f=vals[fixedIndex];let rank=1;for(let i=0;i<vals.length;i++)if(vals[i]>s)rank++;stageCal.push(s);fixedCal.push(f);stageMinusFixed.push(s-f);stageRank.push(rank);if(rank===1)top1++;if(rank<=Math.ceil(vals.length*.10))top10++;if(rank<=Math.ceil(vals.length*.25))topQuartile++;if(s>f)gtFixed++;}
bootstrap.push({block,replications:B,stage21Calmar:{median:quantile(stageCal,.5),p025:quantile(stageCal,.025),p975:quantile(stageCal,.975)},fixed60Calmar:{median:quantile(fixedCal,.5),p025:quantile(fixedCal,.025),p975:quantile(fixedCal,.975)},stage21MinusFixed60:{median:quantile(stageMinusFixed,.5),p025:quantile(stageMinusFixed,.025),p975:quantile(stageMinusFixed,.975),probPositive:gtFixed/B},stage21Rank:{median:quantile(stageRank,.5),p025:quantile(stageRank,.025),p975:quantile(stageRank,.975),probTop1:top1/B,probTop10Pct:top10/B,probTopQuartile:topQuartile/B}});}
console.log(JSON.stringify({method:'Architecture-level Calmar robustness screen using shared stationary bootstrap. Descriptive/rank-stability analysis, not a Hansen SPA p-value.',capture:{rawCalls:raw.length,eligibleFullPeriodCalls:eligible.length,uniqueFullPeriodCurves:unique.length},sample:{start:START,end:END,commonDays:dates.length},observed:{stage21:{index:selectedIndex,script:unique[selectedIndex].script,...unique[selectedIndex].stats,distanceToFrozenReference:selectedDist,rankByCalmar:observedRank,percentileByCalmar:observedPercentile},fixed60Like:{index:fixedIndex,script:unique[fixedIndex].script,...unique[fixedIndex].stats,distanceToReference:fixedDist},top10ByCalmar:observed.slice(0,10)},bootstrap,interpretationNote:'Because Calmar is a nonlinear path-dependent full-sample statistic, these are bootstrap stability and paired-comparison probabilities rather than canonical SPA family-wise p-values.'},null,2));