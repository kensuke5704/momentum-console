import { PRODUCTION_STRATEGY } from "./config";
import { buildMonthlySignal } from "./strategy/momentum";
import { initialEngineState, transitionDay, type EngineState } from "./strategy/state-machine";
import { nextUsTradingSession } from "./trading-calendar";
import type { BacktestResult, EquityPoint, PerformanceStats, PricePoint, StrategyConfig, UniverseMonth } from "./types";

const mean = (values: number[]) => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
const stdev = (values: number[]) => {
  if (values.length < 2) return 0;
  const avg = mean(values);
  return Math.sqrt(values.reduce((sum, value) => sum + (value - avg) ** 2, 0) / (values.length - 1));
};

export function performanceStats(curve: EquityPoint[]): PerformanceStats {
  if (curve.length < 2) return { cagr: 0, maxDrawdown: 0, annualizedVolatility: 0, calmar: null, finalEquity: curve.at(-1)?.equity ?? 1 };
  const first = curve[0], last = curve.at(-1)!;
  const years = Math.max(1 / 365.25, (Date.parse(last.date) - Date.parse(first.date)) / (365.25 * 86_400_000));
  const returns = curve.slice(1).map((point, index) => point.equity / curve[index].equity - 1);
  const cagr = (last.equity / first.equity) ** (1 / years) - 1;
  let peak = curve[0].equity;
  let maxDrawdown = 0;
  for (const point of curve) {
    peak = Math.max(peak, point.equity);
    maxDrawdown = Math.min(maxDrawdown, point.equity / peak - 1);
  }
  return { cagr, maxDrawdown, annualizedVolatility: stdev(returns) * Math.sqrt(252), calmar: maxDrawdown < 0 ? cagr / Math.abs(maxDrawdown) : null, finalEquity: last.equity };
}

function benchmarkCurve(points: PricePoint[], start: string, transactionCost: number): EquityPoint[] {
  const rows = points.filter((point) => point.date >= start);
  if (!rows.length) return [];
  const shares = (1 - transactionCost) / rows[0].open;
  let peak = 1 - transactionCost;
  return rows.map((point) => {
    const equity = shares * point.close;
    peak = Math.max(peak, equity);
    return { date: point.date, equity, drawdown: equity / peak - 1 };
  });
}

export function runBacktest(args: {
  histories: Record<string, PricePoint[]>;
  universeHistory: UniverseMonth[];
  config?: StrategyConfig;
}): BacktestResult {
  return runStrategySimulation(args).backtest;
}

export function runStrategySimulation(args: {
  histories: Record<string, PricePoint[]>;
  universeHistory: UniverseMonth[];
  config?: StrategyConfig;
}): { backtest: BacktestResult; state: EngineState } {
  const config = args.config ?? PRODUCTION_STRATEGY;
  const qqq = [...(args.histories.QQQ ?? [])].sort((a, b) => a.date.localeCompare(b.date));
  const tradingDates = qqq.map((point) => point.date);
  const dateIndex = new Map(tradingDates.map((date, index) => [date, index]));
  const priceMaps = Object.fromEntries(Object.entries(args.histories).map(([symbol, points]) => [symbol, new Map(points.map((point) => [point.date, point]))]));
  const universeBySignalDate = new Map(args.universeHistory.map((month) => [month.asOf, month]));
  let state: EngineState = initialEngineState(config);
  const curve: EquityPoint[] = [];

  for (let index = 0; index < tradingDates.length; index++) {
    const date = tradingDates[index];
    if (date < config.backtestStart) continue;
    const nextSessionDate = tradingDates[index + 1] ?? nextUsTradingSession(date);
    const universe = universeBySignalDate.get(date);
    const signal = universe ? buildMonthlySignal({ universe, histories: args.histories, qqq, nextSessionDate, config }) : null;
    const symbols = new Set([
      "QQQ",
      ...state.currentPositions.map((position) => position.symbol),
      ...(state.pendingSignal?.selectedSymbols ?? []),
      ...state.nextAction.symbols,
      ...(signal?.selectedSymbols ?? []),
    ]);
    const prices = Object.fromEntries([...symbols].map((symbol) => [symbol, priceMaps[symbol]?.get(date)]));
    state = transitionDay(state, { date, prices, qqqHistoryThroughClose: qqq.slice(0, (dateIndex.get(date) ?? index) + 1), monthlySignal: signal, nextSessionDate }, config);
    curve.push({ date, equity: state.currentEquity, drawdown: state.drawdown });
  }

  const tqqq = args.histories.TQQQ ?? [];
  const benchmark = tqqq.length ? (() => {
    const equityCurve = benchmarkCurve(tqqq, config.backtestStart, config.execution.transactionCost);
    return { label: "TQQQ Buy & Hold" as const, equityCurve, stats: performanceStats(equityCurve) };
  })() : null;
  return { backtest: { strategyId: config.strategyId, equityCurve: curve, stats: performanceStats(curve), benchmark, events: state.events }, state };
}
