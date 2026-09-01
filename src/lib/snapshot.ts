import { PRODUCTION_STRATEGY } from "./config";
import { PRODUCTION_PORTFOLIO } from "./portfolio-config";
import { initialEngineState } from "./strategy/state-machine";
import { emptyForwardOos } from "./oos";
import type { DashboardPayload, PortfolioLiveState } from "./types";

const state = initialEngineState();
const portfolioState: PortfolioLiveState = {
  strategyId: PRODUCTION_PORTFOLIO.strategyId,
  asOf: "",
  regime: "NORMAL",
  cftc: { reportDate: null, net: null, priorNet: null, yellow: false },
  m3: { deep: false, coreReturn20: null, qqqReturn20: null, gap: null, recoveryConfirm: 0 },
  fixed60: { strategyId: PRODUCTION_STRATEGY.strategyId, riskState: state.state, symbols: [], innerWeights: [] },
  targets: [{ symbol: "CASH", weight: 1, role: "CASH" }],
  nextAction: { type: "HOLD", executionDate: null, targets: [{ symbol: "CASH", weight: 1, role: "CASH" }], reason: "生成済み市場データ待ち" },
};

export const SNAPSHOT_DASHBOARD: DashboardPayload = {
  generatedAt: "", source: "snapshot", warning: "生成済みの市場データがありません。月次・日次同期を実行してください。", config: PRODUCTION_STRATEGY,
  portfolioConfig: PRODUCTION_PORTFOLIO,
  portfolioState,
  currentUniverse: null, currentSignal: null, liveState: state,
  qqq: { close: null, monthlyMa: null, dailySma: null, momentum20d: null },
  oos: emptyForwardOos(PRODUCTION_PORTFOLIO.strategyId),
  backtest: { strategyId: PRODUCTION_PORTFOLIO.strategyId, equityCurve: [], stats: { cagr: 0, maxDrawdown: 0, annualizedVolatility: 0, calmar: null, finalEquity: 1 }, benchmark: null, events: [] },
};
