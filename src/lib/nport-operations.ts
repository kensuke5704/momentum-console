import { PRODUCTION_STRATEGY } from "./config";
import { buildMonthlySignal } from "./strategy/momentum";
import { nextUsTradingSession } from "./trading-calendar";
import type { MonthlySignal, NportOperations, PricePoint, UniverseMonth } from "./types";

const quarterNumber = (quarter: string) => Number(quarter.slice(0, 4)) * 4 + Number(quarter.at(-1));

export function latestCompletedNportQuarter(signalMonth: string): string {
  const year = Number(signalMonth.slice(0, 4));
  const month = Number(signalMonth.slice(5, 7));
  const quarter = Math.floor(month / 3);
  return quarter > 0 ? `${year}q${quarter}` : `${year - 1}q4`;
}

export function requiresUniverseFallback(signalMonth: string, activeQuarter: string | null): boolean {
  return !activeQuarter || quarterNumber(activeQuarter) < quarterNumber(latestCompletedNportQuarter(signalMonth));
}

export function fallbackUniverse(previous: UniverseMonth, signalMonth: string, asOf: string): UniverseMonth {
  return { ...structuredClone(previous), signalMonth, asOf, added: [], removed: [] };
}

export function nextNportImportDeadline(activeQuarter: string | null, now = new Date()): string {
  let year: number;
  let month: number;
  if (activeQuarter) {
    year = Number(activeQuarter.slice(0, 4));
    const quarter = Number(activeQuarter.at(-1));
    month = quarter * 3 + 1;
    if (month > 12) { year += 1; month -= 12; }
  } else {
    year = now.getUTCFullYear();
    month = Math.floor(now.getUTCMonth() / 3) * 3 + 1;
  }
  // The monthly Universe selection runs at 07:00 UTC on calendar days 1-4.
  // The first run is 16:00 JST, so this is the latest accepted import time.
  return `${year}-${String(month).padStart(2, "0")}-01T16:00:00+09:00`;
}

const sameWeights = (left: number[], right: number[]) => left.length === right.length && left.every((value, index) => Math.abs(value - right[index]) < 1e-12);

export function buildDelayedNportRebalance(args: {
  previousSignal: MonthlySignal;
  newUniverse: UniverseMonth;
  histories: Record<string, PricePoint[]>;
  qqq: PricePoint[];
  receivedAt: string;
}): NonNullable<NportOperations["extraordinaryRebalance"]> {
  if (args.newUniverse.signalMonth !== args.previousSignal.signalMonth || args.newUniverse.asOf !== args.previousSignal.signalDate) {
    throw new Error("Delayed N-PORT activation must retain the previous official month-end signal date");
  }
  const executionDate = nextUsTradingSession(args.receivedAt.slice(0, 10));
  const signal = buildMonthlySignal({ universe: args.newUniverse, histories: args.histories, qqq: args.qqq, nextSessionDate: executionDate });
  if (signal.signalDate !== args.previousSignal.signalDate) throw new Error("Interim prices were used for delayed N-PORT selection");
  const changed = signal.selectedSymbols.join("|") !== args.previousSignal.selectedSymbols.join("|") || !sameWeights(signal.targetWeights, args.previousSignal.targetWeights);
  return {
    evaluatedAt: args.receivedAt,
    priceAsOf: args.previousSignal.signalDate,
    changed,
    executionDate: changed ? executionDate : null,
    previousSymbols: args.previousSignal.selectedSymbols,
    previousWeights: args.previousSignal.targetWeights,
    nextSymbols: signal.selectedSymbols,
    nextWeights: signal.targetWeights,
    signal,
  };
}

export function defaultNportOperations(activeQuarter: string | null, now = new Date()): NportOperations {
  return { activeQuarter, lastImportedAt: null, nextImportDeadlineAt: nextNportImportDeadline(activeQuarter, now), universeMode: "CURRENT", fallbackReason: null, extraordinaryRebalance: null };
}

export function applyExtraordinaryRebalance<T extends { liveState: import("./types").LiveStrategyState }>(dashboard: T, operations: NportOperations): T {
  const rebalance = operations.extraordinaryRebalance;
  if (!rebalance?.changed || !rebalance.signal.marketRiskOn || rebalance.signal.selectedSymbols.length !== PRODUCTION_STRATEGY.selection.topN) return dashboard;
  const liveState = structuredClone(dashboard.liveState);
  liveState.pendingSignal = rebalance.signal;
  if (liveState.state === "INVESTED" || liveState.state === "READY_NEXT_OPEN" || liveState.state === "CASH") {
    const hasPositions = liveState.currentPositions.length > 0;
    liveState.nextAction = {
      type: hasPositions ? "MONTH_END_REBALANCE_NEXT_OPEN" : "BUY_NEXT_OPEN",
      executionDate: rebalance.executionDate,
      symbols: rebalance.nextSymbols,
      targetWeights: rebalance.nextWeights,
      reason: `Delayed N-PORT Universe activated; Momentum remains fixed at ${rebalance.priceAsOf} close`,
    };
  }
  return { ...dashboard, liveState };
}
