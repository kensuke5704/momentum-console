import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { runBacktest } from "../src/lib/backtest";
import { updateForwardOos } from "../src/lib/oos";
import type { DashboardPayload, ForwardOosResult, OosRecord, PricePoint, UniverseMonth } from "../src/lib/types";
async function main() {
  const generated = JSON.parse(await readFile(resolve("public/data/dashboard.json"), "utf8")) as { dashboard: DashboardPayload };
  const dashboard = generated.dashboard, signal = dashboard.currentSignal;
  if (!signal) throw new Error("No current dynamic strategy signal");
  const path = resolve("public/data/oos-performance.json");
  const marketPath = resolve("public/data/market-data.json");
  const market = JSON.parse(await readFile(marketPath, "utf8")) as { generatedAt: string; histories: Record<string, PricePoint[]>; dashboard: DashboardPayload; [key: string]: unknown };
  const universe = JSON.parse(await readFile(resolve("data/universe-history.json"), "utf8")) as { history: UniverseMonth[] };
  let oos = dashboard.oos;
  try {
    const existing = JSON.parse(await readFile(path, "utf8")) as ForwardOosResult;
    if (existing.strategyId === PRODUCTION_STRATEGY.strategyId) oos = existing;
  } catch { /* New strategy starts a separate Forward OOS series. */ }
  const record: OosRecord = {
    strategyId: PRODUCTION_STRATEGY.strategyId, signalMonth: signal.signalMonth, signalDate: signal.signalDate, executionDate: signal.executionDate,
    universeSymbols: signal.universe, rankedCandidates: signal.candidates, selectedSymbols: signal.selectedSymbols, targetWeights: signal.targetWeights,
    marketState: signal.marketRiskOn ? "RISK_ON" : "RISK_OFF", riskState: dashboard.liveState.state,
    entryPrices: Object.fromEntries(dashboard.liveState.currentPositions.map((position) => [position.symbol, position.entryPrice])), exitPrices: {}, return: null, equity: null,
    triggerHistory: dashboard.backtest.events.filter((event) => event.date >= signal.signalDate),
  };
  const records = [...oos.records.filter((row) => row.signalMonth !== record.signalMonth), record].sort((a, b) => a.signalMonth.localeCompare(b.signalMonth));
  const actualBacktest = runBacktest({ histories: market.histories, universeHistory: universe.history });
  const provisionalDates = [...new Set(Object.values(market.histories).flatMap((points) => points.filter((point) => point.provisional).map((point) => point.date)))];
  const updated = { ...updateForwardOos(actualBacktest, oos, provisionalDates), records };
  await mkdir(resolve("public/data"), { recursive: true });
  await writeFile(path, `${JSON.stringify(updated)}\n`);
  const patchedDashboard = { ...dashboard, oos: updated };
  await writeFile(resolve("public/data/dashboard.json"), `${JSON.stringify({ dashboard: patchedDashboard })}\n`);
  await writeFile(marketPath, `${JSON.stringify({ ...market, dashboard: { ...market.dashboard, oos: updated } })}\n`);
  console.log(`Forward OOS ${record.signalMonth}: ${record.selectedSymbols.join(", ") || "CASH"}`);
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
