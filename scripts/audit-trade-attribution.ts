import { readFile, mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import { initialEngineState, transitionDay, type EngineState } from "../src/lib/strategy/state-machine";
import { nextUsTradingSession } from "../src/lib/trading-calendar";
import type { PricePoint, UniverseMonth } from "../src/lib/types";

type MarketDataFile = { histories?: Record<string, PricePoint[]> };
type UniverseFile = { history: UniverseMonth[] };
type OpenLot = { symbol: string; entryDate: string; entryPrice: number; shares: number; grossAllocation: number; targetWeight: number };
type Trade = OpenLot & { exitDate: string; exitPrice: number; holdingTradingDays: number; netProceeds: number; pnl: number; returnOnAllocation: number; exitReason: string };

const START = "2020-01-01";
const END = "2026-08-25";
const COST = PRODUCTION_STRATEGY.execution.transactionCost;

async function main() {
  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as MarketDataFile;
  const universe = JSON.parse(await readFile(resolve("data/universe-history.json"), "utf8")) as UniverseFile;
  const histories = Object.fromEntries(Object.entries(market.histories ?? {}).map(([s, pts]) => [s, pts.filter((p) => p.date <= END)]));
  const qqq = [...(histories.QQQ ?? [])].sort((a, b) => a.date.localeCompare(b.date));
  const dates = qqq.map((p) => p.date);
  const dateIndex = new Map(dates.map((d, i) => [d, i]));
  const priceMaps = Object.fromEntries(Object.entries(histories).map(([s, pts]) => [s, new Map(pts.map((p) => [p.date, p]))]));
  const universeByDate = new Map(universe.history.filter((u) => u.asOf >= START && u.asOf <= END).map((u) => [u.asOf, u]));

  let state: EngineState = initialEngineState(PRODUCTION_STRATEGY);
  const openLots = new Map<string, OpenLot>();
  const trades: Trade[] = [];

  for (let i = 0; i < dates.length; i++) {
    const date = dates[i];
    if (date < START || date > END) continue;
    const nextSessionDate = dates[i + 1] ?? nextUsTradingSession(date);
    const u = universeByDate.get(date);
    const signal = u ? buildMonthlySignal({ universe: u, histories, qqq, nextSessionDate, config: PRODUCTION_STRATEGY }) : null;
    const symbols = new Set(["QQQ", ...state.currentPositions.map((p) => p.symbol), ...(state.pendingSignal?.selectedSymbols ?? []), ...state.nextAction.symbols, ...(signal?.selectedSymbols ?? [])]);
    const prices = Object.fromEntries([...symbols].map((s) => [s, priceMaps[s]?.get(date)]));

    const before = structuredClone(state);
    const beforeEventCount = before.events.length;
    state = transitionDay(state, { date, prices, qqqHistoryThroughClose: qqq.slice(0, (dateIndex.get(date) ?? i) + 1), monthlySignal: signal, nextSessionDate }, PRODUCTION_STRATEGY);
    const newEvents = state.events.slice(beforeEventCount);

    for (const event of newEvents) {
      if (event.type === "EXIT_OPEN") {
        for (const symbol of event.symbols) {
          const lot = openLots.get(symbol);
          if (!lot) continue;
          const exitPrice = prices[symbol]?.open ?? prices[symbol]?.close;
          if (!exitPrice) continue;
          const netProceeds = lot.shares * exitPrice * (1 - COST);
          const pnl = netProceeds - lot.grossAllocation;
          trades.push({ ...lot, exitDate: date, exitPrice, holdingTradingDays: (dateIndex.get(date) ?? 0) - (dateIndex.get(lot.entryDate) ?? 0), netProceeds, pnl, returnOnAllocation: netProceeds / lot.grossAllocation - 1, exitReason: event.reason });
          openLots.delete(symbol);
        }
      }
      if (event.type === "ENTRY_OPEN") {
        for (const position of state.currentPositions) {
          if (!event.symbols.includes(position.symbol)) continue;
          const grossAllocation = position.shares * position.entryPrice / (1 - COST);
          openLots.set(position.symbol, { symbol: position.symbol, entryDate: date, entryPrice: position.entryPrice, shares: position.shares, grossAllocation, targetWeight: position.targetWeight });
        }
      }
    }
  }

  const finalDate = dates.filter((d) => d <= END).at(-1)!;
  for (const [symbol, lot] of openLots) {
    const finalPrice = priceMaps[symbol]?.get(finalDate)?.close;
    if (!finalPrice) continue;
    const netProceeds = lot.shares * finalPrice;
    const pnl = netProceeds - lot.grossAllocation;
    trades.push({ ...lot, exitDate: finalDate, exitPrice: finalPrice, holdingTradingDays: (dateIndex.get(finalDate) ?? 0) - (dateIndex.get(lot.entryDate) ?? 0), netProceeds, pnl, returnOnAllocation: netProceeds / lot.grossAllocation - 1, exitReason: "MARK_TO_MARKET_END" });
  }

  const sorted = [...trades].sort((a, b) => b.pnl - a.pnl);
  const totalPositivePnl = trades.filter((t) => t.pnl > 0).reduce((s, t) => s + t.pnl, 0);
  const totalPnl = trades.reduce((s, t) => s + t.pnl, 0);
  const bySymbol = new Map<string, { pnl: number; trades: number; wins: number; grossAllocation: number }>();
  for (const t of trades) {
    const row = bySymbol.get(t.symbol) ?? { pnl: 0, trades: 0, wins: 0, grossAllocation: 0 };
    row.pnl += t.pnl; row.trades += 1; row.wins += t.pnl > 0 ? 1 : 0; row.grossAllocation += t.grossAllocation;
    bySymbol.set(t.symbol, row);
  }
  const symbolAttribution = [...bySymbol.entries()].map(([symbol, r]) => ({ symbol, ...r, winRate: r.trades ? r.wins / r.trades : 0, pnlShareOfNet: totalPnl ? r.pnl / totalPnl : 0 })).sort((a, b) => b.pnl - a.pnl);

  const output = {
    generatedAt: new Date().toISOString(), period: { start: START, end: END }, strategyId: PRODUCTION_STRATEGY.strategyId,
    method: "Daily Production state-machine replay. Each position lot uses actual next-session open entry/exit prices and Production transaction cost on entry and exit. Open positions at END are marked to final close without hypothetical exit cost.",
    summary: {
      tradeLots: trades.length,
      winners: trades.filter((t) => t.pnl > 0).length,
      losers: trades.filter((t) => t.pnl < 0).length,
      winRate: trades.length ? trades.filter((t) => t.pnl > 0).length / trades.length : 0,
      totalPnl,
      totalPositivePnl,
      top1PositivePnlShare: totalPositivePnl ? Math.max(0, sorted[0]?.pnl ?? 0) / totalPositivePnl : 0,
      top3PositivePnlShare: totalPositivePnl ? sorted.slice(0, 3).reduce((s, t) => s + Math.max(0, t.pnl), 0) / totalPositivePnl : 0,
      top5PositivePnlShare: totalPositivePnl ? sorted.slice(0, 5).reduce((s, t) => s + Math.max(0, t.pnl), 0) / totalPositivePnl : 0,
    },
    topTrades: sorted.slice(0, 15),
    worstTrades: [...trades].sort((a, b) => a.pnl - b.pnl).slice(0, 10),
    symbolAttribution,
    focusSymbols: Object.fromEntries(["MU", "NVDA", "HOOD"].map((s) => [s, trades.filter((t) => t.symbol === s).sort((a, b) => b.pnl - a.pnl)])),
    allTrades: trades,
  };
  const out = resolve("data/research/trade-attribution.json");
  await mkdir(dirname(out), { recursive: true });
  await writeFile(out, `${JSON.stringify(output, null, 2)}\n`);
  console.log(JSON.stringify(output, null, 2));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });