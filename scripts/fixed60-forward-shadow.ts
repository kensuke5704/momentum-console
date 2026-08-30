import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { runBacktest, performanceStats } from "../src/lib/backtest";
import type { EquityPoint, PricePoint, StrategyConfig, UniverseMonth } from "../src/lib/types";

const FREEZE_DATE = "2026-08-30";
const SHADOW_START = "2026-08-31"; // first US session after the rule freeze; signal at close, entry next session open
const STRATEGY_ID = "momentum-dynamic-fixed60-shadow-2026-08-30";

const FIXED60 = {
  ...PRODUCTION_STRATEGY,
  strategyId: STRATEGY_ID,
  allocation: {
    ...PRODUCTION_STRATEGY.allocation,
    baseTop1Weight: 0.60,
    concentratedTop1Weight: 0.60,
    maxTop1Weight: 0.60,
  },
  backtestStart: SHADOW_START,
} satisfies StrategyConfig;

type ShadowFile = {
  strategyId: string;
  frozenAt: string;
  eligibleFrom: string;
  oosClass: "TRUE_FORWARD_ELIGIBLE";
  hasObservations: boolean;
  firstEligibleSignalDate: string;
  firstEligibleExecution: string;
  rule: string;
  source: string;
  latestMarketDate: string | null;
  latestUniverseSignalDate: string | null;
  asOf: string | null;
  baselineRawEquity: number | null;
  equityCurve: EquityPoint[];
  stats: ReturnType<typeof performanceStats>;
  note: string;
};

async function main() {
  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as { histories: Record<string, PricePoint[]> };
  const universe = JSON.parse(await readFile(resolve("data/universe-history.json"), "utf8")) as { history: UniverseMonth[] };
  const result = runBacktest({ histories: market.histories, universeHistory: universe.history, config: FIXED60 });
  const raw = result.equityCurve.filter((p) => p.date >= SHADOW_START);
  const baseline = raw[0]?.equity ?? null;
  const normalized: EquityPoint[] = baseline == null ? [] : raw.map((p) => ({ ...p, equity: p.equity / baseline, drawdown: 0 }));
  let peak = 0;
  const curve = normalized.map((p) => {
    peak = Math.max(peak, p.equity);
    return { ...p, drawdown: peak > 0 ? p.equity / peak - 1 : 0 };
  });
  const latestMarketDate = (market.histories.QQQ ?? []).at(-1)?.date ?? null;
  const latestUniverseSignalDate = [...universe.history].sort((a,b) => a.asOf.localeCompare(b.asOf)).at(-1)?.asOf ?? null;
  // A flat signal-close point is not performance evidence. The first return observation can only exist after next-open execution.
  const hasObservations = curve.some((p) => p.date > SHADOW_START);
  const out: ShadowFile = {
    strategyId: STRATEGY_ID,
    frozenAt: FREEZE_DATE,
    eligibleFrom: SHADOW_START,
    oosClass: "TRUE_FORWARD_ELIGIBLE",
    hasObservations,
    firstEligibleSignalDate: SHADOW_START,
    firstEligibleExecution: "2026-09-01 next US-session open",
    rule: "Production 0/20/80 + unchanged state machine; fixed Top1/Top2 60/40; fresh state after freeze; next-session-open execution; no leverage",
    source: "Yahoo Finance adjusted OHLC + PIT universe history",
    latestMarketDate,
    latestUniverseSignalDate,
    asOf: hasObservations ? curve.at(-1)?.date ?? null : null,
    baselineRawEquity: baseline,
    equityCurve: curve,
    stats: performanceStats(curve),
    note: !hasObservations
      ? `No Fixed60 True Forward performance observation exists yet. Latest market date=${latestMarketDate ?? "none"}; latest completed PIT universe signal=${latestUniverseSignalDate ?? "none"}.`
      : "True Forward shadow uses only dates after the 2026-08-30 rule freeze. Historical Fixed60 state is not carried into this series.",
  };
  const dir = resolve("data/research/fixed60-forward-shadow");
  await mkdir(dir, { recursive: true });
  await writeFile(resolve(dir, "result.json"), `${JSON.stringify(out, null, 2)}\n`);
  console.log(JSON.stringify({ strategyId: out.strategyId, latestMarketDate, latestUniverseSignalDate, oosClass: out.oosClass, hasObservations, asOf: out.asOf, points: curve.length, stats: out.stats, note: out.note }, null, 2));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
