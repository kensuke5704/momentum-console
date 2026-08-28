import { readFile, mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { PRODUCTION_STRATEGY } from "../src/lib/config";
import { performanceStats } from "../src/lib/backtest";
import { buildMonthlySignal } from "../src/lib/strategy/momentum";
import { initialEngineState, type EngineState } from "../src/lib/strategy/state-machine";
import type { EquityPoint, LiveStrategyState, MonthlySignal, PositionState, PricePoint, StrategyConfig, UniverseMonth } from "../src/lib/types";

type MarketDataFile = { histories?: Record<string, PricePoint[]> };
type UniverseFile = { history: UniverseMonth[] };
type DelayMode = { entryRebalanceExtra: number; riskExitExtra: number };
type DayInput = { date: string; prices: Record<string, PricePoint | undefined>; qqqHistoryThroughClose: PricePoint[]; monthlySignal?: MonthlySignal | null; normalNext: string | null; entryNext: string | null; exitNext: string | null };

const END = "2026-08-25";
const emptyAction = (): LiveStrategyState["nextAction"] => ({ type: "CASH", executionDate: null, symbols: [], targetWeights: [], reason: "No pending order" });

function equity(state: EngineState, prices: Record<string, PricePoint | undefined>, field: "open" | "close") {
  return state.cash + state.currentPositions.reduce((sum, p) => sum + p.shares * (prices[p.symbol]?.[field] ?? prices[p.symbol]?.close ?? p.currentPrice ?? p.entryPrice), 0);
}
function sellAllAtOpen(state: EngineState, input: DayInput, config: StrategyConfig) {
  const gross = state.currentPositions.reduce((sum, p) => sum + p.shares * (input.prices[p.symbol]?.open ?? input.prices[p.symbol]?.close ?? p.currentPrice ?? p.entryPrice), 0);
  state.cash += gross * (1 - config.execution.transactionCost);
  state.events.push({ date: input.date, type: "EXIT_OPEN", symbols: state.currentPositions.map((p) => p.symbol), reason: state.nextAction.reason });
  state.currentPositions = []; state.currentEquity = state.cash; state.nextAction = emptyAction();
}
function buyAtOpen(state: EngineState, input: DayInput, config: StrategyConfig, resetPeak: boolean) {
  const signal = state.pendingSignal;
  if (!signal || signal.selectedSymbols.length !== 2 || signal.targetWeights.length !== 2) return false;
  const opens = signal.selectedSymbols.map((s) => input.prices[s]?.open);
  if (opens.some((p) => !p || p <= 0)) return false;
  const grossEquity = state.cash;
  const positions: PositionState[] = signal.selectedSymbols.map((symbol, i) => {
    const open = opens[i] as number;
    const invested = grossEquity * signal.targetWeights[i] * (1 - config.execution.transactionCost);
    return { symbol, shares: invested / open, entryPrice: open, targetWeight: signal.targetWeights[i], currentPrice: open, stopLevel: open * (1 - config.risk.individualStop) };
  });
  state.cash = 0; state.currentPositions = positions; state.state = "INVESTED"; state.currentEquity = equity(state, input.prices, "open");
  state.portfolioPeak = resetPeak ? state.currentEquity : Math.max(state.portfolioPeak, state.currentEquity); state.drawdown = 0; state.recoveryConsecutiveDays = 0;
  state.events.push({ date: input.date, type: "ENTRY_OPEN", symbols: positions.map((p) => p.symbol), reason: state.nextAction.reason });
  state.nextAction = { type: "HOLD", executionDate: null, symbols: positions.map((p) => p.symbol), targetWeights: positions.map((p) => p.targetWeight), reason: "Portfolio invested" };
  return true;
}
function dailyRecoveryOk(qqq: PricePoint[], config: StrategyConfig) {
  const smaDays = config.recovery.qqqDailySmaDays, momentumDays = config.recovery.qqqMomentumDays;
  if (qqq.length < Math.max(smaDays, momentumDays + 1)) return false;
  const latest = qqq.at(-1)?.close, prior = qqq.at(-(momentumDays + 1))?.close;
  if (!latest || !prior) return false;
  const sma = qqq.slice(-smaDays).reduce((s, p) => s + p.close, 0) / smaDays;
  return latest > sma && latest / prior - 1 > 0;
}
function scheduleExit(state: EngineState, input: DayInput, lockedState: EngineState["state"], reason: string) {
  state.state = lockedState; state.lastTrigger = `${input.date}: ${reason}`; state.recoveryConsecutiveDays = 0;
  state.nextAction = { type: "SELL_ALL_NEXT_OPEN", executionDate: input.exitNext, symbols: state.currentPositions.map((p) => p.symbol), targetWeights: [], reason };
}
function transitionSelective(previous: EngineState, input: DayInput, config: StrategyConfig): EngineState {
  const state: EngineState = structuredClone(previous); state.asOf = input.date;
  if (state.nextAction.type === "SELL_ALL_NEXT_OPEN" && state.nextAction.executionDate === input.date) sellAllAtOpen(state, input, config);
  if ((state.nextAction.type === "BUY_NEXT_OPEN" || state.nextAction.type === "MONTH_END_REBALANCE_NEXT_OPEN") && state.nextAction.executionDate === input.date) {
    const resetPeak = state.nextAction.type === "BUY_NEXT_OPEN";
    if (state.currentPositions.length) sellAllAtOpen(state, input, config);
    buyAtOpen(state, input, config, resetPeak);
  }
  for (const p of state.currentPositions) p.currentPrice = input.prices[p.symbol]?.close ?? p.currentPrice;
  state.currentEquity = equity(state, input.prices, "close"); state.portfolioPeak = Math.max(state.portfolioPeak, state.currentEquity); state.drawdown = state.portfolioPeak > 0 ? state.currentEquity / state.portfolioPeak - 1 : 0;

  if (input.monthlySignal) {
    state.pendingSignal = input.monthlySignal; state.marketRiskOn = input.monthlySignal.marketRiskOn;
    if (!state.marketRiskOn) {
      if (state.currentPositions.length) scheduleExit(state, input, "LOCKED_MARKET", "QQQ monthly 10M MA gate is RiskOff");
      else { state.state = "LOCKED_MARKET"; state.lastTrigger = `${input.date}: QQQ monthly 10M MA gate is RiskOff`; state.recoveryConsecutiveDays = 0; }
    } else if (state.state === "CASH" && input.monthlySignal.selectedSymbols.length === 2) {
      state.nextAction = { type: "BUY_NEXT_OPEN", executionDate: input.entryNext, symbols: input.monthlySignal.selectedSymbols, targetWeights: input.monthlySignal.targetWeights, reason: "Monthly Top2 signal confirmed at close" }; state.state = "READY_NEXT_OPEN";
    } else if (state.state === "INVESTED" && input.monthlySignal.selectedSymbols.length === 2) {
      state.nextAction = { type: "MONTH_END_REBALANCE_NEXT_OPEN", executionDate: input.entryNext, symbols: input.monthlySignal.selectedSymbols, targetWeights: input.monthlySignal.targetWeights, reason: "Month-end signal confirmed at close" };
    } else if (state.state === "INVESTED" && input.monthlySignal.selectedSymbols.length < 2) {
      state.nextAction = { type: "SELL_ALL_NEXT_OPEN", executionDate: input.exitNext, symbols: state.currentPositions.map((p) => p.symbol), targetWeights: [], reason: "Fewer than two eligible monthly candidates" }; state.state = "CASH";
    }
  }
  if (state.state === "INVESTED" && state.nextAction.type !== "SELL_ALL_NEXT_OPEN") {
    const stop = state.currentPositions.find((p) => (p.currentPrice ?? Infinity) <= p.stopLevel);
    if (stop) scheduleExit(state, input, "LOCKED_STOP", `${stop.symbol} close breached -${config.risk.individualStop * 100}% stop`);
    else if (state.drawdown <= -config.risk.portfolioCircuit) scheduleExit(state, input, "LOCKED_CIRCUIT", `Portfolio close breached -${config.risk.portfolioCircuit * 100}% circuit`);
  }
  const locked = state.state === "LOCKED_MARKET" || state.state === "LOCKED_STOP" || state.state === "LOCKED_CIRCUIT" || state.state === "WAITING_RECOVERY";
  if (locked && state.nextAction.type !== "SELL_ALL_NEXT_OPEN") {
    state.state = "WAITING_RECOVERY";
    state.recoveryConsecutiveDays = state.marketRiskOn && dailyRecoveryOk(input.qqqHistoryThroughClose, config) ? state.recoveryConsecutiveDays + 1 : 0;
    if (state.recoveryConsecutiveDays >= config.recovery.confirmationDays && state.pendingSignal?.selectedSymbols.length === 2) {
      state.state = "READY_NEXT_OPEN";
      state.nextAction = { type: "BUY_NEXT_OPEN", executionDate: input.entryNext, symbols: state.pendingSignal.selectedSymbols, targetWeights: state.pendingSignal.targetWeights, reason: `${config.recovery.confirmationDays} recovery closes confirmed` };
    } else state.nextAction = { type: "CASH_RECOVERY", executionDate: null, symbols: [], targetWeights: [], reason: `Recovery ${state.recoveryConsecutiveDays}/${config.recovery.confirmationDays}` };
  }
  return state;
}

function run(histories: Record<string, PricePoint[]>, universeHistory: UniverseMonth[], mode: DelayMode) {
  const config = PRODUCTION_STRATEGY;
  const qqq = [...(histories.QQQ ?? [])].filter((p) => p.date <= END).sort((a,b) => a.date.localeCompare(b.date));
  const tradingDates = qqq.map((p) => p.date), dateIndex = new Map(tradingDates.map((d,i) => [d,i]));
  const priceMaps = Object.fromEntries(Object.entries(histories).map(([s, pts]) => [s, new Map(pts.filter((p) => p.date <= END).map((p) => [p.date,p]))]));
  const universeBySignalDate = new Map(universeHistory.map((m) => [m.asOf,m]));
  let state = initialEngineState(config); const curve: EquityPoint[] = [];
  for (let i=0;i<tradingDates.length;i++) {
    const date = tradingDates[i]; if (date < config.backtestStart) continue;
    const normalNext = tradingDates[i+1] ?? null, entryNext = tradingDates[i+1+mode.entryRebalanceExtra] ?? null, exitNext = tradingDates[i+1+mode.riskExitExtra] ?? null;
    const universe = universeBySignalDate.get(date);
    const signal = universe ? buildMonthlySignal({ universe, histories, qqq, nextSessionDate: entryNext, config }) : null;
    const symbols = new Set(["QQQ", ...state.currentPositions.map((p) => p.symbol), ...(state.pendingSignal?.selectedSymbols ?? []), ...state.nextAction.symbols, ...(signal?.selectedSymbols ?? [])]);
    const prices = Object.fromEntries([...symbols].map((s) => [s, priceMaps[s]?.get(date)]));
    state = transitionSelective(state, { date, prices, qqqHistoryThroughClose: qqq.slice(0,(dateIndex.get(date) ?? i)+1), monthlySignal: signal, normalNext, entryNext, exitNext }, config);
    curve.push({ date, equity: state.currentEquity, drawdown: state.drawdown });
  }
  const stats = performanceStats(curve);
  return { stats, entries: state.events.filter((e) => e.type === "ENTRY_OPEN").length, exits: state.events.filter((e) => e.type === "EXIT_OPEN").length };
}

async function main() {
  const market = JSON.parse(await readFile(resolve("public/data/market-data.json"), "utf8")) as MarketDataFile;
  const universe = JSON.parse(await readFile(resolve("data/universe-history.json"), "utf8")) as UniverseFile;
  const histories = market.histories ?? {}; const universeHistory = universe.history.filter((m) => m.asOf >= PRODUCTION_STRATEGY.backtestStart && m.asOf <= END);
  const baseline = run(histories, universeHistory, { entryRebalanceExtra: 0, riskExitExtra: 0 });
  const entryOnly = run(histories, universeHistory, { entryRebalanceExtra: 1, riskExitExtra: 0 });
  const exitOnly = run(histories, universeHistory, { entryRebalanceExtra: 0, riskExitExtra: 1 });
  const both = run(histories, universeHistory, { entryRebalanceExtra: 1, riskExitExtra: 1 });
  const output = { generatedAt: new Date().toISOString(), period: { start: PRODUCTION_STRATEGY.backtestStart, end: END }, method: "Full state-machine decomposition of one-session execution delay. ENTRY/recovery/month-end rebalance delay and risk/RiskOff/fewer-candidate EXIT delay are perturbed separately, with causal downstream state recomputation.", baseline, entryRebalanceDelayOnly: entryOnly, riskExitDelayOnly: exitOnly, bothDelayed: both, differencesVsBaseline: { entryCagr: entryOnly.stats.cagr-baseline.stats.cagr, entryMaxDD: entryOnly.stats.maxDrawdown-baseline.stats.maxDrawdown, exitCagr: exitOnly.stats.cagr-baseline.stats.cagr, exitMaxDD: exitOnly.stats.maxDrawdown-baseline.stats.maxDrawdown, bothCagr: both.stats.cagr-baseline.stats.cagr, bothMaxDD: both.stats.maxDrawdown-baseline.stats.maxDrawdown } };
  const out = resolve("data/research/execution-delay-decomposition.json"); await mkdir(dirname(out), { recursive: true }); await writeFile(out, JSON.stringify(output,null,2)+"\n"); console.log(JSON.stringify(output,null,2));
}
main().catch((e) => { console.error(e); process.exitCode = 1; });
