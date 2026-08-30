import fs from "node:fs/promises";
import path from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import { initialEngineState, transitionDay } from "../src/lib/strategy/state-machine";
import { performanceStats } from "../src/lib/backtest";
import type { EquityPoint, PricePoint, StrategyConfig, UniverseMonth } from "../src/lib/types";

const FIXED60: StrategyConfig = {
  ...PRODUCTION_STRATEGY,
  strategyId: "momentum-dynamic-fixed60-robustness-2026-08-30",
  allocation: {
    ...PRODUCTION_STRATEGY.allocation,
    baseTop1Weight: 0.60,
    concentratedTop1Weight: 0.60,
    maxTop1Weight: 0.60,
  },
};

type StressSpec = {
  family: string;
  label: string;
  config?: StrategyConfig;
  executionDelaySessions?: number;
  signalShiftSessions?: number;
  universeDropSeed?: number;
  universeDropFraction?: number;
};

type Stats = ReturnType<typeof performanceStats>;
type ScenarioResult = StressSpec & { stats: Stats; early: Stats | null; late: Stats | null; deltaCagrVsBase: number; deltaMaxDDVsBase: number };

function cloneConfig(patch: Partial<StrategyConfig> & { momentum?: Partial<StrategyConfig["momentum"]>; risk?: Partial<StrategyConfig["risk"]>; recovery?: Partial<StrategyConfig["recovery"]>; execution?: Partial<StrategyConfig["execution"]> }): StrategyConfig {
  return {
    ...FIXED60,
    ...patch,
    momentum: { ...FIXED60.momentum, ...(patch.momentum ?? {}) },
    risk: { ...FIXED60.risk, ...(patch.risk ?? {}) },
    recovery: { ...FIXED60.recovery, ...(patch.recovery ?? {}) },
    execution: { ...FIXED60.execution, ...(patch.execution ?? {}) },
    allocation: FIXED60.allocation,
  } as StrategyConfig;
}

function hash32(s: string): number {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}

function perturbUniverse(universe: UniverseMonth[], spec: StressSpec): UniverseMonth[] {
  if (spec.universeDropSeed == null || !spec.universeDropFraction) return universe;
  const threshold = spec.universeDropFraction;
  return universe.map((u) => ({
    ...u,
    symbols: u.symbols.filter((row) => {
      const x = hash32(`${spec.universeDropSeed}|${u.signalMonth}|${row.symbol}`) / 2 ** 32;
      return x >= threshold;
    }),
  }));
}

function shiftUniverseDates(universe: UniverseMonth[], dates: string[], shift: number): UniverseMonth[] {
  if (!shift) return universe;
  const idx = new Map(dates.map((d, i) => [d, i]));
  return universe.flatMap((u) => {
    const i = idx.get(u.asOf);
    if (i == null) return [];
    const shifted = dates[i + shift];
    return shifted ? [{ ...u, asOf: shifted }] : [];
  });
}

function sliceStats(curve: EquityPoint[], start: string, end: string): Stats | null {
  const xs = curve.filter((p) => p.date >= start && p.date <= end);
  if (xs.length < 2) return null;
  const prev = [...curve].reverse().find((p) => p.date < start);
  const rows = prev ? [prev, ...xs] : xs;
  const base = rows[0].equity;
  return performanceStats(rows.map((p) => ({ ...p, equity: p.equity / base })));
}

function simulate(histories: Record<string, PricePoint[]>, rawUniverse: UniverseMonth[], spec: StressSpec): EquityPoint[] {
  const config = spec.config ?? FIXED60;
  const qqq = [...(histories.QQQ ?? [])].sort((a, b) => a.date.localeCompare(b.date));
  const dates = qqq.map((p) => p.date);
  const dateIndex = new Map(dates.map((d, i) => [d, i]));
  const priceMaps = Object.fromEntries(Object.entries(histories).map(([s, ps]) => [s, new Map(ps.map((p) => [p.date, p]))]));
  let universe = perturbUniverse(rawUniverse, spec);
  universe = shiftUniverseDates(universe, dates, spec.signalShiftSessions ?? 0);
  const universeByDate = new Map(universe.map((u) => [u.asOf, u]));
  let state = initialEngineState(config);
  const curve: EquityPoint[] = [];
  const delay = spec.executionDelaySessions ?? 0;

  for (let i = 0; i < dates.length; i++) {
    const date = dates[i];
    if (date < config.backtestStart) continue;
    const executionDate = dates[i + 1 + delay] ?? null;
    const u = universeByDate.get(date);
    const signal = u ? buildMonthlySignal({ universe: u, histories, qqq, nextSessionDate: executionDate, config }) : null;
    const syms = new Set<string>([
      "QQQ",
      ...state.currentPositions.map((p) => p.symbol),
      ...(state.pendingSignal?.selectedSymbols ?? []),
      ...state.nextAction.symbols,
      ...(signal?.selectedSymbols ?? []),
    ]);
    const prices = Object.fromEntries([...syms].map((s) => [s, priceMaps[s]?.get(date)]));
    const qEnd = (dateIndex.get(date) ?? i) + 1;
    state = transitionDay(state, {
      date,
      prices,
      qqqHistoryThroughClose: qqq.slice(0, qEnd),
      monthlySignal: signal,
      nextSessionDate: executionDate,
    }, config);
    curve.push({ date, equity: state.currentEquity, drawdown: state.drawdown });
  }
  return curve;
}

const specs: StressSpec[] = [
  { family: "baseline", label: "BASE_FIXED60" },

  { family: "execution_delay", label: "EXEC_PLUS_1_SESSION", executionDelaySessions: 1 },
  { family: "execution_delay", label: "EXEC_PLUS_2_SESSIONS", executionDelaySessions: 2 },

  { family: "signal_date", label: "SIGNAL_MINUS_2_SESSIONS", signalShiftSessions: -2 },
  { family: "signal_date", label: "SIGNAL_MINUS_1_SESSION", signalShiftSessions: -1 },
  { family: "signal_date", label: "SIGNAL_PLUS_1_SESSION", signalShiftSessions: 1 },

  { family: "cost", label: "COST_20BP_SIDE", config: cloneConfig({ execution: { transactionCost: 0.002 } }) },
  { family: "cost", label: "COST_30BP_SIDE", config: cloneConfig({ execution: { transactionCost: 0.003 } }) },
  { family: "cost", label: "COST_50BP_SIDE", config: cloneConfig({ execution: { transactionCost: 0.005 } }) },
  { family: "cost", label: "COST_100BP_SIDE", config: cloneConfig({ execution: { transactionCost: 0.010 } }) },

  { family: "risk_stop", label: "STOP_15_75", config: cloneConfig({ risk: { individualStop: 0.1575 } }) },
  { family: "risk_stop", label: "STOP_19_25", config: cloneConfig({ risk: { individualStop: 0.1925 } }) },
  { family: "risk_circuit", label: "CIRCUIT_13_5", config: cloneConfig({ risk: { portfolioCircuit: 0.135 } }) },
  { family: "risk_circuit", label: "CIRCUIT_16_5", config: cloneConfig({ risk: { portfolioCircuit: 0.165 } }) },
  { family: "recovery", label: "RECOVERY_9", config: cloneConfig({ recovery: { confirmationDays: 9 } }) },
  { family: "recovery", label: "RECOVERY_11", config: cloneConfig({ recovery: { confirmationDays: 11 } }) },

  { family: "momentum", label: "MOM_0_15_85", config: cloneConfig({ momentum: { oneMonth: 0, threeMonth: 0.15, sixMonth: 0.85 } }) },
  { family: "momentum", label: "MOM_0_25_75", config: cloneConfig({ momentum: { oneMonth: 0, threeMonth: 0.25, sixMonth: 0.75 } }) },
  { family: "momentum", label: "MOM_10_20_70", config: cloneConfig({ momentum: { oneMonth: 0.10, threeMonth: 0.20, sixMonth: 0.70 } }) },

  ...[1, 2, 3, 4, 5].map((seed) => ({ family: "universe_dropout", label: `UNIVERSE_DROP10_SEED${seed}`, universeDropSeed: seed, universeDropFraction: 0.10 } as StressSpec)),
];

function q(sorted: number[], p: number): number | null {
  if (!sorted.length) return null;
  const idx = Math.min(sorted.length - 1, Math.max(0, Math.floor((sorted.length - 1) * p)));
  return sorted[idx];
}

async function main() {
  const market = JSON.parse(await fs.readFile(path.join(process.cwd(), "public/data/market-data.json"), "utf8")) as { histories: Record<string, PricePoint[]> };
  const uf = JSON.parse(await fs.readFile(path.join(process.cwd(), "data/universe-history.json"), "utf8")) as { history: UniverseMonth[] };
  const rawUniverse = [...uf.history].sort((a, b) => a.asOf.localeCompare(b.asOf));
  const curves = specs.map((spec) => ({ spec, curve: simulate(market.histories, rawUniverse, spec) }));
  const baseStats = performanceStats(curves[0].curve);
  const results: ScenarioResult[] = curves.map(({ spec, curve }) => {
    const stats = performanceStats(curve);
    return {
      ...spec,
      config: undefined,
      stats,
      early: sliceStats(curve, "2020-01-01", "2023-12-31"),
      late: sliceStats(curve, "2024-01-01", "2026-08-25"),
      deltaCagrVsBase: stats.cagr - baseStats.cagr,
      deltaMaxDDVsBase: stats.maxDrawdown - baseStats.maxDrawdown,
    };
  });
  const nonBase = results.filter((r) => r.family !== "baseline");
  const cagrSorted = nonBase.map((r) => r.stats.cagr).sort((a, b) => a - b);
  const familySummary = Object.fromEntries([...new Set(nonBase.map((r) => r.family))].map((family) => {
    const xs = nonBase.filter((r) => r.family === family);
    const cagrs = xs.map((r) => r.stats.cagr).sort((a, b) => a - b);
    return [family, {
      count: xs.length,
      minCagr: cagrs[0],
      medianCagr: q(cagrs, 0.5),
      maxCagr: cagrs.at(-1),
      allAbove40: xs.every((r) => r.stats.cagr >= 0.40),
      worstLabel: [...xs].sort((a, b) => a.stats.cagr - b.stats.cagr)[0]?.label ?? null,
    }];
  }));
  const output = {
    generatedAt: new Date().toISOString(),
    validity: {
      researchOnly: true,
      trueOOS: false,
      parameterSearch: false,
      fixedCandidate: "Fixed60",
      decisionUse: "Falsification/sensitivity only. Do not adopt the best scenario as a new rule.",
      predeclaredFamilies: ["execution_delay", "signal_date", "cost", "risk_stop", "risk_circuit", "recovery", "momentum", "universe_dropout"],
    },
    baseline: baseStats,
    results,
    ensembleSummary: {
      scenarioCountExcludingBaseline: nonBase.length,
      minGrossCagr: cagrSorted[0],
      p25GrossCagr: q(cagrSorted, 0.25),
      medianGrossCagr: q(cagrSorted, 0.5),
      p75GrossCagr: q(cagrSorted, 0.75),
      maxGrossCagr: cagrSorted.at(-1),
      shareAbove40: nonBase.filter((r) => r.stats.cagr >= 0.40).length / nonBase.length,
      shareAbove50: nonBase.filter((r) => r.stats.cagr >= 0.50).length / nonBase.length,
    },
    familySummary,
  };
  const dir = path.join(process.cwd(), "data/research/fixed60-robustness-stress");
  await fs.mkdir(dir, { recursive: true });
  await fs.writeFile(path.join(dir, "result.json"), JSON.stringify(output, null, 2));
  console.log(JSON.stringify(output, null, 2));
}

main().catch((e) => { console.error(e); process.exit(1); });
