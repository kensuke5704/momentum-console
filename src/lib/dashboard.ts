import { runStrategySimulation } from "./backtest";
import { PRODUCTION_STRATEGY } from "./config";
import { buildExpectedCagrModel } from "./expected-cagr";
import { emptyForwardOos, OOS_START_DATE } from "./oos";
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
  const currentSignal = currentUniverse ? buildMonthlySignal({ universe: currentUniverse, histories, qqq, nextSessionDate: signalIndex >= 0 ? qqq[signalIndex + 1]?.date ?? nextUsTradingSession(currentUniverse.asOf) : null, config: PRODUCTION_STRATEGY }) : null;
  const close = qqq.at(-1)?.close ?? null;
  const sma = qqq.length >= PRODUCTION_STRATEGY.recovery.qqqDailySmaDays ? mean(qqq.slice(-PRODUCTION_STRATEGY.recovery.qqqDailySmaDays).map((point) => point.close)) : null;
  const prior = qqq.at(-(PRODUCTION_STRATEGY.recovery.qqqMomentumDays + 1))?.close;

  // Never let a frozen backtest or Forward OOS series from a prior strategy
  // survive a production strategy-id change.
  const displayedBacktest = persisted?.frozenBacktest?.strategyId === PRODUCTION_STRATEGY.strategyId ? persisted.frozenBacktest : backtest;
  const displayedOos = persisted?.oos?.strategyId === PRODUCTION_STRATEGY.strategyId && persisted.oos.startedAt === OOS_START_DATE
    ? persisted.oos
    : emptyForwardOos(PRODUCTION_STRATEGY.strategyId);
  const expectedCagr = buildExpectedCagrModel(displayedBacktest.equityCurve, PRODUCTION_STRATEGY.strategyId);

  const dashboard: DashboardPayload = {
    generatedAt: new Date().toISOString(),
    source,
    ...(persisted?.latestPrices ? { latestPrices: persisted.latestPrices } : {}),
    config: PRODUCTION_STRATEGY,
    currentUniverse,
    currentSignal,
    liveState: state,
    qqq: { close, monthlyMa: currentSignal?.qqqMonthlyMa ?? null, dailySma: sma, momentum20d: close && prior ? close / prior - 1 : null },
    oos: displayedOos,
    backtest: displayedBacktest,
    ...(expectedCagr ? { expectedCagr } : {}),
    nportOperations: persisted?.nportOperations,
  };
  return persisted?.nportOperations ? applyExtraordinaryRebalance(dashboard, persisted.nportOperations) : dashboard;
}
