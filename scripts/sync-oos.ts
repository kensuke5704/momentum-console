import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import type { DashboardPayload, ForwardOosResult, OosRecord } from "../src/lib/types";
async function main() {
  const generated = JSON.parse(await readFile(resolve("public/data/dashboard.json"), "utf8")) as { dashboard: DashboardPayload };
  const dashboard = generated.dashboard, signal = dashboard.currentSignal;
  if (!signal) throw new Error("No current dynamic strategy signal");
  const path = resolve("public/data/oos-performance.json");
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
  await mkdir(resolve("public/data"), { recursive: true });
  await writeFile(path, `${JSON.stringify({ ...oos, records })}\n`);
  console.log(`Forward OOS ${record.signalMonth}: ${record.selectedSymbols.join(", ") || "CASH"}`);
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
