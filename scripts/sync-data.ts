import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { buildDashboardPayload } from "../src/lib/dashboard";
import type { PricePoint, UniverseMonth } from "../src/lib/types";
import { fetchHistories, fetchIntradayHistories, type IntradayPricePoint } from "../src/lib/yahoo";

type UniverseFile = { history: UniverseMonth[] };
type MarketDataFile = { histories?: Record<string, PricePoint[]>; intraday?: Record<string, IntradayPricePoint[]> };

async function existingHistories(path: string): Promise<Record<string, PricePoint[]>> {
  try { return (JSON.parse(await readFile(path, "utf8")) as MarketDataFile).histories ?? {}; } catch { return {}; }
}
async function existingMarketData(path: string): Promise<MarketDataFile> {
  try { return JSON.parse(await readFile(path, "utf8")) as MarketDataFile; } catch { return {}; }
}
function mergeIntraday(existing: Record<string, IntradayPricePoint[]>, fetched: Record<string, IntradayPricePoint[]>, symbols: string[]) {
  return Object.fromEntries(symbols.map((symbol) => {
    const fresh = fetched[symbol] ?? [];
    if (!fresh.length) return [symbol, existing[symbol] ?? []];
    const byTimestamp = new Map<string, IntradayPricePoint>();
    for (const point of existing[symbol] ?? []) byTimestamp.set(point.timestamp, point);
    for (const point of fresh) byTimestamp.set(point.timestamp, point);
    return [symbol, [...byTimestamp.values()].sort((a, b) => a.timestamp.localeCompare(b.timestamp)).slice(-80)];
  }));
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
  const existing = await existingMarketData(outputPath);
  const [fetchedHistories, fetchedIntraday] = await Promise.all([fetchHistories(symbols, 8), fetchIntradayHistories(symbols, 8)]);
  const histories = merge(existing.histories ?? await existingHistories(outputPath), fetchedHistories, symbols);
  const intraday = mergeIntraday(existing.intraday ?? {}, fetchedIntraday, symbols);
  const dashboard = buildDashboardPayload(histories, universeHistory);
  await mkdir(dirname(outputPath), { recursive: true });
  await writeFile(outputPath, `${JSON.stringify({ generatedAt: dashboard.generatedAt, histories, intraday, dashboard })}\n`);
  await writeFile(resolve("public/data/dashboard.json"), `${JSON.stringify({ dashboard })}\n`);
  await writeFile(resolve("public/data/live-state.json"), `${JSON.stringify(dashboard.liveState)}\n`);
  console.log(`Saved ${outputPath}; signal ${dashboard.currentSignal?.signalDate ?? "none"}; state ${dashboard.liveState.state}`);
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
