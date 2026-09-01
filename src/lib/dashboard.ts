import { PRODUCTION_STRATEGY } from "./config";
import { emptyForwardOos, OOS_START_DATE } from "./oos";
import { applyExtraordinaryRebalance } from "./nport-operations";
import { PRODUCTION_PORTFOLIO } from "./portfolio-config";
import { buildStage21Portfolio } from "./portfolio/stage21";
import { buildMonthlySignal } from "./strategy/momentum";
import { nextUsTradingSession } from "./trading-calendar";
import type { CftcPositionRow } from "./cftc";
import type { BacktestResult, DashboardPayload, ForwardOosResult, LatestPrice, NportOperations, PricePoint, UniverseMonth } from "./types";

const mean = (values: number[]) => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;

export function buildDashboardPayload(histories: Record<string, PricePoint[]>, universeHistory: UniverseMonth[], cftcRows: CftcPositionRow[], source: "live" | "snapshot" = "live", persisted?: { oos?: ForwardOosResult; frozenBacktest?: BacktestResult; nportOperations?: NportOperations; latestPrices?: Record<string, LatestPrice> }): DashboardPayload {
  const stage21 = buildStage21Portfolio(histories, universeHistory, cftcRows);
  const currentUniverse = universeHistory.at(-1) ?? null;
  const qqq = histories.QQQ ?? [];
  const signalIndex = currentUniverse ? qqq.findIndex((point) => point.date === currentUniverse.asOf) : -1;
  const currentSignal = currentUniverse && signalIndex >= 0
    ? buildMonthlySignal({ universe: currentUniverse, histories, qqq, nextSessionDate: qqq[signalIndex + 1]?.date ?? nextUsTradingSession(currentUniverse.asOf), config: PRODUCTION_STRATEGY })
    : null;
  const close = qqq.at(-1)?.close ?? null;
  const sma = qqq.length >= PRODUCTION_STRATEGY.recovery.qqqDailySmaDays ? mean(qqq.slice(-PRODUCTION_STRATEGY.recovery.qqqDailySmaDays).map((point) => point.close)) : null;
  const prior = qqq.at(-(PRODUCTION_STRATEGY.recovery.qqqMomentumDays + 1))?.close;

  const displayedBacktest = persisted?.frozenBacktest?.strategyId === PRODUCTION_PORTFOLIO.strategyId ? persisted.frozenBacktest : stage21.backtest;
  const displayedOos = persisted?.oos?.strategyId === PRODUCTION_PORTFOLIO.strategyId && persisted.oos.startedAt === OOS_START_DATE
    ? persisted.oos
    : emptyForwardOos(PRODUCTION_PORTFOLIO.strategyId);

  let dashboard: DashboardPayload = {
    generatedAt: new Date().toISOString(),
    source,
    ...(persisted?.latestPrices ? { latestPrices: persisted.latestPrices } : {}),
    config: PRODUCTION_STRATEGY,
    portfolioConfig: PRODUCTION_PORTFOLIO,
    portfolioState: stage21.portfolioState,
    currentUniverse,
    currentSignal,
    liveState: stage21.innerState,
    qqq: { close, monthlyMa: currentSignal?.qqqMonthlyMa ?? null, dailySma: sma, momentum20d: close && prior ? close / prior - 1 : null },
    oos: displayedOos,
    backtest: displayedBacktest,
    nportOperations: persisted?.nportOperations,
  };
  if (persisted?.nportOperations) dashboard = applyExtraordinaryRebalance(dashboard, persisted.nportOperations);
  return dashboard;
}
