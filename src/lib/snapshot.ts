import { PRODUCTION_STRATEGY } from "./config";
import { initialEngineState } from "./strategy/state-machine";
import type { DashboardPayload } from "./types";

const state = initialEngineState();
export const SNAPSHOT_DASHBOARD: DashboardPayload = {
  generatedAt: "", source: "snapshot", warning: "生成済みの市場データがありません。月次・日次同期を実行してください。", config: PRODUCTION_STRATEGY,
  currentUniverse: null, universeHistory: [], currentSignal: null, liveState: state,
  qqq: { close: null, monthlyMa: null, dailySma: null, momentum20d: null },
  backtest: { strategyId: PRODUCTION_STRATEGY.strategyId, equityCurve: [], stats: { cagr: 0, maxDrawdown: 0, annualizedVolatility: 0, calmar: null, finalEquity: 1 }, benchmark: null, events: [] },
};
