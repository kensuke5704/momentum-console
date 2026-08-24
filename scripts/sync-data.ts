import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { buildDashboardPayload } from "../src/lib/dashboard";
import { updateForwardOos } from "../src/lib/oos";
import type { BacktestResult, ForwardOosResult, PricePoint, UniverseMonth } from "../src/lib/types";
import { fetchHistories } from "../src/lib/yahoo";

type UniverseFile = { history: UniverseMonth[] };
type MarketDataFile = { histories?: Record<string, PricePoint[]> };
type FrozenBacktestFile = { strategyId: string; frozenAt: string; dataThrough: string | null; backtest: BacktestResult };

async function existingHistories(path: string): Promise<Record<string, PricePoint[]>> {
  try { return (JSON.parse(await readFile(path, "utf8")) as MarketDataFile).histories ?? {}; } catch { return {}; }
}
async function frozenBacktest(expectedStrategyId: string): Promise<BacktestResult> {
  const frozen = JSON.parse(await readFile(resolve("public/data/backtest-frozen.json"), "utf8")) as FrozenBacktestFile;
  if (!frozen.backtest?.strategyId) throw new Error("Frozen backtest is missing; run npm run freeze:backtest once intentionally");
  if (frozen.strategyId !== expectedStrategyId || frozen.backtest.strategyId !== expectedStrategyId) throw new Error("Frozen backtest belongs to a different strategy; create a new intentional freeze before syncing");
  return frozen.backtest;
}
async function existingOos(): Promise<ForwardOosResult | null> {
  try { return JSON.parse(await readFile(resolve("public/data/oos-performance.json"), "utf8")) as ForwardOosResult; } catch { return null; }
}
function merge(existing: Record<string, PricePoint[]>, fetched: Record<string, PricePoint[]>, symbols: string[]) {
  return Object.fromEntries(symbols.map((symbol) => {
    const byDate = new Map<string, PricePoint>();
    for (const point of existing[symbol] ?? []) byDate.set(point.date, point);
    for (const point of fetched[symbol] ?? []) byDate.set(point.date, point);
    return [symbol, [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date))];
  }));
}
async function main() {
  const universeFile = JSON.parse(await readFile(resolve("data/universe-history.json"), "utf8")) as UniverseFile;
  const universeHistory = universeFile.history;
  if (!universeHistory.length) throw new Error("Dynamic Universe history is empty; run npm run sync:universe first");
  const symbols = [...new Set(["QQQ", "TQQQ", ...universeHistory.flatMap((month) => month.symbols.map((member) => member.symbol))])];
  console.log(`Fetching adjusted OHLC for ${symbols.length} dynamic-universe symbols`);
  const outputPath = resolve("public/data/market-data.json");
  const histories = merge(await existingHistories(outputPath), await fetchHistories(symbols, 8), symbols);
  const liveDashboard = buildDashboardPayload(histories, universeHistory);
  const oos = updateForwardOos(liveDashboard.backtest, await existingOos());
  const dashboard = { ...liveDashboard, backtest: await frozenBacktest(liveDashboard.config.strategyId), oos };
  await mkdir(dirname(outputPath), { recursive: true });
  await writeFile(outputPath, `${JSON.stringify({ generatedAt: dashboard.generatedAt, histories, dashboard })}\n`);
  await writeFile(resolve("public/data/dashboard.json"), `${JSON.stringify({ dashboard })}\n`);
  await writeFile(resolve("public/data/live-state.json"), `${JSON.stringify(dashboard.liveState)}\n`);
  await writeFile(resolve("public/data/oos-performance.json"), `${JSON.stringify(oos)}\n`);
  console.log(`Saved ${outputPath}; signal ${dashboard.currentSignal?.signalDate ?? "none"}; state ${dashboard.liveState.state}`);
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
