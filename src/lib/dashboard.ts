import { runStrategySimulation } from "./backtest";
import { PRODUCTION_STRATEGY } from "./config";
import { emptyForwardOos } from "./oos";
import { EXPECTED_CAGR_MODEL } from "./expected-cagr";
import { applyExtraordinaryRebalance } from "./nport-operations";
import { buildMonthlySignal } from "./strategy/momentum";
import { nextUsTradingSession } from "./trading-calendar";
import type { BacktestResult, DashboardPayload, ForwardOosResult, LatestPrice, NportOperations, PricePoint, UniverseMonth } from "./types";

const mean = (values: number[]) => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;

export function buildDashboardPayload(histories: Record<string, PricePoint[]>, universeHistory: UniverseMonth[], source: "live" | "snapshot" = "live", persisted?: { oos?: ForwardOosResult; frozenBacktest?: BacktestResult; nportOperations?: NportOperations; latestPrices?: Record<string, LatestPrice> }): DashboardPayload {
  const { backtest, state } = runStrategySimulation({ histories, universeHistory });
  const currentUniverse = universeHistory.at(-1) ?? null;
  const qqq = histories.QQQ ?? [];
  const signalIndex = currentUniverse ? qqq.findIndex((point) => point.date === currentUniverse.asOf) : -1;
  const currentSignal = currentUniverse ? buildMonthlySignal({ universe: currentUniverse, histories, qqq, nextSessionDate: signalIndex >= 0 ? qqq[signalIndex + 1]?.date ?? nextUsTradingSession(currentUniverse.asOf) : null }) : null;
  const close = qqq.at(-1)?.close ?? null;
  const sma = qqq.length >= PRODUCTION_STRATEGY.recovery.qqqDailySmaDays ? mean(qqq.slice(-PRODUCTION_STRATEGY.recovery.qqqDailySmaDays).map((point) => point.close)) : null;
  const prior = qqq.at(-(PRODUCTION_STRATEGY.recovery.qqqMomentumDays + 1))?.close;
  const dashboard: DashboardPayload = { generatedAt: new Date().toISOString(), source, ...(persisted?.latestPrices ? { latestPrices: persisted.latestPrices } : {}), config: PRODUCTION_STRATEGY, currentUniverse, currentSignal, liveState: state, qqq: { close, monthlyMa: currentSignal?.qqqMonthlyMa ?? null, dailySma: sma, momentum20d: close && prior ? close / prior - 1 : null }, oos: persisted?.oos ?? emptyForwardOos(PRODUCTION_STRATEGY.strategyId), backtest: persisted?.frozenBacktest ?? backtest, expectedCagr: EXPECTED_CAGR_MODEL, nportOperations: persisted?.nportOperations };
  return persisted?.nportOperations ? applyExtraordinaryRebalance(dashboard, persisted.nportOperations) : dashboard;
}
