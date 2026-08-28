import { readFile, mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import { initialEngineState, transitionDay } from "../src/lib/strategy/state-machine";
import type { EquityPoint, PricePoint, StrategyConfig, UniverseMonth } from "../src/lib/types";

type Market = { histories: Record<string, PricePoint[]> };
type UF = { history: UniverseMonth[] };

function stats(curve: EquityPoint[]) {
  const first = curve[0], last = curve.at(-1)!;
  const years = (Date.parse(last.date) - Date.parse(first.date)) / (365.25 * 86_400_000);
  const cagr = (last.equity / first.equity) ** (1 / years) - 1;
  let peak = -Infinity, maxDD = 0;
  for (const p of curve) { peak = Math.max(peak, p.equity); maxDD = Math.min(maxDD, p.equity / peak - 1); }
  return { cagr, maxDrawdown: maxDD, calmar: cagr / Math.abs(maxDD), finalEquity: last.equity };
}

function run(histories: Record<string, PricePoint[]>, universeHistory: UniverseMonth[], cfg: StrategyConfig, monthlyLag: number, riskLag: number) {
  const qqq = [...(histories.QQQ ?? [])].sort((a,b)=>a.date.localeCompare(b.date));
  const tradingDates = qqq.map(p=>p.date);
  const dateIndex = new Map(tradingDates.map((d,i)=>[d,i]));
  const priceMaps = Object.fromEntries(Object.entries(histories).map(([s,pts])=>[s,new Map(pts.map(p=>[p.date,p]))]));
  const universeBySignalDate = new Map(universeHistory.map(m=>[m.asOf,m]));
  let state = initialEngineState(cfg);
  const curve: EquityPoint[] = [];
  for (let i=0;i<tradingDates.length;i++) {
    const date = tradingDates[i]; if (date < cfg.backtestStart) continue;
    const universe = universeBySignalDate.get(date);
    const lag = universe ? monthlyLag : riskLag;
    const executionDate = tradingDates[i + lag] ?? null;
    const signal = universe ? buildMonthlySignal({ universe, histories, qqq, nextSessionDate: executionDate, config: cfg }) : null;
    const symbols = new Set(["QQQ", ...state.currentPositions.map(p=>p.symbol), ...(state.pendingSignal?.selectedSymbols ?? []), ...state.nextAction.symbols, ...(signal?.selectedSymbols ?? [])]);
    const prices = Object.fromEntries([...symbols].map(s=>[s,priceMaps[s]?.get(date)]));
    state = transitionDay(state,{date,prices,qqqHistoryThroughClose:qqq.slice(0,(dateIndex.get(date) ?? i)+1),monthlySignal:signal,nextSessionDate:executionDate},cfg);
    curve.push({date,equity:state.currentEquity,drawdown:state.drawdown});
  }
  return stats(curve);
}

async function main(){
  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"),"utf8")) as Market;
  const uf = JSON.parse(await readFile(resolve("data/universe-history.json"),"utf8")) as UF;
  const cfg = {...PRODUCTION_STRATEGY, execution:{...PRODUCTION_STRATEGY.execution, transactionCost:0.001}} as StrategyConfig;
  const scenarios = [
    {label:"baseline",monthlyLag:1,riskLag:1},
    {label:"monthly+1",monthlyLag:2,riskLag:1},
    {label:"monthly+2",monthlyLag:3,riskLag:1},
    {label:"risk+1",monthlyLag:1,riskLag:2},
    {label:"risk+2",monthlyLag:1,riskLag:3},
    {label:"all+1",monthlyLag:2,riskLag:2},
    {label:"all+2",monthlyLag:3,riskLag:3},
  ];
  const rows:any[]=[];
  for(const sc of scenarios){const s=run(market.histories,uf.history,cfg,sc.monthlyLag,sc.riskLag);rows.push({...sc,...s});console.log(`done ${sc.label} cagr=${s.cagr} dd=${s.maxDrawdown}`)}
  const base=rows[0]; for(const r of rows) r.deltaCagr=r.cagr-base.cagr;
  const result={generatedAt:new Date().toISOString(),purpose:"separate monthly-signal execution lag from risk-exit lag; 0.10% transaction cost per side",base,rows};
  await mkdir(resolve("data/research/execution-robustness-separated"),{recursive:true});
  await writeFile(resolve("data/research/execution-robustness-separated/result.json"),JSON.stringify(result,null,2)+"\n");
  const pct=(x:number)=>`${(x*100).toFixed(2)}%`; let md="# Execution delay decomposition\n\n| Scenario | Monthly lag | Risk lag | CAGR | Δ CAGR | Global MaxDD | Calmar | Final equity |\n|---|---:|---:|---:|---:|---:|---:|---:|\n";
  for(const r of rows)md+=`| ${r.label} | ${r.monthlyLag} | ${r.riskLag} | ${pct(r.cagr)} | ${pct(r.deltaCagr)} | ${pct(r.maxDrawdown)} | ${r.calmar.toFixed(2)} | ${r.finalEquity.toFixed(2)}x |\n`;
  await writeFile(resolve("data/research/execution-robustness-separated/result.md"),md);console.log(md);console.log("RESULT_JSON="+JSON.stringify(result));
}
main().catch(e=>{console.error(e);process.exit(1)});
