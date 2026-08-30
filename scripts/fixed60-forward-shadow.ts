import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { runBacktest, performanceStats } from "../src/lib/backtest";
import type { EquityPoint, PricePoint, StrategyConfig, UniverseMonth } from "../src/lib/types";

const FREEZE_DATE = "2026-08-30";
const SHADOW_START = "2026-08-31"; // first US session after the rule freeze
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
  startedAt: string;
  trueForwardOos: true;
  rule: string;
  source: string;
  asOf: string | null;
  baselineRawEquity: number | null;
  equityCurve: EquityPoint[];
  stats: ReturnType<typeof performanceStats>;
  note: string;
};

async function main() {
  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as {
    histories: Record<string, PricePoint[]>;
  };
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
  const hasPostFreezeObservation = curve.some((p) => p.date > SHADOW_START);
  const out: ShadowFile = {
    strategyId: STRATEGY_ID,
    frozenAt: FREEZE_DATE,
    startedAt: SHADOW_START,
    trueForwardOos: true,
    rule: "Production 0/20/80 + unchanged state machine; fixed Top1/Top2 60/40; fresh state after freeze; next-session-open execution; no leverage",
    source: "Yahoo Finance adjusted OHLC + PIT universe history",
    asOf: hasPostFreezeObservation ? curve.at(-1)?.date ?? null : null,
    baselineRawEquity: baseline,
    equityCurve: curve,
    stats: performanceStats(curve),
    note: latestMarketDate && latestMarketDate < SHADOW_START
      ? `No post-freeze market observation yet; latest market data is ${latestMarketDate}.`
      : "Shadow starts from a fresh state on the first US session after the 2026-08-30 rule freeze. Historical Fixed60 state is not carried into the shadow series.",
  };
  const dir = resolve("data/research/fixed60-forward-shadow");
  await mkdir(dir, { recursive: true });
  await writeFile(resolve(dir, "result.json"), `${JSON.stringify(out, null, 2)}\n`);
  console.log(JSON.stringify({ strategyId: out.strategyId, latestMarketDate, asOf: out.asOf, points: curve.length, stats: out.stats, note: out.note }, null, 2));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
