import { PRODUCTION_STRATEGY } from "../config";
import type { LiveStrategyState, MonthlySignal, PositionState, PricePoint, StrategyConfig } from "../types";

export type TradingDayInput = {
  date: string;
  prices: Record<string, PricePoint | undefined>;
  qqqHistoryThroughClose: PricePoint[];
  monthlySignal?: MonthlySignal | null;
  nextSessionDate: string | null;
};

export type TransitionEvent = { date: string; type: string; symbols: string[]; reason: string };
export type EngineState = LiveStrategyState & { marketRiskOn: boolean; events: TransitionEvent[] };

const emptyAction = (): LiveStrategyState["nextAction"] => ({ type: "CASH", executionDate: null, symbols: [], targetWeights: [], reason: "No pending order" });

export function initialEngineState(config: StrategyConfig = PRODUCTION_STRATEGY): EngineState {
  return { strategyId: config.strategyId, asOf: "", state: "CASH", cash: 1, currentPositions: [], portfolioPeak: 1, currentEquity: 1, drawdown: 0, recoveryConsecutiveDays: 0, lastTrigger: null, pendingSignal: null, nextAction: emptyAction(), marketRiskOn: false, events: [] };
}

function equity(state: EngineState, prices: Record<string, PricePoint | undefined>, field: "open" | "close"): number {
  return state.cash + state.currentPositions.reduce((sum, position) => sum + position.shares * (prices[position.symbol]?.[field] ?? prices[position.symbol]?.close ?? position.currentPrice ?? position.entryPrice), 0);
}

function sellAllAtOpen(state: EngineState, input: TradingDayInput, config: StrategyConfig): void {
  const gross = state.currentPositions.reduce((sum, position) => sum + position.shares * (input.prices[position.symbol]?.open ?? input.prices[position.symbol]?.close ?? position.currentPrice ?? position.entryPrice), 0);
  state.cash += gross * (1 - config.execution.transactionCost);
  const reason = state.nextAction.reason;
  state.events.push({ date: input.date, type: "EXIT_OPEN", symbols: state.currentPositions.map((position) => position.symbol), reason });
  state.currentPositions = [];
  state.currentEquity = state.cash;
  state.nextAction = emptyAction();
}

function buyAtOpen(state: EngineState, input: TradingDayInput, config: StrategyConfig, resetPeak: boolean): boolean {
  const signal = state.pendingSignal;
  if (!signal || signal.selectedSymbols.length !== 2 || signal.targetWeights.length !== 2) return false;
  const opens = signal.selectedSymbols.map((symbol) => input.prices[symbol]?.open);
  if (opens.some((price) => !price || price <= 0)) return false;
  const grossEquity = state.cash;
  const positions: PositionState[] = signal.selectedSymbols.map((symbol, index) => {
    const open = opens[index] as number;
    const grossAllocation = grossEquity * signal.targetWeights[index];
    const invested = grossAllocation * (1 - config.execution.transactionCost);
    return { symbol, shares: invested / open, entryPrice: open, targetWeight: signal.targetWeights[index], currentPrice: open, stopLevel: open * (1 - config.risk.individualStop) };
  });
  state.cash = 0;
  state.currentPositions = positions;
  state.state = "INVESTED";
  state.currentEquity = equity(state, input.prices, "open");
  state.portfolioPeak = resetPeak ? state.currentEquity : Math.max(state.portfolioPeak, state.currentEquity);
  state.drawdown = 0;
  state.recoveryConsecutiveDays = 0;
  state.events.push({ date: input.date, type: "ENTRY_OPEN", symbols: positions.map((position) => position.symbol), reason: state.nextAction.reason });
  state.nextAction = { type: "HOLD", executionDate: null, symbols: positions.map((position) => position.symbol), targetWeights: positions.map((position) => position.targetWeight), reason: "Portfolio invested" };
  return true;
}

function dailyRecoveryOk(qqq: PricePoint[], config: StrategyConfig): boolean {
  const smaDays = config.recovery.qqqDailySmaDays;
  const momentumDays = config.recovery.qqqMomentumDays;
  if (qqq.length < Math.max(smaDays, momentumDays + 1)) return false;
  const latest = qqq.at(-1)?.close;
  const prior = qqq.at(-(momentumDays + 1))?.close;
  if (!latest || !prior) return false;
  const sma = qqq.slice(-smaDays).reduce((sum, point) => sum + point.close, 0) / smaDays;
  return latest > sma && latest / prior - 1 > 0;
}

function scheduleExit(state: EngineState, input: TradingDayInput, lockedState: EngineState["state"], reason: string): void {
  state.state = lockedState;
  state.lastTrigger = `${input.date}: ${reason}`;
  state.recoveryConsecutiveDays = 0;
  state.nextAction = { type: "SELL_ALL_NEXT_OPEN", executionDate: input.nextSessionDate, symbols: state.currentPositions.map((position) => position.symbol), targetWeights: [], reason };
}

export function transitionDay(previous: EngineState, input: TradingDayInput, config: StrategyConfig = PRODUCTION_STRATEGY): EngineState {
  const state: EngineState = structuredClone(previous);
  state.asOf = input.date;

  if (state.nextAction.type === "SELL_ALL_NEXT_OPEN" && state.nextAction.executionDate === input.date) sellAllAtOpen(state, input, config);
  if ((state.nextAction.type === "BUY_NEXT_OPEN" || state.nextAction.type === "MONTH_END_REBALANCE_NEXT_OPEN") && state.nextAction.executionDate === input.date) {
    const resetPeak = state.nextAction.type === "BUY_NEXT_OPEN";
    if (state.currentPositions.length) sellAllAtOpen(state, input, config);
    buyAtOpen(state, input, config, resetPeak);
  }

  for (const position of state.currentPositions) position.currentPrice = input.prices[position.symbol]?.close ?? position.currentPrice;
  state.currentEquity = equity(state, input.prices, "close");
  state.portfolioPeak = Math.max(state.portfolioPeak, state.currentEquity);
  state.drawdown = state.portfolioPeak > 0 ? state.currentEquity / state.portfolioPeak - 1 : 0;

  if (input.monthlySignal) {
    state.pendingSignal = input.monthlySignal;
    state.marketRiskOn = input.monthlySignal.marketRiskOn;
    if (!state.marketRiskOn) {
      if (state.currentPositions.length) scheduleExit(state, input, "LOCKED_MARKET", "QQQ monthly 10M MA gate is RiskOff");
      else { state.state = "LOCKED_MARKET"; state.lastTrigger = `${input.date}: QQQ monthly 10M MA gate is RiskOff`; state.recoveryConsecutiveDays = 0; }
    } else if (state.state === "CASH" && input.monthlySignal.selectedSymbols.length === 2) {
      state.nextAction = { type: "BUY_NEXT_OPEN", executionDate: input.nextSessionDate, symbols: input.monthlySignal.selectedSymbols, targetWeights: input.monthlySignal.targetWeights, reason: "Monthly Top2 signal confirmed at close" };
      state.state = "READY_NEXT_OPEN";
    } else if (state.state === "INVESTED" && input.monthlySignal.selectedSymbols.length === 2) {
      state.nextAction = { type: "MONTH_END_REBALANCE_NEXT_OPEN", executionDate: input.nextSessionDate, symbols: input.monthlySignal.selectedSymbols, targetWeights: input.monthlySignal.targetWeights, reason: "Month-end signal confirmed at close" };
    } else if (state.state === "INVESTED" && input.monthlySignal.selectedSymbols.length < 2) {
      state.nextAction = { type: "SELL_ALL_NEXT_OPEN", executionDate: input.nextSessionDate, symbols: state.currentPositions.map((position) => position.symbol), targetWeights: [], reason: "Fewer than two eligible monthly candidates" };
      state.state = "CASH";
    }
  }

  if (state.state === "INVESTED" && state.nextAction.type !== "SELL_ALL_NEXT_OPEN") {
    const stop = state.currentPositions.find((position) => (position.currentPrice ?? Infinity) <= position.stopLevel);
    if (stop) scheduleExit(state, input, "LOCKED_STOP", `${stop.symbol} close breached -${config.risk.individualStop * 100}% stop`);
    else if (state.drawdown <= -config.risk.portfolioCircuit) scheduleExit(state, input, "LOCKED_CIRCUIT", `Portfolio close breached -${config.risk.portfolioCircuit * 100}% circuit`);
  }

  const locked = state.state === "LOCKED_MARKET" || state.state === "LOCKED_STOP" || state.state === "LOCKED_CIRCUIT" || state.state === "WAITING_RECOVERY";
  if (locked && state.nextAction.type !== "SELL_ALL_NEXT_OPEN") {
    state.state = "WAITING_RECOVERY";
    state.recoveryConsecutiveDays = state.marketRiskOn && dailyRecoveryOk(input.qqqHistoryThroughClose, config) ? state.recoveryConsecutiveDays + 1 : 0;
    if (state.recoveryConsecutiveDays >= config.recovery.confirmationDays && state.pendingSignal?.selectedSymbols.length === 2) {
      state.state = "READY_NEXT_OPEN";
      state.nextAction = { type: "BUY_NEXT_OPEN", executionDate: input.nextSessionDate, symbols: state.pendingSignal.selectedSymbols, targetWeights: state.pendingSignal.targetWeights, reason: `${config.recovery.confirmationDays} recovery closes confirmed` };
    } else state.nextAction = { type: "CASH_RECOVERY", executionDate: null, symbols: [], targetWeights: [], reason: `Recovery ${state.recoveryConsecutiveDays}/${config.recovery.confirmationDays}` };
  }
  return state;
}
