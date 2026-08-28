import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
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
const PATHS = 50;
const SEED = 20260828;
const TOP100_SIZE = 100 as typeof PRODUCTION_STRATEGY.universe.size;

function rng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function choose<T>(rows: T[], count: number, r: () => number): T[] {
  const copy = [...rows];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(r() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy.slice(0, Math.min(count, copy.length));
}

function quantile(xs: number[], q: number) {
  const a = [...xs].sort((x, y) => x - y);
  const p = (a.length - 1) * q;
  const lo = Math.floor(p), hi = Math.ceil(p);
  return a[lo] + (a[hi] - a[lo]) * (p - lo);
}

function summarize(xs: number[]) {
  return {
    min: Math.min(...xs), p05: quantile(xs, 0.05), p25: quantile(xs, 0.25), median: quantile(xs, 0.5),
    mean: xs.reduce((s, x) => s + x, 0) / xs.length, p75: quantile(xs, 0.75), p95: quantile(xs, 0.95), max: Math.max(...xs),
  };
}

function makeBoundaryHistory(args: {
  baseline: UniverseMonth[];
  top100ByDate: Map<string, UniverseMonth>;
  histories: Record<string, PricePoint[]>;
  coreCount: number;
  poolStartRank: number;
  poolEndRank: number;
  chooseCount: number;
  seed: number;
}) {
  const r = rng(args.seed);
  let replacedSlots = 0;
  let skippedMonthsInsufficientPool = 0;
  const history = args.baseline.map((base) => {
    const top100 = args.top100ByDate.get(base.asOf);
    if (!top100 || base.symbols.length < args.coreCount) return base;
    const core = base.symbols.slice(0, args.coreCount);
    const coreSymbols = new Set(core.map((row) => row.symbol));
    const pool = top100.symbols.filter((row) =>
      row.universeRank >= args.poolStartRank && row.universeRank <= args.poolEndRank &&
      !coreSymbols.has(row.symbol) && (args.histories[row.symbol]?.length ?? 0) > 0,
    );
    const selected = choose(pool, args.chooseCount, r);
    if (selected.length < args.chooseCount) {
      skippedMonthsInsufficientPool += 1;
      return base;
    }
    const baselineBoundary = new Set(base.symbols.slice(args.coreCount).map((row) => row.symbol));
    replacedSlots += selected.filter((row) => !baselineBoundary.has(row.symbol)).length;
    const symbols: UniverseMember[] = [...core, ...selected].map((row, index) => ({ ...row, universeRank: index + 1 }));
    return { ...base, symbols };
  });
  return { history, replacedSlots, skippedMonthsInsufficientPool };
}

async function main() {
  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as MarketDataFile;
  const universe = JSON.parse(await readFile(resolve("data/universe-history.json"), "utf8")) as UniverseFile;
  const bootstrap = JSON.parse(gunzipSync(await readFile(resolve("data/sec-nport/bootstrap.json.gz"))).toString("utf8")) as BootstrapFile;
  const baselineHistory = universe.history.filter((u) => u.asOf >= START && u.asOf <= END);
  const top100ByDate = new Map<string, UniverseMonth>();
  const top80Overlap: number[] = [];
  for (const base of baselineHistory) {
    const top100 = buildPointInTimeUniverse(bootstrap.snapshots, base.signalMonth, base.asOf, null, TOP100_SIZE);
    top100ByDate.set(base.asOf, top100);
    const reconstructed80 = new Set(top100.symbols.slice(0, 80).map((r) => r.symbol));
    top80Overlap.push(base.symbols.filter((r) => reconstructed80.has(r.symbol)).length / Math.max(1, base.symbols.length));
  }

  const boundarySymbols = new Set<string>();
  for (const top100 of top100ByDate.values()) for (const row of top100.symbols) if (row.universeRank >= 76 && row.universeRank <= 90) boundarySymbols.add(row.symbol);
  const histories: Record<string, PricePoint[]> = Object.fromEntries(Object.entries(market.histories ?? {}).map(([symbol, points]) => [symbol, points.filter((p) => p.date <= END)]));
  const initiallyMissing = [...boundarySymbols].filter((symbol) => !histories[symbol]?.length);
  if (initiallyMissing.length) {
    console.error(`Fetching ${initiallyMissing.length} missing boundary histories`);
    const fetched = await fetchHistories(initiallyMissing, 6);
    for (const [symbol, points] of Object.entries(fetched)) histories[symbol] = points.filter((p) => p.date <= END);
  }
  const unavailable = initiallyMissing.filter((symbol) => !histories[symbol]?.length);
  console.error(`Unavailable after Yahoo fetch: ${unavailable.length}`);

  const baseline = runStrategySimulation({ histories, universeHistory: baselineHistory, config: PRODUCTION_STRATEGY }).backtest.stats;
  const scenarios = [
    { label: "NARROW_78_83", coreCount: 77, poolStartRank: 78, poolEndRank: 83, chooseCount: 3, offset: 3000 },
    { label: "MODERATE_76_90", coreCount: 75, poolStartRank: 76, poolEndRank: 90, chooseCount: 5, offset: 4000 },
  ];
  const results = [];
  for (const scenario of scenarios) {
    const rows = [];
    for (let i = 0; i < PATHS; i++) {
      const perturbed = makeBoundaryHistory({ baseline: baselineHistory, top100ByDate, histories, ...scenario, seed: SEED + scenario.offset + i });
      const stats = runStrategySimulation({ histories, universeHistory: perturbed.history, config: PRODUCTION_STRATEGY }).backtest.stats;
      rows.push({ path: i + 1, seed: SEED + scenario.offset + i, replacedSlots: perturbed.replacedSlots, skippedMonthsInsufficientPool: perturbed.skippedMonthsInsufficientPool, ...stats });
      if ((i + 1) % 10 === 0) console.error(`${scenario.label}: ${i + 1}/${PATHS}`);
    }
    results.push({ ...scenario, paths: PATHS, summary: {
      cagr: summarize(rows.map((r) => r.cagr)), maxDrawdown: summarize(rows.map((r) => r.maxDrawdown)), calmar: summarize(rows.map((r) => r.calmar ?? 0)), finalEquity: summarize(rows.map((r) => r.finalEquity)),
      replacedSlots: summarize(rows.map((r) => r.replacedSlots)), skippedMonthsInsufficientPool: summarize(rows.map((r) => r.skippedMonthsInsufficientPool)),
      probabilityCagrBelow50: rows.filter((r) => r.cagr < 0.5).length / PATHS, probabilityCagrBelowBaseline: rows.filter((r) => r.cagr < baseline.cagr).length / PATHS,
    }, rows });
  }

  const output = {
    generatedAt: new Date().toISOString(), period: { start: START, end: END }, strategyId: PRODUCTION_STRATEGY.strategyId, seed: SEED, pathsPerScenario: PATHS,
    method: "Top80 boundary perturbation using point-in-time N-PORT bootstrap and production Universe scoring. Boundary slots are resampled from reconstructed ranks near 80, including ranks outside Top80, but only where usable daily price history is available; full strategy state is recomputed causally.",
    caveat: "Candidates whose historical prices are no longer available from Yahoo (typically delisted/old tickers) are excluded from random sampling instead of being treated as ineligible holes. This avoids missing-data downward bias but can introduce survivorship bias, so results are a priced-candidate robustness test rather than a pristine historical counterfactual.",
    boundaryCandidateCount: boundarySymbols.size, initiallyMissingHistories: initiallyMissing.length, unavailableHistoryCount: unavailable.length, unavailableSymbols: unavailable,
    reconstructedTop80Overlap: summarize(top80Overlap), baseline, scenarios: results,
  };
  const out = resolve("data/research/universe-boundary-perturbation-priced.json");
  await mkdir(dirname(out), { recursive: true });
  await writeFile(out, JSON.stringify(output, null, 2) + "\n");
  console.log(JSON.stringify(output, null, 2));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
