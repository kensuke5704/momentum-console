import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { emptyForwardOos, OOS_START_DATE } from "../src/lib/oos";
import type { DashboardPayload } from "../src/lib/types";

async function main() {
  const dashboardPath = resolve("public/data/dashboard.json");
  const dashboardFile = JSON.parse(await readFile(dashboardPath, "utf8")) as { dashboard: DashboardPayload };
  const dashboard = dashboardFile.dashboard;
  const dataThrough = dashboard.backtest.equityCurve.at(-1)?.date ?? null;
  const frozen = { strategyId: dashboard.config.strategyId, frozenAt: OOS_START_DATE, dataThrough, backtest: dashboard.backtest };
  const oos = emptyForwardOos(dashboard.config.strategyId);
  const nextDashboard = { ...dashboard, oos };

  await writeFile(resolve("public/data/backtest-frozen.json"), `${JSON.stringify(frozen)}\n`);
  await writeFile(resolve("public/data/oos-performance.json"), `${JSON.stringify(oos)}\n`);
  await writeFile(dashboardPath, `${JSON.stringify({ dashboard: nextDashboard })}\n`);

  console.log(`Frozen backtest through ${dataThrough ?? "no data"}; Forward OOS starts ${OOS_START_DATE}`);
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
