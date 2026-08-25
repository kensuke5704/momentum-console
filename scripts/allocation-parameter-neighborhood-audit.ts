import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { runBacktest } from "../src/lib/backtest";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import type { BacktestResult, PricePoint, StrategyConfig, UniverseMonth } from "../src/lib/types";

type MarketFile = { histories: Record<string, PricePoint[]> };
type UniverseFile = { history: UniverseMonth[] };
type Group = "production" | "zgap" | "weight" | "fixed";
type Scenario = { group: Group; label: string; value: number; config: StrategyConfig };

const cloneConfig = (): StrategyConfig => structuredClone(PRODUCTION_STRATEGY) as StrategyConfig;
const avg = (x:number[]) => x.length ? x.reduce((a,b)=>a+b,0)/x.length : NaN;
function popSd(x:number[]){if(!x.length)return NaN;const m=avg(x);return Math.sqrt(avg(x.map(v=>(v-m)**2)));}
function pearson(x:number[],y:number[]){if(x.length!==y.length||x.length<3)return NaN;const mx=avg(x),my=avg(y),sx=popSd(x),sy=popSd(y);if(!sx||!sy)return NaN;return avg(x.map((v,i)=>(v-mx)*(y[i]-my)))/(sx*sy);}
function ranks(x:number[]){const idx=x.map((v,i)=>({v,i})).sort((a,b)=>a.v-b.v);const r=new Array(x.length);for(let i=0;i<idx.length;){let j=i;while(j+1<idx.length&&idx[j+1].v===idx[i].v)j++;const rr=(i+j+2)/2;for(let k=i;k<=j;k++)r[idx[k].i]=rr;i=j+1;}return r;}
function spearman(x:number[],y:number[]){return pearson(ranks(x),ranks(y));}

function scenario(group: Group, label: string, value: number, mutate:(c:StrategyConfig)=>void): Scenario {
  const config=cloneConfig(); mutate(config); config.strategyId=`${PRODUCTION_STRATEGY.strategyId}-audit-${label}`; return {group,label,value,config};
}
function countReason(result:BacktestResult, needle:string){return result.events.filter(e=>e.type==="EXIT_OPEN"&&e.reason.includes(needle)).length;}
function metrics(s:Scenario,result:BacktestResult){return {group:s.group,label:s.label,value:s.value,cagr:result.stats.cagr,maxDrawdown:result.stats.maxDrawdown,annualizedVolatility:result.stats.annualizedVolatility,calmar:result.stats.calmar,finalEquity:result.stats.finalEquity,stopExits:countReason(result,"% stop"),circuitExits:countReason(result,"% circuit")};}

function nextSession(hist:PricePoint[], date:string){return hist.find(p=>p.date>date)?.date??null;}
function priceMap(histories:Record<string,PricePoint[]>){return Object.fromEntries(Object.entries(histories).map(([s,ps])=>[s,new Map(ps.map(p=>[p.date,p]))]));}

function signalDiagnostics(histories:Record<string,PricePoint[]>, universeHistory:UniverseMonth[]){
  const qqq=[...(histories.QQQ??[])].sort((a,b)=>a.date.localeCompare(b.date));
  const maps=priceMap(histories);
  const us=[...universeHistory].sort((a,b)=>a.asOf.localeCompare(b.asOf));
  const rows:{month:string;zGap:number;top1:string;top2:string;top1Return:number;top2Return:number;spread:number}[]=[];
  for(let i=0;i<us.length-1;i++){
    const u=us[i], nextU=us[i+1];
    if(u.asOf<PRODUCTION_STRATEGY.backtestStart)continue;
    const entry=nextSession(qqq,u.asOf), exit=nextSession(qqq,nextU.asOf);
    if(!entry||!exit)continue;
    const sig=buildMonthlySignal({universe:u,histories,qqq,nextSessionDate:entry,config:PRODUCTION_STRATEGY});
    if(!sig.marketRiskOn||sig.selectedSymbols.length!==2||sig.zGap==null)continue;
    const [a,b]=sig.selectedSymbols;
    const ao=maps[a]?.get(entry)?.open, ax=maps[a]?.get(exit)?.open, bo=maps[b]?.get(entry)?.open, bx=maps[b]?.get(exit)?.open;
    if(!ao||!ax||!bo||!bx)continue;
    const r1=ax/ao-1,r2=bx/bo-1;
    rows.push({month:u.signalMonth,zGap:sig.zGap,top1:a,top2:b,top1Return:r1,top2Return:r2,spread:r1-r2});
  }
  const summarize=(xs:typeof rows)=>({n:xs.length,meanZGap:avg(xs.map(x=>x.zGap)),meanTop1:avg(xs.map(x=>x.top1Return)),meanTop2:avg(xs.map(x=>x.top2Return)),meanSpread:avg(xs.map(x=>x.spread)),top1WinRate:xs.length?xs.filter(x=>x.spread>0).length/xs.length:NaN});
  const thresholds=[0.15,0.25,0.35].map(t=>({threshold:t,concentrated:summarize(rows.filter(x=>x.zGap>=t)),notConcentrated:summarize(rows.filter(x=>x.zGap<t)),concentratedShare:rows.length?rows.filter(x=>x.zGap>=t).length/rows.length:NaN}));
  return {n:rows.length,spearmanZGapVsForwardSpread:spearman(rows.map(x=>x.zGap),rows.map(x=>x.spread)),pearsonZGapVsForwardSpread:pearson(rows.map(x=>x.zGap),rows.map(x=>x.spread)),thresholds,rows};
}

async function main(){
  const market=JSON.parse(await readFile(resolve("public/data/market-data.json"),"utf8")) as MarketFile;
  const universe=JSON.parse(await readFile(resolve("data/universe-history.json"),"utf8")) as UniverseFile;
  const production:Scenario={group:"production",label:"production",value:0,config:cloneConfig()};
  production.config.strategyId=`${PRODUCTION_STRATEGY.strategyId}-audit-production`;
  const scenarios:Scenario[]=[
    production,
    scenario("zgap","zgap15",0.15,c=>{c.allocation.concentrationZGap=0.15;}),
    scenario("zgap","zgap35",0.35,c=>{c.allocation.concentrationZGap=0.35;}),
    scenario("weight","weight60",0.60,c=>{c.allocation.concentratedTop1Weight=0.60;c.allocation.maxTop1Weight=0.60;}),
    scenario("weight","weight80",0.80,c=>{c.allocation.concentratedTop1Weight=0.80;c.allocation.maxTop1Weight=0.80;}),
    scenario("fixed","fixed50",0.50,c=>{c.allocation.baseTop1Weight=0.50;c.allocation.concentratedTop1Weight=0.50;c.allocation.maxTop1Weight=0.50;}),
  ];
  const results=scenarios.map(s=>metrics(s,runBacktest({histories:market.histories,universeHistory:universe.history,config:s.config})));
  const prod=results.find(x=>x.group==="production")!;
  const neighborhoods={
    zGap:[results.find(x=>x.label==="zgap15")!,{...prod,group:"zgap" as const,label:"production-zgap25",value:0.25},results.find(x=>x.label==="zgap35")!],
    concentratedWeight:[results.find(x=>x.label==="weight60")!,{...prod,group:"weight" as const,label:"production-weight70",value:0.70},results.find(x=>x.label==="weight80")!],
    fixed50:results.find(x=>x.label==="fixed50")!,
  };
  const diagnostics=signalDiagnostics(market.histories,universe.history);
  const out={generatedAt:new Date().toISOString(),strategyId:PRODUCTION_STRATEGY.strategyId,design:{type:"pre-specified one-factor-at-a-time coarse allocation audit",zGap:[0.15,0.25,0.35],concentratedTop1Weight:[0.60,0.70,0.80],fixed50Reference:true,rule:"diagnostic only; do not select a new Production value from best historical CAGR"},production:prod,neighborhoods,signalDiagnostics:diagnostics};
  await mkdir(resolve("data/research/allocation-parameter-neighborhood"),{recursive:true});
  await writeFile(resolve("data/research/allocation-parameter-neighborhood/audit.json"),JSON.stringify(out,null,2));
  console.log("ALLOCATION_NEIGHBORHOOD_JSON="+JSON.stringify({...out,signalDiagnostics:{...diagnostics,rows:undefined}}));
}
main().catch(e=>{console.error(e);process.exit(1)});
