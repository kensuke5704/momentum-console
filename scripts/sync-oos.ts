import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import type { DashboardPayload } from "../src/lib/types";

type OosRecord = {
  strategyId: string; signalMonth: string; signalDate: string; executionDate: string | null;
  universeSymbols: string[]; rankedCandidates: unknown[]; selectedSymbols: string[]; targetWeights: number[];
  marketState: string; riskState: string; entryPrices: Record<string, number>; exitPrices: Record<string, number>;
  return: number | null; equity: number | null; triggerHistory: unknown[];
};
async function main() {
  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as { dashboard: DashboardPayload };
  const dashboard = market.dashboard, signal = dashboard.currentSignal;
  if (!signal) throw new Error("No current dynamic strategy signal");
  const path = resolve("public/data/oos-performance.json");
  let records: OosRecord[] = [];
  try {
    const existing = JSON.parse(await readFile(path, "utf8")) as { strategyId?: string; records?: OosRecord[] };
    if (existing.strategyId === PRODUCTION_STRATEGY.strategyId) records = existing.records ?? [];
  } catch { /* New strategy starts a separate Forward OOS series. */ }
  const record: OosRecord = {
    strategyId: PRODUCTION_STRATEGY.strategyId, signalMonth: signal.signalMonth, signalDate: signal.signalDate, executionDate: signal.executionDate,
    universeSymbols: signal.universe, rankedCandidates: signal.candidates, selectedSymbols: signal.selectedSymbols, targetWeights: signal.targetWeights,
    marketState: signal.marketRiskOn ? "RISK_ON" : "RISK_OFF", riskState: dashboard.liveState.state,
    entryPrices: Object.fromEntries(dashboard.liveState.currentPositions.map((position) => [position.symbol, position.entryPrice])), exitPrices: {}, return: null, equity: null,
    triggerHistory: dashboard.backtest.events.filter((event) => event.date >= signal.signalDate),
  };
  records = [...records.filter((row) => row.signalMonth !== record.signalMonth), record].sort((a, b) => a.signalMonth.localeCompare(b.signalMonth));
  await mkdir(resolve("public/data"), { recursive: true });
  await writeFile(path, `${JSON.stringify({ strategyId: PRODUCTION_STRATEGY.strategyId, startedAt: "2026-08-24", records })}\n`);
  console.log(`Forward OOS ${record.signalMonth}: ${record.selectedSymbols.join(", ") || "CASH"}`);
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
