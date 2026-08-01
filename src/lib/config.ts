import type { StrategyConfig, TickerConfig } from "./types";

export const TICKERS: TickerConfig[] = [
  { symbol: "TQQQ", genre: "Nasdaq Beta" },
  { symbol: "SOXL", genre: "AI Semi" },
  { symbol: "NVDL", genre: "AI Semi" },
  { symbol: "CLSK", genre: "Crypto" },
  { symbol: "RKLB", genre: "Space" },
  { symbol: "LUNR", genre: "Space" },
  { symbol: "IONQ", genre: "Quantum" },
  { symbol: "RGTI", genre: "Quantum" },
  { symbol: "QBTS", genre: "Quantum" },
  { symbol: "UPST", genre: "AI Fintech" },
  { symbol: "AFRM", genre: "AI Fintech" },
  { symbol: "APP", genre: "AI Application" },
  { symbol: "QQQ", genre: "Nasdaq Beta" },
  { symbol: "AVAV", genre: "Defense" },
  { symbol: "KTOS", genre: "Defense" },
  { symbol: "RCAT", genre: "Defense" },
  { symbol: "BE", genre: "Nuclear" },
  { symbol: "PLTR", genre: "Defense AI" },
  { symbol: "CRWD", genre: "Cybersecurity" },
  { symbol: "DDOG", genre: "AI Infrastructure" },
  { symbol: "NET", genre: "AI Infrastructure" },
  { symbol: "SYM", genre: "Robotics" },
  { symbol: "NVDA", genre: "AI Semi" },
  { symbol: "OKLO", genre: "Nuclear" },
  { symbol: "PANW", genre: "Cybersecurity" },
  { symbol: "MSTR", genre: "Crypto" },
  { symbol: "COIN", genre: "Crypto" },
  { symbol: "RIOT", genre: "Crypto" },
  { symbol: "ASTS", genre: "Space" },
  { symbol: "VRT", genre: "AI Infrastructure" },
  { symbol: "BBAI", genre: "Defense AI" },
  { symbol: "MOD", genre: "Energy Infrastructure" },
  { symbol: "PWR", genre: "Energy Infrastructure" },
  { symbol: "LITE", genre: "Optical Networking" },
  { symbol: "FN", genre: "Optical Networking" },
  { symbol: "MU", genre: "AI Semi" },
  { symbol: "S", genre: "Cybersecurity" },
  { symbol: "SERV", genre: "Robotics" },
];

export const DEFAULT_STRATEGY: StrategyConfig = {
  topN: 10,
  weights: {
    oneMonth: 0.2,
    threeMonth: 0.4,
    sixMonth: 0.4,
  },
  surgeLimit: 0.8,
  qqqMaMonths: 10,
  frontierMax: 4,
  genreLimits: {
    Quantum: 2,
    "AI Semi": 2,
    Space: 2,
  },
  frontierGenres: ["Quantum", "Space", "Nuclear", "Crypto"],
  excludedTickers: [],
  backtestStart: "2023-01-01",
  targetTotalJpy: 1000000,
  usdJpy: 163.6375,
};

type LegacyStrategyConfig = Partial<StrategyConfig> & {
  targetAmountUsd?: number;
};

export function normalizeStrategyConfig(
  value: LegacyStrategyConfig,
): StrategyConfig {
  const {
    targetAmountUsd: legacyTargetAmountUsd,
    weights,
    genreLimits,
    ...current
  } = value;
  const topN =
    typeof current.topN === "number" && current.topN > 0
      ? current.topN
      : DEFAULT_STRATEGY.topN;
  const usdJpy =
    typeof current.usdJpy === "number" && current.usdJpy > 0
      ? current.usdJpy
      : DEFAULT_STRATEGY.usdJpy;
  const legacyTotal =
    typeof legacyTargetAmountUsd === "number" && legacyTargetAmountUsd > 0
      ? legacyTargetAmountUsd * usdJpy * topN
      : undefined;

  return {
    ...DEFAULT_STRATEGY,
    ...current,
    topN,
    usdJpy,
    targetTotalJpy:
      typeof current.targetTotalJpy === "number" &&
      current.targetTotalJpy > 0
        ? current.targetTotalJpy
        : legacyTotal ?? DEFAULT_STRATEGY.targetTotalJpy,
    weights: { ...DEFAULT_STRATEGY.weights, ...weights },
    genreLimits: { ...DEFAULT_STRATEGY.genreLimits, ...genreLimits },
  };
}

export function getTargetAmountUsd(config: StrategyConfig) {
  if (config.topN <= 0 || config.usdJpy <= 0) return 0;
  return config.targetTotalJpy / config.usdJpy / config.topN;
}
