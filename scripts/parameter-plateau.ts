import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { runBacktest } from "../src/lib/backtest";
import type { PricePoint, StrategyConfig, UniverseMonth } from "../src/lib/types";

type Market={histories:Record<string,PricePoint[]>}; type UF={history:UniverseMonth[]};
const stops=[0.15,0.175,0.20], circuits=[0.125,0.15,0.175], recoveries=[5,10,15];
const median=(xs:number[])=>{const a=[...xs].sort((x,y)=>x-y),m=Math.floor(a.length/2);return a.length%2?a[m]:(a[m-1]+a[m])/2};
async function main(){
 const market=JSON.parse(await readFile(resolve("public/data/market-data.json"),"utf8")) as Market;
 const uf=JSON.parse(await readFile(resolve("data/universe-history.json"),"utf8")) as UF;
 const rows:any[]=[];
 for(const stop of stops) for(const circuit of circuits) for(const recovery of recoveries){
   const cfg={...PRODUCTION_STRATEGY,risk:{...PRODUCTION_STRATEGY.risk,individualStop:stop,portfolioCircuit:circuit},recovery:{...PRODUCTION_STRATEGY.recovery,confirmationDays:recovery}} as StrategyConfig;
   const bt=runBacktest({histories:market.histories,universeHistory:uf.history,config:cfg});
   rows.push({stop,circuit,recovery,cagr:bt.stats.cagr,maxDrawdown:bt.stats.maxDrawdown,calmar:bt.stats.calmar,finalEquity:bt.stats.finalEquity});
   console.log(`done stop=${stop} circuit=${circuit} recovery=${recovery} cagr=${bt.stats.cagr}`);
 }
 const prod=rows.find(r=>r.stop===0.175&&r.circuit===0.15&&r.recovery===10);
 const neighborhood=rows.filter(r=>!(r===prod));
 const summary={production:prod,neighborhoodMedian:{cagr:median(neighborhood.map(r=>r.cagr)),maxDrawdown:median(neighborhood.map(r=>r.maxDrawdown)),calmar:median(neighborhood.map(r=>r.calmar??0))},fragility:{cagr:prod.cagr-median(neighborhood.map(r=>r.cagr)),maxDrawdown:prod.maxDrawdown-median(neighborhood.map(r=>r.maxDrawdown)),calmar:(prod.calmar??0)-median(neighborhood.map(r=>r.calmar??0))},productionRanks:{cagr:1+rows.filter(r=>r.cagr>prod.cagr).length,maxDrawdown:1+rows.filter(r=>r.maxDrawdown>prod.maxDrawdown).length,calmar:1+rows.filter(r=>(r.calmar??-Infinity)>(prod.calmar??-Infinity)).length,total:rows.length}};
 const result={generatedAt:new Date().toISOString(),strategyId:PRODUCTION_STRATEGY.strategyId,grid:{stops,circuits,recoveries},purpose:"local robustness diagnostic; not parameter optimization",summary,rows};
 await mkdir(resolve("data/research/parameter-plateau"),{recursive:true});
 await writeFile(resolve("data/research/parameter-plateau/result.json"),JSON.stringify(result,null,2)+"\n");
 const pct=(x:number)=>`${(x*100).toFixed(2)}%`;
 let md=`# Parameter plateau\n\nPurpose: local robustness diagnostic only; **not optimization**.\n\nProduction: Stop **17.5%**, Circuit **15%**, Recovery **10**.\n\nProduction CAGR: **${pct(prod.cagr)}** / MaxDD: **${pct(prod.maxDrawdown)}** / Calmar: **${prod.calmar?.toFixed(2)}**\nNeighborhood median CAGR: **${pct(summary.neighborhoodMedian.cagr)}** / MaxDD: **${pct(summary.neighborhoodMedian.maxDrawdown)}** / Calmar: **${summary.neighborhoodMedian.calmar.toFixed(2)}**\nCAGR fragility vs neighborhood median: **${pct(summary.fragility.cagr)}**\n\n| Stop | Circuit | Recovery | CAGR | MaxDD | Calmar | Final equity |\n|---:|---:|---:|---:|---:|---:|---:|\n`;
 for(const r of [...rows].sort((a,b)=>b.cagr-a.cagr)) md+=`| ${pct(r.stop)} | ${pct(r.circuit)} | ${r.recovery} | ${pct(r.cagr)} | ${pct(r.maxDrawdown)} | ${r.calmar?.toFixed(2)??"n/a"} | ${r.finalEquity.toFixed(2)}x |\n`;
 md+=`\nProduction rank within 27 local combinations: CAGR **${summary.productionRanks.cagr}/27**, MaxDD **${summary.productionRanks.maxDrawdown}/27**, Calmar **${summary.productionRanks.calmar}/27**. A robust setting should sit on a broad plateau rather than be an isolated spike.\n`;
 await writeFile(resolve("data/research/parameter-plateau/result.md"),md); console.log(md); console.log("RESULT_JSON="+JSON.stringify(result));
}
main().catch(e=>{console.error(e);process.exit(1)});
