import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { buildDashboardPayload } from "../src/lib/dashboard";
import type { PricePoint, UniverseMonth } from "../src/lib/types";
import { fetchHistories } from "../src/lib/yahoo";

type UniverseFile = { history: UniverseMonth[] };
type MarketDataFile = { histories?: Record<string, PricePoint[]> };

async function existingHistories(path: string): Promise<Record<string, PricePoint[]>> {
  try { return (JSON.parse(await readFile(path, "utf8")) as MarketDataFile).histories ?? {}; } catch { return {}; }
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
  const dashboard = buildDashboardPayload(histories, universeHistory);
  await mkdir(dirname(outputPath), { recursive: true });
  await writeFile(outputPath, `${JSON.stringify({ generatedAt: dashboard.generatedAt, histories, dashboard })}\n`);
  await writeFile(resolve("public/data/live-state.json"), `${JSON.stringify(dashboard.liveState)}\n`);
  console.log(`Saved ${outputPath}; signal ${dashboard.currentSignal?.signalDate ?? "none"}; state ${dashboard.liveState.state}`);
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
