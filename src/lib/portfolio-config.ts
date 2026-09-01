import {PRODUCTION_STRATEGY} from "./config";

export const PRODUCTION_PORTFOLIO = Object.freeze({
  strategyId: "momentum-stage21-sbi-2026-09-v1",
  legacyInnerStrategyId: PRODUCTION_STRATEGY.strategyId,
  oosStartDate: "2026-09-02",
  weights: {
    NORMAL: {fixed60: 0.85, gldm: 0.15, cash: 0},
    YELLOW: {fixed60: 0.555, gldm: 0.225, cash: 0.22},
    DEEP: {fixed60: 0.255, gldm: 0.30, cash: 0.445},
  },
  cftc: {
    contractCode: "209742",
    participant: "Asset Manager / Institutional",
    lookbackReports: 4,
    publicationLagDays: 7,
  },
  m3: {
    shadowFixed60Weight: 0.85,
    shadowGWeight: 0.15,
    lookbackSessions: 20,
    enterCoreReturnBelow: 0,
    enterUnderperformanceVsQqq: -0.10,
    exitUnderperformanceVsQqq: -0.03,
    exitConfirmationSessions: 5,
  },
  execution: {
    rebalance: "next-session-open",
    transactionCost: 0.001,
    monthlyRebalance: true,
    wholeSharesAtBroker: true,
  },
  researchReference: {
    releaseAwareHistoricalCagr: 0.48607237745471776,
    historicalMaxDrawdown: -0.168859518560033,
    planningCagrProxy: 0.43657312844139795,
    rolling36MedianCagr: 0.43657312844139795,
    rolling36P10Cagr: 0.3518527066882371,
    rolling36WorstCagr: 0.23420520311820514,
    note: "Same-sample robustness reference; not a calibrated future-return forecast.",
  },
} as const);

export type PortfolioRegime = keyof typeof PRODUCTION_PORTFOLIO.weights;
