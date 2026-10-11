import { PRODUCTION_PORTFOLIO } from "./portfolio-config";
import type { BacktestResult } from "./types";

export function validateImportedOosIdentity(portfolioStrategyId: string, oosStrategyId: string): void {
  if (portfolioStrategyId !== PRODUCTION_PORTFOLIO.strategyId || oosStrategyId !== portfolioStrategyId) {
    throw new Error("OOS and Dashboard portfolio strategy IDs are inconsistent");
  }
}

export function validateImportedExecutionHistory(previous: BacktestResult, candidate: BacktestResult, beforeDate: string): void {
  const keys = (backtest: BacktestResult) => backtest.events
    .filter((event) => event.type === "PORTFOLIO_REBALANCE_OPEN" && event.date >= PRODUCTION_PORTFOLIO.oosStartDate && event.date < beforeDate)
    .map((event) => JSON.stringify([event.date, [...event.symbols].sort(), event.targets?.map(({ symbol, weight }) => [symbol, weight.toFixed(8)]).sort()]))
    .sort();
  if (JSON.stringify(keys(previous)) !== JSON.stringify(keys(candidate))) {
    throw new Error("Delayed N-PORT import would rewrite already-executed OOS allocations before the new execution date");
  }
}
