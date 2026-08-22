import { TICKERS } from "../src/lib/config";
import { FROZEN_STRATEGY, FROZEN_STRATEGY_ID } from "../src/lib/frozen-strategy";
import { buildDashboard } from "../src/lib/momentum";
import { fetchHistories } from "../src/lib/yahoo";
import type { TickerConfig } from "../src/lib/types";

const candidates: TickerConfig[] = [
  { symbol: "CIEN", genre: "Optical Networking" },
  { symbol: "AXTI", genre: "Optical Networking" },
];

const calmar = (cagr:number, dd:number) => dd < 0 ? cagr / Math.abs(dd) : 0;
const same = (a:string[], b:string[]) => [...a].sort().join("|") === [...b].sort().join("|");

async function main() {
  const symbols = [...new Set([...TICKERS.map(t=>t.symbol), ...candidates.map(t=>t.symbol)])];
  const histories = await fetchHistories(symbols);
  const baseline = buildDashboard(histories, TICKERS, FROZEN_STRATEGY);
  const baseRows = new Map(baseline.backtest.rows.map(r=>[r.signalMonth,r]));
  const b = baseline.backtest.stats;
  const output:any = { strategyId:FROZEN_STRATEGY_ID, baseline:{cagr:b.cagr,maxDrawdown:b.maxDrawdown,annualizedVolatility:b.annualizedVolatility,calmar:calmar(b.cagr,b.maxDrawdown)}, candidates:[] };
  for (const candidate of candidates) {
    const scenario = buildDashboard(histories, [...TICKERS,candidate], FROZEN_STRATEGY);
    const s = scenario.backtest.stats;
    const selected = scenario.backtest.rows.filter(r=>r.picks.includes(candidate.symbol));
    const changed = scenario.backtest.rows.filter(r=>{const br=baseRows.get(r.signalMonth); return br ? !same(br.picks,r.picks) : false;});
    const details = selected.map(r=>{
      const br=baseRows.get(r.signalMonth);
      const displaced=br ? br.picks.filter(x=>!r.picks.includes(x)) : [];
      const h=histories[candidate.symbol] ?? [];
      const ep=h.find(x=>x.date===r.entryDate)?.adjClose;
      const xp=r.exitDate ? h.find(x=>x.date===r.exitDate)?.adjClose : undefined;
      const candidateReturn=ep && xp ? xp/ep-1 : null;
      return {signalMonth:r.signalMonth,entryDate:r.entryDate,exitDate:r.exitDate,candidateReturn,displaced};
    });
    const completed=details.map((d:any)=>d.candidateReturn).filter((x:any)=>typeof x==='number');
    output.candidates.push({symbol:candidate.symbol,genre:candidate.genre,selectedMonths:selected.length,changedMonths:changed.length,cagr:s.cagr,deltaCagr:s.cagr-b.cagr,maxDrawdown:s.maxDrawdown,deltaMaxDrawdown:s.maxDrawdown-b.maxDrawdown,annualizedVolatility:s.annualizedVolatility,deltaAnnualizedVolatility:s.annualizedVolatility-b.annualizedVolatility,calmar:calmar(s.cagr,s.maxDrawdown),deltaCalmar:calmar(s.cagr,s.maxDrawdown)-calmar(b.cagr,b.maxDrawdown),averageSelectedHoldingReturn:completed.length?completed.reduce((a:number,c:number)=>a+c,0)/completed.length:null,selectedWinRate:completed.length?completed.filter((x:number)=>x>0).length/completed.length:null,worstSelectedHoldingReturn:completed.length?Math.min(...completed):null,bestSelectedHoldingReturn:completed.length?Math.max(...completed):null,selectedDetail:details});
  }
  console.log("LYTE_SANITY_JSON_START"); console.log(JSON.stringify(output,null,2)); console.log("LYTE_SANITY_JSON_END");
}
main().catch(e=>{console.error(e);process.exitCode=1});
