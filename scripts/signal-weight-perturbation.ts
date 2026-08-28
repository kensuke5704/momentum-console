import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { runBacktest } from "../src/lib/backtest";
import type { PricePoint, StrategyConfig, UniverseMonth } from "../src/lib/types";

type Market={histories:Record<string,PricePoint[]>}; type UF={history:UniverseMonth[]};
const weights=[{label:"15_85",threeMonth:.15,sixMonth:.85},{label:"20_80",threeMonth:.20,sixMonth:.80},{label:"25_75",threeMonth:.25,sixMonth:.75}];
async function main(){
 const market=JSON.parse(await readFile(resolve("public/data/market-data.json"),"utf8")) as Market;
 const uf=JSON.parse(await readFile(resolve("data/universe-history.json"),"utf8")) as UF;
 const rows=[] as any[];
 for(const w of weights){
  const cfg={...PRODUCTION_STRATEGY,momentum:{...PRODUCTION_STRATEGY.momentum,threeMonth:w.threeMonth,sixMonth:w.sixMonth}} as StrategyConfig;
  const bt=runBacktest({histories:market.histories,universeHistory:uf.history,config:cfg});
  rows.push({...w,cagr:bt.stats.cagr,maxDrawdown:bt.stats.maxDrawdown,calmar:bt.stats.calmar,finalEquity:bt.stats.finalEquity});
 }
 const base=rows.find(x=>x.label==="20_80");
 const result={generatedAt:new Date().toISOString(),purpose:"small signal-weight perturbation; not optimization",base,rows:rows.map(x=>({...x,deltaCagr:x.cagr-base.cagr,deltaMaxDrawdown:x.maxDrawdown-base.maxDrawdown}))};
 await mkdir(resolve("data/research/signal-perturbation"),{recursive:true});
 await writeFile(resolve("data/research/signal-perturbation/weight-result.json"),JSON.stringify(result,null,2)+"\n");
 const pct=(x:number)=>`${(x*100).toFixed(2)}%`; let md="# Signal weight perturbation\n\n";
 md+="Small perturbation of the Production 3M/6M weights only. No optimization.\n\n| 3M / 6M | CAGR | Δ CAGR | MaxDD | Calmar | Final equity |\n|---|---:|---:|---:|---:|---:|\n";
 for(const x of result.rows) md+=`| ${(x.threeMonth*100).toFixed(0)} / ${(x.sixMonth*100).toFixed(0)} | ${pct(x.cagr)} | ${pct(x.deltaCagr)} | ${pct(x.maxDrawdown)} | ${x.calmar?.toFixed(2)??"n/a"} | ${x.finalEquity.toFixed(2)}x |\n`;
 await writeFile(resolve("data/research/signal-perturbation/weight-result.md"),md); console.log(md); console.log("RESULT_JSON="+JSON.stringify(result));
}
main().catch(e=>{console.error(e);process.exit(1)});
