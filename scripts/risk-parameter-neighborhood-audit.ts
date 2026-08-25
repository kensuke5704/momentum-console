import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { runBacktest } from "../src/lib/backtest";
import type { BacktestResult, PricePoint, StrategyConfig, UniverseMonth } from "../src/lib/types";

type MarketFile = { histories: Record<string, PricePoint[]> };
type UniverseFile = { history: UniverseMonth[] };
type Scenario = { group: "production" | "stop" | "circuit" | "recovery"; label: string; value: number; config: StrategyConfig };

const cloneConfig = (): StrategyConfig => structuredClone(PRODUCTION_STRATEGY) as StrategyConfig;

function scenario(group: Scenario["group"], label: string, value: number, mutate: (c: StrategyConfig) => void): Scenario {
  const config = cloneConfig();
  mutate(config);
  config.strategyId = `${PRODUCTION_STRATEGY.strategyId}-audit-${label}`;
  return { group, label, value, config };
}

function countReason(result: BacktestResult, needle: string): number {
  return result.events.filter((e) => e.type === "EXIT_OPEN" && e.reason.includes(needle)).length;
}

function recoveryEntries(result: BacktestResult): number {
  return result.events.filter((e) => e.type === "ENTRY_OPEN" && e.reason.includes("recovery closes confirmed")).length;
}

function exposureShare(result: BacktestResult): number {
  const dates = result.equityCurve.map((x) => x.date);
  const index = new Map(dates.map((d, i) => [d, i]));
  const exposed = new Array(dates.length).fill(false);
  let start: number | null = null;
  for (const e of result.events) {
    const i = index.get(e.date);
    if (i == null) continue;
    if (e.type === "ENTRY_OPEN" && start == null) start = i;
    if (e.type === "EXIT_OPEN" && start != null) {
      for (let j = start; j < i; j++) exposed[j] = true;
      start = null;
    }
  }
  if (start != null) for (let j = start; j < exposed.length; j++) exposed[j] = true;
  return exposed.filter(Boolean).length / Math.max(1, exposed.length);
}

function metrics(s: Scenario, result: BacktestResult) {
  return {
    group: s.group,
    label: s.label,
    value: s.value,
    cagr: result.stats.cagr,
    maxDrawdown: result.stats.maxDrawdown,
    annualizedVolatility: result.stats.annualizedVolatility,
    calmar: result.stats.calmar,
    finalEquity: result.stats.finalEquity,
    stopExits: countReason(result, "% stop"),
    circuitExits: countReason(result, "% circuit"),
    marketExits: countReason(result, "RiskOff"),
    recoveryEntries: recoveryEntries(result),
    exposureShare: exposureShare(result),
  };
}

function localShape(rows: ReturnType<typeof metrics>[], group: "stop" | "circuit" | "recovery", prodValue: number) {
  const xs = rows.filter((r) => r.group === group || r.group === "production")
    .filter((r) => group === "stop" ? [0.15, 0.175, 0.20].includes(r.value) : group === "circuit" ? [0.125, 0.15, 0.175].includes(r.value) : [5, 10, 15].includes(r.value))
    .sort((a,b)=>a.value-b.value);
  const production = xs.find((r) => r.value === prodValue)!;
  const peers = xs.filter((r) => r.value !== prodValue);
  const cagrSpan = Math.max(...xs.map(x=>x.cagr))-Math.min(...xs.map(x=>x.cagr));
  const ddSpan = Math.max(...xs.map(x=>x.maxDrawdown))-Math.min(...xs.map(x=>x.maxDrawdown));
  const isolatedCagrPeak = peers.length === 2 && production.cagr > Math.max(...peers.map(x=>x.cagr)) && production.cagr - Math.max(...peers.map(x=>x.cagr)) > 0.10;
  return { group, productionValue: prodValue, rows: xs, cagrSpan, maxDrawdownSpan: ddSpan, isolatedCagrPeak };
}

async function main() {
  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as MarketFile;
  const universe = JSON.parse(await readFile(resolve("data/universe-history.json"), "utf8")) as UniverseFile;

  const production: Scenario = { group: "production", label: "production", value: NaN, config: cloneConfig() };
  production.config.strategyId = `${PRODUCTION_STRATEGY.strategyId}-audit-production`;

  const scenarios: Scenario[] = [
    production,
    scenario("stop", "stop15", 0.15, c => { c.risk.individualStop = 0.15; }),
    scenario("stop", "stop17_5", 0.175, c => { c.risk.individualStop = 0.175; }),
    scenario("stop", "stop20", 0.20, c => { c.risk.individualStop = 0.20; }),
    scenario("circuit", "circuit12_5", 0.125, c => { c.risk.portfolioCircuit = 0.125; }),
    scenario("circuit", "circuit15", 0.15, c => { c.risk.portfolioCircuit = 0.15; }),
    scenario("circuit", "circuit17_5", 0.175, c => { c.risk.portfolioCircuit = 0.175; }),
    scenario("recovery", "recovery5", 5, c => { c.recovery.confirmationDays = 5; }),
    scenario("recovery", "recovery10", 10, c => { c.recovery.confirmationDays = 10; }),
    scenario("recovery", "recovery15", 15, c => { c.recovery.confirmationDays = 15; }),
  ];

  const rows = scenarios.map(s => metrics(s, runBacktest({ histories: market.histories, universeHistory: universe.history, config: s.config })));
  const prod = rows.find(r=>r.label==="production")!;
  // Substitute production row into each local neighborhood at its actual parameter value.
  const normalized = rows.filter(r=>r.label!=="production");
  const stopRows = [
    ...normalized.filter(r=>r.group==="stop" && r.value!==0.175),
    { ...prod, group: "stop" as const, label: "production-stop17_5", value: 0.175 },
  ];
  const circuitRows = [
    ...normalized.filter(r=>r.group==="circuit" && r.value!==0.15),
    { ...prod, group: "circuit" as const, label: "production-circuit15", value: 0.15 },
  ];
  const recoveryRows = [
    ...normalized.filter(r=>r.group==="recovery" && r.value!==10),
    { ...prod, group: "recovery" as const, label: "production-recovery10", value: 10 },
  ];

  const shape = {
    stop: localShape(stopRows, "stop", 0.175),
    circuit: localShape(circuitRows, "circuit", 0.15),
    recovery: localShape(recoveryRows, "recovery", 10),
  };
  const out = {
    generatedAt: new Date().toISOString(),
    strategyId: PRODUCTION_STRATEGY.strategyId,
    design: {
      type: "pre-specified one-factor-at-a-time coarse neighborhood audit",
      stop: [0.15,0.175,0.20],
      circuit: [0.125,0.15,0.175],
      recoveryDays: [5,10,15],
      rule: "diagnostic only; do not choose a new value from the best historical CAGR",
    },
    production: prod,
    neighborhoods: { stop: stopRows.sort((a,b)=>a.value-b.value), circuit: circuitRows.sort((a,b)=>a.value-b.value), recovery: recoveryRows.sort((a,b)=>a.value-b.value) },
    shape,
  };
  await mkdir(resolve("data/research/risk-parameter-neighborhood"), { recursive: true });
  await writeFile(resolve("data/research/risk-parameter-neighborhood/audit.json"), JSON.stringify(out, null, 2));
  console.log("RISK_NEIGHBORHOOD_JSON=" + JSON.stringify(out));
}

main().catch(err=>{ console.error(err); process.exit(1); });
