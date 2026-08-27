import { readFile, mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { runStrategySimulation } from "../src/lib/backtest";
import type { PricePoint, UniverseMonth } from "../src/lib/types";

type MarketDataFile = { histories?: Record<string, PricePoint[]> };
type UniverseFile = { history: UniverseMonth[] };
type Profile = { symbol: string; companyName?: string; industry?: string; sector?: string };
type ProfilesFile = { profiles?: Record<string, Profile> };

const START = "2020-01-01";
const END = "2026-08-25";

function filteredUniverse(history: UniverseMonth[], excluded: Set<string>) {
  return history.map((u) => ({ ...u, symbols: u.symbols.filter((row) => !excluded.has(row.symbol)) }));
}

function selectedCounts(events: Array<{ type: string; symbols: string[] }>) {
  const counts = new Map<string, number>();
  for (const event of events) {
    if (event.type !== "ENTRY_OPEN") continue;
    for (const symbol of event.symbols) counts.set(symbol, (counts.get(symbol) ?? 0) + 1);
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([symbol, entries]) => ({ symbol, entries }));
}

async function main() {
  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as MarketDataFile;
  const universe = JSON.parse(await readFile(resolve("data/universe-history.json"), "utf8")) as UniverseFile;
  const profilesFile = JSON.parse(await readFile(resolve("public/data/company-profiles.json"), "utf8")) as ProfilesFile;
  const profiles = profilesFile.profiles ?? {};
  const histories = Object.fromEntries(Object.entries(market.histories ?? {}).map(([s, pts]) => [s, pts.filter((p) => p.date <= END)]));
  const universeHistory = universe.history.filter((u) => u.asOf >= START && u.asOf <= END);

  const baseline = runStrategySimulation({ histories, universeHistory, config: PRODUCTION_STRATEGY }).backtest;
  const selections = selectedCounts(baseline.events);
  const selectedSymbols = selections.map((row) => row.symbol);

  const leaveOneOut = [] as Array<Record<string, unknown>>;
  for (const symbol of selectedSymbols) {
    const sim = runStrategySimulation({ histories, universeHistory: filteredUniverse(universeHistory, new Set([symbol])), config: PRODUCTION_STRATEGY }).backtest;
    leaveOneOut.push({
      symbol,
      entriesInBaseline: selections.find((row) => row.symbol === symbol)?.entries ?? 0,
      companyName: profiles[symbol]?.companyName ?? null,
      sector: profiles[symbol]?.sector ?? "Unknown",
      industry: profiles[symbol]?.industry ?? "Unknown",
      stats: sim.stats,
      cagrDifferenceVsBaseline: sim.stats.cagr - baseline.stats.cagr,
      maxDrawdownDifferenceVsBaseline: sim.stats.maxDrawdown - baseline.stats.maxDrawdown,
    });
  }
  leaveOneOut.sort((a, b) => Number(a.cagrDifferenceVsBaseline) - Number(b.cagrDifferenceVsBaseline));

  const selectedBySector = new Map<string, Set<string>>();
  for (const symbol of selectedSymbols) {
    const sector = profiles[symbol]?.sector ?? "Unknown";
    if (!selectedBySector.has(sector)) selectedBySector.set(sector, new Set());
    selectedBySector.get(sector)!.add(symbol);
  }

  const sectorLeaveOut = [] as Array<Record<string, unknown>>;
  for (const [sector, symbols] of selectedBySector) {
    const sim = runStrategySimulation({ histories, universeHistory: filteredUniverse(universeHistory, symbols), config: PRODUCTION_STRATEGY }).backtest;
    sectorLeaveOut.push({
      sector,
      baselineSelectedSymbols: [...symbols].sort(),
      symbolCount: symbols.size,
      stats: sim.stats,
      cagrDifferenceVsBaseline: sim.stats.cagr - baseline.stats.cagr,
      maxDrawdownDifferenceVsBaseline: sim.stats.maxDrawdown - baseline.stats.maxDrawdown,
    });
  }
  sectorLeaveOut.sort((a, b) => Number(a.cagrDifferenceVsBaseline) - Number(b.cagrDifferenceVsBaseline));

  const sectorEntryCounts = new Map<string, number>();
  for (const row of selections) {
    const sector = profiles[row.symbol]?.sector ?? "Unknown";
    sectorEntryCounts.set(sector, (sectorEntryCounts.get(sector) ?? 0) + row.entries);
  }
  const totalSymbolEntries = selections.reduce((sum, row) => sum + row.entries, 0);
  const sectorSelectionShare = [...sectorEntryCounts.entries()]
    .map(([sector, entries]) => ({ sector, entries, share: totalSymbolEntries ? entries / totalSymbolEntries : 0 }))
    .sort((a, b) => b.entries - a.entries);

  const output = {
    generatedAt: new Date().toISOString(),
    period: { start: START, end: END },
    strategyId: PRODUCTION_STRATEGY.strategyId,
    method: "Production strategy unchanged. Each leave-one-out run removes the symbol (or sector's baseline-selected symbols) from every point-in-time Universe and lets the normal ranking fill the next candidate.",
    baseline: baseline.stats,
    baselineSelections: selections.map((row) => ({ ...row, companyName: profiles[row.symbol]?.companyName ?? null, sector: profiles[row.symbol]?.sector ?? "Unknown", industry: profiles[row.symbol]?.industry ?? "Unknown" })),
    sectorSelectionShare,
    leaveOneOut,
    sectorLeaveOut,
  };
  const out = resolve("data/research/symbol-concentration-audit.json");
  await mkdir(dirname(out), { recursive: true });
  await writeFile(out, `${JSON.stringify(output, null, 2)}\n`);
  console.log(JSON.stringify(output, null, 2));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
