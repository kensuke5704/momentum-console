import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { PRODUCTION_PORTFOLIO } from "../src/lib/portfolio-config";
import { OOS_START_DATE, updateForwardOos } from "../src/lib/oos";
import type { DashboardPayload, ForwardOosResult, OosRecord, PricePoint } from "../src/lib/types";

async function main() {
  const generated = JSON.parse(await readFile(resolve("public/data/dashboard.json"), "utf8")) as { dashboard: DashboardPayload };
  const dashboard = generated.dashboard, signal = dashboard.currentSignal;
  if (!signal) throw new Error("No current Fixed60 dynamic signal; Stage21 OOS snapshot cannot be audited");
  const path = resolve("public/data/oos-performance.json"), marketPath = resolve("public/data/market-data.json");
  const market = JSON.parse(await readFile(marketPath, "utf8")) as { generatedAt: string; histories: Record<string, PricePoint[]>; dashboard: DashboardPayload; [key: string]: unknown };
  let oos = dashboard.oos;
  try {
    const existing = JSON.parse(await readFile(path, "utf8")) as ForwardOosResult;
    if (existing.strategyId === PRODUCTION_PORTFOLIO.strategyId && existing.startedAt === OOS_START_DATE) oos = existing;
  } catch { /* Stage21 starts a clean Forward OOS series. */ }

  const recordDate = dashboard.portfolioState.asOf;
  const fundedTargets = dashboard.portfolioState.targets;
  const record: OosRecord = {
    strategyId: PRODUCTION_PORTFOLIO.strategyId,
    recordDate,
    signalMonth: signal.signalMonth,
    signalDate: signal.signalDate,
    executionDate: dashboard.portfolioState.nextAction.executionDate,
    universeSymbols: signal.universe,
    rankedCandidates: signal.candidates,
    selectedSymbols: fundedTargets.filter((target) => target.symbol !== "CASH").map((target) => target.symbol),
    targetWeights: fundedTargets.filter((target) => target.symbol !== "CASH").map((target) => target.weight),
    marketState: signal.marketRiskOn ? "RISK_ON" : "RISK_OFF",
    riskState: dashboard.liveState.state,
    portfolioState: dashboard.portfolioState.regime,
    portfolioTargets: fundedTargets,
    cftc: dashboard.portfolioState.cftc,
    entryPrices: Object.fromEntries(dashboard.portfolioState.holdings.map((position) => [position.symbol, position.entryPrice])),
    exitPrices: {}, return: null, equity: null,
    triggerHistory: dashboard.oosBacktest.events.filter((event) => event.date >= OOS_START_DATE),
  };
  const records = recordDate >= OOS_START_DATE
    ? [...oos.records.filter((row) => (row.recordDate ?? row.signalDate) !== recordDate), record].sort((a, b) => (a.recordDate ?? a.signalDate).localeCompare(b.recordDate ?? b.signalDate))
    : oos.records;
  const provisionalDates = [...new Set(Object.values(market.histories).flatMap((points) => points.filter((point) => point.provisional).map((point) => point.date)))];
  // Keep the Backtest tab frozen at the OOS boundary, while extending OOS
  // from the current daily simulation (including a validated provisional close).
  const updated = { ...updateForwardOos(dashboard.oosBacktest, oos, provisionalDates), records };
  await mkdir(resolve("public/data"), { recursive: true });
  await writeFile(path, `${JSON.stringify(updated)}\n`);
  const patchedDashboard = { ...dashboard, oos: updated };
  await writeFile(resolve("public/data/dashboard.json"), `${JSON.stringify({ dashboard: patchedDashboard })}\n`);
  await writeFile(marketPath, `${JSON.stringify({ ...market, dashboard: { ...market.dashboard, oos: updated } })}\n`);
  console.log(recordDate >= OOS_START_DATE
    ? `Stage21 Forward OOS ${recordDate}: ${dashboard.portfolioState.regime}; ${fundedTargets.map((target) => `${target.symbol} ${(target.weight*100).toFixed(1)}%`).join(", ")}`
    : `Stage21 Forward OOS not started: ${recordDate} precedes ${OOS_START_DATE}`);
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
