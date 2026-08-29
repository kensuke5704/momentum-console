import fs from "node:fs/promises";
import path from "node:path";
import { runBacktest } from "../src/lib/backtest";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import type { PricePoint, UniverseMonth } from "../src/lib/types";

type Day={date:string;logReturn:number;good:boolean;highVol:boolean};
type Stats={totalReturn:number;cagr:number;maxDD:number;terminal:number};
const mean=(x:number[])=>x.length?x.reduce((a,b)=>a+b,0)/x.length:0;
const stdev=(x:number[])=>{if(x.length<2)return 0;const m=mean(x);return Math.sqrt(x.reduce((s,v)=>s+(v-m)**2,0)/(x.length-1));};
function stats(rs:number[],dates:string[]):Stats{let eq=1,peak=1,maxDD=0;for(const r of rs){eq*=Math.exp(r);peak=Math.max(peak,eq);maxDD=Math.min(maxDD,eq/peak-1);}const years=(Date.parse(dates.at(-1)!)-Date.parse(dates[0]))/(365.25*86400000);return{totalReturn:eq-1,cagr:eq**(1/years)-1,maxDD,terminal:eq};}
function quantile(v:number[],q:number){const x=[...v].sort((a,b)=>a-b);const p=(x.length-1)*q,l=Math.floor(p),h=Math.ceil(p);return l===h?x[l]:x[l]*(h-p)+x[h]*(p-l);}
function mulberry32(a:number){return()=>{let t=a+=0x6D2B79F5;t=Math.imul(t^t>>>15,t|1);t^=t+Math.imul(t^t>>>7,t|61);return((t^t>>>14)>>>0)/4294967296;}}
async function main(){
 const market=JSON.parse(await fs.readFile(path.join(process.cwd(),"public/data/market-data.json"),"utf8")) as {histories:Record<string,PricePoint[]>};
 const uf=JSON.parse(await fs.readFile(path.join(process.cwd(),"data/universe-history.json"),"utf8")) as {history:UniverseMonth[]};
 const histories=market.histories,universe=[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf));
 const bt=runBacktest({histories,universeHistory:universe,config:PRODUCTION_STRATEGY});const curve=bt.equityCurve;
 const qqq=[...(histories.QQQ??[])].sort((a,b)=>a.date.localeCompare(b.date));const qi=new Map(qqq.map((p,i)=>[p.date,i]));
 const days:Day[]=[];
 for(let i=1;i<curve.length;i++){const prev=curve[i-1],today=curve[i],j=qi.get(prev.date);if(j===undefined||j<199)continue;const q=qqq[j];const sma200=mean(qqq.slice(j-199,j+1).map(p=>p.close));const rets=qqq.slice(j-19,j+1).map((p,k,a)=>k?Math.log(p.close/a[k-1].close):null).filter((v):v is number=>v!==null);const rv=stdev(rets)*Math.sqrt(252);const up=q.close>sma200,high=rv>=.30;days.push({date:today.date,logReturn:Math.log(today.equity/prev.equity),good:up&&!high,highVol:high});}
 const dates=days.map(d=>d.date),baseR=days.map(d=>d.logReturn),base=stats(baseR,dates);const goodRs=days.filter(d=>d.good).map(d=>d.logReturn);const muGood=mean(goodRs);const goodShare=goodRs.length/days.length;const highShare=days.filter(d=>d.highVol).length/days.length;
 const edgeRetention=[1,.75,.5,.25,0];
 const driftStress=edgeRetention.map(ret=>{const rs=days.map(d=>d.good?d.logReturn-(1-ret)*muGood:d.logReturn);return{edgeRetention:ret,...stats(rs,dates)};});
 const opportunities=[1,.8,.6];const combined=[] as any[];const draws=20000,seed=20260830;
 for(const edge of [.75,.5,.25])for(const opp of opportunities){const cagrs:number[]=[],dds:number[]=[],terms:number[]=[];const rng=mulberry32(seed+Math.round(edge*1000)+Math.round(opp*10000));for(let b=0;b<draws;b++){const rs=days.map(d=>{let r=d.good?d.logReturn-(1-edge)*muGood:d.logReturn;if(d.good&&rng()>opp)r=0;return r;});const s=stats(rs,dates);cagrs.push(s.cagr);dds.push(s.maxDD);terms.push(s.terminal);}combined.push({edgeRetention:edge,opportunityRetention:opp,draws,cagrMedian:quantile(cagrs,.5),cagrP10:quantile(cagrs,.1),cagrP90:quantile(cagrs,.9),maxDDMedian:quantile(dds,.5),maxDDP10:quantile(dds,.1),maxDDP90:quantile(dds,.9),probCagrBelow0:cagrs.filter(x=>x<0).length/draws,probCagrBelow10:cagrs.filter(x=>x<.10).length/draws,probMaxDDBelowMinus50:dds.filter(x=>x<-.50).length/draws,terminalMedian:quantile(terms,.5)});}
 // Adverse-shock sensitivity: preserve all historical returns, then add extra loss shocks on randomly chosen good-regime days.
 const shocks=[] as any[];for(const shock of [.05,.10,.15]){const eventsPerYear=[.5,1,2];for(const freq of eventsPerYear){const cagrs:number[]=[],dds:number[]=[];const rng=mulberry32(seed+Math.round(shock*10000)+Math.round(freq*100));const p=freq/252;for(let b=0;b<draws;b++){const rs=days.map(d=>{let r=d.logReturn;if(d.good&&rng()<p)r+=Math.log(1-shock);return r;});const s=stats(rs,dates);cagrs.push(s.cagr);dds.push(s.maxDD);}shocks.push({shockSize:shock,eventsPerYear:freq,draws,cagrMedian:quantile(cagrs,.5),cagrP10:quantile(cagrs,.1),maxDDMedian:quantile(dds,.5),maxDDP10:quantile(dds,.1),probMaxDDBelowMinus50:dds.filter(x=>x<-.50).length/draws});}}
 const out={generatedAt:new Date().toISOString(),strategyId:PRODUCTION_STRATEGY.strategyId,method:"Structural return-process stress. Good regime = prior-close QQQ above 200DMA AND 20D realized vol <30%. Edge-retention stress subtracts a fraction of the historical good-regime mean daily log return while preserving daily residuals/losses. Opportunity stress independently converts a fraction of good-regime days to cash. Shock sensitivity injects additional discrete losses. 20,000 Monte Carlo masks per combined scenario.",validity:{trueOOS:false,stateMachineRerun:false,descriptiveCounterfactual:true,architectureHindsightRemains:true,warning:"These are conditional counterfactual stresses, not estimated probabilities of future structural changes. Opportunity masking and shock injection perturb realized strategy returns rather than re-running signals/positions; use them for sensitivity, not forecast calibration."},sample:{start:dates[0],end:dates.at(-1),days:days.length,goodRegimeDayShare:goodShare,highVolDayShare:highShare,goodRegimeMeanDailyLogReturn:muGood},baseline:base,driftStress,combined,shockSensitivity:shocks};
 const dir=path.join(process.cwd(),"data/research/structural-stress");await fs.mkdir(dir,{recursive:true});await fs.writeFile(path.join(dir,"result.json"),JSON.stringify(out,null,2));console.log(JSON.stringify({baseline:base,driftStress,combined,shockSensitivity:shocks},null,2));
}
main().catch(e=>{console.error(e);process.exit(1)});
