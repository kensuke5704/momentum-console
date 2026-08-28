import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { gunzipSync } from "node:zlib";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { runStrategySimulation } from "../src/lib/backtest";
import { buildPointInTimeUniverse } from "../src/lib/universe/universe";
import { fetchHistories } from "../src/lib/yahoo";
import type { NportFiling, PricePoint, UniverseMember, UniverseMonth } from "../src/lib/types";

type MarketDataFile = { histories?: Record<string, PricePoint[]> };
type UniverseFile = { history: UniverseMonth[] };
type BootstrapFile = { snapshots: NportFiling[] };

const START = "2020-01-01";
const END = "2026-08-25";
const SIZES = [60, 70, 80, 90, 100] as const;
const MAX_SIZE = 120 as typeof PRODUCTION_STRATEGY.universe.size;

function overlap(a: UniverseMember[], b: UniverseMember[]) {
  const bs = new Set(b.map((x) => x.symbol));
  return a.filter((x) => bs.has(x.symbol)).length / Math.max(1, a.length);
}

async function main() {
  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as MarketDataFile;
  const universe = JSON.parse(await readFile(resolve("data/universe-history.json"), "utf8")) as UniverseFile;
  const bootstrap = JSON.parse(gunzipSync(await readFile(resolve("data/sec-nport/bootstrap.json.gz"))).toString("utf8")) as BootstrapFile;
  const baselineHistory = universe.history.filter((u) => u.asOf >= START && u.asOf <= END);

  const top120ByDate = new Map<string, UniverseMonth>();
  const allSymbols = new Set<string>();
  for (const base of baselineHistory) {
    const u = buildPointInTimeUniverse(bootstrap.snapshots, base.signalMonth, base.asOf, null, MAX_SIZE);
    top120ByDate.set(base.asOf, u);
    for (const row of u.symbols) allSymbols.add(row.symbol);
  }

  const histories: Record<string, PricePoint[]> = Object.fromEntries(
    Object.entries(market.histories ?? {}).map(([symbol, points]) => [symbol, points.filter((p) => p.date <= END)]),
  );
  const missing = [...allSymbols].filter((s) => !histories[s]?.length);
  if (missing.length) {
    console.error(`Fetching ${missing.length} missing Top120 histories`);
    const fetched = await fetchHistories(missing, 6);
    for (const [symbol, points] of Object.entries(fetched)) histories[symbol] = points.filter((p) => p.date <= END);
  }
  const unavailable = [...allSymbols].filter((s) => !histories[s]?.length);
  console.error(`Unavailable after Yahoo fetch: ${unavailable.length}`);

  const rows = SIZES.map((size) => {
    const history: UniverseMonth[] = baselineHistory.map((base) => {
      if (size === 80) return base;
      const source = top120ByDate.get(base.asOf);
      if (!source) return base;
      const selected = source.symbols.filter((row) => histories[row.symbol]?.length).slice(0, size);
      return {
        ...base,
        symbols: selected.map((row, index) => ({ ...row, universeRank: index + 1 })),
      };
    });
    const stats = runStrategySimulation({ histories, universeHistory: history, config: PRODUCTION_STRATEGY }).backtest.stats;
    const meanUniverseCount = history.reduce((s, u) => s + u.symbols.length, 0) / Math.max(1, history.length);
    const baselineOverlap = size === 80 ? 1 : history.reduce((s, u, i) => s + overlap(u.symbols, baselineHistory[i]?.symbols ?? []), 0) / Math.max(1, history.length);
    return { size, meanUniverseCount, baselineOverlap, ...stats };
  });

  const baseline = rows.find((r) => r.size === 80)!;
  const output = {
    generatedAt: new Date().toISOString(),
    period: { start: START, end: END },
    strategyId: PRODUCTION_STRATEGY.strategyId,
    method: "Deterministic Universe size sensitivity using point-in-time N-PORT ranking. Top80 uses the exact saved Production universe history. Other sizes use reconstructed Top120 ranking, remove symbols with no usable Yahoo history, then take the first N priced candidates. Full Production strategy state machine is recomputed causally.",
    caveat: "Top90/100 can contain historical delisted/old tickers no longer available from Yahoo; unavailable symbols are replaced by the next ranked priced candidate. Therefore this is a priced-candidate size sensitivity test, not a pristine historical reconstruction.",
    unavailableHistoryCount: unavailable.length,
    unavailableSymbols: unavailable,
    baselineSize: 80,
    baseline,
    rows: rows.map((r) => ({ ...r, cagrDeltaVs80: r.cagr - baseline.cagr, maxDrawdownDeltaVs80: r.maxDrawdown - baseline.maxDrawdown })),
  };
  console.log(JSON.stringify(output, null, 2));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
