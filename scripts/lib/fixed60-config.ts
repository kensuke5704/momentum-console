import type { StrategyConfig } from "../../src/lib/types";

// Explicit copy of main PRODUCTION_STRATEGY after the 2026-08-30 Fixed60 freeze.
// Research branch src/lib/config.ts intentionally remains on the older Production rule,
// so Fixed60 studies must import this file rather than branch-local PRODUCTION_STRATEGY.
export const FIXED60_STRATEGY: StrategyConfig = {
  strategyId: "momentum-fixed60-2026-08-v1",
  universe: { size: 80, mode: "sec-nport-breadth" },
  momentum: { oneMonth: 0, threeMonth: 0.2, sixMonth: 0.8, surgeLimit: 0.8, requireAboveQqqScore: true },
  selection: { topN: 2 },
  allocation: { baseTop1Weight: 0.6, concentratedTop1Weight: 0.6, concentrationZGap: 0.25, maxTop1Weight: 0.6 },
  market: { qqqMonthlyMaMonths: 10 },
  risk: { individualStop: 0.175, portfolioCircuit: 0.15 },
  recovery: { qqqDailySmaDays: 100, qqqMomentumDays: 20, confirmationDays: 10 },
  execution: { entry: "next-session-open", exit: "next-session-open", transactionCost: 0.001 },
  backtestStart: "2020-01-01",
};
