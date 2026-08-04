import type { StrategyConfig } from "./types";

export const FROZEN_STRATEGY_ID = "momentum-2026-08-v1";
export const FROZEN_STRATEGY_FROZEN_AT = "2026-08-04";
export const FROZEN_STRATEGY_FIRST_SIGNAL_MONTH = "2026-07";
export const FROZEN_STRATEGY_FIRST_HOLDING_MONTH = "2026-08";

/**
 * Immutable strategy definition used for forward out-of-sample tracking.
 *
 * Do not derive this object from DEFAULT_STRATEGY. Future production changes
 * must not rewrite the historical OOS benchmark that was frozen on 2026-08-04.
 */
export const FROZEN_STRATEGY: StrategyConfig = {
  topN: 9,
  weights: {
    oneMonth: 0.1,
    threeMonth: 0.4,
    sixMonth: 0.5,
  },
  surgeLimit: 0.8,
  qqqMaMonths: 10,
  genreMax: 2,
  frontierMax: 2,
  frontierGenres: ["Quantum", "Space", "Nuclear", "Crypto"],
  excludedTickers: [],
  backtestStart: "2023-01-01",
  targetTotalJpy: 1000000,
  usdJpy: 163.6375,
};
