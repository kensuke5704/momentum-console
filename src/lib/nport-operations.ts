import { PRODUCTION_STRATEGY } from "./config";
import { PRODUCTION_PORTFOLIO } from "./portfolio-config";
import { buildMonthlySignal } from "./strategy/momentum";
import { nextUsTradingSession } from "./trading-calendar";
import type { PortfolioLiveState, PortfolioTarget } from "./portfolio-types";
import type { LiveStrategyState, MonthlySignal, NportOperations, PricePoint, UniverseMonth } from "./types";

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
    month = quarter * 3 + 4;
    if (month > 12) { year += 1; month -= 12; }
  } else {
    year = now.getUTCFullYear();
    month = Math.floor(now.getUTCMonth() / 3) * 3 + 4;
    if (month > 12) { year += 1; month -= 12; }
  }
  const firstOfMonth = `${year}-${String(month).padStart(2, "0")}-01`;
  const previousDay = new Date(`${firstOfMonth}T00:00:00Z`);
  previousDay.setUTCDate(previousDay.getUTCDate() - 1);
  const firstTradingDay = nextUsTradingSession(previousDay.toISOString().slice(0, 10));
  return `${firstTradingDay}T09:00:00+09:00`;
}

const sameWeights = (left: number[], right: number[]) => left.length === right.length && left.every((value, index) => Math.abs(value - right[index]) < 1e-12);

export function buildDelayedNportRebalance(args: {
  previousSignal: MonthlySignal;
  newUniverse: UniverseMonth;
  histories: Record<string, PricePoint[]>;
  qqq: PricePoint[];
  receivedAt: string;
}): NonNullable<NportOperations["extraordinaryRebalance"]> {
  if (args.newUniverse.signalMonth !== args.previousSignal.signalMonth || args.newUniverse.asOf !== args.previousSignal.signalDate) throw new Error("Delayed N-PORT activation must retain the previous official month-end signal date");
  const executionDate = nextUsTradingSession(args.receivedAt.slice(0, 10));
  const signal = buildMonthlySignal({ universe: args.newUniverse, histories: args.histories, qqq: args.qqq, nextSessionDate: executionDate });
  if (signal.signalDate !== args.previousSignal.signalDate) throw new Error("Interim prices were used for delayed N-PORT selection");
  const changed = signal.selectedSymbols.join("|") !== args.previousSignal.selectedSymbols.join("|") || !sameWeights(signal.targetWeights, args.previousSignal.targetWeights);
  return { evaluatedAt: args.receivedAt, priceAsOf: args.previousSignal.signalDate, changed, executionDate: changed ? executionDate : null, previousSymbols: args.previousSignal.selectedSymbols, previousWeights: args.previousSignal.targetWeights, nextSymbols: signal.selectedSymbols, nextWeights: signal.targetWeights, signal };
}

export function defaultNportOperations(activeQuarter: string | null, now = new Date()): NportOperations {
  return { activeQuarter, lastImportedAt: null, nextImportDeadlineAt: nextNportImportDeadline(activeQuarter, now), universeMode: "CURRENT", fallbackReason: null, extraordinaryRebalance: null };
}

function stage21Targets(portfolio: PortfolioLiveState, symbols:string[], innerWeights:number[]): PortfolioTarget[] {
  const outer = PRODUCTION_PORTFOLIO.weights[portfolio.regime], targets:PortfolioTarget[]=[];
  symbols.forEach((symbol,index)=>{const weight=outer.fixed60*(innerWeights[index]??0);if(weight>0)targets.push({symbol,weight,role:"FIXED60"})});
  targets.push({symbol:"GLDM",weight:outer.gldm,role:"DIVERSIFIER"});
  const innerTotal=innerWeights.reduce((sum,value)=>sum+value,0),cash=outer.cash+outer.fixed60*Math.max(0,1-innerTotal);if(cash>1e-9)targets.push({symbol:"CASH",weight:cash,role:"CASH"});
  return targets;
}

export function applyExtraordinaryRebalance<T extends { liveState: LiveStrategyState; portfolioState?: PortfolioLiveState }>(dashboard: T, operations: NportOperations): T {
  const rebalance = operations.extraordinaryRebalance;
  if (!rebalance?.changed || !rebalance.signal.marketRiskOn || rebalance.signal.selectedSymbols.length !== PRODUCTION_STRATEGY.selection.topN) return dashboard;
  const liveState = structuredClone(dashboard.liveState);
  liveState.pendingSignal = rebalance.signal;
  if (liveState.state === "INVESTED" || liveState.state === "READY_NEXT_OPEN" || liveState.state === "CASH") {
    const hasPositions = liveState.currentPositions.length > 0;
    liveState.nextAction = { type: hasPositions ? "MONTH_END_REBALANCE_NEXT_OPEN" : "BUY_NEXT_OPEN", executionDate: rebalance.executionDate, symbols: rebalance.nextSymbols, targetWeights: rebalance.nextWeights, reason: `Delayed N-PORT Universe activated; Momentum remains fixed at ${rebalance.priceAsOf} close` };
  }
  if (!dashboard.portfolioState) return { ...dashboard, liveState };
  const portfolioState=structuredClone(dashboard.portfolioState),targets=stage21Targets(portfolioState,rebalance.nextSymbols,rebalance.nextWeights);
  portfolioState.fixed60.symbols=[...rebalance.nextSymbols];portfolioState.fixed60.innerWeights=[...rebalance.nextWeights];portfolioState.targets=targets;
  portfolioState.nextAction={type:"REBALANCE_NEXT_OPEN",executionDate:rebalance.executionDate,targets,reason:`Delayed N-PORT Universe activated; Stage21 funded target updated from ${rebalance.priceAsOf} close`};
  return { ...dashboard, liveState, portfolioState };
}
