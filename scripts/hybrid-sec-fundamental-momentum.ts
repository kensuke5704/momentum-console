import fs from "node:fs/promises";
import path from "node:path";
import { PRODUCTION_STRATEGY as BASE } from "../src/lib/config";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import { initialEngineState, transitionDay } from "../src/lib/strategy/state-machine";
import { nextUsTradingSession } from "../src/lib/trading-calendar";
import { performanceStats } from "../src/lib/backtest";
import type { EquityPoint, PricePoint, UniverseMonth } from "../src/lib/types";

const CONFIG:any={...BASE,strategyId:"momentum-hybrid-60-70-sec-fundamental",allocation:{...BASE.allocation,baseTop1Weight:.60,concentratedTop1Weight:.70,concentrationZGap:.25,maxTop1Weight:.70}};
const UA="momentum-console-research/1.0 kensuke5704@users.noreply.github.com";

type Factor="BASE"|"SALES_ACCEL"|"MARGIN_DELTA"|"FUND_COMPOSITE";
type Variant={id:string;factor:Factor;lambda:number};
const VARIANTS:Variant[]=[
 {id:"HYBRID_BASE",factor:"BASE",lambda:0},
 {id:"SALES_ACCEL_25",factor:"SALES_ACCEL",lambda:.25},{id:"SALES_ACCEL_50",factor:"SALES_ACCEL",lambda:.50},
 {id:"MARGIN_DELTA_25",factor:"MARGIN_DELTA",lambda:.25},{id:"MARGIN_DELTA_50",factor:"MARGIN_DELTA",lambda:.50},
 {id:"FUND_COMPOSITE_25",factor:"FUND_COMPOSITE",lambda:.25},{id:"FUND_COMPOSITE_50",factor:"FUND_COMPOSITE",lambda:.50},
];

const mean=(x:number[])=>x.length?x.reduce((a,b)=>a+b,0)/x.length:0;
const sd=(x:number[])=>{if(x.length<2)return 0;const m=mean(x);return Math.sqrt(x.reduce((s,v)=>s+(v-m)**2,0)/x.length)};
const z=(v:number,m:number,s:number)=>s>1e-12?(v-m)/s:0;
const sleep=(ms:number)=>new Promise(r=>setTimeout(r,ms));

async function getJson(url:string,retries=4):Promise<any>{
 let last:any;
 for(let i=0;i<retries;i++){
  try{const r=await fetch(url,{headers:{"User-Agent":UA,"Accept-Encoding":"gzip, deflate","Host":new URL(url).host}});if(r.ok)return await r.json();last=new Error(`${r.status} ${r.statusText}`);}catch(e){last=e}
  await sleep(500*(i+1));
 }
 throw last;
}

type Obs={frame:string;filed:string;val:number;form:string;end?:string};
type Series={revenue:Obs[];opIncome:Obs[]};
const REV_TAGS=["RevenueFromContractWithCustomerExcludingAssessedTax","Revenues","SalesRevenueNet","SalesRevenueGoodsNet","SalesRevenueServicesNet"];
const OP_TAGS=["OperatingIncomeLoss"];
function quarterObs(cf:any,tags:string[],unit="USD"):Obs[]{
 const us=cf?.facts?.["us-gaap"]??{};
 for(const tag of tags){const units=us?.[tag]?.units?.[unit];if(!Array.isArray(units))continue;const rows=units.filter((x:any)=>/^CY\d{4}Q[1-4]$/.test(x.frame??"")&&["10-Q","10-K","20-F","40-F"].includes(x.form)&&Number.isFinite(x.val)).map((x:any)=>({frame:x.frame,filed:x.filed,val:Number(x.val),form:x.form,end:x.end}));if(rows.length>=6)return rows;}
 return [];
}
function dedupe(rows:Obs[]):Obs[]{const m=new Map<string,Obs>();for(const r of rows.sort((a,b)=>a.filed.localeCompare(b.filed))){const k=`${r.frame}|${r.filed}`;m.set(k,r)}return [...m.values()];}
function framesUpTo(rows:Obs[],date:string){const by=new Map<string,Obs>();for(const r of rows.filter(x=>x.filed<=date).sort((a,b)=>a.filed.localeCompare(b.filed))){by.set(r.frame,r)}return by;}
function qIndex(frame:string){const m=/^CY(\d{4})Q([1-4])$/.exec(frame);return m?Number(m[1])*4+Number(m[2])-1:null;}
function frameFromIndex(i:number){const y=Math.floor(i/4),q=i%4+1;return `CY${y}Q${q}`;}
function latestCommonQuarter(rev:Map<string,Obs>,op:Map<string,Obs>){const fs=[...rev.keys()].filter(f=>op.has(f)).sort((a,b)=>(qIndex(b)??0)-(qIndex(a)??0));return fs[0]??null;}
function metricAt(s:Series,date:string){
 const rev=framesUpTo(s.revenue,date),op=framesUpTo(s.opIncome,date);const latest=[...rev.keys()].sort((a,b)=>(qIndex(b)??0)-(qIndex(a)??0))[0];if(!latest)return null;const qi=qIndex(latest);if(qi===null)return null;
 const r0=rev.get(latest)?.val,r4=rev.get(frameFromIndex(qi-4))?.val,r1=rev.get(frameFromIndex(qi-1))?.val,r5=rev.get(frameFromIndex(qi-5))?.val;
 const salesYoy=r0&&r4&&r4!==0?r0/r4-1:null;const prevYoy=r1&&r5&&r5!==0?r1/r5-1:null;const salesAccel=salesYoy!==null&&prevYoy!==null?salesYoy-prevYoy:null;
 const common=latestCommonQuarter(rev,op);let marginDelta:null|number=null;if(common){const ci=qIndex(common)!;const rc=rev.get(common)?.val,oc=op.get(common)?.val,ry=rev.get(frameFromIndex(ci-4))?.val,oy=op.get(frameFromIndex(ci-4))?.val;if(rc&&ry&&oc!==undefined&&oy!==undefined&&rc!==0&&ry!==0)marginDelta=oc/rc-oy/ry;}
 return{salesYoy,salesAccel,marginDelta,latestFrame:latest};
}

async function loadSeries(symbols:string[]){
 const ticks=await getJson("https://www.sec.gov/files/company_tickers.json");const map=new Map<string,string>();for(const v of Object.values(ticks) as any[]){map.set(String(v.ticker).toUpperCase(),String(v.cik_str).padStart(10,"0"));}
 const out=new Map<string,Series>();const failures:any[]=[];let cursor=0;
 async function worker(){while(true){const i=cursor++;if(i>=symbols.length)return;const sym=symbols[i],cik=map.get(sym.toUpperCase());if(!cik){failures.push({sym,reason:"no-cik"});continue;}try{const cf=await getJson(`https://data.sec.gov/api/xbrl/companyfacts/CIK${cik}.json`);const revenue=dedupe(quarterObs(cf,REV_TAGS)),opIncome=dedupe(quarterObs(cf,OP_TAGS));out.set(sym,{revenue,opIncome});}catch(e:any){failures.push({sym,reason:String(e?.message??e)});}await sleep(130);}}
 await Promise.all(Array.from({length:4},()=>worker()));return{out,failures};
}

function customSignal(u:UniverseMonth,hist:Record<string,PricePoint[]>,qqq:PricePoint[],next:string,v:Variant,factors:Map<string,Map<string,any>>){
 const base:any=buildMonthlySignal({universe:u,histories:hist,qqq,nextSessionDate:next,config:CONFIG});if(v.factor==="BASE"||!base.marketRiskOn)return base;const eligible=base.candidates.filter((c:any)=>c.eligible&&c.score!==null);if(eligible.length<2)return base;
 const fm=factors.get(u.asOf);const raw=eligible.map((c:any)=>({c,m:fm?.get(c.symbol)})).filter((x:any)=>x.m);if(raw.length<2)return base;
 const sales=raw.filter((x:any)=>x.m.salesAccel!==null).map((x:any)=>x.m.salesAccel),marg=raw.filter((x:any)=>x.m.marginDelta!==null).map((x:any)=>x.m.marginDelta);const sam=mean(sales),sas=sd(sales),mam=mean(marg),mas=sd(marg);
 const rows=raw.map((x:any)=>{let fv:null|number=null;if(v.factor==="SALES_ACCEL")fv=x.m.salesAccel;else if(v.factor==="MARGIN_DELTA")fv=x.m.marginDelta;else if(x.m.salesAccel!==null&&x.m.marginDelta!==null)fv=z(x.m.salesAccel,sam,sas)+z(x.m.marginDelta,mam,mas);return{...x,fv};}).filter((x:any)=>x.fv!==null);
 if(rows.length<2)return base;const sm=mean(rows.map((x:any)=>x.c.score)),ss=sd(rows.map((x:any)=>x.c.score)),fmv=mean(rows.map((x:any)=>x.fv)),fsv=sd(rows.map((x:any)=>x.fv));const ranked=rows.map((x:any)=>({...x,combo:z(x.c.score,sm,ss)+v.lambda*z(x.fv,fmv,fsv)})).sort((a:any,b:any)=>b.combo-a.combo||a.c.symbol.localeCompare(b.c.symbol));const sel=ranked.slice(0,2);if(sel.length<2)return base;const combos=ranked.map((x:any)=>x.combo),disp=sd(combos),zg=disp>0?(sel[0].combo-sel[1].combo)/disp:0,conc=zg>=CONFIG.allocation.concentrationZGap,top1=conc?.70:.60;return{...base,selectedSymbols:sel.map((x:any)=>x.c.symbol),targetWeights:[top1,1-top1],zGap:zg,allocationMode:conc?"70/30":"60/40"};
}
function sim(hist:Record<string,PricePoint[]>,universe:UniverseMonth[],v:Variant,factors:Map<string,Map<string,any>>){const qqq=[...(hist.QQQ??[])].sort((a,b)=>a.date.localeCompare(b.date)),dates=qqq.map(p=>p.date),di=new Map(dates.map((d,i)=>[d,i])),pm=Object.fromEntries(Object.entries(hist).map(([s,ps])=>[s,new Map(ps.map(p=>[p.date,p]))])),um=new Map(universe.map(x=>[x.asOf,x]));let st=initialEngineState(CONFIG);const curve:EquityPoint[]=[];for(let i=0;i<dates.length;i++){const date=dates[i];if(date<CONFIG.backtestStart)continue;const next=dates[i+1]??nextUsTradingSession(date),u=um.get(date),sig=u?customSignal(u,hist,qqq,next,v,factors):null,sy=new Set(["QQQ",...st.currentPositions.map(p=>p.symbol),...(st.pendingSignal?.selectedSymbols??[]),...st.nextAction.symbols,...(sig?.selectedSymbols??[])]),prices=Object.fromEntries([...sy].map(s=>[s,pm[s]?.get(date)]));st=transitionDay(st,{date,prices,qqqHistoryThroughClose:qqq.slice(0,(di.get(date)??i)+1),monthlySignal:sig,nextSessionDate:next},CONFIG);curve.push({date,equity:st.currentEquity,drawdown:st.drawdown});}return curve;}
function normSlice(c:EquityPoint[],s:string,e:string){const x=c.filter(p=>p.date>=s&&p.date<=e);if(x.length<2)return[];const b=x[0].equity;return x.map(p=>({...p,equity:p.equity/b}));}

async function main(){
 const market=JSON.parse(await fs.readFile(path.join(process.cwd(),"public/data/market-data.json"),"utf8")) as {histories:Record<string,PricePoint[]>};const uf=JSON.parse(await fs.readFile(path.join(process.cwd(),"data/universe-history.json"),"utf8")) as {history:UniverseMonth[]};const universe=[...uf.history].filter(x=>x.asOf>=CONFIG.backtestStart).sort((a,b)=>a.asOf.localeCompare(b.asOf));const symbols=[...new Set(universe.flatMap(u=>u.symbols.map((x:any)=>typeof x==="string"?x:x.symbol)))].filter(Boolean).sort();console.log("SEC fetch symbols",symbols.length);const loaded=await loadSeries(symbols);console.log("SEC loaded",loaded.out.size,"failures",loaded.failures.length);
 const factors=new Map<string,Map<string,any>>();const coverage:any[]=[];for(const u of universe){const m=new Map<string,any>();for(const raw of u.symbols as any[]){const sym=typeof raw==="string"?raw:raw.symbol;const s=loaded.out.get(sym);if(!s)continue;const x=metricAt(s,u.asOf);if(x)m.set(sym,x);}factors.set(u.asOf,m);const vals=[...m.values()];coverage.push({date:u.asOf,total:u.symbols.length,any:m.size,salesAccel:vals.filter(x=>x.salesAccel!==null).length,marginDelta:vals.filter(x=>x.marginDelta!==null).length});}
 const curves=new Map<string,EquityPoint[]>();for(const v of VARIANTS){console.log("run",v.id);curves.set(v.id,sim(market.histories,universe,v,factors));}
 const full=VARIANTS.map(v=>({variant:v,...performanceStats(curves.get(v.id)!)}));const splits=[] as any[];for(const y of [2022,2023,2024,2025,2026]){const trainEnd=`${y-1}-12-31`,oosEnd=y===2026?"2026-08-25":`${y}-12-31`;const train=VARIANTS.map(v=>({v,stats:performanceStats(normSlice(curves.get(v.id)!,"2020-01-01",trainEnd))})).sort((a,b)=>(b.stats.calmar??-Infinity)-(a.stats.calmar??-Infinity));const chosen=train[0].v,base=performanceStats(normSlice(curves.get("HYBRID_BASE")!,`${y}-01-01`,oosEnd)),oos=performanceStats(normSlice(curves.get(chosen.id)!,`${y}-01-01`,oosEnd));splits.push({trainThrough:y-1,oosYear:y,chosen:chosen.id,trainCalmar:train[0].stats.calmar,oos,hybridBase:base,cagrDiff:oos.cagr-base.cagr});}
 const med=(a:number[])=>{const x=[...a].sort((a,b)=>a-b);return x.length?x[Math.floor(x.length/2)]:null};const out={generatedAt:new Date().toISOString(),method:{data:"SEC companyfacts, free public XBRL",pit:"only observations with filed <= signal close",quarterIdentification:"SEC CYyyyyQn frame",baseline:"Hybrid 60/40, 70/30 when zGap>=0.25",factors:{SALES_ACCEL:"current revenue YoY growth minus prior-quarter revenue YoY growth",MARGIN_DELTA:"operating margin minus same calendar-quarter prior-year operating margin",FUND_COMPOSITE:"cross-sectional standardized SALES_ACCEL + MARGIN_DELTA"},blend:"z(momentum)+lambda*z(fundamental), lambda 0.25/0.50",selection:"training-only Calmar then next-calendar-year pseudo-OOS"},validity:{freeDataOnly:true,trueOOS:false,architectureHindsightRemains:true,noLeverage:true,warning:"SEC tag/frame coverage varies by issuer. This is retrospective anchored pseudo-OOS inside an already-observed sample."},sourceCoverage:{uniqueSymbols:symbols.length,loaded:loaded.out.size,failures:loaded.failures,monthlyMedianAny:med(coverage.map(x=>x.any)),monthlyMedianSalesAccel:med(coverage.map(x=>x.salesAccel)),monthlyMedianMarginDelta:med(coverage.map(x=>x.marginDelta)),coverage},full,splits};const dir=path.join(process.cwd(),"data/research/hybrid-sec-fundamental-momentum");await fs.mkdir(dir,{recursive:true});await fs.writeFile(path.join(dir,"result.json"),JSON.stringify(out,null,2));console.log(JSON.stringify({sourceCoverage:out.sourceCoverage,full,splits},null,2));}
main().catch(e=>{console.error(e);process.exit(1)});