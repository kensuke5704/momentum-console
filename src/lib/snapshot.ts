import { DEFAULT_STRATEGY, getTargetAmountUsd } from "./config";
import type {
  BacktestRow,
  DashboardPayload,
  MomentumRow,
  PortfolioRow,
} from "./types";

type SnapshotInput = Omit<
  MomentumRow,
  "rank" | "eligible" | "selected" | "reason"
> & {
  rank: number;
  eligible: boolean;
};

const rows: SnapshotInput[] = [
  { symbol: "TQQQ", genre: "Nasdaq Beta", current: 84.56, oneMonth: 0.367, threeMonth: 0.7076, sixMonth: 0.5504, score: 0.5766, rank: 13, eligible: true },
  { symbol: "SOXL", genre: "AI Semi", current: 224.34, oneMonth: 0.9017, threeMonth: 2.574, sixMonth: 4.4372, score: 2.9848, rank: 1, eligible: false },
  { symbol: "NVDL", genre: "AI Semi", current: 34.24, oneMonth: -0.0026, threeMonth: 0.3427, sixMonth: 0.2738, score: 0.2461, rank: 25, eligible: true },
  { symbol: "CLSK", genre: "Crypto", current: 18.29, oneMonth: 0.6086, threeMonth: 0.8382, sixMonth: 0.2113, score: 0.5415, rank: 14, eligible: true },
  { symbol: "RKLB", genre: "Space", current: 143.48, oneMonth: 0.8629, threeMonth: 1.0764, sixMonth: 2.4048, score: 1.5651, rank: 4, eligible: false },
  { symbol: "LUNR", genre: "Space", current: 43.83, oneMonth: 0.7681, threeMonth: 1.6596, sixMonth: 3.6137, score: 2.2629, rank: 2, eligible: true },
  { symbol: "IONQ", genre: "Quantum", current: 72.07, oneMonth: 0.7115, threeMonth: 0.8783, sixMonth: 0.4619, score: 0.6784, rank: 10, eligible: true },
  { symbol: "RGTI", genre: "Quantum", current: 25.54, oneMonth: 0.5883, threeMonth: 0.4661, sixMonth: -0.0012, score: 0.3036, rank: 20, eligible: true },
  { symbol: "QBTS", genre: "Quantum", current: 30.14, oneMonth: 0.6497, threeMonth: 0.6049, sixMonth: 0.3295, score: 0.5037, rank: 16, eligible: true },
  { symbol: "UPST", genre: "AI Fintech", current: 33.79, oneMonth: 0.1086, threeMonth: 0.2409, sixMonth: -0.2484, score: 0.0187, rank: 32, eligible: false },
  { symbol: "AFRM", genre: "AI Fintech", current: 73.65, oneMonth: 0.1602, threeMonth: 0.5677, sixMonth: 0.0381, score: 0.2743, rank: 21, eligible: true },
  { symbol: "APP", genre: "AI Application", current: 613.09, oneMonth: 0.3826, threeMonth: 0.4101, sixMonth: 0.0227, score: 0.2497, rank: 24, eligible: true },
  { symbol: "QQQ", genre: "Nasdaq Beta", current: 738.31, oneMonth: 0.116, threeMonth: 0.2157, sixMonth: 0.1923, score: 0.1864, rank: 26, eligible: false },
  { symbol: "AVAV", genre: "Defense", current: 207.24, oneMonth: 0.1294, threeMonth: -0.1784, sixMonth: -0.2584, score: -0.1489, rank: 36, eligible: false },
  { symbol: "KTOS", genre: "Defense", current: 64.13, oneMonth: 0.0767, threeMonth: -0.2559, sixMonth: -0.1573, score: -0.1499, rank: 37, eligible: false },
  { symbol: "RCAT", genre: "Defense", current: 14.5, oneMonth: 0.3098, threeMonth: 0.2446, sixMonth: 0.9542, score: 0.5415, rank: 15, eligible: true },
  { symbol: "BE", genre: "Nuclear", current: 285, oneMonth: -0.0103, threeMonth: 0.8308, sixMonth: 1.6089, score: 0.9738, rank: 5, eligible: true },
  { symbol: "PLTR", genre: "Defense AI", current: 156.54, oneMonth: 0.1346, threeMonth: 0.141, sixMonth: -0.0707, score: 0.0551, rank: 30, eligible: false },
  { symbol: "CRWD", genre: "Cybersecurity", current: 182.75, oneMonth: 0.6158, threeMonth: 0.9651, sixMonth: 0.4357, score: 0.6835, rank: 9, eligible: true },
  { symbol: "DDOG", genre: "AI Infrastructure", current: 247.35, oneMonth: 0.8462, threeMonth: 1.2093, sixMonth: 0.5458, score: 0.8713, rank: 6, eligible: false },
  { symbol: "NET", genre: "AI Infrastructure", current: 241.82, oneMonth: 0.1408, threeMonth: 0.4044, sixMonth: 0.2078, score: 0.273, rank: 22, eligible: true },
  { symbol: "SYM", genre: "Robotics", current: 46.43, oneMonth: -0.1904, threeMonth: -0.1524, sixMonth: -0.4457, score: -0.2774, rank: 38, eligible: false },
  { symbol: "NVDA", genre: "AI Semi", current: 211.14, oneMonth: 0.009, threeMonth: 0.1916, sixMonth: 0.1929, score: 0.1556, rank: 27, eligible: false },
  { symbol: "OKLO", genre: "Nuclear", current: 66.88, oneMonth: 0.0292, threeMonth: 0.0624, sixMonth: -0.2681, score: -0.0764, rank: 34, eligible: false },
  { symbol: "PANW", genre: "Cybersecurity", current: 281.69, oneMonth: 0.5517, threeMonth: 0.8916, sixMonth: 0.4816, score: 0.6596, rank: 12, eligible: true },
  { symbol: "ASTS", genre: "Space", current: 113.41, oneMonth: 0.6236, threeMonth: 0.4321, sixMonth: 1.018, score: 0.7048, rank: 8, eligible: true },
  { symbol: "LITE", genre: "Optical Networking", current: 854.96, oneMonth: -0.0039, threeMonth: 0.2198, sixMonth: 1.6294, score: 0.7389, rank: 7, eligible: true },
  { symbol: "MOD", genre: "Energy Infrastructure", current: 278.91, oneMonth: 0.195, threeMonth: 0.2273, sixMonth: 0.7203, score: 0.4181, rank: 17, eligible: true },
];

const selectedSymbols = new Set([
  "LUNR",
  "BE",
  "LITE",
  "ASTS",
  "CRWD",
  "IONQ",
  "PANW",
  "TQQQ",
  "RCAT",
  "MOD",
]);

const momentum: MomentumRow[] = rows.map((row) => ({
  ...row,
  selected: selectedSymbols.has(row.symbol),
  reason: row.eligible
    ? selectedSymbols.has(row.symbol)
      ? "採用"
      : "テーマ上限または順位"
    : row.oneMonth !== null && row.oneMonth >= DEFAULT_STRATEGY.surgeLimit
      ? "1か月急騰を除外"
      : "QQQスコア以下",
}));

const portfolio: PortfolioRow[] = momentum
  .filter((row) => row.selected)
  .sort((a, b) => (a.rank ?? 999) - (b.rank ?? 999))
  .map((row) => ({
    ...row,
    targetAmount: getTargetAmountUsd(DEFAULT_STRATEGY),
    targetShares:
      row.current && row.current > 0
        ? getTargetAmountUsd(DEFAULT_STRATEGY) / row.current
        : null,
  }));

const backtestInput: Array<
  [string, number, number, string, string[]?]
> = [
  ["2023-01-31", 0, 1, "Cash"],
  ["2023-02-28", 0.108, 1.108, "RiskOn"],
  ["2023-03-31", -0.0583, 1.0434, "RiskOn"],
  ["2023-04-30", 0.1981, 1.25, "RiskOn"],
  ["2023-05-31", 0.1555, 1.4444, "RiskOn"],
  ["2023-06-30", 0.2115, 1.7499, "RiskOn"],
  ["2023-07-31", -0.0838, 1.6032, "RiskOn"],
  ["2023-08-31", -0.1553, 1.3543, "RiskOn"],
  ["2023-09-30", 0.0529, 1.4259, "RiskOn"],
  ["2023-10-31", 0.1475, 1.6362, "RiskOn"],
  ["2023-11-30", 0.005, 1.6445, "RiskOn"],
  ["2023-12-31", 0.0215, 1.6798, "RiskOn"],
  ["2024-01-31", 0.3341, 2.241, "RiskOn"],
  ["2024-02-29", 0.0273, 2.3021, "RiskOn"],
  ["2024-03-31", -0.083, 2.1111, "RiskOn"],
  ["2024-04-30", 0.1465, 2.4205, "RiskOn"],
  ["2024-05-31", -0.0089, 2.3988, "RiskOn"],
  ["2024-06-30", -0.0653, 2.2422, "RiskOn"],
  ["2024-07-31", 0.1472, 2.5722, "RiskOn"],
  ["2024-08-31", 0.1632, 2.992, "RiskOn"],
  ["2024-09-30", 0.1244, 3.3644, "RiskOn"],
  ["2024-10-31", 0.7291, 5.8175, "RiskOn"],
  ["2024-11-30", 0.1906, 6.9263, "RiskOn"],
  ["2024-12-31", 0.0006, 6.9308, "RiskOn"],
  ["2025-01-31", -0.1614, 5.8121, "RiskOn"],
  ["2025-02-28", -0.0481, 5.5325, "RiskOn"],
  ["2025-03-31", 0, 5.5325, "Cash"],
  ["2025-04-30", 0, 5.5325, "Cash"],
  ["2025-05-31", 0.2114, 6.702, "RiskOn"],
  ["2025-06-30", 0.1392, 7.6352, "RiskOn"],
  ["2025-07-31", -0.0406, 7.3255, "RiskOn"],
  ["2025-08-31", 0.3917, 10.1949, "RiskOn"],
  ["2025-09-30", 0.1211, 11.4299, "RiskOn"],
  ["2025-10-31", -0.119, 10.07, "RiskOn"],
  ["2025-11-30", 0.1065, 11.1424, "RiskOn"],
  ["2025-12-31", 0.0767, 11.9974, "RiskOn"],
  ["2026-01-31", 0.0198, 12.2353, "RiskOn"],
  ["2026-02-28", 0.0201, 12.4812, "RiskOn"],
  ["2026-03-31", 0, 12.4812, "Cash"],
  ["2026-04-30", 0.2192, 15.2164, "RiskOn"],
];

const backtestRows: BacktestRow[] = backtestInput.map(
  ([signalMonth, monthlyReturn, equity, market]) => ({
    signalMonth,
    entryDate: null,
    exitDate: null,
    market: market as BacktestRow["market"],
    picks: [],
    monthlyReturn,
    equity,
  }),
);

export const SNAPSHOT_DASHBOARD: DashboardPayload = {
  source: "snapshot",
  asOf: "2026-05-31",
  warning:
    "ライブデータを取得できなかったため、元スプレッドシートの最終確認値を表示しています。",
  market: {
    state: "RiskOn",
    decisionDate: "2026-05-31",
    qqq: 738.31,
    ma10: null,
    qqqScore: 0.1864,
    allocationStatus: "Invest",
    selectedCount: 10,
  },
  momentum,
  portfolio,
  backtest: {
    rows: backtestRows,
    stats: {
      finalEquity: 15.2164,
      cagr: 1.263,
      averageMonthlyReturn: 0.0811,
      monthlyVolatility: 0.1629,
      annualizedVolatility: 0.5644,
      maxDrawdown: -0.2261,
    },
  },
  config: DEFAULT_STRATEGY,
};
