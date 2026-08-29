import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import { initialEngineState, transitionDay } from "../src/lib/strategy/state-machine";
import type { PricePoint, UniverseMonth } from "../src/lib/types";

type Market = { histories: Record<string, PricePoint[]> };
type UF = { history: UniverseMonth[] };
type DailyRow = { date: string; equity: number };
type Stats = { start: string; end: string; tradingDays: number; totalReturn: number; cagr: number | null; maxDD: number };

function reconstruct(histories: Record<string, PricePoint[]>, universeHistory: UniverseMonth[]): DailyRow[] {
  const qqq = [...(histories.QQQ ?? [])].sort((a,b)=>a.date.localeCompare(b.date));
  const dates = qqq.map(p=>p.date);
  const di = new Map(dates.map((d,i)=>[d,i]));
  const pm = Object.fromEntries(Object.entries(histories).map(([s,ps])=>[s,new Map(ps.map(p=>[p.date,p]))]));
  const ub = new Map(universeHistory.map(u=>[u.asOf,u]));
  let st = initialEngineState(PRODUCTION_STRATEGY);
  const rows: DailyRow[] = [];
  for (let i=0;i<dates.length;i++) {
    const date = dates[i];
    if (date < PRODUCTION_STRATEGY.backtestStart) continue;
    const next = dates[i+1] ?? null;
    const u = ub.get(date) ?? null;
    const signal = u ? buildMonthlySignal({ universe:u, histories, qqq, nextSessionDate:next, config:PRODUCTION_STRATEGY }) : null;
    const syms = new Set(["QQQ", ...st.currentPositions.map(p=>p.symbol), ...(st.pendingSignal?.selectedSymbols??[]), ...st.nextAction.symbols, ...(signal?.selectedSymbols??[])]);
    const prices = Object.fromEntries([...syms].map(s=>[s,pm[s]?.get(date)]));
    st = transitionDay(st, { date, prices, qqqHistoryThroughClose: qqq.slice(0,(di.get(date)??i)+1), monthlySignal:signal, nextSessionDate:next }, PRODUCTION_STRATEGY);
    rows.push({ date, equity: st.currentEquity });
  }
  return rows;
}

function stats(rows: DailyRow[]): Stats {
  if (rows.length < 2) throw new Error("Need at least two rows");
  const startEq = rows[0].equity;
  const endEq = rows.at(-1)!.equity;
  const totalReturn = endEq / startEq - 1;
  const years = (new Date(rows.at(-1)!.date + "T00:00:00Z").getTime() - new Date(rows[0].date + "T00:00:00Z").getTime()) / (365.25*24*3600*1000);
  const cagr = years > 0 ? Math.pow(endEq/startEq,1/years)-1 : null;
  let peak = startEq, maxDD = 0;
  for (const r of rows) { peak = Math.max(peak,r.equity); maxDD = Math.min(maxDD,r.equity/peak-1); }
  return { start: rows[0].date, end: rows.at(-1)!.date, tradingDays: rows.length, totalReturn, cagr, maxDD };
}

async function main() {
  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"),"utf8")) as Market;
  const uf = JSON.parse(await readFile(resolve("data/universe-history.json"),"utf8")) as UF;
  const rows = reconstruct(market.histories,[...uf.history].sort((a,b)=>a.asOf.localeCompare(b.asOf)));
  const lastDate = rows.at(-1)!.date;
  const splits = [2020,2021,2022,2023,2024,2025].map(trainEndYear=>{
    const trainRows = rows.filter(r=>r.date <= `${trainEndYear}-12-31`);
    const testStart = `${trainEndYear+1}-01-01`;
    const testEnd = trainEndYear+1 < 2026 ? `${trainEndYear+1}-12-31` : lastDate;
    const testRowsAll = rows.filter(r=>r.date >= testStart && r.date <= testEnd);
    if (trainRows.length < 2 || testRowsAll.length < 2) return null;
    const prev = [...rows].reverse().find(r=>r.date < testStart);
    const testRows = prev ? [prev,...testRowsAll] : testRowsAll;
    return {
      trainThrough: trainRows.at(-1)!.date,
      train: stats(trainRows),
      pseudoOOS: stats(testRows),
      note: "Current Production rules are held fixed; no refit/selection is performed at each split. This is a temporal pseudo-OOS decomposition, not a historically frozen strategy reconstruction."
    };
  }).filter(Boolean);
  const out = {
    generatedAt: new Date().toISOString(),
    strategyId: PRODUCTION_STRATEGY.id,
    method: "anchored yearly pseudo-OOS using current Production strategy; expanding train window and next-calendar-year test window",
    sample: { start: rows[0].date, end: lastDate, tradingDays: rows.length },
    full: stats(rows),
    splits
  };
  await mkdir(resolve("data/research/anchored-walkforward"),{recursive:true});
  await writeFile(resolve("data/research/anchored-walkforward/result.json"),JSON.stringify(out,null,2));
  console.log(JSON.stringify(out));
}

main().catch(e=>{console.error(e);process.exit(1)});
