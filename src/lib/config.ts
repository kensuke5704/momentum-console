import type { StrategyConfig } from "./types";

/**
 * Frozen Fixed60 inner alpha/risk engine. Stage21 is the production portfolio
 * wrapper and production/OOS identity; this config remains the single source
 * of truth for Top2 selection and the inner Fixed60 state machine.
 */
export const FIXED60_INNER_STRATEGY = Object.freeze({
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
} as const satisfies StrategyConfig);

/** Legacy compatibility alias; production portfolio identity is PRODUCTION_PORTFOLIO. */
export const PRODUCTION_STRATEGY: StrategyConfig = FIXED60_INNER_STRATEGY;
export const DEFAULT_STRATEGY: StrategyConfig = FIXED60_INNER_STRATEGY;
