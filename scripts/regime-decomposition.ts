import fs from "node:fs/promises";
import path from "node:path";
import { runBacktest } from "../src/lib/backtest";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { monthlyCloses } from "../src/lib/strategy/momentum";
import type { PricePoint, UniverseMonth } from "../src/lib/types";

type Row = { date:string; strategyLogReturn:number; year:string; trend:"ABOVE_200DMA"|"BELOW_200DMA"|"NA"; vol:"HIGH_VOL"|"LOW_VOL"|"NA"; mom20:"POS_20D"|"NEG_20D"|"NA"; breadth:"HIGH_BREADTH"|"LOW_BREADTH"|"NA"; composite:"TREND_UP_LOW_VOL"|"TREND_UP_HIGH_VOL"|"TREND_DOWN_LOW_VOL"|"TREND_DOWN_HIGH_VOL"|"NA" };
const mean=(x:number[])=>x.length?x.reduce((a,b)=>a+b,0)/x.length:0;
const stdev=(x:number[])=>{if(x.length<2)return 0;const m=mean(x);return Math.sqrt(x.reduce((s,v)=>s+(v-m)**2,0)/(x.length-1));};
function summarize(rows:Row[], key:keyof Pick<Row,"trend"|"vol"|"mom20"|"breadth"|"composite">){
  const totalLog=rows.reduce((s,r)=>s+r.strategyLogReturn,0);
  const labels=[...new Set(rows.map(r=>String(r[key])))].sort();
  return labels.map(label=>{const xs=rows.filter(r=>r[key]===label).map(r=>r.strategyLogReturn);const ann=Math.exp(mean(xs)*252)-1;return{label,days:xs.length,dayShare:xs.length/rows.length,conditionalAnnualizedGrowth:ann,meanDailyLogReturn:mean(xs),dailyVol:stdev(xs),positiveDayShare:xs.filter(v=>v>0).length/xs.length,logGrowthContribution:xs.reduce((a,b)=>a+b,0),logGrowthContributionShare:totalLog!==0?xs.reduce((a,b)=>a+b,0)/totalLog:null};});
}
function yearly(rows:Row[], key:keyof Pick<Row,"trend"|"vol"|"mom20"|"breadth"|"composite">){
  const years=[...new Set(rows.map(r=>r.year))].sort(); const out:any[]=[];
  for(const y of years){const yr=rows.filter(r=>r.year===y);for(const s of summarize(yr,key))out.push({year:y,...s});}
  return out;
}
function lastN<T>(x:T[],i:number,n:number){return x.slice(Math.max(0,i-n+1),i+1)}
function sixMonthReturn(points:PricePoint[], date:string){const m=monthlyCloses(points).filter(p=>p.date<=date);if(m.length<7)return null;return m.at(-1)!.close/m.at(-7)!.close-1;}
async function main(){
 const market=JSON.parse(await fs.readFile(path.join(process.cwd(),"public/data/market-data.json"),"utf8")) as {histories:Record<string,PricePoint[]>};
 const uf=JSON.parse(await fs.readFile(path.join(process.cwd(),"data/universe-history.json"),"utf8")) as {history:UniverseMonth[]};
 const histories=market.histories; const universe=[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf));
 const bt=runBacktest({histories,universeHistory:universe,config:PRODUCTION_STRATEGY});
 const curve=bt.equityCurve; const qqq=[...(histories.QQQ??[])].sort((a,b)=>a.date.localeCompare(b.date)); const qi=new Map(qqq.map((p,i)=>[p.date,i]));
 const breadthByDate=new Map<string,number>();
 for(const u of universe){const vals=u.symbols.slice(0,PRODUCTION_STRATEGY.universe.size).map(({symbol})=>sixMonthReturn(histories[symbol]??[],u.asOf)).filter((v):v is number=>v!==null);breadthByDate.set(u.asOf,vals.length?vals.filter(v=>v>0).length/vals.length:NaN);}
 const breadthDates=[...breadthByDate.keys()].sort();
 function latestBreadth(date:string){let best:string|null=null;for(const d of breadthDates){if(d<=date)best=d;else break;}return best?breadthByDate.get(best)??NaN:NaN;}
 const rows:Row[]=[];
 for(let i=1;i<curve.length;i++){
   const today=curve[i], prev=curve[i-1]; const qidx=qi.get(prev.date); if(qidx===undefined)continue; const q=qqq[qidx];
   const sma200=qidx>=199?mean(lastN(qqq,qidx,200).map(p=>p.close)):NaN;
   const qret20=qidx>=20?q.close/qqq[qidx-20].close-1:NaN;
   const dailyRets=qidx>=20?qqq.slice(qidx-19,qidx+1).map((p,j,a)=>j===0?null:Math.log(p.close/a[j-1].close)).filter((v):v is number=>v!==null):[];
   const rv20=dailyRets.length>=19?stdev(dailyRets)*Math.sqrt(252):NaN;
   const b=latestBreadth(prev.date);
   const trend=Number.isFinite(sma200)?(q.close>sma200?"ABOVE_200DMA":"BELOW_200DMA"):"NA";
   const vol=Number.isFinite(rv20)?(rv20>=0.30?"HIGH_VOL":"LOW_VOL"):"NA";
   const mom20=Number.isFinite(qret20)?(qret20>0?"POS_20D":"NEG_20D"):"NA";
   const breadth=Number.isFinite(b)?(b>=0.50?"HIGH_BREADTH":"LOW_BREADTH"):"NA";
   const composite=trend==="ABOVE_200DMA"?(vol==="HIGH_VOL"?"TREND_UP_HIGH_VOL":vol==="LOW_VOL"?"TREND_UP_LOW_VOL":"NA"):trend==="BELOW_200DMA"?(vol==="HIGH_VOL"?"TREND_DOWN_HIGH_VOL":vol==="LOW_VOL"?"TREND_DOWN_LOW_VOL":"NA"):"NA";
   rows.push({date:today.date,strategyLogReturn:Math.log(today.equity/prev.equity),year:today.date.slice(0,4),trend,vol,mom20,breadth,composite});
 }
 const valid=rows.filter(r=>r.trend!=="NA"&&r.vol!=="NA"&&r.mom20!=="NA"&&r.breadth!=="NA");
 const output={generatedAt:new Date().toISOString(),strategyId:PRODUCTION_STRATEGY.strategyId,method:"Lagged regime decomposition: prior-close regime labels condition next strategy close-to-close log return. Fixed thresholds: QQQ 200DMA; 20D realized vol 30% annualized; QQQ 20D momentum 0%; dynamic-universe 6M positive-return breadth 50%.",validity:{descriptiveHistoricalTest:true,trueOOS:false,regimesLaggedOneTradingDay:true,thresholdsFixedNotSampleMedian:true,architectureHindsightRemains:true,warning:"This tests historical regime dependence of the already-selected Production architecture. It is not evidence that the architecture itself was discoverable ex ante, and conditional annualized growth is not a forecast."},sample:{start:valid[0]?.date,end:valid.at(-1)?.date,days:valid.length,totalLogGrowth:valid.reduce((s,r)=>s+r.strategyLogReturn,0)},axes:{trend:summarize(valid,"trend"),vol:summarize(valid,"vol"),mom20:summarize(valid,"mom20"),breadth:summarize(valid,"breadth"),composite:summarize(valid,"composite")},yearly:{trend:yearly(valid,"trend"),vol:yearly(valid,"vol"),mom20:yearly(valid,"mom20"),breadth:yearly(valid,"breadth"),composite:yearly(valid,"composite")}};
 const dir=path.join(process.cwd(),"data/research/regime-decomposition");await fs.mkdir(dir,{recursive:true});await fs.writeFile(path.join(dir,"result.json"),JSON.stringify(output,null,2));console.log(JSON.stringify(output.axes,null,2));
}
main().catch(e=>{console.error(e);process.exit(1)});
