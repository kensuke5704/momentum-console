import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { OOS_START_DATE } from "../src/lib/oos";
import type { DashboardPayload } from "../src/lib/types";

async function main() {
  const dashboardPath = resolve(process.argv[2] ?? "public/data/dashboard.json");
  const outputPath = resolve(process.argv[3] ?? "public/data/backtest-frozen.json");
  const dashboardFile = JSON.parse(await readFile(dashboardPath, "utf8")) as { dashboard: DashboardPayload };
  const dashboard = dashboardFile.dashboard;
  const dataThrough = dashboard.backtest.equityCurve.at(-1)?.date ?? null;
  const strategyId = dashboard.portfolioConfig.strategyId;
  if (dashboard.backtest.strategyId !== strategyId) throw new Error(`Cannot freeze mismatched backtest ${dashboard.backtest.strategyId} for ${strategyId}`);
  const frozen = { strategyId, frozenAt: OOS_START_DATE, dataThrough, backtest: dashboard.backtest };

  await writeFile(outputPath, `${JSON.stringify(frozen)}\n`);
  console.log(`Frozen Stage21 backtest through ${dataThrough ?? "no data"}; Forward OOS was left unchanged`);
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
